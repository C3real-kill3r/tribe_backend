"""
Notification related schemas.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TribeBaseModel, PaginationMeta, TimeAgoMixin
from app.schemas.user import UserPublicResponse


class NotificationResponse(TimeAgoMixin):  # TimeAgoMixin already inherits from TribeBaseModel
    """Notification response schema."""
    
    id: UUID
    notification_type: str
    title: str
    message: str
    related_user: Optional[UserPublicResponse] = None
    related_goal: Optional[dict] = None  # { id, title }
    related_post: Optional[dict] = None  # { id }
    image_url: Optional[str] = None
    icon_type: Optional[str] = None
    icon_color: Optional[str] = None
    action_url: Optional[str] = None
    is_read: bool = False
    created_at: datetime


class NotificationListResponse(TribeBaseModel):
    """Paginated notification list response."""
    
    notifications: List[NotificationResponse]
    pagination: PaginationMeta


class UnreadCountResponse(TribeBaseModel):
    """Unread notification count."""
    
    count: int


class NotificationPreferenceResponse(TribeBaseModel):
    """Notification preferences response."""
    
    push_enabled: bool = True
    email_enabled: bool = False
    goal_reminders: bool = True
    friend_requests: bool = True
    messages: bool = True
    achievements: bool = True
    post_likes: bool = True
    post_comments: bool = True
    goal_updates: bool = True
    updated_at: datetime


class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating notification preferences."""
    
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    goal_reminders: Optional[bool] = None
    friend_requests: Optional[bool] = None
    messages: Optional[bool] = None
    achievements: Optional[bool] = None
    post_likes: Optional[bool] = None
    post_comments: Optional[bool] = None
    goal_updates: Optional[bool] = None


class PushTokenCreate(BaseModel):
    """Schema for registering push token."""
    
    token: str = Field(..., min_length=1)
    device_type: str = Field(..., pattern=r"^(ios|android|web)$")
    device_id: Optional[str] = None


class PushTokenResponse(TribeBaseModel):
    """Push token response."""
    
    id: UUID
    token: str
    device_type: str
    device_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime

