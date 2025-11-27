# WebSocket Endpoint Setup

## Endpoint Configuration

The WebSocket endpoint is now implemented and configured at:

**URL:** `ws://{host}/api/v1/ws?token={JWT_TOKEN}`

For example:
- Development: `ws://localhost:8000/api/v1/ws?token=eyJ...`
- Production: `wss://api.tribe.app/api/v1/ws?token=eyJ...`

## App Configuration

The Flutter app is configured to connect to:
- Base URL from `.env`: `API_BASE_URL` (default: `http://localhost:8000`)
- API Version: `v1`
- WebSocket URL: Automatically converts `http://` to `ws://` and `https://` to `wss://`
- Final URL: `{baseUrl}/api/v1/ws?token={accessToken}`

## Features Implemented

1. **Authentication**: JWT token authentication via query parameter
2. **Connection Management**: Tracks active connections per user
3. **Conversation Subscriptions**: Users can subscribe/unsubscribe to conversations
4. **Real-time Messages**: Broadcasts new messages to all subscribers
5. **Typing Indicators**: Handles typing start/stop events
6. **Presence**: Supports online/offline status (ready for future use)
7. **Heartbeat**: Responds to ping events with pong

## WebSocket Events

### Client → Server

```json
// Subscribe to conversation
{
  "event": "subscribe",
  "channel": "conversation",
  "conversation_id": "uuid"
}

// Unsubscribe from conversation
{
  "event": "unsubscribe",
  "conversation_id": "uuid"
}

// Send typing indicator
{
  "event": "typing",
  "conversation_id": "uuid",
  "is_typing": true
}

// Presence update
{
  "event": "presence",
  "status": "online"
}

// Heartbeat
{
  "event": "ping"
}
```

### Server → Client

```json
// Connection confirmation
{
  "event": "connected",
  "message": "WebSocket connection established"
}

// New message
{
  "event": "message.new",
  "conversation_id": "uuid",
  "data": {
    "id": "message_uuid",
    "conversation_id": "uuid",
    "sender": {
      "id": "user_uuid",
      "username": "username",
      "full_name": "Full Name",
      "profile_image_url": "url"
    },
    "content": "Message content",
    "message_type": "text",
    "created_at": "2024-01-01T12:00:00Z"
  }
}

// Typing indicator
{
  "event": "typing",
  "conversation_id": "uuid",
  "data": {
    "user_id": "user_uuid",
    "user_name": "Full Name",
    "is_typing": true
  }
}

// Subscription confirmation
{
  "event": "subscribed",
  "conversation_id": "uuid"
}

// Heartbeat response
{
  "event": "pong"
}
```

## Integration

The WebSocket endpoint is automatically integrated with the message sending endpoint. When a message is sent via `POST /api/v1/conversations/{id}/messages`, it:
1. Saves the message to the database
2. Broadcasts the message to all subscribed users via WebSocket
3. Excludes the sender from the broadcast

## Testing

To test the WebSocket endpoint:

1. Start the backend server
2. Get a JWT token by logging in
3. Connect to `ws://localhost:8000/api/v1/ws?token={token}`
4. Send subscription event:
   ```json
   {"event": "subscribe", "channel": "conversation", "conversation_id": "your-conversation-id"}
   ```
5. Send a message via REST API - it should appear in the WebSocket connection

## Notes

- The WebSocket connection requires a valid JWT access token
- Connections are automatically cleaned up on disconnect
- The endpoint supports multiple concurrent connections per user
- Conversation subscriptions are verified against database to ensure user is a participant

