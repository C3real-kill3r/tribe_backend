"""
Friendship and social connection models.
"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from app.models.base import BaseModel, TimestampMixin, UUIDMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class Friendship(Base, UUIDMixin):
    """Friendship connections between users."""
    
    __tablename__ = "friendships"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    friend_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status = Column(
        String(20),
        nullable=False,
        default="pending"
    )  # 'pending', 'accepted', 'blocked'
    requested_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("user_id != friend_id", name="check_not_self_friend"),
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        backref="friendships_initiated"
    )
    friend: Mapped["User"] = relationship(
        "User",
        foreign_keys=[friend_id],
        backref="friendships_received"
    )
    
    def __repr__(self) -> str:
        return f"<Friendship {self.user_id} -> {self.friend_id}>"


class FriendSuggestion(Base, UUIDMixin, TimestampMixin):
    """Friend suggestions for user discovery."""
    
    __tablename__ = "friend_suggestions"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    suggested_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    score = Column(Float, default=0, nullable=False)
    reason = Column(String(100), nullable=True)  # 'mutual_friends', 'common_goals', etc.
    dismissed = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        backref="friend_suggestions"
    )
    suggested_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[suggested_user_id],
        backref="suggested_to"
    )
    
    def __repr__(self) -> str:
        return f"<FriendSuggestion {self.user_id} -> {self.suggested_user_id}>"


class AccountabilityPartner(Base, UUIDMixin):
    """Accountability partner relationships."""
    
    __tablename__ = "accountability_partners"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    partner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    status = Column(String(20), default="active", nullable=False)  # 'active', 'paused', 'ended'
    check_in_frequency = Column(String(20), nullable=True)  # 'daily', 'weekly', etc.
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        backref="accountability_as_user"
    )
    partner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[partner_id],
        backref="accountability_as_partner"
    )
    
    def __repr__(self) -> str:
        return f"<AccountabilityPartner {self.user_id} <-> {self.partner_id}>"

