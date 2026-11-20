"""Unit-Test fuer check_precomputed --root (nur stdlib)."""
import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import check_precomputed


class CheckPrecomputedRootTest(unittest.TestCase):
    def test_manipuliert_liefert_1(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            src = json.loads((APP_DIR / "precomputed" / "de_001.json")
                             .read_text(encoding="utf-8"))
            src["claims"][0]["text"] = src["claims"][0]["text"] + " X"
            Path(tmp, "de_001.json").write_text(json.dumps(src),
                                                encoding="utf-8")
            Path(tmp, "en_001.json").write_text(
                (APP_DIR / "precomputed" / "en_001.json")
                .read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(check_precomputed.main(["--root", tmp]), 1)

    def test_standard_liefert_0(self):
        self.assertEqual(check_precomputed.main([]), 0)


if __name__ == "__main__":
    unittest.main()
