from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/open_choice_reader.db"
    auth_session_cookie_name: str = "open_choice_reader_session"
    auth_session_ttl_hours: int = 168
    auth_session_secure: bool = False
    auth_session_samesite: str = "lax"
    auth_password_min_length: int = 12
    auth_bootstrap_token: str | None = None
    auth_login_max_attempts: int = 10
    auth_login_window_seconds: int = 300
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cors_allowed_origin_regex: str | None = None
    remote_fetch_allow_private_hosts: bool = False
    remote_metadata_max_bytes: int = 5 * 1024 * 1024
    remote_image_max_bytes: int = 10 * 1024 * 1024
    remote_document_max_bytes: int = 50 * 1024 * 1024
    remote_audio_max_bytes: int = 25 * 1024 * 1024
    document_upload_max_bytes: int = 50 * 1024 * 1024
    epub_max_entries: int = 5_000
    epub_max_member_bytes: int = 50 * 1024 * 1024
    epub_max_uncompressed_bytes: int = 200 * 1024 * 1024
    epub_max_compression_ratio: float = 200.0
    voice_upload_max_bytes: int = 25 * 1024 * 1024
    theme_upload_max_bytes: int = 1024 * 1024
    storage_root: Path = Path("data")
    source_root: Path = Path("data/source")
    cache_root: Path = Path("data/cache")
    export_root: Path = Path("data/exports")
    inbox_root: Path = Path("data/inbox")
    seed_download_root: Path = Path("data/seed-downloads")
    frontend_dist_root: Path = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    tts_engine: str = "piper"
    kokoro_binary: str = "kokoro-onnx"
    kokoro_model_path: Path = Path("data/models/kokoro/kokoro-v1.0.onnx")
    kokoro_voices_path: Path = Path("data/models/kokoro/voices-v1.0.bin")
    piper_binary: str = "piper"
    piper_model_path: Path = Path("data/models/piper/default.onnx")
    qwen_clone_model_name: str = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
    qwen_clone_large_model_name: str = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    voice_transcription_model_name: str = "base.en"
    voice_transcription_device: str = "cpu"
    voice_transcription_compute_type: str = "int8"
    worker_stale_job_minutes: int = 15
    audio_cache_max_gb: float = 8.0
    audio_cache_eviction_minutes: int = 30
    metadata_enrichment_enabled: bool = True
    metadata_request_timeout_seconds: float = 10.0
    project_gutenberg_top_url: str = "https://www.gutenberg.org/browse/scores/top"
    gutendex_api_base: str = "https://gutendex.com/books"
    open_library_search_url: str = "https://openlibrary.org/search.json"
    open_library_cover_base: str = "https://covers.openlibrary.org/b/id"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OPEN_CHOICE_READER_",
        extra="ignore",
    )

    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
