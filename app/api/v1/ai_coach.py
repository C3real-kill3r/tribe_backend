"""
AI Coach API endpoints.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.goal import Goal, GoalParticipant
from app.models.conversation import Conversation, ConversationParticipant, Message, AICoachSession
from app.schemas.conversation import (
    AICoachChatRequest,
    AICoachChatResponse,
    MessageResponse,
)
from app.schemas.user import UserPublicResponse

router = APIRouter()


async def get_or_create_ai_coach_conversation(
    user: User,
    db: AsyncSession
) -> tuple[Conversation, AICoachSession]:
    """Get or create the AI coach conversation for a user."""
    # Check for existing AI coach session
    result = await db.execute(
        select(AICoachSession)
        .where(AICoachSession.user_id == user.id)
        .options(selectinload(AICoachSession.conversation))
    )
    session = result.scalar_one_or_none()
    
    if session:
        return session.conversation, session
    
    # Create new conversation
    conversation = Conversation(
        conversation_type="ai_coach",
        name="Tribe Coach",
        is_group=False,
    )
    db.add(conversation)
    await db.flush()
    
    # Add user as participant
    participant = ConversationParticipant(
        conversation_id=conversation.id,
        user_id=user.id,
        role="member",
    )
    db.add(participant)
    
    # Get user's goals for context
    goals_result = await db.execute(
        select(Goal)
        .join(GoalParticipant)
        .where(
            GoalParticipant.user_id == user.id,
            Goal.status == "active"
        )
        .limit(5)
    )
    goals = goals_result.scalars().all()
    user_goals_data = [
        {"id": str(g.id), "title": g.title, "category": g.category}
        for g in goals
    ]
    
    # Create AI coach session
    session = AICoachSession(
        user_id=user.id,
        conversation_id=conversation.id,
        user_goals=user_goals_data,
    )
    db.add(session)
    
    # Add welcome message from AI
    welcome_message = Message(
        conversation_id=conversation.id,
        sender_id=None,  # AI messages have no sender
        content="Hi! I'm your Tribe Coach. How can I help you today? I can assist with goal setting, motivation, accountability strategies, and staying connected with friends.",
        message_type="text",
    )
    db.add(welcome_message)
    
    conversation.last_message_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(conversation)
    await db.refresh(session)
    
    return conversation, session


async def get_ai_response(
    message: str,
    session: AICoachSession,
    user: User
) -> str:
    """
    Get response from AI coach.
    
    In production, this would call OpenAI API. For now, returns mock responses.
    """
    # TODO: Implement OpenAI integration
    # For now, return contextual mock responses
    
    message_lower = message.lower()
    
    if "hello" in message_lower or "hi" in message_lower:
        return f"Hi {user.full_name.split()[0]}! Great to hear from you. How are your goals coming along?"
    
    if "goal" in message_lower and ("help" in message_lower or "suggest" in message_lower):
        return """Here are some tips for achieving your goals:

1. **Break it down** - Split large goals into smaller, manageable milestones
2. **Track progress** - Regular check-ins keep you motivated
3. **Share with friends** - Accountability partners can boost success by 65%
4. **Celebrate wins** - Recognize even small achievements

Would you like specific advice for any of your current goals?"""
    
    if "motivat" in message_lower:
        return """I understand staying motivated can be challenging! Here are some strategies:

🎯 **Visualize success** - Imagine how you'll feel when you reach your goal
👥 **Connect with friends** - Share your journey and support each other
📅 **Set reminders** - Regular check-ins keep your goal top of mind
🏆 **Reward yourself** - Plan small celebrations for milestones

