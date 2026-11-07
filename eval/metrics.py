"""Gate-3-Metriken: Mengen-F1, Pk, WindowDiff, DCTAP-Check, Krippendorff-alpha (nominal)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

REQUIRED = ["record_id", "interview_date", "interviewer", "consent_status",
            "accessRights", "title", "language"]
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
LANG_RE = re.compile(r"^[a-z]{3}$")
ACCESS_ENUM = {"open", "restricted", "closed"}


def set_scores(gold, pred):
    g, p = set(gold), set(pred)
    tp = len(g & p)
    prec = tp / len(p) if p else 0.0
    rec = tp / len(g) if g else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"precision": round(prec, 4), "recall": round(rec, 4),
            "f1": round(f1, 4)}


def cuts_from_sections(sections, n):
    return {s["end_sent"] for s in sections if 0 < s["end_sent"] < n}


def _pk_wd(ref_cuts, hyp_cuts, n, k, diff):
    if n - k < 1:
        return 0.0
    bad, total = 0, 0
    for i in range(1, n - k + 1):
        win = set(range(i, i + k))
        r = len(ref_cuts & win) > 0
        h = len(hyp_cuts & win) > 0
        if diff:
            same = (len(ref_cuts & win) == len(hyp_cuts & win))
        else:
            same = (r == h)
        bad += 0 if same else 1
        total += 1
    return round(bad / total, 4) if total else 0.0


def segmentation_scores(gold_sections, hyp_sections, n_sent):
    gold_cuts = cuts_from_sections(gold_sections, n_sent)
    hyp_cuts = cuts_from_sections(hyp_sections, n_sent)
    avg = sum(s["end_sent"] - s["start_sent"] for s in gold_sections)
    avg = avg / len(gold_sections) if gold_sections else n_sent
    k = max(1, round(avg / 2))
    eq = n_sent // 3
    trivial_eq = {eq, 2 * eq} & set(range(1, n_sent))
    return {
        "pk": _pk_wd(gold_cuts, hyp_cuts, n_sent, k, False),
        "windiff": _pk_wd(gold_cuts, hyp_cuts, n_sent, k, True),
        "pk_trivial_eq": _pk_wd(gold_cuts, trivial_eq, n_sent, k, False),
        "windiff_trivial_eq": _pk_wd(gold_cuts, trivial_eq, n_sent, k, True),
        "pk_trivial_none": _pk_wd(gold_cuts, set(), n_sent, k, False),
        "windiff_trivial_none": _pk_wd(gold_cuts, set(), n_sent, k, True),
        "k": k,
    }


def dctap_check(record):
    missing = [f for f in REQUIRED if not record.get(f)]
    errors = []
    if record.get("interview_date") and not DATE_RE.match(record["interview_date"]):
        errors.append("interview_date")
    if record.get("language") and not LANG_RE.match(record["language"]):
        errors.append("language")
    if record.get("accessRights") and record["accessRights"] not in ACCESS_ENUM:
        errors.append("accessRights")
    return {"missing": missing, "errors": errors,
            "valid": not missing and not errors}


def krippendorff_alpha_nominal(coder_a, coder_b):
    """Alpha nominal fuer zwei vollstaendige Kodierungen gleicher Units."""
    assert len(coder_a) == len(coder_b) and coder_a
    coinc = defaultdict(Counter)
    for a, b in zip(coder_a, coder_b):
        coinc[a][b] += 1
        coinc[b][a] += 1
    total = sum(sum(c.values()) for c in coinc.values())
    values = list(coinc)
    n_c = {v: sum(coinc[v].values()) for v in values}
    do = sum(coinc[a][b] for a in values for b in values
             if a != b) / total
    de = sum(n_c[a] * n_c[b] for a in values for b in values
             if a != b) / (total * (total - 1))
    if de == 0:
        return 1.0
    return round(1 - do / de, 4)
