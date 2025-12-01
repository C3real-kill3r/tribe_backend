"""
AI Coach API endpoints.
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.llm_service import get_llm_service
from app.models.user import User
from app.models.goal import Goal, GoalParticipant
from app.models.conversation import Conversation, ConversationParticipant, Message, AICoachSession
from app.schemas.conversation import (
    AICoachChatRequest,
    AICoachChatResponse,
    MessageResponse,
)
from app.schemas.user import UserPublicResponse

logger = logging.getLogger(__name__)

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
        # Refresh user goals periodically (every time we access the session)
        # This ensures the AI has up-to-date context
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
        session.user_goals = user_goals_data
        await db.commit()
        await db.refresh(session)
        
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


async def get_conversation_history(
    conversation_id: UUID,
    db: AsyncSession,
    limit: int = None
) -> List[Message]:
    """
    Get conversation history for context.
    
    Args:
        conversation_id: Conversation ID
        db: Database session
        limit: Maximum number of messages to retrieve (uses config default if None)
        
    Returns:
        List of messages ordered by creation time
    """
    limit = limit or settings.ai_coach_context_window
    
    result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.is_deleted == False
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    
    # Return in chronological order (oldest first)
    return list(reversed(messages))


def build_system_prompt(user: User, session: AICoachSession) -> str:
    """
    Build the system prompt for the AI coach.
    
    Args:
        user: User object
        session: AI Coach session with user context
        
    Returns:
        System prompt string
    """
    prompt = f"""You are Tribe Coach, a supportive and empathetic AI accountability coach for {user.full_name} (username: {user.username}).

Your role is to help users:
- Set and achieve meaningful goals
- Stay motivated and accountable
- Build and maintain friendships
- Track progress and celebrate wins
- Overcome challenges and obstacles

