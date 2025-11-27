"""
Database seeding script for Tribe backend.
This script populates the database with comprehensive test data.
"""
import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User
from app.models.friendship import Friendship
from app.models.conversation import Conversation, ConversationParticipant, Message, MessageRead
from app.models.goal import Goal, GoalParticipant, GoalContribution, GoalMilestone
from app.models.post import Post, PostLike, PostComment, Story
from app.models.notification import Notification

# Test users data
TEST_USERS = [
    {
        "email": "brian@tribe.test",
        "username": "brianokuku",
        "full_name": "Brian Okuku",
        "bio": "Chasing goals and making memories with my favorite people. ✨",
        "password": "TestPass123!",
        "goals_achieved": 5,
        "photos_shared": 12,
    },
    {
        "email": "cedric@tribe.test",
        "username": "cedricochola",
        "full_name": "Cedric Ochola",
        "bio": "Fitness enthusiast and goal achiever. Let's do this together! 💪",
        "password": "TestPass123!",
        "goals_achieved": 8,
        "photos_shared": 25,
    },
    {
        "email": "brian.onyango@tribe.test",
        "username": "brianonyango",
        "full_name": "Brian Onyango",
        "bio": "Building the future, one goal at a time.",
        "password": "TestPass123!",
        "goals_achieved": 3,
        "photos_shared": 8,
    },
    {
        "email": "robert@tribe.test",
        "username": "robertangira",
        "full_name": "Robert Angira",
        "bio": "Music producer and creative soul 🎵",
        "password": "TestPass123!",
        "goals_achieved": 6,
        "photos_shared": 18,
    },
    {
        "email": "derrick@tribe.test",
        "username": "derrickjuma",
        "full_name": "Derrick Juma",
        "bio": "Tech enthusiast | Always learning",
        "password": "TestPass123!",
        "goals_achieved": 4,
        "photos_shared": 15,
    },
    {
        "email": "alvin@tribe.test",
        "username": "alvinamwata",
        "full_name": "Alvin Amwata",
        "bio": "Adventure seeker 🌍",
        "password": "TestPass123!",
        "goals_achieved": 7,
        "photos_shared": 22,
    },
    {
        "email": "frank@tribe.test",
        "username": "frankamwata",
        "full_name": "Frank Amwata",
        "bio": "Photographer and storyteller 📸",
        "password": "TestPass123!",
        "goals_achieved": 9,
        "photos_shared": 35,
    },
    {
        "email": "clarie@tribe.test",
        "username": "clariegor",
        "full_name": "Clarie Gor",
        "bio": "Living life to the fullest! ✨",
        "password": "TestPass123!",
        "goals_achieved": 5,
        "photos_shared": 20,
    },
    {
        "email": "nicy@tribe.test",
        "username": "nicyawino",
        "full_name": "Nicy Awino",
        "bio": "Fashion designer | Creative mind",
        "password": "TestPass123!",
        "goals_achieved": 6,
        "photos_shared": 28,
    },
    {
        "email": "tabitha@tribe.test",
        "username": "tabithaombura",
        "full_name": "Tabitha Ombura",
        "bio": "Entrepreneur | Goal getter",
        "password": "TestPass123!",
        "goals_achieved": 10,
        "photos_shared": 30,
    },
]

# Sample messages for conversations
SAMPLE_MESSAGES = [
    "Hey! How's your goal progress going?",
    "Just completed my daily workout! 💪",
    "We should plan a group goal together",
    "Thanks for the motivation!",
    "Check out this new photo I posted",
    "Great job on achieving that milestone!",
    "Let's catch up this weekend",
    "I'm so close to my target!",
    "Your progress is inspiring!",
    "We got this! 💯",
    "Just hit 75% of my goal!",
    "Can't wait to celebrate together",
    "This accountability thing really works!",
    "Thanks for being my accountability partner",
    "Let's push each other to finish strong",
]

# Sample goal titles
GOAL_TITLES = [
    "Run a 5K Marathon",
    "Save $5,000 for Vacation",
    "Read 12 Books This Year",
    "Meditate Daily for 30 Days",
    "Learn Spanish",
    "Build a Mobile App",
    "Lose 10kg",
    "Start a Side Business",
    "Complete Online Course",
    "Travel to 3 New Countries",
    "Write a Book",
    "Get Fit and Healthy",
    "Master Photography",
    "Learn Guitar",
    "Build Emergency Fund",
]

