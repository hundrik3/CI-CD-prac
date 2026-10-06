mock_provider "aws" {}
run "network_security" {
  command = plan
  module { source = "./modules/network" }
  variables {
    project = "project26"
    region  = "us-east-1"
  }
  assert {
    condition     = length(aws_security_group.ssm.ingress) == 0
    error_message = "No inbound access is permitted."
  }
  assert {
    condition     = alltrue([for rule in aws_security_group.ssm.egress : rule.from_port == 443 && rule.to_port == 443 && rule.protocol == "tcp"])
    error_message = "Only HTTPS egress is permitted."
  }
  assert {
    condition     = aws_subnet.lab.map_public_ip_on_launch == false
    error_message = "Subnet must not assign public IPs by default."
  }
}
