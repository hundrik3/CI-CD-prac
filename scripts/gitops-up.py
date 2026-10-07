#!/usr/bin/env python3
"""Bootstrap the dedicated local Kind cluster and its ArgoCD application."""
import os
from pathlib import Path
import socket
import subprocess
import time
import json
import yaml

os.umask(0o077)
root = Path(__file__).resolve().parents[1]
os.chdir(root)
(root / '.local').mkdir(exist_ok=True)
env = dict(os.environ)
env['KUBECONFIG'] = str(root / '.local/kubeconfig')
cluster = 'portfolio'
node = cluster + '-control-plane'
managed = Path('/etc/codex/network-policy.json').exists()
if managed:
    proxy_ip = socket.gethostbyname('proxy')
    env['HTTP_PROXY'] = env['HTTPS_PROXY'] = 'http://' + proxy_ip + ':8080'
env['NO_PROXY'] = env.get('NO_PROXY', '') + ',localhost,127.0.0.1,.svc,.cluster.local,10.96.0.0/12,10.244.0.0/16'

def run(*args, **kwargs):
    return subprocess.run(args, env=env, check=True, **kwargs)

networks = run('docker', 'network', 'ls', '--format', '{{.Name}}', capture_output=True, text=True).stdout.splitlines()
if 'portfolio-kind' not in networks:
    run('docker', 'network', 'create', 'portfolio-kind')
env['KIND_EXPERIMENTAL_DOCKER_NETWORK'] = 'portfolio-kind'
clusters = run('kind', 'get', 'clusters', capture_output=True, text=True).stdout.splitlines()
if cluster not in clusters:
    config = 'platform/kind/cluster.yaml'
    if managed:
        spec = yaml.safe_load(Path(config).read_text())
        spec['containerdConfigPatches'] = ['[plugins."io.containerd.grpc.v1.cri".containerd]\n  snapshotter = "native"']
        config = '.local/kind-managed.yaml'
        Path(config).write_text(yaml.safe_dump(spec))
    command = ['kind', 'create', 'cluster', '--name', cluster, '--image', 'kindest/node:v1.32.2', '--config', config, '--wait', '180s', '--retain']
    process = subprocess.Popen(command, env=env)
    if managed:
        # This nested environment omits the kernel log device; touch only our node.
        for _ in range(120):
            check = subprocess.run(['docker', 'exec', node, 'sh', '-c', 'test -e /dev/kmsg || mknod -m 600 /dev/kmsg c 1 11'], capture_output=True)
            if check.returncode == 0 or process.poll() is not None:
                break
            time.sleep(1)
    code = process.wait()
    if code:
        raise SystemExit(code)
else:
    run('kind', 'export', 'kubeconfig', '--name', cluster)
run('kubectl', 'wait', '--for=condition=Ready', 'nodes', '--all', '--timeout=180s')
run('kind', 'load', 'docker-image', 'portfolio-api:v1', '--name', cluster)
namespace = run('kubectl', 'create', 'namespace', 'argocd', '--dry-run=client', '-o', 'yaml', capture_output=True).stdout
run('kubectl', 'apply', '-f', '-', input=namespace)
manifest = root / '.local/argocd-v3.5.4.yaml'
run('curl', '-fsSL', 'https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/core-install.yaml', '-o', str(manifest))
run('kubectl', 'apply', '--server-side', '-n', 'argocd', '-f', str(manifest))
if managed:
    for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY'):
        run('kubectl', '-n', 'argocd', 'set', 'env', 'deployment/argocd-repo-server', name + '=' + env[name], stdout=subprocess.DEVNULL)
    cert = os.environ.get('CODEX_PROXY_CERT')
    if cert:
        cm = run('kubectl', '-n', 'argocd', 'create', 'configmap', 'argocd-tls-certs-cm', '--from-file=github.com=' + cert, '--dry-run=client', '-o', 'yaml', capture_output=True).stdout
        run('kubectl', '-n', 'argocd', 'apply', '-f', '-', input=cm)
# Avoid two large repo-server replicas during updates on small nested runtimes.
run('kubectl', '-n', 'argocd', 'patch', 'deployment', 'argocd-repo-server', '--type=merge', '-p', '{"spec":{"strategy":{"type":"Recreate","rollingUpdate":null}}}')
run('kubectl', '-n', 'argocd', 'rollout', 'status', 'deployment/argocd-repo-server', '--timeout=240s')
run('kubectl', '-n', 'argocd', 'rollout', 'status', 'statefulset/argocd-application-controller', '--timeout=240s')
run('docker', 'compose', '-f', 'compose.yaml', '-f', 'compose.gitops.yaml', 'up', '-d', '--remove-orphans')
metadata = json.loads(run('docker', 'inspect', 'ci-cd-prac-otel-collector-1', capture_output=True, text=True).stdout)[0]
address = metadata['NetworkSettings']['Networks']['portfolio-kind']['IPAddress']
namespace = run('kubectl', 'create', 'namespace', 'portfolio', '--dry-run=client', '-o', 'yaml', capture_output=True).stdout
run('kubectl', 'apply', '-f', '-', input=namespace)
endpoints = {'apiVersion': 'v1', 'kind': 'Endpoints', 'metadata': {'name': 'otel-collector', 'namespace': 'portfolio'}, 'subsets': [{'addresses': [{'ip': address}], 'ports': [{'name': 'otlp-http', 'port': 4318, 'protocol': 'TCP'}]}]}
run('kubectl', 'apply', '-f', '-', input=json.dumps(endpoints).encode())
application = yaml.safe_load_all(Path('platform/argocd/application.yaml').read_text())
documents = list(application)
if env.get('GITOPS_REVISION'):
    documents[-1]['spec']['source']['targetRevision'] = env['GITOPS_REVISION']
run('kubectl', 'apply', '-f', '-', input=yaml.safe_dump_all(documents).encode())
print('ArgoCD now follows main:deploy/overlays/local. Use make gitops-check to verify reconciliation.')
