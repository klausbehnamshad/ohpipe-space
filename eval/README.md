# Eval-Harness (Phase 1)

`python eval/run_gates.py --split dev` prüft drei Gates auf den Dev-Fixtures.
`--split heldout` meldet SKIP, bis die zurückgehaltene Testmenge vorliegt.

## Leiter

trivial (Baseline: erster Satz, erste Wörter, gleiche Drittel) <
Kandidat (TF-Regeln, Sprecherblöcke) < Modell (Phase 2, Qwen-Entwurf).
Die +0,10-F1-Schwelle gilt in Phase 1 Kandidat-gegen-trivial,
in Phase 2 Modell-gegen-Kandidat.

## Festlegungen mit Objektbezug

- Wortanker sind case-insensitiv (ganzes Token), Satzanker exakt.
  Keywords sind freie Strings (IMM-Core ohne kontrolliertes Vokabular);
  kontrollierte Felder (Datum, Sprache, accessRights) werden exakt geprüft.
- Formatmutanten (NFD, CRLF, BOM) werden kanonisch absorbiert (Robustheit,
  STA-Profil). Inhaltsänderungen brechen den Hash.
- Der α-Harness prüft nominales Krippendorff-α auf einem festen
  Testpaar (0,6429); Gold-Gate α ≥ 0,80 läuft auf der Testmenge.
- `spec_freeze.py` schreibt `prereg.json` (Schwellen, Hashes, Datum).
