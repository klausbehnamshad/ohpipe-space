---
title: ohpipe-space
emoji: 📜
colorFrom: gray
colorTo: gray
sdk: gradio
sdk_version: 6.31.0
app_file: app/app.py
python_version: "3.12.12"
pinned: false
---

# ohpipe-space

**KI-gestützter Erschließungsentwurf mit Belegbindung, Nachspielbarkeit und menschlicher Prüfung als öffentliche Demo auf synthetischem Material.**

Gilt für synthetische Fixtures, nichts über echte Interviews. Kein Upload-Pfad: Dieses Repository enthält keine echten Aufnahmen und nimmt keine entgegen. Verantwortung für Daten, Rechte und Freigaben liegt beim Controller.

## Was die Gates beweisen (und was nicht)

- Gate 1: Jeder Claim trägt Text, Art, Status, Zitat und Anker-Hash. Ein Satz-Claim gilt als belegt, wenn sein Text nach NFC-Normierung, LF-Normierung und BOM-Entfernung wörtlich im Transkript steht. Ein Schlagwort gilt als belegt, wenn es als ganzes Wort vorkommt, Groß- und Kleinschreibung egal. Wortposition, Zeit und Stimme stehen in den Fixtures, die App gibt sie im Claim noch nicht aus (Folgeauftrag S3). Beweist nicht, dass die Aussage inhaltlich stimmt.
- Gate 2: Gleicher Stand erzeugt bytegleiche Bundles. Nach einem geänderten Eingangs-Hash werden `proposal` und `decision` als STALE markiert, `register` und `note` bleiben gültig. Beweist keine fachliche Richtigkeit und keine modellübergreifende Determiniertheit.
- Gate 3: Der Dev-Läufer prüft Goldfelder mit Review gegen den mitgelieferten IMM-Core-1.2.0-TAP zu IMM-Core 1.2.0; die App erzeugt und prüft keinen DCTAP-Datensatz. `consent_status` und `accessRights` setzt nur der Mensch im Review, nie die Maschine. Beweist nichts über echte Interviews.
- Anker-Gate: Sieben Mutantenfälle werden live gerechnet. `format_nfd` prüft gleiche Zeichen in anderer Unicode-Normierung. `format_crlf` prüft Windows-Zeilenenden. `format_bom` prüft eine Datei mit BOM-Markierung. `inspan_negation` prüft einen verneinten Zusatz im belegten Bereich. `outspan_greeting` prüft einen Begrüßungstausch außerhalb des Bereichs. `outspan_speaker_labels` prüft einen Sprecherwechsel außerhalb des Bereichs. `degenerate_junk` prüft fremden Text ohne Bezug an der Untergrenze.

## Stand

Phase 2 ist in `main` gemergt (`d5bca36`). Der erste öffentliche Space-Stand zeigt den Fixture-Modus.

## Space

Die App zeigt die drei Gates an eingefrorenen Dev-Fixtures. Leitsatz auf jedem Reiter: „Gilt für synthetische Fixtures, nichts über echte Interviews.“

- Betriebsarten (`OHPIPE_SPACE_MODE`, sonst automatisch): `fixture` (öffentlicher Start, S1, vorberechnete Kandidat-Entwürfe, keine Anmeldung, kein Tageslimit), `cpu` (lokaler Rauchtest mit Qwen2.5-0.5B-Instruct), `zerogpu` (S2, Qwen2.5-7B-Instruct bf16, Modellladung auf Modulebene, `@spaces.GPU(duration=45)`, 512 Ausgabetokens). Nur `zerogpu` nutzt GPU. `zerogpu` braucht `hf_oauth: true` im Frontmatter und eine eigene Freigabe.
- Limits je UTC-Tag, nur in den Modellmodi: 2 Entwürfe anonym (je Session und UTC-Tag), 3 angemeldet (OAuth per Frontmatter, `LoginButton`). Der `LoginButton` erscheint nur auf dem Space. Lokal und in CI gilt die anonyme Grenze. Darüber und bei Quota-Fehler liefert die App den vorberechneten Entwurf mit Etikett `vorberechnet (Kandidat), Entwurfs-Hash …`. Die Tageszähler sind nicht persistent: Neustart und Datumswechsel setzen sie zurück. Der Fixture-Modus zählt nicht.
- Reiter: Entwurf (Claims mit Status, Anker-Hash, Zitat; `consent_status` und `accessRights` leer, nur im Review), Anker-Gate (sieben Mutanten live gerechnet), Replay/STALE (Journal mit vier Ereignissen, zwei Replays, STALE-Markierung, Manipulationserkennung).
- Queue `max_size=5`, `concurrency_limit=1`.
- HF-Quoten (Doku, abgerufen 7.11.2026, `docs/hf-zerogpu-2026-11-07.md`): GPU-Tagesquote unangemeldet 2 Minuten, Gratis-Konto 5 Minuten, Reset 24 Stunden nach der ersten GPU-Nutzung.

