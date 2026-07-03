#!/usr/bin/env python3
"""
Wire up translation files into mod.json (committed to git).

For every non-Translation mod and submod, scans its content/translation directory
and, for each <lang>.json other than english.json, ensures mod.json contains

  "<lang>": { ..., "translations": ["translation/<lang>.json"] }

so the game actually loads that translation. Existing language blocks and any
existing "translations" reference are left untouched. Translation-type mods
(modType == "Translation") are skipped - they apply via their own "language" field.

Runs in the format-json job before Prettier, so the result is committed alongside
the re-exported translations and reformatted JSON.

Usage: wire_translations.py [--root .]
"""

import argparse
import json
from pathlib import Path

from mod_metadata_common import find_mods, iter_language_files, load_jsonc, mod_json_path


def wire_mod(mod_dir: Path) -> None:
    path = mod_json_path(mod_dir)
    config = load_jsonc(path)

    if config.get("modType") == "Translation":
        return

    changed = False
    for language, _entry in iter_language_files(mod_dir):
        block = config.get(language)
        if not isinstance(block, dict):
            block = {}
        if "translations" not in block:
            block["translations"] = [f"translation/{language}.json"]
            changed = True
        config[language] = block

    if changed:
        # Prettier reformats mod.json afterwards, so plain dump is fine here.
        path.write_text(
            json.dumps(config, ensure_ascii=False, indent="\t", separators=(",", " : "))
            + "\n",
            encoding="utf-8",
        )
        print(f"wired translations into {path}")


def run(root: Path) -> None:
    for mod_dir, _segments in find_mods(root):
        wire_mod(mod_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    run(Path(args.root))
