"""
Goal related schemas.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TribeBaseModel, PaginationMeta
from app.schemas.user import UserPublicResponse


class GoalCreate(BaseModel):
    """Schema for creating a goal."""
    
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = Field(None, max_length=50)
    goal_type: str = Field(..., pattern=r"^(individual|group)$")
    target_type: Optional[str] = Field(None, pattern=r"^(amount|date|milestone)$")
    target_amount: Optional[Decimal] = Field(None, ge=0)
    target_currency: str = Field(default="USD", max_length=3)
    target_date: Optional[date] = None
    is_public: bool = False
    image_url: Optional[str] = None
    participant_ids: Optional[List[UUID]] = None


class GoalUpdate(BaseModel):
    """Schema for updating a goal."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = Field(None, max_length=50)
    target_amount: Optional[Decimal] = Field(None, ge=0)
    target_date: Optional[date] = None
    is_public: Optional[bool] = None
    image_url: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(active|completed|paused|cancelled)$")


class ParticipantPreview(TribeBaseModel):
    """Preview of a goal participant."""
    
    user_id: UUID
    profile_image_url: Optional[str] = None


class ParticipantResponse(TribeBaseModel):
    """Full participant response."""
    
    user_id: UUID
    username: str
    full_name: str
    profile_image_url: Optional[str] = None
    role: str
    contribution_amount: Decimal = Decimal("0")
    joined_at: datetime


class GoalResponse(TribeBaseModel):
    """Goal response schema."""
    
    id: UUID
    creator_id: UUID
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    goal_type: str
    target_type: Optional[str] = None
    target_amount: Optional[Decimal] = None
    target_currency: str = "USD"
    target_date: Optional[date] = None
    current_amount: Decimal = Decimal("0")
    progress_percentage: float = 0.0
    image_url: Optional[str] = None
    status: str = "active"
    is_public: bool = False
    days_remaining: Optional[int] = None
    participants_count: int = 0
    participants: Optional[List[ParticipantResponse]] = None
    participants_preview: Optional[List[ParticipantPreview]] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class GoalListResponse(TribeBaseModel):
    """Paginated goal list response."""
    
    goals: List[GoalResponse]
    pagination: PaginationMeta


class ContributionCreate(BaseModel):
    """Schema for creating a contribution."""
    
    amount: Decimal = Field(..., ge=0)
    note: Optional[str] = Field(None, max_length=500)
    contribution_type: str = Field(default="monetary", pattern=r"^(monetary|milestone|checkin)$")


class GoalProgressResponse(TribeBaseModel):
    """Goal progress after contribution."""
    
    current_amount: Decimal
    progress_percentage: float


class ContributionResponse(TribeBaseModel):
    """Contribution response."""
    
    id: UUID
    goal_id: UUID
    user_id: UUID
    amount: Decimal
    note: Optional[str] = None
    contribution_type: str
    created_at: datetime
    goal_progress: Optional[GoalProgressResponse] = None


class MilestoneCreate(BaseModel):
    """Schema for creating a milestone."""
    
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    target_value: Optional[Decimal] = Field(None, ge=0)
    order_index: Optional[int] = None


class MilestoneUpdate(BaseModel):
    """Schema for updating a milestone."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    target_value: Optional[Decimal] = Field(None, ge=0)
    achieved: Optional[bool] = None
    order_index: Optional[int] = None


class MilestoneResponse(TribeBaseModel):
    """Milestone response."""
    
    id: UUID
    goal_id: UUID
    title: str
    description: Optional[str] = None
    target_value: Optional[Decimal] = None
    achieved: bool = False
    achieved_at: Optional[datetime] = None
    achieved_by: Optional[UUID] = None
    order_index: Optional[int] = None
    created_at: datetime

