"""Prueba de integracion contra DynamoDB simulado (moto).

Se omite si moto no esta instalado: pip install -r backend/requirements-dev.txt
"""
import random
from datetime import date, datetime, timezone

import pytest

pytest.importorskip("moto")
from moto import mock_aws  # noqa: E402

EPOCH = date(2026, 11, 25)
NOW = datetime(2026, 11, 27, 15, 0, tzinfo=timezone.utc)
PID = "123e4567-e89b-42d3-a456-426614174000"


def _create_tables(client):
    def table(name, keys, attrs, gsi=None):
        kw = dict(TableName=name, BillingMode="PAY_PER_REQUEST",
                  KeySchema=[{"AttributeName": k, "KeyType": t} for k, t in keys],
                  AttributeDefinitions=[{"AttributeName": a, "AttributeType": t} for a, t in attrs])
        if gsi:
            kw["GlobalSecondaryIndexes"] = [gsi]
        client.create_table(**kw)

    table("parlache-words", [("word_key", "HASH")], [("word_key", "S")])
    table("parlache-daily", [("date", "HASH")], [("date", "S")])
    table("parlache-attempts", [("pk", "HASH")], [("pk", "S")])
    table("parlache-players", [("player_id", "HASH")],
          [("player_id", "S"), ("gsi_pk", "S"), ("current_streak", "N")],
          {"IndexName": "streak-index", "Projection": {"ProjectionType": "ALL"},
           "KeySchema": [{"AttributeName": "gsi_pk", "KeyType": "HASH"},
                         {"AttributeName": "current_streak", "KeyType": "RANGE"}]})
    table("parlache-results", [("date", "HASH"), ("player_id", "RANGE")],
          [("date", "S"), ("player_id", "S"), ("score_key", "S")],
          {"IndexName": "ranking-index", "Projection": {"ProjectionType": "ALL"},
           "KeySchema": [{"AttributeName": "date", "KeyType": "HASH"},
                         {"AttributeName": "score_key", "KeyType": "RANGE"}]})


def test_flujo_completo_con_dynamodb(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    with mock_aws():
        import boto3

        from common import logic
        from common.db import DynamoStore

        client = boto3.client("dynamodb")
        _create_tables(client)
        store = DynamoStore(client)
        rng = random.Random(3)

        item = {"word": "parce", "display": "parce", "meaning": "Amigo.", "example": "",
                "region": "Antioquia", "source": "X"}
        assert logic.import_words(store, [item, {**item, "word": "arepa", "display": "arepa"}]) == 2

        ensure = lambda d: logic.pick_word(store, d, EPOCH, NOW, rng)[0]  # noqa: E731
        d1, created = logic.pick_word(store, "2026-11-27", EPOCH, NOW, rng)
        d2, created2 = logic.pick_word(store, "2026-11-27", EPOCH, NOW, rng)
        assert created and not created2 and d1 == d2

        body, _ = logic.get_today(store, PID, NOW, EPOCH, ensure, rng)
        assert body["state"]["status"] == "playing"

        wrong = "zzzzz"
        out, _ = logic.submit_guess(store, PID, wrong, NOW, ensure, rng)
        assert out["status"] == "playing" and out["attempts_used"] == 1
        out, _ = logic.submit_guess(store, PID, d1["word_key"], NOW, ensure, rng)
        assert out["status"] == "won" and out["player"]["current_streak"] == 1

        with pytest.raises(logic.ApiError) as err:
            logic.submit_guess(store, PID, wrong, NOW, ensure, rng)
        assert err.value.status == 409

        ranking = logic.get_ranking(store, "daily", NOW)
        assert ranking["entries"][0]["attempts"] == 2
        assert logic.get_ranking(store, "streak", NOW)["entries"][0]["streak"] == 1
