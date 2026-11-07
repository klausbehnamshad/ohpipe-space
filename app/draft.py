"""Modelladapter der Space-App (Phase 2).

Drei Betriebsarten: zerogpu, cpu, fixture. Dispatch-Regel resolve_mode():
Ein explizit gesetztes OHPIPE_SPACE_MODE (gueltiger Wert) gewinnt immer.
Fehlt es, gilt zerogpu, wenn SPACE_ID gesetzt und spaces importierbar ist,
sonst fixture. Nur zerogpu nutzt GPU und hat Quota-Rueckfall. Rauchtest
und App rufen denselben Adapter draft(fixture_id, mode) auf.
"""
from __future__ import annotations

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

import anchor as anchor_mod

FIX = REPO / "fixtures"
PRE = APP_DIR / "precomputed"

MODEL_ID_ZERO = "Qwen/Qwen2.5-7B-Instruct"
MODEL_REV_ZERO = "a09a35458c702b33eeacc393d103063234e8bc28"
MODEL_ID_CPU = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REV_CPU = "7ae557604adf67be50417f59c2c2f167def9a775"
MAX_TOKENS_ZERO = 512
MAX_TOKENS_CPU = 512
SEED = 7
FIXTURE_IDS = ("de_001", "en_001")


def resolve_mode() -> str:
    explicit = os.environ.get("OHPIPE_SPACE_MODE", "").strip().lower()
    if explicit in ("zerogpu", "cpu", "fixture"):
        return explicit
    if os.environ.get("SPACE_ID"):
        try:
            import spaces  # noqa: F401
            return "zerogpu"
        except Exception:
            pass
    return "fixture"


_MODE = resolve_mode()

_generate_gpu = None
if _MODE == "zerogpu":
    try:
        import spaces
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:
        raise RuntimeError(
            "Modus zerogpu braucht spaces, torch und transformers; "
            "ausserhalb des Space ist der Import geschuetzt, der Modus "
            "darf dort nicht gewaehlt werden."
        ) from exc
    _tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID_ZERO, revision=MODEL_REV_ZERO)
    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID_ZERO, revision=MODEL_REV_ZERO, dtype=torch.bfloat16)
    _model.to("cuda")
    _model.eval()

    @spaces.GPU(duration=45)
    def _generate_gpu(prompt: str) -> str:
        encoded = _tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            return_tensors="pt", add_generation_prompt=True)
        input_ids = encoded["input_ids"].to("cuda")
        with torch.no_grad():
            out = _model.generate(
                input_ids, max_new_tokens=MAX_TOKENS_ZERO,
                do_sample=False, pad_token_id=_tokenizer.eos_token_id)
        return _tokenizer.decode(out[0][input_ids.shape[1]:],
                                 skip_special_tokens=True)


def _run_generation(tokenizer, model, prompt: str, max_tokens: int,
                    device=None) -> str:
    """Ein Generierungsdurchlauf: input_ids-Tensor ans Modell, Rest dekodieren.

    apply_chat_template liefert ein Dict; generate braucht den Tensor.
    """
    encoded = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        return_tensors="pt", add_generation_prompt=True)
    input_ids = encoded["input_ids"]
    if device:
        input_ids = input_ids.to(device)
    out = model.generate(
        input_ids, max_new_tokens=max_tokens,
        do_sample=False, pad_token_id=tokenizer.eos_token_id)
    return tokenizer.decode(out[0][input_ids.shape[1]:],
                            skip_special_tokens=True)


def _config_sha256(model_id: str, revision: str) -> str:
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(model_id, "config.json", revision=revision)
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_prompt(text: str, sentences: list, language: str) -> str:
    numbered = "\n".join(f"[{i}] {s}" for i, s in enumerate(sentences))
    if language == "de":
        return (
            "Du erstellst einen Erschliessungsentwurf zu einem Transkript. "
            "Antworte nur mit JSON, ohne weitere Worte, in genau dieser Form:\n"
            '{"title": "Titel (ein Satz aus dem Transkript)", '
            '"abstract": ["Satz 1", "Satz 2"], '
            '"keywords": ["wort1", "wort2"], '
            '"sections": [{"start_sent": 0, "end_sent": 2, "title": "Abschnittstitel"}]}\n'
            "Nimm fuer title, abstract und keywords nur Woerter und Saetze, "
            "die woertlich im Transkript stehen. Schreibe jeden Satz "
            "Zeichen fuer Zeichen ab, erfinde kein Wort, keine Zahl. "
            "sections decken alle Saetze lueckenlos ab (start_sent inklusiv, "
            "end_sent exklusiv). Transkript:\n"
            + numbered)
    return (
        "You draft an archival description for a transcript. "
        "Answer with JSON only, no other words, exactly in this shape:\n"
        '{"title": "Title (one sentence from the transcript)", '
        '"abstract": ["Sentence 1", "Sentence 2"], '
        '"keywords": ["word1", "word2"], '
        '"sections": [{"start_sent": 0, "end_sent": 2, "title": "Section title"}]}\n'
        "Use only words and sentences that appear verbatim in the transcript "
        "for title, abstract and keywords. Copy every sentence "
        "character for character, invent no word, no number. Sections "
        "cover all sentences without gaps (start_sent inclusive, "
        "end_sent exclusive). Transcript:\n"
        + numbered)


