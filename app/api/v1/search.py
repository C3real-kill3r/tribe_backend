"""
Search API endpoints.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.goal import Goal, GoalParticipant
from app.models.post import Post
from app.models.friendship import Friendship
from app.schemas.user import UserPublicResponse
from app.schemas.goal import GoalResponse
from app.schemas.post import PostResponse, GoalPreview
from app.schemas.common import TribeBaseModel

router = APIRouter()


class SearchResultsResponse(TribeBaseModel):
    """Combined search results."""
    users: List[UserPublicResponse]
    goals: List[GoalResponse]
    posts: List[PostResponse]


@router.get("", response_model=SearchResultsResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    type: str = Query(default="all", description="Search type: all, users, goals, posts"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SearchResultsResponse:
    """
    Search across users, goals, and posts.
    
    Args:
        q: Search query
        type: Type of content to search
        page: Page number
        limit: Items per page
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        SearchResultsResponse: Search results
    """
    search_term = f"%{q.lower()}%"
    offset = (page - 1) * limit
    
    users = []
    goals = []
    posts = []
    
    # Search users
    if type in ["all", "users"]:
        user_query = (
            select(User)
            .where(
                User.id != current_user.id,
                User.is_active == True,
                or_(
                    func.lower(User.username).like(search_term),
                    func.lower(User.full_name).like(search_term)
                )
            )
            .offset(offset)
            .limit(limit if type == "users" else 5)
        )
        result = await db.execute(user_query)
        users = [UserPublicResponse.model_validate(u) for u in result.scalars().all()]
    
    # Search goals
    if type in ["all", "goals"]:
        goal_query = (
            select(Goal)
            .where(
                Goal.is_public == True,
                Goal.status == "active",
                or_(
                    func.lower(Goal.title).like(search_term),
                    func.lower(Goal.description).like(search_term)
                )
            )
            .offset(offset)
            .limit(limit if type == "goals" else 5)
        )
        result = await db.execute(goal_query)
        
        for goal in result.scalars().all():
            # Count participants
            participant_count = await db.execute(
                select(func.count(GoalParticipant.id)).where(
                    GoalParticipant.goal_id == goal.id
                )
            )
            count = participant_count.scalar() or 0
            
            goals.append(GoalResponse(
                id=goal.id,
                creator_id=goal.creator_id,
                title=goal.title,
                description=goal.description,
                category=goal.category,
                goal_type=goal.goal_type,
                target_type=goal.target_type,
                target_amount=goal.target_amount,
                target_currency=goal.target_currency,
                target_date=goal.target_date,
                current_amount=goal.current_amount,
                progress_percentage=goal.progress_percentage,
                image_url=goal.image_url,
                status=goal.status,
                is_public=goal.is_public,
                participants_count=count,
                created_at=goal.created_at,
                updated_at=goal.updated_at,
            ))
    
    # Search posts
    if type in ["all", "posts"]:
        # Get friend IDs for visibility filtering
        friend_result = await db.execute(
            select(Friendship).where(
                or_(
                    Friendship.user_id == current_user.id,
                    Friendship.friend_id == current_user.id
                ),
                Friendship.status == "accepted"
            )
        )
        friend_ids = [current_user.id]
        for f in friend_result.scalars().all():
            friend_ids.append(
                f.friend_id if f.user_id == current_user.id else f.user_id
            )
        
        post_query = (
            select(Post)
            .where(
                Post.is_archived == False,
                or_(
                    Post.visibility == "public",
                    Post.user_id.in_(friend_ids)
                ),
                func.lower(Post.caption).like(search_term)
            )
            .offset(offset)
            .limit(limit if type == "posts" else 5)
        )
        result = await db.execute(post_query)
        
        for post in result.scalars().all():
            # Get user
            user_result = await db.execute(select(User).where(User.id == post.user_id))
            user = user_result.scalar_one_or_none()
            
            if user:
                posts.append(PostResponse(
                    id=post.id,
                    user=UserPublicResponse.model_validate(user),
                    caption=post.caption,
                    media_url=post.media_url,
                    media_thumbnail_url=post.media_thumbnail_url,
                    post_type=post.post_type,
                    goal=None,
                    visibility=post.visibility,
                    likes_count=post.likes_count,
                    comments_count=post.comments_count,
                    is_liked_by_me=False,
                    created_at=post.created_at,
                ))
    
    return SearchResultsResponse(users=users, goals=goals, posts=posts)


@router.get("/users", response_model=List[UserPublicResponse])
async def search_users(
    q: str = Query(..., min_length=1),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[UserPublicResponse]:
    """
    Search for users.
    
    Args:
        q: Search query
        page: Page number
        limit: Items per page
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[UserPublicResponse]: Search results
    """
    search_term = f"%{q.lower()}%"
    offset = (page - 1) * limit
    
    query = (
        select(User)
        .where(
            User.id != current_user.id,
            User.is_active == True,
            or_(
                func.lower(User.username).like(search_term),
                func.lower(User.full_name).like(search_term)
            )
        )
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    return [UserPublicResponse.model_validate(u) for u in result.scalars().all()]


@router.get("/goals", response_model=List[GoalResponse])
async def search_goals(
    q: str = Query(..., min_length=1),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[GoalResponse]:
    """
    Search for public goals.
    
    Args:
        q: Search query
        page: Page number
        limit: Items per page
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[GoalResponse]: Search results
    """
    search_term = f"%{q.lower()}%"
    offset = (page - 1) * limit
    
    query = (
        select(Goal)
        .where(
            Goal.is_public == True,
            Goal.status == "active",
            or_(
                func.lower(Goal.title).like(search_term),
                func.lower(Goal.description).like(search_term)
            )
        )
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    goals = []
    
    for goal in result.scalars().all():
        participant_count = await db.execute(
            select(func.count(GoalParticipant.id)).where(
                GoalParticipant.goal_id == goal.id
            )
        )
        count = participant_count.scalar() or 0
        
        goals.append(GoalResponse(
            id=goal.id,
            creator_id=goal.creator_id,
            title=goal.title,
            description=goal.description,
            category=goal.category,
            goal_type=goal.goal_type,
            target_type=goal.target_type,
            target_amount=goal.target_amount,
            target_currency=goal.target_currency,
            target_date=goal.target_date,
            current_amount=goal.current_amount,
            progress_percentage=goal.progress_percentage,
            image_url=goal.image_url,
            status=goal.status,
            is_public=goal.is_public,
            participants_count=count,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        ))
    
    return goals


@router.get("/posts", response_model=List[PostResponse])
async def search_posts(
    q: str = Query(..., min_length=1),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[PostResponse]:
    """
    Search for posts.
    
    Args:
        q: Search query
        page: Page number
        limit: Items per page
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[PostResponse]: Search results
    """
    search_term = f"%{q.lower()}%"
    offset = (page - 1) * limit
    
    # Get friend IDs
    friend_result = await db.execute(
        select(Friendship).where(
            or_(
                Friendship.user_id == current_user.id,
                Friendship.friend_id == current_user.id
            ),
            Friendship.status == "accepted"
        )
    )
    friend_ids = [current_user.id]
    for f in friend_result.scalars().all():
        friend_ids.append(f.friend_id if f.user_id == current_user.id else f.user_id)
    
    query = (
        select(Post)
        .where(
            Post.is_archived == False,
            or_(
                Post.visibility == "public",
                Post.user_id.in_(friend_ids)
            ),
            func.lower(Post.caption).like(search_term)
        )
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    posts = []
    
    for post in result.scalars().all():
        user_result = await db.execute(select(User).where(User.id == post.user_id))
        user = user_result.scalar_one_or_none()
        
        if user:
            posts.append(PostResponse(
                id=post.id,
                user=UserPublicResponse.model_validate(user),
                caption=post.caption,
                media_url=post.media_url,
                media_thumbnail_url=post.media_thumbnail_url,
                post_type=post.post_type,
                goal=None,
                visibility=post.visibility,
                likes_count=post.likes_count,
                comments_count=post.comments_count,
                is_liked_by_me=False,
                created_at=post.created_at,
            ))
    
    return posts

