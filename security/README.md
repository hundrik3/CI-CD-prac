# Supply-chain checks and signed evidence

## Local image checks

After building with make compose-up or make gitops-up:

```sh
make scan
make sbom
```

Trivy checks the real application image for HIGH/CRITICAL vulnerabilities and secrets. There are no vulnerability suppressions or ignore-unfixed flags. A nonzero exit is a failed gate and must be investigated. Scan results depend on the database at execution time; a past pass is not a permanent security guarantee. Syft generates `.local/sbom.spdx.json`. These commands do not sign a registry image.

## GitHub Actions

The application job has contents:read only. It builds and tests, scans and uploads small records with one-day retention. After that succeeds, a separate trusted-main job gets id-token:write and signs the image manifest using GitHub OIDC and Sigstore. Pull requests do not receive the signing job. No permanent private key, registry credential or AWS credential is stored.

The manifest binds source commit, local image ID, Docker archive hash, SPDX SBOM hash and Trivy report hash. The archive is hashed then removed; it is not uploaded. This binds evidence to an image artifact but does not distribute or sign a production registry digest. Records are intentionally small and short lived.

Download the signed-supply-chain-records artifact from a successful application workflow. From that directory:

```sh
cosign verify-blob \
  --bundle manifest.sigstore.json \
  --certificate-identity 'https://github.com/hundrik3/CI-CD-prac/.github/workflows/application.yml@refs/heads/main' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  manifest.json
sha256sum sbom.spdx.json trivy.json
```

Compare those checksums with the signed manifest. Do not trust a bundle solely because it exists: verification must succeed for the expected identity and issuer. The workflow also changes a copy of the manifest and requires verification to reject it. It does not suppress a failing positive-verification command.

A reviewer should inspect the specific run, source commit, scan result and signature result together. Old artifacts expire; successful runner logs and documented outcomes remain evidence of that execution. Live signing outside GitHub requires an appropriate identity and is not simulated with invented credentials.
