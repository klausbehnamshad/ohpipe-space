"""Gate 1: Stable-Text-Anchor (Profil nach anchorprobe).

Kanonisch: NFC, LF, BOM-strip. Ein Anchor bindet (SHA-256 des kanonischen
Texts, Zitatzeuge). Formatmutanten, die kanonisch identisch sind (NFD, CRLF,
BOM), werden absorbiert (Robustheit). Inhaltsaenderungen brechen den Hash.
"""
from __future__ import annotations

import hashlib
import unicodedata


def canonical(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("﻿"):
        text = text[1:]
    return unicodedata.normalize("NFC", text)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(canonical(text).encode("utf-8")).hexdigest()


def resolve(claim: str, transcript_text: str) -> bool:
    """Loest genau dann auf, wenn der kanonische Claim Teil des kanonischen Texts ist."""
    return canonical(claim) in canonical(transcript_text)


def resolve_token(token: str, transcript_text: str) -> bool:
    """Wortanker: case-insensitiv, ganzes Token (Satzanker bleiben exakt)."""
    toks = [t.strip(".,!?;:\"'()").lower()
            for t in canonical(transcript_text).split()]
    return token.strip().lower() in toks


def check_claims(claims, transcript_text):
    resolved = [c for c in claims if resolve(c, transcript_text)]
    total = len(claims)
    rate = len(resolved) / total if total else 0.0
    return {"total": total, "resolved": len(resolved),
            "unresolved": [c for c in claims if c not in resolved],
            "resolution_rate": round(rate, 4)}