# Sample post captions
POST_CAPTIONS = [
    "Just completed my morning run! Feeling amazing! 🏃‍♂️",
    "Weekend trip with the crew! Making memories ✨",
    "Another milestone achieved! Thanks for the support everyone!",
    "Beautiful sunset from today's hike 🌅",
    "Progress update: 75% done! Almost there!",
    "Celebrating small wins today! 🎉",
    "Accountability works! Thanks to my tribe 💪",
    "New personal best! Couldn't have done it alone",
    "Weekend vibes with friends 🎊",
    "Goal achieved! Time to set new ones 🚀",
]


async def create_users(session: AsyncSession) -> List[User]:
    """Create test users."""
    print("Creating test users...")
    users = []
    
    for user_data in TEST_USERS:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"  User {user_data['username']} already exists, skipping...")
            users.append(existing_user)
            continue
        
        user = User(
            email=user_data["email"],
            username=user_data["username"],
            full_name=user_data["full_name"],
            bio=user_data["bio"],
            password_hash=get_password_hash(user_data["password"]),
            goals_achieved=user_data["goals_achieved"],
            photos_shared=user_data["photos_shared"],
            email_verified=True,
            is_active=True,
            last_seen_at=datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
            profile_image_url=f"https://i.pravatar.cc/150?u={user_data['username']}",
            cover_image_url=f"https://picsum.photos/800/300?random={random.randint(1, 100)}",
        )
        session.add(user)
        users.append(user)
        print(f"  Created user: {user_data['username']}")
    
    await session.commit()
    # Refresh to get IDs
    for user in users:
        await session.refresh(user)
    
    return users


async def create_friendships(session: AsyncSession, users: List[User]):
    """Create friendships between users."""
    print("Creating friendships...")
    
    # Create a network of friendships
    # User 0 (brian) is friends with users 1-5
    main_user = users[0]
    
    for i in range(1, min(6, len(users))):
        friend = users[i]
        
        # Check if friendship already exists
        result = await session.execute(
            select(Friendship).where(
                Friendship.user_id == main_user.id,
                Friendship.friend_id == friend.id
            )
        )
        if result.scalar_one_or_none():
            continue
        
        # Create bidirectional friendship
        friendship1 = Friendship(
            user_id=main_user.id,
            friend_id=friend.id,
            status="accepted",
            requested_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            accepted_at=datetime.utcnow() - timedelta(days=random.randint(1, 25)),
        )
        friendship2 = Friendship(
            user_id=friend.id,
            friend_id=main_user.id,
            status="accepted",
            requested_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            accepted_at=datetime.utcnow() - timedelta(days=random.randint(1, 25)),
        )
        session.add(friendship1)
        session.add(friendship2)
        print(f"  Created friendship: {main_user.username} <-> {friend.username}")
    
    # Create some friendships between other users
    for i in range(1, min(5, len(users))):
        for j in range(i + 1, min(i + 3, len(users))):
            if random.random() > 0.5:  # 50% chance
                user1 = users[i]
                user2 = users[j]
                
                result = await session.execute(
                    select(Friendship).where(
                        Friendship.user_id == user1.id,
                        Friendship.friend_id == user2.id
                    )
                )
                if result.scalar_one_or_none():
                    continue
                
                friendship1 = Friendship(
                    user_id=user1.id,
                    friend_id=user2.id,
                    status="accepted",
                    requested_at=datetime.utcnow() - timedelta(days=random.randint(1, 20)),
                    accepted_at=datetime.utcnow() - timedelta(days=random.randint(1, 18)),
                )
                friendship2 = Friendship(
                    user_id=user2.id,
                    friend_id=user1.id,
                    status="accepted",
                    requested_at=datetime.utcnow() - timedelta(days=random.randint(1, 20)),
                    accepted_at=datetime.utcnow() - timedelta(days=random.randint(1, 18)),
                )
                session.add(friendship1)
                session.add(friendship2)
    
    await session.commit()
    print("  Friendships created!")


