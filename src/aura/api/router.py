from fastapi import APIRouter

from aura.api.routes.advisor import router as advisor_router
from aura.api.routes.documents import router as documents_router
from aura.api.routes.rag import router as rag_router
from aura.api.routes.tax import router as tax_router
from aura.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(advisor_router, prefix="/advisor", tags=["tax advisor"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(tax_router, prefix="/tax", tags=["tax calculator"])
api_router.include_router(rag_router, prefix="/knowledge", tags=["RAG knowledge"])
