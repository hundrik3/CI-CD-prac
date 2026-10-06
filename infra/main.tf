data "aws_ssm_parameter" "ami" {
  count = var.ami_id == null ? 1 : 0
  name  = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}
module "network" {
  source  = "./modules/network"
  project = var.project
  region  = var.region
}
module "compute" {
  source            = "./modules/compute"
  project           = var.project
  subnet_id         = module.network.subnet_id
  security_group_id = module.network.security_group_id
  ami_id            = var.ami_id == null ? data.aws_ssm_parameter.ami[0].value : var.ami_id
  instance_type     = var.instance_type
}