def parse_model_json(answer: str) -> dict:
    start = answer.find("{")
    if start < 0:
        raise ValueError("Modellantwort enthaelt kein JSON")
    raw, _ = json.JSONDecoder().raw_decode(answer[start:])
    if not isinstance(raw, dict):
        raise ValueError("Modellantwort ist kein JSON-Objekt")
    return raw


def _claim_entry(text: str, kind: str, transcript: str) -> dict:
    if not text.strip():
        ok = False
    elif kind == "keyword":
        ok = anchor_mod.resolve_token(text, transcript)
    else:
        ok = anchor_mod.resolve(text, transcript)
    return {"text": text, "kind": kind,
            "status": "belegt" if ok else "unbelegt",
            "anchor_hash": anchor_mod.sha256_hex(text) if ok else None,
            "quote": text if ok else None}


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    return []


def anchor_raw_draft(raw: dict, transcript: str, n_sent: int) -> dict:
    claims = [_claim_entry(str(raw.get("title", "")), "title", transcript)]
    for sent in _as_list(raw.get("abstract", []))[:8]:
        claims.append(_claim_entry(str(sent), "abstract", transcript))
    for kw in _as_list(raw.get("keywords", []))[:12]:
        claims.append(_claim_entry(str(kw), "keyword", transcript))
    sections = []
    for sec in _as_list(raw.get("sections", [])):
        if not isinstance(sec, dict):
            continue
        try:
            a = max(0, int(sec.get("start_sent", 0)))
            b = min(n_sent, int(sec.get("end_sent", 0)))
        except (TypeError, ValueError):
            continue
        if a < b:
            sections.append({"start_sent": a, "end_sent": b,
                             "title": str(sec.get("title", ""))})
    return {"claims": claims, "sections": sections}


def draft_part_of(raw: dict, sections: list) -> dict:
    """Entwurfs-Teil des Bundles; abstrakte Felder robust normiert."""
    return {"title": str(raw.get("title", "")),
            "abstract": [str(s)
                         for s in _as_list(raw.get("abstract", []))[:8]],
            "keywords": [str(k)
                         for k in _as_list(raw.get("keywords", []))[:12]],
            "sections": sections}


def _sentences(text: str) -> list:
    out, buf = [], ""
    for ch in text:
        buf += ch
        if ch in ".!?":
            if buf.strip():
                out.append(buf.strip())
            buf = ""
    if buf.strip():
        out.append(buf.strip())
    return out


def _generate_cpu(prompt: str) -> str:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID_CPU, revision=MODEL_REV_CPU)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID_CPU, revision=MODEL_REV_CPU, dtype=torch.float32)
    model.eval()
    torch.manual_seed(SEED)
    with torch.no_grad():
        return _run_generation(tokenizer, model, prompt, MAX_TOKENS_CPU)


def _bundle_hash(body: dict) -> str:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()


def _model_draft(fixture_id: str, mode: str) -> dict:
    fx = json.loads((FIX / "dev" / f"{fixture_id}.json").read_text())
    text = fx["transcript"]["text"]
    sents = _sentences(text)
    prompt = build_prompt(text, sents, fx.get("language", "de"))
    if mode == "zerogpu":
        answer = _generate_gpu(prompt)
        model_id, revision = MODEL_ID_ZERO, MODEL_REV_ZERO
    else:
        answer = _generate_cpu(prompt)
        model_id, revision = MODEL_ID_CPU, MODEL_REV_CPU
    raw = parse_model_json(answer)
    anchored = anchor_raw_draft(raw, text, len(sents))
    draft_part = draft_part_of(raw, anchored["sections"])
    draft_hash = _bundle_hash(draft_part)
    body = {"fixture_id": fixture_id, "mode": mode,
            "label": f"Modell ({model_id}), Hash {draft_hash}",
            "draft": draft_part, "claims": anchored["claims"],
            "metadata": {"consent_status": "", "accessRights": "",
                         "note": "nur im Review"},
            "model": {"id": model_id, "revision": revision,
                      "config_sha256": _config_sha256(model_id, revision)}}
    body["bundle_hash"] = _bundle_hash(
        {k: v for k, v in body.items() if k != "bundle_hash"})
    return body


def draft(fixture_id: str, mode: str | None = None) -> dict:
    """Erzeugt das Entwurfs-Bundle fuer ein Fixture.

    mode None nimmt den Modulmodus aus resolve_mode(). Im Modus fixture
    wird kein Modell geladen und weder torch noch spaces importiert.
    """
    use = mode or _MODE
    if fixture_id not in FIXTURE_IDS:
        raise ValueError(f"unbekanntes Fixture: {fixture_id}")
    if use == "fixture":
        body = json.loads((PRE / f"{fixture_id}.json").read_text())
        body = dict(body)
        body["mode"] = "fixture"
        body.setdefault("metadata", {"consent_status": "", "accessRights": "",
                                     "note": "nur im Review"})
        return body
    if use in ("zerogpu", "cpu"):
        return _model_draft(fixture_id, use)
    raise ValueError(f"unbekannter Modus: {use}")
