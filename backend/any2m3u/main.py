from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .api import auth as auth_api
from .config import get_settings
from .db import init_db


@asynccontextmanager
async def _lifespan(app: FastAPI):
    s = get_settings()
    await init_db(s.data_dir)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Any2M3U", lifespan=_lifespan)
    app.include_router(auth_api.router)

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    return app
