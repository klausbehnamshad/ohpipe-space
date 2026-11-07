#!/bin/sh
# Prueft die drei Reiter der App im Fixture-Modus (ohne GPU).
# Erwartet: letzte Zeile `3 Reiter grün, STALE-Demo ok`, Exit 0.
set -u
REPO="$(dirname "$0")/.."
PORT="${PORT:-7861}"
APP_PID=""

cleanup() {
  if [ -n "$APP_PID" ]; then
    kill "$APP_PID" 2>/dev/null
    wait "$APP_PID" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

OHPIPE_SPACE_MODE=fixture PORT="$PORT" python3 "$REPO/app/app.py" > /tmp/space_check_app.log 2>&1 &
APP_PID="$!"

i=0
while [ "$i" -lt 60 ]; do
  if curl -sf "http://127.0.0.1:$PORT/config" > /dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 1
done
if ! curl -sf "http://127.0.0.1:$PORT/config" > /dev/null 2>&1; then
  echo "space_check FAIL: App antwortet nicht auf Port $PORT"
  sed -n '1,20p' /tmp/space_check_app.log
  exit 1
fi

SPACE_CHECK_PORT="$PORT" python3 - <<'EOF'
import os
from gradio_client import Client

port = os.environ["SPACE_CHECK_PORT"]
c = Client(f"http://127.0.0.1:{port}")
fails = []


def rows_of(value, headers):
    if isinstance(value, dict) and "data" in value:
        heads = value.get("headers") or headers
        return heads, value["data"]
    if isinstance(value, list):
        return headers, value
    raise AssertionError(f"unerwartete Tabellenform: {type(value)}")


# Reiter 1: Entwurf
table, bundle, label = c.predict("de_001", api_name="/draft")
heads, rows = rows_of(table, ["Claim", "Art", "Status", "Anker-Hash",
                              "Zitatzeuge"])
try:
    sidx = heads.index("Status")
except ValueError:
    sidx = 2
if "vorberechnet" not in label:
    fails.append(f"Entwurf ohne Etikett vorberechnet: {label!r:.80}")
claims = bundle.get("claims", [])
if not claims or any(x.get("status") != "belegt" for x in claims):
    fails.append("Entwurf enthaelt Claim ohne Status belegt")
if len(rows) != len(claims) or any(r[sidx] != "belegt" for r in rows):
    fails.append("Tabelle zeigt nicht alle Claims als belegt")

# Reiter 2: Anker-Gate
gtable, summary = c.predict("de_001", api_name="/anchor_gate")
gheads, grows = rows_of(gtable, ["Name", "Klasse", "erwartet", "beobachtet",
                                 "Treffer"])
names = [r[0] for r in grows]
want = ["format_nfd", "format_crlf", "format_bom", "inspan_negation",
        "outspan_greeting", "outspan_speaker_labels", "degenerate_junk"]
if names != want:
    fails.append(f"Mutantennamen abweichend: {names}")
try:
    tidx = (gheads or []).index("Treffer")
except ValueError:
    tidx = 4
if any(r[tidx] != "ja" for r in grows):
    fails.append("Mutantentabelle ohne vollen Treffer")

# Reiter 3: Replay/STALE
rep = c.predict(api_name="/replay")
if not rep.get("gleich"):
    fails.append("Replay nicht bytegleich")
got = {e["kind"]: e["stale"] for e in rep.get("stale", [])}
if got != {"register": False, "proposal": True, "note": False,
           "decision": True}:
    fails.append(f"STALE-Menge falsch: {got}")
if not rep.get("manipulation_erkannt"):
    fails.append("Manipulation unerkannt")

if fails:
    for f in fails:
        print(f"space_check FAIL: {f}")
    raise SystemExit(1)
print("3 Reiter grün, STALE-Demo ok")
EOF
