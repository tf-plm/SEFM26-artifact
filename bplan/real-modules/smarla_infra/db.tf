resource "aws_db_subnet_group" "default" {
  name = "smarla-sg-${var.environment}"
  description = "Subnet for the ${var.environment} RDS"
  subnet_ids = ["${aws_subnet.private.id}", "${aws_subnet.private.id}"]
  # tags {
  #   Name = "subnet-group-rds_elephant-${var.environment}"
  # }
}

resource "aws_db_instance" "default" {
  allocated_storage    = 5
  engine               = "postgres"
  engine_version       = "${var.db_engine_version}"
  instance_class       = "${var.db_instance_class}"
  # name                 = "${var.db_name}"
  username             = "${var.db_username}"
  password             = "${var.db_password}"
  db_subnet_group_name = "${aws_db_subnet_group.default.name}"
  multi_az = true
  publicly_accessible = false
}
