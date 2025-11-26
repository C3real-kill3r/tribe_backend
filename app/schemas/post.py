"""
Post, comment, and story schemas.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TribeBaseModel, PaginationMeta, TimeAgoMixin
from app.schemas.user import UserPublicResponse


class PostCreate(BaseModel):
    """Schema for creating a post."""
    
    caption: Optional[str] = Field(None, max_length=2000)
    goal_id: Optional[UUID] = None
    visibility: str = Field(default="friends", pattern=r"^(public|friends|private)$")
    # Note: media_url will be set after file upload


class PostUpdate(BaseModel):
    """Schema for updating a post."""
    
    caption: Optional[str] = Field(None, max_length=2000)
    visibility: Optional[str] = Field(None, pattern=r"^(public|friends|private)$")


class GoalPreview(TribeBaseModel):
    """Preview of associated goal."""
    
    id: UUID
    title: str


class PostResponse(TribeBaseModel, TimeAgoMixin):
    """Post response schema."""
    
    id: UUID
    user: UserPublicResponse
    caption: Optional[str] = None
    media_url: str
    media_thumbnail_url: Optional[str] = None
    post_type: str = "photo"
    goal: Optional[GoalPreview] = None
    visibility: str = "friends"
    likes_count: int = 0
    comments_count: int = 0
    is_liked_by_me: bool = False
    created_at: datetime


class PostListResponse(TribeBaseModel):
    """Paginated post list response."""
    
    posts: List[PostResponse]
    pagination: PaginationMeta


class CommentCreate(BaseModel):
    """Schema for creating a comment."""
    
    content: str = Field(..., min_length=1, max_length=1000)
    parent_comment_id: Optional[UUID] = None


class CommentUpdate(BaseModel):
    """Schema for updating a comment."""
    
    content: str = Field(..., min_length=1, max_length=1000)


class CommentResponse(TribeBaseModel, TimeAgoMixin):
    """Comment response schema."""
    
    id: UUID
    post_id: UUID
    user: UserPublicResponse
    content: str
    parent_comment_id: Optional[UUID] = None
    likes_count: int = 0
    is_liked_by_me: bool = False
    created_at: datetime
    replies: Optional[List["CommentResponse"]] = None


class CommentListResponse(TribeBaseModel):
    """Paginated comment list response."""
    
    comments: List[CommentResponse]
    pagination: PaginationMeta


class LikeResponse(TribeBaseModel):
    """Like response."""
    
    user: UserPublicResponse
    created_at: datetime


class StoryCreate(BaseModel):
    """Schema for creating a story."""
    
    media_type: str = Field(default="image", pattern=r"^(image|video)$")
    duration: int = Field(default=5, ge=1, le=30)
    # Note: media_url will be set after file upload


class StoryResponse(TribeBaseModel):
    """Story response schema."""
    
    id: UUID
    user_id: UUID
    media_url: str
    media_thumbnail_url: Optional[str] = None
    media_type: str = "image"
    duration: int = 5
    views_count: int = 0
    viewed_by_me: bool = False
    expires_at: datetime
    created_at: datetime


class UserStoriesResponse(TribeBaseModel):
    """User stories grouped response."""
    
    user: UserPublicResponse
    stories: List[StoryResponse]
    has_unviewed: bool = False


class StoriesListResponse(TribeBaseModel):
    """Stories list response."""
    
    stories: List[UserStoriesResponse]


class FeedResponse(TribeBaseModel):
    """Feed response."""
    
    posts: List[PostResponse]
    pagination: PaginationMeta