## Prüfen

Alle Befehle laufen aus der Repo-Wurzel mit einer Python-3.12.12-Umgebung, in der `requirements-ci.txt` installiert ist.

```sh
OHPIPE_SPACE_MODE=fixture python -B eval/run_gates.py --split dev
```

Erwartet: neun Zeilen `PASS`, letzte Zeile `PASS harness:alpha: alpha=0.6429`, Exit 0.

```sh
python -B eval/spec_freeze.py
```

Erwartet: `OK: prereg.json stimmt (Schwellen, 3 Hashes, Spec-Hash)`, Exit 0.

```sh
OHPIPE_SPACE_MODE=fixture python -B -m unittest discover -s app -t app -p 'test_*.py'
```

Erwartet: `OK`, mehr als 10 Tests, darunter die Hash-Fälle und der Fixture-Modus-Test, Exit 0.

```sh
python -B app/check_precomputed.py
```

Erwartet: `precomputed ok: 2 Dateien, Hash gespeichert und ausgeliefert gültig (de_001, en_001), keine Review-Felder`, Exit 0.

```sh
PYTHON=python bash eval/space_check.sh
```

Erwartet: letzte Zeile `3 Reiter grün, STALE-Demo ok`, Exit 0. `PYTHON` zeigt auf das Python der Prüf-Umgebung.

```sh
H=$(mktemp -d); HF_HOME=$H HF_HUB_OFFLINE=1 SYSTEM=spaces SPACE_ID=klausbehnamshad/ohpipe-space OHPIPE_SPACE_MODE=fixture PYTHON=python bash eval/space_check.sh; ls -A $H | wc -l
```

Erwartet: wie der Aufruf davor, danach `0`.

Eigener Prüfweg `deploy-check` für die vollständigen Pins auf Linux: Auslöser `workflow_dispatch` und `push` mit Pfadfilter auf `README.md`, `requirements.txt`, `requirements-ci.txt`, `app/**`, `eval/**`, `fixtures/**` und die Workflow-Datei. Job `linux-full-pins` auf `ubuntu-24.04` mit Python `3.12.12`, danach `python -m pip install -r requirements.txt`, `python -m pip check` (erwartet `No broken requirements found.`), `pip freeze`, Dev-Läufer, Spec-Prüfung, Unit-Suite, Precomputed-Prüfung und Space-ähnlicher Offline-Start mit leerem `HF_HOME`. Die Dateien `install.log`, `pip-freeze.txt` und die `space_check`-Ausgabe werden als Artefakt `deploy-check-3.12.12` hochgeladen, auch bei Fehlschlag.

## Aufbau

- `fixtures/dev/`: eingefrorene synthetische Sets (Transkript, Wort-zu-Stimme mit Zeitquelle, Gold mit Review-Status, Hashes); Audio nur als Release-Asset oder LFS.
- `fixtures/manifest.json`: SHA-256 je Fixture-Datei.
- `eval/`: Gate-Läufer, Mutationssuite, Metriken, α-Harness, Präregistrierung, `space_check.sh` für die drei Reiter.
- `app/`: Gradio-App mit drei Reitern (Entwurf, Anker-Gate, Replay/STALE). `draft.py` mit den Modi `fixture`, `cpu` und `zerogpu`, Hash-Prüfung der vorberechneten Entwürfe in `precomputed/`, Etikett mit Entwurfs-Hash. `limits.py` mit Tageszähler je Besucher. Tests mit `test_*.py`.

## Verwandte Repos

ohpipe (Pipeline, Journal), ohpipe-mini-windows (lokale Kette, diar2_merge), DINOH (Evaluation), DigQDA (Methodenverträge), anchorprobe (Text-Anker), dh-provenance-journal (Ereignisketten), imm-core (Metadatenmodell), AegisQDA (PII-Gate), relational-justice-analysis (Reliabilität).

## Zitieren

Siehe [CITATION.cff](CITATION.cff). Nach Phase 3: Zenodo-DOI über das GitHub-Release dieses Repos.
