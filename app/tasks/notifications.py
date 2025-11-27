"""
Notification-related background tasks.
"""
from app.celery_app import celery_app


@celery_app.task(name="app.tasks.notifications.send_push_notification")
def send_push_notification(user_id: str, title: str, body: str, data: dict = None):
    """Send a push notification to a user."""
    # TODO: Implement push notification sending
    print(f"Sending push notification to user {user_id}: {title} - {body}")
    return {"status": "sent", "user_id": user_id}


@celery_app.task(name="app.tasks.notifications.send_bulk_notifications")
def send_bulk_notifications(user_ids: list[str], title: str, body: str, data: dict = None):
    """Send push notifications to multiple users."""
    # TODO: Implement bulk notification sending
    print(f"Sending bulk notifications to {len(user_ids)} users: {title} - {body}")
    return {"status": "sent", "count": len(user_ids)}

