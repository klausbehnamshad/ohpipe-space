"""Gate-Laeufer: python eval/run_gates.py --split dev."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters import baseline, candidate
from anchor import canonical, check_claims, resolve, resolve_token
from journal import append, replay, stale_after_change, verify
from metrics import (dctap_check, krippendorff_alpha_nominal,
                     segmentation_scores, set_scores)
from mutations import (delete_first_word, fmt_variants, negate_sentence,
                       outside_swap_greeting, swap_speaker_labels)

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"
F1_GAP = 0.10
COVERAGE_FLOOR = 0.80  # Vorschlag der Regie; Klaus bestaetigt bei der Signatur
ALPHA_EXPECTED = 0.6429  # alpha_pair.json (Harness-Test, kein Gold-Massstab)

PASS, FAIL = "PASS", "FAIL"


def load(name):
    return json.loads((FIX / name).read_text())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_manifest():
    man = json.loads((FIX / "manifest.json").read_text())
    bad = [p for p, h in man["files"].items()
           if sha256_file(FIX / p) != h]
    return (PASS, f"manifest ok") if not bad else (FAIL, f"hash mismatch: {bad}")


def claims_of(draft):
    return [draft["title"]] + draft["abstract"] + draft["keywords"]


def anchored(draft, tx):
    """Saetze exakt, einzelne Keywords als case-insensitive Wortanker."""
    ok = [c for c in [draft["title"]] + draft["abstract"] if resolve(c, tx)]
    ok += [k for k in draft["keywords"] if resolve_token(k, tx)]
    total = 1 + len(draft["abstract"]) + len(draft["keywords"])
    return ok, total


def gate1(fx):
    tx = fx["transcript"]["text"]
    draft = candidate({"text": tx, "words": fx["transcript"]["words"],
                       "speakers": fx["speakers"]})
    ok, total = anchored(draft, tx)
    rate = len(ok) / total if total else 0.0
    if rate < COVERAGE_FLOOR:
        have = set(ok)
        missing = [c for c in claims_of(draft) if c not in have][:3]
        return FAIL, f"unter Untergrenze {COVERAGE_FLOOR}: {missing}"
    # Formatmutanten werden kanonisch absorbiert (Robustheit)
    for name, var in fmt_variants(tx).items():
        o, t = anchored(draft, var)
        if len(o) != t:
            return FAIL, f"Formatmutante {name} bricht Anker"
    # Inhaltsbruch in der Spanne: Titel aus gebrochenem Text darf NICHT loesen
    tw = next((t.strip("?.,!") for t in draft["title"].split()
               if len(t.strip("?.,!")) > 4), None)
    if tw:
        broken = delete_first_word(tx, tw)
        if tw in tx and resolve(draft["title"], broken):
            return FAIL, "Inhaltsbruch unerkannt"
    # Tausch in der Spanne: negierter Titelsatz darf nicht loesen
    if resolve(draft["title"] + " NICHT", tx):
        return FAIL, "Tausch in Spanne loest auf"
    # Ausserhalb-Tausch: alle Claims loesen weiter (Review-Pflicht, kein Gate-Fail)
    out = outside_swap_greeting(tx)
    o, t = anchored(draft, out)
    if len(o) != t:
        return FAIL, "Ausserhalb-Tausch reisst Anker"
    # Entartet: Entwurf ohne jeden Bezug muss an der Untergrenze scheitern
    junk = {"title": "XYZQ Fremder Satz ohne Bezug",
            "abstract": ["Noch ein fremder Satz ohne jeden Bezug."],
            "keywords": ["xyzabc", "qwertzui"]}
    jok, jtotal = anchored(junk, tx)
    jrate = len(jok) / jtotal if jtotal else 0.0
    if jrate >= COVERAGE_FLOOR:
        return FAIL, "Untergrenze faengt entartet nicht"
    return PASS, f"Abdeckung {rate:.2f} (Untergrenze {COVERAGE_FLOOR}), Mutanten ok"


def gate2(fx, fname):
    fh = sha256_file(FIX / fname)
    j = []
    append(j, "register", {"fixture": fx["fixture_id"], "hash": fh})
    append(j, "proposal", {"draft": "candidate-v1"})
    append(j, "note", {"text": "unabhaengige Notiz"})
    append(j, "decision", {"accept": True, "reviewer": "Mensch"})
    r1, r2 = replay(j, fh), replay(j, fh)
    if not (r1["ok"] and r2["ok"]) or r1["bundle"]["hash"] != r2["bundle"]["hash"]:
        return FAIL, "Replay nicht bytegleich"
    st = stale_after_change(j, fh, fh + "x")
    kinds = [e["event"]["kind"] for e in j]
    want = [k in ("proposal", "decision") for k in kinds]
    if st["stale"] != want:
        return FAIL, f"STALE-Menge falsch: {st['stale']}"
    if any(v for v, k in zip(stale_after_change(j, fh, fh)["stale"], kinds)):
        return FAIL, "Fehlalarm ohne Aenderung"
    bad = [dict(e) for e in j]
    bad[1]["event"] = dict(bad[1]["event"])
    bad[1]["event"]["payload"] = {"draft": "manipuliert"}
    if verify(bad):
        return FAIL, "Manipulation unerkannt"
    # P/R ueber 3 Input-Mutationen
    tp = fp = fn = 0
    for m in ["x", "y", "z"]:
        s = stale_after_change(j, fh, fh + m)["stale"]
        for flag, k in zip(s, kinds):
            dep = k in ("proposal", "decision")
            if flag and dep:
                tp += 1
            elif flag:
                fp += 1
            elif dep:
                fn += 1
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    if prec != 1.0 or rec != 1.0:
        return FAIL, f"STALE P={prec} R={rec}"
    return PASS, f"Replay {r1['bundle']['hash'][:12]}…, STALE P=R=1.0"


def hms(h):
    p = h.split(":")
    return int(p[0]) * 3600 + int(p[1]) * 60 + int(p[2])


def gold_sent_sections(fx):
    """Zeitcodierte Gold-Abschnitte -> Satzspannen (deterministisch)."""
    text = fx["transcript"]["text"]
    words = fx["transcript"]["words"]
    sents, buf, bounds, pos = [], "", [], 0
    for ch in text:
        buf += ch
        if ch in ".!?":
            if buf.strip():
                n = len(buf.strip().split(" "))
                bounds.append((pos, pos + n))
                pos += n
                buf = ""
    n_sent = len(bounds)
    out = []
    for seg in fx["gold"]["draft_fields"]["timecoded_segments"]:
        end = hms(seg["end"])
        cut = sum(1 for a, b in bounds if words[b - 1]["t1"] <= end + 1e-9)
        out.append(cut)
    spans, prev = [], 0
    for c in out:
        spans.append({"start_sent": prev, "end_sent": c})
        prev = c
    if spans:
        spans[-1]["end_sent"] = n_sent  # letzter Abschnitt laeuft immer bis Ende
    return spans, n_sent


def gate3(fx):
    tx_in = {"text": fx["transcript"]["text"],
             "words": fx["transcript"]["words"],
             "speakers": fx["speakers"]}
    base, cand = baseline(tx_in), candidate(tx_in)
    gold = fx["gold"]["draft_fields"]
    # Keywords sind freie Strings (Core ohne kontrolliertes Vokabular):
    # Vergleich case-insensitiv; kontrollierte Felder bleiben exakt.
    gk = [k.lower() for k in gold["keywords"]]
    fb = set_scores(gk, [k.lower() for k in base["keywords"]])["f1"]
    fc = set_scores(gk, [k.lower() for k in cand["keywords"]])["f1"]
    if fc - fb < F1_GAP:
        return FAIL, f"F1-Differenz {fc - fb:.2f} < {F1_GAP}"
    gold_secs, n = gold_sent_sections(fx)
    seg = segmentation_scores(gold_secs, cand["sections"], n)
    if not (seg["pk"] < seg["pk_trivial_eq"] and seg["pk"] < seg["pk_trivial_none"]):
        return FAIL, f"Pk {seg} nicht unter trivial"
    if not (seg["windiff"] < seg["windiff_trivial_eq"] and seg["windiff"] < seg["windiff_trivial_none"]):
        return FAIL, f"WindowDiff {seg} nicht unter trivial"
    reviewed = dict(gold)
    reviewed.update(fx["gold"]["review"])
    chk = dctap_check(reviewed)
    if not chk["valid"]:
        return FAIL, f"DCTAP Review: {chk}"
    if "consent_status" in gold or "accessRights" in gold:
        return FAIL, "Entwurf enthaelt consent/access"
    return PASS, f"F1 {fb:.2f}->{fc:.2f} (+{fc - fb:.2f}), Pk {seg['pk']}"


def speaker_label_mutant():
    """Aussen-Mutante Sprecherlabel (Phase 2, additiv).

    Das Label ist nicht Teil der Spanne: der Entwurf aus vertauschten
    Labels loest alle Claims weiter auf. Erwartung: Anker unberuehrt.
    """
    for name in ["dev/de_001.json", "dev/en_001.json"]:
        fx = load(name)
        tx = fx["transcript"]["text"]
        swapped = swap_speaker_labels(fx["transcript"]["words"])
        draft_sw = candidate({"text": tx, "words": swapped,
                              "speakers": fx["speakers"]})
        ok, total = anchored(draft_sw, tx)
        if len(ok) != total:
            return FAIL, f"Sprecherlabel-Tausch reisst Anker in {fx['fixture_id']}"
    return PASS, "Sprecherlabel-Tausch: Anker unberuehrt (de_001, en_001)"


def alpha_check():
    pair = load("dev/alpha_pair.json")
    a = krippendorff_alpha_nominal(pair["coder_a"], pair["coder_b"])
    if ALPHA_EXPECTED is None:
        return PASS, f"alpha={a} (Fixpunkt noch offen)"
    if abs(a - ALPHA_EXPECTED) > 0.002:
        return FAIL, f"alpha {a} != {ALPHA_EXPECTED}"
    return PASS, f"alpha={a}"


def main():
    split = sys.argv[sys.argv.index("--split") + 1] if "--split" in sys.argv else "dev"
    if split != "dev":
        held = FIX / "heldout"
        if not held.exists() or not list(held.glob("*.json")):
            print("heldout: SKIP (keine zurueckgehaltenen Fixtures)")
            return 0
    results = []
    man = check_manifest()
    results.append(("manifest",) + man)
    for name in ["dev/de_001.json", "dev/en_001.json"]:
        fx = load(name)
        results.append((f"gate1:{fx['fixture_id']}",) + gate1(fx))
        results.append((f"gate2:{fx['fixture_id']}",) + gate2(fx, name))
        results.append((f"gate3:{fx['fixture_id']}",) + gate3(fx))
    results.append(("mutants:outspan_speaker_labels",) + speaker_label_mutant())
    results.append(("harness:alpha",) + alpha_check())
    code = 0
    for name, status, msg in results:
        print(f"{status} {name}: {msg}")
        code = code or (status != PASS)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
