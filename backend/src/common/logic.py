"""Logica de negocio de las funciones.

Recibe un `store` (ver common/db.py) y no conoce boto3, asi que se prueba
con un almacen en memoria. Ninguna funcion devuelve ni registra la palabra secreta
mientras la partida sigue en juego.
"""
import random
from datetime import date, datetime, timezone

from common import game
from common.words import validate_words

PLAYING, WON, LOST = "playing", "won", "lost"
ATTEMPT_TTL_SECONDS = 48 * 3600
RANKING_SIZE = 20


class ApiError(Exception):
    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status = status
        self.code = code


def iso_utc(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_date(value: str) -> date:
    """Falla con ValueError si no es YYYY-MM-DD."""
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f"fecha invalida: {value!r}")
    return date.fromisoformat(value)


# ---------- jugador ----------

def ensure_player(store, player_id: str, now: datetime, rng=None):
    player = store.get_player(player_id)
    if player:
        return player, False
    created, player = store.create_player(player_id, game.make_alias(rng), iso_utc(now))
    return player, created


def _public_player(player: dict, today: date) -> dict:
    return {
        "alias": player["alias"],
        "current_streak": game.effective_streak(
            player.get("last_win_date"), player["current_streak"], today
        ),
        "best_streak": player.get("best_streak", 0),
        "wins": player.get("wins", 0),
        "played": player.get("played", 0),
    }


def _reveal(word: dict) -> dict:
    return {
        "word": word["display"],
        "meaning": word["meaning"],
        "example": word.get("example", ""),
        "region": word["region"],
    }


# ---------- GET /api/today ----------

def get_today(store, player_id: str, now: datetime, epoch: date, ensure_daily, rng=None):
    today = game.today_bogota(now)
    today_iso = today.isoformat()
    player, created = ensure_player(store, player_id, now, rng)

    daily = ensure_daily(today_iso)
    if not daily:
        raise ApiError(500, "internal")

    attempt = store.get_attempt(player_id, today_iso)
    status = attempt["status"] if attempt else PLAYING
    guesses = list(attempt["guesses"]) if attempt else []
    reveal = None
    if status != PLAYING:
        reveal = _reveal(store.get_word(daily["word_key"]))

    body = {
        "puzzle_number": daily.get("puzzle_number", game.puzzle_number(today, epoch)),
        "date": today_iso,
        "word_length": game.WORD_LENGTH,
        "max_attempts": game.MAX_ATTEMPTS,
        "seconds_to_next": game.seconds_to_next_midnight(now),
        "player": _public_player(player, today),
        "state": {"status": status, "guesses": guesses, "reveal": reveal},
    }
    return body, created


# ---------- POST /api/guess ----------

def submit_guess(store, player_id: str, raw_guess, now: datetime, ensure_daily, rng=None):
    """Devuelve (cuerpo, metricas). Lanza ApiError ante errores del cliente."""
    guess = game.clean_guess(raw_guess)
    if guess is None:
        raise ApiError(400, "invalid_guess")

    today = game.today_bogota(now)
    today_iso = today.isoformat()
    player, _ = ensure_player(store, player_id, now, rng)

    daily = ensure_daily(today_iso)
    if not daily:
        raise ApiError(500, "internal")
    secret = daily["word_key"]

    attempt = store.get_attempt(player_id, today_iso)
    prev_n = attempt["n_attempts"] if attempt else 0
    if attempt and attempt["status"] != PLAYING:
        raise ApiError(409, "game_over")
    if prev_n >= game.MAX_ATTEMPTS:
        raise ApiError(409, "game_over")

    result = game.score(guess, secret)
    n = prev_n + 1
    if all(c == "correct" for c in result):
        status = WON
    elif n >= game.MAX_ATTEMPTS:
        status = LOST
    else:
        status = PLAYING

    entry = {"guess": guess, "result": result}
    now_iso = iso_utc(now)
    ttl = int(now.timestamp()) + ATTEMPT_TTL_SECONDS
    metrics = {"GuessesSubmitted": 1}

    if status == PLAYING:
        ok = store.save_progress(player_id, today_iso, entry, prev_n, now_iso, ttl)
        player_out = {
            "current_streak": game.effective_streak(
                player.get("last_win_date"), player["current_streak"], today
            ),
            "best_streak": player.get("best_streak", 0),
        }
        reveal = None
    else:
        if status == WON:
            streak = game.next_streak(player.get("last_win_date"), player["current_streak"], today)
            metrics["GamesWon"] = 1
        else:
            streak = 0
            metrics["GamesLost"] = 1
        best = max(player.get("best_streak", 0), streak)
        ok = store.finish_game(
            player_id=player_id, date_iso=today_iso, entry=entry, prev_n=prev_n,
            status=status, now_iso=now_iso, ttl=ttl, current_streak=streak,
            best_streak=best, alias=player["alias"],
        )
        player_out = {"current_streak": streak, "best_streak": best}
        reveal = _reveal(store.get_word(secret)) if ok else None

    if not ok:
        raise ApiError(409, "conflict")

    body = {
        "result": result,
        "attempts_used": n,
        "status": status,
        "reveal": reveal,
        "player": player_out,
    }
    return body, metrics


# ---------- GET /api/ranking ----------

def get_ranking(store, rtype: str, now: datetime):
    today = game.today_bogota(now)
    if rtype == "daily":
        rows = store.ranking_daily(today.isoformat(), RANKING_SIZE)
        entries = [
            {"rank": i + 1, "alias": r["alias"], "attempts": r["attempts"],
             "finished_at": r["finished_at"]}
            for i, r in enumerate(rows)
        ]
        return {"type": "daily", "date": today.isoformat(), "entries": entries}
    if rtype == "streak":
        rows = store.ranking_streak(50)
        live = []
        for r in rows:
            s = game.effective_streak(r.get("last_win_date"), r["current_streak"], today)
            if s > 0:
                live.append((s, r["alias"]))
        live.sort(key=lambda t: -t[0])
        entries = [{"rank": i + 1, "alias": a, "streak": s}
                   for i, (s, a) in enumerate(live[:RANKING_SIZE])]
        return {"type": "streak", "entries": entries}
    raise ApiError(400, "invalid_type")


# ---------- picker ----------

def pick_word(store, date_iso: str, epoch: date, now: datetime, rng=None):
    """Elige y guarda la palabra del dia. Idempotente. Devuelve (daily, creado)."""
    day = parse_date(date_iso)
    existing = store.get_daily(date_iso)
    if existing:
        return existing, False

    rng = rng or random
    words = store.scan_words()
    if not words:
        raise RuntimeError("no_words")
    candidates = [w for w in words if not w.get("used_on")]
    if not candidates:
        store.clear_used_on([w["word_key"] for w in words])
        candidates = words
    choice = rng.choice(candidates)

    created = store.create_daily(
        date_iso, choice["word_key"], game.puzzle_number(day, epoch), iso_utc(now)
    )
    if not created:  # otro picker se adelanto
        return store.get_daily(date_iso), False
    return store.get_daily(date_iso), True


# ---------- importer ----------

def import_words(store, items) -> int:
    errors = validate_words(items)
    if errors:
        raise ValueError("words.json invalido: " + "; ".join(errors[:5]))
    return store.put_words(items)
