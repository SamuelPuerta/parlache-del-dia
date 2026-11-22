#!/usr/bin/env python3
"""Convierte backend/data/colombianismos_5_letras.csv en backend/data/words.json."""
import csv
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend", "src"))

from common.game import normalize  # noqa: E402
from common.words import validate_words  # noqa: E402

PLACEHOLDER = "No especificado en la fuente"


def main() -> int:
    src = os.path.join(ROOT, "backend", "data", "colombianismos_5_letras.csv")
    dst = os.path.join(ROOT, "backend", "data", "words.json")
    items = []
    with open(src, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            display = r["palabra"].strip()
            word = normalize(display)
            example = r["ejemplo"].strip()
            items.append({
                "word": word,
                "display": display,
                "meaning": r["significado"].strip(),
                "example": "" if example == PLACEHOLDER else example,
                "region": r["región"].strip(),
                "source": r["fuente"].strip(),
            })
    errors = validate_words(items)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{len(items)} palabras escritas en {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
