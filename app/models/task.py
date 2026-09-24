from datetime import datetime, timedelta, timezone

from .user import db


# =========================
# NIGERIAN TIME (WAT)
# =========================

WAT = timezone(timedelta(hours=1))


def now_wat():
    """
    Return the current Nigerian time as a naive datetime.
    The database currently stores naive datetime values,
    so this keeps all time comparisons consistent.
    """
    return datetime.now(WAT).replace(tzinfo=None)


class Task(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    priority = db.Column(
        db.String(20),
        default="Medium"
    )

    importance = db.Column(
        db.String(20),
        default="Medium"
    )

    status = db.Column(
        db.String(20),
        default="Pending"
    )

    deadline = db.Column(
        db.DateTime,
        nullable=False
    )

    # =========================
    # REMINDER FIELDS
    # =========================

    reminder_at = db.Column(
        db.DateTime,
        nullable=True
    )

    reminder_sent = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    # =========================
    # DATE FIELDS
    # =========================

    created_at = db.Column(
        db.DateTime,
        default=now_wat
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

    now = now_wat()

    time_remaining = deadline - now

    hours_remaining = (
        time_remaining.total_seconds() / 3600
    )

    # Deadline has passed
    if hours_remaining <= 0:
        return "High"

    # =========================
    # HIGH IMPORTANCE
    # =========================

    if importance == "High":

        if hours_remaining <= 72:
            return "High"

        else:
            return "Medium"

    # =========================
    # MEDIUM IMPORTANCE
    # =========================

    elif importance == "Medium":

        if hours_remaining <= 24:
            return "High"

        elif hours_remaining <= 72:
            return "Medium"

        else:
            return "Low"

    # =========================
    # LOW IMPORTANCE
    # =========================

    else:

        if hours_remaining <= 24:
            return "Medium"

        else:
            return "Low"


# =========================
# DEADLINE RISK
# =========================

def calculate_deadline_risk(deadline, status):

    # Completed tasks have no deadline risk
    if status == "Completed":
        return "No Risk"

    now = now_wat()

    time_remaining = deadline - now

    hours_remaining = (
        time_remaining.total_seconds() / 3600
    )

    # Deadline has passed
    if hours_remaining <= 0:
        return "High"

    # Due within 24 hours
    elif hours_remaining <= 24:
        return "High"

    # Due within 3 days
    elif hours_remaining <= 72:
        return "Medium"

    # More than 3 days remaining
    else:
        return "Low"


# =========================
# DEADLINE RISK REASON
# =========================

def get_deadline_risk_reason(deadline, status):

    # Completed tasks have no risk
    if status == "Completed":
        return "Task is already completed."

    now = now_wat()

    time_remaining = deadline - now

    hours_remaining = (
        time_remaining.total_seconds() / 3600
    )

    # Deadline has passed
    if hours_remaining <= 0:
        return "Task is overdue."

    # Due within 24 hours
    elif hours_remaining <= 24:
        return "Task is due within 24 hours."

    # Due within 3 days
    elif hours_remaining <= 72:
        return "Task is due within 3 days."

    # More than 3 days remaining
    else:
        return "More than 3 days remain before the deadline."


# =========================
# PRODUCTIVITY SCORE
# =========================

def calculate_productivity_score(tasks):
    """
    Calculate a productivity score based on:
    - task completion
    - on-time completion
    - pending workload
    """

    if not tasks:
        return 0

    total_tasks = len(tasks)

    # =========================
    # COMPLETED TASKS
    # =========================

    completed_tasks = [
        task
        for task in tasks
        if task.status == "Completed"
    ]

    completed_count = len(
        completed_tasks
    )

    # =========================
    # COMPLETION RATE
    # =========================

    completion_rate = (
        completed_count / total_tasks
    ) * 100

    # =========================
    # ON-TIME COMPLETION RATE
    # =========================

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
            len(on_time_tasks)
            / completed_count
        ) * 100

    else:

        on_time_rate = 0

    # =========================
    # PENDING RATE
    # =========================

    pending_tasks = [
        task
        for task in tasks
        if task.status != "Completed"
    ]

    pending_rate = (
        len(pending_tasks)
        / total_tasks
    ) * 100

    # =========================
    # PRODUCTIVITY SCORE
    # =========================

    productivity_score = (
        (completion_rate * 0.5)
        +
        (on_time_rate * 0.3)
        +
        ((100 - pending_rate) * 0.2)
    )

    return round(productivity_score)