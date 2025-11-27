"""
Authentication-related background tasks.
"""
from app.celery_app import celery_app


@celery_app.task(name="app.tasks.auth.cleanup_expired_tokens")
def cleanup_expired_tokens():
    """Remove expired refresh tokens and password reset tokens."""
    # TODO: Implement token cleanup logic
    print("Cleaning up expired tokens...")
    return {"status": "completed", "tokens_removed": 0}

