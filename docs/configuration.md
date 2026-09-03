# Configuration

Backend settings are loaded from environment variables beginning with `OPEN_CHOICE_READER_`. When the backend starts from the `backend` directory, it also reads `backend/.env`.

The checked-in `backend/.env.example` contains the supported security, storage, CORS, and upload-limit settings. Never commit the populated `.env` file.

Every backend setting in `backend/app/config.py` has a corresponding entry in `.env.example`. Boolean values use `true` or `false`; byte and time limits are integer values unless the example contains a decimal. `OPEN_CHOICE_READER_FRONTEND_DIST_ROOT` points to the built web interface, and `OPEN_CHOICE_READER_AUTH_SESSION_COOKIE_NAME` changes only the session cookie's name.

Remote metadata, cover images, documents, and audio are downloaded with separate size limits. Remote URLs are restricted to public HTTP(S) addresses by default; private-network access requires the explicit `OPEN_CHOICE_READER_REMOTE_FETCH_ALLOW_PRIVATE_HOSTS=true` override. Keep that override disabled on any server used by people you do not fully trust.

EPUB parsing has separate limits for archive entry count, individual expanded members, total expanded bytes, and compression ratio. Increase the `OPEN_CHOICE_READER_EPUB_*` values only when trusted books require it and the host has enough memory for the expanded content.

Path values in `backend/.env` are resolved from the directory where the backend process starts. The bundled scripts start it from `backend`, so the example's relative `data/...` paths stay inside that directory.

## Network access

The bundled runtime binds to `127.0.0.1:8000` by default. Set `OPEN_CHOICE_READER_HOST` and `OPEN_CHOICE_READER_PORT` for the shell runtime. The PowerShell WSL launcher exposes the service to the LAN only when called with `-Expose`.

For remote use, terminate HTTPS at a reverse proxy, enable secure session cookies, configure exact allowed origins, and rate-limit authentication routes. Configure `OPEN_CHOICE_READER_AUTH_BOOTSTRAP_TOKEN` before the first proxied request, then enter that value in the first-run form. Any request carrying proxy forwarding headers requires the token even when the proxy connects from loopback.

## Browser extension

The extension defaults to `http://127.0.0.1:8000`. Saving another server asks the browser for permission to reach only that origin. The backend must also allow the extension's exact origin through `OPEN_CHOICE_READER_CORS_ALLOWED_ORIGIN_REGEX`.

## Optional speech engines

The base backend includes Piper. Optional dependency groups are:

- `all`: Kokoro, faster-whisper transcription, and Qwen voice cloning
- `dev`: test and lint tools

Downloaded model and voice files belong under `backend/data/models` and are excluded from Git.

The Linux/WSL bootstrap also accepts these shell-only setup variables:

- `PYTHON_BIN`: supported Python interpreter to use
- `OPEN_CHOICE_READER_EXTRAS`: comma-separated Python extras, such as `all`
- `PIPER_DEFAULT_VOICE`: Piper voice linked as the default
- `PIPER_VOICE_MATRIX`: comma-separated Piper voices to download
- `DOWNLOAD_KOKORO_MODELS=1`: download the default Kokoro model and voice bundle
- `KOKORO_MODEL_URL` and `KOKORO_VOICES_URL`: override those download sources
