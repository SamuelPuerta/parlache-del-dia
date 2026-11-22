import json
import os

from common.words import validate_words

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "words.json")
OK = {"word": "parce", "display": "parce", "meaning": "Amigo.", "example": "", "region": "Antioquia", "source": "X"}


def test_words_json_del_repo_es_valido():
    with open(DATA, encoding="utf-8") as f:
        items = json.load(f)
    assert validate_words(items) == []
    assert len(items) >= 60


def test_valida_item_correcto():
    assert validate_words([OK]) == []


def test_rechaza_lista_vacia_o_no_lista():
    assert validate_words([]) != []
    assert validate_words({"a": 1}) != []


def test_rechaza_longitud_y_caracteres():
    assert validate_words([{**OK, "word": "parc", "display": "parc"}])
    assert validate_words([{**OK, "word": "pa1ce", "display": "pa1ce"}])


def test_rechaza_duplicados_con_tilde():
    a = {**OK, "word": "bacan", "display": "bacán"}
    assert validate_words([a, {**a, "display": "bacan"}])


def test_rechaza_campos_vacios_y_display_distinto():
    assert validate_words([{**OK, "meaning": " "}])
    assert validate_words([{**OK, "source": ""}])
    assert validate_words([{**OK, "display": "pelao"}])
