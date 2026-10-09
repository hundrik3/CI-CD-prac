#!/usr/bin/env python3
"""Exercise real controller transitions and Prometheus quality gates, locally."""
import collections
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ['KUBECONFIG'] = str(ROOT / '.local/kubeconfig')
NS = 'progressive-delivery'
context = subprocess.check_output(['kubectl', 'config', 'current-context'], text=True).strip()
if context != 'kind-portfolio':
    raise SystemExit('Expected dedicated kind-portfolio context')
CLIENT = urllib.request.build_opener(urllib.request.ProxyHandler({}))
Path('.local/rollouts-evidence.json').unlink(missing_ok=True)
EVIDENCE = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'checks': []}

def kubectl(*args):
    return subprocess.check_output(['kubectl', '-n', NS, *args], text=True)

def state():
    return json.loads(kubectl('get', 'rollout', 'release-api', '-o', 'json'))

def wait(name, predicate, timeout=240):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            if predicate():
                print('PASS: ' + name, flush=True)
                return
        except (urllib.error.URLError, TimeoutError):
            pass  # Service endpoints may briefly have no ready pod during switches.
        time.sleep(2)
    raise RuntimeError(name + ' timed out: ' + json.dumps(state().get('status', {})))

def status_patch(value):
    kubectl('patch', 'rollout', 'release-api', '--subresource=status', '--type=merge', '-p', json.dumps({'status': value}))

def promote():
    # Same status-subresource operation as kubectl argo rollouts promote.
    status_patch({'pauseConditions': None})

def release(version, bad=False):
    kubectl('patch', 'rollout', 'release-api', '--type=merge', '-p', json.dumps({'spec': {'template': {'spec': {'containers': [{
        'name': 'app', 'image': 'portfolio-api:v1', 'imagePullPolicy': 'Never', 'ports': [{'containerPort': 8080}],
        'env': [{'name': 'APP_VERSION', 'value': version}, {'name': 'APP_FAIL_WORK', 'value': str(bad).lower()}],
        **CONTAINER_SECURITY}]}}}}))
    generation = state()['metadata']['generation']
    wait('canary paused at 20% for ' + version, lambda: str(state().get('status', {}).get('observedGeneration')) == str(generation) and state().get('status', {}).get('currentStepIndex') == 1 and bool(state().get('status', {}).get('pauseConditions')))

def healthy():
    s = state().get('status', {})
    return s.get('phase') == 'Healthy' and s.get('currentPodHash') == s.get('stableRS')

def http(url):
    try:
        with CLIENT.open(url, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())

def version(port):
    return http(BASE + ':' + str(port) + '/')[1]['version']

def sample_versions(count):
    return collections.Counter(version(30083) for _ in range(count))

def snapshot(name):
    s = state()['status']
    services = {name: json.loads(kubectl('get', 'service', name, '-o', 'json'))['spec']['selector'] for name in ('release-stable','release-canary','release-api')}
    EVIDENCE['checks'].append({'name': name, 'phase': s.get('phase'), 'step': s.get('currentStepIndex'), 'stable_hash': s.get('stableRS'), 'current_hash': s.get('currentPodHash'), 'service_selectors': services,
        'replica_sets': json.loads(kubectl('get', 'rs', '-l', 'app=release-api', '-o', 'json'))['items']})
    # Keep only useful replica counts and hashes; exclude Kubernetes internals.
    EVIDENCE['checks'][-1]['replica_sets'] = [{'name': x['metadata']['name'], 'desired': x['spec']['replicas'], 'ready': x.get('status', {}).get('readyReplicas', 0)} for x in EVIDENCE['checks'][-1]['replica_sets']]

def latest_analysis():
    items = json.loads(kubectl('get', 'analysisrun', '-o', 'json'))['items']
    return sorted(items, key=lambda x: x['metadata']['creationTimestamp'])[-1]

stop = threading.Event()
def traffic():
    while not stop.is_set():
        try:
            http(BASE + ':30082/work?delay_ms=0')
        except (OSError, ValueError):
            pass
        stop.wait(0.1)

