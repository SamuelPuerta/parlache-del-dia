import logging
import os
from datetime import date, datetime, timezone

from common import emf, game, logic
from common.db import get_store

log = logging.getLogger()
log.setLevel(logging.INFO)

EPOCH = date.fromisoformat(os.environ.get("EPOCH_DATE", "2026-11-25"))


def handler(event, context):
    """Scheduler (00:00 Bogota) o invocacion directa con {"date": "YYYY-MM-DD"}.

    Los errores se propagan a proposito: asi cuentan como error de la Lambda
    (alarma) y el Scheduler los reintenta o los manda a la DLQ.
    No se registra la palabra elegida.
    """
    now = datetime.now(timezone.utc)
    date_iso = (event or {}).get("date") or game.today_bogota(now).isoformat()
    daily, created = logic.pick_word(get_store(), date_iso, EPOCH, now)
    if created:
        emf.emit("picker", DailyWordSet=1)
    log.info("picker date=%s created=%s puzzle=%s", date_iso, created, daily["puzzle_number"])
    return {"date": date_iso, "created": created}
