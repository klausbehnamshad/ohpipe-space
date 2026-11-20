"""Unit-Test fuer draft._run_generation (nur stdlib).

Der Generierungslauf muss den input_ids-Tensor ans Modell geben, nicht
das Dict aus apply_chat_template, und beim Dekodieren genau die
Prompt-Laenge ueberspringen.
"""
import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from draft import _run_generation


class FakeIDs:
    shape = (1, 7)
    moved = None

    def to(self, device):
        self.moved = device
        return self


class FakeOut:
    def __init__(self):
        self.slices = []

    def __getitem__(self, index):
        assert index == 0
        parent = self

        class Row:
            def __getitem__(self, sl):
                parent.slices.append(sl)
                return "GEN"

        return Row()


class FakeModel:
    def __init__(self):
        self.seen = None
        self.kwargs = None

    def generate(self, input_ids, **kwargs):
        self.seen = input_ids
        self.kwargs = kwargs
        return FakeOut()


class FakeTokenizer:
    eos_token_id = 0

    def __init__(self):
        self.ids = FakeIDs()
        self.decoded = None

    def apply_chat_template(self, messages, **kwargs):
        return {"input_ids": self.ids}

    def decode(self, tokens, **kwargs):
        self.decoded = tokens
        return "TEXT"


class RunGenerationTest(unittest.TestCase):
    def test_generate_bekommt_tensor(self):
        tok, model = FakeTokenizer(), FakeModel()
        text = _run_generation(tok, model, "Hallo", 256)
        self.assertIs(model.seen, tok.ids)
        self.assertEqual(text, "TEXT")
        self.assertEqual(tok.decoded, "GEN")

    def test_decode_ueberspringt_prompt(self):
        tok, model = FakeTokenizer(), FakeModel()
        out = FakeOut()
        model.generate = lambda input_ids, **kw: out
        _run_generation(tok, model, "Hallo", 256)
        self.assertEqual(out.slices, [slice(7, None, None)])

    def test_device_wird_angewendet(self):
        tok, model = FakeTokenizer(), FakeModel()
        _run_generation(tok, model, "Hallo", 256, device="cuda")
        self.assertEqual(tok.ids.moved, "cuda")


class ClaimEntryTest(unittest.TestCase):
    def test_leerer_claim_ist_unbelegt(self):
        from draft import anchor_raw_draft
        out = anchor_raw_draft({"title": "", "abstract": [""],
                                "keywords": [""],
                                "sections": [{"start_sent": 0,
                                              "end_sent": 1,
                                              "title": "x"}]},
                               "Guten Tag.", 1)
        self.assertTrue(out["claims"])
        for claim in out["claims"]:
            self.assertEqual(claim["status"], "unbelegt")


class DraftPartTest(unittest.TestCase):
    def test_string_wird_liste(self):
        from draft import anchor_raw_draft, draft_part_of
        raw = {"title": "Titel", "abstract": "[0-4]", "keywords": "[5]",
               "sections": [{"start_sent": 0, "end_sent": 1,
                             "title": "x"}]}
        anchored = anchor_raw_draft(raw, "Titel.", 1)
        part = draft_part_of(raw, anchored["sections"])
        self.assertEqual(part["abstract"], ["[0-4]"])
        self.assertEqual(part["keywords"], ["[5]"])

    def test_null_wird_leer(self):
        from draft import anchor_raw_draft, draft_part_of
        raw = {"title": "Titel", "abstract": None, "keywords": None,
               "sections": []}
        anchored = anchor_raw_draft(raw, "Titel.", 1)
        part = draft_part_of(raw, anchored["sections"])
        self.assertEqual(part["abstract"], [])
        self.assertEqual(part["keywords"], [])
        self.assertEqual(part["title"], "Titel")


class PrecomputedHashTest(unittest.TestCase):
    def _read_precomputed(self, fid):
        import json
        pre = Path(__file__).resolve().parent / "precomputed"
        return json.loads((pre / f"{fid}.json").read_text(encoding="utf-8"))

    def test_ausgelieferter_hash_stimmt(self):
        import json
        import draft
        for fid in ("de_001", "en_001"):
            out = draft.draft(fid, "fixture")
            rest = {k: v for k, v in out.items() if k != "bundle_hash"}
            body = json.dumps(rest, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False).encode("utf-8")
            import hashlib
            self.assertEqual(out["bundle_hash"],
                             hashlib.sha256(body).hexdigest())

    def _manipulierte_kopie(self, tmpdir):
        import json
        src = self._read_precomputed("de_001")
        src["claims"][0]["text"] = src["claims"][0]["text"] + " X"
        tmp = Path(tmpdir)
        (tmp / "de_001.json").write_text(json.dumps(src),
                                         encoding="utf-8")
        (tmp / "en_001.json").write_text(
            (Path(__file__).resolve().parent / "precomputed"
             / "en_001.json").read_text(encoding="utf-8"),
            encoding="utf-8")
        return src

    def test_manipuliert_scheitert_load(self):
        import tempfile
        import draft
        with tempfile.TemporaryDirectory() as tmp:
            self._manipulierte_kopie(tmp)
            with self.assertRaises(draft.PrecomputedHashError):
                draft.load_precomputed("de_001",
                                       root=Path(tmp))

    def test_manipuliert_scheitert_draft_mit_patch(self):
        import json
        import tempfile
        import draft
        with tempfile.TemporaryDirectory() as tmp:
            kopie = self._manipulierte_kopie(tmp)
            erwartet = {k: v for k, v in kopie.items()
                        if k != "bundle_hash"}
            aufrufe = []
            original = draft._bundle_hash

            def wrapper(obj):
                aufrufe.append(obj)
                return original(obj)

            altes_pre = draft.PRE
            draft.PRE = Path(tmp)
            draft._bundle_hash = wrapper
            try:
                with self.assertRaises(draft.PrecomputedHashError):
                    draft.draft("de_001", "fixture")
            finally:
                draft.PRE = altes_pre
                draft._bundle_hash = original
            self.assertEqual(len(aufrufe), 1)
            self.assertEqual(aufrufe[0], erwartet)

    def test_ohne_hash_scheitert(self):
        import json
        import tempfile
        import draft
        with tempfile.TemporaryDirectory() as tmp:
            src = self._read_precomputed("de_001")
            src.pop("bundle_hash", None)
            tmp = Path(tmp)
            (tmp / "de_001.json").write_text(json.dumps(src),
                                            encoding="utf-8")
            with self.assertRaises(draft.PrecomputedHashError):
                draft.load_precomputed("de_001", root=tmp)


if __name__ == "__main__":
    unittest.main()