node = json.loads(subprocess.check_output(['docker', 'inspect', 'portfolio-control-plane'], text=True))[0]
BASE = 'http://' + node['NetworkSettings']['Networks']['portfolio-kind']['IPAddress']
CONTAINER_SECURITY = json.loads(kubectl('get', 'rollout', 'release-api', '-o', 'json'))['spec']['template']['spec']['containers'][0]
CONTAINER_SECURITY = {k: v for k, v in CONTAINER_SECURITY.items() if k not in ('name','image','imagePullPolicy','env','ports')}
kubectl('apply', '-f', 'platform/rollouts/resources.yaml')
status_patch({'promoteFull': True})
wait('initial v1 fully available', lambda: healthy() and version(30081) == 'v1')
assert version(30081) == 'v1'
thread = threading.Thread(target=traffic, daemon=True)
thread.start()
try:
    release('v2')
    wait('stable v1 and candidate v2 endpoints', lambda: version(30081) == 'v1' and version(30082) == 'v2')
    snapshot('20% pause')
    observed = {}
    def mixed_ready():
        observed.clear()
        observed.update(sample_versions(100))
        return observed.get('v1', 0) > 0 and observed.get('v2', 0) > 0
    wait('shared service reaches both versions after endpoint convergence', mixed_ready)
    EVIDENCE['mixed_service_sample'] = dict(observed)
    # Warm the isolated canary scrape before the analysis starts.
    time.sleep(12)
    promote()
    wait('quality analysis passed and canary paused at 60%', lambda: state()['status'].get('currentStepIndex') == 4 and bool(state()['status'].get('pauseConditions')))
    assert latest_analysis()['status']['phase'] == 'Successful'
    EVIDENCE['successful_analysis'] = latest_analysis()['status']
    snapshot('60% pause after successful analysis')
    promote()
    wait('v2 promoted to stable', lambda: healthy() and version(30081) == 'v2')
    snapshot('v2 stable')
    GOOD_TEMPLATE = state()['spec']['template']
    release('v3-manual')
    wait('manual candidate reachable', lambda: version(30082) == 'v3-manual')
    status_patch({'abort': True})
    wait('manual abort restores v2 service', lambda: state()['status'].get('abort') is True and version(30081) == 'v2')
    wait('manual abort removes candidate replicas', lambda: all(x['spec']['replicas'] == 0 for x in json.loads(kubectl('get', 'rs', '-l', 'app=release-api', '-o', 'json'))['items'] if x['metadata']['labels'].get('rollouts-pod-template-hash') == state()['status']['currentPodHash']))
    wait('shared service exclusively returns stable v2', lambda: sample_versions(30) == {'v2': 30})
    snapshot('manual abort')
    # Restore the exact successful template; abort does not rewrite desired state.
    kubectl('patch', 'rollout', 'release-api', '--type=merge', '-p', json.dumps({'spec': {'template': GOOD_TEMPLATE}}))
    wait('desired state restored after manual abort', healthy)
    release('v-broken', bad=True)
    wait('broken candidate returns real HTTP 500', lambda: http(BASE + ':30082/work?delay_ms=0')[0] == 500)
    time.sleep(12)
    promote()
    wait('failed quality analysis automatically aborts candidate', lambda: state()['status'].get('abort') is True and latest_analysis()['status'].get('phase') == 'Failed')
    EVIDENCE['failed_analysis'] = latest_analysis()['status']
    assert any(x['name'] == 'success-ratio' and x['phase'] == 'Failed' for x in latest_analysis()['status']['metricResults'])
    wait('stable v2 remains healthy after automatic abort', lambda: version(30081) == 'v2' and http(BASE + ':30081/work?delay_ms=0')[0] == 200)
    wait('automatic abort removes candidate replicas', lambda: all(x['spec']['replicas'] == 0 for x in json.loads(kubectl('get', 'rs', '-l', 'app=release-api', '-o', 'json'))['items'] if x['metadata']['labels'].get('rollouts-pod-template-hash') == state()['status']['currentPodHash']))
    wait('shared service exclusively returns stable v2', lambda: sample_versions(30) == {'v2': 30})
    snapshot('automatic abort protects stable v2')
    stop.set()
    thread.join(timeout=6)
    kubectl('patch', 'rollout', 'release-api', '--type=merge', '-p', json.dumps({'spec': {'template': GOOD_TEMPLATE}}))
    wait('stable template restored before no-traffic test', healthy)
    release('v-no-traffic')
    wait('no-traffic candidate reachable', lambda: version(30082) == 'v-no-traffic')
    time.sleep(12)
    promote()
    wait('zero business traffic fails closed', lambda: state()['status'].get('abort') is True and latest_analysis()['status'].get('phase') == 'Failed')
    EVIDENCE['no_traffic_analysis'] = latest_analysis()['status']
    assert any(x['name'] == 'sample-count' and x['phase'] == 'Failed' for x in latest_analysis()['status']['metricResults'])
    snapshot('no traffic rejected')
finally:
    stop.set()
    thread.join(timeout=6)
# Restore the known baseline explicitly. Full promotion here is cleanup only.
kubectl('apply', '-f', 'platform/rollouts/resources.yaml')
status_patch({'promoteFull': True})
wait('baseline v1 restored', lambda: healthy() and version(30081) == 'v1')
EVIDENCE['baseline_restored'] = True
Path('.local/rollouts-evidence.json').write_text(json.dumps(EVIDENCE, indent=2) + '\n')
print('PASS: promotion, manual abort, automatic metric-based abort; baseline restored')
