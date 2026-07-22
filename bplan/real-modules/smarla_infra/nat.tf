resource "aws_nat_gateway" "default" {
  subnet_id = "${aws_vpc.smarla.id}"

  # tags {
  #   Name = "smarla-nat"
  #   Environment = "${var.environment}"
  # }
}
