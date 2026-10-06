variable "project" { type = string }
variable "region" { type = string }
resource "aws_vpc" "lab" {
  cidr_block           = "10.26.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = var.project }
}
resource "aws_default_security_group" "closed" {
  vpc_id = aws_vpc.lab.id
}
resource "aws_subnet" "lab" {
  vpc_id                  = aws_vpc.lab.id
  cidr_block              = "10.26.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = false
}
resource "aws_internet_gateway" "lab" { vpc_id = aws_vpc.lab.id }
resource "aws_route_table" "lab" { vpc_id = aws_vpc.lab.id }
resource "aws_route" "internet" {
  route_table_id         = aws_route_table.lab.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.lab.id
}
resource "aws_route_table_association" "lab" {
  subnet_id      = aws_subnet.lab.id
  route_table_id = aws_route_table.lab.id
}
# Lab exception: SSM endpoints have changing public IPs; only TCP 443 is allowed.
# tfsec:ignore:aws-ec2-no-public-egress-sgr
resource "aws_security_group" "ssm" {
  ingress     = []
  name        = "${var.project}-ssm"
  description = "No ingress; HTTPS egress for SSM and package repositories"
  vpc_id      = aws_vpc.lab.id
  egress {
    description = "HTTPS for AWS SSM and operating system updates"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
output "vpc_id" { value = aws_vpc.lab.id }
output "subnet_id" { value = aws_subnet.lab.id }
output "security_group_id" { value = aws_security_group.ssm.id }
