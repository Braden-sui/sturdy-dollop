from fastapi import APIRouter
from fastapi import APIRouter
from api.v1.endpoints import simulate, admin

api_router = APIRouter()
api_router.include_router(simulate.router, tags=["Simulation"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"]) # Add admin router
# Add other routers here in the future, e.g., for admin endpoints
