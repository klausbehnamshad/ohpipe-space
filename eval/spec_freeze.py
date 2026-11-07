"""Praeregistrierung: schreibt eval/prereg.json (Schwellen, Fixture-Hashes, Datum).

Lauf: python eval/spec_freeze.py -> OK + Datei. Keine Messung, nur Festschreibung.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"

THRESHOLDS = {
    "f1_gap": 0.10,
    "coverage_floor": 0.80,
    "coverage_floor_status": "proposed",
    "alpha_gate": 0.80,
    "alpha_preliminary": [0.667, 0.80],
}
SPEC_HASH = "dc88f8f8c0c8ffe20b44cddadb3526e056959d7a5efccf08535e4b4e571095c3"


def main() -> int:
    man = json.loads((FIX / "manifest.json").read_text())
    prereg = {
        "date": date.today().isoformat(),
        "thresholds": THRESHOLDS,
        "fixture_hashes": man["files"],
        "spec_hash": SPEC_HASH,
        "status": "proposed",
    }
    out = Path(__file__).resolve().parent / "prereg.json"
    out.write_text(json.dumps(prereg, indent=1, sort_keys=True) + "\n")
    print(f"OK: Schwellen, {len(man['files'])} Fixture-Hashes und Datum festgeschrieben")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
