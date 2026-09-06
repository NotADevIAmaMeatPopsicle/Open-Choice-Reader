# Data, privacy, and responsible use

Open Choice Reader stores its SQLite database, uploaded documents, cover art, voice samples, generated audio, and downloaded models locally under its configured data directories. User-owned source files, covers, cached audio, exports, inbox files, and voice samples are namespaced by user. On POSIX systems the application applies owner-only permissions when it creates these directories and the SQLite database. Those paths are excluded from Git, but operators remain responsible for backups and filesystem access controls.

Default storage and work limits bound uploaded files, extracted text, archive expansion, PDF pages, transcription duration, active export jobs, and each user's persistent files. Operators can tune these values in `backend/.env`; see [configuration](configuration.md).

Only import documents you are allowed to copy and process. Public-domain catalogs can contain inaccurate metadata, and a work's copyright status can vary by country.

Voice cloning must be used only with the informed consent of the person whose voice is represented or with material whose license clearly permits that use. Do not use generated speech to impersonate, deceive, harass, or bypass authorization. Model weights and voice packs retain their own upstream terms and are not covered by the future source-code license for this repository.

The optional browser extension can read the active page or selected text after a user action and send it to the configured Open Choice Reader server. Its requested host access should be limited to servers the user trusts.
