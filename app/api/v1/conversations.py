"""
Conversations and messaging API endpoints.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.conversation import Conversation, ConversationParticipant, Message, MessageRead
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    ParticipantInfo,
    LastMessagePreview,
)
from app.schemas.user import UserPublicResponse
from app.schemas.common import MessageResponse as SimpleMessageResponse, PaginationMeta

router = APIRouter()


@router.get("", response_model=ConversationListResponse)
async def get_conversations(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ConversationListResponse:
    """
    Get user's conversations.
    
    Args:
        page: Page number
        limit: Items per page
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        ConversationListResponse: Paginated conversations
    """
    offset = (page - 1) * limit
    
    # Get conversations where user is a participant
    query = (
        select(Conversation)
        .join(ConversationParticipant)
        .where(
            ConversationParticipant.user_id == current_user.id,
            ConversationParticipant.left_at.is_(None)
        )
        .options(
            selectinload(Conversation.participants).selectinload(ConversationParticipant.user),
            selectinload(Conversation.messages)
        )
        .order_by(Conversation.last_message_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    conversations = result.scalars().unique().all()
    
    # Count total
    count_result = await db.execute(
        select(func.count(Conversation.id))
        .join(ConversationParticipant)
        .where(
            ConversationParticipant.user_id == current_user.id,
            ConversationParticipant.left_at.is_(None)
        )
    )
    total = count_result.scalar() or 0
    
    conversation_responses = []
    for conv in conversations:
        # Get participant info
        participants = []
        current_user_participant = None
        for p in conv.participants:
            if p.user:
                participants.append(ParticipantInfo(
                    user_id=p.user.id,
                    username=p.user.username,
                    full_name=p.user.full_name,
                    profile_image_url=p.user.profile_image_url,
                    role=p.role,
                ))
                if p.user_id == current_user.id:
                    current_user_participant = p
        
        # Get last message
        last_message = None
        if conv.messages:
            msg = sorted(conv.messages, key=lambda m: m.created_at, reverse=True)[0]
            sender_info = None
            if msg.sender_id:
                sender = next((p for p in conv.participants if p.user_id == msg.sender_id), None)
                if sender and sender.user:
                    sender_info = ParticipantInfo(
                        user_id=sender.user.id,
                        username=sender.user.username,
                        full_name=sender.user.full_name,
                        profile_image_url=sender.user.profile_image_url,
                        role=sender.role,
                    )
            last_message = LastMessagePreview(
                id=msg.id,
                sender=sender_info,
                content=msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                message_type=msg.message_type,
                created_at=msg.created_at,
            )
        
        conversation_responses.append(ConversationResponse(
            id=conv.id,
            conversation_type=conv.conversation_type,
            name=conv.name,
            image_url=conv.image_url,
            is_group=conv.is_group,
            participants=participants,
            participants_count=len(participants),
            last_message=last_message,
            unread_count=current_user_participant.unread_count if current_user_participant else 0,
            is_muted=current_user_participant.is_muted if current_user_participant else False,
            is_archived=current_user_participant.is_archived if current_user_participant else False,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
        ))
    
    return ConversationListResponse(
        conversations=conversation_responses,
        pagination=PaginationMeta.create(page, limit, total)
    )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ConversationResponse:
    """
    Create a new conversation.
    
    Args:
        conversation_data: Conversation data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        ConversationResponse: Created conversation
    """
    # For direct conversations, check if one already exists
    if conversation_data.conversation_type == "direct" and len(conversation_data.participant_ids) == 1:
        other_user_id = conversation_data.participant_ids[0]
        
        # Check if direct conversation already exists
        existing = await db.execute(
            select(Conversation)
            .join(ConversationParticipant, Conversation.id == ConversationParticipant.conversation_id)
            .where(
                Conversation.conversation_type == "direct",
                ConversationParticipant.user_id == current_user.id
            )
        )
        for conv in existing.scalars().all():
            participant_ids = [p.user_id for p in conv.participants]
            if other_user_id in participant_ids and current_user.id in participant_ids:
                # Return existing conversation
                return await get_conversation(conv.id, current_user, db)
    
    # Create conversation
    conversation = Conversation(
        conversation_type=conversation_data.conversation_type,
        name=conversation_data.name if conversation_data.conversation_type == "group" else None,
        is_group=conversation_data.conversation_type == "group",
    )
    db.add(conversation)
    await db.flush()
    
    # Add current user as admin (for groups) or member
    role = "admin" if conversation_data.conversation_type == "group" else "member"
    creator_participant = ConversationParticipant(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role=role,
    )
    db.add(creator_participant)
    
    # Add other participants
    for participant_id in conversation_data.participant_ids:
        if participant_id != current_user.id:
            participant = ConversationParticipant(
                conversation_id=conversation.id,
                user_id=participant_id,
                role="member",
            )
            db.add(participant)
    
    await db.commit()
    
    return await get_conversation(conversation.id, current_user, db)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ConversationResponse:
    """
    Get a specific conversation.
    
    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        ConversationResponse: Conversation details
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            selectinload(Conversation.participants).selectinload(ConversationParticipant.user),
            selectinload(Conversation.messages)
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Verify user is a participant
    is_participant = any(
        p.user_id == current_user.id and p.left_at is None
        for p in conversation.participants
    )
    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Build response (similar to get_conversations)
    participants = []
    current_user_participant = None
    for p in conversation.participants:
        if p.user:
            participants.append(ParticipantInfo(
                user_id=p.user.id,
                username=p.user.username,
                full_name=p.user.full_name,
                profile_image_url=p.user.profile_image_url,
                role=p.role,
            ))
            if p.user_id == current_user.id:
                current_user_participant = p
    
    last_message = None
    if conversation.messages:
        msg = sorted(conversation.messages, key=lambda m: m.created_at, reverse=True)[0]
        sender_info = None
        if msg.sender_id:
            sender = next((p for p in conversation.participants if p.user_id == msg.sender_id), None)
            if sender and sender.user:
                sender_info = ParticipantInfo(
                    user_id=sender.user.id,
                    username=sender.user.username,
                    full_name=sender.user.full_name,
                    profile_image_url=sender.user.profile_image_url,
                    role=sender.role,
                )
        last_message = LastMessagePreview(
            id=msg.id,
            sender=sender_info,
            content=msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
            message_type=msg.message_type,
            created_at=msg.created_at,
        )
    
    return ConversationResponse(
        id=conversation.id,
        conversation_type=conversation.conversation_type,
        name=conversation.name,
        image_url=conversation.image_url,
        is_group=conversation.is_group,
        participants=participants,
        participants_count=len(participants),
        last_message=last_message,
        unread_count=current_user_participant.unread_count if current_user_participant else 0,
        is_muted=current_user_participant.is_muted if current_user_participant else False,
        is_archived=current_user_participant.is_archived if current_user_participant else False,
        last_message_at=conversation.last_message_at,
        created_at=conversation.created_at,
    )


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    conversation_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    before: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageListResponse:
    """
    Get messages in a conversation.
    
    Args:
        conversation_id: Conversation ID
        page: Page number
        limit: Items per page
        before: Get messages before this message ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageListResponse: Messages in the conversation
    """
    # Verify user is a participant
    participant_result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id,
            ConversationParticipant.left_at.is_(None)
        )
    )
    if not participant_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    query = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.is_deleted == False
        )
        .options(selectinload(Message.sender))
        .order_by(Message.created_at.desc())
        .limit(limit + 1)  # Get one extra to check if there are more
    )
    
    if before:
        before_msg = await db.execute(select(Message).where(Message.id == before))
        before_msg = before_msg.scalar_one_or_none()
        if before_msg:
            query = query.where(Message.created_at < before_msg.created_at)
    
    result = await db.execute(query)
    messages = list(result.scalars().all())
    
    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]
    
    message_responses = []
    for msg in reversed(messages):  # Return in chronological order
        sender = None
        if msg.sender:
            sender = UserPublicResponse.model_validate(msg.sender)
        
        message_responses.append(MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            sender=sender,
            content=msg.content,
            message_type=msg.message_type,
            media_url=msg.media_url,
            media_thumbnail_url=msg.media_thumbnail_url,
            metadata=msg.message_metadata,
            is_edited=msg.is_edited,
            is_deleted=msg.is_deleted,
            created_at=msg.created_at,
        ))
    
    next_cursor = messages[-1].id if has_more and messages else None
    
    return MessageListResponse(
        messages=message_responses,
        has_more=has_more,
        next_cursor=next_cursor,
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: UUID,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Send a message in a conversation.
    
    Args:
        conversation_id: Conversation ID
        message_data: Message data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Sent message
    """
    # Verify conversation exists and user is a participant
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.participants))
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    is_participant = any(
        p.user_id == current_user.id and p.left_at is None
        for p in conversation.participants
    )
    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Create message
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=message_data.content,
        message_type=message_data.message_type,
        reply_to_message_id=message_data.reply_to_message_id,
    )
    db.add(message)
    
    # Update conversation last message time
    conversation.last_message_at = datetime.utcnow()
    
    # Increment unread count for other participants
    for p in conversation.participants:
        if p.user_id != current_user.id:
            p.unread_count += 1
    
    await db.commit()
    await db.refresh(message)
    
    # Broadcast new message via WebSocket
    from app.api.v1.websocket import broadcast_new_message
    message_data = {
        "id": str(message.id),
        "conversation_id": str(message.conversation_id),
        "sender": {
            "id": str(current_user.id),
            "username": current_user.username,
            "full_name": current_user.full_name,
            "profile_image_url": current_user.profile_image_url
        },
        "content": message.content,
        "message_type": message.message_type,
        "created_at": message.created_at.isoformat()
    }
    await broadcast_new_message(conversation_id, message_data, exclude_user_id=current_user.id)
    
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender=UserPublicResponse.model_validate(current_user),
        content=message.content,
        message_type=message.message_type,
        media_url=message.media_url,
        media_thumbnail_url=message.media_thumbnail_url,
        metadata=message.message_metadata,
        is_edited=message.is_edited,
        is_deleted=message.is_deleted,
        created_at=message.created_at,
    )


@router.post("/{conversation_id}/read", response_model=SimpleMessageResponse)
async def mark_conversation_read(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SimpleMessageResponse:
    """
    Mark all messages in a conversation as read.
    
    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        SimpleMessageResponse: Success message
    """
    result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id
        )
    )
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    participant.last_read_at = datetime.utcnow()
    participant.unread_count = 0
    await db.commit()
    
    return SimpleMessageResponse(message="Conversation marked as read")

