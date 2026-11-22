# Un rol por funcion con politica en linea de minimo privilegio (sin "*").
# El rol de la EC2 se crea junto con ec2.tf en la fase 5.

locals {
  tables = {
    words    = aws_dynamodb_table.words.arn
    daily    = aws_dynamodb_table.daily.arn
    players  = aws_dynamodb_table.players.arn
    attempts = aws_dynamodb_table.attempts.arn
    results  = aws_dynamodb_table.results.arn
  }

  picker_arn = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:parlache-picker"

  fn_policies = {
    today = [
      { actions = ["dynamodb:GetItem"], resources = [local.tables.daily, local.tables.attempts, local.tables.words] },
      { actions = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"], resources = [local.tables.players] },
      { actions = ["lambda:InvokeFunction"], resources = [local.picker_arn] },
    ]
    guess = [
      { actions = ["dynamodb:GetItem"], resources = [local.tables.daily, local.tables.words] },
      { actions = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"], resources = [local.tables.attempts, local.tables.players, local.tables.results] },
      { actions = ["lambda:InvokeFunction"], resources = [local.picker_arn] },
    ]
    ranking = [
      { actions = ["dynamodb:Query"], resources = ["${local.tables.results}/index/ranking-index", "${local.tables.players}/index/streak-index"] },
    ]
    picker = [
      { actions = ["dynamodb:Scan", "dynamodb:UpdateItem"], resources = [local.tables.words] },
      { actions = ["dynamodb:PutItem", "dynamodb:GetItem"], resources = [local.tables.daily] },
    ]
    importer = [
      { actions = ["s3:GetObject"], resources = ["${aws_s3_bucket.admin.arn}/imports/*"] },
      { actions = ["dynamodb:BatchWriteItem", "dynamodb:PutItem", "dynamodb:GetItem"], resources = [local.tables.words] },
    ]
  }
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "fn" {
  for_each           = local.functions
  name               = "parlache-${each.key}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "fn" {
  for_each = local.functions

  dynamic "statement" {
    for_each = local.fn_policies[each.key]

    content {
      actions   = statement.value.actions
      resources = statement.value.resources
    }
  }

  # Logs: solo en el log group propio (ya existe, lo crea lambda.tf).
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.fn[each.key].arn}:*"]
  }
}

resource "aws_iam_role_policy" "fn" {
  for_each = local.functions
  name     = "parlache-${each.key}-policy"
  role     = aws_iam_role.fn[each.key].id
  policy   = data.aws_iam_policy_document.fn[each.key].json
}

# ---------- Rol del Scheduler ----------
data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "parlache-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = [local.picker_arn]
  }

  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.scheduler_dlq.arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "parlache-scheduler-policy"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}
