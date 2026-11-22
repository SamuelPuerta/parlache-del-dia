import json
import random
from datetime import date, datetime, timedelta, timezone

from common import logic
from fakes import FakeStore

EPOCH = date(2026, 11, 25)
NOW = datetime(2026, 11, 27, 15, 0, tzinfo=timezone.utc)  # 10:00 en Bogota
A = "123e4567-e89b-42d3-a456-426614174000"
B = "223e4567-e89b-42d3-a456-426614174001"
WORDS = ("parce", "arepa", "guaro", "tombo", "bacan", "chepa", "paila")


def make_env():
    store = FakeStore()
    store.seed_words(WORDS)
    rng = random.Random(7)
    ensure = lambda d: logic.pick_word(store, d, EPOCH, NOW, rng)[0]  # noqa: E731
    return store, ensure, rng


def api_error(fn):
    try:
        fn()
    except logic.ApiError as e:
        return e
    raise AssertionError("se esperaba ApiError")


def day(n):
    return NOW + timedelta(days=n)


def secret_of(store, now):
    return store.daily[logic.game.today_bogota(now).isoformat()]["word_key"]


def guess(store, ensure, rng, pid, text, now=NOW):
    return logic.submit_guess(store, pid, text, now, ensure, rng)


def test_today_crea_jugador_y_no_filtra_la_palabra():
    store, ensure, rng = make_env()
    body, created = logic.get_today(store, A, NOW, EPOCH, ensure, rng)
    assert created is True
    assert body["date"] == "2026-11-27" and body["puzzle_number"] == 3
    assert body["state"] == {"status": "playing", "guesses": [], "reveal": None}
    assert body["player"]["current_streak"] == 0
    assert secret_of(store, NOW) not in json.dumps(body)
    _, created2 = logic.get_today(store, A, NOW, EPOCH, ensure, rng)
    assert created2 is False


def test_primer_intento_crea_attempts_y_no_revela():
    store, ensure, rng = make_env()
    body, m = guess(store, ensure, rng, A, "zzzzz")
    assert body["status"] == "playing" and body["attempts_used"] == 1
    assert body["reveal"] is None and m == {"GuessesSubmitted": 1}
    att = store.attempts[f"{A}#2026-11-27"]
    assert att["n_attempts"] == 1 and att["guesses"][0]["guess"] == "zzzzz"
    assert att["ttl"] > int(NOW.timestamp())


def test_intento_invalido():
    store, ensure, rng = make_env()
    for bad in ("abc", "abcdef", "ab1de", None, 123):
        e = api_error(lambda: guess(store, ensure, rng, A, bad))
        assert (e.status, e.code) == (400, "invalid_guess")


def test_intento_normaliza_tildes_y_mayusculas():
    store = FakeStore()
    store.seed_words(["bacan"])  # unica palabra posible
    rng = random.Random(1)
    ensure = lambda d: logic.pick_word(store, d, EPOCH, NOW, rng)[0]  # noqa: E731
    body, _ = guess(store, ensure, rng, A, "Bacán")
    assert body["status"] == "won" and body["result"] == ["correct"] * 5


def test_ganar_incrementa_racha_y_escribe_results():
    store, ensure, rng = make_env()
    logic.get_today(store, A, NOW, EPOCH, ensure, rng)
    guess(store, ensure, rng, A, "zzzzz")
    body, m = guess(store, ensure, rng, A, secret_of(store, NOW))
    assert body["status"] == "won" and body["attempts_used"] == 2
    assert body["reveal"]["word"] == secret_of(store, NOW)
    assert body["player"] == {"current_streak": 1, "best_streak": 1}
    assert m == {"GuessesSubmitted": 1, "GamesWon": 1}
    assert store.results[("2026-11-27", A)]["score_key"].startswith("02#")
    assert store.players[A]["wins"] == 1 and store.players[A]["played"] == 1


def test_perder_en_el_sexto_intento_reinicia_racha():
    store, ensure, rng = make_env()
    logic.get_today(store, A, NOW, EPOCH, ensure, rng)
    store.players[A].update(current_streak=3, best_streak=3, last_win_date="2026-11-26")
    for i in range(5):
        body, _ = guess(store, ensure, rng, A, "zzzzz")
        assert body["status"] == "playing"
    body, m = guess(store, ensure, rng, A, "zzzzz")
    assert body["status"] == "lost" and body["attempts_used"] == 6
    assert body["reveal"] is not None and m["GamesLost"] == 1
    assert body["player"] == {"current_streak": 0, "best_streak": 3}
    assert store.players[A]["current_streak"] == 0 and store.players[A]["played"] == 1
    assert ("2026-11-27", A) not in store.results


def test_intento_tras_terminar_da_409():
    store, ensure, rng = make_env()
    guess(store, ensure, rng, A, secret_of_after_pick(store, ensure))
    e = api_error(lambda: guess(store, ensure, rng, A, "zzzzz"))
    assert (e.status, e.code) == (409, "game_over")


def secret_of_after_pick(store, ensure):
    return ensure("2026-11-27")["word_key"]


def test_conflicto_de_concurrencia_da_409():
    store, ensure, rng = make_env()
    store.save_progress = lambda *a, **k: False
    e = api_error(lambda: guess(store, ensure, rng, A, "zzzzz"))
    assert (e.status, e.code) == (409, "conflict")