async def create_conversations(session: AsyncSession, users: List[User]):
    """Create conversations and messages."""
    print("Creating conversations and messages...")
    
    main_user = users[0]
    
    # Create direct conversations with friends
    for i in range(1, min(6, len(users))):
        friend = users[i]
        
        # Check if conversation exists by querying participants directly
        # Find conversations where main_user is a participant
        result1 = await session.execute(
            select(ConversationParticipant.conversation_id).where(
                ConversationParticipant.user_id == main_user.id
            )
        )
        main_user_convs = {row[0] for row in result1.all()}
        
        # Find conversations where friend is a participant
        result2 = await session.execute(
            select(ConversationParticipant.conversation_id).where(
                ConversationParticipant.user_id == friend.id
            )
        )
        friend_convs = {row[0] for row in result2.all()}
        
        # Find intersection (conversations with both)
        common_convs = main_user_convs & friend_convs
        
        conversation = None
        if common_convs:
            # Check if it's a direct conversation with exactly 2 participants
            for conv_id in common_convs:
                conv_result = await session.execute(
                    select(Conversation).where(Conversation.id == conv_id)
                )
                conv = conv_result.scalar_one_or_none()
                if conv and conv.conversation_type == "direct":
                    # Count participants
                    part_count_result = await session.execute(
                        select(ConversationParticipant).where(
                            ConversationParticipant.conversation_id == conv_id
                        )
                    )
                    part_count = len(part_count_result.scalars().all())
                    if part_count == 2:
                        conversation = conv
                        break
        
        if not conversation:
            conversation = Conversation(
                conversation_type="direct",
                is_group=False,
                last_message_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
            )
            session.add(conversation)
            await session.flush()
            
            # Add participants
            participant1 = ConversationParticipant(
                conversation_id=conversation.id,
                user_id=main_user.id,
                role="member",
                last_read_at=datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
                unread_count=random.randint(0, 3),
            )
            participant2 = ConversationParticipant(
                conversation_id=conversation.id,
                user_id=friend.id,
                role="member",
                last_read_at=datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
                unread_count=random.randint(0, 5),
            )
            session.add(participant1)
            session.add(participant2)
            await session.flush()
        
        # Create messages in conversation
        num_messages = random.randint(5, 15)
        for j in range(num_messages):
            sender = main_user if j % 2 == 0 else friend
            message_time = datetime.utcnow() - timedelta(
                hours=random.randint(1, 72),
                minutes=random.randint(0, 59)
            )
            
            message = Message(
                conversation_id=conversation.id,
                sender_id=sender.id,
                content=random.choice(SAMPLE_MESSAGES),
                message_type="text",
                created_at=message_time,
            )
            session.add(message)
            await session.flush()
            
            # Create read receipts for some messages
            if random.random() > 0.3:
                reader = friend if sender == main_user else main_user
                read_receipt = MessageRead(
                    message_id=message.id,
                    user_id=reader.id,
                    read_at=message_time + timedelta(minutes=random.randint(1, 30)),
                )
                session.add(read_receipt)
        
        # Update conversation last message time
        conversation.last_message_at = datetime.utcnow() - timedelta(hours=random.randint(1, 24))
        print(f"  Created conversation with {friend.username} ({num_messages} messages)")
    
    # Create a group conversation
    group_members = users[:5]  # First 5 users
    group_conv = Conversation(
        conversation_type="group",
        is_group=True,
        name="Goal Achievers Squad",
        image_url="https://picsum.photos/200/200?random=group",
        last_message_at=datetime.utcnow() - timedelta(hours=random.randint(1, 12)),
    )
    session.add(group_conv)
    await session.flush()
    
    # Add group participants
    for member in group_members:
        participant = ConversationParticipant(
            conversation_id=group_conv.id,
            user_id=member.id,
            role="admin" if member == main_user else "member",
            last_read_at=datetime.utcnow() - timedelta(hours=random.randint(0, 6)),
            unread_count=random.randint(0, 10),
        )
        session.add(participant)
    
    # Add messages to group
    for i in range(20):
        sender = random.choice(group_members)
        message_time = datetime.utcnow() - timedelta(
            hours=random.randint(1, 24),
            minutes=random.randint(0, 59)
        )
        
        message = Message(
            conversation_id=group_conv.id,
            sender_id=sender.id,
            content=random.choice(SAMPLE_MESSAGES),
            message_type="text",
            created_at=message_time,
        )
        session.add(message)
    
    await session.commit()
    print("  Conversations and messages created!")


