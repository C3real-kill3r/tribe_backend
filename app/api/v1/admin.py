"""
Admin and utility endpoints for database management.
"""
import logging
import sys
from pathlib import Path
from typing import Dict, Any
from sqlalchemy import inspect, text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_db
from app.db.session import init_db, engine, Base
from app.models import *  # Import all models to register them with Base

logger = logging.getLogger(__name__)

router = APIRouter()


class SeedingResponse(BaseModel):
    """Response model for seeding endpoint."""
    success: bool
    message: str
    tables_created: bool
    tables_checked: list[str]
    seeding_results: Dict[str, Any]


async def check_tables_exist(db: AsyncSession) -> tuple[bool, list[str]]:
    """
    Check if all required tables exist in the database.
    
    Returns:
        Tuple of (all_exist: bool, existing_tables: list[str])
    """
    try:
        # Get list of all table names from metadata
        expected_tables = set(Base.metadata.tables.keys())
        
        # Query database for existing tables
        result = await db.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
        )
        existing_tables = {row[0] for row in result.fetchall()}
        
        missing_tables = expected_tables - existing_tables
        
        if missing_tables:
            logger.info(f"Missing tables: {missing_tables}")
            return False, list(existing_tables)
        
        return True, list(existing_tables)
    except Exception as e:
        logger.error(f"Error checking tables: {e}")
        # If we can't check, assume tables don't exist
        return False, []


async def run_seeding(session: AsyncSession) -> Dict[str, Any]:
    """
    Run database seeding functions.
    
    Returns:
        Dict with seeding results
    """
    results = {
        "users_created": 0,
        "friendships_created": 0,
        "conversations_created": 0,
        "messages_created": 0,
        "goals_created": 0,
        "posts_created": 0,
        "stories_created": 0,
        "notifications_created": 0,
        "errors": []
    }
    
    try:
        # Add scripts directory to path for imports
        scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))
        
        # Import seeding functions
        from seed_data import (
            create_users,
            create_friendships,
            create_conversations,
            create_goals,
            create_posts,
            create_stories,
            create_notifications,
            TEST_USERS
        )
        
        # Create users
        try:
            users = await create_users(session)
            results["users_created"] = len(users)
            logger.info(f"Created {len(users)} users")
        except Exception as e:
            error_msg = f"Error creating users: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Create friendships
        try:
            if 'users' in locals() and users:
                await create_friendships(session, users)
                # Count friendships
                from app.models.friendship import Friendship
                count_result = await session.execute(
                    select(func.count(Friendship.id))
                )
                results["friendships_created"] = count_result.scalar() or 0
                logger.info(f"Created friendships")
        except Exception as e:
            error_msg = f"Error creating friendships: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Create conversations
        try:
            if 'users' in locals() and users:
                await create_conversations(session, users)
                # Count conversations and messages
                from app.models.conversation import Conversation, Message
                conv_count = await session.execute(
                    select(func.count(Conversation.id))
                )
                msg_count = await session.execute(
                    select(func.count(Message.id))
                )
                results["conversations_created"] = conv_count.scalar() or 0
                results["messages_created"] = msg_count.scalar() or 0
                logger.info(f"Created conversations and messages")
        except Exception as e:
            error_msg = f"Error creating conversations: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Create goals
        try:
            if 'users' in locals() and users:
                await create_goals(session, users)
                from app.models.goal import Goal
                goal_count = await session.execute(
                    select(func.count(Goal.id))
                )
                results["goals_created"] = goal_count.scalar() or 0
                logger.info(f"Created goals")
        except Exception as e:
            error_msg = f"Error creating goals: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Create posts
        try:
            if 'users' in locals() and users:
                await create_posts(session, users)
                from app.models.post import Post
                post_count = await session.execute(
                    select(func.count(Post.id))
                )
                results["posts_created"] = post_count.scalar() or 0
                logger.info(f"Created posts")
        except Exception as e:
            error_msg = f"Error creating posts: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Create stories
        try:
            if 'users' in locals() and users:
                await create_stories(session, users)
                from app.models.post import Story
                story_count = await session.execute(
                    select(func.count(Story.id))
                )
                results["stories_created"] = story_count.scalar() or 0
                logger.info(f"Created stories")
        except Exception as e:
            error_msg = f"Error creating stories: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Create notifications
        try:
            if 'users' in locals() and users:
                await create_notifications(session, users)
                from app.models.notification import Notification
                notif_count = await session.execute(
                    select(func.count(Notification.id))
                )
                results["notifications_created"] = notif_count.scalar() or 0
                logger.info(f"Created notifications")
        except Exception as e:
            error_msg = f"Error creating notifications: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Add test credentials info
        results["test_credentials"] = [
            {
                "email": user["email"],
                "password": user["password"],
                "username": user["username"]
            }
            for user in TEST_USERS[:3]  # First 3 users
        ]
        
    except ImportError as e:
        error_msg = f"Failed to import seeding functions: {str(e)}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during seeding: {str(e)}"
        logger.error(error_msg, exc_info=True)
        results["errors"].append(error_msg)
    
    return results


