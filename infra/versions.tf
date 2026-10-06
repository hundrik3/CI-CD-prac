terraform {
  required_version = ">= 1.11.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.100.0"
    }
  }
  backend "s3" {}
}
provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, ManagedBy = "Terraform" }
  }
}
