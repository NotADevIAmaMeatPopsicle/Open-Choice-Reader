# Security policy

Open Choice Reader is designed primarily for self-hosting on a trusted machine or private network. Do not expose the development server directly to the public internet.

## Supported versions

| Version | Supported |
| --- | --- |
| Latest `main` | Yes |
| Older revisions | No |

The project has not reached its first stable release. Security fixes currently target the latest commit on `main`.

## Deployment requirements

- Run the service as a dedicated, unprivileged operating-system account. `scripts/start.sh` refuses to run as root.
- Put remote installations behind a maintained HTTPS reverse proxy.
- Set `OPEN_CHOICE_READER_AUTH_SESSION_SECURE=true` when using HTTPS.
- Set a strong, temporary `OPEN_CHOICE_READER_AUTH_BOOTSTRAP_TOKEN` before first-run setup over a network, then remove it after the administrator exists.
- Configure exact CORS origins. Do not use a wildcard with credentialed requests.
- Apply request and login rate limits at the reverse proxy as an additional layer.
- Keep `backend/data`, `.env` files, logs, backups, uploaded documents, voice samples, and generated audio private.
- Keep the default request, parser, transcription, storage, and export-job limits unless the host has capacity for larger workloads.

Remote document and audio downloads reject non-public network addresses, pin the validated destination, revalidate redirects, and enforce size and total-time limits by default. Only enable `OPEN_CHOICE_READER_REMOTE_FETCH_ALLOW_PRIVATE_HOSTS` on a trusted network after considering server-side request-forgery risk.

Imported EPUB SVG covers are not served directly. Raster covers are signature-checked, and generated SVG placeholders are returned with a restrictive content security policy.

## Reporting a vulnerability

Do not disclose a suspected vulnerability in a public issue. Use GitHub's private [Report a vulnerability](https://github.com/NotADevIAmaMeatPopsicle/Open-Choice-Reader/security/advisories/new) workflow.

Include the affected revision, relevant route or workflow, reproduction details, impact, and any suggested mitigation. Do not include credentials, private documents, voice samples, or other sensitive data in a public issue.
