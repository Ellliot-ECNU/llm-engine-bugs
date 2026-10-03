#!/usr/bin/env python3
"""Regenerate SHA256SUMS for every published artifact file."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "SHA256SUMS"
EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}


def is_published_file(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        path.is_file()
        and path != OUTPUT
        and not any(part in EXCLUDED_DIRS for part in relative.parts)
        and path.suffix not in {".pyc", ".pyo"}
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    paths = sorted(path for path in ROOT.rglob("*") if is_published_file(path))
    lines = [f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}" for path in paths]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} for {len(paths)} files")


if __name__ == "__main__":
    main()
