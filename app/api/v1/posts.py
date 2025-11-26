"""
Posts and comments API endpoints.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.post import Post, PostLike, PostComment, CommentLike
from app.models.goal import Goal
from app.models.friendship import Friendship
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostListResponse,
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    CommentListResponse,
    LikeResponse,
    GoalPreview,
    FeedResponse,
)
from app.schemas.user import UserPublicResponse
from app.schemas.common import MessageResponse, PaginationMeta

router = APIRouter()


async def get_user_friend_ids(user_id: UUID, db: AsyncSession) -> List[UUID]:
    """Get list of friend IDs for a user."""
    result = await db.execute(
        select(Friendship).where(
            or_(
                Friendship.user_id == user_id,
                Friendship.friend_id == user_id
            ),
            Friendship.status == "accepted"
        )
    )
    friendships = result.scalars().all()
    
    friend_ids = []
    for f in friendships:
        friend_ids.append(f.friend_id if f.user_id == user_id else f.user_id)
    
    return friend_ids


@router.get("", response_model=PostListResponse)
async def get_posts(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PostListResponse:
    """
    Get posts from friends.
    
    Args:
        page: Page number
        limit: Items per page
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        PostListResponse: Paginated posts
    """
    offset = (page - 1) * limit
    friend_ids = await get_user_friend_ids(current_user.id, db)
    friend_ids.append(current_user.id)  # Include own posts
    
    query = (
        select(Post)
        .where(
            Post.user_id.in_(friend_ids),
            Post.is_archived == False,
            Post.visibility != "private"
        )
        .options(selectinload(Post.user), selectinload(Post.goal))
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    # Count total
    count_result = await db.execute(
        select(func.count(Post.id)).where(
            Post.user_id.in_(friend_ids),
            Post.is_archived == False,
            Post.visibility != "private"
        )
    )
    total = count_result.scalar() or 0
    
    # Check which posts are liked by current user
    liked_post_ids = set()
    if posts:
        post_ids = [p.id for p in posts]
        like_result = await db.execute(
            select(PostLike.post_id).where(
                PostLike.post_id.in_(post_ids),
                PostLike.user_id == current_user.id
            )
        )
        liked_post_ids = set(like_result.scalars().all())
    
    post_responses = []
    for post in posts:
        goal_preview = None
        if post.goal:
            goal_preview = GoalPreview(id=post.goal.id, title=post.goal.title)
        
        post_responses.append(PostResponse(
            id=post.id,
            user=UserPublicResponse.model_validate(post.user),
            caption=post.caption,
            media_url=post.media_url,
            media_thumbnail_url=post.media_thumbnail_url,
            post_type=post.post_type,
            goal=goal_preview,
            visibility=post.visibility,
            likes_count=post.likes_count,
            comments_count=post.comments_count,
            is_liked_by_me=post.id in liked_post_ids,
            created_at=post.created_at,
        ))
    
    return PostListResponse(
        posts=post_responses,
        pagination=PaginationMeta.create(page, limit, total)
    )


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    caption: Optional[str] = Form(None),
    goal_id: Optional[UUID] = Form(None),
    visibility: str = Form(default="friends"),
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PostResponse:
    """
    Create a new post.
    
    Args:
        caption: Post caption
        goal_id: Associated goal ID
        visibility: Post visibility
        image: Image file
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        PostResponse: Created post
    """
    # Validate file type
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # TODO: Upload to S3 and get URLs
    media_url = f"https://cdn.tribe.app/posts/{current_user.id}/{datetime.utcnow().timestamp()}.jpg"
    media_thumbnail_url = f"{media_url.replace('.jpg', '_thumb.jpg')}"
    
    # Verify goal if provided
    goal = None
    if goal_id:
        result = await db.execute(select(Goal).where(Goal.id == goal_id))
        goal = result.scalar_one_or_none()
    
    post = Post(
        user_id=current_user.id,
        caption=caption,
        post_type="photo",
        goal_id=goal_id,
        media_url=media_url,
        media_thumbnail_url=media_thumbnail_url,
        visibility=visibility,
    )
    db.add(post)
    
    # Update user stats
    current_user.photos_shared += 1
    
    await db.commit()
    await db.refresh(post)
    
    goal_preview = None
    if goal:
        goal_preview = GoalPreview(id=goal.id, title=goal.title)
    
    return PostResponse(
        id=post.id,
        user=UserPublicResponse.model_validate(current_user),
        caption=post.caption,
        media_url=post.media_url,
        media_thumbnail_url=post.media_thumbnail_url,
        post_type=post.post_type,
        goal=goal_preview,
        visibility=post.visibility,
        likes_count=0,
        comments_count=0,
        is_liked_by_me=False,
        created_at=post.created_at,
    )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PostResponse:
    """
    Get a specific post.
    
    Args:
        post_id: Post ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        PostResponse: Post details
    """
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.user), selectinload(Post.goal))
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check visibility
    if post.visibility == "private" and post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if liked by current user
    like_result = await db.execute(
        select(PostLike).where(
            PostLike.post_id == post_id,
            PostLike.user_id == current_user.id
        )
    )
    is_liked = like_result.scalar_one_or_none() is not None
    
    goal_preview = None
    if post.goal:
        goal_preview = GoalPreview(id=post.goal.id, title=post.goal.title)
    
    return PostResponse(
        id=post.id,
        user=UserPublicResponse.model_validate(post.user),
        caption=post.caption,
        media_url=post.media_url,
        media_thumbnail_url=post.media_thumbnail_url,
        post_type=post.post_type,
        goal=goal_preview,
        visibility=post.visibility,
        likes_count=post.likes_count,
        comments_count=post.comments_count,
        is_liked_by_me=is_liked,
        created_at=post.created_at,
    )


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: UUID,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PostResponse:
    """
    Update a post.
    
    Args:
        post_id: Post ID
        post_data: Post update data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        PostResponse: Updated post
    """
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own posts"
        )
    
    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)
    
    post.updated_at = datetime.utcnow()
    await db.commit()
    
    return await get_post(post_id, current_user, db)


@router.delete("/{post_id}", response_model=MessageResponse)
async def delete_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Delete a post.
    
    Args:
        post_id: Post ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts"
        )
    
    await db.delete(post)
    await db.commit()
    
    return MessageResponse(message="Post deleted successfully")


@router.post("/{post_id}/like", response_model=MessageResponse)
async def like_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Like a post.
    
    Args:
        post_id: Post ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check if already liked
    existing_like = await db.execute(
        select(PostLike).where(
            PostLike.post_id == post_id,
            PostLike.user_id == current_user.id
        )
    )
    if existing_like.scalar_one_or_none():
        return MessageResponse(message="Already liked")
    
    like = PostLike(post_id=post_id, user_id=current_user.id)
    db.add(like)
    post.likes_count += 1
    await db.commit()
    
    return MessageResponse(message="Post liked")


@router.delete("/{post_id}/like", response_model=MessageResponse)
async def unlike_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Unlike a post.
    
    Args:
        post_id: Post ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    like_result = await db.execute(
        select(PostLike).where(
            PostLike.post_id == post_id,
            PostLike.user_id == current_user.id
        )
    )
    like = like_result.scalar_one_or_none()
    
    if like:
        await db.delete(like)
        post.likes_count = max(0, post.likes_count - 1)
        await db.commit()
    
    return MessageResponse(message="Post unliked")


@router.get("/{post_id}/comments", response_model=CommentListResponse)
async def get_comments(
    post_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CommentListResponse:
    """
    Get comments on a post.
    
    Args:
        post_id: Post ID
        page: Page number
        limit: Items per page
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        CommentListResponse: Paginated comments
    """
    offset = (page - 1) * limit
    
    query = (
        select(PostComment)
        .where(PostComment.post_id == post_id, PostComment.parent_comment_id.is_(None))
        .options(selectinload(PostComment.user))
        .order_by(PostComment.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    comments = result.scalars().all()
    
    count_result = await db.execute(
        select(func.count(PostComment.id)).where(
            PostComment.post_id == post_id,
            PostComment.parent_comment_id.is_(None)
        )
    )
    total = count_result.scalar() or 0
    
    comment_responses = [
        CommentResponse(
            id=c.id,
            post_id=c.post_id,
            user=UserPublicResponse.model_validate(c.user),
            content=c.content,
            parent_comment_id=c.parent_comment_id,
            likes_count=c.likes_count,
            is_liked_by_me=False,  # TODO: Check if liked
            created_at=c.created_at,
        )
        for c in comments
    ]
    
    return CommentListResponse(
        comments=comment_responses,
        pagination=PaginationMeta.create(page, limit, total)
    )


@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: UUID,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CommentResponse:
    """
    Add a comment to a post.
    
    Args:
        post_id: Post ID
        comment_data: Comment data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        CommentResponse: Created comment
    """
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    comment = PostComment(
        post_id=post_id,
        user_id=current_user.id,
        content=comment_data.content,
        parent_comment_id=comment_data.parent_comment_id,
    )
    db.add(comment)
    post.comments_count += 1
    
    await db.commit()
    await db.refresh(comment)
    
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        user=UserPublicResponse.model_validate(current_user),
        content=comment.content,
        parent_comment_id=comment.parent_comment_id,
        likes_count=0,
        is_liked_by_me=False,
        created_at=comment.created_at,
    )


@router.delete("/comments/{comment_id}", response_model=MessageResponse)
async def delete_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Delete a comment.
    
    Args:
        comment_id: Comment ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(
        select(PostComment).where(PostComment.id == comment_id)
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments"
        )
    
    # Update post comment count
    post_result = await db.execute(select(Post).where(Post.id == comment.post_id))
    post = post_result.scalar_one_or_none()
    if post:
        post.comments_count = max(0, post.comments_count - 1)
    
    await db.delete(comment)
    await db.commit()
    
    return MessageResponse(message="Comment deleted successfully")

