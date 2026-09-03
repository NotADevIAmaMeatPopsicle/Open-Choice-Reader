# Open Choice Reader

Open Choice Reader is a self-hosted document library and read-aloud application. It imports text, Markdown, HTML, EPUB, and PDF files; supports public-domain catalog and article imports; and can generate speech with local Piper, Kokoro, or Qwen-based voice-cloning runtimes. It is intended for people who want control over their library, audio, and choice of speech engine rather than sending their documents to a hosted reading service.

Open Choice Reader is in its early public-release stage. It currently has no packaged release or published Python or npm package; installation is from source while the project matures.

## Components

- `backend/`: FastAPI API, SQLite data model, document parsing, playback, and export worker
- `frontend/`: React and Vite web interface
- `browser-extension/`: optional Chromium extension for sending pages or selected text to a configured server
- `scripts/`: local development and Windows/WSL host helpers

## Requirements

- Python 3.12 through 3.14
- Node.js 22.12 or newer
- FFmpeg, libsndfile, SoX, and eSpeak NG
- Linux or WSL is recommended for the bundled host scripts

GPU acceleration is optional. Piper is the base text-to-speech engine; Kokoro, transcription, and Qwen voice cloning are optional installations.

The checked-in automation targets Ubuntu/Debian-style Linux or WSL and Windows PowerShell. Other operating systems may work through the manual Python and Node setup, but are not currently covered by project automation.

## Verified quick start on Ubuntu or WSL

From a clean checkout, install the system and application dependencies, build the web interface, and start the loopback-only service:

```bash
bash scripts/bootstrap.sh
(cd frontend && npm run build)
bash scripts/start.sh
```

Open `http://127.0.0.1:8000`, create the first administrator, and use `bash scripts/stop.sh` when finished. The bootstrap downloads a default Piper voice from its upstream source. Review that voice's upstream license before redistributing it.

## Development setup

Create the backend environment and install the application with development dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m alembic upgrade head
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1` instead.

Install the frontend dependencies:

```bash
cd frontend
npm ci
```

Start the development servers on Windows:

```powershell
.\scripts\dev.ps1
```

The frontend runs at `http://127.0.0.1:5173` and proxies API calls to the backend at `http://127.0.0.1:8000`.

## Linux or WSL host setup

The setup script installs system packages, creates `backend/.venv`, installs the base backend, downloads the default Piper voice, and installs frontend dependencies:

```bash
bash scripts/bootstrap.sh
(cd frontend && npm run build)
bash scripts/start.sh
```

Optional engines can be installed by setting `OPEN_CHOICE_READER_EXTRAS` to a comma-separated extras list such as `all`. Set `DOWNLOAD_KOKORO_MODELS=1` to download the default Kokoro model bundle.

The server binds to loopback by default. On Windows, `scripts/start-open-choice-reader.ps1 -Expose` deliberately opens the configured port to the LAN; review [SECURITY.md](SECURITY.md) first.

## Main workflows

- Import local text, Markdown, HTML, EPUB, or PDF documents into a private library.
- Browse supported public-domain catalogs or import a readable article URL.
- Read in the web interface, track progress, and generate local speech or export jobs.
- Install the optional [Chromium extension](browser-extension/README.md) to send a page or selection to the server.
- Add optional speech engines only when their runtime and model requirements suit the host.

## Configuration

Copy `backend/.env.example` to `backend/.env` and change only the settings you need. Environment variables use the `OPEN_CHOICE_READER_` prefix. See [configuration](docs/configuration.md) for deployment guidance.

Initial administrator creation is accepted from localhost only unless `OPEN_CHOICE_READER_AUTH_BOOTSTRAP_TOKEN` is configured. Set secure cookies and HTTPS before allowing access from another machine.

The live HTTP interface is documented by the backend at `/docs` and `/openapi.json`. See the [API overview](docs/api.md) for its scope and compatibility status. There is no standalone command-line client; the repository scripts are development and self-hosting helpers.

## Tests

```bash
cd backend
python -m ruff check app tests
python -m pytest

cd ../frontend
npm test
npm run build

cd ../browser-extension
node --test tests/core.test.mjs
```

## Data and model licensing

Application data, uploaded documents, generated audio, downloaded models, and voice samples are intentionally excluded from Git. Users are responsible for the rights to documents and voice samples they process. Downloaded TTS models and voices retain their own upstream licenses; see [data and privacy](docs/data-and-privacy.md).

## Project status

Open Choice Reader is pre-release software intended for self-hosting. Review the security guidance before exposing it outside a trusted machine or network.

See [CONTRIBUTING.md](CONTRIBUTING.md) for development expectations, [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards, [SECURITY.md](SECURITY.md) for vulnerability-reporting guidance, the [public source manifest](docs/PUBLIC-SOURCE-MANIFEST.md) for the repository boundary, the [release checklist](docs/PUBLIC-RELEASE-CHECKLIST.md) for approval gates, and the [dependency review](docs/DEPENDENCIES.md) for third-party terms.

Open Choice Reader's original source is licensed under the [Apache License 2.0](LICENSE). Third-party packages, downloaded models, and voice files retain their own licenses. In particular, the base `piper-tts` dependency declares GPL-3.0-or-later; review the dependency guidance before redistributing a combined installation.
