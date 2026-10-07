# Case study: one service across GitOps, observability and supply-chain controls

## Goal

Build a portfolio platform that demonstrates actual delivery and diagnosis without a cloud budget. The existing Terraform project validates IaC but does not exercise a running service. Projects 50, 51 and 53 are combined around one small API to cover that gap.

## Implementation

The API exposes health, bounded work and controlled error routes. It is packaged in a non-root container, deployed in Kind through ArgoCD Core, and emits correlated traces/logs through OpenTelemetry. Prometheus and Grafana show request/error rate and latency. GitHub Actions builds the image, runs functional checks, scans vulnerabilities, generates an SBOM and verifies signed build evidence.

## Problems investigated

1. Source files created under a restrictive umask were unreadable by non-root containers. Explicit COPY modes and readable configuration mounts restored startup without switching the app to root.
2. The managed proxy injected both uppercase and lowercase variables. Requests used the lowercase exclusion list, sending internal OTLP traffic to the proxy. Configuring both internal exclusion lists restored export; external TLS verification stayed enabled.
3. The initial Debian base had HIGH/CRITICAL OS findings. A minimal Alpine base reduced the package surface and passed the same unsuppressed application gate.
4. Nested Kind lacked /dev/kmsg and could not mount overlay snapshots. Node-scoped device recovery and native snapshots enabled Kubernetes. Full ArgoCD then exhausted disk, so Core and a shared Compose backend reduced duplication.
5. An alert check read a stale metric after an app restart. The test now establishes an exact fresh baseline before generating errors, preventing false claims about an increase-based alert.

## Evidence and limits

See platform-validation.md for the final executed outcomes and hosted run links. AWS is unused; registry image promotion, production HA and security scanning of every platform component are not claimed. The Terraform/GitLab lab is preserved and separately documented.

The project demonstrates modular infrastructure, application packaging, Git-driven reconciliation, operational diagnosis, negative testing, telemetry correlation and signed evidence. It includes reproducible failure and cleanup procedures rather than only configuration files.
