"""
Goal-related background tasks.
"""
from app.celery_app import celery_app


@celery_app.task(name="app.tasks.goals.send_goal_reminders")
def send_goal_reminders():
    """Send reminders for goals that are due soon."""
    # TODO: Implement goal reminder logic
    print("Sending goal reminders...")
    return {"status": "completed", "reminders_sent": 0}


@celery_app.task(name="app.tasks.goals.update_goal_progress")
def update_goal_progress(goal_id: str):
    """Update progress for a specific goal."""
    # TODO: Implement goal progress update
    print(f"Updating progress for goal {goal_id}")
    return {"status": "updated", "goal_id": goal_id}

