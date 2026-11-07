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


if __name__ == "__main__":
    unittest.main()
