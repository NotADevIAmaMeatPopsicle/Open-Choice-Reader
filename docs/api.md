# API reference

Open Choice Reader exposes a FastAPI HTTP API under `/api`. When the backend is running, the implementation-generated OpenAPI document is available at `/openapi.json` and the interactive Swagger UI is available at `/docs`.

The API is organized into these route groups:

- authentication, administrator setup, invitations, users, and sessions;
- documents, collections, catalogs, article imports, and reading progress;
- playback sessions, voices, voice samples, and export jobs;
- friends and document sharing;
- themes, settings, browser-extension support, and health checks.

Most routes require the signed-in session cookie. The intentionally unauthenticated routes are limited to authentication and account-onboarding flows, the health check, the catalog-source list, the browser-extension download, and static frontend delivery. Consult the generated OpenAPI document for the current request and response schemas rather than relying on a manually duplicated endpoint list.

The project does not currently provide a standalone command-line client or a versioned compatibility guarantee for the HTTP API. The scripts under `scripts/` are development and self-hosting helpers, not a stable CLI.
