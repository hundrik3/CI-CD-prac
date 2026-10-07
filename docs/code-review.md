# Code review

Review date: 2026-10-07. Scope: application, Dockerfile, dependency locks, Compose connectivity, Kubernetes/ArgoCD configuration, bootstrap/cleanup helpers, GitHub workflows and signed evidence. This is a source review backed by the documented tests, not an independent security audit.

## Corrections made before readiness

- Explicit application COPY modes and readable configuration mounts prevent restrictive-umask failures without switching containers to root.
- Request inputs are bounded; metrics use route templates and a single unmatched label rather than attacker-controlled paths. Unit tests exercise invalid inputs and label cardinality.
- One threaded worker keeps metric state coherent. Gunicorn's administrative control socket is disabled, and the app runs with a read-only root filesystem and writable temporary storage.
- Internal telemetry routes set both proxy exclusion variants. External downloads retain TLS verification and upstream checksum validation.
- The scanner is an unsuppressed HIGH/CRITICAL and secret gate; a vulnerable Debian base was replaced and the resulting actual Alpine image rescanned.
- Runtime collector endpoints are discovered from the dedicated Docker network, not hardcoded to an environment-specific IP in Git.
- CI signs only after the read-only application job passes. Signing permissions are restricted to a separate trusted-main job. Verification checks the exact issuer and workflow identity, and altered content must fail verification.
- Manifest generation refuses dirty source trees, preventing a signed record from falsely attributing uncommitted source to HEAD.
- Cleanup names only this project's resources and does not run global Docker pruning. Kubeconfig and generated records are ignored by Git.
- Fresh Applications can have no status until the first controller reconciliation. The checker now treats that as pending and additionally verifies the requested Git revision.
- End-to-end metrics checks wait for a fresh baseline, so an old scrape cannot masquerade as a successful new error exercise.

## Accepted lab limitations

- The Kubernetes and third-party observability versions are tested lab pins, not a fully audited production stack. The image vulnerability gate covers the application, not every service image.
- The custom Kind network is experimental. Managed nested Docker requires node-scoped recovery and more disk than normal Linux.
- Telemetry endpoints have no authentication within the local bridge, and Grafana permits anonymous viewing on loopback. There is no HA or durable storage.
- GitOps manages Kubernetes configuration; local image loading and runtime collector endpoint discovery are bootstrap exceptions. There is no registry admission/signature policy or automatic production image promotion.
- Signed manifests bind the local build artifact and its reports. They are not OCI registry signatures or a claim of SLSA certification.
- A successful scan is dated evidence, not a guarantee against future vulnerability database findings.

Live AWS and GitLab cloud jobs remain outside the verified workflow. Terraform's pre-existing documented security exception and medium findings remain visible in validation.md.
