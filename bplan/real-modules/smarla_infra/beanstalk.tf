resource "aws_elastic_beanstalk_application" "application" {
  name = "application-${var.environment}"
  description = "Beanstalk application for environment ${var.environment}"
}

resource "aws_elastic_beanstalk_environment" "environment" {
  name = "${var.environment}"
  application = "${aws_elastic_beanstalk_application.application.name}"
  solution_stack_name = "64bit Amazon Linux 2016.03 v2.1.3 running Node.js"

  # tags {
  #   Environment = "${var.environment}"
  # }
}

