#!/usr/bin/env python3
"""
Export mod name/description into the Weblate source english.json.

For the top-level mod and every (nested) submod, writes metadata keys into the
TOP-LEVEL mod's content/translation/english.json (submod strings aggregate into
the main mod's translation, matching VCMI's in-game export):

  mod.<id>.name        always (from that mod's mod.json "name")
  mod.<id>.description  only if that mod has NO description/english.md
                        (when present, the .md is the authoritative source and is
                         translated as its own per-language component instead)

Runs after the in-game english.json has been regenerated, before it is committed
as the Weblate source. Creates english.json if the mod has no in-game strings yet.

Usage: export_mod_metadata.py [--root .]
"""

import argparse
from pathlib import Path

from mod_metadata_common import (
    description_md,
    find_mods,
    load_jsonc,
    metadata_key,
    mod_json_path,
    translation_dir,
    write_json,
)


def english_json_path(root: Path) -> Path:
    """Path to the top-level mod's english.json, resolving existing dirs case-insensitively."""
    tdir = translation_dir(root)
    if tdir is not None:
        existing = next((p for p in tdir.iterdir() if p.name.lower() == "english.json"), None)
        if existing is not None:
            return existing
        return tdir / "english.json"
    return root / "content" / "translation" / "english.json"


def run(root: Path) -> None:
    target = english_json_path(root)
    strings = load_jsonc(target) if target.exists() else {}

    for mod_dir, segments in find_mods(root):
        config = load_jsonc(mod_json_path(mod_dir))

        name = config.get("name")
        if isinstance(name, str) and name:
            strings[metadata_key(segments, "name")] = name

        # description.md (now description/english.md) is authoritative when present
        if description_md(mod_dir, "english") is None:
            description = config.get("description")
            if isinstance(description, str) and description:
                strings[metadata_key(segments, "description")] = description

    target.parent.mkdir(parents=True, exist_ok=True)
    write_json(target, strings)
    print(f"wrote {len(strings)} entries to {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    run(Path(args.root))
