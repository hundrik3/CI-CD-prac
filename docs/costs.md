# Cost estimate and approval boundary

No AWS resources have been created. Provisioning requires explicit owner approval and configured temporary AWS authentication.

Illustrative us-east-1 Linux on-demand estimate, without Free Tier, credits or taxes:

| Resource | Approximate charge |
|---|---:|
| EC2 t3.micro | $0.0104/hour (~$7.59 at 730 hours) |
| One public IPv4 | $0.005/hour (~$3.65 at 730 hours) |
| gp3 root volume, 8 GiB | ~$0.64/month |
| One customer-managed KMS key | ~$1/month plus requests |
| S3 state and DynamoDB on-demand lock table | Usage-based; typically small for a short lab |
| VPC, subnet, internet gateway, route table, security groups and IAM roles | No standalone hourly fee |

Baseline: approximately $12–13/month continuously, before variable usage. A short lab costs less, but actual charges depend on lifetime and key/storage retention. T3 surplus CPU credits, outbound transfer, KMS requests and API/storage activity can add charges. No NAT Gateway, load balancer or VPC endpoints are provisioned. These are estimates, not a live AWS Pricing API quote.

Check current [EC2 pricing](https://aws.amazon.com/ec2/pricing/on-demand/), [VPC public IPv4 pricing](https://aws.amazon.com/vpc/pricing/), [EBS pricing](https://aws.amazon.com/ebs/pricing/), [KMS pricing](https://aws.amazon.com/kms/pricing/), [S3 pricing](https://aws.amazon.com/s3/pricing/) and [DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/on-demand/) before approval. Set an account budget alert; alerts are not a spending cap.

Destroy the workload promptly and follow the complete backend cleanup runbook. Versioned S3 objects persist until explicitly deleted. KMS deletion has a seven-day waiting period. Identity federation prerequisites are not provisioned automatically.
