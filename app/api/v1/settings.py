"""
Settings API endpoints.
"""
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.settings import UserSettings, BlockedUser
from app.models.notification import NotificationPreference
from app.schemas.settings import (
    PrivacySettingsResponse,
    PrivacySettingsUpdate,
    AppearanceSettingsResponse,
    AppearanceSettingsUpdate,
    FullSettingsResponse,
    BlockedUserResponse,
    BlockedUsersListResponse,
    BlockUserRequest,
)
from app.schemas.user import UserPublicResponse
from app.schemas.common import MessageResponse

router = APIRouter()


async def get_or_create_settings(user_id: UUID, db: AsyncSession) -> UserSettings:
    """Get or create user settings."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


@router.get("", response_model=FullSettingsResponse)
async def get_all_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FullSettingsResponse:
    """
    Get all user settings.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        FullSettingsResponse: All settings
    """
    settings = await get_or_create_settings(current_user.id, db)
    
    # Get notification preferences
    notif_result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    notif_prefs = notif_result.scalar_one_or_none()
    
    if not notif_prefs:
        notif_prefs = NotificationPreference(user_id=current_user.id)
        db.add(notif_prefs)
        await db.commit()
        await db.refresh(notif_prefs)
    
    return FullSettingsResponse(
        user_id=current_user.id,
        privacy=PrivacySettingsResponse(
            profile_visibility=current_user.profile_visibility,
            online_status_visible=current_user.online_status_visible,
            appear_in_suggestions=current_user.appear_in_suggestions,
            who_can_send_friend_requests=settings.who_can_send_friend_requests,
            who_can_send_messages=settings.who_can_send_messages,
            share_activity_with_friends=settings.share_activity_with_friends,
        ),
        appearance=AppearanceSettingsResponse(
            theme_mode=settings.theme_mode,
            accent_color=settings.accent_color,
            font_size_multiplier=float(settings.font_size_multiplier),
        ),
        notifications={
            "push_enabled": notif_prefs.push_enabled,
            "email_enabled": notif_prefs.email_enabled,
            "goal_reminders": notif_prefs.goal_reminders,
            "friend_requests": notif_prefs.friend_requests,
            "messages": notif_prefs.messages,
            "achievements": notif_prefs.achievements,
        },
    )


@router.get("/privacy", response_model=PrivacySettingsResponse)
async def get_privacy_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PrivacySettingsResponse:
    """
    Get privacy settings.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        PrivacySettingsResponse: Privacy settings
    """
    settings = await get_or_create_settings(current_user.id, db)
    
    return PrivacySettingsResponse(
        profile_visibility=current_user.profile_visibility,
        online_status_visible=current_user.online_status_visible,
        appear_in_suggestions=current_user.appear_in_suggestions,
        who_can_send_friend_requests=settings.who_can_send_friend_requests,
        who_can_send_messages=settings.who_can_send_messages,
        share_activity_with_friends=settings.share_activity_with_friends,
    )


@router.put("/privacy", response_model=PrivacySettingsResponse)
async def update_privacy_settings(
    privacy_data: PrivacySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PrivacySettingsResponse:
    """
    Update privacy settings.
    
    Args:
        privacy_data: Privacy settings update
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        PrivacySettingsResponse: Updated privacy settings
    """
    settings = await get_or_create_settings(current_user.id, db)
    
    update_data = privacy_data.model_dump(exclude_unset=True)
    
    # User-level settings
    user_fields = ["profile_visibility", "online_status_visible", "appear_in_suggestions"]
    for field in user_fields:
        if field in update_data:
            setattr(current_user, field, update_data[field])
    
    # UserSettings-level settings
    settings_fields = ["who_can_send_friend_requests", "who_can_send_messages", "share_activity_with_friends"]
    for field in settings_fields:
        if field in update_data:
            setattr(settings, field, update_data[field])
    
    settings.updated_at = datetime.utcnow()
    await db.commit()
    
    return await get_privacy_settings(current_user, db)


@router.get("/appearance", response_model=AppearanceSettingsResponse)
async def get_appearance_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AppearanceSettingsResponse:
    """
    Get appearance settings.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        AppearanceSettingsResponse: Appearance settings
    """
    settings = await get_or_create_settings(current_user.id, db)
    
    return AppearanceSettingsResponse(
        theme_mode=settings.theme_mode,
        accent_color=settings.accent_color,
        font_size_multiplier=float(settings.font_size_multiplier),
    )


@router.put("/appearance", response_model=AppearanceSettingsResponse)
async def update_appearance_settings(
    appearance_data: AppearanceSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AppearanceSettingsResponse:
    """
    Update appearance settings.
    
    Args:
        appearance_data: Appearance settings update
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        AppearanceSettingsResponse: Updated appearance settings
    """
    settings = await get_or_create_settings(current_user.id, db)
    
    update_data = appearance_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    settings.updated_at = datetime.utcnow()
    await db.commit()
    
    return await get_appearance_settings(current_user, db)


@router.get("/blocked-users", response_model=BlockedUsersListResponse)
async def get_blocked_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BlockedUsersListResponse:
    """
    Get list of blocked users.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        BlockedUsersListResponse: List of blocked users
    """
    result = await db.execute(
        select(BlockedUser)
        .where(BlockedUser.blocker_id == current_user.id)
        .options(selectinload(BlockedUser.blocked))
        .order_by(BlockedUser.blocked_at.desc())
    )
    blocked_users = result.scalars().all()
    
    return BlockedUsersListResponse(
        blocked_users=[
            BlockedUserResponse(
                id=bu.id,
                user=UserPublicResponse.model_validate(bu.blocked),
                blocked_at=bu.blocked_at,
            )
            for bu in blocked_users
        ]
    )


@router.post("/blocked-users", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def block_user(
    block_data: BlockUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Block a user.
    
    Args:
        block_data: Block user request
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    if block_data.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot block yourself"
        )
    
    # Check if target user exists
    result = await db.execute(select(User).where(User.id == block_data.user_id))
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already blocked
    existing = await db.execute(
        select(BlockedUser).where(
            BlockedUser.blocker_id == current_user.id,
            BlockedUser.blocked_id == block_data.user_id
        )
    )
    if existing.scalar_one_or_none():
        return MessageResponse(message="User already blocked")
    
    blocked_user = BlockedUser(
        blocker_id=current_user.id,
        blocked_id=block_data.user_id,
        reason=block_data.reason,
    )
    db.add(blocked_user)
    await db.commit()
    
    return MessageResponse(message="User blocked successfully")


@router.delete("/blocked-users/{user_id}", response_model=MessageResponse)
async def unblock_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Unblock a user.
    
    Args:
        user_id: User ID to unblock
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(
        select(BlockedUser).where(
            BlockedUser.blocker_id == current_user.id,
            BlockedUser.blocked_id == user_id
        )
    )
    blocked_user = result.scalar_one_or_none()
    
    if not blocked_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blocked user not found"
        )
    
    await db.delete(blocked_user)
    await db.commit()
    
    return MessageResponse(message="User unblocked successfully")


@router.post("/download-data", response_model=MessageResponse)
async def request_data_download(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Request a download of all user data.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    # TODO: Implement data export job
    return MessageResponse(
        message="Your data download request has been received. You will receive an email when it's ready."
    )


@router.delete("/delete-account", response_model=MessageResponse)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Delete user account.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    # Soft delete - deactivate account
    current_user.is_active = False
    current_user.email = f"deleted_{current_user.id}@deleted.tribe.app"
    current_user.username = f"deleted_{current_user.id}"
    await db.commit()
    
    return MessageResponse(message="Account deleted successfully")

