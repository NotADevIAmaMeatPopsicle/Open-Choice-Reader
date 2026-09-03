"""Verify relative Markdown links in the proposed public tree."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
INLINE_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def markdown_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def main() -> int:
    broken: list[str] = []
    files = markdown_files()
    for markdown_file in files:
        content = markdown_file.read_text(encoding="utf-8")
        for match in INLINE_LINK.finditer(content):
            target = match.group(1).strip().strip("<>")
            if target.startswith(("#", "/", "http://", "https://", "mailto:")):
                continue
            relative_target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if relative_target and not (markdown_file.parent / relative_target).exists():
                broken.append(f"{markdown_file.relative_to(ROOT).as_posix()} -> {target}")

    if broken:
        print("Broken relative Markdown links:")
        for finding in broken:
            print(f"  {finding}")
        return 1

    print(f"Markdown links verified across {len(files)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
