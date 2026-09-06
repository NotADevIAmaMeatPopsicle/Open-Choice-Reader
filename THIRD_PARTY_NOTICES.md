# Third-party notices

Open Choice Reader installs Python and npm dependencies from their upstream registries. No dependency source trees, model weights, downloaded voices, generated audio, or user documents are vendored in this repository.

## Direct runtime dependencies

| Package | Scope | Declared license | Purpose |
| --- | --- | --- | --- |
| `alembic` | base | MIT | Database migrations |
| `fastapi` | base | MIT | HTTP API framework |
| `httpx` | base | BSD-3-Clause | Bounded remote requests |
| `pydantic`, `pydantic-settings` | base | MIT | Validation and configuration |
| `piper-tts` | base | GPL-3.0-or-later | Default local speech engine |
| `pwdlib[argon2]` | base | MIT | Password hashing |
| `pypdf` | base | BSD-3-Clause | PDF text extraction |
| `python-multipart` | base | Apache-2.0 | Upload parsing |
| `soundfile` | base | BSD-3-Clause | Audio-file inspection |
| `sqlalchemy` | base | MIT | Database access |
| `trafilatura` | base | Apache-2.0 | Article extraction |
| `uvicorn[standard]` | base | BSD-3-Clause | ASGI server |
| `faster-whisper` | optional | MIT | Voice-reference transcription |
| `kokoro-onnx` | optional | MIT | Optional speech engine |
| `qwen-tts` | optional | Apache-2.0 | Optional voice-cloning engine |
| `react`, `react-dom` | web runtime | MIT | Browser interface |

The exact frontend versions and transitive packages are recorded in `frontend/package-lock.json`. Python dependency bounds are declared in `backend/pyproject.toml`.

During the 2026-09-06 release-candidate review, the locked frontend dependency tree declared only MIT, MIT-0, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, CC0-1.0, and BlueOak-1.0.0 licenses. `npm audit --audit-level=high` and `pip-audit` reported no known vulnerabilities in the tested base development installation.

## Copyleft and model notice

Open Choice Reader's original source is Apache-2.0. Apache-2.0 is GPLv3-compatible, but `piper-tts` remains GPL-3.0-or-later and is not relicensed by this project. Anyone distributing a combined installation or binary must review and satisfy the terms that apply to that distribution.

Downloaded models and voices are separate works with their own model cards, licenses, and usage terms. The project license does not grant rights to redistribute those files or another person's voice sample.

This notice is an engineering inventory, not legal advice. Recheck package and model terms before distributing a binary, container, model bundle, or hosted service.
