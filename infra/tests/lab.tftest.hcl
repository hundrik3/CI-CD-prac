mock_provider "aws" {}

run "secure_lab" {
  command = plan
  variables {
    ami_id = "ami-0123456789abcdef0"
  }

}
run "reject_expensive_instance" {
  command = plan
  variables {
    ami_id        = "ami-0123456789abcdef0"
    instance_type = "m5.24xlarge"
  }
  expect_failures = [var.instance_type]
}
run "reject_invalid_name" {
  command = plan
  variables {
    ami_id  = "ami-0123456789abcdef0"
    project = "Invalid name!"
  }
  expect_failures = [var.project]
}
