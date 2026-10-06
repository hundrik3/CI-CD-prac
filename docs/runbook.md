# Deployment and cleanup runbook

## Prerequisites

Use the existing checkout in the isolated cloud task; do not create a worktree. Install the versions in README. Use your own AWS account and GitLab project. Before provisioning, confirm the budget and authorization. Configure temporary AWS CLI credentials through your supported account/identity mechanism; never paste secrets into chat or Git. Verify `aws sts get-caller-identity` locally without publishing account details.

## Backend bootstrap

Pick a globally unique bucket name. Bootstrap state is local: protect it and retain it securely outside Git; it is needed for backend cleanup.

```sh
terraform -chdir=bootstrap init -lockfile=readonly
terraform -chdir=bootstrap plan -var='state_bucket=YOUR_UNIQUE_BUCKET' -out=backend.tfplan
terraform -chdir=bootstrap apply backend.tfplan
cp infra/backend.hcl.example infra/backend.hcl
# Edit bucket and dynamodb_table in the ignored backend.hcl.
terraform -chdir=infra init -backend-config=backend.hcl -lockfile=readonly
terraform -chdir=infra plan -out=deployment.tfplan
terraform -chdir=infra apply deployment.tfplan
```

The default region is us-east-1. For another region set both the provider variable and backend region; in CI change AWS_REGION and TF_VAR_region together. Default AMI comes from AWS's Amazon Linux 2023 public SSM parameter. `ami_id` can override it for a reviewed pinned AMI.

## GitLab OIDC and CI

Import/mirror this GitHub repository to GitLab without changing its GitHub origin. Protect the default branch. Configure an AWS IAM OIDC provider for your GitLab issuer and audience `sts.amazonaws.com`. Create a deployment role whose trust policy allows `sts:AssumeRoleWithWebIdentity` only for that issuer, audience, and exact subject `project_path:YOUR_GROUP/YOUR_PROJECT:ref_type:branch:ref:main` (adjust the default branch). Do not use wildcard project or branch trust. Review the issuer's official OIDC documentation for self-managed GitLab.

Role permissions must cover this lab's EC2/VPC lifecycle and describe calls, SSM GetParameter for the public AMI, S3 state object read/write and bucket listing, DynamoDB lock operations, KMS access to the state key, and the project-specific IAM role/profile lifecycle and PassRole to EC2. Scope resources where supported; scope PassRole to the project SSM role and EC2 service. Do not grant AdministratorAccess. IAM federation and its permissions are account-specific prerequisites and are not created by this lab's Terraform.

Add protected GitLab variables `AWS_ROLE_ARN`, `TF_STATE_BUCKET`, `TF_LOCK_TABLE`. They are identifiers, not secret credentials. Restrict plan artifacts to maintainers and protect the `aws-lab` environment. Run the protected default-branch pipeline, review the plan, then manually run apply. Do not run cloud jobs from untrusted merge requests. Delete old pipelines/artifacts containing state-derived details according to your retention policy.

## Live readiness checks

After apply, record the EC2 ID from `terraform -chdir=infra output -raw instance_id`. Check EC2 status with `aws ec2 wait instance-status-ok --instance-ids INSTANCE_ID`. Wait for Systems Manager registration and verify `aws ssm describe-instance-information` shows the instance online. Use Session Manager (`aws ssm start-session --target INSTANCE_ID`, requires its CLI plugin) or SSM Run Command to execute `uname -a` and `systemctl is-active amazon-ssm-agent`. Record command status and output only after execution. These steps have **not** been executed for the portfolio evidence.

## Cleanup

Do not run apply and destroy concurrently. In GitLab trigger the manual destroy job, or locally:

```sh
terraform -chdir=infra plan -destroy -out=destroy.tfplan
terraform -chdir=infra apply destroy.tfplan
terraform -chdir=infra state list
```

Confirm the state is empty and verify the EC2 instance is terminated and the VPC removed through AWS describe/list calls. Keep state until those checks pass. Removing workload resources leaves the backend intact. For complete cleanup, download a secure state backup, then explicitly remove every S3 object version and delete marker through the AWS console or a reviewed version-aware procedure. `aws s3 rm --recursive` alone does not remove old versions. The bucket deliberately has `force_destroy=false`.

With the original local bootstrap state, run `terraform -chdir=bootstrap plan -destroy -var='state_bucket=YOUR_UNIQUE_BUCKET' -out=cleanup.tfplan`, review, and apply it. Verify bucket and lock table absence. The KMS key enters a seven-day deletion window; confirm deletion is scheduled and follow up after the window. Remove lab-only OIDC role/provider only if no other project uses them. Check AWS billing and inventory for residual resources. Never remove a shared backend or identity provider.
