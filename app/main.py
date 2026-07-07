from __future__ import annotations

import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.db import seed_catalogs
from app.routers import api_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_catalogs()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Mock backend for the AI Career Helper. Interface contracts follow "
        "design-docs/api-design.md; business logic is mocked (local SQLite store, "
        "mock AI/matching). See README for the full list of decisions."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"

if FRONTEND_DIST.exists() and FRONTEND_INDEX.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str) -> FileResponse:
        """Serve the Vite SPA for browser routes after API/docs routes are matched."""
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_INDEX)


if settings.enable_dev_reset:
    import sqlite3

    from fastapi import Depends

    from app.core.deps import get_current_user
    from app.db import get_conn
    from app.models import UserRecord
    from app.services import account_service

    @app.post("/__dev/reset", tags=["meta"], status_code=204, response_model=None)
    def dev_reset(
        user: UserRecord = Depends(get_current_user),
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> None:
        """Dev-only: clear the current user's demo data (use-case SET-07)."""
        account_service.reset_user_data(conn, user.id)

    @app.post("/__dev/shutdown", tags=["meta"], include_in_schema=False)
    def dev_shutdown(x_dev_action: str | None = Header(default=None)) -> dict[str, str]:
        """Dev-only: let local scripts stop the server when the OS PID is inaccessible."""
        if x_dev_action != "shutdown":
            raise HTTPException(status_code=403, detail="Missing dev shutdown header.")

        def exit_process() -> None:
            time.sleep(0.2)
            os._exit(0)

        threading.Thread(target=exit_process, daemon=True).start()
        return {"status": "shutting_down"}
