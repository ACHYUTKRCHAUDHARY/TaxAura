from fastapi import APIRouter

from aura.api.dependencies import CurrentUser
from aura.db.models import User
from aura.schemas.user import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> User:
    return current_user
