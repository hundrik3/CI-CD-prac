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
| ArgoCD sync and replica drift | Pending Git source push | Source path must exist in the remote revision before this can execute |
| Kubernetes app telemetry | Pending ArgoCD sync | Not inferred from Compose success |
| Git revision promotion and revert | Pending | No successful claim yet |
| Hosted application CI | Pending first push | Local tests do not establish hosted success |
| Keyless signature and tamper rejection | Pending hosted CI | No identity or signing result is invented locally |
| Cleanup | Pending final validation | Cached images are deliberately retained |
| Live AWS / GitLab cloud jobs | Not run | No paid resources, AWS credentials or cloud cost approval |

Local transient records are saved in ignored .local. Durable sanitized results and exact hosted run links will be added after integration validation. Terraform evidence remains in validation.md.
