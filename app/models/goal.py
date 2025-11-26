"""
Goal and accountability related models.
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer,
    Numeric, String, Text
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TimestampMixin, UUIDMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.post import Post


class Goal(BaseModel):
    """Goals for users and groups."""
    
    __tablename__ = "goals"
    
    creator_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)  # 'savings', 'fitness', 'education', etc.
    goal_type = Column(String(20), nullable=False)  # 'individual', 'group'
    
    # Target settings
    target_type = Column(String(20), nullable=True)  # 'amount', 'date', 'milestone'
    target_amount = Column(Numeric(12, 2), nullable=True)
    target_currency = Column(String(3), default="USD", nullable=True)
    target_date = Column(Date, nullable=True)
    
    # Progress
    current_amount = Column(Numeric(12, 2), default=0, nullable=False)
    progress_percentage = Column(Float, default=0, nullable=False)
    
    # Media
    image_url = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), default="active", nullable=False, index=True)  # 'active', 'completed', 'paused', 'cancelled'
    is_public = Column(Boolean, default=False, nullable=False)
    
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    creator: "User" = relationship("User", back_populates="goals_created")
    participants: List["GoalParticipant"] = relationship(
        "GoalParticipant",
        back_populates="goal",
        cascade="all, delete-orphan"
    )
    contributions: List["GoalContribution"] = relationship(
        "GoalContribution",
        back_populates="goal",
        cascade="all, delete-orphan"
    )
    milestones: List["GoalMilestone"] = relationship(
        "GoalMilestone",
        back_populates="goal",
        cascade="all, delete-orphan"
    )
    reminders: List["GoalReminder"] = relationship(
        "GoalReminder",
        back_populates="goal",
        cascade="all, delete-orphan"
    )
    posts: List["Post"] = relationship("Post", back_populates="goal")
    
    def __repr__(self) -> str:
        return f"<Goal {self.title}>"


class GoalParticipant(Base, UUIDMixin):
    """Participants in a goal."""
    
    __tablename__ = "goal_participants"
    
    goal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(String(20), default="member", nullable=False)  # 'creator', 'member', 'supporter'
    contribution_amount = Column(Numeric(12, 2), default=0, nullable=False)
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    goal: "Goal" = relationship("Goal", back_populates="participants")
    user: "User" = relationship("User", back_populates="goal_participations")
    
    def __repr__(self) -> str:
        return f"<GoalParticipant {self.user_id} in {self.goal_id}>"


class GoalContribution(Base, UUIDMixin, TimestampMixin):
    """Contributions/activities towards a goal."""
    
    __tablename__ = "goal_contributions"
    
    goal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    amount = Column(Numeric(12, 2), nullable=False)
    note = Column(Text, nullable=True)
    contribution_type = Column(
        String(20),
        default="monetary",
        nullable=False
    )  # 'monetary', 'milestone', 'checkin'
    
    # Relationships
    goal: "Goal" = relationship("Goal", back_populates="contributions")
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<GoalContribution {self.amount} to {self.goal_id}>"


class GoalMilestone(Base, UUIDMixin, TimestampMixin):
    """Milestones within a goal."""
    
    __tablename__ = "goal_milestones"
    
    goal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_value = Column(Numeric(12, 2), nullable=True)
    achieved = Column(Boolean, default=False, nullable=False)
    achieved_at = Column(DateTime(timezone=True), nullable=True)
    achieved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    order_index = Column(Integer, nullable=True)
    
    # Relationships
    goal: "Goal" = relationship("Goal", back_populates="milestones")
    achiever: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<GoalMilestone {self.title}>"


class GoalReminder(Base, UUIDMixin, TimestampMixin):
    """Reminders for goals."""
    
    __tablename__ = "goal_reminders"
    
    goal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    reminder_type = Column(String(20), nullable=True)  # 'daily', 'weekly', 'custom'
    reminder_time = Column(String(5), nullable=True)  # HH:MM format
    reminder_days = Column(ARRAY(Integer), nullable=True)  # Array of day numbers (0-6)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    goal: "Goal" = relationship("Goal", back_populates="reminders")
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<GoalReminder {self.id}>"

