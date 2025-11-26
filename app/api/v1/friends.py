"""
Friends and social API endpoints.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.friendship import Friendship, FriendSuggestion
from app.schemas.user import (
    FriendResponse,
    FriendRequestResponse,
    FriendSuggestionResponse,
    UserPublicResponse,
)
from app.schemas.common import MessageResponse, PaginationMeta

router = APIRouter()


@router.get("", response_model=List[FriendResponse])
async def get_friends(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="recent", pattern=r"^(recent|alphabetical|active)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[FriendResponse]:
    """
    Get current user's friends list.
    
    Args:
        page: Page number
        limit: Items per page
        sort: Sort order
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[FriendResponse]: Friends list
    """
    offset = (page - 1) * limit
    
    # Get accepted friendships
    query = (
        select(Friendship)
        .where(
            or_(
                Friendship.user_id == current_user.id,
                Friendship.friend_id == current_user.id
            ),
            Friendship.status == "accepted"
        )
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    friendships = result.scalars().all()
    
    friends = []
    for friendship in friendships:
        friend_id = (
            friendship.friend_id 
            if friendship.user_id == current_user.id 
            else friendship.user_id
        )
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
                mutual_friends_count=0,
            ))
    
    # Sort friends
    if sort == "alphabetical":
        friends.sort(key=lambda f: f.full_name.lower())
    elif sort == "active":
        friends.sort(key=lambda f: f.last_seen_at or datetime.min, reverse=True)
    # 'recent' is default order from query
    
    return friends


@router.get("/requests", response_model=List[FriendRequestResponse])
async def get_friend_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[FriendRequestResponse]:
    """
    Get pending friend requests received by the user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[FriendRequestResponse]: Pending friend requests
    """
    query = (
        select(Friendship)
        .where(
            Friendship.friend_id == current_user.id,
            Friendship.status == "pending"
        )
        .order_by(Friendship.requested_at.desc())
    )
    
    result = await db.execute(query)
    requests = result.scalars().all()
    
    responses = []
    for request in requests:
        user_result = await db.execute(select(User).where(User.id == request.user_id))
        user = user_result.scalar_one_or_none()
        
        responses.append(FriendRequestResponse(
            id=request.id,
            user_id=request.user_id,
            friend_id=request.friend_id,
            status=request.status,
            requested_at=request.requested_at,
            user=UserPublicResponse.model_validate(user) if user else None,
        ))
    
    return responses


@router.post("/requests", response_model=FriendRequestResponse, status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FriendRequestResponse:
    """
    Send a friend request to another user.
    
    Args:
        user_id: Target user ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        FriendRequestResponse: Created friend request
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send friend request to yourself"
        )
    
    # Check if target user exists
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check for existing friendship/request
    existing_query = select(Friendship).where(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.friend_id == user_id),
            and_(Friendship.user_id == user_id, Friendship.friend_id == current_user.id)
        )
    )
    result = await db.execute(existing_query)
    existing = result.scalar_one_or_none()
    
    if existing:
        if existing.status == "accepted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already friends with this user"
            )
        elif existing.status == "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Friend request already pending"
            )
        elif existing.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send friend request"
            )
    
    # Create friend request
    friendship = Friendship(
        user_id=current_user.id,
        friend_id=user_id,
        status="pending",
        requested_at=datetime.utcnow()
    )
    db.add(friendship)
    await db.commit()
    await db.refresh(friendship)
    
    return FriendRequestResponse(
        id=friendship.id,
        user_id=friendship.user_id,
        friend_id=friendship.friend_id,
        status=friendship.status,
        requested_at=friendship.requested_at,
    )


@router.put("/requests/{request_id}/accept", response_model=MessageResponse)
async def accept_friend_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Accept a friend request.
    
    Args:
        request_id: Friend request ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(
        select(Friendship).where(
            Friendship.id == request_id,
            Friendship.friend_id == current_user.id,
            Friendship.status == "pending"
        )
    )
    friendship = result.scalar_one_or_none()
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found"
        )
    
    friendship.status = "accepted"
    friendship.accepted_at = datetime.utcnow()
    await db.commit()
    
    return MessageResponse(message="Friend request accepted")


@router.put("/requests/{request_id}/decline", response_model=MessageResponse)
async def decline_friend_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Decline a friend request.
    
    Args:
        request_id: Friend request ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(
        select(Friendship).where(
            Friendship.id == request_id,
            Friendship.friend_id == current_user.id,
            Friendship.status == "pending"
        )
    )
    friendship = result.scalar_one_or_none()
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found"
        )
    
    await db.delete(friendship)
    await db.commit()
    
    return MessageResponse(message="Friend request declined")


