"""
Activity, achievement, and feed models.
"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TimestampMixin, UUIDMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserActivity(Base, UUIDMixin, TimestampMixin):
    """User activity log."""
    
    __tablename__ = "user_activities"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    activity_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relationships
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<UserActivity {self.activity_type}>"


class Achievement(BaseModel):
    """Achievements/badges that users can earn."""
    
    __tablename__ = "achievements"
    
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon_url = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    points = Column(Integer, default=0, nullable=False)
    
    # Criteria
    criteria = Column(JSONB, nullable=True)  # Rules for earning the achievement
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self) -> str:
        return f"<Achievement {self.code}>"


class UserAchievement(Base, UUIDMixin):
    """Achievements earned by users."""
    
    __tablename__ = "user_achievements"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    achievement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("achievements.id", ondelete="CASCADE"),
        nullable=False
    )
    earned_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    user: "User" = relationship("User")
    achievement: "Achievement" = relationship("Achievement")
    
    def __repr__(self) -> str:
        return f"<UserAchievement {self.user_id} earned {self.achievement_id}>"


class FeedEntry(Base, UUIDMixin, TimestampMixin):
    """Feed/timeline entries."""
    
    __tablename__ = "feed_entries"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )  # Feed owner
    
    # Source
    source_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )
    entry_type = Column(String(50), nullable=False)  # 'post', 'goal_update', 'achievement', etc.
    
    # Related entities
    related_post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=True
    )
    related_goal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=True
    )
    
    # Ranking/sorting
    score = Column(Float, default=0, nullable=False)
    
    # Relationships
    user: "User" = relationship("User", foreign_keys=[user_id])
    source_user: "User" = relationship("User", foreign_keys=[source_user_id])
    
    def __repr__(self) -> str:
        return f"<FeedEntry {self.id}>"

