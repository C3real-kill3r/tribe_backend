"""
WebSocket endpoint for real-time chat and notifications.
"""
import json
from typing import Dict, Set
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from fastapi.exceptions import HTTPException

from app.api.deps import get_current_user_from_token
from app.models.user import User
from app.models.conversation import Conversation, ConversationParticipant, Message
from app.db.session import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

router = APIRouter()

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        # Map of user_id -> WebSocket
        self.active_connections: Dict[UUID, WebSocket] = {}
        # Map of conversation_id -> Set of user_ids
        self.conversation_subscriptions: Dict[UUID, Set[UUID]] = {}
        # Map of conversation_id -> Set of user_ids who are typing
        self.typing_users: Dict[UUID, Set[UUID]] = {}

    async def connect(self, websocket: WebSocket, user_id: UUID):
        """Connect a user's WebSocket."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        # Send connection confirmation
        await self.send_personal_message({
            "event": "connected",
            "message": "WebSocket connection established"
        }, websocket)

    def disconnect(self, user_id: UUID):
        """Disconnect a user's WebSocket."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        # Remove from all conversation subscriptions
        for conversation_id, users in self.conversation_subscriptions.items():
            users.discard(user_id)
            if not users:
                del self.conversation_subscriptions[conversation_id]
        # Remove from typing indicators
        for conversation_id, users in self.typing_users.items():
            users.discard(user_id)
            if not users:
                del self.typing_users[conversation_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            pass  # Connection may be closed

    async def send_to_user(self, user_id: UUID, message: dict):
        """Send a message to a specific user."""
        if user_id in self.active_connections:
            await self.send_personal_message(message, self.active_connections[user_id])

    async def subscribe_to_conversation(self, conversation_id: UUID, user_id: UUID):
        """Subscribe a user to a conversation."""
        if conversation_id not in self.conversation_subscriptions:
            self.conversation_subscriptions[conversation_id] = set()
        self.conversation_subscriptions[conversation_id].add(user_id)

    async def unsubscribe_from_conversation(self, conversation_id: UUID, user_id: UUID):
        """Unsubscribe a user from a conversation."""
        if conversation_id in self.conversation_subscriptions:
            self.conversation_subscriptions[conversation_id].discard(user_id)
            if not self.conversation_subscriptions[conversation_id]:
                del self.conversation_subscriptions[conversation_id]

    async def broadcast_to_conversation(self, conversation_id: UUID, message: dict, exclude_user_id: UUID = None):
        """Broadcast a message to all users subscribed to a conversation."""
        if conversation_id in self.conversation_subscriptions:
            for user_id in self.conversation_subscriptions[conversation_id]:
                if user_id != exclude_user_id:
                    await self.send_to_user(user_id, message)

    async def handle_typing(self, conversation_id: UUID, user_id: UUID, user_name: str, is_typing: bool):
        """Handle typing indicator."""
        if conversation_id not in self.typing_users:
            self.typing_users[conversation_id] = set()
        
        if is_typing:
            self.typing_users[conversation_id].add(user_id)
        else:
            self.typing_users[conversation_id].discard(user_id)
            if not self.typing_users[conversation_id]:
                del self.typing_users[conversation_id]

        # Broadcast typing indicator to other users in the conversation
        await self.broadcast_to_conversation(conversation_id, {
            "event": "typing",
            "conversation_id": str(conversation_id),
            "data": {
                "user_id": str(user_id),
                "user_name": user_name,
                "is_typing": is_typing
            }
        }, exclude_user_id=user_id)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time chat.
    
    Connection URL: ws://host/api/v1/ws?token=JWT_TOKEN
    """
    user: User = None
    db: AsyncSession = None
    
    try:
        # Get database session
        db = AsyncSessionLocal()
        
        # Authenticate user from token
        user = await get_current_user_from_token(token, db)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            if db:
                await db.close()
            return
        
        # Connect the user
        await manager.connect(websocket, user.id)
        
        # Main message loop
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            event = message.get("event")
            
            if event == "subscribe":
                # Subscribe to a conversation
                conversation_id_str = message.get("conversation_id")
                if conversation_id_str:
                    try:
                        conversation_id = UUID(conversation_id_str)
                        # Verify user is a participant
                        result = await db.execute(
                            select(Conversation)
                            .where(Conversation.id == conversation_id)
                            .options(selectinload(Conversation.participants))
                        )
                        conversation = result.scalar_one_or_none()
                        
                        if conversation:
                            is_participant = any(
                                p.user_id == user.id and p.left_at is None
                                for p in conversation.participants
                            )
                            if is_participant:
                                await manager.subscribe_to_conversation(conversation_id, user.id)
                                await manager.send_personal_message({
                                    "event": "subscribed",
                                    "conversation_id": conversation_id_str
                                }, websocket)
                    except (ValueError, AttributeError):
                        pass
            
            elif event == "unsubscribe":
                # Unsubscribe from a conversation
                conversation_id_str = message.get("conversation_id")
                if conversation_id_str:
                    try:
                        conversation_id = UUID(conversation_id_str)
                        await manager.unsubscribe_from_conversation(conversation_id, user.id)
                    except ValueError:
                        pass
            
            elif event == "typing":
                # Handle typing indicator
                conversation_id_str = message.get("conversation_id")
                is_typing = message.get("is_typing", False)
                if conversation_id_str:
                    try:
                        conversation_id = UUID(conversation_id_str)
                        await manager.handle_typing(
                            conversation_id,
                            user.id,
                            user.full_name or user.username,
                            is_typing
                        )
                    except ValueError:
                        pass
            
            elif event == "presence":
                # Handle presence updates (online/offline)
                status = message.get("status", "online")
                # Could broadcast to friends or conversations
                pass
            
            elif event == "ping":
                # Respond to heartbeat
                await manager.send_personal_message({
                    "event": "pong"
                }, websocket)
    
    except WebSocketDisconnect:
        if user:
            manager.disconnect(user.id)
        if db:
            await db.close()
    except Exception as e:
        if user:
            manager.disconnect(user.id)
        if db:
            await db.close()
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


async def broadcast_new_message(conversation_id: UUID, message_data: dict, exclude_user_id: UUID = None):
    """Helper function to broadcast a new message to conversation subscribers."""
    await manager.broadcast_to_conversation(conversation_id, {
        "event": "message.new",
        "conversation_id": str(conversation_id),
        "data": message_data
    }, exclude_user_id=exclude_user_id)

