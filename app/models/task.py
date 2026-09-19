from datetime import datetime
from .user import db


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    priority = db.Column(db.String(20), default="Medium")
    importance = db.Column(db.String(20), default="Medium")
    status = db.Column(db.String(20), default="Pending")

    deadline = db.Column(db.DateTime, nullable=False)

    # =========================
    # REMINDER FIELDS
    # =========================

    reminder_at = db.Column(db.DateTime, nullable=True)
    reminder_sent = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    completed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    def __repr__(self):
        return f"<Task {self.title}>"


# =========================
# INTELLIGENT PRIORITY
# =========================

def recommend_priority(deadline, importance):
    from datetime import datetime

    now = datetime.utcnow()

    time_remaining = deadline - now

    hours_remaining = (
        time_remaining.total_seconds() / 3600
    )

    if hours_remaining <= 0:
        return "High"

    if importance == "High":

        if hours_remaining <= 72:
            return "High"
        else:
            return "Medium"

    elif importance == "Medium":

        if hours_remaining <= 24:
            return "High"

        elif hours_remaining <= 72:
            return "Medium"

        else:
            return "Low"

    else:

        if hours_remaining <= 24:
            return "Medium"
        else:
            return "Low"


# =========================
# DEADLINE RISK
# =========================

def calculate_deadline_risk(deadline, status):
    from datetime import datetime

    if status == "Completed":
        return "No Risk"

    now = datetime.utcnow()

    time_remaining = deadline - now

    hours_remaining = (
        time_remaining.total_seconds() / 3600
    )

    if hours_remaining <= 0:
        return "High"

    elif hours_remaining <= 24:
        return "High"

    elif hours_remaining <= 72:
        return "Medium"

    else:
        return "Low"


# =========================
# DEADLINE RISK REASON
# =========================

def get_deadline_risk_reason(deadline, status):
    from datetime import datetime

    if status == "Completed":
        return "Task is already completed."

    now = datetime.utcnow()

    time_remaining = deadline - now

    hours_remaining = (
        time_remaining.total_seconds() / 3600
    )

    if hours_remaining <= 0:
        return "Task is overdue."

    elif hours_remaining <= 24:
        return "Task is due within 24 hours."

    elif hours_remaining <= 72:
        return "Task is due within 3 days."

    else:
        return "More than 3 days remain before the deadline."


# =========================
# PRODUCTIVITY SCORE
# =========================

def calculate_productivity_score(tasks):
    """
    Calculate a productivity score based on task completion,
    on-time completion, and pending workload.
    """

    if not tasks:
        return 0

    total_tasks = len(tasks)

    completed_tasks = [
        task
        for task in tasks
        if task.status == "Completed"
    ]

    completed_count = len(completed_tasks)

    completion_rate = (
        completed_count / total_tasks
    ) * 100

    if completed_count > 0:

        on_time_tasks = [
            task
            for task in completed_tasks
            if (
                task.completed_at
                and task.completed_at <= task.deadline
            )
        ]

        on_time_rate = (
            len(on_time_tasks) / completed_count
        ) * 100

    else:

        on_time_rate = 0

    pending_tasks = [
        task
        for task in tasks
        if task.status != "Completed"
    ]

    pending_rate = (
        len(pending_tasks) / total_tasks
    ) * 100

    productivity_score = (
        (completion_rate * 0.5)
        +
        (on_time_rate * 0.3)
        +
        ((100 - pending_rate) * 0.2)
    )

    return round(productivity_score)