from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.api.dependencies import get_db_session, get_current_user
from app.api.schemas.auth import UserLogin, UserResponse, Token, ChangePassword, AdminChangePassword
from app.utils.auth import authenticate_user, create_access_token, get_password_hash, verify_password, get_user_by_username
from app.config import settings
from app.db.models.user import User
from sqlalchemy import select

router = APIRouter()


@router.post("/login", response_model=Token, summary="Login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Authenticate user and return access token.
    
    - **username**: User's username
    - **password**: User's password
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/change-password", summary="Change Password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Change the current user's password.
    
    Requires authentication. User must provide their current password.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    await db.refresh(current_user)
    
    return {"message": "Password changed successfully"}


@router.post("/admin/change-password", summary="Admin Change Password")
async def admin_change_password(
    password_data: AdminChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Change any user's password (admin only).
    
    Requires superuser privileges.
    """
    # Check if current user is superuser
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can change other users' passwords"
        )
    
    # Find target user
    target_user = await get_user_by_username(db, password_data.username)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    target_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    await db.refresh(target_user)
    
    return {"message": f"Password changed successfully for user '{password_data.username}'"}


@router.get("/me", response_model=UserResponse, summary="Get Current User")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get information about the currently authenticated user.
    """
    return current_user


@router.post("/login-json", response_model=Token, summary="Login with JSON")
async def login_json(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Authenticate user with JSON payload and return access token.
    
    - **username**: User's username
    - **password**: User's password
    """
    user = await authenticate_user(db, user_credentials.username, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/change-password", summary="Change Password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Change the current user's password.
    
    Requires authentication. User must provide their current password.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    await db.refresh(current_user)
    
    return {"message": "Password changed successfully"}


@router.post("/admin/change-password", summary="Admin Change Password")
async def admin_change_password(
    password_data: AdminChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Change any user's password (admin only).
    
    Requires superuser privileges.
    """
    # Check if current user is superuser
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can change other users' passwords"
        )
    
    # Find target user
    target_user = await get_user_by_username(db, password_data.username)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    target_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    await db.refresh(target_user)
    
    return {"message": f"Password changed successfully for user '{password_data.username}'"}


@router.get("/me", response_model=UserResponse, summary="Get Current User")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get information about the currently authenticated user.
    """
    return current_user