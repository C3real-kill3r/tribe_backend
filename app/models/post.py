"""
Post, Story, and social content models.
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TimestampMixin, UUIDMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.goal import Goal


class Post(BaseModel):
    """Posts/memories shared by users."""
    
    __tablename__ = "posts"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    caption = Column(Text, nullable=True)
    post_type = Column(String(20), default="photo", nullable=False)  # 'photo', 'video', 'text'
    
    # Associated goal (optional)
    goal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Media
    media_url = Column(Text, nullable=False)
    media_thumbnail_url = Column(Text, nullable=True)
    media_width = Column(Integer, nullable=True)
    media_height = Column(Integer, nullable=True)
    
    # Visibility
    visibility = Column(
        String(20),
        default="friends",
        nullable=False
    )  # 'public', 'friends', 'private'
    
    # Stats
    likes_count = Column(Integer, default=0, nullable=False)
    comments_count = Column(Integer, default=0, nullable=False)
    
    # Status
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user: "User" = relationship("User", back_populates="posts")
    goal: Optional["Goal"] = relationship("Goal", back_populates="posts")
    likes: List["PostLike"] = relationship(
        "PostLike",
        back_populates="post",
        cascade="all, delete-orphan"
    )
    comments: List["PostComment"] = relationship(
        "PostComment",
        back_populates="post",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Post {self.id}>"


class Story(BaseModel):
    """24-hour ephemeral stories."""
    
    __tablename__ = "stories"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    media_url = Column(Text, nullable=False)
    media_thumbnail_url = Column(Text, nullable=True)
    media_type = Column(String(20), nullable=True)  # 'image', 'video'
    duration = Column(Integer, default=5, nullable=False)  # seconds
    
    # Stats
    views_count = Column(Integer, default=0, nullable=False)
    
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Relationships
    user: "User" = relationship("User")
    views: List["StoryView"] = relationship(
        "StoryView",
        back_populates="story",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Story {self.id}>"


class StoryView(Base, UUIDMixin):
    """Story view tracking."""
    
    __tablename__ = "story_views"
    
    story_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    viewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    viewed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    story: "Story" = relationship("Story", back_populates="views")
    viewer: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<StoryView {self.story_id} by {self.viewer_id}>"


class PostLike(Base, UUIDMixin, TimestampMixin):
    """Likes on posts."""
    
    __tablename__ = "post_likes"
    
    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Relationships
    post: "Post" = relationship("Post", back_populates="likes")
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<PostLike {self.post_id} by {self.user_id}>"


class PostComment(BaseModel):
    """Comments on posts."""
    
    __tablename__ = "post_comments"
    
    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content = Column(Text, nullable=False)
    parent_comment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("post_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Stats
    likes_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    post: "Post" = relationship("Post", back_populates="comments")
    user: "User" = relationship("User")
    parent_comment: Optional["PostComment"] = relationship(
        "PostComment",
        remote_side="PostComment.id",
        backref="replies"
    )
    likes: List["CommentLike"] = relationship(
        "CommentLike",
        back_populates="comment",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<PostComment {self.id}>"


class CommentLike(Base, UUIDMixin, TimestampMixin):
    """Likes on comments."""
    
    __tablename__ = "comment_likes"
    
    comment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("post_comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Relationships
    comment: "PostComment" = relationship("PostComment", back_populates="likes")
    user: "User" = relationship("User")
    
    def __repr__(self) -> str:
        return f"<CommentLike {self.comment_id} by {self.user_id}>"