async def create_goals(session: AsyncSession, users: List[User]):
    """Create goals (individual and group)."""
    print("Creating goals...")
    
    main_user = users[0]
    
    # Create individual goals for main user
    for i in range(5):
        goal_title = random.choice(GOAL_TITLES)
        goal = Goal(
            creator_id=main_user.id,
            title=goal_title,
            description=f"Working towards {goal_title.lower()}",
            category=random.choice(["fitness", "savings", "education", "health", "career"]),
            goal_type="individual",
            target_type=random.choice(["amount", "date", "milestone"]),
            target_amount=Decimal(random.randint(100, 10000)) if random.random() > 0.5 else None,
            target_date=datetime.utcnow().date() + timedelta(days=random.randint(30, 180)) if random.random() > 0.5 else None,
            current_amount=Decimal(random.randint(0, 5000)),
            progress_percentage=random.uniform(0, 100),
            status=random.choice(["active", "active", "active", "completed", "paused"]),
            is_public=random.random() > 0.3,
            image_url=f"https://picsum.photos/400/300?random=goal{i}",
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
        )
        session.add(goal)
        await session.flush()
        
        # Add creator as participant
        participant = GoalParticipant(
            goal_id=goal.id,
            user_id=main_user.id,
            role="creator",
            contribution_amount=goal.current_amount,
        )
        session.add(participant)
        
        # Add some contributions
        if goal.status == "active":
            for j in range(random.randint(2, 5)):
                contribution = GoalContribution(
                    goal_id=goal.id,
                    user_id=main_user.id,
                    amount=Decimal(random.randint(10, 500)),
                    note=f"Progress update #{j+1}",
                    contribution_type=random.choice(["monetary", "milestone", "checkin"]),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                )
                session.add(contribution)
        
        # Add milestones
        for j in range(random.randint(2, 4)):
            milestone = GoalMilestone(
                goal_id=goal.id,
                title=f"Milestone {j+1}",
                description=f"Reach {25 * (j+1)}% progress",
                target_value=Decimal(goal.target_amount or 1000) * Decimal(0.25 * (j+1)) if goal.target_amount else None,
                achieved=goal.progress_percentage >= (25 * (j+1)),
                achieved_at=datetime.utcnow() - timedelta(days=random.randint(1, 20)) if goal.progress_percentage >= (25 * (j+1)) else None,
                achieved_by=main_user.id if goal.progress_percentage >= (25 * (j+1)) else None,
                order_index=j,
            )
            session.add(milestone)
        
        print(f"  Created goal: {goal_title}")
    
    # Create group goals
    for i in range(3):
        goal_title = random.choice(GOAL_TITLES)
        group_members = users[:4]  # First 4 users
        creator = random.choice(group_members)
        
        goal = Goal(
            creator_id=creator.id,
            title=f"Group: {goal_title}",
            description=f"Team goal: {goal_title.lower()}",
            category=random.choice(["fitness", "savings", "education"]),
            goal_type="group",
            target_type="amount",
            target_amount=Decimal(random.randint(1000, 10000)),
            current_amount=Decimal(random.randint(100, 5000)),
            progress_percentage=random.uniform(10, 80),
            status="active",
            is_public=True,
            image_url=f"https://picsum.photos/400/300?random=groupgoal{i}",
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
        )
        session.add(goal)
        await session.flush()
        
        # Add all group members as participants
        total_contribution = Decimal(0)
        for member in group_members:
            contribution = Decimal(random.randint(50, 500))
            total_contribution += contribution
            participant = GoalParticipant(
                goal_id=goal.id,
                user_id=member.id,
                role="creator" if member == creator else "member",
                contribution_amount=contribution,
            )
            session.add(participant)
        
        goal.current_amount = total_contribution
        goal.progress_percentage = float((total_contribution / goal.target_amount) * 100)
        
        print(f"  Created group goal: {goal_title}")
    
    await session.commit()
    print("  Goals created!")


async def create_posts(session: AsyncSession, users: List[User]):
    """Create posts with likes and comments."""
    print("Creating posts...")
    
    # Get goals for linking posts
    result = await session.execute(select(Goal))
    goals = result.scalars().all()
    
    for user in users[:8]:  # First 8 users create posts
        num_posts = random.randint(3, 8)
        for i in range(num_posts):
            # Randomly link to a goal
            linked_goal = random.choice(goals) if goals and random.random() > 0.6 else None
            
            post = Post(
                user_id=user.id,
                caption=random.choice(POST_CAPTIONS),
                post_type=random.choice(["photo", "photo", "photo", "video", "text"]),
                goal_id=linked_goal.id if linked_goal else None,
                media_url=f"https://picsum.photos/800/600?random=post{user.id}{i}",
                media_thumbnail_url=f"https://picsum.photos/400/300?random=post{user.id}{i}",
                visibility=random.choice(["public", "friends", "friends"]),
                likes_count=0,
                comments_count=0,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
            )
            session.add(post)
            await session.flush()
            
            # Add likes
            num_likes = random.randint(2, 15)
            likers = random.sample([u for u in users if u.id != user.id], min(num_likes, len(users) - 1))
            for liker in likers:
                like = PostLike(
                    post_id=post.id,
                    user_id=liker.id,
                    created_at=post.created_at + timedelta(minutes=random.randint(1, 60)),
                )
                session.add(like)
                post.likes_count += 1
            
            # Add comments
            num_comments = random.randint(1, 8)
            commenters = random.sample([u for u in users if u.id != user.id], min(num_comments, len(users) - 1))
            for commenter in commenters:
                comment = PostComment(
                    post_id=post.id,
                    user_id=commenter.id,
                    content=random.choice([
                        "Great job! Keep it up!",
                        "So proud of you!",
                        "This is amazing!",
                        "You're inspiring!",
                        "Way to go!",
                        "Keep pushing!",
                    ]),
                    created_at=post.created_at + timedelta(hours=random.randint(1, 24)),
                )
                session.add(comment)
                post.comments_count += 1
            
            # Update user's photos_shared count
            if post.post_type in ["photo", "video"]:
                user.photos_shared += 1
            
            print(f"  Created post by {user.username} ({post.likes_count} likes, {post.comments_count} comments)")
    
    await session.commit()
    print("  Posts created!")


