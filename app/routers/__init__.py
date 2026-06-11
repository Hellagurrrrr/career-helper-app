from __future__ import annotations

from fastapi import APIRouter

from app.routers import (
    alumni,
    applications,
    auth,
    coaching,
    goals,
    jobs,
    meetings,
    notifications,
    profile,
    saved_jobs,
    tailored_cv,
    tracking,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(goals.router)
api_router.include_router(tracking.router)
api_router.include_router(jobs.router)
api_router.include_router(saved_jobs.router)
api_router.include_router(tailored_cv.router)
api_router.include_router(applications.router)
api_router.include_router(coaching.router)
api_router.include_router(alumni.router)
api_router.include_router(meetings.router)
api_router.include_router(notifications.router)
