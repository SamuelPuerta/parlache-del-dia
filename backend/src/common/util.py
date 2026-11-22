"""Utilidades HTTP y de logging para los handlers."""
import json

from common.game import is_valid_player_id


def response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def error(status: int, code: str) -> dict:
    return response(status, {"error": code})


def get_player_id(event: dict) -> str | None:
    """HTTP API (payload v2) entrega las cabeceras en minusculas."""
    headers = event.get("headers") or {}
    value = headers.get("x-player-id")
    return value if is_valid_player_id(value) else None


def short_id(player_id: str) -> str:
    """Solo los primeros 8 caracteres, para no registrar el ID completo."""
    return player_id[:8]


def parse_json_body(event: dict) -> dict | None:
    try:
        data = json.loads(event.get("body") or "")
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None
