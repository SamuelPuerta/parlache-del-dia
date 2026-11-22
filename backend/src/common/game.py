"""Reglas del juego: funciones puras, solo biblioteca estandar."""
import random
import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta, timezone

WORD_LENGTH = 5
MAX_ATTEMPTS = 6

BOGOTA = timezone(timedelta(hours=-5))  # Colombia no tiene horario de verano

PLAYER_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
GUESS_RE = re.compile(r"^[a-zñ]{5}$")

ALIAS_FOODS = [
    "Arepa", "Patacón", "Buñuelo", "Sancocho", "Ajiaco", "Lulo", "Arequipe",
    "Obleas", "Mazamorra", "Changua", "Guarapo", "Bandeja", "Empanada",
    "Aguapanela", "Chontaduro", "Tamal", "Fritanga", "Chicharrón", "Mondongo",
    "Cuajada", "Natilla", "Hogao", "Carimañola", "Almojábana", "Pandebono",
    "Pandeyuca", "Lechona", "Cholado", "Salpicón", "Chicha", "Masato",
    "Champús", "Brevas", "Bocadillo", "Avena", "Frijoles", "Sudado",
    "Calentado", "Morcilla", "Guanábana",
]


def normalize(s: str) -> str:
    """Minusculas y sin tildes, conservando la ñ."""
    s = s.strip().lower().replace("ñ", "\u0001")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("\u0001", "ñ")


def is_valid_player_id(value) -> bool:
    return isinstance(value, str) and PLAYER_ID_RE.match(value) is not None


def clean_guess(raw) -> str | None:
    """Devuelve el intento normalizado, o None si no son 5 letras validas."""
    if not isinstance(raw, str):
        return None
    g = normalize(raw)
    return g if GUESS_RE.match(g) else None


def score(guess: str, secret: str) -> list[str]:
    """Colores por letra, manejando letras repetidas."""
    result = ["absent"] * len(secret)
    remaining: Counter = Counter()
    for i, (g, s) in enumerate(zip(guess, secret)):
        if g == s:
            result[i] = "correct"
        else:
            remaining[s] += 1
    for i, g in enumerate(guess):
        if result[i] == "correct":
            continue
        if remaining[g] > 0:
            result[i] = "present"
            remaining[g] -= 1
    return result


def today_bogota(now: datetime | None = None) -> date:
    return (now or datetime.now(BOGOTA)).astimezone(BOGOTA).date()


def seconds_to_next_midnight(now: datetime | None = None) -> int:
    now = (now or datetime.now(BOGOTA)).astimezone(BOGOTA)
    nxt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((nxt - now).total_seconds())


def puzzle_number(today: date, epoch: date) -> int:
    return (today - epoch).days + 1


def next_streak(last_win_date: str | None, current: int, today: date) -> int:
    if last_win_date == (today - timedelta(days=1)).isoformat():
        return current + 1
    return 1


def effective_streak(last_win_date: str | None, current: int, today: date) -> int:
    alive = {today.isoformat(), (today - timedelta(days=1)).isoformat()}
    return current if last_win_date in alive else 0


def make_alias(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"{r.choice(ALIAS_FOODS)}-{r.randint(100, 999)}"
