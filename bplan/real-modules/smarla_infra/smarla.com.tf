resource "aws_route53_zone" "smarla_main" {
  name = "smarla.com"

  # tags {
  #   Tier = "root"
  # }
}

resource "aws_route53_zone" "smarla_connect" {
  name = "connect.smarla.com"

  # tags {
  #   Tier = "intranet"
  #   Component = "connect"
  #   Access = "admin"
  #   Environment = "${var.environment}"
  # }
}

resource "aws_route53_record" "smarla_main-eb" {
  zone_id = "${aws_route53_zone.smarla_main.id}"
  name = "smarla.com"
  type = "CNAME"
  ttl = "3600"
  records = ["${aws_elastic_beanstalk_environment.environment.cname}"]
}

resource "aws_route53_record" "smarla_www-eb" {
  zone_id = "${aws_route53_zone.smarla_main.id}"
  name = "www.smarla.com"
  type = "CNAME"
  ttl = "3600"
  records = ["${aws_route53_record.smarla_main-eb.name}"]
}

# TODO MX Records

resource "aws_route53_record" "smarla_connect-ns" {
  zone_id = "${aws_route53_zone.smarla_main.id}"
  name = "connect.smarla.com"
  type = "NS"
  ttl = 60
  records = [
    "${aws_route53_zone.smarla_connect.name_servers.0}",
    "${aws_route53_zone.smarla_connect.name_servers.1}",
    "${aws_route53_zone.smarla_connect.name_servers.2}",
    "${aws_route53_zone.smarla_connect.name_servers.3}"
  ]
}

//resource "aws_route53_record" "smarla_connect-gateway" {
//  zone_id = "${aws_route53_zone.smarla_main.id}"
//  name = "connect.smarla.com"
//  type = "A"
//
//  alias {
//    name = "TODO-ELB-alias"
//    zone_id = "TODO Zone-id"
//    evaluate_target_health = true
//  }
//}
