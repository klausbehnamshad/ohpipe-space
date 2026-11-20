#!/bin/sh
# Prueft die drei Reiter der App im Fixture-Modus (ohne GPU).
# Erwartet: letzte Zeile `3 Reiter grün, STALE-Demo ok`, Exit 0.
set -u
REPO="$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
APP_PID=""
LOG="$(mktemp "${TMPDIR:-/tmp}/space_check.XXXXXX")"
if [ -n "${PORT:-}" ]; then
  PORT="$PORT"
else
  PORT="$("$PYTHON" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
fi
case "$PORT" in
  ''|*[!0-9]*)
    echo "space_check FAIL: kein freier Port bestimmbar"
    echo "space_check: Log $LOG"
    exit 1
    ;;
esac

fail() {
  echo "space_check FAIL: $1"
  echo "space_check: Log $LOG"
  exit 1
}

cleanup() {
  if [ -n "$APP_PID" ]; then
    kill "$APP_PID" 2>/dev/null
    wait "$APP_PID" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

check_listener() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -a -p "$APP_PID" -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -q "pid=$APP_PID,"
    return $?
  fi
  echo "space_check FAIL: weder lsof noch ss vorhanden"
  echo "space_check: Log $LOG"
  exit 1
}

# Vorbedingung: Port muss frei sein.
if curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$PORT/config" 2>/dev/null; then
  echo "space_check FAIL: Port $PORT schon belegt"
  echo "space_check: Log $LOG"
  exit 1
fi
if ! "$PYTHON" -c 'import socket, sys; s = socket.socket(); s.bind(("127.0.0.1", int(sys.argv[1])))' "$PORT" 2>/dev/null; then
  echo "space_check FAIL: Port $PORT schon belegt"
  echo "space_check: Log $LOG"
  exit 1
fi

export GRADIO_SERVER_NAME=127.0.0.1
export OHPIPE_SPACE_MODE=fixture
export PORT="$PORT"
"$PYTHON" "$REPO/app/app.py" > "$LOG" 2>&1 &
APP_PID="$!"

echo "space_check: PID $APP_PID, Port $PORT, Log $LOG"

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
  echo "space_check: Log $LOG"
  exit 1
fi

if check_listener; then
  echo "space_check: Listener gehört PID $APP_PID"
else
  echo "space_check FAIL: Listener auf Port $PORT gehört nicht PID $APP_PID"
  echo "space_check: Log $LOG"
  exit 1
fi

SPACE_CHECK_PORT="$PORT" "$PYTHON" - <<'EOF'
import hashlib
import json
import os
from gradio_client import Client

port = os.environ["SPACE_CHECK_PORT"]
c = Client(f"http://127.0.0.1:{port}")
fails = []
oks = []


def rows_of(value, headers):
    if isinstance(value, dict) and "data" in value:
        heads = value.get("headers") or headers
        return heads, value["data"]
    if isinstance(value, list):
        return headers, value
    raise AssertionError(f"unerwartete Tabellenform: {type(value)}")


def canon(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


for fid in ("de_001", "en_001"):
    table, bundle, meta, label = c.predict(fid, api_name="/draft")
    heads, rows = rows_of(table, ["Claim", "Art", "Status", "Anker-Hash",
                                  "Zitatzeuge"])
    try:
        sidx = heads.index("Status")
    except ValueError:
        sidx = 2
    if "vorberechnet" not in label or "Entwurfs-Hash" not in label:
        fails.append(f"Entwurf ohne Etikett vorberechnet/Entwurfs-Hash "
                     f"({fid}): {label!r:.80}")
    claims = bundle.get("claims", [])
    if not claims or any(x.get("status") != "belegt" for x in claims):
        fails.append(f"Entwurf enthaelt Claim ohne Status belegt ({fid})")
    if len(rows) != len(claims) or any(r[sidx] != "belegt" for r in rows):
        fails.append(f"Tabelle zeigt nicht alle Claims als belegt ({fid})")
    if meta.get("consent_status") != "" or meta.get("accessRights") != "":
        fails.append(f"Review-Feld befuellt ({fid})")
    rest = {k: v for k, v in bundle.items() if k != "bundle_hash"}
    if bundle.get("bundle_hash") != hashlib.sha256(canon(rest)).hexdigest():
        fails.append(f"Bundle-Hash falsch ({fid})")
    else:
        oks.append(f"space_check: Hash ok {fid} "
                   f"{bundle['bundle_hash'][:12]}")

for fid in ("de_001", "en_001"):
    gtable, summary = c.predict(fid, api_name="/anchor_gate")
    gheads, grows = rows_of(gtable, ["Name", "Klasse", "erwartet",
                                     "beobachtet", "Treffer"])
    names = [r[0] for r in grows]
    want = ["format_nfd", "format_crlf", "format_bom", "inspan_negation",
            "outspan_greeting", "outspan_speaker_labels", "degenerate_junk"]
    if names != want:
        fails.append(f"Mutantennamen abweichend ({fid}): {names}")
    try:
        tidx = (gheads or []).index("Treffer")
    except ValueError:
        tidx = 4
    if any(r[tidx] != "ja" for r in grows):
        fails.append(f"Mutantentabelle ohne vollen Treffer ({fid})")
    if summary.get("treffer") != "7/7":
        fails.append(f"Anker-Gate Zusammenfassung falsch ({fid}): "
                     f"{summary.get('treffer')}")
    else:
        oks.append(f"space_check: Anker-Gate 7/7 {fid}")

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
for line in oks:
    print(line)
EOF
CLIENT_EXIT="$?"
if [ "$CLIENT_EXIT" -ne 0 ]; then
  echo "space_check: Log $LOG"
  exit "$CLIENT_EXIT"
fi

if check_listener; then
  echo "space_check: Listener gehört PID $APP_PID"
else
  echo "space_check FAIL: Listener auf Port $PORT gehört nicht PID $APP_PID"
  echo "space_check: Log $LOG"
  exit 1
fi

kill "$APP_PID" 2>/dev/null
wait "$APP_PID" 2>/dev/null
APP_PID=""

if curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$PORT/config" 2>/dev/null; then
  echo "space_check FAIL: Port $PORT nach Ende noch belegt"
  echo "space_check: Log $LOG"
  exit 1
fi
echo "space_check: Port nach Ende frei"
rm -f "$LOG"
echo "3 Reiter grün, STALE-Demo ok"
