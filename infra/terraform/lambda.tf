data "archive_file" "backend" {
  type        = "zip"
  source_dir  = "${path.module}/../../backend/src"
  output_path = "${path.module}/build/backend.zip"
}

locals {
  functions = {
    today    = { handler = "handlers.today.handler", timeout = 5, memory = 256 }
    guess    = { handler = "handlers.guess.handler", timeout = 10, memory = 256 }
    ranking  = { handler = "handlers.ranking.handler", timeout = 5, memory = 256 }
    picker   = { handler = "handlers.picker.handler", timeout = 15, memory = 256 }
    importer = { handler = "handlers.importer.handler", timeout = 30, memory = 256 }
  }

  # El nombre del picker se escribe a mano para no crear un ciclo (today/guess/picker comparten entorno).
  common_env = {
    TABLE_WORDS          = aws_dynamodb_table.words.name
    TABLE_DAILY          = aws_dynamodb_table.daily.name
    TABLE_PLAYERS        = aws_dynamodb_table.players.name
    TABLE_ATTEMPTS       = aws_dynamodb_table.attempts.name
    TABLE_RESULTS        = aws_dynamodb_table.results.name
    PICKER_FUNCTION_NAME = "parlache-picker"
    MAX_ATTEMPTS         = "6"
    WORD_LENGTH          = "5"
    EPOCH_DATE           = var.epoch_date
  }
}

resource "aws_cloudwatch_log_group" "fn" {
  for_each          = local.functions
  name              = "/aws/lambda/parlache-${each.key}"
  retention_in_days = 7
}

resource "aws_lambda_function" "fn" {
  for_each         = local.functions
  function_name    = "parlache-${each.key}"
  role             = aws_iam_role.fn[each.key].arn
  runtime          = "python3.12"
  architectures    = ["arm64"]
  handler          = each.value.handler
  timeout          = each.value.timeout
  memory_size      = each.value.memory
  filename         = data.archive_file.backend.output_path
  source_code_hash = data.archive_file.backend.output_base64sha256

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.fn]
}

# ---------- S3 (bucket admin) -> importer ----------
resource "aws_lambda_permission" "s3_importer" {
  statement_id   = "AllowS3Invoke"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.fn["importer"].function_name
  principal      = "s3.amazonaws.com"
  source_arn     = aws_s3_bucket.admin.arn
  source_account = data.aws_caller_identity.current.account_id
}

resource "aws_s3_bucket_notification" "admin" {
  bucket = aws_s3_bucket.admin.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.fn["importer"].arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "imports/"
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.s3_importer]
}
