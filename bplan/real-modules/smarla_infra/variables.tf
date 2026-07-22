variable "access_key" {}
variable "secret_key" {}
variable "db_name" {}
variable "db_username" {}
variable "db_password" {}


variable "environment" {
  default = "hydrogen"
}

variable "region" {
  default = "eu-west-1"
}

variable "azs" {
  default = "eu-west-1a,eu-west-1b"
}

variable "db_engine_version" {
  default = "9.5.2"
}

variable "db_instance_class" {
  default = "db.t2.medium"
}

variable "vpc_cidr" {
  default = "10.0.0.0/8"
}

variable "private_subnet_cidr" {
  default = "10.0.0.0/16,10.1.0.0/16,10.2.0.0/16"
}