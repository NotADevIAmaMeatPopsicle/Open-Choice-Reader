# Security policy

Open Choice Reader is designed primarily for self-hosting on a trusted machine or private network. Do not expose the development server directly to the public internet.

## Supported versions

Open Choice Reader has not reached its first public release. Security fixes currently target the latest commit on `main`.

## Deployment requirements

- Put remote installations behind an HTTPS reverse proxy.
- Set `OPEN_CHOICE_READER_AUTH_SESSION_SECURE=true` when using HTTPS.
- Set a strong, temporary `OPEN_CHOICE_READER_AUTH_BOOTSTRAP_TOKEN` before first-run setup over a network, then remove it after the administrator exists.
- Configure an exact CORS allowlist. Do not use a wildcard with credentialed requests.
- Apply request and login rate limits at the reverse proxy.
- Keep `backend/data`, `.env` files, logs, backups, uploaded documents, voice samples, and generated audio private.
- Run the service as an unprivileged operating-system account.

Remote document and audio downloads reject non-public network addresses and enforce size limits by default. Only enable `OPEN_CHOICE_READER_REMOTE_FETCH_ALLOW_PRIVATE_HOSTS` on a trusted network after considering server-side request-forgery risk.

## Reporting a vulnerability

Do not disclose a suspected vulnerability in a public issue. After the GitHub repository is available, use its private [Report a vulnerability](https://github.com/NotADevIAmaMeatPopsicle/Open-Choice-Reader/security/advisories/new) workflow in the Security tab. Until that channel is enabled, contact the maintainer through a contact method listed on their GitHub profile.

Include the affected revision, relevant route or workflow, reproduction details, impact, and any suggested mitigation. Do not include credentials, private documents, voice samples, or other sensitive data in a public issue.
