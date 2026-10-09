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
- Manifest generation refuses dirty source trees, preventing a signed record from falsely attributing uncommitted source to HEAD. The refusal was exercised locally; hosted signing verified the clean source record and rejected tampering.
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

## Project 54 extension review (2026-10-09)

- The optional lab uses its own namespace, selector and NodePorts. It does not change the ArgoCD-managed Deployment or reuse its service selectors.
- Bootstrap checks the dedicated Kind context; controller installation uses a pinned release manifest and verifies its SHA256. The checker and optional teardown also refuse an unexpected context.
- The candidate remains non-root with a read-only filesystem, dropped capabilities, no service-account token, resource limits and health probes. Deliberate business failure is opt-in through an environment flag and does not weaken readiness to hide the failure.
- Analysis is scoped to candidate business requests. A minimum request volume prevents absent metrics or zero traffic from becoming a successful release. Real measurement results are captured, and the failed success-ratio gate is explicitly asserted.
- The first exercise exposed that restoring the v1 template starts another rollout with pauses. Baseline cleanup now explicitly fully promotes the known v1 template; the actual v2 release still passes every analysis and pause. The completed revised checker is the authoritative reproducibility check.
- Service transitions can briefly have no ready endpoint. The checker retries transport availability while waiting, including full shared-Service samples after replica downscale, without converting failed metrics or failed assertions into passes.
- Abort restores traffic but leaves the failed desired template. The exercise restores the exact known-good template, verifies candidate replica removal and tests the shared Service after both kinds of abort.
- Old evidence is deleted at the beginning of a new check, so a failed invocation cannot leave an earlier successful record at the expected output path.

The updated GitHub runner enabled Buildx Bake filesystem checks and rejected a CA secret outside the project directory. Build targets now prepare a public system CA bundle under ignored `.local` and still mount it as a BuildKit secret; TLS and image-layer isolation remain intact.

Accepted limits: replica-based weights are approximate; one-candidate Service scraping is sufficient for the inline 20% analysis but not a production multi-pod metrics design. Counters cover an isolated fresh candidate, not a rolling-window SLO. Releases use explicit local template mutations rather than GitOps image promotion. No weighted ingress, production authentication, multi-node availability or production readiness is claimed. The optional namespace teardown leaves cluster-scoped CRDs/RBAC; complete Kind teardown removes them.
