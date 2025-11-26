"""
Goals API endpoints.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.goal import Goal, GoalParticipant, GoalContribution, GoalMilestone
from app.schemas.goal import (
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    GoalListResponse,
    ContributionCreate,
    ContributionResponse,
    GoalProgressResponse,
    MilestoneCreate,
    MilestoneUpdate,
    MilestoneResponse,
    ParticipantResponse,
    ParticipantPreview,
)
from app.schemas.common import MessageResponse, PaginationMeta

router = APIRouter()


def calculate_days_remaining(target_date: Optional[date]) -> Optional[int]:
    """Calculate days remaining until target date."""
    if not target_date:
        return None
    today = date.today()
    delta = target_date - today
    return delta.days


@router.get("", response_model=GoalListResponse)
async def get_goals(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(default="active", alias="status"),
    category: Optional[str] = None,
    goal_type: Optional[str] = Query(default=None, alias="type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> GoalListResponse:
    """
    Get user's goals.
    
    Args:
        page: Page number
        limit: Items per page
        status_filter: Goal status filter
        category: Category filter
        goal_type: Goal type filter
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        GoalListResponse: Paginated list of goals
    """
    offset = (page - 1) * limit
    
    # Build query for goals the user participates in
    query = (
        select(Goal)
        .join(GoalParticipant)
        .where(
            GoalParticipant.user_id == current_user.id,
            GoalParticipant.left_at.is_(None)
        )
        .options(selectinload(Goal.participants))
    )
    
    if status_filter and status_filter != "all":
        query = query.where(Goal.status == status_filter)
    
    if category:
        query = query.where(Goal.category == category)
    
    if goal_type and goal_type != "all":
        query = query.where(Goal.goal_type == goal_type)
    
    # Count total
    count_query = (
        select(func.count(Goal.id))
        .join(GoalParticipant)
        .where(
            GoalParticipant.user_id == current_user.id,
            GoalParticipant.left_at.is_(None)
        )
    )
    if status_filter and status_filter != "all":
        count_query = count_query.where(Goal.status == status_filter)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Fetch goals
    query = query.order_by(Goal.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    goals = result.scalars().unique().all()
    
    goal_responses = []
    for goal in goals:
        # Get participant previews
        participants_preview = [
            ParticipantPreview(
                user_id=p.user_id,
                profile_image_url=None  # TODO: Load user profile image
            )
            for p in goal.participants[:3]
        ]
        
        goal_responses.append(GoalResponse(
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
            days_remaining=calculate_days_remaining(goal.target_date),
            participants_count=len(goal.participants),
            participants_preview=participants_preview,
            completed_at=goal.completed_at,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        ))
    
    return GoalListResponse(
        goals=goal_responses,
        pagination=PaginationMeta.create(page, limit, total)
    )


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    goal_data: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> GoalResponse:
    """
    Create a new goal.
    
    Args:
        goal_data: Goal creation data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        GoalResponse: Created goal
    """
    # Create goal
    goal = Goal(
        creator_id=current_user.id,
        title=goal_data.title,
        description=goal_data.description,
        category=goal_data.category,
        goal_type=goal_data.goal_type,
        target_type=goal_data.target_type,
        target_amount=goal_data.target_amount,
        target_currency=goal_data.target_currency,
        target_date=goal_data.target_date,
        is_public=goal_data.is_public,
        image_url=goal_data.image_url,
    )
    db.add(goal)
    await db.flush()
    
    # Add creator as participant
    creator_participant = GoalParticipant(
        goal_id=goal.id,
        user_id=current_user.id,
        role="creator"
    )
    db.add(creator_participant)
    
    # Add other participants if provided
    if goal_data.participant_ids:
        for participant_id in goal_data.participant_ids:
            if participant_id != current_user.id:
                participant = GoalParticipant(
                    goal_id=goal.id,
                    user_id=participant_id,
                    role="member"
                )
                db.add(participant)
    
    await db.commit()
    await db.refresh(goal)
    
    # Load participants
    result = await db.execute(
        select(Goal)
        .where(Goal.id == goal.id)
        .options(selectinload(Goal.participants))
    )
    goal = result.scalar_one()
    
    participants = []
    for p in goal.participants:
        user_result = await db.execute(select(User).where(User.id == p.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            participants.append(ParticipantResponse(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                profile_image_url=user.profile_image_url,
                role=p.role,
                contribution_amount=p.contribution_amount,
                joined_at=p.joined_at,
            ))
    
    return GoalResponse(
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
        days_remaining=calculate_days_remaining(goal.target_date),
        participants_count=len(participants),
        participants=participants,
        completed_at=goal.completed_at,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> GoalResponse:
    """
    Get a specific goal.
    
    Args:
        goal_id: Goal ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        GoalResponse: Goal details
    """
    result = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id)
        .options(selectinload(Goal.participants))
    )
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )
    
    # Check if user has access
    is_participant = any(p.user_id == current_user.id for p in goal.participants)
    if not is_participant and not goal.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    participants = []
    for p in goal.participants:
        user_result = await db.execute(select(User).where(User.id == p.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            participants.append(ParticipantResponse(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                profile_image_url=user.profile_image_url,
                role=p.role,
                contribution_amount=p.contribution_amount,
                joined_at=p.joined_at,
            ))
    
    return GoalResponse(
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
        days_remaining=calculate_days_remaining(goal.target_date),
        participants_count=len(participants),
        participants=participants,
        completed_at=goal.completed_at,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: UUID,
    goal_data: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> GoalResponse:
    """
    Update a goal.
    
    Args:
        goal_id: Goal ID
        goal_data: Goal update data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        GoalResponse: Updated goal
    """
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )
    
    if goal.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can update this goal"
        )
    
    # Update fields
    update_data = goal_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(goal, field, value)
    
    goal.updated_at = datetime.utcnow()
    await db.commit()
    
    return await get_goal(goal_id, current_user, db)


@router.delete("/{goal_id}", response_model=MessageResponse)
async def delete_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Delete a goal.
    
    Args:
        goal_id: Goal ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MessageResponse: Success message
    """
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )
    
    if goal.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can delete this goal"
        )
    
    await db.delete(goal)
    await db.commit()
    
    return MessageResponse(message="Goal deleted successfully")


