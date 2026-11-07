---
title: ohpipe-space
emoji: 📜
colorFrom: gray
colorTo: gray
sdk: gradio
sdk_version: 6.31.0
app_file: app/app.py
hf_oauth: true
pinned: false
---

# ohpipe-space

**KI-gestützter Erschließungsentwurf mit Belegbindung, Nachspielbarkeit und menschlicher Prüfung – als öffentliche Demo auf synthetischem Material.**

Gilt für synthetische Fixtures, nichts über echte Interviews. Kein Upload-Pfad: Dieses Repository enthält keine echten Aufnahmen und nimmt keine entgegen. Verantwortung für Daten, Rechte und Freigaben liegt beim Controller.

## Was die Gates beweisen (und was nicht)

- Gate 1: Jede Aussage zeigt auf eine Wortspanne mit Zeit und Stimme – oder bleibt `unbelegt`. Beweist nicht, dass die Aussage inhaltlich stimmt.
- Gate 2: Gleicher Stand erzeugt bytegleiche Bundles; geänderte Eingänge werden STALE markiert. Beweist keine fachliche Richtigkeit und keine modellübergreifende Determiniertheit.
- Gate 3: Aus belegtem Transkript entsteht ein DCTAP-valider Metadatenentwurf (IMM-Core 1.2.0); `consent_status` und `accessRights` setzt nur der Mensch im Review, nie die Maschine. Beweist nichts über echte Interviews.

## Stand

Phase 2: Gradio-App mit drei Reitern im Repo (Branch `phase2-app`). Der Space-Deploy folgt nach Abnahme durch die Regie.

## Space

Die App zeigt die drei Gates an eingefrorenen Dev-Fixtures. Leitsatz auf jedem Reiter: „Gilt für synthetische Fixtures, nichts über echte Interviews.“

- Betriebsarten (`OHPIPE_SPACE_MODE`, sonst automatisch): `fixture` (Standard ohne GPU, vorberechnete Kandidat-Entwürfe), `cpu` (Rauchtest mit Qwen2.5-0.5B-Instruct), `zerogpu` (Space, Qwen2.5-7B-Instruct bf16, Modellladung auf Modulebene, `@spaces.GPU(duration=45)`, 512 Ausgabetokens). Nur `zerogpu` nutzt GPU.
- Limits je UTC-Tag: 2 Entwürfe anonym (je Session), 3 angemeldet (OAuth per Frontmatter, `LoginButton`). Der LoginButton erscheint nur auf dem Space; lokal und in CI gilt die anonyme Grenze. Darüber und bei Quota-Fehler liefert die App den vorberechneten Entwurf mit Etikett „vorberechnet, Hash …“. Die Tageszähler sind nicht persistent: Neustart und Datumswechsel setzen sie zurück.
- Reiter: Entwurf (Claims mit Status, Anker-Hash, Zitatzeuge; `consent_status` und `accessRights` leer, nur im Review), Anker-Gate (sieben Mutanten live gerechnet), Replay/STALE (Journal mit vier Ereignissen, zwei Replays, STALE-Markierung, Manipulationserkennung).
- Queue `max_size=5`, `concurrency_limit=1`.
- HF-Quoten (Doku, abgerufen 7.11.2026, `docs/hf-zerogpu-2026-11-07.md`): 2 ZeroGPU-Spaces gratis, nur Gradio; Tagesquote unangemeldet 2 Minuten, gratis 5 Minuten; Aufrufdauer Standard 60 Sekunden.

## Prüfen

```sh
python3 eval/run_gates.py --split dev
python3 eval/spec_freeze.py
bash eval/space_check.sh
python3 -m unittest app/test_draft.py app/test_limits.py
python3 app/check_precomputed.py
OHPIPE_SPACE_MODE=cpu python3 app/smoke.py
```

## Aufbau

- `fixtures/dev/` – eingefrorene synthetische Sets (Transkript, Wort-zu-Stimme mit Zeitquelle, Gold mit Review-Status, Hashes); Audio nur als Release-Asset oder LFS.
- `fixtures/manifest.json` – SHA-256 je Fixture-Datei.
- `eval/` – Gate-Läufer, Mutationssuite, Metriken, α-Harness, Präregistrierung.
- `app/` – folgt in Phase 2 (Gradio, 3 Reiter).

## Prüfen

```sh
python3 eval/run_gates.py --split dev
python3 eval/spec_freeze.py
```

## Verwandte Repos

ohpipe (Pipeline, Journal), ohpipe-mini-windows (lokale Kette, diar2_merge), DINOH (Evaluation), DigQDA (Methodenverträge), anchorprobe (Text-Anker), dh-provenance-journal (Ereignisketten), imm-core (Metadatenmodell), AegisQDA (PII-Gate), relational-justice-analysis (Reliabilität).

## Zitieren

Siehe [CITATION.cff](CITATION.cff). Nach Phase 3: Zenodo-DOI über das GitHub-Release dieses Repos.
