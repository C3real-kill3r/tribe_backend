# Database Seeding Script

This script populates the database with comprehensive test data for development and testing.

## What Gets Seeded

- **10 Test Users** - Complete user profiles with bios, stats, and profile images
- **Friendships** - Network of accepted friendships between users
- **Conversations** - Direct messages and group chats with message history
- **Goals** - Individual and group goals with progress, milestones, and contributions
- **Posts** - Social media posts with likes and comments
- **Stories** - 24-hour ephemeral stories
- **Notifications** - Various notification types (friend requests, likes, goal updates)

## How to Run

### Option 1: Using Python directly

```bash
# Make sure you're in the backend directory
cd /Users/brianokuku/Projects/tribe_backend

# Activate virtual environment (if using one)
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Run the seeding script
python scripts/seed_data.py
```

### Option 2: Using Docker

If your backend is running in Docker:

```bash
# Execute the script inside the container
docker-compose exec app python scripts/seed_data.py
```

### Option 3: Add to Makefile (optional)

You can add this to your Makefile:

```makefile
seed:
	python scripts/seed_data.py
```

Then run: `make seed`

## Prerequisites

1. **Database must be running** - PostgreSQL should be accessible
2. **Migrations applied** - Run `alembic upgrade head` first
3. **Environment variables set** - Ensure `.env` file has correct `DATABASE_URL`

## Test Credentials

After running the script, you can use any of these accounts:

### Main Test Account (Recommended)
- **Email:** `brian@tribe.test`
- **Password:** `TestPass123!`
- **Username:** `brianokuku`

### Other Test Accounts

| Email | Password | Username |
|-------|----------|----------|
| cedric@tribe.test | TestPass123! | cedricochola |
| brian.onyango@tribe.test | TestPass123! | brianonyango |
| robert@tribe.test | TestPass123! | robertangira |
| derrick@tribe.test | TestPass123! | derrickjuma |
| alvin@tribe.test | TestPass123! | alvinamwata |
| frank@tribe.test | TestPass123! | frankamwata |
| clarie@tribe.test | TestPass123! | clariegor |
| nicy@tribe.test | TestPass123! | nicyawino |
| tabitha@tribe.test | TestPass123! | tabithaombura |

## What Data is Created

### Users
- 10 users with complete profiles
- Varying stats (goals achieved: 3-10, photos shared: 8-35)
- Profile and cover images
- Different last seen times

### Friendships
- Main user (brian@tribe.test) is friends with users 1-5
- Additional friendships between other users
- All friendships are in "accepted" status

### Conversations
- 5 direct conversations with message history (5-15 messages each)
- 1 group conversation ("Goal Achievers Squad") with 20 messages
- Messages have read receipts
- Varying unread counts

### Goals
- 5 individual goals for main user
- 3 group goals with multiple participants
- Goals have milestones, contributions, and progress tracking
- Mix of active, completed, and paused goals

### Posts
- 3-8 posts per user (first 8 users)
- Posts have likes (2-15 per post) and comments (1-8 per post)
- Some posts are linked to goals
- Mix of photo, video, and text posts

### Stories
- Stories for first 6 users
- Expiring within 24 hours
- Various view counts

### Notifications
- Friend request notifications
- Post like notifications
- Goal update notifications
- Mix of read and unread

## Resetting Data

To reset and reseed:

```bash
# Option 1: Drop and recreate database
alembic downgrade base
alembic upgrade head
python scripts/seed_data.py

# Option 2: Clear specific tables (manual SQL)
# Then run seed_data.py again
```

## Notes

- The script is idempotent - running it multiple times won't create duplicates
- Existing users are skipped (checked by email)
- All passwords are: `TestPass123!`
- Profile images use placeholder services (pravatar.cc, picsum.photos)
- Timestamps are randomized within realistic ranges

