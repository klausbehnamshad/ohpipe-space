# ohpipe-space

**KI-gestützter Erschließungsentwurf mit Belegbindung, Nachspielbarkeit und menschlicher Prüfung – als öffentliche Demo auf synthetischem Material.**

Gilt für synthetische Fixtures, nichts über echte Interviews. Kein Upload-Pfad: Dieses Repository enthält keine echten Aufnahmen und nimmt keine entgegen. Verantwortung für Daten, Rechte und Freigaben liegt beim Controller.

## Was die Gates beweisen (und was nicht)

- Gate 1: Jede Aussage zeigt auf eine Wortspanne mit Zeit und Stimme – oder bleibt `unbelegt`. Beweist nicht, dass die Aussage inhaltlich stimmt.
- Gate 2: Gleicher Stand erzeugt bytegleiche Bundles; geänderte Eingänge werden STALE markiert. Beweist keine fachliche Richtigkeit und keine modellübergreifende Determiniertheit.
- Gate 3: Aus belegtem Transkript entsteht ein DCTAP-valider Metadatenentwurf (IMM-Core 1.2.0); `consent_status` und `accessRights` setzt nur der Mensch im Review, nie die Maschine. Beweist nichts über echte Interviews.

## Stand

Phase 1: Fixtures, Eval-Harness und Präregistrierung. App und Space folgen in Phase 2.

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
