"""Offline-Test fuer den Fixture-Modus (nur stdlib plus Gradio).

Startet einen frischen Unterprozess mit Netzsperre ausserhalb von
Loopback und ruft den Entwurfs-Handler je Fixture dreimal auf.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REPO = APP_DIR.parent


class FixtureModeTest(unittest.TestCase):
    def test_fixture_ohne_netz_ohne_zaehler(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            hf_home = Path(tmp) / "hf-home"
            hf_home.mkdir()
            child = Path(tmp) / "kind.py"
            child.write_text(
                "import json, socket, sys\n"
                "abgewiesen = []\n"
                "ECHT_CONNECT = socket.socket.connect\n"
                "ECHT_CREATE = socket.create_connection\n"
                "ERLAUBT = {\"127.0.0.1\", \"::1\", \"localhost\"}\n"
                "def _wirt(address):\n"
                "    try:\n"
                "        return address[0]\n"
                "    except Exception:\n"
                "        return repr(address)\n"
                "def _connect(self, address):\n"
                "    if _wirt(address) not in ERLAUBT:\n"
                "        abgewiesen.append(_wirt(address))\n"
                "        raise OSError(\"Netz gesperrt\")\n"
                "    return ECHT_CONNECT(self, address)\n"
                "def _create(address, *a, **k):\n"
                "    if _wirt(address) not in ERLAUBT:\n"
                "        abgewiesen.append(_wirt(address))\n"
                "        raise OSError(\"Netz gesperrt\")\n"
                "    return ECHT_CREATE(address, *a, **k)\n"
                "socket.socket.connect = _connect\n"
                "socket.create_connection = _create\n"
                "import importlib.util\n"
                "pfad = sys.argv[1]\n"
                "spec = importlib.util.spec_from_file_location(\n"
                "    \"ohpipe_app\", pfad)\n"
                "modul = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(modul)\n"
                "import gradio as gr\n"
                "import limits\n"
                "class Anfrage:\n"
                "    session_hash = \"s-fixture\"\n"
                "    client = None\n"
                "erg = {\"etiketten\": [], \"abgewiesen\": abgewiesen}\n"
                "for fid in (\"de_001\", \"en_001\"):\n"
                "    for _ in range(3):\n"
                "        _, _, _, etikett = modul.entwurf(\n"
                "            fid, Anfrage(), None)\n"
                "        erg[\"etiketten\"].append(etikett)\n"
                "erg[\"counts_leer\"] = (limits._counts == {})\n"
                "erg[\"ohne_torch\"] = (\"torch\" not in sys.modules\n"
                "                       and \"transformers\" not in sys.modules\n"
                "                       and \"spaces\" not in sys.modules)\n"
                "bloecke = getattr(modul.demo, \"blocks\", {}) or {}\n"
                "erg[\"ohne_login\"] = not any(\n"
                "    isinstance(b, gr.LoginButton) for b in bloecke.values())\n"
                "print(\"OHPIPE_RESULT:\" + json.dumps(erg))\n",
                encoding="utf-8")
            umgebung = {k: v for k, v in os.environ.items()
                        if not k.startswith("OAUTH_")}
            umgebung.update({
                "OHPIPE_SPACE_MODE": "fixture",
                "HF_HUB_OFFLINE": "1",
                "HF_HOME": str(hf_home),
                "HF_HUB_CACHE": str(Path(tmp) / "hub-cache"),
                "TRANSFORMERS_CACHE": str(Path(tmp) / "tf-cache"),
                "XDG_CACHE_HOME": str(Path(tmp) / "xdg-cache"),
                "SYSTEM": "spaces",
                "SPACE_ID": "klausbehnamshad/ohpipe-space",
                "GRADIO_ANALYTICS_ENABLED": "False",
            })
            for name in ("HF_HUB_CACHE", "TRANSFORMERS_CACHE",
                         "XDG_CACHE_HOME"):
                Path(umgebung[name]).mkdir(parents=True, exist_ok=True)
            proc = subprocess.run(
                [sys.executable, str(child), str(APP_DIR / "app.py")],
                capture_output=True, text=True, env=umgebung,
                cwd=str(REPO))
            self.assertEqual(proc.returncode, 0, msg=proc.stderr[-4000:])
            zeilen = [z for z in proc.stdout.splitlines()
                      if z.startswith("OHPIPE_RESULT:")]
            self.assertEqual(len(zeilen), 1, msg=proc.stdout[-4000:])
            erg = json.loads(zeilen[0].split(":", 1)[1])
            for etikett in erg["etiketten"]:
                self.assertNotIn("Tageslimit", etikett)
            self.assertTrue(erg["counts_leer"], msg="limits gezaehlt")
            self.assertTrue(erg["ohne_torch"], msg="Modellmodul geladen")
            self.assertTrue(erg["ohne_login"], msg="LoginButton vorhanden")
            self.assertEqual(erg["abgewiesen"], [])
            self.assertEqual(list(hf_home.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
