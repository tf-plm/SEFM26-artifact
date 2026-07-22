resource "aws_route53_zone" "pesama_main" {
  name = "pesama.org"

  # tags {
  #   Tier = "root"
  #   Environment = "${var.environment}"
  # }
}

resource "aws_route53_record" "pesama_main" {
  zone_id = "${aws_route53_zone.smarla_main.id}"
  name = "pesama.org"
  type = "CNAME"
  ttl = "3600"
  records = ["${aws_elastic_beanstalk_environment.environment.cname}"]
}

resource "aws_route53_record" "pesama_www" {
  zone_id = "${aws_route53_zone.pesama_main.id}"
  name = "www.pesama.org"
  type = "CNAME"
  ttl = "3600"
  records = ["${aws_route53_record.pesama_main.name}"]
}
