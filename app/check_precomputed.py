"""Prueft die vorberechneten Entwuerfe (Schritt 5, ohne GPU)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
FORBIDDEN = ("consent_status", "accessRights")


def _find_forbidden(node, path=""):
    hits = []
    if isinstance(node, dict):
        for key, val in node.items():
            here = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN:
                hits.append(here)
            hits.extend(_find_forbidden(val, here))
    elif isinstance(node, list):
        for i, val in enumerate(node):
            hits.extend(_find_forbidden(val, f"{path}[{i}]"))
    return hits


def main(argv: list | None = None) -> int:
    import sys
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))
    from draft import PrecomputedHashError, _bundle_hash, draft, load_precomputed

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(APP_DIR / "precomputed"))
    args = parser.parse_args(argv)
    root = Path(args.root)
    is_default = root.resolve() == (APP_DIR / "precomputed").resolve()
    files = sorted(root.glob("*.json"))
    if len(files) != 2:
        print(f"precomputed FAIL: {len(files)} Dateien, erwartet 2")
        return 1
    for path in files:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"precomputed FAIL: {path.name} nicht lesbar "
                  f"({type(exc).__name__})")
            return 1
        try:
            body = json.loads(raw)
        except ValueError as exc:
            print(f"precomputed FAIL: {path.name} nicht lesbar "
                  f"({type(exc).__name__})")
            return 1
        try:
            load_precomputed(path.stem, root=root)
        except PrecomputedHashError:
            print(f"precomputed FAIL: {path.name} "
                  f"gespeicherter Hash stimmt nicht")
            return 1
        hits = _find_forbidden(body)
        if hits:
            print(f"precomputed FAIL: {path.name} enthaelt Review-Feld: "
                  f"{hits[0]}")
            return 1
    if is_default:
        for path in files:
            fid = path.stem
            try:
                out = draft(fid, "fixture")
            except PrecomputedHashError:
                print(f"precomputed FAIL: {path.name} "
                      f"gespeicherter Hash stimmt nicht")
                return 1
            if out.get("mode") != "fixture":
                print(f"precomputed FAIL: {path.name} Modus falsch")
                return 1
            label = out.get("label", "")
            if "vorberechnet" not in label or "Entwurfs-Hash" not in label:
                print(f"precomputed FAIL: {path.name} Etikett falsch")
                return 1
            rest = {k: v for k, v in out.items() if k != "bundle_hash"}
            if out.get("bundle_hash") != _bundle_hash(rest):
                print(f"precomputed FAIL: {path.name} "
                      f"ausgelieferter Hash stimmt nicht")
                return 1
    print("precomputed ok: 2 Dateien, Hash gespeichert und ausgeliefert "
          "gültig (de_001, en_001), keine Review-Felder")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
