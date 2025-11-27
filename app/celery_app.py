"""
Celery application configuration for background tasks.
"""
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "tribe",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.notifications",
        "app.tasks.goals",
        "app.tasks.posts",
        "app.tasks.analytics",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    # Task routing
    task_routes={
        "app.tasks.notifications.*": {"queue": "notifications"},
        "app.tasks.goals.*": {"queue": "goals"},
        "app.tasks.posts.*": {"queue": "posts"},
        "app.tasks.analytics.*": {"queue": "analytics"},
    },
    # Periodic tasks (Celery Beat)
    beat_schedule={
        "send-goal-reminders": {
            "task": "app.tasks.goals.send_goal_reminders",
            "schedule": 60.0,  # Every minute
        },
        "cleanup-expired-tokens": {
            "task": "app.tasks.auth.cleanup_expired_tokens",
            "schedule": 3600.0,  # Every hour
        },
        "update-user-stats": {
            "task": "app.tasks.analytics.update_user_stats",
            "schedule": 300.0,  # Every 5 minutes
        },
        "cleanup-old-stories": {
            "task": "app.tasks.posts.cleanup_old_stories",
            "schedule": 3600.0,  # Every hour
        },
    },
)

if __name__ == "__main__":
    celery_app.start()

