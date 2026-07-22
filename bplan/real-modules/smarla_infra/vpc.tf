resource "aws_vpc" "smarla" {
  cidr_block = "${var.vpc_cidr}"
  enable_dns_hostnames  = "true"

  # tags {
  #   Name = "smarla-vpc"
  #   Environment = "${var.environment}"
  # }
}