def test_today_tras_terminar_incluye_reveal():
    store, ensure, rng = make_env()
    guess(store, ensure, rng, A, secret_of_after_pick(store, ensure))
    body, _ = logic.get_today(store, A, NOW, EPOCH, ensure, rng)
    assert body["state"]["status"] == "won"
    assert body["state"]["reveal"]["meaning"] == "m"
    assert len(body["state"]["guesses"]) == 1


def play_win(store, rng, pid, now):
    """Juega el dia de `now` acertando a la primera."""
    ensure = lambda d: logic.pick_word(store, d, EPOCH, now, rng)[0]  # noqa: E731
    iso = logic.game.today_bogota(now).isoformat()
    secret = ensure(iso)["word_key"]
    return logic.submit_guess(store, pid, secret, now, ensure, rng)[0]


def test_racha_consecutiva_y_rota_por_salto():
    store, _, rng = make_env()
    assert play_win(store, rng, A, NOW)["player"] == {"current_streak": 1, "best_streak": 1}
    assert play_win(store, rng, A, day(1))["player"] == {"current_streak": 2, "best_streak": 2}
    # se salta el dia 3 (29 de nov) y vuelve el 30: la racha reinicia
    assert play_win(store, rng, A, day(3))["player"] == {"current_streak": 1, "best_streak": 2}
    assert store.players[A]["wins"] == 3


def test_ranking_diario_ordena_por_intentos_y_hora():
    store, ensure, rng = make_env()
    secret = secret_of_after_pick(store, ensure)
    guess(store, ensure, rng, A, "zzzzz")
    guess(store, ensure, rng, A, "zzzzz")
    guess(store, ensure, rng, A, secret)           # A gana en 3
    guess(store, ensure, rng, B, "zzzzz")
    guess(store, ensure, rng, B, secret)           # B gana en 2
    r = logic.get_ranking(store, "daily", NOW)
    assert [e["rank"] for e in r["entries"]] == [1, 2]
    assert [e["attempts"] for e in r["entries"]] == [2, 3]
    assert "player_id" not in json.dumps(r)


def test_ranking_rachas_descarta_rachas_vencidas():
    store, ensure, rng = make_env()
    for pid, streak, last in ((A, 5, "2026-11-26"), (B, 9, "2026-11-20")):
        logic.get_today(store, pid, NOW, EPOCH, ensure, rng)
        store.players[pid].update(current_streak=streak, last_win_date=last)
    r = logic.get_ranking(store, "streak", NOW)
    assert [e["streak"] for e in r["entries"]] == [5]
    assert "player_id" not in json.dumps(r)


def test_ranking_tipo_invalido():
    store, _, _ = make_env()
    assert api_error(lambda: logic.get_ranking(store, "otro", NOW)).status == 400


# ---------- picker ----------

def test_picker_es_idempotente():
    store, _, rng = make_env()
    d1, created1 = logic.pick_word(store, "2026-11-27", EPOCH, NOW, rng)
    d2, created2 = logic.pick_word(store, "2026-11-27", EPOCH, NOW, rng)
    assert created1 is True and created2 is False
    assert d1["word_key"] == d2["word_key"] and d1["puzzle_number"] == 3
    assert store.words[d1["word_key"]]["used_on"] == "2026-11-27"


def test_picker_no_repite_hasta_agotar_y_luego_reinicia():
    store, _, rng = make_env()
    chosen = []
    for i in range(len(WORDS)):
        d = (date(2026, 12, 1) + timedelta(days=i)).isoformat()
        chosen.append(logic.pick_word(store, d, EPOCH, NOW, rng)[0]["word_key"])
    assert sorted(chosen) == sorted(WORDS)
    logic.pick_word(store, "2026-12-20", EPOCH, NOW, rng)
    assert sum(1 for w in store.words.values() if w.get("used_on")) == 1


def test_picker_sin_palabras_y_fecha_invalida():
    store = FakeStore()
    for fn in (lambda: logic.pick_word(store, "2026-11-27", EPOCH, NOW),
               lambda: logic.pick_word(store, "27/11/2026", EPOCH, NOW)):
        try:
            fn()
        except (RuntimeError, ValueError):
            continue
        raise AssertionError("se esperaba un error")


# ---------- importer ----------

ITEM = {"word": "parce", "display": "parce", "meaning": "Amigo.", "example": "",
        "region": "Antioquia", "source": "X"}


def test_importer_rechaza_invalidos_y_no_escribe():
    store = FakeStore()
    try:
        logic.import_words(store, [ITEM, {**ITEM, "word": "abc", "display": "abc"}])
    except ValueError:
        assert store.words == {}
        return
    raise AssertionError("se esperaba ValueError")


def test_importer_conserva_used_on():
    store = FakeStore()
    store.seed_words(["parce"])
    store.words["parce"]["used_on"] = "2026-11-27"
    assert logic.import_words(store, [ITEM, {**ITEM, "word": "arepa", "display": "arepa"}]) == 2
    assert store.words["parce"]["used_on"] == "2026-11-27"
    assert store.words["parce"]["meaning"] == "Amigo."
    assert "used_on" not in store.words["arepa"]
