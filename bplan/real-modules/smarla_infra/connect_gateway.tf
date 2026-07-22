resource "aws_api_gateway_rest_api" "connect" {
  name = "connect-${var.environment}"
  description = "Connect API Gateway for environment ${var.environment}"
}

resource "aws_api_gateway_resource" "auth" {
  rest_api_id = "${aws_api_gateway_rest_api.connect.id}"
  parent_id = "${aws_api_gateway_rest_api.connect.root_resource_id}"
  path_part = "auth"
}

resource "aws_api_gateway_method" "login" {
  rest_api_id = "${aws_api_gateway_rest_api.connect.id}"
  resource_id = "${aws_api_gateway_resource.auth.id}"
  http_method = "POST"
  authorization = "NONE"
}

# resource "aws_api_gateway_integration" "login_integration" {
#   rest_api_id = "${aws_api_gateway_rest_api.connect.id}"
#   resource_id = "${aws_api_gateway_resource.auth.id}"
#   uri = "${aws_lambda_function.smarla_login_lambda.arn}"
#   http_method = "${aws_api_gateway_method.login.http_method}"
#   integration_http_method = "POST"
#   type = "AWS"
# }

resource "aws_api_gateway_method_response" "login_ok" {
  rest_api_id = "${aws_api_gateway_rest_api.connect.id}"
  resource_id = "${aws_api_gateway_resource.auth.id}"
  http_method = "${aws_api_gateway_method.login.http_method}"
  status_code = "200"
}

resource "aws_api_gateway_integration_response" "login_ok_integration" {
  rest_api_id = "${aws_api_gateway_rest_api.connect.id}"
  resource_id = "${aws_api_gateway_resource.auth.id}"
  http_method = "${aws_api_gateway_method.login.http_method}"
  status_code = "${aws_api_gateway_method_response.login_ok.status_code}"
}

resource "aws_api_gateway_method_response" "login_ko" {
  rest_api_id = "${aws_api_gateway_rest_api.connect.id}"
  resource_id = "${aws_api_gateway_resource.auth.id}"
  http_method = "${aws_api_gateway_method.login.http_method}"
  status_code = "401"
}

resource "aws_api_gateway_integration_response" "login_ko_integration" {
  rest_api_id = "${aws_api_gateway_rest_api.connect.id}"
  resource_id = "${aws_api_gateway_resource.auth.id}"
  http_method = "${aws_api_gateway_method.login.http_method}"
  status_code = "${aws_api_gateway_method_response.login_ko.status_code}"
}
