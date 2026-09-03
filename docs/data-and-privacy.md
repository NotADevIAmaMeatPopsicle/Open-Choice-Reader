# Data, privacy, and responsible use

Open Choice Reader stores its SQLite database, uploaded documents, cover art, voice samples, generated audio, and downloaded models locally under its configured data directories. Those paths are excluded from Git, but operators remain responsible for backups and filesystem access controls.

Only import documents you are allowed to copy and process. Public-domain catalogs can contain inaccurate metadata, and a work's copyright status can vary by country.

Voice cloning must be used only with the informed consent of the person whose voice is represented or with material whose license clearly permits that use. Do not use generated speech to impersonate, deceive, harass, or bypass authorization. Model weights and voice packs retain their own upstream terms and are not covered by the future source-code license for this repository.

The optional browser extension can read the active page or selected text after a user action and send it to the configured Open Choice Reader server. Its requested host access should be limited to servers the user trusts.