@router.post("/{goal_id}/contributions", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
async def create_contribution(
    goal_id: UUID,
    contribution_data: ContributionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ContributionResponse:
    """
    Add a contribution to a goal.
    
    Args:
        goal_id: Goal ID
        contribution_data: Contribution data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        ContributionResponse: Created contribution
    """
    # Verify goal exists and user is participant
    result = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id)
        .options(selectinload(Goal.participants))
    )
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )
    
    is_participant = any(p.user_id == current_user.id for p in goal.participants)
    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a participant to contribute"
        )
    
    # Create contribution
    contribution = GoalContribution(
        goal_id=goal_id,
        user_id=current_user.id,
        amount=contribution_data.amount,
        note=contribution_data.note,
        contribution_type=contribution_data.contribution_type,
    )
    db.add(contribution)
    
    # Update goal progress
    goal.current_amount = (goal.current_amount or Decimal("0")) + contribution_data.amount
    if goal.target_amount and goal.target_amount > 0:
        goal.progress_percentage = float(goal.current_amount / goal.target_amount * 100)
        if goal.progress_percentage >= 100:
            goal.status = "completed"
            goal.completed_at = datetime.utcnow()
    
    # Update participant contribution
    participant_result = await db.execute(
        select(GoalParticipant).where(
            GoalParticipant.goal_id == goal_id,
            GoalParticipant.user_id == current_user.id
        )
    )
    participant = participant_result.scalar_one()
    participant.contribution_amount = (participant.contribution_amount or Decimal("0")) + contribution_data.amount
    
    await db.commit()
    await db.refresh(contribution)
    
    return ContributionResponse(
        id=contribution.id,
        goal_id=contribution.goal_id,
        user_id=contribution.user_id,
        amount=contribution.amount,
        note=contribution.note,
        contribution_type=contribution.contribution_type,
        created_at=contribution.created_at,
        goal_progress=GoalProgressResponse(
            current_amount=goal.current_amount,
            progress_percentage=goal.progress_percentage
        )
    )


@router.get("/{goal_id}/contributions", response_model=List[ContributionResponse])
async def get_contributions(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[ContributionResponse]:
    """
    Get contributions for a goal.
    
    Args:
        goal_id: Goal ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[ContributionResponse]: Goal contributions
    """
    result = await db.execute(
        select(GoalContribution)
        .where(GoalContribution.goal_id == goal_id)
        .order_by(GoalContribution.created_at.desc())
    )
    contributions = result.scalars().all()
    
    return [
        ContributionResponse(
            id=c.id,
            goal_id=c.goal_id,
            user_id=c.user_id,
            amount=c.amount,
            note=c.note,
            contribution_type=c.contribution_type,
            created_at=c.created_at,
        )
        for c in contributions
    ]


@router.post("/{goal_id}/milestones", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
async def create_milestone(
    goal_id: UUID,
    milestone_data: MilestoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MilestoneResponse:
    """
    Create a milestone for a goal.
    
    Args:
        goal_id: Goal ID
        milestone_data: Milestone data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        MilestoneResponse: Created milestone
    """
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )
    
    if goal.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can add milestones"
        )
    
    milestone = GoalMilestone(
        goal_id=goal_id,
        title=milestone_data.title,
        description=milestone_data.description,
        target_value=milestone_data.target_value,
        order_index=milestone_data.order_index,
    )
    db.add(milestone)
    await db.commit()
    await db.refresh(milestone)
    
    return MilestoneResponse(
        id=milestone.id,
        goal_id=milestone.goal_id,
        title=milestone.title,
        description=milestone.description,
        target_value=milestone.target_value,
        achieved=milestone.achieved,
        achieved_at=milestone.achieved_at,
        achieved_by=milestone.achieved_by,
        order_index=milestone.order_index,
        created_at=milestone.created_at,
    )


@router.post("/{goal_id}/complete", response_model=GoalResponse)
async def complete_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> GoalResponse:
    """
    Mark a goal as completed.
    
    Args:
        goal_id: Goal ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        GoalResponse: Completed goal
    """
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )
    
    if goal.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can complete this goal"
        )
    
    goal.status = "completed"
    goal.completed_at = datetime.utcnow()
    goal.progress_percentage = 100.0
    
    # Update user stats
    current_user.goals_achieved += 1
    
    await db.commit()
    
    return await get_goal(goal_id, current_user, db)

