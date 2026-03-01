from fastapi import APIRouter
from app.api import rankings, debug, journals

api_router = APIRouter()
api_router.include_router(rankings.router, prefix="")
api_router.include_router(debug.router, prefix="")
api_router.include_router(journals.router, prefix="")
