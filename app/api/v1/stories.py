"""
Stories API endpoints.
"""
from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.post import Story, StoryView
from app.models.friendship import Friendship
from app.schemas.post import (
    StoryCreate,
    StoryResponse,
    UserStoriesResponse,
    StoriesListResponse,
)
from app.schemas.user import UserPublicResponse
from app.schemas.common import MessageResponse

router = APIRouter()


@router.get("", response_model=StoriesListResponse)
async def get_stories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StoriesListResponse:
    """
    Get stories from friends (non-expired).
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        StoriesListResponse: Grouped stories by user
    """
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
    friendships = friend_result.scalars().all()
    
    friend_ids = [current_user.id]  # Include own stories
    for f in friendships:
        friend_ids.append(f.friend_id if f.user_id == current_user.id else f.user_id)
    
    # Get non-expired stories
    now = datetime.utcnow()
    result = await db.execute(
        select(Story)
        .where(
            Story.user_id.in_(friend_ids),
            Story.expires_at > now
        )
        .options(selectinload(Story.user), selectinload(Story.views))
        .order_by(Story.created_at.desc())
    )
    stories = result.scalars().all()
    
    # Group stories by user
    user_stories_map = {}
    for story in stories:
        user_id = story.user_id
        if user_id not in user_stories_map:
            user_stories_map[user_id] = {
                "user": story.user,
                "stories": [],
                "has_unviewed": False
            }
        
        viewed_by_me = any(v.viewer_id == current_user.id for v in story.views)
        if not viewed_by_me:
            user_stories_map[user_id]["has_unviewed"] = True
        
        user_stories_map[user_id]["stories"].append(StoryResponse(
            id=story.id,
            user_id=story.user_id,
            media_url=story.media_url,
            media_thumbnail_url=story.media_thumbnail_url,
            media_type=story.media_type or "image",
            duration=story.duration,
            views_count=story.views_count,
            viewed_by_me=viewed_by_me,
            expires_at=story.expires_at,
            created_at=story.created_at,
        ))
    
    # Convert to response format
    user_stories_list = []
    for user_id, data in user_stories_map.items():
        user_stories_list.append(UserStoriesResponse(
            user=UserPublicResponse.model_validate(data["user"]),
            stories=data["stories"],
            has_unviewed=data["has_unviewed"],
        ))
    
    # Sort: unviewed first, then by most recent story
    user_stories_list.sort(
        key=lambda x: (not x.has_unviewed, -x.stories[0].created_at.timestamp())
    )
    
    return StoriesListResponse(stories=user_stories_list)


@router.post("", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    media_type: str = Form(default="image"),
    duration: int = Form(default=5),
    media: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StoryResponse:
    """
    Create a new story.
    
    Args:
        media_type: Type of media (image/video)
        duration: Display duration in seconds
        media: Media file
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        StoryResponse: Created story
    """
    # Validate file type
    allowed_types = {
        "image": ["image/jpeg", "image/png", "image/gif", "image/webp"],
        "video": ["video/mp4", "video/quicktime", "video/webm"]
    }
    
    if media.content_type not in allowed_types.get(media_type, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type for {media_type}"
        )
    
    # TODO: Upload to S3 and get URL
    media_url = f"https://cdn.tribe.app/stories/{current_user.id}/{datetime.utcnow().timestamp()}.jpg"
    media_thumbnail_url = f"{media_url.replace('.jpg', '_thumb.jpg')}"
    
    # Story expires after 24 hours
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    story = Story(
        user_id=current_user.id,
        media_url=media_url,
        media_thumbnail_url=media_thumbnail_url,
        media_type=media_type,
        duration=duration,
        expires_at=expires_at,
    )
    db.add(story)
    await db.commit()
    await db.refresh(story)
    
    return StoryResponse(
        id=story.id,
        user_id=story.user_id,
        media_url=story.media_url,
        media_thumbnail_url=story.media_thumbnail_url,
        media_type=story.media_type or "image",
        duration=story.duration,
        views_count=0,
        viewed_by_me=False,
        expires_at=story.expires_at,
        created_at=story.created_at,
    )


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StoryResponse:
    """
    Get a specific story.
    
    Args:
        story_id: Story ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        StoryResponse: Story details
    """
    result = await db.execute(
        select(Story)
        .where(Story.id == story_id)
        .options(selectinload(Story.views))
    )
    story = result.scalar_one_or_none()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    if story.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Story has expired"
        )
    
    viewed_by_me = any(v.viewer_id == current_user.id for v in story.views)
    
    return StoryResponse(
        id=story.id,
        user_id=story.user_id,
        media_url=story.media_url,
        media_thumbnail_url=story.media_thumbnail_url,
        media_type=story.media_type or "image",
        duration=story.duration,
        views_count=story.views_count,
        viewed_by_me=viewed_by_me,
        expires_at=story.expires_at,
        created_at=story.created_at,
    )


@router.delete("/{story_id}", response_model=MessageResponse)
async def delete_story(
    story_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Delete a story.
    
    Args:
        story_id: Story ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    if story.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own stories"
        )
    
    await db.delete(story)
    await db.commit()
    
    return MessageResponse(message="Story deleted successfully")


@router.post("/{story_id}/view", response_model=MessageResponse)
async def view_story(
    story_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Mark a story as viewed.
    
    Args:
        story_id: Story ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Check if already viewed
    view_result = await db.execute(
        select(StoryView).where(
            StoryView.story_id == story_id,
            StoryView.viewer_id == current_user.id
        )
    )
    existing_view = view_result.scalar_one_or_none()
    
    if not existing_view:
        view = StoryView(
            story_id=story_id,
            viewer_id=current_user.id
        )
        db.add(view)
        story.views_count += 1
        await db.commit()
    
    return MessageResponse(message="Story viewed")


@router.get("/{story_id}/views", response_model=List[UserPublicResponse])
async def get_story_views(
    story_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[UserPublicResponse]:
    """
    Get list of users who viewed a story.
    
    Args:
        story_id: Story ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[UserPublicResponse]: Users who viewed the story
    """
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    if story.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view viewers of your own stories"
        )
    
    views_result = await db.execute(
        select(StoryView)
        .where(StoryView.story_id == story_id)
        .options(selectinload(StoryView.viewer))
        .order_by(StoryView.viewed_at.desc())
    )
    views = views_result.scalars().all()
    
    return [UserPublicResponse.model_validate(v.viewer) for v in views]

