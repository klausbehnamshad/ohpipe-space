"""Gradio-App ohpipe-space, Phase 2: drei Reiter.

Entwurf, Anker-Gate, Replay/STALE. Laeuft ohne GPU vollstaendig im
Fixture-Modus; auf ZeroGPU bietet sie einen Qwen-Entwurf als einzigen
GPU-Teil an. Gates und Replay nutzen dieselben Module wie eval/.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REPO = APP_DIR.parent
EVAL = REPO / "eval"
if str(EVAL) not in sys.path:
    sys.path.insert(0, str(EVAL))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import gradio as gr
from adapters import candidate
from anchor import resolve
from draft import FIXTURE_IDS, draft, resolve_mode
from journal import append, replay, stale_after_change, verify
from limits import check_and_consume, identity_of
from mutations import (fmt_variants, outside_swap_greeting,
                       swap_speaker_labels)
from run_gates import anchored

LEIT = "Gilt für synthetische Fixtures, nichts über echte Interviews."
PRUEF = ("Prüfbefehl: `bash eval/space_check.sh` — gespeicherte Ausgabe: "
         "`docs/checks/space_check_<datum>.txt`")
MUTANT_ROWS = ("format_nfd", "format_crlf", "format_bom", "inspan_negation",
               "outspan_greeting", "outspan_speaker_labels",
               "degenerate_junk")
ENTWURF_HEADER = ["Claim", "Art", "Status", "Anker-Hash", "Zitatzeuge"]
GATE_HEADER = ["Name", "Klasse", "erwartet", "beobachtet", "Treffer"]


def _request_parts(request) -> tuple:
    sess = getattr(request, "session_hash", "") or ""
    ip = ""
    try:
        client = getattr(request, "client", None)
        ip = (getattr(client, "host", "") or "") if client else ""
    except Exception:
        ip = ""
    return sess, ip


def entwurf(fixture_id: str, request: gr.Request,
            profile: gr.OAuthProfile | None = None):
    username = getattr(profile, "username", None) if profile else None
    sess, ip = _request_parts(request)
    identity, authed = identity_of(sess, ip, username)
    ok, used, limit = check_and_consume(identity, authed)
    mode = resolve_mode()
    hinweis = ""
    if mode == "zerogpu":
        if not ok:
            bundle = draft(fixture_id, mode="fixture")
            hinweis = (f"Tageslimit erreicht ({used}/{limit} je UTC-Tag), "
                       "Fixture-Modus")
        else:
            try:
                bundle = draft(fixture_id, mode="zerogpu")
            except Exception as exc:
                bundle = draft(fixture_id, mode="fixture")
                hinweis = (f"GPU-Fehler ({type(exc).__name__}), "
                           "Fixture-Modus")
    else:
        bundle = draft(fixture_id, mode=mode)
    rows = [[c["text"], c["kind"], c["status"],
             c["anchor_hash"] or "-", (c["quote"] or "")[:80] or "-"]
            for c in bundle["claims"]]
    label = bundle["label"]
    if hinweis:
        label = f"{label} | {hinweis}"
    meta = {"consent_status": "", "accessRights": "",
            "status": "vorgeschlagen",
            "darstellung": "consent_status und accessRights nur im Review"}
    return rows, bundle, meta, f"{label}\n\n{LEIT}"


def anchor_gate(fixture_id: str):
    fx = json.loads((REPO / "fixtures" / "dev"
                     / f"{fixture_id}.json").read_text())
    tx = fx["transcript"]["text"]
    draft_c = candidate({"text": tx, "words": fx["transcript"]["words"],
                         "speakers": fx["speakers"]})
    rows = []
    for name, var in fmt_variants(tx).items():
        o, t = anchored(draft_c, var)
        hit = len(o) == t
        rows.append([f"format_{name}", "Format in der Spanne",
                     "erkannt (robust)",
                     "Anker gilt weiter" if hit else "Anker bricht",
                     "ja" if hit else "nein"])
    title = draft_c["title"]
    broken = resolve(title + " NICHT", tx)
    rows.append(["inspan_negation", "Tausch in der Spanne",
                 "kein Aufloesen",
                 "aufgeloest" if broken else "nicht aufgeloest",
                 "nein" if broken else "ja"])
    out = outside_swap_greeting(tx)
    o, t = anchored(draft_c, out)
    hit = len(o) == t
    rows.append(["outspan_greeting", "Tausch ausserhalb der Spanne",
                 "Anker unberuehrt (Review-Pflicht)",
                 "alle Claims loesen" if hit else "Anker riss",
                 "ja" if hit else "nein"])
    swapped = swap_speaker_labels(fx["transcript"]["words"])
    draft_sw = candidate({"text": tx, "words": swapped,
                          "speakers": fx["speakers"]})
    o, t = anchored(draft_sw, tx)
    hit = len(o) == t
    rows.append(["outspan_speaker_labels", "Tausch ausserhalb der Spanne",
                 "Anker unberuehrt (Review-Pflicht)",
                 "alle Claims loesen" if hit else "Anker riss",
                 "ja" if hit else "nein"])
    junk = {"title": "XYZQ Fremder Satz ohne Bezug",
            "abstract": ["Noch ein fremder Satz ohne jeden Bezug."],
            "keywords": ["xyzabc", "qwertzui"]}
    jok, jtotal = anchored(junk, tx)
    rate = len(jok) / jtotal if jtotal else 0.0
    hit = rate < 0.80
    rows.append(["degenerate_junk", "entartet",
                 "scheitert an der Untergrenze",
                 f"Abdeckung {rate:.2f}",
                 "ja" if hit else "nein"])
    summary = {"fixture": fixture_id,
               "treffer": f"{sum(1 for r in rows if r[4] == 'ja')}/{len(rows)}"}
    return rows, summary


def replay_demo():
    name = "dev/de_001.json"
    fh = hashlib.sha256((REPO / "fixtures" / name).read_bytes()).hexdigest()
    journal = []
    append(journal, "register", {"fixture": "de_001", "hash": fh})
    append(journal, "proposal", {"draft": "candidate-v1"})
    append(journal, "note", {"text": "unabhaengige Notiz"})
    append(journal, "decision", {"accept": True, "reviewer": "Mensch"})
    first = replay(journal, fh)
    second = replay(journal, fh)
    changed = stale_after_change(journal, fh, fh + "x")
    kinds = [e["event"]["kind"] for e in journal]
    stale = [{"kind": k, "stale": bool(s)}
             for k, s in zip(kinds, changed["stale"])]
    bad = copy.deepcopy(journal)
    bad[1]["event"] = {"kind": "proposal", "payload": {"draft": "manipuliert"}}
    result = {
        "fixture": "de_001",
        "ereignisse": len(journal),
        "replay_a": first["bundle"]["hash"] if first["ok"] else None,
        "replay_b": second["bundle"]["hash"] if second["ok"] else None,
        "gleich": (first["ok"] and second["ok"]
                   and first["bundle"]["hash"] == second["bundle"]["hash"]),
        "stale": stale,
        "manipulation_erkannt": not verify(bad),
    }
    return result


with gr.Blocks(title="ohpipe-space: drei Gates") as demo:
    gr.Markdown("# ohpipe-space: drei Gates\n\n" + LEIT)
    gr.LoginButton()
    with gr.Tab("Entwurf"):
        gr.Markdown(LEIT)
        fixture_dd = gr.Dropdown(choices=list(FIXTURE_IDS), value="de_001",
                                 label="Fixture")
        go_btn = gr.Button("Entwurf erzeugen")
        claims_df = gr.Dataframe(headers=ENTWURF_HEADER, label="Claims")
        bundle_json = gr.JSON(label="Bundle")
        meta_json = gr.JSON(label="Metadaten (nur im Review)")
        label_md = gr.Markdown()
        go_btn.click(fn=entwurf, inputs=[fixture_dd],
                     outputs=[claims_df, bundle_json, meta_json, label_md],
                     api_name="draft")
        gr.Markdown(PRUEF)
    with gr.Tab("Anker-Gate"):
        gr.Markdown(LEIT)
        fixture_dd2 = gr.Dropdown(choices=list(FIXTURE_IDS), value="de_001",
                                  label="Fixture")
        gate_btn = gr.Button("Mutanten prüfen")
        gate_df = gr.Dataframe(headers=GATE_HEADER, label="Mutantentabelle")
        gate_json = gr.JSON(label="Zusammenfassung")
        gate_btn.click(fn=anchor_gate, inputs=[fixture_dd2],
                       outputs=[gate_df, gate_json], api_name="anchor_gate")
        gr.Markdown(PRUEF)
    with gr.Tab("Replay/STALE"):
        gr.Markdown(LEIT)
        replay_btn = gr.Button("Replay starten")
        replay_json = gr.JSON(label="Replay und STALE")
        replay_btn.click(fn=replay_demo, inputs=[], outputs=[replay_json],
                         api_name="replay")
        gr.Markdown(PRUEF)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    demo.queue(max_size=5, default_concurrency_limit=1)
    demo.launch(server_name=None, server_port=port, share=False)
