"""
User profile API endpoints.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.goal import Goal, GoalParticipant
from app.models.post import Post
from app.models.friendship import Friendship
from app.schemas.user import (
    UserUpdate,
    UserProfileResponse,
    UserPublicResponse,
    UserStatsResponse,
    ImageUploadResponse,
    FriendResponse,
)
from app.schemas.goal import GoalResponse
from app.schemas.post import PostResponse
from app.schemas.common import PaginationParams, PaginatedResponse

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
) -> UserProfileResponse:
    """
    Get current user's full profile.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        UserProfileResponse: User's full profile
    """
    return UserProfileResponse.model_validate(current_user)


@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserProfileResponse:
    """
    Update current user's profile.
    
    Args:
        user_data: Profile update data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        UserProfileResponse: Updated user profile
    """
    # Check username uniqueness if changing
    if user_data.username and user_data.username != current_user.username:
        result = await db.execute(
            select(User).where(User.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Check email uniqueness if changing
    if user_data.email and user_data.email != current_user.email:
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        # Mark email as unverified when changed
        current_user.email_verified = False
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)
    
    return UserProfileResponse.model_validate(current_user)


@router.patch("/me/profile-image", response_model=ImageUploadResponse)
async def update_profile_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ImageUploadResponse:
    """
    Update user's profile image.
    
    Args:
        image: Image file to upload
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        ImageUploadResponse: Updated image URL
    """
    # Validate file type
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # TODO: Upload to S3 and get URL
    # For now, use a placeholder URL
    image_url = f"https://cdn.tribe.app/users/{current_user.id}/profile.jpg"
    
    current_user.profile_image_url = image_url
    current_user.updated_at = datetime.utcnow()
    await db.commit()
    
    return ImageUploadResponse(
        image_url=image_url,
        updated_at=current_user.updated_at
    )


@router.patch("/me/cover-image", response_model=ImageUploadResponse)
async def update_cover_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ImageUploadResponse:
    """
    Update user's cover image.
    
    Args:
        image: Image file to upload
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        ImageUploadResponse: Updated image URL
    """
    # Validate file type
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # TODO: Upload to S3 and get URL
    image_url = f"https://cdn.tribe.app/users/{current_user.id}/cover.jpg"
    
    current_user.cover_image_url = image_url
    current_user.updated_at = datetime.utcnow()
    await db.commit()
    
    return ImageUploadResponse(
        image_url=image_url,
        updated_at=current_user.updated_at
    )


@router.get("/{user_id}", response_model=UserPublicResponse)
async def get_user_profile(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserPublicResponse:
    """
    Get a user's public profile.
    
    Args:
        user_id: Target user ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        UserPublicResponse: User's public profile
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check privacy settings
    # TODO: Implement privacy checks based on friendship status
    
    return UserPublicResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        bio=user.bio,
        profile_image_url=user.profile_image_url,
        is_verified=user.is_verified,
        goals_achieved=user.goals_achieved,
        photos_shared=user.photos_shared,
        is_online=user.online_status_visible and user.last_seen_at is not None,
        last_seen_at=user.last_seen_at if user.online_status_visible else None,
    )


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserStatsResponse:
    """
    Get user statistics.
    
    Args:
        user_id: Target user ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        UserStatsResponse: User statistics
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Count active goals
    goals_in_progress_result = await db.execute(
        select(func.count(GoalParticipant.id)).where(
            GoalParticipant.user_id == user_id,
            GoalParticipant.left_at.is_(None)
        ).join(Goal).where(Goal.status == "active")
    )
    goals_in_progress = goals_in_progress_result.scalar() or 0
    
    # Count friends
    friends_count_result = await db.execute(
        select(func.count(Friendship.id)).where(
            ((Friendship.user_id == user_id) | (Friendship.friend_id == user_id)),
            Friendship.status == "accepted"
        )
    )
    friends_count = friends_count_result.scalar() or 0
    
    return UserStatsResponse(
        goals_achieved=user.goals_achieved,
        goals_in_progress=goals_in_progress,
        photos_shared=user.photos_shared,
        friends_count=friends_count,
        achievements_count=0,  # TODO: Implement achievements
    )


@router.get("/{user_id}/goals", response_model=List[GoalResponse])
async def get_user_goals(
    user_id: UUID,
    status: Optional[str] = "active",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[GoalResponse]:
    """
    Get user's goals.
    
    Args:
        user_id: Target user ID
        status: Goal status filter
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[GoalResponse]: User's goals
    """
    query = (
        select(Goal)
        .join(GoalParticipant)
        .where(GoalParticipant.user_id == user_id)
    )
    
    if status and status != "all":
        query = query.where(Goal.status == status)
    
    query = query.order_by(Goal.created_at.desc())
    
    result = await db.execute(query)
    goals = result.scalars().all()
    
    return [GoalResponse.model_validate(goal) for goal in goals]


@router.get("/{user_id}/posts", response_model=List[PostResponse])
async def get_user_posts(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    limit: int = 20
) -> List[PostResponse]:
    """
    Get user's posts.
    
    Args:
        user_id: Target user ID
        current_user: Current authenticated user
        db: Database session
        page: Page number
        limit: Items per page
    
    Returns:
        List[PostResponse]: User's posts
    """
    offset = (page - 1) * limit
    
    query = (
        select(Post)
        .options(selectinload(Post.user))
        .where(Post.user_id == user_id, Post.is_archived == False)
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    return [
        PostResponse(
            id=post.id,
            user=UserPublicResponse.model_validate(post.user),
            caption=post.caption,
            media_url=post.media_url,
            media_thumbnail_url=post.media_thumbnail_url,
            post_type=post.post_type,
            goal=None,  # TODO: Load goal if exists
            visibility=post.visibility,
            likes_count=post.likes_count,
            comments_count=post.comments_count,
            is_liked_by_me=False,  # TODO: Check if current user liked
            created_at=post.created_at,
        )
        for post in posts
    ]


@router.get("/{user_id}/friends", response_model=List[FriendResponse])
async def get_user_friends(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    limit: int = 20
) -> List[FriendResponse]:
    """
    Get user's friends.
    
    Args:
        user_id: Target user ID
        current_user: Current authenticated user
        db: Database session
        page: Page number
        limit: Items per page
    
    Returns:
        List[FriendResponse]: User's friends
    """
    offset = (page - 1) * limit
    
    # Get friendships where user is either user_id or friend_id
    query = (
        select(Friendship)
        .where(
            ((Friendship.user_id == user_id) | (Friendship.friend_id == user_id)),
            Friendship.status == "accepted"
        )
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    friendships = result.scalars().all()
    
    friends = []
    for friendship in friendships:
        # Get the friend (the other user in the friendship)
        friend_id = friendship.friend_id if friendship.user_id == user_id else friendship.user_id
        friend_result = await db.execute(select(User).where(User.id == friend_id))
        friend = friend_result.scalar_one_or_none()
        
        if friend:
            friends.append(FriendResponse(
                id=friend.id,
                username=friend.username,
                full_name=friend.full_name,
                profile_image_url=friend.profile_image_url,
                is_online=friend.online_status_visible and friend.last_seen_at is not None,
                last_seen_at=friend.last_seen_at if friend.online_status_visible else None,
                friendship_since=friendship.accepted_at or friendship.requested_at,
                mutual_friends_count=0,  # TODO: Calculate mutual friends
            ))
    
    return friends

