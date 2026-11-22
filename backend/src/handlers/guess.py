import logging
import os
from datetime import date, datetime, timezone

from common import emf, logic, util
from common.db import get_store, make_ensure_daily

log = logging.getLogger()
log.setLevel(logging.INFO)

EPOCH = date.fromisoformat(os.environ.get("EPOCH_DATE", "2026-11-25"))


def handler(event, context):
    player_id = util.get_player_id(event)
    if not player_id:
        return util.error(400, "invalid_player")
    payload = util.parse_json_body(event) or {}
    try:
        store = get_store()
        body, metrics = logic.submit_guess(
            store, player_id, payload.get("guess"), datetime.now(timezone.utc),
            make_ensure_daily(store))
        emf.emit("guess", **metrics)
        return util.response(200, body)
    except logic.ApiError as e:
        if e.code == "invalid_guess":
            emf.emit("guess", InvalidGuesses=1)
        return util.error(e.status, e.code)
    except Exception:
        # No se registra el intento ni la palabra secreta.
        log.exception("guess fallo (jugador %s)", util.short_id(player_id))
        return util.error(500, "internal")
