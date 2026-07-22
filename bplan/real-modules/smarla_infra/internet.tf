resource "aws_internet_gateway" "internet" {
  vpc_id = "${aws_vpc.smarla.id}"

  # tags {
  #   Name = "smarla-internet"
  #   Environment = "${var.environment}"
  # }
}
