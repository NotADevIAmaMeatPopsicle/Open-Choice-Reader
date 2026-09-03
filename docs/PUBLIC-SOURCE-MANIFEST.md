# Public source manifest

This document defines the intended public source boundary. It does not authorize a GitHub visibility change, package publication, release, deployment, or distribution of user data and downloaded models.

## Included source

The public candidate contains:

- root project metadata and community policies;
- the FastAPI application, Alembic migrations, and tests under `backend/`;
- the React application and tests under `frontend/`;
- the optional Chromium extension and its tests under `browser-extension/`;
- generic development and self-hosting helpers under `scripts/`;
- original built-in SVG theme artwork; and
- public installation, API, configuration, privacy, dependency, contribution, and security documentation.

`public-files.allowlist` is the machine-enforced source boundary. `scripts/verify-public-tree.py` rejects any non-ignored file outside the approved path families and blocks common data, secret, model, media, archive, editor, agent, cache, and build-artifact classes. `scripts/verify-doc-links.py` checks public documentation links.

## Excluded material

The public candidate excludes the private source repository's Git history, private documentation, machine-specific deployment material, environment files, credentials, databases, logs, caches, downloaded models, user documents, voice samples, generated audio, screenshots, local workspaces, and editor or agent state.

Ignore rules prevent routine artifacts from entering Git, but they are not proof that arbitrary content is safe. Before every approved push, review the exact `git ls-files` result, rerun the allowlist and secret scanners, and compare it with the approved private SHA-256 manifest.

## Python archive boundary

The Python wheel and source archive are narrower than the Git repository. They contain the backend's `app` package and package metadata. Tests, migrations, local data, environment files, models, and generated artifacts are excluded. `scripts/verify-python-package.py` enforces that boundary after each build.

The package build is a verification artifact only. Publishing it to an index requires separate explicit approval.
