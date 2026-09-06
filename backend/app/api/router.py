from fastapi import APIRouter

from app.api.routes import auth, coach, health, plans

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(coach.router)
api_router.include_router(plans.router)
