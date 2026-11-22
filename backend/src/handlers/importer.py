import json
import logging
from urllib.parse import unquote_plus

import boto3

from common import emf, logic
from common.db import get_store

log = logging.getLogger()
log.setLevel(logging.INFO)

_s3 = boto3.client("s3")


def handler(event, context):
    """Evento S3 en imports/*.json. Un archivo invalido se rechaza completo (lanza error)."""
    total = 0
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        raw = _s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        items = json.loads(raw.decode("utf-8"))
        total += logic.import_words(get_store(), items)
        log.info("importadas %s palabras desde %s", len(items), key)
    emf.emit("importer", WordsImported=total)
    return {"imported": total}
