"""
User profile related schemas.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import TribeBaseModel


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    bio: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None


class UserProfileResponse(TribeBaseModel):
    """Full user profile response."""
    
    id: UUID
    email: str
    username: str
    full_name: str
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    profile_visibility: str = "friends_only"
    online_status_visible: bool = True
    appear_in_suggestions: bool = True
    goals_achieved: int = 0
    photos_shared: int = 0
    email_verified: bool = False
    is_active: bool = True
    is_verified: bool = False
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UserPublicResponse(TribeBaseModel):
    """Public user profile (limited fields)."""
    
    id: UUID
    username: str
    full_name: str
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_verified: bool = False
    goals_achieved: int = 0
    photos_shared: int = 0
    is_online: bool = False
    last_seen_at: Optional[datetime] = None


class UserStatsResponse(TribeBaseModel):
    """User statistics."""
    
    goals_achieved: int = 0
    goals_in_progress: int = 0
    photos_shared: int = 0
    friends_count: int = 0
    achievements_count: int = 0


class ImageUploadResponse(TribeBaseModel):
    """Response for image upload."""
    
    image_url: str
    updated_at: datetime


class FriendResponse(TribeBaseModel):
    """Friend list response."""
    
    id: UUID
    username: str
    full_name: str
    profile_image_url: Optional[str] = None
    is_online: bool = False
    last_seen_at: Optional[datetime] = None
    friendship_since: datetime
    mutual_friends_count: int = 0


class FriendRequestResponse(TribeBaseModel):
    """Friend request response."""
    
    id: UUID
    user_id: UUID
    friend_id: UUID
    status: str
    requested_at: datetime
    user: Optional[UserPublicResponse] = None


class FriendSuggestionResponse(TribeBaseModel):
    """Friend suggestion response."""
    
    user: UserPublicResponse
    reason: Optional[str] = None
    mutual_friends_count: int = 0
    common_goals: int = 0

