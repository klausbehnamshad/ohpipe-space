"""Rauchtest im Modus cpu (Phase 2, Abnahme, nicht CI).

Laedt Qwen2.5-0.5B-Instruct (feste Revision) auf CPU, erzeugt einen
Entwurf fuer de_001 und druckt die Kennzahl. Modell-Download ~1 GB.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["OHPIPE_SPACE_MODE"] = "cpu"
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from draft import draft


def main() -> int:
    bundle = draft("de_001", mode="cpu")
    claims = bundle["claims"]
    n = len(claims)
    m = sum(1 for c in claims if c["status"] == "belegt")
    print(f"smoke ok: Entwurf aus Modell, {n} Claims, {m} belegt")
    return 0 if n >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
