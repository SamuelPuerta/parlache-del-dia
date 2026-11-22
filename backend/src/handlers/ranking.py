import logging
from datetime import datetime, timezone

from common import logic, util
from common.db import get_store

log = logging.getLogger()
log.setLevel(logging.INFO)


def handler(event, context):
    params = event.get("queryStringParameters") or {}
    try:
        body = logic.get_ranking(get_store(), params.get("type", "daily"), datetime.now(timezone.utc))
        return util.response(200, body)
    except logic.ApiError as e:
        return util.error(e.status, e.code)
    except Exception:
        log.exception("ranking fallo")
        return util.error(500, "internal")
