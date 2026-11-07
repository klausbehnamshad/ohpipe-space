"""Praeregistrierung: Standard ist PRUEFEN, Schreiben nur mit --write.

Pruefen: python eval/spec_freeze.py -> vergleicht eingecheckte prereg.json
mit Manifest-Hashes und Schwellen, Datum bleibt unangetastet. Abweichung
-> FAIL, Exit 1. Schreiben: python eval/spec_freeze.py --write.
"""
from __future__ import annotations

import hashlib
import json
import sys
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


def expected():
    man = json.loads((FIX / "manifest.json").read_text())
    return {
        "thresholds": THRESHOLDS,
        "fixture_hashes": man["files"],
        "spec_hash": SPEC_HASH,
    }


def verify() -> int:
    path = Path(__file__).resolve().parent / "prereg.json"
    if not path.exists():
        print("FAIL: eval/prereg.json fehlt (erst --write, dann pruefen)")
        return 1
    have = json.loads(path.read_text())
    want = expected()
    for key in ("thresholds", "fixture_hashes", "spec_hash"):
        if have.get(key) != want[key]:
            print(f"FAIL: {key} weicht ab (eingecheckt vs. erwartet)")
            return 1
    print(f"OK: prereg.json stimmt (Schwellen, {len(want['fixture_hashes'])} Hashes, Spec-Hash)")
    return 0


def write() -> int:
    prereg = {"date": date.today().isoformat(), "status": "proposed"}
    prereg.update(expected())
    out = Path(__file__).resolve().parent / "prereg.json"
    out.write_text(json.dumps(prereg, indent=1, sort_keys=True) + "\n")
    print(f"OK: Schwellen, {len(prereg['fixture_hashes'])} Fixture-Hashes und Datum festgeschrieben")
    return 0


if __name__ == "__main__":
    if "--write" in sys.argv:
        raise SystemExit(write())
    raise SystemExit(verify())
