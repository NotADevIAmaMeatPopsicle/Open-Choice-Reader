# Project status

Open Choice Reader is at version 0.1.0 as source-only pre-release software. It is usable from source, but its interfaces and installation flow may still change.

## Supported now

- Local library accounts with administrator bootstrap, invitations, and per-user storage
- TXT, Markdown, HTML, EPUB, and text-based PDF imports
- Pasted text, supported article URLs, and public-domain catalog discovery
- In-browser reading, bookmarks, collections, series, themes, and friend-to-friend copies
- Local Piper narration and WAV audiobook export
- Optional Kokoro narration, faster-whisper transcription, and Qwen voice cloning
- An unpacked Manifest V3 extension for Chromium-based browsers
- Windows development and Ubuntu/Debian or WSL self-hosting workflows

## Not yet provided

- A packaged desktop installer, Docker image, hosted service, or one-command Windows production install
- Published PyPI, npm, browser-store, or GitHub release artifacts
- OCR for scanned PDFs
- Packaged Firefox or Safari extensions
- A stable, versioned external API compatibility guarantee
- A supported public-internet deployment profile

Hardware acceleration and the optional speech engines depend on the host, installed runtimes, downloaded models, and their upstream licenses. The base application works without a GPU.
