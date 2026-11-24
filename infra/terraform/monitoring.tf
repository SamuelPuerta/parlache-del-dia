# Fase 5 - Observabilidad: SNS, 5 alarmas, 1 dashboard y 1 Budget (sección 9 del plan).
# Menos de 10 alarmas y menos de 10 métricas personalizadas para quedar en el nivel gratuito.

locals {
  fn_names = { for k, f in aws_lambda_function.fn : k => f.function_name }

  ddb_tables = [
    aws_dynamodb_table.words.name,
    aws_dynamodb_table.daily.name,
    aws_dynamodb_table.players.name,
    aws_dynamodb_table.attempts.name,
    aws_dynamodb_table.results.name,
  ]

  # Métricas de negocio (EMF, namespace ParlacheDelDia, una sola dimensión: Service).
  business_metrics = [
    ["ParlacheDelDia", "GuessesSubmitted", "Service", "guess"],
    ["ParlacheDelDia", "GamesWon", "Service", "guess"],
    ["ParlacheDelDia", "GamesLost", "Service", "guess"],
    ["ParlacheDelDia", "InvalidGuesses", "Service", "guess"],
    ["ParlacheDelDia", "PlayersCreated", "Service", "today"],
    ["ParlacheDelDia", "DailyWordSet", "Service", "picker"],
    ["ParlacheDelDia", "WordsImported", "Service", "importer"],
  ]
}

