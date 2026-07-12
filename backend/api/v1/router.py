from fastapi import APIRouter

from backend.api.v1.endpoints.auth import router as auth_router
from backend.api.v1.endpoints.document import router as document_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(document_router, prefix="/documents", tags=["documents"])