Guidelines:
- Be warm, encouraging, and personable
- Use the user's name naturally in conversation
- Reference their specific goals when relevant
- Keep responses concise but helpful (2-4 paragraphs max)
- Ask follow-up questions to understand their needs better
- Use emojis sparingly and appropriately
- Be authentic and avoid being overly formal
"""
    
    # Add user goals context if available
    if session.user_goals:
        goals_list = "\n".join([
            f"- {goal.get('title', 'Untitled Goal')} ({goal.get('category', 'general')})"
            for goal in session.user_goals[:5]
        ])
        prompt += f"\n\nUser's Active Goals:\n{goals_list}\n"
        prompt += "\nReference these goals naturally when relevant, but don't force them into every response.\n"
    
    return prompt


def messages_to_llm_format(messages: List[Message], user: User) -> List[Dict[str, str]]:
    """
    Convert database messages to LLM format.
    
    Args:
        messages: List of Message objects
        user: User object to identify user messages
        
    Returns:
        List of message dicts with 'role' and 'content' keys
    """
    llm_messages = []
    
    for msg in messages:
        if msg.sender_id is None:
            # AI message
            llm_messages.append({
                "role": "assistant",
                "content": msg.content
            })
        elif msg.sender_id == user.id:
            # User message
            llm_messages.append({
                "role": "user",
                "content": msg.content
            })
        # Skip messages from other users (shouldn't happen in AI coach conversations)
    
    return llm_messages


async def get_ai_response(
    message: str,
    session: AICoachSession,
    user: User,
    conversation: Conversation,
    db: AsyncSession
) -> tuple[str, Dict]:
    """
    Get response from AI coach using LLM service.
    
    Args:
        message: User's message
        session: AI Coach session
        user: User object
        conversation: Conversation object
        db: Database session
        
    Returns:
        Tuple of (response_text, metadata_dict) where metadata includes token usage
    """
    # Log configuration status
    api_key_attr = f"{settings.llm_provider}_api_key"
    api_key_value = getattr(settings, api_key_attr, None)
    api_key_present = bool(api_key_value)
    api_key_preview = f"{api_key_value[:10]}..." if api_key_value and len(api_key_value) > 10 else "None"
    
    logger.info(
        f"Attempting to initialize LLM service: "
        f"provider={settings.llm_provider}, "
        f"has_api_key={api_key_present}, "
        f"api_key_preview={api_key_preview}"
    )
    
    try:
        # Get LLM service
        llm_service = get_llm_service()
        logger.info(f"✓ LLM service initialized successfully: provider={settings.llm_provider}")
    except ValueError as e:
        # API key missing or invalid provider
        logger.error(f"LLM service configuration error: {e}")
        error_msg = str(e)
        if "API key is required" in error_msg:
            return (
                "I'm not configured properly. Please contact support - the AI service API key is missing.",
                {"tokens_used": 0, "provider": "fallback", "error": error_msg}
            )
        return (
            f"I'm having trouble connecting to my AI service right now. Error: {error_msg}",
            {"tokens_used": 0, "provider": "fallback", "error": error_msg}
        )
    except Exception as e:
        logger.error(f"Failed to initialize LLM service: {e}", exc_info=True)
        # Fallback to a simple response
        return (
            f"I'm having trouble connecting to my AI service right now. Error: {str(e)}. Please check the server logs for details.",
            {"tokens_used": 0, "provider": "fallback", "error": str(e)}
        )
    
    try:
        # Get conversation history
        history_messages = await get_conversation_history(conversation.id, db)
        logger.info(f"Retrieved {len(history_messages)} messages from conversation history")
        
        # Convert to LLM format
        llm_messages = messages_to_llm_format(history_messages, user)
        logger.info(f"Converted to {len(llm_messages)} LLM messages")
        
        # Add current user message
        llm_messages.append({
            "role": "user",
            "content": message
        })
        
        # Build system prompt
        system_prompt = build_system_prompt(user, session)
        logger.debug(f"System prompt length: {len(system_prompt)} characters")
        
        # Generate response
        logger.info("Calling LLM service to generate response...")
        response_text, metadata = await llm_service.generate_response(
            messages=llm_messages,
            system_prompt=system_prompt,
            temperature=settings.ai_coach_temperature,
            max_tokens=settings.ai_coach_max_tokens,
        )
        
        logger.info(
            f"✓ LLM response generated: "
            f"provider={metadata.get('provider', 'unknown')}, "
            f"tokens_used={metadata.get('tokens_used', 0)}, "
            f"response_length={len(response_text)}"
        )
        
        return response_text, metadata
        
    except Exception as e:
        logger.error(f"Error generating AI response: {e}", exc_info=True)
        # More detailed error for debugging
        error_details = str(e)
        if "API key" in error_details or "authentication" in error_details.lower():
            error_msg = "Authentication error with AI service. Please check API key configuration."
        elif "rate limit" in error_details.lower():
            error_msg = "AI service rate limit exceeded. Please try again in a moment."
        else:
            error_msg = f"Error: {error_details}"
        
        # Fallback response
        return (
            f"I apologize, but I encountered an error processing your message: {error_msg}. Please try again in a moment.",
            {"tokens_used": 0, "provider": "fallback", "error": error_details}
        )


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
    try:
        # Get or create AI coach conversation
        conversation, session = await get_or_create_ai_coach_conversation(current_user, db)
        
        # Save user's message first
        user_message = Message(
            conversation_id=conversation.id,
            sender_id=current_user.id,
            content=request.message,
            message_type="text",
        )
        db.add(user_message)
        await db.flush()  # Flush to get the message ID
        
        # Get AI response with conversation history
        ai_response_content, metadata = await get_ai_response(
            request.message,
            session,
            current_user,
            conversation,
            db
        )
        
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
        
        # Update token usage
        tokens_used = metadata.get("tokens_used", 0)
        if tokens_used > 0:
            session.tokens_used = (session.tokens_used or 0) + tokens_used
        
        # Update conversation
        conversation.last_message_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(ai_message)
        
        # Generate contextual suggestions
        suggestions = await generate_contextual_suggestions(
            current_user,
            session,
            db
        )
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat_with_ai_coach: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your message. Please try again."
        )


async def generate_contextual_suggestions(
    user: User,
    session: AICoachSession,
    db: AsyncSession
) -> List[str]:
    """
    Generate contextual suggestions based on user's goals and conversation.
    
    Args:
        user: User object
        session: AI Coach session
        db: Database session
        
    Returns:
        List of suggestion strings
    """
    suggestions = []
    
    # Get user's active goals
    goals_result = await db.execute(
        select(Goal)
        .join(GoalParticipant)
        .where(
            GoalParticipant.user_id == user.id,
            Goal.status == "active"
        )
        .limit(3)
    )
    goals = goals_result.scalars().all()
    
    if goals:
        for goal in goals[:2]:
            suggestions.append(f"How can I make progress on '{goal.title}'?")
    else:
        suggestions.append("Help me create my first goal")
    
    # Add general suggestions
    suggestions.extend([
        "What are some tips for staying accountable?",
        "How can I connect better with my friends?",
        "Give me motivation for today",
    ])
    
    return suggestions[:5]


@router.get("/conversation", response_model=list[MessageResponse])
async def get_current_ai_coach_conversation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list[MessageResponse]:
    """
    Get the current user's AI coach conversation history.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List[MessageResponse]: Conversation history
    """
    # Get or create AI coach conversation
    conversation, _ = await get_or_create_ai_coach_conversation(current_user, db)
    
    # Get messages
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .options(selectinload(Message.sender))
        .order_by(Message.created_at.asc())
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


@router.post("/test", response_model=dict)
async def test_ai_coach_connection(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Test AI coach LLM connection (for debugging).
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Dict with test results
    """
    test_result = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": str(current_user.id),
        "provider": settings.llm_provider,
    }
    
    try:
        # Test 1: Check API key
        api_key_attr = f"{settings.llm_provider}_api_key"
        api_key = getattr(settings, api_key_attr, None)
        test_result["api_key_check"] = {
            "present": bool(api_key),
            "length": len(api_key) if api_key else 0,
            "preview": f"{api_key[:10]}..." if api_key and len(api_key) > 10 else "None"
        }
        
        if not api_key:
            test_result["status"] = "failed"
            test_result["error"] = f"{api_key_attr} is not set"
            return test_result
        
        # Test 2: Initialize service
        try:
            llm_service = get_llm_service()
            test_result["service_initialization"] = {
                "status": "success",
                "provider": settings.llm_provider
            }
        except Exception as e:
            test_result["service_initialization"] = {
                "status": "failed",
                "error": str(e)
            }
            test_result["status"] = "failed"
            return test_result
        
        # Test 3: Make a simple API call
        try:
            test_messages = [
                {"role": "user", "content": "Say 'Hello, this is a test' and nothing else."}
            ]
            response_text, metadata = await llm_service.generate_response(
                messages=test_messages,
                system_prompt="You are a helpful assistant.",
                temperature=0.7,
                max_tokens=50,
            )
            test_result["api_call"] = {
                "status": "success",
                "response": response_text,
                "tokens_used": metadata.get("tokens_used", 0),
                "provider": metadata.get("provider", "unknown")
            }
            test_result["status"] = "success"
        except Exception as e:
            test_result["api_call"] = {
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__
            }
            test_result["status"] = "failed"
            logger.error(f"API call test failed: {e}", exc_info=True)
        
    except Exception as e:
        test_result["status"] = "error"
        test_result["error"] = str(e)
        logger.error(f"Test endpoint error: {e}", exc_info=True)
    
    return test_result


