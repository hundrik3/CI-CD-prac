terraform {
  required_version = ">= 1.11.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.100.0"
    }
  }
}
variable "region" {
  type    = string
  default = "us-east-1"
}
variable "state_bucket" { type = string }
provider "aws" { region = var.region }
resource "aws_s3_bucket" "state" {
  bucket        = var.state_bucket
  force_destroy = false
}
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.state.arn
    }
  }
}
resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_policy" "tls" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Sid = "DenyInsecureTransport", Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } } }]
  })
}
resource "aws_dynamodb_table" "lock" {
  name         = "${var.state_bucket}-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.state.arn
  }
  attribute {
    name = "LockID"
    type = "S"
  }
}
output "bucket" { value = aws_s3_bucket.state.id }
output "lock_table" { value = aws_dynamodb_table.lock.name }

resource "aws_kms_key" "state" {
  description             = "Project26 state and lock encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 7
}
