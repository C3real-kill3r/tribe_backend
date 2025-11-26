"""
User settings and preferences models.
"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import TimestampMixin, UUIDMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserSettings(Base, UUIDMixin, TimestampMixin):
    """User settings and preferences."""
    
    __tablename__ = "user_settings"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    
    # Privacy settings
    who_can_send_friend_requests = Column(
        String(20),
        default="friends_of_friends",
        nullable=False
    )  # 'everyone', 'friends_of_friends', 'no_one'
    who_can_send_messages = Column(
        String(20),
        default="friends_only",
        nullable=False
    )  # 'everyone', 'friends_only'
    share_activity_with_friends = Column(Boolean, default=True, nullable=False)
    
    # Appearance settings
    theme_mode = Column(
        String(20),
        default="system",
        nullable=False
    )  # 'light', 'dark', 'system'
    accent_color = Column(String(7), default="#FF6B6B", nullable=False)  # Hex color
    font_size_multiplier = Column(Numeric(3, 2), default=1.0, nullable=False)
    
    # Relationships
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<UserSettings for {self.user_id}>"


class BlockedUser(Base, UUIDMixin):
    """Blocked users."""
    
    __tablename__ = "blocked_users"
    
    blocker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    blocked_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    reason = Column(Text, nullable=True)
    blocked_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    blocker: "User" = relationship("User", foreign_keys=[blocker_id])
    blocked: "User" = relationship("User", foreign_keys=[blocked_id])
    
    def __repr__(self) -> str:
        return f"<BlockedUser {self.blocker_id} blocked {self.blocked_id}>"

