# api_endpoint y sns_topic_arn se añaden en las fases 2 y 5.

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
