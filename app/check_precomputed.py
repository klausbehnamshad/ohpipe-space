"""Prueft die vorberechneten Entwuerfe (Schritt 5, ohne GPU)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
FORBIDDEN = ("consent_status", "accessRights")


def _find_forbidden(node, path=""):
    hits = []
    if isinstance(node, dict):
        for key, val in node.items():
            here = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN:
                hits.append(here)
            hits.extend(_find_forbidden(val, here))
    elif isinstance(node, list):
        for i, val in enumerate(node):
            hits.extend(_find_forbidden(val, f"{path}[{i}]"))
    return hits


def main() -> int:
    files = sorted((APP_DIR / "precomputed").glob("*.json"))
    if len(files) != 2:
        print(f"precomputed FAIL: {len(files)} Dateien, erwartet 2")
        return 1
    for path in files:
        body = json.loads(path.read_text())
        hits = _find_forbidden(body)
        if hits:
            print(f"precomputed FAIL: {path.name} enthaelt Review-Feld: "
                  f"{hits[0]}")
            return 1
    print("precomputed ok: 2 Dateien, keine Review-Felder")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
