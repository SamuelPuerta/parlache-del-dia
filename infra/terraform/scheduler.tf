# Elige la palabra del dia a las 00:00 de Colombia (el Scheduler maneja la zona horaria).

resource "aws_sqs_queue" "scheduler_dlq" {
  name                      = "parlache-scheduler-dlq"
  message_retention_seconds = 1209600
}

resource "aws_scheduler_schedule" "daily_word" {
  name                         = "parlache-daily-word"
  schedule_expression          = "cron(0 0 * * ? *)"
  schedule_expression_timezone = "America/Bogota"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.fn["picker"].arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ source = "scheduler" })

    retry_policy {
      maximum_retry_attempts       = 3
      maximum_event_age_in_seconds = 3600
    }

    dead_letter_config {
      arn = aws_sqs_queue.scheduler_dlq.arn
    }
  }
}
