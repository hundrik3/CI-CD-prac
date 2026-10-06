mock_provider "aws" {}
run "compute_security" {
  command = plan
  module { source = "./modules/compute" }
  variables {
    project           = "project26"
    subnet_id         = "subnet-123"
    security_group_id = "sg-123"
    ami_id            = "ami-0123456789abcdef0"
    instance_type     = "t3.micro"
  }
  assert {
    condition     = aws_instance.lab.metadata_options[0].http_tokens == "required"
    error_message = "IMDSv2 must be required."
  }
  assert {
    condition     = aws_instance.lab.root_block_device[0].encrypted && aws_instance.lab.root_block_device[0].volume_size == 8
    error_message = "Root disk must be encrypted and cost limited."
  }
}
