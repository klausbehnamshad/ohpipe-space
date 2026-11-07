"""Baseline (naiv, --voll-aequivalent) und Kandidat (bessere Regeln).

Beide erhalten NUR das Transkript (Text, Woerter, Sprecher). Wer Gold
liest, faellt durch: run_gates prueft die Signatur per Inspektions-Test.
"""
from __future__ import annotations

STOP = {
    "und", "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer",
    "einem", "einen", "mit", "fuer", "für", "sie", "ich", "wir", "ist",
    "sind", "war", "waren", "hat", "haben", "auch", "als", "auf", "aus",
    "bei", "im", "in", "nicht", "sich", "von", "zu", "zum", "zur", "über",
    "über", "oder", "aber", "wie", "was", "wer", "wo", "so", "da", "es",
    "er", "ja", "nein", "and", "the", "a", "an", "of", "to", "in", "on",
    "for", "with", "was", "were", "is", "are", "be", "been", "have", "has",
    "had", "at", "by", "from", "as", "or", "but", "how", "what", "who",
    "where", "so", "that", "this", "these", "those", "then", "than", "our",
    "your", "his", "her", "its", "you", "we", "they", "he", "she", "it",
    "i", "me", "my", "yes", "no", "not",
}


def sentences(text):
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


def content_tokens(text):
    toks = []
    for raw in text.split():
        t = raw.strip(".,!?;:\"'()").lower()
        if len(t) > 3 and t not in STOP:
            toks.append(t)
    return toks


def term_freq(text):
    from collections import Counter
    return Counter(content_tokens(text))


def baseline(tx):
    """Trivial: erster Satz, erste zwei Saetze, erste fuenf Inhaltswoerter,
    drei gleiche Teile. Keine Stopwortliste, keine Statistik."""
    sents = sentences(tx["text"])
    seen, top = set(), []
    for raw in tx["text"].split():
        t = raw.strip(".,!?;:\"'()").lower()
        if len(t) > 3 and t not in seen:
            seen.add(t)
            top.append(t)
        if len(top) == 5:
            break
    n = len(sents)
    thirds = [0, round(n / 3), round(2 * n / 3), n]
    secs = [{"start_sent": thirds[i], "end_sent": thirds[i + 1],
             "title": f"Teil {i + 1}"} for i in range(3) if thirds[i] < thirds[i + 1]]
    return {"title": sents[0][:80], "abstract": sents[:2],
            "keywords": top, "sections": secs}


def candidate(tx):
    """Bessere Regeln: Fragesatz als Titel, TF-Sentences, TF-Keywords, Sprecherbloecke."""
    sents = sentences(tx["text"])
    tf = term_freq(tx["text"])
    title = next((s for s in sents if s.endswith("?")), sents[0])[:80]
    scored = []
    for i, s in enumerate(sents):
        scored.append((sum(tf.get(w, 0) for w in content_tokens(s)), -i, s))
    scored.sort(key=lambda t: (-t[0], t[1]))
    abstract = [s for _, _, s in scored[:2]]
    first = {}
    for i, w in enumerate(content_tokens(tx["text"])):
        first.setdefault(w, i)
    top = sorted(tf, key=lambda w: (-tf[w], w))[:8]
    # Bloecke: neuer Block vor jedem SPK_02-Satz ausser dem ersten Satz
    words = tx["words"]
    sent_spk = []
    pos = 0
    for s in sents:
        n = len(s.split(" "))
        spks = [w["speaker"] for w in words[pos:pos + n]]
        sent_spk.append(max(set(spks), key=spks.count) if spks else "?")
        pos += n
    bounds, start = [], 0
    for i in range(1, len(sents)):
        if sent_spk[i] == "SPK_02":
            bounds.append((start, i))
            start = i
    bounds.append((start, len(sents)))
    secs = []
    for a, b in bounds:
        block = " ".join(sents[a:b])
        btf = term_freq(block)
        term = max(btf, key=lambda w: (btf[w], w)) if btf else "Block"
        secs.append({"start_sent": a, "end_sent": b, "title": f"Block: {term}"})
    return {"title": title, "abstract": abstract,
            "keywords": top, "sections": secs}
