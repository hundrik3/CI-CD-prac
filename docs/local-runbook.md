# Local setup, verification and cleanup

## Prerequisites and installation

Use Linux amd64 with Docker, Docker Compose, Python 3.12, curl and Make. Reserve the cluster name `portfolio` and Compose project `ci-cd-prac` for this repository; do not run cleanup against an unrelated cluster with that name. Standard Linux hosts should have at least 6 GiB free RAM and 12–15 GiB free disk; nested VFS/native environments may need 30 GiB or more. Do not create a Git worktree in an already isolated task.

From the checkout root:

```sh
make tools
make validate
```

Tools are installed into `.local/bin` and the Python venv into `.local/venv`. `.local` contains kubeconfig and generated artifacts and must never be committed. Downloads preserve TLS checks and are verified against official SHA256 manifests. Versions: Kind 0.27.0, Kubernetes/kubectl 1.32.2, ArgoCD Core 3.5.4, Trivy 0.75.0, Syft 1.54.1 and Cosign 3.1.3. These are tested lab versions, not a promise of future security support.

## Standalone observability

```sh
make compose-up
make compose-check
```

The smoke test waits for a fresh counter baseline, sends valid and invalid inputs, generates a 150 ms request and HTTP 500s, then verifies the resulting Prometheus metric, Tempo trace, correlated Loki log, firing alert and provisioned Grafana dashboard. Success writes `.local/compose-evidence.json` and prints each executed check.

Use local requests or open local tools on your own machine: app on port 8080, Grafana on 3000, Prometheus on 9090, Tempo on 3200 and Loki on 3100. All published ports bind 127.0.0.1. Grafana is anonymous Viewer; dashboard editing and administration are not exposed. Intentional /error requests are expected 500 responses, not a failed health check.

```sh
docker compose logs --tail=100 app otel-collector
make compose-down
```

## GitOps mode

Stop standalone mode first; both modes share the telemetry ports.

```sh
make compose-down
make gitops-up
make gitops-check
```

The bootstrap creates only the dedicated Kind cluster, loads the local image, installs ArgoCD Core and starts the Compose backend with `compose.gitops.yaml`. It creates a runtime collector Endpoints object and applies the restricted AppProject/Application. Wait for Git sync and deployment health. The app is available on loopback port 8081.

`make gitops-check` scales the app to two replicas, waits for ArgoCD to restore one, and reruns the observability checks against the Kubernetes app. It writes `.local/gitops-evidence.json` and `.local/kubernetes-evidence.json` only after successful checks.

```sh
.local/bin/kubectl --kubeconfig .local/kubeconfig -n argocd get applications
.local/bin/kubectl --kubeconfig .local/kubeconfig -n portfolio get pods,services
.local/bin/kubectl --kubeconfig .local/kubeconfig -n portfolio logs deployment/portfolio-api
```

Fork users must edit both repoURL and sourceRepos in `platform/argocd/application.yaml`; no GitHub token is needed for a public repository. To pin a test to a reachable commit, set `GITOPS_REVISION=FULL_SHA make gitops-up`.

## Release and recovery exercise

APP_VERSION is a manifest input. Commit a change from v1 to v2, push it, request an ArgoCD hard refresh, and wait for deployment rollout. Confirm `/` reports v2. Revert that commit normally (no reset or force push), refresh, and confirm v1. ArgoCD automated sync works with Git revert; an imperative rollback alone is overwritten by automated synchronization. Image upgrades additionally require building/loading their tag first.

## Troubleshooting

- Permission denied reading mounts: configs must be readable by the non-root service UIDs. Dockerfile COPY explicitly sets app file modes.
- Export returns a proxy denial: ensure both NO_PROXY and no_proxy include internal service names. Do not disable TLS verification or bypass policy for Internet requests.
- ArgoCD reports missing path: ensure the commit containing deploy/overlays/local is pushed and the repository/ref are correct.
- Collector IP changed: rerun gitops-up to rediscover runtime Endpoints. A recreated collector can change the bridge address.
- Missing /dev/kmsg or nested overlayfs errors: managed bootstrap handles the dedicated node; normal host troubleshooting should follow Kind documentation.
- No space left: inspect disk and only your lab resources. Prefer Core and the shared Compose backend. Do not globally prune Docker or remove unrelated user images.
- Alert not firing after restart: wait for a fresh scrape baseline before generating new errors; stale counters can otherwise invalidate increase-based checks.

## Complete cleanup

```sh
make gitops-down
make compose-down
docker ps --filter label=com.docker.compose.project=ci-cd-prac
.local/bin/kind get clusters
```

Only this project's Compose containers/volumes, the named Kind cluster and its dedicated bridge are removed. Cached images and tools may remain for fast rebuilds. Delete `.local` when you no longer need credentials or records; do not remove a live kubeconfig before stopping the cluster. No AWS resource exists to delete in this workflow; optional Terraform cleanup is documented separately in runbook.md.
