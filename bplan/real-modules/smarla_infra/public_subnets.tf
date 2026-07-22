resource "aws_subnet" "public" {
  vpc_id = "${aws_vpc.smarla.id}"
  # count = "${length(split(",", var.azs))}"
  cidr_block = "${cidrsubnet(var.vpc_cidr, 8, 0)}"
  availability_zone = "${split(",", var.azs)[0]}"
  # tags {
  #   Name = "smarla-public-subnet"
  #   Environment = "${var.environment}"
  # }
}

resource "aws_route_table" "public" {
  vpc_id = "${aws_vpc.smarla.id}"

  # tags {
  #   Name = "smarl-apublic-routetable"
  #   Environment = "${var.environment}"
  # }
}

resource "aws_route" "public_internet" {
  route_table_id = "${aws_route_table.public.id}"
  gateway_id = "${aws_internet_gateway.internet.id}"
  destination_cidr_block = "0.0.0.0/0"
}

resource "aws_route_table_association" "public" {
  # count = "${length(split(",", var.azs))}"
  subnet_id = "${aws_subnet.public.id}"
  route_table_id = "${aws_route_table.public.id}"
}
