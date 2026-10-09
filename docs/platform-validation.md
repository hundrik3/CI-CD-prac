# Platform validation evidence

Prepared on 2026-10-07 in the CI/CD prac environment. Results are updated only after the underlying check executes.

| Check | Current result | Scope |
|---|---|---|
| API tests | Passed: 4 tests | Version/health, bounded input, observed 500s, bounded metric labels |
| Compose end-to-end | Passed | Fresh metric baseline, 150 ms request, 500s, Tempo trace, Loki correlated log, firing Prometheus alert, provisioned Grafana dashboard |
| Application Trivy gate | Passed locally | Alpine image, HIGH/CRITICAL vulnerabilities and secrets; no ignore-unfixed or vulnerability exceptions |
| SPDX SBOM | Generated locally | Syft catalog of the actual image |
| Manifest YAML and Actions syntax | Passed locally | Kustomize render and actionlint |
| Kind control plane | Ready | Managed nested-Docker recovery was required |
| ArgoCD sync and replica drift | Passed locally | Revision 4658841 Synced/Healthy; scale to two was reconciled back to one |
| Kubernetes app telemetry | Passed locally | All nine HTTP/metrics/traces/logs/alert/dashboard checks executed against the Kind app |
| Git revision promotion and revert | Passed locally | 28e7ad9 deployed v2; ordinary revert 66ca606 restored healthy v1 |
| Hosted application CI | Passed | [Run 37601631088](https://github.com/hundrik3/CI-CD-prac/actions/runs/37601631088), source f28bf35; application and attest jobs both successful |
| Keyless signature and tamper rejection | Passed on GitHub | Cosign Verified OK; changed manifest failed with invalid signature in run 37601631088 |
| Cleanup | Passed locally | Both cleanup targets executed; no project containers or Kind cluster remained, dedicated bridge removed |
| Live AWS / GitLab cloud jobs | Not run | No paid resources, AWS credentials or cloud cost approval |

Local transient records are saved in ignored .local. Sanitized local outcomes are committed in evidence/platform-local.json, and actual runner-log excerpts in evidence/hosted-checks.txt. Terraform evidence remains in validation.md.

## Verified release exercise

The app served v2 after commit `28e7ad9e03f4b2d5741e91d503944495ec88ab43`, with ArgoCD reporting that revision Synced/Healthy. An ordinary Git revert produced `66ca606` and the app then served v1 with that revision Synced/Healthy. No kubectl set image or imperative version mutation was used to substitute for Git delivery.

## Hosted failure diagnosis

The first application run passed installation, API tests, Compose end-to-end checks, Trivy and SBOM. It failed when a newly created Application did not yet have a status field. The checker now treats missing status as pending, reads one status snapshot per attempt and verifies the requested commit. The original failed run is not counted as a pass; its signing job was skipped.

## Successful hosted run

[Run 37601631088](https://github.com/hundrik3/CI-CD-prac/actions/runs/37601631088) completed with success for commit `f28bf350518833a901352a8455a60c94ec812bf1`. Actual logs confirmed 4 API tests and 3 pipeline-control tests, both Compose and Kubernetes telemetry checks, Synced/Healthy at the selected source revision, replica self-healing, an unsuppressed Trivy gate, SBOM generation and cleanup. The separate attest job printed `Verified OK` and rejected changed content with `invalid signature`. Signing records use one-day artifact retention; the persistent excerpts retain the outcome without any private key or token.

The preserved [Terraform workflow](https://github.com/hundrik3/CI-CD-prac/actions/runs/37601630955) also succeeded for f28bf35. Superseded release-exercise application runs were cancelled by the configured concurrency policy and are not counted as passes. Documentation-only commits do not rerun the full platform job; runtime and CI input changes do.

## Project 54 extension

The integrated progressive-delivery extension passed locally and on a fresh GitHub runner at runtime source `4904ad4`. See [its validation report](progressive-delivery-validation.md) for measured canary results, expected candidate rejection, cleanup, the initial Bake failure and corrected successful hosted run. The earlier results above retain their original scope and dates.
