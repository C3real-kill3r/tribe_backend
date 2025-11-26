"""
User and authentication related models.
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TimestampMixin, UUIDMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.goal import Goal, GoalParticipant
    from app.models.post import Post
    from app.models.friendship import Friendship


class User(BaseModel):
    """User model for authentication and profile."""
    
    __tablename__ = "users"
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)
    profile_image_url = Column(Text, nullable=True)
    cover_image_url = Column(Text, nullable=True)
    
    # Privacy settings
    profile_visibility = Column(
        String(20),
        default="friends_only",
        nullable=False
    )  # 'everyone', 'friends_only', 'private'
    online_status_visible = Column(Boolean, default=True, nullable=False)
    appear_in_suggestions = Column(Boolean, default=True, nullable=False)
    
    # Stats
    goals_achieved = Column(Integer, default=0, nullable=False)
    photos_shared = Column(Integer, default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    refresh_tokens: List["RefreshToken"] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    goals_created: List["Goal"] = relationship(
        "Goal",
        back_populates="creator",
        foreign_keys="Goal.creator_id",
        cascade="all, delete-orphan"
    )
    goal_participations: List["GoalParticipant"] = relationship(
        "GoalParticipant",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    posts: List["Post"] = relationship(
        "Post",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User {self.username}>"


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    """Refresh tokens for JWT authentication."""
    
    __tablename__ = "refresh_tokens"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    token_hash = Column(String(255), nullable=False, index=True)
    device_info = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user: "User" = relationship("User", back_populates="refresh_tokens")
    
    def __repr__(self) -> str:
        return f"<RefreshToken {self.id}>"


class PasswordResetToken(Base, UUIDMixin, TimestampMixin):
    """Password reset tokens."""
    
    __tablename__ = "password_reset_tokens"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<PasswordResetToken {self.id}>"


class EmailVerificationToken(Base, UUIDMixin, TimestampMixin):
    """Email verification tokens."""
    
    __tablename__ = "email_verification_tokens"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<EmailVerificationToken {self.id}>"

