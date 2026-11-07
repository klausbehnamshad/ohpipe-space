"""Erzeugt die vorberechneten Entwuerfe (Kandidat, Phase 2).

Modell-Entwuerfe kommen in Phase 3, nachdem der Space einmal gelaufen ist.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REPO = APP_DIR.parent
EVAL = REPO / "eval"
if str(EVAL) not in sys.path:
    sys.path.insert(0, str(EVAL))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from adapters import candidate
from draft import (FIXTURE_IDS, PRE, FIX, anchor_raw_draft, _bundle_hash,
                   _sentences)


def main() -> None:
    PRE.mkdir(parents=True, exist_ok=True)
    for fixture_id in FIXTURE_IDS:
        fx = json.loads((FIX / "dev" / f"{fixture_id}.json").read_text())
        text = fx["transcript"]["text"]
        raw = candidate({"text": text, "words": fx["transcript"]["words"],
                         "speakers": fx["speakers"]})
        n_sent = len(_sentences(text))
        anchored = anchor_raw_draft(raw, text, n_sent)
        draft_part = {"title": raw["title"], "abstract": raw["abstract"],
                      "keywords": raw["keywords"],
                      "sections": anchored["sections"]}
        draft_hash = _bundle_hash(draft_part)
        body = {"fixture_id": fixture_id, "mode": "fixture",
                "label": f"vorberechnet (Kandidat), Hash {draft_hash}",
                "draft": draft_part, "claims": anchored["claims"],
                "model": {"kind": "candidate-v1",
                          "note": "Regelbaseline aus eval/adapters.py, kein Modell"}}
        body["bundle_hash"] = _bundle_hash(
            {k: v for k, v in body.items() if k != "bundle_hash"})
        (PRE / f"{fixture_id}.json").write_text(
            json.dumps(body, ensure_ascii=False, indent=1) + "\n")
        print(f"{fixture_id}: {len(anchored['claims'])} Claims, "
              f"{body['bundle_hash'][:12]}")


if __name__ == "__main__":
    main()
