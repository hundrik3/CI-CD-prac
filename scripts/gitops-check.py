#!/usr/bin/env python3
"""Verify actual ArgoCD health, drift healing and Kubernetes telemetry."""
import json
import os
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parents[1]
os.chdir(root)
os.environ['KUBECONFIG'] = str(root / '.local/kubeconfig')

def kubectl(*args):
    return subprocess.check_output(['kubectl', *args], text=True)

def wait_for(name, predicate, timeout=300):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            print(name + ': PASS', flush=True)
            return
        time.sleep(3)
    raise RuntimeError(name + ' timed out')

def app_status():
    return json.loads(kubectl('-n', 'argocd', 'get', 'application', 'portfolio', '-o', 'json' )).get('status', {})

def ready():
    state = app_status()
    expected = os.environ.get('GITOPS_REVISION')
    sync = state.get('sync', {})
    return sync.get('status') == 'Synced' and state.get('health', {}).get('status') == 'Healthy' and (not expected or sync.get('revision') == expected)

wait_for('ArgoCD Synced and Healthy at the selected revision', ready)
# Mutate exactly the deployment created for this lab, then wait for GitOps healing.
kubectl('-n', 'portfolio', 'scale', 'deployment/portfolio-api', '--replicas=2')
wait_for('replica drift healed to one', lambda: json.loads(kubectl('-n', 'portfolio', 'get', 'deployment', 'portfolio-api', '-o', 'json'))['spec']['replicas'] == 1)
subprocess.run(['kubectl', '-n', 'portfolio', 'rollout', 'status', 'deployment/portfolio-api', '--timeout=120s'], check=True)
subprocess.run(['python', 'scripts/smoke-observability.py', '--app', 'http://127.0.0.1:8081', '--output', '.local/kubernetes-evidence.json'], check=True)
final = app_status()
Path('.local/gitops-evidence.json').write_text(json.dumps({'sync': final['sync'], 'health': final['health'], 'replica_drift_healed': True}, indent=2) + '\n')
