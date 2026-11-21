"""Voxora Voice: FastAPI application. Serves the API under /api and the web app at /."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db, seed
from .config import FRONTEND_DIR, settings
from .routers import admin, auth, client, meta, voice


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = db.connect()
    try:
        db.init_db(conn)
        seed.ensure_seed(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="Voxora Voice API", version="1.0.0", description="Intelligent Conversations. Limitless Possibilities.",
              lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if not request.url.path.startswith("/api"):
        response.headers.setdefault("Cache-Control", "no-cache")  # always pick up the latest UI while developing
    return response


for module in (auth, meta, admin, client, voice):
    app.include_router(module.router)

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="web")
