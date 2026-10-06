variable "region" {
  type    = string
  default = "us-east-1"
}
variable "project" {
  type    = string
  default = "project26"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.project))
    error_message = "Use 3-25 lowercase letters, digits or hyphens."
  }
}
variable "instance_type" {
  type    = string
  default = "t3.micro"
  validation {
    condition     = var.instance_type == "t3.micro"
    error_message = "This cost-limited lab supports only t3.micro."
  }
}
variable "ami_id" {
  type    = string
  default = null
}
