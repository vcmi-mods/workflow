#!/usr/bin/env python3
"""
Write release-specific metadata into the PUBLISHED top-level mod.json.

Runs in the package job after the release ZIP is built (its size is needed) and before
mod.json is uploaded. These keys describe the download itself and are read by the
Launcher via getRepositoryValue, so they only need to live in the uploaded mod.json,
not inside the packaged ZIP.

Fields written:
  download      release asset URL of the packaged ZIP
  downloadSize  ZIP size in MiB (float, matches getDownloadSizeMegabytes)
  screenshots   raw URLs of every image in the top-level screenshots/ dir (if any)
  githubStars   stargazer count of this repository (omitted if unknown)
  updateDate    UTC timestamp, ISO 8601 "YYYY-MM-DDThh:mm:ssZ"

updateDate is UTC on purpose: std::get_time(&tm, "%Y-%m-%dT%H:%M:%SZ") + timegm parses
it trivially, and comparing against std::time(nullptr) needs no timezone handling.

Usage: inject_release_metadata.py [--root .]
"""

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from mod_metadata_common import child_ci, load_jsonc, mod_json_path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def megabytes(num_bytes: int) -> float:
    return round(num_bytes / (1024 * 1024), 2)


def download_url(repository: str, tag: str, asset: str) -> str:
    return f"https://github.com/{repository}/releases/download/{tag}/{asset}"


def screenshot_urls(root: Path, repository: str, sha: str) -> list:
    directory = child_ci(root, "screenshots")
    if directory is None:
        return []
    files = [e for e in directory.iterdir() if e.is_file() and e.suffix.lower() in IMAGE_SUFFIXES]
    return [
        f"https://raw.githubusercontent.com/{repository}/{sha}/{directory.name}/{e.name}"
        for e in sorted(files, key=lambda p: p.name.lower())
    ]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def version_at_least(ref_name: str, major: int, minor: int) -> bool:
    """True if ref_name is vcmi-<major>.<minor> or newer (numeric compare, so 1.10 > 1.8)."""
    match = re.match(r"vcmi-(\d+)\.(\d+)", ref_name)
    if match is None:
        return False
    return (int(match.group(1)), int(match.group(2))) >= (major, minor)


def run(root: Path) -> None:
    repository = os.environ["GITHUB_REPOSITORY"]          # owner/repo
    ref_name = os.environ["GITHUB_REF_NAME"]              # vcmi-1.8
    sha = os.environ["GITHUB_SHA"]
    repo = repository.split("/")[-1]
    tag = ref_name.removeprefix("vcmi-")                  # 1.8 - matches release tag
    asset = f"{repo}-{ref_name}.zip"

    zip_path = root / "dist" / asset
    config = load_jsonc(mod_json_path(root))

    config["download"] = download_url(repository, tag, asset)
    config["downloadSize"] = megabytes(zip_path.stat().st_size)

    # updateDate is a 1.8+ feature; 1.7 and older releases omit it.
    if version_at_least(ref_name, 1, 8):
        config["updateDate"] = utc_now()
    else:
        config.pop("updateDate", None)

    screenshots = screenshot_urls(root, repository, sha)
    if screenshots:
        config["screenshots"] = screenshots

    stars = os.environ.get("GITHUB_STARS", "").strip()
    if stars.isdigit():
        config["githubStars"] = int(stars)

    mod_json_path(root).write_text(
        json.dumps(config, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
    )
    print(f"wrote release metadata into {mod_json_path(root)}")


def selfcheck() -> None:
    assert megabytes(1024 * 1024) == 1.0
    assert megabytes(1572864) == 1.5
    assert download_url("vcmi-mods/foo", "1.8", "foo-vcmi-1.8.zip") == (
        "https://github.com/vcmi-mods/foo/releases/download/1.8/foo-vcmi-1.8.zip"
    )
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", utc_now())
    assert version_at_least("vcmi-1.8", 1, 8)
    assert version_at_least("vcmi-1.9", 1, 8)
    assert version_at_least("vcmi-1.10", 1, 8)  # numeric, not string, compare
    assert version_at_least("vcmi-2.0", 1, 8)
    assert not version_at_least("vcmi-1.7", 1, 8)
    assert not version_at_least("vcmi-1.0", 1, 8)
    assert not version_at_least("nonsense", 1, 8)
    print("selfcheck ok")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--selfcheck", action="store_true")
    args = parser.parse_args()
    if args.selfcheck:
        selfcheck()
    else:
        run(Path(args.root))
