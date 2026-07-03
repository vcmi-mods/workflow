#!/usr/bin/env python3
"""
Shared helpers for mod metadata (name / description) translation handling.

Used by:
  - migrate_description.py  (one-time split of legacy description.md -> description/<lang>.md)
  - export_mod_metadata.py  (write mod.<id>.name / .description keys into Weblate source english.json)
  - inject_mod_metadata.py  (fold translated name/description into published mod.json at release time)

Mod layout (case-insensitive on disk, VCMI is case-insensitive):
  <root>/mod.json                       top-level mod
  <root>/Mods/<sub>/mod.json            submod
  <root>/Mods/<sub>/Mods/<sub2>/...     nested submods (recursive)
  <mod>/content/translation/<lang>.json in-game strings (also our name/description keys)
  <mod>/description/<lang>.md            extended per-language description

Mod "segments" are the lower-cased mod directory names below each Mods/ level.
The top-level mod has no segments. Metadata keys are:
  mod.name / mod.description                 (top-level)
  mod.<sub>.name / mod.<sub>.description     (submod)
  mod.<sub>.<sub2>.name / ...                (nested)
"""

import jstyleson
from pathlib import Path
from typing import Optional

# Language identifiers, lower-case, as defined in vcmi lib/texts/Languages.h.
# Order does not matter here; callers that match by substring sort by length
# descending so e.g. "tchinese" wins over "chinese".
LANGUAGES = [
    "belarusian", "bulgarian", "czech", "chinese", "tchinese", "dutch",
    "english", "filipino", "finnish", "french", "german", "greek",
    "hungarian", "italian", "japanese", "korean", "latvian", "norwegian",
    "polish", "portuguese", "romanian", "russian", "serbian", "spanish",
    "swedish", "turkish", "ukrainian", "vietnamese",
]


def child_ci(directory: Path, name: str) -> Optional[Path]:
    """Return child entry of `directory` whose name matches `name` case-insensitively."""
    if not directory.is_dir():
        return None
    lowered = name.lower()
    for entry in directory.iterdir():
        if entry.name.lower() == lowered:
            return entry
    return None


def mod_json_path(mod_dir: Path) -> Optional[Path]:
    """Return the mod.json inside `mod_dir`, case-insensitive, or None."""
    return child_ci(mod_dir, "mod.json")


def translation_dir(mod_dir: Path) -> Optional[Path]:
    """Return <mod>/content/translation directory if it exists (case-insensitive)."""
    content = child_ci(mod_dir, "content")
    if content is None:
        return None
    return child_ci(content, "translation")


def description_dir(mod_dir: Path) -> Optional[Path]:
    """Return <mod>/description directory if it exists (case-insensitive)."""
    return child_ci(mod_dir, "description")


def description_md(mod_dir: Path, language: str) -> Optional[Path]:
    """Return <mod>/description/<language>.md if it exists (case-insensitive)."""
    desc = description_dir(mod_dir)
    if desc is None:
        return None
    return child_ci(desc, language + ".md")


def find_mods(root: Path):
    """
    Recursively discover the top-level mod and all (nested) submods.

    Returns list of (mod_dir, segments) where segments is the list of lower-cased
    submod directory names; the top-level mod has an empty segments list.
    """
    result = []

    def visit(directory: Path, segments):
        if mod_json_path(directory) is None:
            return
        result.append((directory, segments))
        mods = child_ci(directory, "Mods")
        if mods is None:
            return
        for sub in sorted(mods.iterdir(), key=lambda p: p.name.lower()):
            if sub.is_dir():
                visit(sub, segments + [sub.name.lower()])

    visit(root, [])
    return result


def metadata_key(segments, field: str) -> str:
    """Build the english.json key for a mod's metadata field ('name' / 'description')."""
    return ".".join(["mod"] + list(segments) + [field])


def load_jsonc(path: Path) -> dict:
    """Load JSON-with-comments (mod.json) or strict JSON (translation files)."""
    return jstyleson.loads(path.read_text(encoding="utf-8"))


def detect_language(heading: str) -> Optional[str]:
    """
    Find the language identifier referenced by a markdown heading line.

    Language ids in real description.md files are guaranteed lower-case. We match
    the longest identifier first so "tchinese" is not shadowed by "chinese".
    """
    lowered = heading.lower()
    for lang in sorted(LANGUAGES, key=len, reverse=True):
        if lang in lowered:
            return lang
    return None
