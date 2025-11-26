"""
Authentication API endpoints.
"""
from datetime import datetime, timedelta
import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User, RefreshToken
from app.schemas.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    AccessTokenResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.schemas.common import MessageResponse

router = APIRouter()


def _hash_token(token: str) -> str:
    """Hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        request: Request object
        db: Database session
    
    Returns:
        TokenResponse: User data with access and refresh tokens
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        password_hash=get_password_hash(user_data.password),
    )
    db.add(user)
    await db.flush()
    
    # Create tokens
    access_token = create_access_token(
        subject=user.id,
        additional_claims={
            "username": user.username,
            "email": user.email,
        }
    )
    
    refresh_token_id = uuid.uuid4()
    refresh_token = create_refresh_token(
        subject=user.id,
        token_id=refresh_token_id,
    )
    
    # Store refresh token
    refresh_token_record = RefreshToken(
        id=refresh_token_id,
        user_id=user.id,
        token_hash=_hash_token(refresh_token),
        device_info=None,
        ip_address=str(request.client.host) if request.client else None,
        expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_token_record)
    await db.commit()
    await db.refresh(user)
    
    return TokenResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate user and return tokens.
    
    Args:
        credentials: User login credentials
        request: Request object
        db: Database session
    
    Returns:
        TokenResponse: User data with access and refresh tokens
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last seen
    user.last_seen_at = datetime.utcnow()
    
    # Create tokens
    access_token = create_access_token(
        subject=user.id,
        additional_claims={
            "username": user.username,
            "email": user.email,
        }
    )
    
    refresh_token_id = uuid.uuid4()
    refresh_token = create_refresh_token(
        subject=user.id,
        token_id=refresh_token_id,
    )
    
    # Store refresh token
    refresh_token_record = RefreshToken(
        id=refresh_token_id,
        user_id=user.id,
        token_hash=_hash_token(refresh_token),
        device_info=credentials.device_info,
        ip_address=str(request.client.host) if request.client else None,
        expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_token_record)
    await db.commit()
    await db.refresh(user)
    
    return TokenResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    token_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> AccessTokenResponse:
    """
    Refresh access token using refresh token.
    
    Args:
        token_request: Refresh token request
        db: Database session
    
    Returns:
        AccessTokenResponse: New access token
    """
    # Decode refresh token
    payload = decode_token(token_request.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    token_id = payload.get("token_id")
    user_id = payload.get("sub")
    
    if not token_id or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Verify token in database
    token_hash = _hash_token(token_request.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.id == uuid.UUID(token_id),
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    refresh_token_record = result.scalar_one_or_none()
    
    if not refresh_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or expired"
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled"
        )
    
    # Create new access token
    access_token = create_access_token(
        subject=user.id,
        additional_claims={
            "username": user.username,
            "email": user.email,
        }
    )
    
    return AccessTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    token_request: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Logout user by revoking refresh token.
    
    Args:
        token_request: Refresh token to revoke
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    # Find and revoke refresh token
    token_hash = _hash_token(token_request.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == current_user.id,
        )
    )
    refresh_token_record = result.scalar_one_or_none()
    
    if refresh_token_record:
        refresh_token_record.revoked = True
        await db.commit()
    
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        UserResponse: Current user data
    """
    return UserResponse.model_validate(current_user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Request password reset email.
    
    Args:
        request: Password reset request with email
        db: Database session
    
    Returns:
        MessageResponse: Success message (always returns success for security)
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    # Always return success message for security
    # In production, send email with reset link if user exists
    if user:
        # TODO: Create password reset token and send email
        pass
    
    return MessageResponse(
        message="If an account exists with this email, you will receive a password reset link"
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Reset password using token.
    
    Args:
        request: Password reset confirmation with token and new password
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    # Decode token
    payload = decode_token(request.token)
    
    if not payload or payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload"
        )
    
    # Find user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Update password
    user.password_hash = get_password_hash(request.new_password)
    
    # Revoke all refresh tokens
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user.id)
    )
    for token in result.scalars():
        token.revoked = True
    
    await db.commit()
    
    return MessageResponse(message="Password successfully reset")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Verify email address using token.
    
    Args:
        token: Email verification token
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    # Decode token
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "email_verification":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload"
        )
    
    # Find user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Mark email as verified
    user.email_verified = True
    await db.commit()
    
    return MessageResponse(message="Email successfully verified")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Resend email verification.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    if current_user.email_verified:
        return MessageResponse(message="Email already verified")
    
    # TODO: Create verification token and send email
    
    return MessageResponse(message="Verification email sent")

