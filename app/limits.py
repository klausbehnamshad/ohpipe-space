"""Tageslimit je Besucher (Speicher, UTC-Tag, Lock).

Identitaet ist bei angemeldeten Besuchern der OAuth-Nutzername, sonst
Session-Hash plus Client-IP aus dem Request. Grenze angemeldet 3 je
UTC-Tag, anonym 2 je Session und UTC-Tag. Der Zaehler ist nicht
persistent: Beim Datumswechsel beginnt er bei 0, ein Neustart setzt
ihn ebenfalls zurueck. Beides steht in der Doku.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone

LIMIT_ANON = 2
LIMIT_AUTH = 3

_lock = threading.Lock()
_counts: dict = {}


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def identity_of(session_hash: str = "", client_ip: str = "",
                username: str | None = None):
    if username:
        return f"user:{username}", True
    return f"anon:{session_hash}:{client_ip}", False


def check_and_consume(identity: str, authenticated: bool):
    limit = LIMIT_AUTH if authenticated else LIMIT_ANON
    key = (_today(), identity)
    with _lock:
        used = _counts.get(key, 0)
        if used >= limit:
            return False, used, limit
        _counts[key] = used + 1
        return True, used + 1, limit


def reset() -> None:
    with _lock:
        _counts.clear()
