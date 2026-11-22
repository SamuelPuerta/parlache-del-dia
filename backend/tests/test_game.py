import random
from datetime import date, datetime, timedelta, timezone

from common import game
from common.util import get_player_id, parse_json_body, short_id

VALID_ID = "123e4567-e89b-42d3-a456-426614174000"


def test_score_todo_correcto():
    assert game.score("parce", "parce") == ["correct"] * 5


def test_score_pelao_parce():
    assert game.score("pelao", "parce") == [
        "correct", "present", "absent", "present", "absent",
    ]


def test_score_letras_repetidas():
    assert game.score("aaaaa", "arepa") == [
        "correct", "absent", "absent", "absent", "correct",
    ]


def test_score_no_marca_present_de_mas():
    # Solo hay una 'o' en la palabra secreta
    assert game.score("ooxxx", "oabcd") == [
        "correct", "absent", "absent", "absent", "absent",
    ]


def test_normalize_quita_tildes_y_conserva_enie():
    assert game.normalize("Bacán") == "bacan"
    assert game.normalize("Año") == "año"
    assert game.normalize("  PAÍSA ") == "paisa"


def test_clean_guess():
    assert game.clean_guess("Bacán") == "bacan"
    assert game.clean_guess("año") is None  # 3 letras
    assert game.clean_guess("cañon") == "cañon"
    assert game.clean_guess("ab1de") is None
    assert game.clean_guess("abcdef") is None
    assert game.clean_guess(None) is None
    assert game.clean_guess(12345) is None


def test_player_id():
    assert game.is_valid_player_id(VALID_ID)
    assert not game.is_valid_player_id("123e4567-e89b-12d3-a456-426614174000")  # no es v4
    assert not game.is_valid_player_id("no-es-uuid")
    assert not game.is_valid_player_id(None)


def test_get_player_id_cabecera_minuscula():
    assert get_player_id({"headers": {"x-player-id": VALID_ID}}) == VALID_ID
    assert get_player_id({"headers": {"X-Player-Id": VALID_ID}}) is None
    assert get_player_id({"headers": {}}) is None
    assert get_player_id({}) is None
    assert short_id(VALID_ID) == "123e4567"


def test_parse_json_body():
    assert parse_json_body({"body": '{"guess": "parce"}'}) == {"guess": "parce"}
    assert parse_json_body({"body": "no json"}) is None
    assert parse_json_body({"body": "[1, 2]"}) is None
    assert parse_json_body({}) is None


def test_fecha_colombia_usa_utc_menos_5():
    # 03:00 UTC del 28 de nov sigue siendo 27 de nov a las 22:00 en Bogota
    now = datetime(2026, 11, 28, 3, 0, tzinfo=timezone.utc)
    assert game.today_bogota(now) == date(2026, 11, 27)


def test_segundos_hasta_medianoche():
    now = datetime(2026, 11, 27, 23, 0, tzinfo=game.BOGOTA)
    assert game.seconds_to_next_midnight(now) == 3600
    now = datetime(2026, 11, 27, 0, 0, tzinfo=game.BOGOTA)
    assert game.seconds_to_next_midnight(now) == 86400


def test_numero_del_dia():
    epoch = date(2026, 11, 25)
    assert game.puzzle_number(date(2026, 11, 25), epoch) == 1
    assert game.puzzle_number(date(2026, 11, 27), epoch) == 3


def test_next_streak():
    today = date(2026, 11, 27)
    assert game.next_streak(None, 0, today) == 1
    assert game.next_streak("2026-11-26", 2, today) == 3
    assert game.next_streak("2026-11-20", 5, today) == 1


def test_effective_streak():
    today = date(2026, 11, 27)
    assert game.effective_streak("2026-11-27", 4, today) == 4
    assert game.effective_streak("2026-11-26", 4, today) == 4
    assert game.effective_streak("2026-11-25", 4, today) == 0
    assert game.effective_streak(None, 0, today) == 0


def test_alias_formato():
    alias = game.make_alias(random.Random(1))
    nombre, numero = alias.rsplit("-", 1)
    assert nombre in game.ALIAS_FOODS
    assert len(numero) == 3 and numero.isdigit()


def test_emf_estructura(capsys):
    import json

    from common import emf

    emf.emit("guess", GuessesSubmitted=1, GamesWon=1)
    data = json.loads(capsys.readouterr().out)
    assert data["Service"] == "guess"
    spec = data["_aws"]["CloudWatchMetrics"][0]
    assert spec["Namespace"] == "ParlacheDelDia"
    assert spec["Dimensions"] == [["Service"]]
    assert [m["Name"] for m in spec["Metrics"]] == ["GuessesSubmitted", "GamesWon"]
