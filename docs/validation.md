# Validation evidence

Executed in the CI/CD prac cloud environment on 2026-10-06. These results describe local execution, not deployment to AWS or a hosted GitLab runner.

| Check | Result | Evidence / scope |
|---|---|---|
| Terraform 1.11.4 and tfsec 1.28.14 installation | Passed | Official TLS downloads checked against upstream SHA256 manifests |
| AWS CLI installation | Passed | `aws --version`: aws-cli/1.38.38; no cloud API calls |
| Repeatable setup script | Passed | Official artifacts verified, venv created, both directories initialized; AWS CLI added and independently verified |
| Provider initialization | Passed | AWS 5.100.0 installed with HashiCorp signature; lockfiles committed |
| Terraform format | Passed | `terraform fmt -check -recursive`, exit 0 |
| Terraform validate | Passed | Both infra and bootstrap, exit 0 |
| Terraform mock tests | Passed | 5 runs passed, 0 failed: network ingress/egress, disk encryption and IMDSv2, root plan, invalid name, expensive instance rejection |
| Pipeline structure tests | Passed | 3 Python unittest tests; manual gates, saved-plan dependency, protected branch and OIDC audience |
| GitHub Actions definition | Passed locally | actionlint 1.7.7, exit 0; official action revisions confirmed |
| GitHub hosted CI | Pending first push | Results will be linked after the runner completes; no success claimed yet |
| Shell syntax | Passed | Both shell scripts parsed with `sh -n` |
| tfsec HIGH/CRITICAL gate | Passed with accepted exception | Both directories exit 0; one documented public HTTPS egress exception |
| Full tfsec scan | Findings remain | Infra: 1 medium (VPC flow logs); bootstrap: 2 medium (S3 access logging, DynamoDB PITR). Full scans exit 1, not counted as passing |
| AWS create / readiness / destroy | Not run | No AWS credentials configured and no cost approval; no resources created |
| GitLab hosted CI and OIDC exchange | Not run | Requires a GitLab project and account-specific AWS federation |
| OpenTofu | Not run | Compatibility is not claimed |

## Diagnosed failures

The cloud execution sandbox initially blocked access to the configured proxy and local Terraform provider sockets. Approved execution through the same proxy and with local socket access resolved those failures; TLS verification remained enabled.

Initial mock assertions attempted to inspect computed fields during plan. Tests were corrected to assert explicit configuration and known security settings. Initial tfsec findings for state encryption were resolved by adding a rotating customer-managed KMS key and explicit DynamoDB encryption. The public HTTPS egress finding remains an explicit accepted lab exception, not a remediated finding.

Medium findings are retained visibly to avoid adding logging/storage services to this small lab without cost approval. Production deployment should add VPC flow logs and S3 access auditing. DynamoDB contains ephemeral lock records; PITR is less valuable for that table than for application data. This project is a lab, not a production security certification.

## Free GitHub Actions verification

The public repository runs `.github/workflows/validate.yml` on standard Ubuntu runners. It uses read-only repository permissions, no AWS/OIDC credentials and no deployment commands. Its installer supports a custom `TOOLING_ROOT` rather than requiring `/workspace`, and has been exercised locally in a separate temporary tool directory.

The hosted result must be read from the specific GitHub run, not inferred from local tests. GitLab hosting and live AWS checks remain unrun.
