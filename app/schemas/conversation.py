"""
Conversation and messaging schemas.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TribeBaseModel, PaginationMeta, TimeAgoMixin
from app.schemas.user import UserPublicResponse


class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""
    
    conversation_type: str = Field(default="direct", pattern=r"^(direct|group)$")
    participant_ids: List[UUID] = Field(..., min_length=1)
    name: Optional[str] = Field(None, max_length=255)  # For group chats


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""
    
    name: Optional[str] = Field(None, max_length=255)
    image_url: Optional[str] = None


class ParticipantInfo(TribeBaseModel):
    """Participant info in conversation."""
    
    user_id: UUID
    username: str
    full_name: str
    profile_image_url: Optional[str] = None
    role: str = "member"


class LastMessagePreview(TribeBaseModel):
    """Preview of last message in conversation."""
    
    id: UUID
    sender: Optional[ParticipantInfo] = None
    content: str
    message_type: str = "text"
    created_at: datetime


class ConversationResponse(TribeBaseModel):
    """Conversation response schema."""
    
    id: UUID
    conversation_type: str
    name: Optional[str] = None
    image_url: Optional[str] = None
    is_group: bool = False
    participants: List[ParticipantInfo]
    participants_count: int = 0
    last_message: Optional[LastMessagePreview] = None
    unread_count: int = 0
    is_muted: bool = False
    is_archived: bool = False
    last_message_at: Optional[datetime] = None
    created_at: datetime


class ConversationListResponse(TribeBaseModel):
    """Paginated conversation list response."""
    
    conversations: List[ConversationResponse]
    pagination: PaginationMeta


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: str = Field(default="text", pattern=r"^(text|image|video|audio|file)$")
    reply_to_message_id: Optional[UUID] = None
    # Note: media_url will be set after file upload if message_type is not text


class MessageUpdate(BaseModel):
    """Schema for updating a message."""
    
    content: str = Field(..., min_length=1, max_length=5000)


class ReadReceipt(TribeBaseModel):
    """Read receipt info."""
    
    user_id: UUID
    read_at: datetime


class MessageResponse(TribeBaseModel, TimeAgoMixin):
    """Message response schema."""
    
    id: UUID
    conversation_id: UUID
    sender: Optional[UserPublicResponse] = None
    content: str
    message_type: str = "text"
    media_url: Optional[str] = None
    media_thumbnail_url: Optional[str] = None
    metadata: Optional[dict] = None
    reply_to_message: Optional["MessageResponse"] = None
    is_edited: bool = False
    is_deleted: bool = False
    read_by: Optional[List[ReadReceipt]] = None
    created_at: datetime


class MessageListResponse(TribeBaseModel):
    """Paginated message list response."""
    
    messages: List[MessageResponse]
    has_more: bool = False
    next_cursor: Optional[UUID] = None


class TypingIndicator(TribeBaseModel):
    """Typing indicator event."""
    
    conversation_id: UUID
    user: UserPublicResponse
    is_typing: bool = True


class AICoachChatRequest(BaseModel):
    """Request for AI coach chat."""
    
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[UUID] = None
    context: Optional[dict] = None


class AICoachSuggestion(TribeBaseModel):
    """AI coach suggestion."""
    
    text: str


class AICoachChatResponse(TribeBaseModel):
    """Response from AI coach."""
    
    message: MessageResponse
    suggestions: Optional[List[str]] = None

