"""
Messaging and conversation models.
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TimestampMixin, UUIDMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class Conversation(BaseModel):
    """Conversations (direct, group, ai_coach)."""
    
    __tablename__ = "conversations"
    
    conversation_type = Column(
        String(20),
        nullable=False
    )  # 'direct', 'group', 'ai_coach'
    name = Column(String(255), nullable=True)  # For group chats
    image_url = Column(Text, nullable=True)  # For group chats
    
    # Group settings
    is_group = Column(Boolean, default=False, nullable=False)
    
    # Last activity
    last_message_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    participants: List["ConversationParticipant"] = relationship(
        "ConversationParticipant",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    messages: List["Message"] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    ai_coach_session: Optional["AICoachSession"] = relationship(
        "AICoachSession",
        back_populates="conversation",
        uselist=False
    )
    
    def __repr__(self) -> str:
        return f"<Conversation {self.id}>"


class ConversationParticipant(Base, UUIDMixin):
    """Participants in a conversation."""
    
    __tablename__ = "conversation_participants"
    
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(String(20), default="member", nullable=False)  # 'admin', 'member'
    
    # Read status
    last_read_at = Column(DateTime(timezone=True), nullable=True)
    unread_count = Column(Integer, default=0, nullable=False)
    
    # Settings
    is_muted = Column(Boolean, default=False, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    conversation: "Conversation" = relationship("Conversation", back_populates="participants")
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<ConversationParticipant {self.user_id} in {self.conversation_id}>"


class Message(BaseModel):
    """Messages in conversations."""
    
    __tablename__ = "messages"
    
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )  # NULL for system/AI messages
    
    # Content
    content = Column(Text, nullable=False)
    message_type = Column(
        String(20),
        default="text",
        nullable=False
    )  # 'text', 'image', 'video', 'audio', 'file', 'system', 'goal_update'
    
    # Media attachments
    media_url = Column(Text, nullable=True)
    media_thumbnail_url = Column(Text, nullable=True)
    
    # Special messages
    metadata = Column(JSONB, nullable=True)  # For system messages, goal updates, etc.
    
    # Reply/Thread
    reply_to_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Status
    is_edited = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    conversation: "Conversation" = relationship("Conversation", back_populates="messages")
    sender: Optional["User"] = relationship("User")
    reply_to: Optional["Message"] = relationship(
        "Message",
        remote_side="Message.id",
        backref="replies"
    )
    reads: List["MessageRead"] = relationship(
        "MessageRead",
        back_populates="message",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Message {self.id}>"


class MessageRead(Base, UUIDMixin):
    """Message read receipts."""
    
    __tablename__ = "message_reads"
    
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    read_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    message: "Message" = relationship("Message", back_populates="reads")
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<MessageRead {self.message_id} by {self.user_id}>"


class AICoachSession(Base, UUIDMixin, TimestampMixin):
    """AI Coach session tracking."""
    
    __tablename__ = "ai_coach_sessions"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    
    # Context
    context_summary = Column(Text, nullable=True)
    user_goals = Column(JSONB, nullable=True)  # Snapshot of user goals for context
    
    # Usage tracking
    message_count = Column(Integer, default=0, nullable=False)
    tokens_used = Column(Integer, default=0, nullable=False)
    
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_interaction_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    user: "User" = relationship("User")
    conversation: "Conversation" = relationship("Conversation", back_populates="ai_coach_session")
    
    def __repr__(self) -> str:
        return f"<AICoachSession {self.id}>"

