"""
Authentication related schemas.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import TribeBaseModel


class UserCreate(BaseModel):
    """Schema for user registration."""
    
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate that passwords match."""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v
    
    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    
    email: EmailStr
    password: str = Field(..., min_length=1)
    device_info: Optional[dict] = None


class DeviceInfo(BaseModel):
    """Device information for login tracking."""
    
    device_type: Optional[str] = None  # 'ios', 'android', 'web'
    device_id: Optional[str] = None
    app_version: Optional[str] = None


class UserResponse(TribeBaseModel):
    """User response schema."""
    
    id: UUID
    email: str
    username: str
    full_name: str
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    goals_achieved: int = 0
    photos_shared: int = 0
    email_verified: bool = False
    is_active: bool = True
    last_seen_at: Optional[datetime] = None
    created_at: datetime


class TokenResponse(TribeBaseModel):
    """Token response for authentication."""
    
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh."""
    
    refresh_token: str


class AccessTokenResponse(TribeBaseModel):
    """Response for access token refresh."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate that passwords match."""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class EmailVerificationRequest(BaseModel):
    """Schema for email verification."""
    
    token: str


class ChangePasswordRequest(BaseModel):
    """Schema for changing password."""
    
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate that passwords match."""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v

