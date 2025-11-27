# Test Credentials

After running the seeding script (`make seed` or `python scripts/seed_data.py`), use these credentials to test the app.

## 🎯 Main Test Account (Recommended)

This account has the most data:
- **Email:** `brian@tribe.test`
- **Password:** `TestPass123!`
- **Username:** `brianokuku`

**What this account has:**
- ✅ Friends with 5 other users
- ✅ 5 direct conversations with message history
- ✅ Member of 1 group chat
- ✅ 5 individual goals (various statuses)
- ✅ Member of 3 group goals
- ✅ Multiple posts with likes and comments
- ✅ Stories
- ✅ Notifications

## 📋 All Test Accounts

| # | Email | Password | Username | Full Name |
|---|-------|----------|----------|-----------|
| 1 | brian@tribe.test | TestPass123! | brianokuku | Brian Okuku |
| 2 | cedric@tribe.test | TestPass123! | cedricochola | Cedric Ochola |
| 3 | brian.onyango@tribe.test | TestPass123! | brianonyango | Brian Onyango |
| 4 | robert@tribe.test | TestPass123! | robertangira | Robert Angira |
| 5 | derrick@tribe.test | TestPass123! | derrickjuma | Derrick Juma |
| 6 | alvin@tribe.test | TestPass123! | alvinamwata | Alvin Amwata |
| 7 | frank@tribe.test | TestPass123! | frankamwata | Frank Amwata |
| 8 | clarie@tribe.test | TestPass123! | clariegor | Clarie Gor |
| 9 | nicy@tribe.test | TestPass123! | nicyawino | Nicy Awino |
| 10 | tabitha@tribe.test | TestPass123! | tabithaombura | Tabitha Ombura |

**Note:** All accounts use the same password: `TestPass123!`

## 🔗 Social Network

### Friendships
- **brian@tribe.test** is friends with:
  - cedric@tribe.test
  - brian.onyango@tribe.test
  - robert@tribe.test
  - derrick@tribe.test
  - alvin@tribe.test

### Conversations
- **Direct Messages:** brian@tribe.test has active conversations with all 5 friends
- **Group Chat:** "Goal Achievers Squad" (includes first 5 users)

### Goals
- **Individual Goals:** Each user has 0-5 individual goals
- **Group Goals:** 3 group goals with multiple participants

### Posts
- First 8 users have 3-8 posts each
- Posts have 2-15 likes and 1-8 comments
- Some posts are linked to goals

## 🚀 Quick Start

1. **Run the seeding script:**
   ```bash
   cd /Users/brianokuku/Projects/tribe_backend
   make seed
   # or
   python scripts/seed_data.py
   ```

2. **Start the backend:**
   ```bash
   make dev
   # or
   docker-compose up
   ```

3. **Login in the Flutter app:**
   - Email: `brian@tribe.test`
   - Password: `TestPass123!`

4. **Explore the app:**
   - Dashboard will show your name and stats
   - Chat will show conversations with friends
   - Profile will show your goals and posts
   - Home feed will show posts from friends

## 📊 Data Summary

- **Users:** 10
- **Friendships:** ~15 accepted friendships
- **Conversations:** 6 (5 direct + 1 group)
- **Messages:** ~100+ messages across conversations
- **Goals:** ~15 goals (individual + group)
- **Posts:** ~40 posts with likes and comments
- **Stories:** ~6 active stories
- **Notifications:** Various types

## 🔄 Resetting Data

To clear and reseed:

```bash
# Option 1: Using Alembic
make migrate-down  # Downgrade all migrations
make migrate-up    # Reapply migrations
make seed          # Reseed data

# Option 2: Manual (if needed)
# Drop database and recreate, then:
make migrate
make seed
```

