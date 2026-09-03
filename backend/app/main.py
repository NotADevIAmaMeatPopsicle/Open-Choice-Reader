from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.auth import router as auth_router
from app.api.clone_samples import router as clone_samples_router
from app.api.collections import router as collections_router
from app.api.catalogs import router as catalogs_router
from app.api.documents import router as documents_router
from app.api.extension import router as extension_router
from app.api.friends import router as friends_router
from app.api.health import router as health_router
from app.api.issues import router as issues_router
from app.api.jobs import router as jobs_router
from app.api.playback import router as playback_router
from app.api.settings import router as settings_router
from app.api.shares import router as shares_router
from app.api.themes import router as themes_router
from app.api.voices import router as voices_router
from app.config import settings
from app.services.documents import init_database


def create_storage_roots() -> None:
    for path in (
        settings.storage_root,
        settings.source_root,
        settings.cache_root,
        settings.export_root,
        settings.inbox_root,
        settings.seed_download_root,
        settings.storage_root / "covers",
        settings.storage_root / "voices",
    ):
        Path(path).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_storage_roots()
    init_database()
    yield


app = FastAPI(title="Open Choice Reader", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
    allow_origins=settings.allowed_cors_origins(),
    allow_origin_regex=settings.cors_allowed_origin_regex,
)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(clone_samples_router)
app.include_router(extension_router)
app.include_router(catalogs_router)
app.include_router(collections_router)
app.include_router(documents_router)
app.include_router(friends_router)
app.include_router(issues_router)
app.include_router(jobs_router)
app.include_router(playback_router)
app.include_router(settings_router)
app.include_router(shares_router)
app.include_router(themes_router)
app.include_router(voices_router)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=()")
    return response


@app.get("/{full_path:path}", include_in_schema=False)
async def frontend_shell(full_path: str):
    dist_root = settings.frontend_dist_root.resolve()
    index_file = dist_root / "index.html"

    if not dist_root.is_dir() or not index_file.is_file():
        raise HTTPException(status_code=404, detail="Frontend bundle not built")

    requested_path = (dist_root / full_path).resolve()
    try:
        requested_path.relative_to(dist_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc

    if full_path and requested_path.is_file():
        return FileResponse(requested_path)

    return FileResponse(index_file)