What's been your biggest challenge with motivation lately?"""
    
    if "friend" in message_lower:
        return """Building and maintaining friendships is wonderful! Here are some ideas:

💬 **Regular check-ins** - A quick message can brighten someone's day
🎯 **Shared goals** - Work on goals together for accountability
📸 **Share moments** - Post memories and celebrate each other
🤝 **Be supportive** - Encourage your friends in their journeys

Is there a specific friend you'd like to reconnect with?"""
    
    if "progress" in message_lower or "how am i doing" in message_lower:
        goals_info = ""
        if session.user_goals:
            goals_info = f"\n\nYou currently have {len(session.user_goals)} active goals. Keep up the great work!"
        
        return f"You're doing great! Remember, progress is progress, no matter how small.{goals_info}\n\nWould you like tips on accelerating your progress?"
    
    # Default response
    return f"""That's a great question! As your Tribe Coach, I'm here to help you with:

• 🎯 Goal setting and tracking
• 💪 Motivation and accountability
• 👥 Connecting with friends
• 📊 Analyzing your progress

What would you like to focus on today?"""


@router.post("/chat", response_model=AICoachChatResponse)
async def chat_with_ai_coach(
    request: AICoachChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AICoachChatResponse:
    """
    Send a message to the AI coach.
    
    Args:
        request: Chat request with message
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        AICoachChatResponse: AI response with suggestions
    """
    # Get or create AI coach conversation
    conversation, session = await get_or_create_ai_coach_conversation(current_user, db)
    
    # Save user's message
    user_message = Message(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        content=request.message,
        message_type="text",
    )
    db.add(user_message)
    
    # Get AI response
    ai_response_content = await get_ai_response(request.message, session, current_user)
    
    # Save AI's response
    ai_message = Message(
        conversation_id=conversation.id,
        sender_id=None,  # AI messages have no sender
        content=ai_response_content,
        message_type="text",
    )
    db.add(ai_message)
    
    # Update session stats
    session.message_count += 2
    session.last_interaction_at = datetime.utcnow()
    
    # Update conversation
    conversation.last_message_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(ai_message)
    
    # Generate suggestions based on context
    suggestions = [
        "How can I stay motivated?",
        "Help me set a new goal",
        "Tips for connecting with friends",
    ]
    
    return AICoachChatResponse(
        message=MessageResponse(
            id=ai_message.id,
            conversation_id=ai_message.conversation_id,
            sender=None,
            content=ai_message.content,
            message_type=ai_message.message_type,
            is_edited=False,
            is_deleted=False,
            created_at=ai_message.created_at,
        ),
        suggestions=suggestions,
    )


@router.get("/conversations/{conversation_id}", response_model=list[MessageResponse])
async def get_ai_coach_history(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[MessageResponse]:
    """
    Get AI coach conversation history.
    
    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[MessageResponse]: Conversation history
    """
    # Verify it's an AI coach conversation and user has access
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.conversation_type == "ai_coach"
        )
        .options(selectinload(Conversation.participants))
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI Coach conversation not found"
        )
    
    is_participant = any(p.user_id == current_user.id for p in conversation.participants)
    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get messages
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .options(selectinload(Message.sender))
        .order_by(Message.created_at.asc())
        .limit(100)
    )
    messages = messages_result.scalars().all()
    
    return [
        MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            sender=UserPublicResponse.model_validate(msg.sender) if msg.sender else None,
            content=msg.content,
            message_type=msg.message_type,
            is_edited=msg.is_edited,
            is_deleted=msg.is_deleted,
            created_at=msg.created_at,
        )
        for msg in messages
    ]


@router.get("/suggestions", response_model=list[str])
async def get_ai_suggestions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[str]:
    """
    Get AI-powered suggestions for the user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[str]: Suggested actions/prompts
    """
    # Get user's goals
    goals_result = await db.execute(
        select(Goal)
        .join(GoalParticipant)
        .where(
            GoalParticipant.user_id == current_user.id,
            Goal.status == "active"
        )
        .limit(3)
    )
    goals = goals_result.scalars().all()
    
    suggestions = []
    
    if goals:
        for goal in goals:
            suggestions.append(f"How can I make progress on '{goal.title}'?")
    else:
        suggestions.append("Help me create my first goal")
    
    suggestions.extend([
        "What are some tips for staying accountable?",
        "How can I connect better with my friends?",
        "Give me motivation for today",
    ])
    
    return suggestions[:5]

