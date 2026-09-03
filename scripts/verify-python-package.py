"""Inspect built Python archives without extracting them."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


DENIED_PARTS = {".git", "__pycache__", "alembic", "data", "tests"}
DENIED_SUFFIXES = {
    ".db",
    ".flac",
    ".key",
    ".log",
    ".mp3",
    ".ogg",
    ".onnx",
    ".pem",
    ".sqlite",
    ".sqlite3",
    ".wav",
}


def unsafe_name(raw_name: str) -> bool:
    path = PurePosixPath(raw_name.replace("\\", "/"))
    parts_lower = {part.lower() for part in path.parts}
    name_lower = path.name.lower()
    return bool(
        parts_lower & DENIED_PARTS
        or name_lower.startswith(".env")
        or path.suffix.lower() in DENIED_SUFFIXES
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_directory", type=Path)
    args = parser.parse_args()

    wheels = sorted(args.archive_directory.glob("*.whl"))
    sdists = sorted(args.archive_directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        parser.error("expected exactly one wheel and one .tar.gz source archive")

    entries: list[str] = []
    unsafe: list[str] = []

    with zipfile.ZipFile(wheels[0]) as archive:
        wheel_entries = archive.namelist()
        entries.extend(wheel_entries)
        unsafe.extend(f"{wheels[0].name}: {name}" for name in wheel_entries if unsafe_name(name))

    with tarfile.open(sdists[0], mode="r:gz") as archive:
        for member in archive.getmembers():
            entries.append(member.name)
            if member.issym() or member.islnk() or unsafe_name(member.name):
                unsafe.append(f"{sdists[0].name}: {member.name}")

    if not any(PurePosixPath(name).as_posix().endswith("/app/main.py") or name == "app/main.py" for name in entries):
        unsafe.append("package is missing app/main.py")
    if not any(name.endswith(".dist-info/licenses/LICENSE") for name in wheel_entries):
        unsafe.append("wheel is missing its Apache-2.0 LICENSE file")
    if not any(PurePosixPath(name).name == "LICENSE" for name in entries):
        unsafe.append("source archive is missing its Apache-2.0 LICENSE file")

    if unsafe:
        print("Unsafe or incomplete Python package contents:")
        for finding in unsafe:
            print(f"  {finding}")
        return 1

    print(f"Python package verified: {len(entries)} entries across wheel and sdist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
