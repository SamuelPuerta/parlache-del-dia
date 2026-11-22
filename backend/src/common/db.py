"""Almacen DynamoDB (boto3). La logica vive en common/logic.py."""
import json
import os
import time
from decimal import Decimal
from functools import lru_cache

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError

_ser = TypeSerializer()
_de = TypeDeserializer()
CONFLICT_CODES = {"ConditionalCheckFailed", "TransactionConflict"}


def _to_db(d: dict) -> dict:
    return {k: _ser.serialize(v) for k, v in d.items()}


def _plain(v):
    if isinstance(v, Decimal):
        return int(v)
    if isinstance(v, list):
        return [_plain(x) for x in v]
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    return v


def _from_db(item: dict) -> dict:
    return {k: _plain(_de.deserialize(v)) for k, v in item.items()}


def _code(e: ClientError) -> str:
    return e.response.get("Error", {}).get("Code", "")


def _cancelled_by_conflict(e: ClientError) -> bool:
    if _code(e) != "TransactionCanceledException":
        return False
    return any(r.get("Code") in CONFLICT_CODES for r in e.response.get("CancellationReasons", []))


class DynamoStore:
    def __init__(self, client=None):
        self.c = client or boto3.client("dynamodb")
        env = os.environ.get
        self.t_words = env("TABLE_WORDS", "parlache-words")
        self.t_daily = env("TABLE_DAILY", "parlache-daily")
        self.t_players = env("TABLE_PLAYERS", "parlache-players")
        self.t_attempts = env("TABLE_ATTEMPTS", "parlache-attempts")
        self.t_results = env("TABLE_RESULTS", "parlache-results")

    # ---- lecturas ----
    def _get(self, table: str, key: dict):
        r = self.c.get_item(TableName=table, Key=_to_db(key), ConsistentRead=True)
        item = r.get("Item")
        return _from_db(item) if item else None

    def get_daily(self, date_iso):
        return self._get(self.t_daily, {"date": date_iso})

    def get_word(self, word_key):
        return self._get(self.t_words, {"word_key": word_key})

    def get_player(self, player_id):
        return self._get(self.t_players, {"player_id": player_id})

    def get_attempt(self, player_id, date_iso):
        return self._get(self.t_attempts, {"pk": f"{player_id}#{date_iso}"})

    def scan_words(self):
        kwargs = {"TableName": self.t_words, "ProjectionExpression": "word_key, used_on"}
        items = []
        while True:
            r = self.c.scan(**kwargs)
            items += [_from_db(i) for i in r.get("Items", [])]
            if not r.get("LastEvaluatedKey"):
                return items
            kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]

    # ---- picker ----
    def create_daily(self, date_iso, word_key, puzzle_number, created_at) -> bool:
        try:
            self.c.transact_write_items(TransactItems=[
                {"Put": {
                    "TableName": self.t_daily,
                    "Item": _to_db({"date": date_iso, "word_key": word_key,
                                    "puzzle_number": puzzle_number, "created_at": created_at}),
                    "ConditionExpression": "attribute_not_exists(#d)",
                    "ExpressionAttributeNames": {"#d": "date"},
                }},
                {"Update": {
                    "TableName": self.t_words,
                    "Key": _to_db({"word_key": word_key}),
                    "UpdateExpression": "SET used_on = :d",
                    "ExpressionAttributeValues": _to_db({":d": date_iso}),
                }},
            ])
            return True
        except ClientError as e:
            if _cancelled_by_conflict(e):
                return False
            raise

    def clear_used_on(self, word_keys):
        for k in word_keys:
            self.c.update_item(
                TableName=self.t_words, Key=_to_db({"word_key": k}),
                UpdateExpression="REMOVE used_on",
            )

    # ---- jugador ----
    def create_player(self, player_id, alias, created_at):
        item = {"player_id": player_id, "alias": alias, "current_streak": 0, "best_streak": 0,
                "wins": 0, "played": 0, "gsi_pk": "ALL", "created_at": created_at}
        try:
            self.c.put_item(
                TableName=self.t_players, Item=_to_db(item),
                ConditionExpression="attribute_not_exists(player_id)",
            )
            return True, item
        except ClientError as e:
            if _code(e) == "ConditionalCheckFailedException":
                return False, self.get_player(player_id)
            raise

    # ---- intentos ----
    def _attempt_update(self, player_id, date_iso, entry, prev_n, status, now_iso, ttl):
        finished = status != "playing"
        expr = ("SET player_id = :p, #d = :d, "
                "guesses = list_append(if_not_exists(guesses, :empty), :new), "
                "n_attempts = :n, #s = :st, started_at = if_not_exists(started_at, :now), "
                "#ttl = :ttl")
        values = {":p": player_id, ":d": date_iso, ":empty": [], ":new": [entry],
                  ":n": prev_n + 1, ":st": status, ":now": now_iso, ":ttl": ttl,
                  ":prev": prev_n, ":playing": "playing"}
        if finished:
            expr += ", finished_at = :now"
        return {
            "TableName": self.t_attempts,
            "Key": _to_db({"pk": f"{player_id}#{date_iso}"}),
            "UpdateExpression": expr,
            "ConditionExpression": "attribute_not_exists(pk) OR (n_attempts = :prev AND #s = :playing)",
            "ExpressionAttributeNames": {"#d": "date", "#s": "status", "#ttl": "ttl"},
            "ExpressionAttributeValues": _to_db(values),
        }

    def save_progress(self, player_id, date_iso, entry, prev_n, now_iso, ttl) -> bool:
        try:
            self.c.update_item(**self._attempt_update(
                player_id, date_iso, entry, prev_n, "playing", now_iso, ttl))
            return True
        except ClientError as e:
            if _code(e) == "ConditionalCheckFailedException":
                return False
            raise

    def finish_game(self, *, player_id, date_iso, entry, prev_n, status, now_iso, ttl,
                    current_streak, best_streak, alias) -> bool:
        won = status == "won"
        if won:
            expr = ("SET played = played + :one, wins = wins + :one, "
                    "current_streak = :cs, best_streak = :bs, last_win_date = :today")
            values = {":one": 1, ":cs": current_streak, ":bs": best_streak, ":today": date_iso}
        else:
            expr = "SET played = played + :one, current_streak = :zero"
            values = {":one": 1, ":zero": 0, ":today": date_iso}
        items = [
            {"Update": self._attempt_update(
                player_id, date_iso, entry, prev_n, status, now_iso, ttl)},
            {"Update": {
                "TableName": self.t_players,
                "Key": _to_db({"player_id": player_id}),
                "UpdateExpression": expr,
                "ConditionExpression": "attribute_not_exists(last_win_date) OR last_win_date <> :today",
                "ExpressionAttributeValues": _to_db(values),
            }},
        ]
        if won:
            n = prev_n + 1
            items.append({"Put": {
                "TableName": self.t_results,
                "Item": _to_db({"date": date_iso, "player_id": player_id, "alias": alias,
                                "attempts": n, "finished_at": now_iso,
                                "score_key": f"{n:02d}#{now_iso}"}),
            }})
        try:
            self.c.transact_write_items(TransactItems=items)
            return True
        except ClientError as e:
            if _cancelled_by_conflict(e):
                return False
            raise

    # ---- ranking ----
    def ranking_daily(self, date_iso, limit):
        r = self.c.query(
            TableName=self.t_results, IndexName="ranking-index",
            KeyConditionExpression="#d = :d",
            ExpressionAttributeNames={"#d": "date"},
            ExpressionAttributeValues=_to_db({":d": date_iso}),
            ScanIndexForward=True, Limit=limit,
        )
        return [_from_db(i) for i in r.get("Items", [])]

    def ranking_streak(self, limit):
        r = self.c.query(
            TableName=self.t_players, IndexName="streak-index",
            KeyConditionExpression="gsi_pk = :g",
            ExpressionAttributeValues=_to_db({":g": "ALL"}),
            ScanIndexForward=False, Limit=limit,
        )
        return [_from_db(i) for i in r.get("Items", [])]

    # ---- importer ----
    def put_words(self, items) -> int:
        requests = []
        for it in items:
            rec = {"word_key": it["word"], "display": it["display"], "meaning": it["meaning"],
                   "example": it.get("example", ""), "region": it["region"], "source": it["source"]}
            existing = self.get_word(it["word"])
            if existing and existing.get("used_on"):
                rec["used_on"] = existing["used_on"]
            requests.append({"PutRequest": {"Item": _to_db(rec)}})
        for i in range(0, len(requests), 25):
            self._batch_write(requests[i:i + 25])
        return len(requests)

    def _batch_write(self, chunk):
        pending = {self.t_words: chunk}
        for attempt in range(6):
            r = self.c.batch_write_item(RequestItems=pending)
            pending = r.get("UnprocessedItems") or {}
            if not pending:
                return
            time.sleep(0.2 * 2 ** attempt)
        raise RuntimeError("batch_write_unprocessed")


@lru_cache(maxsize=1)
def get_store() -> DynamoStore:
    return DynamoStore()


def make_ensure_daily(store):
    """Devuelve la palabra del dia; si no existe, invoca a `picker` de forma sincrona."""
    lam = boto3.client("lambda")

    def ensure(date_iso: str):
        daily = store.get_daily(date_iso)
        if daily:
            return daily
        resp = lam.invoke(
            FunctionName=os.environ.get("PICKER_FUNCTION_NAME", "parlache-picker"),
            InvocationType="RequestResponse",
            Payload=json.dumps({"date": date_iso}).encode(),
        )
        resp["Payload"].read()
        if resp.get("FunctionError"):
            raise RuntimeError("picker_failed")
        return store.get_daily(date_iso)

    return ensure
