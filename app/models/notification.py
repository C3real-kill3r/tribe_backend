"""
Notification and push notification models.
"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TimestampMixin, UUIDMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class Notification(BaseModel):
    """User notifications."""
    
    __tablename__ = "notifications"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Content
    notification_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Related entities
    related_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )
    related_goal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=True
    )
    related_post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=True
    )
    related_comment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("post_comments.id", ondelete="CASCADE"),
        nullable=True
    )
    
    # Media
    image_url = Column(Text, nullable=True)
    icon_type = Column(String(50), nullable=True)
    icon_color = Column(String(20), nullable=True)
    
    # Navigation
    action_url = Column(Text, nullable=True)  # Deep link for app navigation
    
    # Status
    is_read = Column(Boolean, default=False, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Push notification
    push_sent = Column(Boolean, default=False, nullable=False)
    push_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user: "User" = relationship("User", foreign_keys=[user_id])
    related_user: "User" = relationship("User", foreign_keys=[related_user_id])
    
    def __repr__(self) -> str:
        return f"<Notification {self.id}>"


class NotificationPreference(Base, UUIDMixin, TimestampMixin):
    """User notification preferences."""
    
    __tablename__ = "notification_preferences"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    
    # Push notifications
    push_enabled = Column(Boolean, default=True, nullable=False)
    
    # Email notifications
    email_enabled = Column(Boolean, default=False, nullable=False)
    
    # Notification types
    goal_reminders = Column(Boolean, default=True, nullable=False)
    friend_requests = Column(Boolean, default=True, nullable=False)
    messages = Column(Boolean, default=True, nullable=False)
    achievements = Column(Boolean, default=True, nullable=False)
    post_likes = Column(Boolean, default=True, nullable=False)
    post_comments = Column(Boolean, default=True, nullable=False)
    goal_updates = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<NotificationPreference for {self.user_id}>"


class PushToken(Base, UUIDMixin, TimestampMixin):
    """Push notification tokens."""
    
    __tablename__ = "push_tokens"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    token = Column(Text, nullable=False)
    device_type = Column(String(20), nullable=True)  # 'ios', 'android', 'web'
    device_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<PushToken {self.id}>"

