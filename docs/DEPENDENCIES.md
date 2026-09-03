# Dependency and license review

Open Choice Reader uses Python packages for its API, document processing, and speech engines, plus npm packages for its web interface. Dependencies are installed from their upstream package registries and are not vendored into this repository or its Python archives.

## Direct runtime dependencies

| Package | Scope | Declared license | Purpose |
| --- | --- | --- | --- |
| `alembic` | base | MIT | Database migrations |
| `fastapi` | base | MIT | HTTP API framework |
| `httpx` | base | BSD | Bounded remote HTTP requests |
| `pydantic`, `pydantic-settings` | base | MIT | Validation and configuration |
| `piper-tts` | base | GPL-3.0-or-later | Default local speech engine |
| `pwdlib[argon2]` | base | MIT | Password hashing |
| `pypdf` | base | BSD-3-Clause | PDF text extraction |
| `soundfile` | base | BSD | Audio-file handling |
| `sqlalchemy` | base | MIT | Database access |
| `trafilatura` | base | Apache-2.0 | Article extraction |
| `uvicorn[standard]` | base | BSD-3-Clause | ASGI server |
| `python-multipart` | base | Apache-2.0 | Upload parsing |
| `faster-whisper` | optional | MIT | Voice-reference transcription |
| `kokoro-onnx` | optional | MIT in its upstream repository | Optional speech engine |
| `qwen-tts` | optional | Apache-2.0 | Optional voice-cloning engine |
| `react`, `react-dom` | web runtime | MIT | Browser interface |

The frontend development tree currently resolves packages declaring MIT-family, BSD, Apache-2.0, MPL-2.0, ISC, CC0-1.0, and BlueOak-1.0.0 licenses. The exact versions and transitive package set are recorded in `frontend/package-lock.json`; Python versions are resolved within the bounds in `backend/pyproject.toml`.

## Copyleft and model notice

Open Choice Reader's original source is licensed under Apache-2.0. Apache-2.0 is compatible with GPLv3, but `piper-tts` remains GPL-3.0-or-later and is not relicensed by this project. Anyone distributing an installation or bundle that combines these components must review and satisfy the GPL terms that apply to that distribution.

Downloaded speech models and voices are separate works with their own model cards, licenses, and usage terms. They are excluded from Git and from the Python package. A source-code license does not grant rights to redistribute those files or a person's voice sample.

This inventory is an engineering aid, not legal advice. Verify package and model terms again before distributing a binary, container, model bundle, or hosted service.

## Verification

At the 2026-09-02 release-candidate review:

- `npm audit --audit-level=high` reported zero vulnerabilities;
- a candidate-project `pip-audit` reported no known vulnerabilities;
- the Python wheel and source archive passed metadata and denied-content checks; and
- the npm package remains marked `private` and no package release is authorized.

Run the dependency, build, and package checks in `.github/workflows/ci.yml` after every dependency change.
