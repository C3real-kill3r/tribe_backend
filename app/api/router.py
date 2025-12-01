"""
Main API router that includes all endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1 import auth, users, friends, goals, posts, stories, conversations, ai_coach, notifications, settings, search, websocket, admin

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(
    auth.router,
    prefix="/v1/auth",
    tags=["Authentication"]
)
api_router.include_router(
    users.router,
    prefix="/v1/users",
    tags=["Users"]
)
api_router.include_router(
    friends.router,
    prefix="/v1/friends",
    tags=["Friends"]
)
api_router.include_router(
    goals.router,
    prefix="/v1/goals",
    tags=["Goals"]
)
api_router.include_router(
    posts.router,
    prefix="/v1/posts",
    tags=["Posts"]
)
api_router.include_router(
    stories.router,
    prefix="/v1/stories",
    tags=["Stories"]
)
api_router.include_router(
    conversations.router,
    prefix="/v1/conversations",
    tags=["Conversations"]
)
api_router.include_router(
    ai_coach.router,
    prefix="/v1/ai-coach",
    tags=["AI Coach"]
)
api_router.include_router(
    notifications.router,
    prefix="/v1/notifications",
    tags=["Notifications"]
)
api_router.include_router(
    settings.router,
    prefix="/v1/settings",
    tags=["Settings"]
)
api_router.include_router(
    search.router,
    prefix="/v1/search",
    tags=["Search"]
)
api_router.include_router(
    websocket.router,
    prefix="/v1",
    tags=["WebSocket"]
)
api_router.include_router(
    admin.router,
    prefix="/v1/admin",
    tags=["Admin"]
)

