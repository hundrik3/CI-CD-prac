#!/usr/bin/env python3
"""Install pinned Argo Rollouts into the existing dedicated portfolio cluster."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ['KUBECONFIG'] = str(ROOT / '.local/kubeconfig')

def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)

# Verify the expected context before touching any Kubernetes resource.
context = run('kubectl', 'config', 'current-context', capture_output=True, text=True).stdout.strip()
if context != 'kind-portfolio':
    raise SystemExit('Expected kind-portfolio; run make gitops-up first.')
manifest = ROOT / '.local/argo-rollouts-v1.10.0.yaml'
run('curl', '-fsSL', 'https://raw.githubusercontent.com/argoproj/argo-rollouts/v1.10.0/manifests/install.yaml', '-o', str(manifest))
if hashlib.sha256(manifest.read_bytes()).hexdigest() != 'be25242c55bab7650e0b845da11dbce811f7427deae367e224435e0d766ebe5a':
    raise SystemExit('Argo Rollouts manifest checksum mismatch')
namespace = run('kubectl', 'create', 'namespace', 'argo-rollouts', '--dry-run=client', '-o', 'yaml', capture_output=True).stdout
run('kubectl', 'apply', '-f', '-', input=namespace)
run('kubectl', 'apply', '--server-side', '-n', 'argo-rollouts', '-f', str(manifest))
run('kubectl', '-n', 'argo-rollouts', 'rollout', 'status', 'deployment/argo-rollouts', '--timeout=300s')
run('kubectl', 'apply', '-f', 'platform/rollouts/resources.yaml', '-f', 'platform/rollouts/analysis.yaml')
run('chmod', '-R', 'a+rX', 'platform/rollouts')
run('docker', 'compose', '-f', 'compose.yaml', '-f', 'compose.gitops.yaml', '-f', 'compose.rollouts.yaml', 'up', '-d', '--remove-orphans')
metadata = json.loads(run('docker', 'inspect', 'ci-cd-prac-prometheus-1', capture_output=True, text=True).stdout)[0]
address = metadata['NetworkSettings']['Networks']['portfolio-kind']['IPAddress']
endpoints = {'apiVersion':'v1','kind':'Endpoints','metadata':{'name':'prometheus','namespace':'progressive-delivery'},'subsets':[{'addresses':[{'ip':address}],'ports':[{'port':9090,'protocol':'TCP'}]}]}
run('kubectl', 'apply', '-f', '-', input=yaml.safe_dump(endpoints).encode())
print('Progressive delivery installed. Run make rollouts-check.')
