"""Mutantenklassen fuer Gate 1 (vgl. Bauplan-Mutantentabelle)."""
from __future__ import annotations

import unicodedata


def fmt_variants(text: str):
    return {
        "nfd": unicodedata.normalize("NFD", text),
        "crlf": text.replace("\n", "\r\n"),
        "bom": "﻿" + text,
    }


def delete_first_word(text: str, word: str) -> str:
    return text.replace(word, "", 1)


def negate_sentence(text: str, idx: int) -> str:
    parts, cur = [], ""
    for ch in text:
        cur += ch
        if ch in ".!?":
            parts.append(cur.strip())
            cur = ""
    if cur.strip():
        parts.append(cur.strip())
    parts[idx] = parts[idx] + " NICHT"
    return " ".join(parts)


def outside_swap_greeting(text: str) -> str:
    return text.replace("Guten Tag.", "Guten Tag NICHT.", 1).replace(
        "Good morning.", "Good morning NOT.", 1)


def swap_speaker_labels(words):
    """Aussen-Mutante: vertauscht SPK_01 und SPK_02 in den Wortlabels.

    Das Sprecherlabel ist nicht Teil der Spanne (Regie-Entscheidung Phase 2):
    der kanonische Text bleibt unveraendert, alle Anker bleiben gueltig.
    Erwartung: Anker unberuehrt, Review-Pflicht.
    """
    out = []
    for w in words:
        w2 = dict(w)
        if w2.get("speaker") == "SPK_01":
            w2["speaker"] = "SPK_02"
        elif w2.get("speaker") == "SPK_02":
            w2["speaker"] = "SPK_01"
        out.append(w2)
    return out
