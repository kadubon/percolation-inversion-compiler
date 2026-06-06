"""Fail when publishable files contain local paths or obvious secret markers."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    ".git",
    "uv.lock",
}
PUBLISH_SUFFIXES = {
    ".cff",
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
PATTERNS = [
    re.compile(r"C:\\Users\\", re.IGNORECASE),
    re.compile(r"/home/[^/\s]+"),
    re.compile(r"Desktop\\Downloads", re.IGNORECASE),
    re.compile(
        r"(api[_-]?key|secret|password|private[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}",
        re.IGNORECASE,
    ),
    re.compile(r"bearer\s+[A-Za-z0-9_./+=-]{16,}", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?" + r"PRIVATE" + r" KEY-----"),
]


def publishable_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "check_publish_safety.py":
            continue
        if any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix in PUBLISH_SUFFIXES:
            files.append(path)
    return files


def main() -> int:
    failures: list[str] = []
    for path in publishable_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in PATTERNS:
            if pattern.search(text):
                failures.append(f"{path.relative_to(ROOT)} matched {pattern.pattern}")
    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