@router.delete("/{friend_id}", response_model=MessageResponse)
async def remove_friend(
    friend_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Remove a friend.
    
    Args:
        friend_id: Friend's user ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(
        select(Friendship).where(
            or_(
                and_(
                    Friendship.user_id == current_user.id,
                    Friendship.friend_id == friend_id
                ),
                and_(
                    Friendship.user_id == friend_id,
                    Friendship.friend_id == current_user.id
                )
            ),
            Friendship.status == "accepted"
        )
    )
    friendship = result.scalar_one_or_none()
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friendship not found"
        )
    
    await db.delete(friendship)
    await db.commit()
    
    return MessageResponse(message="Friend removed")


@router.get("/suggestions", response_model=List[FriendSuggestionResponse])
async def get_friend_suggestions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[FriendSuggestionResponse]:
    """
    Get friend suggestions for the user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[FriendSuggestionResponse]: Friend suggestions
    """
    # Get stored suggestions
    query = (
        select(FriendSuggestion)
        .where(
            FriendSuggestion.user_id == current_user.id,
            FriendSuggestion.dismissed == False
        )
        .order_by(FriendSuggestion.score.desc())
        .limit(10)
    )
    
    result = await db.execute(query)
    suggestions = result.scalars().all()
    
    responses = []
    for suggestion in suggestions:
        user_result = await db.execute(
            select(User).where(User.id == suggestion.suggested_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            responses.append(FriendSuggestionResponse(
                user=UserPublicResponse.model_validate(user),
                reason=suggestion.reason,
                mutual_friends_count=0,  # TODO: Calculate
                common_goals=0,  # TODO: Calculate
            ))
    
    return responses


@router.post("/suggestions/{user_id}/dismiss", response_model=MessageResponse)
async def dismiss_suggestion(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Dismiss a friend suggestion.
    
    Args:
        user_id: Suggested user ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(
        select(FriendSuggestion).where(
            FriendSuggestion.user_id == current_user.id,
            FriendSuggestion.suggested_user_id == user_id
        )
    )
    suggestion = result.scalar_one_or_none()
    
    if suggestion:
        suggestion.dismissed = True
        await db.commit()
    
    return MessageResponse(message="Suggestion dismissed")


@router.get("/search", response_model=List[UserPublicResponse])
async def search_friends(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[UserPublicResponse]:
    """
    Search for users to add as friends.
    
    Args:
        q: Search query
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[UserPublicResponse]: Search results
    """
    search_term = f"%{q.lower()}%"
    
    query = (
        select(User)
        .where(
            User.id != current_user.id,
            User.is_active == True,
            User.appear_in_suggestions == True,
            or_(
                func.lower(User.username).like(search_term),
                func.lower(User.full_name).like(search_term)
            )
        )
        .limit(20)
    )
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [UserPublicResponse.model_validate(user) for user in users]


@router.get("/online", response_model=List[FriendResponse])
async def get_online_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[FriendResponse]:
    """
    Get friends who are currently online.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[FriendResponse]: Online friends
    """
    # Get accepted friendships
    query = (
        select(Friendship)
        .where(
            or_(
                Friendship.user_id == current_user.id,
                Friendship.friend_id == current_user.id
            ),
            Friendship.status == "accepted"
        )
    )
    
    result = await db.execute(query)
    friendships = result.scalars().all()
    
    online_friends = []
    for friendship in friendships:
        friend_id = (
            friendship.friend_id 
            if friendship.user_id == current_user.id 
            else friendship.user_id
        )
        friend_result = await db.execute(select(User).where(User.id == friend_id))
        friend = friend_result.scalar_one_or_none()
        
        # Check if friend is online (has been seen in last 5 minutes)
        if friend and friend.last_seen_at:
            time_since_seen = datetime.utcnow() - friend.last_seen_at.replace(tzinfo=None)
            is_online = time_since_seen.total_seconds() < 300  # 5 minutes
            
            if is_online and friend.online_status_visible:
                online_friends.append(FriendResponse(
                    id=friend.id,
                    username=friend.username,
                    full_name=friend.full_name,
                    profile_image_url=friend.profile_image_url,
                    is_online=True,
                    last_seen_at=friend.last_seen_at,
                    friendship_since=friendship.accepted_at or friendship.requested_at,
                    mutual_friends_count=0,
                ))
    
    return online_friends

