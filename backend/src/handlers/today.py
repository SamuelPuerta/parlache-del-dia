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
    try:
        store = get_store()
        body, created = logic.get_today(
            store, player_id, datetime.now(timezone.utc), EPOCH, make_ensure_daily(store))
        if created:
            emf.emit("today", PlayersCreated=1)
        return util.response(200, body)
    except logic.ApiError as e:
        return util.error(e.status, e.code)
    except Exception:
        log.exception("today fallo (jugador %s)", util.short_id(player_id))
        return util.error(500, "internal")