@router.post("/seed-database", response_model=SeedingResponse)
async def seed_database(
    db: AsyncSession = Depends(get_db)
) -> SeedingResponse:
    """
    Seed the database with test data.
    
    This endpoint:
    1. Checks if all required tables exist
    2. Creates tables if they don't exist
    3. Seeds the database with test data (users, friendships, conversations, etc.)
    4. Returns detailed results
    
    Returns:
        SeedingResponse: Detailed seeding results
    """
    try:
        # Step 1: Check if tables exist
        logger.info("Checking if database tables exist...")
        all_tables_exist, existing_tables = await check_tables_exist(db)
        
        tables_created = False
        if not all_tables_exist:
            logger.info("Some tables are missing. Creating all tables...")
            try:
                await init_db()
                tables_created = True
                logger.info("✅ All tables created successfully")
            except Exception as e:
                logger.error(f"Error creating tables: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create database tables: {str(e)}"
                )
        else:
            logger.info(f"✅ All tables exist ({len(existing_tables)} tables)")
        
        # Step 2: Run seeding
        logger.info("Starting database seeding...")
        seeding_results = await run_seeding(db)
        
        # Commit all changes
        try:
            await db.commit()
            logger.info("✅ Database seeding completed successfully")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error committing seeding changes: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to commit seeding changes: {str(e)}"
            )
        
        # Determine success
        has_errors = len(seeding_results.get("errors", [])) > 0
        success = not has_errors and seeding_results.get("users_created", 0) > 0
        
        message = "Database seeded successfully" if success else "Seeding completed with some errors"
        if has_errors:
            message += f". Errors: {', '.join(seeding_results['errors'])}"
        
        return SeedingResponse(
            success=success,
            message=message,
            tables_created=tables_created,
            tables_checked=existing_tables if all_tables_exist else list(Base.metadata.tables.keys()),
            seeding_results=seeding_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in seed_database endpoint: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during database seeding: {str(e)}"
        )


@router.get("/database-status")
async def get_database_status(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the current status of the database.
    
    Returns:
        Dict with database status information
    """
    try:
        all_tables_exist, existing_tables = await check_tables_exist(db)
        expected_tables = set(Base.metadata.tables.keys())
        missing_tables = expected_tables - set(existing_tables)
        
        # Count records in key tables
        from app.models.user import User
        from app.models.goal import Goal
        from app.models.post import Post
        
        user_count = await db.execute(select(func.count(User.id)))
        goal_count = await db.execute(select(func.count(Goal.id)))
        post_count = await db.execute(select(func.count(Post.id)))
        
        return {
            "database_connected": True,
            "all_tables_exist": all_tables_exist,
            "expected_tables": len(expected_tables),
            "existing_tables": len(existing_tables),
            "missing_tables": list(missing_tables),
            "table_names": sorted(existing_tables),
            "record_counts": {
                "users": user_count.scalar() or 0,
                "goals": goal_count.scalar() or 0,
                "posts": post_count.scalar() or 0,
            }
        }
    except Exception as e:
        logger.error(f"Error checking database status: {e}")
        return {
            "database_connected": False,
            "error": str(e)
        }

