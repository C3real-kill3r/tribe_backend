"""
Settings related schemas.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TribeBaseModel
from app.schemas.user import UserPublicResponse


class PrivacySettingsResponse(TribeBaseModel):
    """Privacy settings response."""
    
    profile_visibility: str = "friends_only"
    online_status_visible: bool = True
    appear_in_suggestions: bool = True
    who_can_send_friend_requests: str = "friends_of_friends"
    who_can_send_messages: str = "friends_only"
    share_activity_with_friends: bool = True


class PrivacySettingsUpdate(BaseModel):
    """Schema for updating privacy settings."""
    
    profile_visibility: Optional[str] = Field(
        None, pattern=r"^(everyone|friends_only|private)$"
    )
    online_status_visible: Optional[bool] = None
    appear_in_suggestions: Optional[bool] = None
    who_can_send_friend_requests: Optional[str] = Field(
        None, pattern=r"^(everyone|friends_of_friends|no_one)$"
    )
    who_can_send_messages: Optional[str] = Field(
        None, pattern=r"^(everyone|friends_only)$"
    )
    share_activity_with_friends: Optional[bool] = None


class AppearanceSettingsResponse(TribeBaseModel):
    """Appearance settings response."""
    
    theme_mode: str = "system"
    accent_color: str = "#FF6B6B"
    font_size_multiplier: float = 1.0


class AppearanceSettingsUpdate(BaseModel):
    """Schema for updating appearance settings."""
    
    theme_mode: Optional[str] = Field(None, pattern=r"^(light|dark|system)$")
    accent_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    font_size_multiplier: Optional[float] = Field(None, ge=0.8, le=1.5)


class FullSettingsResponse(TribeBaseModel):
    """Full settings response."""
    
    user_id: UUID
    privacy: PrivacySettingsResponse
    appearance: AppearanceSettingsResponse
    notifications: dict  # NotificationPreferenceResponse


class BlockedUserResponse(TribeBaseModel):
    """Blocked user response."""
    
    id: UUID
    user: UserPublicResponse
    blocked_at: datetime


class BlockedUsersListResponse(TribeBaseModel):
    """List of blocked users."""
    
    blocked_users: List[BlockedUserResponse]


class BlockUserRequest(BaseModel):
    """Schema for blocking a user."""
    
    user_id: UUID
    reason: Optional[str] = Field(None, max_length=500)

