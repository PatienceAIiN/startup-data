from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse
from app.services.auth_service import create_user, authenticate_user, create_access_token, create_refresh_token, get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def signup(request: Request, data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user = await create_user(db, data.email, data.password, data.full_name)
        access_token = create_access_token({"sub": str(user.id), "email": user.email})
        refresh_token = create_refresh_token(str(user.id))
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        user = await authenticate_user(db, data.email, data.password)
        access_token = create_access_token({"sub": str(user.id), "email": user.email})
        refresh_token = create_refresh_token(str(user.id))
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await get_current_user(credentials.credentials, db)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
