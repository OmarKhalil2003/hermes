from fastapi import APIRouter

from backend.api.v1.endpoints.agent import router as agent_router
from backend.api.v1.endpoints.document import router as document_router
from backend.api.v1.endpoints.jobs import router as jobs_router

api_router = APIRouter()
api_router.include_router(document_router, prefix="/documents", tags=["documents"])
api_router.include_router(agent_router, prefix="/agents", tags=["agents"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
