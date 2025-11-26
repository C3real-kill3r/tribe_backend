"""
Notifications API endpoints.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.notification import Notification, NotificationPreference, PushToken
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    PushTokenCreate,
    PushTokenResponse,
)
from app.schemas.user import UserPublicResponse
from app.schemas.common import MessageResponse, PaginationMeta

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    filter_type: Optional[str] = Query(default="all", alias="filter"),
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> NotificationListResponse:
    """
    Get user's notifications.
    
    Args:
        page: Page number
        limit: Items per page
        filter_type: Filter by notification type
        unread_only: Only return unread notifications
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        NotificationListResponse: Paginated notifications
    """
    offset = (page - 1) * limit
    
    query = (
        select(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_archived == False
        )
        .options(selectinload(Notification.related_user))
    )
    
    if unread_only:
        query = query.where(Notification.is_read == False)
    
    # Filter by type
    type_mapping = {
        "goals": ["goal_completed", "goal_update", "goal_reminder", "goal_milestone"],
        "social": ["friend_request", "friend_accepted", "post_like", "post_comment"],
        "system": ["achievement", "system_update"],
    }
    
    if filter_type and filter_type != "all":
        notification_types = type_mapping.get(filter_type, [filter_type])
        query = query.where(Notification.notification_type.in_(notification_types))
    
    # Count total
    count_query = (
        select(func.count(Notification.id))
        .where(
            Notification.user_id == current_user.id,
            Notification.is_archived == False
        )
    )
    if unread_only:
        count_query = count_query.where(Notification.is_read == False)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Count unread
    unread_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
            Notification.is_archived == False
        )
    )
    unread_count = unread_result.scalar() or 0
    
    # Get notifications
    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    notification_responses = []
    for notif in notifications:
        related_user = None
        if notif.related_user:
            related_user = UserPublicResponse.model_validate(notif.related_user)
        
        notification_responses.append(NotificationResponse(
            id=notif.id,
            notification_type=notif.notification_type,
            title=notif.title,
            message=notif.message,
            related_user=related_user,
            related_goal={"id": str(notif.related_goal_id)} if notif.related_goal_id else None,
            related_post={"id": str(notif.related_post_id)} if notif.related_post_id else None,
            image_url=notif.image_url,
            icon_type=notif.icon_type,
            icon_color=notif.icon_color,
            action_url=notif.action_url,
            is_read=notif.is_read,
            created_at=notif.created_at,
        ))
    
    pagination = PaginationMeta.create(page, limit, total)
    
    return NotificationListResponse(
        notifications=notification_responses,
        pagination=pagination,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UnreadCountResponse:
    """
    Get count of unread notifications.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        UnreadCountResponse: Unread count
    """
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
            Notification.is_archived == False
        )
    )
    count = result.scalar() or 0
    
    return UnreadCountResponse(count=count)


@router.put("/{notification_id}/read", response_model=MessageResponse)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Mark a notification as read.
    
    Args:
        notification_id: Notification ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    await db.commit()
    
    return MessageResponse(message="Notification marked as read")


@router.put("/mark-all-read", response_model=MessageResponse)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Mark all notifications as read.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
        .values(is_read=True)
    )
    await db.commit()
    
    return MessageResponse(message="All notifications marked as read")


@router.delete("/{notification_id}", response_model=MessageResponse)
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Delete (archive) a notification.
    
    Args:
        notification_id: Notification ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_archived = True
    await db.commit()
    
    return MessageResponse(message="Notification deleted")


@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> NotificationPreferenceResponse:
    """
    Get notification preferences.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        NotificationPreferenceResponse: Notification preferences
    """
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    preferences = result.scalar_one_or_none()
    
    if not preferences:
        # Create default preferences
        preferences = NotificationPreference(user_id=current_user.id)
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)
    
    return NotificationPreferenceResponse(
        push_enabled=preferences.push_enabled,
        email_enabled=preferences.email_enabled,
        goal_reminders=preferences.goal_reminders,
        friend_requests=preferences.friend_requests,
        messages=preferences.messages,
        achievements=preferences.achievements,
        post_likes=preferences.post_likes,
        post_comments=preferences.post_comments,
        goal_updates=preferences.goal_updates,
        updated_at=preferences.updated_at,
    )


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    preferences_data: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> NotificationPreferenceResponse:
    """
    Update notification preferences.
    
    Args:
        preferences_data: Preferences update data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        NotificationPreferenceResponse: Updated preferences
    """
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    preferences = result.scalar_one_or_none()
    
    if not preferences:
        preferences = NotificationPreference(user_id=current_user.id)
        db.add(preferences)
    
    update_data = preferences_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preferences, field, value)
    
    preferences.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(preferences)
    
    return NotificationPreferenceResponse(
        push_enabled=preferences.push_enabled,
        email_enabled=preferences.email_enabled,
        goal_reminders=preferences.goal_reminders,
        friend_requests=preferences.friend_requests,
        messages=preferences.messages,
        achievements=preferences.achievements,
        post_likes=preferences.post_likes,
        post_comments=preferences.post_comments,
        goal_updates=preferences.goal_updates,
        updated_at=preferences.updated_at,
    )


@router.post("/push-tokens", response_model=PushTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_push_token(
    token_data: PushTokenCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PushTokenResponse:
    """
    Register a push notification token.
    
    Args:
        token_data: Push token data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        PushTokenResponse: Registered token
    """
    # Check if token already exists
    result = await db.execute(
        select(PushToken).where(
            PushToken.user_id == current_user.id,
            PushToken.token == token_data.token
        )
    )
    existing_token = result.scalar_one_or_none()
    
    if existing_token:
        existing_token.is_active = True
        existing_token.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing_token)
        return PushTokenResponse(
            id=existing_token.id,
            token=existing_token.token,
            device_type=existing_token.device_type,
            device_id=existing_token.device_id,
            is_active=existing_token.is_active,
            created_at=existing_token.created_at,
        )
    
    # Create new token
    push_token = PushToken(
        user_id=current_user.id,
        token=token_data.token,
        device_type=token_data.device_type,
        device_id=token_data.device_id,
    )
    db.add(push_token)
    await db.commit()
    await db.refresh(push_token)
    
    return PushTokenResponse(
        id=push_token.id,
        token=push_token.token,
        device_type=push_token.device_type,
        device_id=push_token.device_id,
        is_active=push_token.is_active,
        created_at=push_token.created_at,
    )


@router.delete("/push-tokens/{token_id}", response_model=MessageResponse)
async def delete_push_token(
    token_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Delete a push notification token.
    
    Args:
        token_id: Push token ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(
        select(PushToken).where(
            PushToken.id == token_id,
            PushToken.user_id == current_user.id
        )
    )
    push_token = result.scalar_one_or_none()
    
    if not push_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Push token not found"
        )
    
    push_token.is_active = False
    await db.commit()
    
    return MessageResponse(message="Push token deleted")

