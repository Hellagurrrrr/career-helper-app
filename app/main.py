from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.routers import api_router
from app.services.store import seed_catalogs


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_catalogs()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Mock backend for the AI Career Helper. Interface contracts follow "
        "design-docs/api-design.md; business logic is mocked (in-memory store, "
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


if settings.enable_dev_reset:
    from app.core.deps import get_current_user
    from app.services.store import UserRecord, store
    from fastapi import Depends

    @app.post("/__dev/reset", tags=["meta"], status_code=204, response_model=None)
    def dev_reset(user: "UserRecord" = Depends(get_current_user)) -> None:
        """Dev-only: clear the current user's demo data (use-case SET-07)."""
        store.reset_user_data(user.id)
