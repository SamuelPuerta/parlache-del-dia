"""Validacion del archivo words.json (la reutilizara la Lambda importer)."""
from common.game import GUESS_RE, normalize

REQUIRED = ("word", "display", "meaning", "region", "source")


def validate_words(items) -> list[str]:
    """Devuelve la lista de errores; vacia si el archivo es valido."""
    errors: list[str] = []
    if not isinstance(items, list) or not items:
        return ["El archivo debe ser una lista no vacia"]
    seen: set[str] = set()
    for i, it in enumerate(items):
        where = f"#{i}"
        if not isinstance(it, dict):
            errors.append(f"{where}: no es un objeto")
            continue
        for field in REQUIRED:
            if not isinstance(it.get(field), str) or not it[field].strip():
                errors.append(f"{where}: falta '{field}'")
        if not isinstance(it.get("example", ""), str):
            errors.append(f"{where}: 'example' debe ser texto")
        word, display = it.get("word"), it.get("display")
        if isinstance(word, str):
            key = normalize(word)
            if not GUESS_RE.match(key):
                errors.append(f"{where}: '{word}' no tiene 5 letras validas")
            if key in seen:
                errors.append(f"{where}: '{key}' esta duplicada")
            seen.add(key)
            if isinstance(display, str) and normalize(display) != key:
                errors.append(f"{where}: 'display' no coincide con 'word'")
    return errors
