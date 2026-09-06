# Contributing

Open Choice Reader is source-only pre-release software. Contributions should keep the project portable and must not include personal paths, hostnames, credentials, private documents, generated audio, model files, or deployment-specific data. Read the [architecture overview](ARCHITECTURE.md) and follow the development setup in [README.md](README.md) before changing a runtime path.

## Development checks

Before proposing a change, run:

```bash
python scripts/verify-public-tree.py
python scripts/verify-doc-links.py
cd backend && python -m ruff check app tests && python -m pytest
cd ../frontend && npm test && npm run build
cd ../browser-extension && node --test tests/core.test.mjs
```

Keep environment-specific values in environment variables or ignored `.env` files. Add tests for behavior changes and document new configuration keys in `docs/configuration.md`.

Keep pull requests focused. Describe the user-facing behavior, tests performed, and any storage, network, authentication, dependency, or licensing impact. Screenshots are useful for interface changes, but they must use synthetic data and contain no browser or desktop chrome.

Do not add a file outside the families in `public-files.allowlist` without reviewing and updating that allowlist. Never commit user data, downloaded models, voice samples, generated audio, credentials, or private deployment notes.
