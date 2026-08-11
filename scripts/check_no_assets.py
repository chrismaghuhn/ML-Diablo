#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {
    "diabdat.mpq",
    "spawn.mpq",
    "hellfire.mpq",
    "hfmonk.mpq",
    "hfmusic.mpq",
    "hfvoice.mpq",
}
FORBIDDEN_SUFFIXES = {
    ".mpq",
    ".sv",
    ".dsv",
    ".hsv",
    ".wav",
    ".mp3",
    ".ogg",
    ".flac",
    ".avi",
    ".mp4",
    ".mov",
}
ALLOWED_BINARY_SUFFIXES = {".png"}  # none are expected, but diagrams may be added later
MAX_NORMAL_FILE_BYTES = 5 * 1024 * 1024


def main() -> int:
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".venv" in path.parts:
            continue
        relative = path.relative_to(ROOT)
        lowered = path.name.lower()
        suffix = path.suffix.lower()
        if lowered in FORBIDDEN_NAMES or suffix in FORBIDDEN_SUFFIXES:
            violations.append(f"forbidden asset-like file: {relative}")
        if path.stat().st_size > MAX_NORMAL_FILE_BYTES and suffix not in ALLOWED_BINARY_SUFFIXES:
            violations.append(f"unexpected large file ({path.stat().st_size} bytes): {relative}")
    if violations:
        raise SystemExit("\n".join(violations))
    print("asset boundary OK: no forbidden Diablo/game-media files found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
