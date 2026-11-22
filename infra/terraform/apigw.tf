resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/apigateway/parlache-http"
  retention_in_days = 7
}

resource "aws_apigatewayv2_api" "http" {
  name          = "parlache-http"
  protocol_type = "HTTP"
}

locals {
  routes = {
    today   = "GET /api/today"
    guess   = "POST /api/guess"
    ranking = "GET /api/ranking"
  }
}

resource "aws_apigatewayv2_integration" "fn" {
  for_each               = local.routes
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.fn[each.key].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "r" {
  for_each  = local.routes
  api_id    = aws_apigatewayv2_api.http.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.fn[each.key].id}"
}

resource "aws_lambda_permission" "apigw" {
  for_each      = local.routes
  statement_id  = "AllowApiGw-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fn[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

# Logs de acceso sin IP ni cabeceras del jugador.
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }

  route_settings {
    route_key              = "POST /api/guess"
    throttling_burst_limit = 60
    throttling_rate_limit  = 30
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      latency          = "$context.responseLatency"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  depends_on = [aws_apigatewayv2_route.r]
}
