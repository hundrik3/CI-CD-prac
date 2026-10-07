# Architecture and design decisions

## Connected data paths

The same API image supports two modes. Standalone mode runs the API with all observability services in Compose. GitOps mode runs the API in a dedicated Kind cluster, with ArgoCD Core following `deploy/overlays/local`, while Compose hosts the telemetry backend.

In GitOps mode the collector joins the `portfolio-kind` Docker bridge. Kubernetes Service `otel-collector` routes to a runtime Endpoints object populated from that container's bridge address. The collector scrapes the app at `portfolio-control-plane:30080`, and exports scraped metrics on port 8889. Prometheus scrapes that exporter. The API uses OTLP HTTP for traces and logs; Collector exports to Tempo and Loki. Grafana provisions all three data sources and a dashboard with request rate, error rate and p95 latency.

## Delivery model

A non-root, digest-pinned Python/Alpine image contains pinned Python dependencies and a single Gunicorn worker with four threads. One worker deliberately keeps Prometheus counters consistent without a multiprocess registry. `/work` allows only 0–2000 ms delay and bounded route labels avoid URL-driven metric cardinality. `/error` returns an intentional HTTP 500 for incident exercises.

Kind receives the locally built image through `kind load docker-image`; imagePullPolicy is Never. ArgoCD delivers Kubernetes configuration from Git, performs automatic sync/pruning and corrects replica drift. Image distribution is a bootstrap step, not a claimed registry promotion pipeline. Changing image tags requires building/loading the new tag before committing the manifest change.

ArgoCD Core is sufficient for controller-driven reconciliation and inspection through kubectl. It avoids UI, Dex and unused controllers on a small local machine. The AppProject restricts the repository and destination namespace. The GitHub runner pins the Application to its source commit so it tests that revision, while an interactive lab follows main.

## Runtime and security boundaries

App pods have no service-account token, use non-root UID 10001, drop Linux capabilities, prohibit privilege escalation, have a read-only root filesystem and explicit CPU/memory limits. The app uses writable ephemeral /tmp. Lab endpoints are loopback-only; Grafana anonymous access is read-only. Collector-to-backend traffic is plain HTTP within a local Docker network. No public ingress or cloud resources are configured.

Telemetry is ephemeral and is removed on cleanup. There is no persistent storage, network-policy enforcement, authentication for telemetry endpoints or production HA. Full platform images are pinned by version but have not received the same vulnerability gate as the application image; production hardening requires independent review and upgrade policy.

For managed Docker-in-Docker, the bootstrap uses the provided proxy and CA, native containerd snapshots and restores a missing /dev/kmsg device only inside the dedicated Kind node. It does not restart the host Docker daemon or change its storage driver. Normal Linux hosts keep the default Kind snapshotter. The custom IPv4 Docker network is an experimental Kind option, retained to avoid nested-environment IPv6 limitations.

## Supply-chain record

The scanner checks HIGH/CRITICAL vulnerabilities and secrets without ignore-unfixed or vulnerability exceptions. Syft catalogs the image as SPDX JSON. A custom image manifest binds the source commit, image config ID, exported image archive SHA256, SBOM SHA256 and scan report SHA256. A separate trusted-main GitHub job signs that file with short-lived Sigstore credentials and verifies the exact workflow identity. This is signed build evidence, not a signed registry image or a certified SLSA provenance claim.
