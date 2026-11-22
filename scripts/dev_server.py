#!/usr/bin/env python3
"""Servidor local para jugar sin AWS.

Sirve `frontend/` y atiende /api/* con la misma lógica de las Lambdas (common/logic.py)
sobre un almacén en memoria. Los datos se pierden al reiniciar.

    python3 scripts/dev_server.py            # http://127.0.0.1:8000
    python3 scripts/dev_server.py --port 9000
"""
import argparse
import json
import mimetypes
import os
import sys
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "backend", "src"))
sys.path.insert(0, os.path.join(ROOT, "backend", "tests"))

from common import logic, util  # noqa: E402
from common.game import is_valid_player_id  # noqa: E402
from fakes import FakeStore  # noqa: E402

EPOCH = date.fromisoformat(os.environ.get("EPOCH_DATE", "2026-11-25"))
STORE = FakeStore()


def load_words():
    with open(os.path.join(ROOT, "backend", "data", "words.json"), encoding="utf-8") as f:
        n = logic.import_words(STORE, json.load(f))
    print(f"{n} palabras cargadas")


def ensure_daily(date_iso):
    daily = STORE.get_daily(date_iso)
    if daily:
        return daily
    daily, _ = logic.pick_word(STORE, date_iso, EPOCH, datetime.now(timezone.utc))
    return daily


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if self.path.startswith("/api/"):
            super().log_message(fmt, *args)

    def _send(self, status, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _api(self, method):
        url = urlparse(self.path)
        player = self.headers.get("X-Player-Id")
        now = datetime.now(timezone.utc)
        try:
            if method == "GET" and url.path == "/api/today":
                if not is_valid_player_id(player):
                    return self._send(400, json.dumps({"error": "invalid_player"}))
                body, _ = logic.get_today(STORE, player, now, EPOCH, ensure_daily)
            elif method == "POST" and url.path == "/api/guess":
                if not is_valid_player_id(player):
                    return self._send(400, json.dumps({"error": "invalid_player"}))
                size = int(self.headers.get("Content-Length") or 0)
                payload = util.parse_json_body({"body": self.rfile.read(size).decode("utf-8")}) or {}
                body, _ = logic.submit_guess(STORE, player, payload.get("guess"), now, ensure_daily)
            elif method == "GET" and url.path == "/api/ranking":
                rtype = parse_qs(url.query).get("type", ["daily"])[0]
                body = logic.get_ranking(STORE, rtype, now)
            else:
                return self._send(404, json.dumps({"error": "not_found"}))
            self._send(200, json.dumps(body, ensure_ascii=False))
        except logic.ApiError as e:
            self._send(e.status, json.dumps({"error": e.code}))

    def _static(self):
        path = urlparse(self.path).path
        rel = "index.html" if path == "/" else path.lstrip("/")
        full = os.path.normpath(os.path.join(ROOT, "frontend", rel))
        if not full.startswith(os.path.normpath(os.path.join(ROOT, "frontend"))) or not os.path.isfile(full):
            return self._send(404, "No encontrado", "text/plain; charset=utf-8")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if full.endswith(".js"):
            ctype = "text/javascript"
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_GET(self):
        self._api("GET") if self.path.startswith("/api/") else self._static()

    def do_POST(self):
        self._api("POST")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    load_words()
    print(f"Parlache del día en http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
