"""
API v1 router aggregation
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, scans, subscriptions, webhooks, admin, setup

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(scans.router, prefix="/scans", tags=["scans"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(setup.router, prefix="/setup", tags=["setup"])
