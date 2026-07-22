resource "aws_subnet" "private" {
  vpc_id = "${aws_vpc.smarla.id}"
  # count = "${length(split(",", var.azs))}"
  cidr_block = "${split(",", var.private_subnet_cidr)[0]}"
  availability_zone = "${split (",", var.azs)[0]}"

  # tags {
  #   Name = "smarla-private-subnet"
  #   Environment = "${var.environment}"
  # }
}

resource "aws_route_table" "private" {
  vpc_id = "${aws_vpc.smarla.id}"

  # tags {
  #   Name = "private-route-table"
  #   Environment = "${var.environment}"
  # }
}

resource "aws_route" "private_internet" {
  route_table_id = "${aws_route_table.private.id}"
  nat_gateway_id = "${aws_nat_gateway.default.id}"
  destination_cidr_block = "0.0.0.0/0"
}

resource "aws_route_table_association" "private" {
  # count = "${length(split(",",var.azs))}"
  subnet_id = "${aws_subnet.private.id}"
  route_table_id = "${aws_route_table.private.id}"
}
