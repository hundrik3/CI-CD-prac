# Case study: validating infrastructure delivery without a cloud budget

## Problem and scope

[Project 26](https://github.com/DevCloudNinjas/DevOps-Projects/tree/main/project-26-terraform-gitlab-cicd) asks for AWS provisioning with Terraform and GitLab CI/CD. The portfolio goal is to demonstrate infrastructure design, deployment controls and repeatable verification without spending money on cloud resources.

The repository therefore contains the AWS implementation and GitLab delivery pipeline, plus a credential-free GitHub Actions workflow that executes the checks on standard GitHub-hosted Linux runners. This public repository does not need AWS credentials, an AWS account or a paid runner for that workflow. If it is made private, runner allowances and billing must be reviewed first.

## Implementation

The network module creates a dedicated VPC, subnet, internet route and security group. The compute module describes one cost-limited EC2 instance managed through SSM, with no inbound access, encrypted storage and IMDSv2. A separate bootstrap configuration describes versioned, encrypted S3 state and DynamoDB locking.

The GitLab pipeline validates and scans before planning. Its cloud jobs are restricted to a protected default branch and use short-lived OIDC credentials. Manual apply consumes the saved plan. Manual destroy and serialized cloud jobs control lifecycle changes. Account-specific federation and actual deployment remain outside the verified scope.

GitHub Actions proves the parts that can run without AWS: initialization with `-backend=false`, provider-backed configuration validation, five mock-plan runs, three tests of GitLab delivery controls, shell parsing and a high/critical security gate. Mock providers replace AWS operations; there are no cloud deployment commands in this workflow.

## Engineering choices

- Split network and compute concerns into reusable modules.
- Keep state, binary plans and credentials out of Git; commit provider lockfiles.
- Prefer SSM and temporary credentials to open SSH and permanent access keys.
- Pin action revisions, tool versions and provider versions; verify downloaded tool checksums.
- Give the GitHub workflow read-only repository permissions and no OIDC permission.
- Keep an explicit exception for HTTPS egress to changing public SSM endpoints. Report medium findings rather than calling the lab production hardened.

## Evidence and limits

[Validation evidence](validation.md) distinguishes local results, the hosted GitHub run and checks that were not performed. The [Actions page](https://github.com/hundrik3/CI-CD-prac/actions/workflows/validate.yml) exposes actual runner logs and commit-specific outcomes; a badge is not evidence of AWS deployment.

Local verification has passed both Terraform configurations, five mock test runs and three pipeline tests. No EC2 instance or state backend was created. SSM connectivity, AWS permissions, real lifecycle cleanup, hosted GitLab execution and OpenTofu compatibility remain unverified. These limits are deliberate and visible.

## What this demonstrates

Infrastructure as code, modular design, CI security controls, temporary-credential design, dependency reproducibility, negative testing, cost awareness and honest reporting of evidence. A live cloud deployment would be a separate, budget-approved exercise, not a prerequisite for using this repository as a portfolio sample.
