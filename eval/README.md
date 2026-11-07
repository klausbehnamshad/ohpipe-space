# Eval-Harness (Phase 1)

`python eval/run_gates.py --split dev` prüft drei Gates auf den Dev-Fixtures.
`--split heldout` meldet SKIP, bis die zurückgehaltene Testmenge vorliegt.

## Leiter

trivial (Baseline: erster Satz, erste fünf Inhaltswörter, gleiche Drittel,
keine Statistik) < Kandidat (TF-Regeln, Sprecherblöcke) <
Modell (Phase 2, Qwen-Entwurf). Der Phase-1-Vergleich Kandidat-gegen-trivial
ist absichtlich schwach (Baseline trifft auf beiden Dev-Fixtures kein
Gold-Keyword, F1 0,00); der tragende Vergleich Modell-gegen-Kandidat kommt in
Phase 2. Die +0,10-Schwelle gilt für beide Stufen.

## Festlegungen mit Objektbezug

- Wortanker sind case-insensitiv (ganzes Token), Satzanker exakt.
  Keywords sind freie Strings (IMM-Core ohne kontrolliertes Vokabular);
  kontrollierte Felder (Datum, Sprache, accessRights) werden exakt geprüft.
- Formatmutanten (NFD, CRLF, BOM) werden kanonisch absorbiert (Robustheit,
  STA-Profil). Inhaltsänderungen brechen den Hash.
- Der α-Harness prüft nominales Krippendorff-α auf einem festen
  Testpaar (0,6429); Gold-Gate α ≥ 0,80 läuft auf der Testmenge.
- `spec_freeze.py` prüft `prereg.json` (Standard; Schreiben nur mit `--write`).
- Pflichtfelder, Muster und Enums stammen aus `vendor/imm_core_tap_core.csv`
  (tap/core.csv aus imm-core 1.2.0, CC-BY-4.0, © Klaus Behnam Shad).
