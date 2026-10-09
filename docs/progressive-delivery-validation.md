# Project 54 validation

Validation date: 2026-10-09. This page reports actual local and hosted outcomes separately. No AWS resources or paid services were used.

## Executed checks

- `make validate`: five API tests and three preserved pipeline tests passed; existing Kubernetes Kustomize rendering, progressive-delivery YAML parsing and both Compose configurations passed.
- `make gitops-check`: the original ArgoCD Application was Synced/Healthy, replica drift healed, and all nine telemetry/HTTP checks passed before enabling the optional rollout lab.
- `make scan`: the changed actual application image passed an unsuppressed Trivy HIGH/CRITICAL vulnerability and secret scan; the JSON report contained zero findings in those categories.
- `make sbom`: the actual application image produced an SPDX SBOM with 78 packages.

The first release exercise successfully promoted v2 and rejected manual/broken candidates, but baseline restoration failed on a transient endpoint error; it is not counted as a fully successful run. The second invocation failed while sampling the shared Service immediately after replica downscale. The controller had progressed correctly, but a short-lived stale endpoint refused a connection. The checker now waits a bounded time for a complete sample after endpoint convergence. It also explicitly promotes the known baseline during reset and removes old evidence at startup.

## Completed local release exercise

The revised `make rollouts-check` completed with exit code 0, including baseline restoration. Permanent [sanitized machine-readable evidence](evidence/progressive-delivery-local.json) contains the actual run timestamp, selector hashes, ReplicaSet counts and AnalysisRun measurement values. The [successful checker output](evidence/progressive-delivery-local-checks.txt) is also retained.

| Scenario | Actual result |
|---|---|
| 20% pause | Stable v1 and candidate v2 observed; shared Service sample: 75 v1, 25 v2 out of 100 |
| Good candidate analysis | Success ratio 1.0 on all three measurements; request counts 212, 260, 309 |
| 60% pause and promotion | Analysis Successful, second explicit promotion completed v2 |
| Manual abort | Candidate replicas reduced to zero; 30 shared-Service requests returned only v2 |
| Broken candidate | Actual `/work` HTTP 500; measured success ratio 0.0, analysis Failed; controller automatically aborted |
| Stable service after automatic abort | Working v2 preserved; candidate replicas zero; 30 shared-Service requests returned only v2 |
| No business traffic | Sample count 0 and ratio 0.0; analysis Failed, rollout aborted |
| Baseline reset | Known v1 restored and Healthy |

Candidate analysis failures are expected safety outcomes and were explicitly checked. The first two incomplete invocations above are not counted as complete successes. NodePort routing is stochastic; the observed 25% sample is not a claim of exact weighted routing.

## Cleanup and regression

`make rollouts-down` removed both optional namespaces and restored the original Prometheus configuration. The original `make gitops-check` then passed again: ArgoCD sync/health, replica drift healing and all nine functional observability checks. This demonstrates that optional-lab teardown preserves the original workflow.

`make gitops-down` followed by `make compose-down` completed successfully. Read-only postchecks confirmed no Kind clusters, zero Compose containers belonging to `ci-cd-prac`, no `portfolio-kind` or project Compose network, and no `.local/kubeconfig`. Cached images/tools remain; no global prune was performed. The original regression check output is retained in [the cleanup evidence](evidence/progressive-delivery-cleanup.txt).

## Hosted CI

The application workflow has been extended to run Project 54 after its existing GitOps checks and to upload the resulting evidence. The first hosted run [37913799484](https://github.com/hundrik3/CI-CD-prac/actions/runs/37913799484) failed before Project 54 executed: the updated runner's Docker Buildx Bake refused reading `/etc/ssl/certs/ca-certificates.crt` outside the project directory. Unit/render checks and cleanup passed; image scanning, GitOps, Rollouts and signing were skipped. This run is not claimed as successful.

The build helper now copies the public system CA bundle into ignored `.local/build-ca.pem` before building and supplies it through the existing BuildKit secret mount. This retains TLS verification and keeps the CA out of image layers, while allowing Bake to read only the project-local file. A local `COMPOSE_BAKE=true make compose-up` completed using the actual Bake backend, followed by all nine `make compose-check` checks and successful targeted cleanup. Hosted revalidation is pending.

## Limits

No exact weighted routing, ingress integration, production SLO, multi-pod canary metrics aggregation, multi-node outage, cloud deployment, GitOps-driven release change or invalid-image recovery is claimed. The exercise rejects a runnable but functionally broken candidate, which directly tests the Prometheus success-ratio gate. The local checker's baseline reset intentionally bypasses analysis for the known v1 template; the v2 promotion does not bypass it.
