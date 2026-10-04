from fastapi import APIRouter

from app.api.routes import (
    auth,
    coach,
    health,
    measurements,
    notifications,
    plans,
    progress,
    requests,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(coach.router)
api_router.include_router(plans.router)
api_router.include_router(requests.router)
api_router.include_router(notifications.router)
api_router.include_router(measurements.router)
api_router.include_router(progress.router)
