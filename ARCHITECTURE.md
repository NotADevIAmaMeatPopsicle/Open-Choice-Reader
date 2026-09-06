# Architecture

Open Choice Reader is a single-host web application with four cooperating parts.

## Runtime components

1. **React frontend**: the browser interface under `frontend/src`. A production build is served by the backend from `frontend/dist`.
2. **FastAPI backend**: authentication, document import, library queries, playback sessions, settings, themes, sharing, and export APIs under `backend/app`.
3. **SQLite and local files**: structured state lives in SQLite; documents, covers, voice references, generated audio, and exports live below the configured storage root.
4. **Export worker**: `backend/app/worker` claims queued jobs from SQLite, generates chunk audio, and writes downloadable WAV artifacts.

The optional Chromium extension calls the same authenticated HTTP API to import a page or selected text.

## Main data flow

An import request is authenticated, bounded by request and format-specific limits, parsed into sections and chunks, and stored in the current user's namespace. Reader sessions request speech for one chunk at a time; generated audio is cached per user. Export jobs reuse that speech pipeline and place final artifacts below a user- and job-specific export directory.

Remote imports resolve and pin public IP addresses, reject private-network destinations by default, revalidate redirects, and enforce download size and total-time limits.

## Storage layout

With the default `backend/data` root, user-owned files follow this shape:

```text
data/
  open_choice_reader.db
  models/
  users/<USER_ID>/
    source/
    covers/
    cache/
    exports/job-<JOB_ID>/
    inbox/
    voices/
```

The application creates private directory and file permissions on POSIX hosts. Per-user storage and active-export limits prevent unbounded persistent growth. Operators still need filesystem-level backups and access controls.

## Code map

- `backend/app/api`: HTTP routes and authorization boundaries
- `backend/app/models`: SQLAlchemy persistence models
- `backend/app/parsers`: bounded TXT, Markdown, HTML, EPUB, and PDF parsing
- `backend/app/services`: business rules, imports, storage, playback, security, and integrations
- `backend/app/tts`: Piper, Kokoro, and Qwen adapters
- `backend/app/worker`: export job execution
- `backend/alembic`: schema migrations
- `frontend/src/components`: reusable interface components
- `frontend/src/routes`: application pages
- `frontend/src/api`: typed backend client
- `browser-extension`: Manifest V3 extension and its tests

## Trust boundary

The supported default is a trusted self-hosted machine or private network. Session cookies protect user operations; unsafe cross-origin mutations are rejected, remote fetches are constrained, and user artifacts are namespaced. Open Choice Reader is not an internet-scale identity provider or a replacement for a hardened reverse proxy. See [SECURITY.md](SECURITY.md) and [docs/configuration.md](docs/configuration.md).
