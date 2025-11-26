# Tribe Backend API

A production-ready FastAPI backend for the Tribe social accountability app. This backend provides comprehensive APIs for authentication, goal tracking, social features, real-time messaging, AI coaching, and more.

## 🚀 Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+ with SQLAlchemy 2.0 (async)
- **Cache**: Redis
- **Task Queue**: Celery
- **Migrations**: Alembic
- **Authentication**: JWT (access + refresh tokens)
- **File Storage**: AWS S3 / CloudFlare R2
- **AI**: OpenAI GPT-4
- **Push Notifications**: Firebase Cloud Messaging

## 📁 Project Structure

```
tribe_backend/
├── app/
│   ├── api/
│   │   ├── v1/               # API v1 endpoints
│   │   │   ├── auth.py       # Authentication
│   │   │   ├── users.py      # User profiles
│   │   │   ├── friends.py    # Friendships
│   │   │   ├── goals.py      # Goals & accountability
│   │   │   ├── posts.py      # Posts & comments
│   │   │   ├── stories.py    # 24h stories
│   │   │   ├── conversations.py  # Messaging
│   │   │   ├── ai_coach.py   # AI Coach
│   │   │   ├── notifications.py  # Notifications
│   │   │   ├── settings.py   # User settings
│   │   │   └── search.py     # Search
│   │   ├── deps.py           # Dependencies
│   │   └── router.py         # Router configuration
│   ├── core/
│   │   ├── config.py         # Settings
│   │   └── security.py       # Auth utilities
│   ├── db/
│   │   └── session.py        # Database session
│   ├── models/               # SQLAlchemy models
│   │   ├── user.py
│   │   ├── friendship.py
│   │   ├── goal.py
│   │   ├── post.py
│   │   ├── conversation.py
│   │   ├── notification.py
│   │   ├── settings.py
│   │   ├── activity.py
│   │   └── tribe.py
│   ├── schemas/              # Pydantic schemas
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── goal.py
│   │   ├── post.py
│   │   ├── conversation.py
│   │   ├── notification.py
│   │   └── settings.py
│   └── main.py               # FastAPI app
├── alembic/                  # Database migrations
├── tests/                    # Test files
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🛠️ Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd tribe_backend

# Start all services
docker-compose up -d

# The API will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload
```

## 📚 API Documentation

When running in development mode, API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 Authentication

The API uses JWT-based authentication with access and refresh tokens.

### Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "username",
    "full_name": "Full Name",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

### Using the Access Token
```bash
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"
```

## 🗃️ Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/logout` - Logout
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user

### Users
- `GET /api/v1/users/me` - Get my profile
- `PUT /api/v1/users/me` - Update my profile
- `PATCH /api/v1/users/me/profile-image` - Update profile image
- `GET /api/v1/users/{user_id}` - Get user profile
- `GET /api/v1/users/{user_id}/goals` - Get user's goals
- `GET /api/v1/users/{user_id}/posts` - Get user's posts

### Friends
- `GET /api/v1/friends` - Get friends list
- `GET /api/v1/friends/requests` - Get pending requests
- `POST /api/v1/friends/requests` - Send friend request
- `PUT /api/v1/friends/requests/{id}/accept` - Accept request
- `DELETE /api/v1/friends/{friend_id}` - Remove friend
- `GET /api/v1/friends/suggestions` - Get suggestions

### Goals
- `GET /api/v1/goals` - Get my goals
- `POST /api/v1/goals` - Create goal
- `GET /api/v1/goals/{goal_id}` - Get goal details
- `PUT /api/v1/goals/{goal_id}` - Update goal
- `POST /api/v1/goals/{goal_id}/contributions` - Add contribution
- `POST /api/v1/goals/{goal_id}/milestones` - Add milestone

### Posts & Stories
- `GET /api/v1/posts` - Get feed
- `POST /api/v1/posts` - Create post
- `POST /api/v1/posts/{post_id}/like` - Like post
- `POST /api/v1/posts/{post_id}/comments` - Add comment
- `GET /api/v1/stories` - Get stories
- `POST /api/v1/stories` - Create story

### Conversations
- `GET /api/v1/conversations` - Get conversations
- `POST /api/v1/conversations` - Create conversation
- `GET /api/v1/conversations/{id}/messages` - Get messages
- `POST /api/v1/conversations/{id}/messages` - Send message

### AI Coach
- `POST /api/v1/ai-coach/chat` - Chat with AI coach
- `GET /api/v1/ai-coach/suggestions` - Get AI suggestions

### Notifications
- `GET /api/v1/notifications` - Get notifications
- `PUT /api/v1/notifications/{id}/read` - Mark as read
- `GET /api/v1/notifications/preferences` - Get preferences

### Settings
- `GET /api/v1/settings` - Get all settings
- `PUT /api/v1/settings/privacy` - Update privacy
- `PUT /api/v1/settings/appearance` - Update appearance
- `GET /api/v1/settings/blocked-users` - Get blocked users

### Search
- `GET /api/v1/search?q=query` - Search all
- `GET /api/v1/search/users?q=query` - Search users
- `GET /api/v1/search/goals?q=query` - Search goals

## ⚙️ Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | development |
| `DEBUG` | Enable debug mode | true |
| `DATABASE_URL` | PostgreSQL connection URL | - |
| `REDIS_URL` | Redis connection URL | - |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | - |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | 60 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | 30 |
| `OPENAI_API_KEY` | OpenAI API key for AI coach | - |
| `AWS_ACCESS_KEY_ID` | AWS access key for S3 | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for S3 | - |
| `S3_BUCKET` | S3 bucket name | tribe-app-media |

## 🚀 Deployment

### Production Checklist

1. Set `DEBUG=false` and `APP_ENV=production`
2. Use strong, unique `JWT_SECRET_KEY`
3. Configure proper database connection pooling
4. Set up Redis for caching and Celery
5. Configure CORS origins properly
6. Enable HTTPS
7. Set up monitoring (Sentry, DataDog)
8. Configure rate limiting
9. Set up database backups

### AWS Deployment

The application is designed to work with:
- **EC2/ECS** for the FastAPI application
- **RDS** for PostgreSQL
- **ElastiCache** for Redis
- **S3 + CloudFront** for media storage
- **SQS** or Redis for Celery message broker

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## 📞 Support

For questions or issues, please open a GitHub issue.