async def create_stories(session: AsyncSession, users: List[User]):
    """Create 24-hour stories."""
    print("Creating stories...")
    
    for user in users[:6]:  # First 6 users have stories
        if random.random() > 0.3:  # 70% chance
            story = Story(
                user_id=user.id,
                media_url=f"https://picsum.photos/400/600?random=story{user.id}",
                media_thumbnail_url=f"https://picsum.photos/200/300?random=story{user.id}",
                media_type="image",
                duration=5,
                views_count=random.randint(5, 50),
                expires_at=datetime.utcnow() + timedelta(hours=random.randint(1, 23)),
                created_at=datetime.utcnow() - timedelta(hours=random.randint(0, 12)),
            )
            session.add(story)
            print(f"  Created story for {user.username}")
    
    await session.commit()
    print("  Stories created!")


async def create_notifications(session: AsyncSession, users: List[User]):
    """Create notifications for users."""
    print("Creating notifications...")
    
    # Get some posts and goals for notifications
    result = await session.execute(select(Post))
    posts = result.scalars().all()[:10]
    
    result = await session.execute(select(Goal))
    goals = result.scalars().all()[:5]
    
    main_user = users[0]
    
    # Friend request notifications
    for i in range(6, min(8, len(users))):
        notification = Notification(
            user_id=main_user.id,
            notification_type="friend_request",
            title="New Friend Request",
            message=f"{users[i].full_name} sent you a friend request",
            related_user_id=users[i].id,
            is_read=random.random() > 0.5,
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
        )
        session.add(notification)
    
    # Post like notifications
    for post in posts[:5]:
        if post.user_id != main_user.id:
            notification = Notification(
                user_id=post.user_id,
                notification_type="post_like",
                title="New Like",
                message=f"{main_user.full_name} liked your post",
                related_user_id=main_user.id,
                related_post_id=post.id,
                is_read=random.random() > 0.6,
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
            )
            session.add(notification)
    
    # Goal update notifications
    for goal in goals[:3]:
        if goal.creator_id != main_user.id:
            notification = Notification(
                user_id=goal.creator_id,
                notification_type="goal_update",
                title="Goal Progress",
                message=f"{main_user.full_name} made progress on your group goal",
                related_user_id=main_user.id,
                related_goal_id=goal.id,
                is_read=random.random() > 0.5,
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 12)),
            )
            session.add(notification)
    
    await session.commit()
    print("  Notifications created!")


async def main():
    """Main seeding function."""
    print("=" * 60)
    print("Starting database seeding...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        try:
            # Create users
            users = await create_users(session)
            
            # Create friendships
            await create_friendships(session, users)
            
            # Create conversations and messages
            await create_conversations(session, users)
            
            # Create goals
            await create_goals(session, users)
            
            # Create posts
            await create_posts(session, users)
            
            # Create stories
            await create_stories(session, users)
            
            # Create notifications
            await create_notifications(session, users)
            
            print("=" * 60)
            print("✅ Database seeding completed successfully!")
            print("=" * 60)
            print("\n📋 Test Credentials:")
            print("-" * 60)
            for user_data in TEST_USERS:
                print(f"Email: {user_data['email']}")
                print(f"Password: {user_data['password']}")
                print(f"Username: {user_data['username']}")
                print("-" * 60)
            print("\n💡 Recommended test account:")
            print(f"   Email: {TEST_USERS[0]['email']}")
            print(f"   Password: {TEST_USERS[0]['password']}")
            print("=" * 60)
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error during seeding: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(main())

