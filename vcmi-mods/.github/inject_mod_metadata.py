#!/usr/bin/env python3
"""
Fold translated mod name/description into the PUBLISHED mod.json at release time.

Runs in the release/package job (fresh checkout, never committed back to git), before
content/ is zipped away. For the top-level mod and every (nested) submod it writes
per-language blocks into that mod's mod.json:

  <lang>.name         <- translated mod.<id>.name from the top-level <lang>.json
  <lang>.description  <- description/<lang>.md if present, else translated
                         mod.<id>.description from the top-level <lang>.json

English: name and short description already live in mod.json root, so only the
extended english description (description/english.md), when present, is injected.

The Launcher then reads these via ModDescription::getLocalizedValue / getLocalizedDescription
with no source changes - for installed mods from this mod.json, and for repository mods
from the index which embeds it.

Usage: inject_mod_metadata.py [--root .]
"""

import argparse
import json
from pathlib import Path

from mod_metadata_common import (
    LANGUAGES,
    description_md,
    find_mods,
    load_jsonc,
    metadata_key,
    mod_json_path,
    translation_dir,
)


def read_md(path: Path) -> str:
    return path.read_text(encoding="utf-8").rstrip("\n") + "\n"


def load_translations(root: Path) -> dict:
    """Load every top-level content/translation/<lang>.json keyed by language."""
    tdir = translation_dir(root)
    translations = {}
    if tdir is not None:
        for entry in tdir.iterdir():
            lower = entry.name.lower()
            if lower.endswith(".json"):
                language = lower[: -len(".json")]
                if language in LANGUAGES:
                    translations[language] = load_jsonc(entry)
    return translations


def inject_mod(mod_dir: Path, segments, translations: dict) -> None:
    config = load_jsonc(mod_json_path(mod_dir))
    name_key = metadata_key(segments, "name")
    desc_key = metadata_key(segments, "description")

    languages = set(translations)
    languages.update(lang for lang in LANGUAGES if description_md(mod_dir, lang) is not None)

    changed = False
    for language in sorted(languages):
        block = config.get(language)
        if not isinstance(block, dict):
            block = {}

        if language != "english":
            name = translations.get(language, {}).get(name_key)
            if isinstance(name, str) and name:
                block["name"] = name
                changed = True

        md = description_md(mod_dir, language)
        if md is not None:
            block["description"] = read_md(md)
            changed = True
        elif language != "english":
            description = translations.get(language, {}).get(desc_key)
            if isinstance(description, str) and description:
                block["description"] = description
                changed = True

        if block:
            config[language] = block

    if changed:
        mod_json_path(mod_dir).write_text(
            json.dumps(config, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
        )
        print(f"injected metadata into {mod_json_path(mod_dir)}")


def run(root: Path) -> None:
    translations = load_translations(root)
    for mod_dir, segments in find_mods(root):
        inject_mod(mod_dir, segments, translations)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    run(Path(args.root))
