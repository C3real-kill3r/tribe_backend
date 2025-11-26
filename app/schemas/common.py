"""
Common schemas used across the API.
"""
from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TribeBaseModel(BaseModel):
    """Base model with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )


class MessageResponse(TribeBaseModel):
    """Generic message response."""
    
    message: str
    success: bool = True


class ErrorResponse(TribeBaseModel):
    """Error response model."""
    
    detail: str
    code: Optional[str] = None


class PaginationParams(BaseModel):
    """Pagination parameters."""
    
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.limit


class PaginationMeta(TribeBaseModel):
    """Pagination metadata."""
    
    page: int
    limit: int
    total: int
    total_pages: int
    has_more: bool = False
    
    @classmethod
    def create(cls, page: int, limit: int, total: int) -> "PaginationMeta":
        """Create pagination metadata."""
        total_pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
            has_more=page < total_pages
        )


T = TypeVar("T")


class PaginatedResponse(TribeBaseModel, Generic[T]):
    """Generic paginated response."""
    
    items: List[T]
    pagination: PaginationMeta


class TimestampMixin(TribeBaseModel):
    """Mixin for timestamp fields."""
    
    created_at: datetime
    updated_at: datetime


class TimeAgoMixin(TribeBaseModel):
    """Mixin that includes time_ago field."""
    
    created_at: datetime
    time_ago: Optional[str] = None
    
    def model_post_init(self, __context: Any) -> None:
        """Calculate time_ago after model initialization."""
        if self.time_ago is None and self.created_at:
            self.time_ago = self._calculate_time_ago(self.created_at)
    
    @staticmethod
    def _calculate_time_ago(dt: datetime) -> str:
        """Calculate human-readable time ago string."""
        now = datetime.utcnow()
        diff = now - dt.replace(tzinfo=None) if dt.tzinfo else now - dt
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds // 86400)
            return f"{days} day{'s' if days > 1 else ''} ago"
        elif seconds < 2592000:
            weeks = int(seconds // 604800)
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            months = int(seconds // 2592000)
            return f"{months} month{'s' if months > 1 else ''} ago"