@router.get("/config", response_model=dict)
async def get_ai_coach_config(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get AI coach configuration status (for debugging).
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Dict with configuration status
    """
    # Get API key previews (first 10 chars for security)
    openai_key_preview = f"{settings.openai_api_key[:10]}..." if settings.openai_api_key and len(settings.openai_api_key) > 10 else "Not set"
    anthropic_key_preview = f"{settings.anthropic_api_key[:10]}..." if settings.anthropic_api_key and len(settings.anthropic_api_key) > 10 else "Not set"
    gemini_key_preview = f"{settings.gemini_api_key[:10]}..." if settings.gemini_api_key and len(settings.gemini_api_key) > 10 else "Not set"
    
    config_status = {
        "provider": settings.llm_provider,
        "has_openai_key": bool(settings.openai_api_key),
        "openai_key_preview": openai_key_preview,
        "has_anthropic_key": bool(settings.anthropic_api_key),
        "anthropic_key_preview": anthropic_key_preview,
        "has_gemini_key": bool(settings.gemini_api_key),
        "gemini_key_preview": gemini_key_preview,
        "openai_model": settings.openai_model,
        "anthropic_model": settings.anthropic_model,
        "gemini_model": settings.gemini_model,
        "temperature": settings.ai_coach_temperature,
        "max_tokens": settings.ai_coach_max_tokens,
        "context_window": settings.ai_coach_context_window,
    }
    
    # Try to initialize the service to check for errors
    try:
        llm_service = get_llm_service()
        config_status["service_status"] = "ready"
        config_status["service_provider"] = settings.llm_provider
        config_status["service_initialized"] = True
    except ValueError as e:
        config_status["service_status"] = "configuration_error"
        config_status["service_error"] = str(e)
        config_status["service_initialized"] = False
    except Exception as e:
        config_status["service_status"] = "initialization_error"
        config_status["service_error"] = str(e)
        config_status["service_initialized"] = False
    
    return config_status


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
    # Get or create session to access user goals
    try:
        result = await db.execute(
            select(AICoachSession)
            .where(AICoachSession.user_id == current_user.id)
        )
        session = result.scalar_one_or_none()
    except Exception:
        session = None
    
    if session and session.user_goals:
        suggestions = []
        for goal in session.user_goals[:3]:
            suggestions.append(f"How can I make progress on '{goal.get('title', 'my goal')}'?")
        suggestions.extend([
            "What are some tips for staying accountable?",
            "How can I connect better with my friends?",
        ])
        return suggestions[:5]
    
    # Fallback to querying goals directly
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

