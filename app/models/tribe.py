"""
Tribe (group) related models.
"""
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from app.models.base import BaseModel, TimestampMixin, UUIDMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class Tribe(BaseModel):
    """Tribes (groups with shared goals)."""
    
    __tablename__ = "tribes"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    cover_image_url = Column(Text, nullable=True)
    
    # Settings
    is_private = Column(Boolean, default=False, nullable=False)
    require_approval = Column(Boolean, default=True, nullable=False)
    
    # Stats
    member_count = Column(Integer, default=0, nullable=False)
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Relationships
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    members: Mapped[List["TribeMember"]] = relationship(
        "TribeMember",
        back_populates="tribe",
        cascade="all, delete-orphan"
    )
    invitations: Mapped[List["TribeInvitation"]] = relationship(
        "TribeInvitation",
        back_populates="tribe",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Tribe {self.name}>"


class TribeMember(Base, UUIDMixin):
    """Tribe members."""
    
    __tablename__ = "tribe_members"
    
    tribe_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tribes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(String(20), default="member", nullable=False)  # 'admin', 'moderator', 'member'
    
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tribe: Mapped["Tribe"] = relationship("Tribe", back_populates="members")
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self) -> str:
        return f"<TribeMember {self.user_id} in {self.tribe_id}>"


class TribeInvitation(Base, UUIDMixin, TimestampMixin):
    """Tribe invitations."""
    
    __tablename__ = "tribe_invitations"
    
    tribe_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tribes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    inviter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    invitee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status = Column(String(20), default="pending", nullable=False)  # 'pending', 'accepted', 'declined'
    
    responded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tribe: Mapped["Tribe"] = relationship("Tribe", back_populates="invitations")
    inviter: Mapped["User"] = relationship("User", foreign_keys=[inviter_id])
    invitee: Mapped["User"] = relationship("User", foreign_keys=[invitee_id])
    
    def __repr__(self) -> str:
        return f"<TribeInvitation {self.id}>"

