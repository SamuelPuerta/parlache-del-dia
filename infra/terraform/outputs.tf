# sns_topic_arn se añade en la fase 5.

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.main.id
}

output "frontend_bucket" {
  value = aws_s3_bucket.frontend.bucket
}

output "admin_bucket" {
  value = aws_s3_bucket.admin.bucket
}

output "api_endpoint" {
  description = "Endpoint directo de API Gateway (el tráfico normal entra por CloudFront en /api/*)."
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "picker_function_name" {
  value = aws_lambda_function.fn["picker"].function_name
}
