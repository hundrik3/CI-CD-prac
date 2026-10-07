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
| Hosted application CI | First run failed; corrected run pending | Run 37600367202 failed on an initial absent ArgoCD status; wait helper corrected and revision guard added |
| Keyless signature and tamper rejection | Pending hosted CI | No identity or signing result is invented locally |
| Cleanup | Pending final validation | Cached images are deliberately retained |
| Live AWS / GitLab cloud jobs | Not run | No paid resources, AWS credentials or cloud cost approval |

Local transient records are saved in ignored .local. Durable sanitized results and exact hosted run links will be added after integration validation. Terraform evidence remains in validation.md.

## Verified release exercise

The app served v2 after commit `28e7ad9e03f4b2d5741e91d503944495ec88ab43`, with ArgoCD reporting that revision Synced/Healthy. An ordinary Git revert produced `66ca606` and the app then served v1 with that revision Synced/Healthy. No kubectl set image or imperative version mutation was used to substitute for Git delivery.

## Hosted failure diagnosis

The first application run passed installation, API tests, Compose end-to-end checks, Trivy and SBOM. It failed when a newly created Application did not yet have a status field. The checker now treats missing status as pending, reads one status snapshot per attempt and verifies the requested commit. The original failed run is not counted as a pass; its signing job was skipped.
