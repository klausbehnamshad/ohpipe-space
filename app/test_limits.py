"""Unit-Test fuer app/limits.py (nur stdlib)."""
import sys
import threading
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import limits


class LimitsTest(unittest.TestCase):
    def setUp(self):
        limits.reset()

    def test_anon_zwei_dann_stopp(self):
        ident, authed = limits.identity_of("sess1", "1.2.3.4")
        self.assertFalse(authed)
        self.assertTrue(limits.check_and_consume(ident, authed)[0])
        self.assertTrue(limits.check_and_consume(ident, authed)[0])
        ok, used, limit = limits.check_and_consume(ident, authed)
        self.assertFalse(ok)
        self.assertEqual((used, limit), (2, 2))

    def test_angemeldet_drei_dann_stopp(self):
        ident, authed = limits.identity_of("sess1", "1.2.3.4",
                                           username="klaus")
        self.assertTrue(authed)
        for _ in range(3):
            self.assertTrue(limits.check_and_consume(ident, authed)[0])
        ok, used, limit = limits.check_and_consume(ident, authed)
        self.assertFalse(ok)
        self.assertEqual((used, limit), (3, 3))

    def test_datumswechsel_setzt_zurueck(self):
        ident, _ = limits.identity_of("sess1", "1.2.3.4")
        real = limits._today
        try:
            limits._today = lambda: "2026-11-07"
            self.assertTrue(limits.check_and_consume(ident, False)[0])
            self.assertTrue(limits.check_and_consume(ident, False)[0])
            self.assertFalse(limits.check_and_consume(ident, False)[0])
            limits._today = lambda: "2026-11-08"
            self.assertTrue(limits.check_and_consume(ident, False)[0])
        finally:
            limits._today = real

    def test_threads_verlieren_nichts(self):
        ident, _ = limits.identity_of("sess1", "1.2.3.4")
        results = []
        def worker():
            results.append(limits.check_and_consume(ident, False)[0])
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sum(results), 2)


if __name__ == "__main__":
    unittest.main()
