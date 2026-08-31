from fastapi import APIRouter

from aura.api.routes.documents import router as documents_router
from aura.api.routes.advisor import router as advisor_router

api_router = APIRouter()
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(advisor_router, prefix="/advisor", tags=["tax advisor"])
