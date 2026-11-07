"""Gate 2: Journal mit Hash-Kette, Replay, STALE (nach ohpipe/dh-provenance-journal)."""
from __future__ import annotations

import copy
import hashlib
import json


def canonical_json_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def event_hash(event, prev_hash: str) -> str:
    return hashlib.sha256(canonical_json_bytes([prev_hash, event])).hexdigest()


def append(journal, kind: str, payload: dict):
    prev = journal[-1]["hash"] if journal else "GENESIS"
    event = {"kind": kind, "payload": payload}
    journal.append({"event": event, "prev": prev,
                    "hash": event_hash(event, prev)})
    return journal


def verify(journal) -> bool:
    prev = "GENESIS"
    for entry in journal:
        if entry["prev"] != prev:
            return False
        if entry["hash"] != event_hash(entry["event"], prev):
            return False
        prev = entry["hash"]
    return True


def bundle(journal, fixture_hash: str) -> dict:
    decisions = [e for e in journal if e["event"]["kind"] == "decision"]
    body = {"fixture": fixture_hash,
            "decisions": [d["event"]["payload"] for d in decisions]}
    digest = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return {"body": body, "hash": digest}


def replay(journal, fixture_hash: str):
    if not verify(journal):
        return {"ok": False, "reason": "chain-broken"}
    return {"ok": True, "bundle": bundle(journal, fixture_hash)}


def stale_after_change(journal, fixture_hash_old: str, fixture_hash_new: str):
    """STALE genau dann, wenn sich der Input-Hash geaendert hat."""
    if fixture_hash_old == fixture_hash_new:
        return {"stale": [False] * len(journal)}
    deps = [e["event"]["kind"] in ("proposal", "decision") for e in journal]
    return {"stale": deps}
