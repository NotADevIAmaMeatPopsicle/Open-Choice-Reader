"""Fail when the proposed public tree contains an unapproved or unsafe file type."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path, PurePosixPath
import re


ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "public-files.allowlist"

DENIED_PARTS = {
    ".claude",
    ".codex",
    ".idea",
    ".vscode",
    ".worktrees",
    "__pycache__",
    "data",
    "dist",
    "htmlcov",
    "node_modules",
    "output",
    "playwright-report",
    "test-results",
}
DENIED_SUFFIXES = {
    ".7z",
    ".bak",
    ".db",
    ".docx",
    ".epub",
    ".flac",
    ".gz",
    ".key",
    ".log",
    ".m4a",
    ".mp3",
    ".ogg",
    ".onnx",
    ".p12",
    ".pdf",
    ".pem",
    ".pfx",
    ".pt",
    ".pth",
    ".safetensors",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".wav",
    ".webm",
    ".zip",
}
TEXT_SCAN_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yml",
    ".yaml",
}
SENSITIVE_CONTENT_PATTERNS = {
    "absolute Windows user profile path": re.compile(
        rb"(?i)\b[a-z]:[\\/]users[\\/][^\\/\s]+[\\/]"
    ),
    "absolute Unix user home path": re.compile(rb"/(?:home|Users)/[^/\s]+/"),
    "private IPv4 address": re.compile(
        rb"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
        rb"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
    ),
    "private key": re.compile(rb"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GitHub token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "GitLab token": re.compile(rb"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    "Slack token": re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}


def candidate_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return sorted(path for path in result.stdout.decode("utf-8").split("\0") if path)


def allowlist_entries() -> tuple[set[str], tuple[str, ...]]:
    entries = [
        line.strip()
        for line in ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    exact = {entry for entry in entries if not entry.endswith("/")}
    prefixes = tuple(entry for entry in entries if entry.endswith("/"))
    return exact, prefixes


def main() -> int:
    exact, prefixes = allowlist_entries()
    unapproved: list[str] = []
    unsafe: list[str] = []
    sensitive_content: list[str] = []

    for raw_path in candidate_files():
        path = PurePosixPath(raw_path)
        normalized = path.as_posix()
        disk_path = ROOT / Path(*path.parts)

        if normalized not in exact and not normalized.startswith(prefixes):
            unapproved.append(normalized)

        name_lower = path.name.lower()
        parts_lower = {part.lower() for part in path.parts}
        is_example_env = name_lower == ".env.example"
        if (
            parts_lower & DENIED_PARTS
            or any(part.startswith("open_choice_reader_backend-") for part in parts_lower)
            or (name_lower.startswith(".env") and not is_example_env)
            or path.suffix.lower() in DENIED_SUFFIXES
            or disk_path.is_symlink()
        ):
            unsafe.append(normalized)

        if path.suffix.lower() in TEXT_SCAN_SUFFIXES and "tests" not in parts_lower:
            payload = disk_path.read_bytes()
            if b"\0" not in payload:
                for description, pattern in SENSITIVE_CONTENT_PATTERNS.items():
                    if pattern.search(payload):
                        sensitive_content.append(f"{normalized}: {description}")

    if unapproved:
        print("Files outside public-files.allowlist:", file=sys.stderr)
        for path in unapproved:
            print(f"  {path}", file=sys.stderr)
    if unsafe:
        print("Files denied from the public candidate:", file=sys.stderr)
        for path in unsafe:
            print(f"  {path}", file=sys.stderr)
    if sensitive_content:
        print("Potentially sensitive content in public files:", file=sys.stderr)
        for finding in sensitive_content:
            print(f"  {finding}", file=sys.stderr)

    if unapproved or unsafe or sensitive_content:
        return 1

    print(f"Public tree verified: {len(candidate_files())} files match the allowlist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
