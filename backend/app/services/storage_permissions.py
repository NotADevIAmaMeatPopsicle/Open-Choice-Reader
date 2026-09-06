import os
from pathlib import Path


def ensure_private_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        directory.chmod(0o700)
    return directory


def ensure_private_file(path: str | Path) -> Path:
    file_path = Path(path)
    if os.name == "posix" and file_path.is_file():
        file_path.chmod(0o600)
    return file_path
