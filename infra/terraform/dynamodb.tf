# Cinco tablas on-demand (PAY_PER_REQUEST).

resource "aws_dynamodb_table" "words" {
  name         = "parlache-words"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "word_key"

  attribute {
    name = "word_key"
    type = "S"
  }
}

resource "aws_dynamodb_table" "daily" {
  name         = "parlache-daily"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "date"

  attribute {
    name = "date"
    type = "S"
  }
}

resource "aws_dynamodb_table" "players" {
  name         = "parlache-players"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "player_id"

  attribute {
    name = "player_id"
    type = "S"
  }

  attribute {
    name = "gsi_pk"
    type = "S"
  }

  attribute {
    name = "current_streak"
    type = "N"
  }

  global_secondary_index {
    name            = "streak-index"
    hash_key        = "gsi_pk"
    range_key       = "current_streak"
    projection_type = "ALL"
  }
}

resource "aws_dynamodb_table" "attempts" {
  name         = "parlache-attempts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "results" {
  name         = "parlache-results"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "date"
  range_key    = "player_id"

  attribute {
    name = "date"
    type = "S"
  }

  attribute {
    name = "player_id"
    type = "S"
  }

  attribute {
    name = "score_key"
    type = "S"
  }

  global_secondary_index {
    name            = "ranking-index"
    hash_key        = "date"
    range_key       = "score_key"
    projection_type = "ALL"
  }
}
