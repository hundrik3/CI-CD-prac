# Design decisions

- **Terraform modules:** separate network and compute concerns with explicit inputs and outputs. AWS provider 5.100.x is locked, Terraform 1.11.4 is the tested runtime.
- **SSM instead of SSH:** no inbound security-group rules or key pairs. The EC2 role has AmazonSSMManagedInstanceCore. Outbound HTTPS permits SSM and operating-system repositories; broad HTTPS egress is a deliberate lab tradeoff. The exact tfsec rule `aws-ec2-no-public-egress-sgr` has a documented inline exception because public SSM IPs change. This is one accepted critical finding, not a claim of zero findings. All other high/critical findings block the pipeline.
- **Public IPv4 instead of NAT:** one public-routed instance reduces costs. A public address is not an ingress permission. Production private workloads should evaluate VPC endpoints and their costs.
- **State:** S3 versioning, customer-managed KMS encryption, TLS-only access, public access block and DynamoDB locking reproduce the original assignment. DynamoDB locking is deprecated in newer Terraform; migrating to S3 lockfiles is a future improvement, not silently mixed with this lab.
- **OIDC:** GitLab ID tokens obtain temporary AWS credentials. No permanent AWS keys, credentials files, state files or binary plans belong in Git.
- **Controlled deployment:** cloud jobs run only on a protected default branch. Apply consumes its pipeline's saved plan; apply and destroy are manual and serialize through one resource group. Configure protected environments and restrict who may run them. An old plan may fail if state changed; rerun the pipeline rather than forcing it.
- **Security gate:** high and critical tfsec findings block delivery; lower findings remain visible and must be considered before production use.
- **Scope:** no application is required by project 26. Hosted GitLab, live AWS creation, SSM connectivity and cleanup require independent live evidence.
- **Compatibility:** OpenTofu compatibility is not claimed without running its checks. The source assignment contains conflicting examples (open SSH and long-lived keys); this implementation uses its stated hardening goals instead.
