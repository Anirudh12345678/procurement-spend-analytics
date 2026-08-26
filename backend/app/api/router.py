from fastapi import APIRouter

from app.api.routes.analytics import router as analytics_router
from app.api.routes.catalog import router as catalog_router
from app.api.routes.optimization import router as optimization_router
from app.api.routes.recommendations import router as recommendations_router

api_router = APIRouter(prefix="/api")
api_router.include_router(analytics_router)
api_router.include_router(catalog_router)
api_router.include_router(optimization_router)
api_router.include_router(recommendations_router)