# ---------- SNS ----------
# Sin cifrado con la llave aws/sns: su política no deja publicar a CloudWatch Alarms.
resource "aws_sns_topic" "alerts" {
  name = "parlache-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ---------- Alarmas ----------
# Todas con treat_missing_data = notBreaching (decisión D5: sin alarmas por ausencia de métrica).

resource "aws_cloudwatch_metric_alarm" "picker_errors" {
  alarm_name          = "parlache-picker-errors"
  alarm_description   = "La Lambda picker falló: puede que hoy no haya palabra del día."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = local.fn_names["picker"] }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "scheduler_dlq" {
  alarm_name          = "parlache-scheduler-dlq"
  alarm_description   = "El Scheduler agotó los reintentos y dejó un mensaje en la DLQ."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = aws_sqs_queue.scheduler_dlq.name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name          = "parlache-api-5xx"
  alarm_description   = "API Gateway devolvió 5 o más errores 5xx en 5 minutos."
  namespace           = "AWS/ApiGateway"
  metric_name         = "5xx"
  dimensions          = { ApiId = aws_apigatewayv2_api.http.id }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "guess_errors" {
  alarm_name          = "parlache-guess-errors"
  alarm_description   = "La Lambda guess acumuló 3 o más errores en 5 minutos."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = local.fn_names["guess"] }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 3
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "guess_latency" {
  alarm_name          = "parlache-guess-latency"
  alarm_description   = "La duración p95 de guess superó 2 s en 2 de 3 periodos."
  namespace           = "AWS/Lambda"
  metric_name         = "Duration"
  dimensions          = { FunctionName = local.fn_names["guess"] }
  extended_statistic  = "p95"
  period              = 300
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  threshold           = 2000
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

locals {
  alarm_arns = [
    aws_cloudwatch_metric_alarm.picker_errors.arn,
    aws_cloudwatch_metric_alarm.scheduler_dlq.arn,
    aws_cloudwatch_metric_alarm.api_5xx.arn,
    aws_cloudwatch_metric_alarm.guess_errors.arn,
    aws_cloudwatch_metric_alarm.guess_latency.arn,
  ]
}

# ---------- Dashboard ----------
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "parlache"

  dashboard_body = jsonencode({
    widgets = [
      # Fila 1: API
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6
        properties = {
          title   = "API: peticiones y errores"
          region  = var.region
          view    = "timeSeries"
          stat    = "Sum"
          period  = 300
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiId", aws_apigatewayv2_api.http.id],
            [".", "4xx", ".", "."],
            [".", "5xx", ".", "."],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6
        properties = {
          title   = "API: latencia (ms)"
          region  = var.region
          view    = "timeSeries"
          period  = 300
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiId", aws_apigatewayv2_api.http.id, { stat = "p50", label = "Latency p50" }],
            ["...", { stat = "p95", label = "Latency p95" }],
            [".", "IntegrationLatency", ".", ".", { stat = "p95", label = "IntegrationLatency p95" }],
          ]
        }
      },
      # Fila 2: Lambda por función
      {
        type = "metric", x = 0, y = 6, width = 6, height = 6
        properties = {
          title   = "Lambda: invocaciones"
          region  = var.region
          view    = "timeSeries"
          stat    = "Sum"
          period  = 300
          metrics = [for k, n in local.fn_names : ["AWS/Lambda", "Invocations", "FunctionName", n]]
        }
      },
      {
        type = "metric", x = 6, y = 6, width = 6, height = 6
        properties = {
          title   = "Lambda: errores"
          region  = var.region
          view    = "timeSeries"
          stat    = "Sum"
          period  = 300
          metrics = [for k, n in local.fn_names : ["AWS/Lambda", "Errors", "FunctionName", n]]
        }
      },
      {
        type = "metric", x = 12, y = 6, width = 6, height = 6
        properties = {
          title   = "Lambda: duración p95 (ms)"
          region  = var.region
          view    = "timeSeries"
          stat    = "p95"
          period  = 300
          metrics = [for k, n in local.fn_names : ["AWS/Lambda", "Duration", "FunctionName", n]]
        }
      },
      {
        type = "metric", x = 18, y = 6, width = 6, height = 6
        properties = {
          title   = "Lambda: throttles"
          region  = var.region
          view    = "timeSeries"
          stat    = "Sum"
          period  = 300
          metrics = [for k, n in local.fn_names : ["AWS/Lambda", "Throttles", "FunctionName", n]]
        }
      },
      # Fila 3: DynamoDB
      {
        type = "metric", x = 0, y = 12, width = 12, height = 6
        properties = {
          title   = "DynamoDB: lecturas consumidas (RCU)"
          region  = var.region
          view    = "timeSeries"
          stat    = "Sum"
          period  = 300
          metrics = [for t in local.ddb_tables : ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", t]]
        }
      },
      {
        type = "metric", x = 12, y = 12, width = 12, height = 6
        properties = {
          title   = "DynamoDB: escrituras consumidas (WCU)"
          region  = var.region
          view    = "timeSeries"
          stat    = "Sum"
          period  = 300
          metrics = [for t in local.ddb_tables : ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", t]]
        }
      },
      # Fila 4: negocio (EMF) y CloudFront
      {
        type = "metric", x = 0, y = 18, width = 12, height = 6
        properties = {
          title   = "Negocio: partidas e intentos (EMF)"
          region  = var.region
          view    = "timeSeries"
          stat    = "Sum"
          period  = 300
          metrics = local.business_metrics
        }
      },
      {
        type = "metric", x = 12, y = 18, width = 12, height = 6
        properties = {
          title  = "CloudFront: peticiones y tasa de error"
          region = "us-east-1"
          view   = "timeSeries"
          period = 300
          metrics = [
            ["AWS/CloudFront", "Requests", "DistributionId", aws_cloudfront_distribution.main.id, "Region", "Global", { stat = "Sum" }],
            [".", "TotalErrorRate", ".", ".", ".", ".", { stat = "Average", yAxis = "right" }],
          ]
        }
      },
      # Fila 5: estado de las alarmas
      {
        type = "alarm", x = 0, y = 24, width = 24, height = 3
        properties = {
          title  = "Estado de las alarmas"
          alarms = local.alarm_arns
        }
      },
    ]
  })
}

# ---------- Budget ----------
# El pronóstico necesita unos días de consumo para dispararse; por eso hay también aviso sobre gasto real.
resource "aws_budgets_budget" "monthly" {
  name         = "parlache-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}
