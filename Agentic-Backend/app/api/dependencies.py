from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.database import get_async_session
from app.config import settings
from app.utils.auth import verify_token, get_user_by_username
from app.db.models.user import User

security = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncSession:
    """Dependency to get database session."""
    async for session in get_async_session():
        yield session


async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> bool:
    """Verify API key if configured."""
    if not settings.api_key:
        return True  # No API key required
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    username = verify_token(credentials.credentials)
    if username is None:
        raise credentials_exception
    
    user = await get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user