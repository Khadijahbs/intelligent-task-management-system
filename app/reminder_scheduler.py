from datetime import datetime, timedelta, timezone

from flask_mail import Message
from app.models.user import db
from app.models.task import Task


WAT = timezone(timedelta(hours=1))


def now_wat():
    """
    Return the current Nigerian time as a naive datetime.
    The database stores naive datetime values,
    so this keeps time comparisons consistent.
    """
    return datetime.now(WAT).replace(tzinfo=None)


def send_due_reminders(app):
    """
    Check for due task reminders and send Gmail notifications.
    This function can run independently of a logged-in user.
    """

    with app.app_context():

        now = now_wat()

        print("========================================")
        print("REMINDER SCHEDULER")
        print("Current Nigerian time:", now)
        print("========================================")

        due_tasks = Task.query.filter(
            Task.reminder_at.isnot(None),
            Task.reminder_at <= now,
            Task.reminder_sent == False,
            Task.status != "Completed"
        ).all()

        print(
            "Due reminders found:",
            len(due_tasks)
        )

        for task in due_tasks:

            user = task.user

            try:

                print(
                    f"Attempting to send reminder "
                    f"for: {task.title}"
                )

                message = Message(
                    subject=f"Task Reminder: {task.title}",
                    recipients=[user.email]
                )

                message.body = (
                    f"Hello {user.username},\n\n"
                    f"This is a reminder for your task:\n\n"
                    f"Task: {task.title}\n"
                    f"Priority: {task.priority}\n"
                    f"Importance: {task.importance}\n"
                    f"Deadline: "
                    f"{task.deadline.strftime('%d %B %Y, %I:%M %p')}\n\n"
                    f"You planned to work on "
                    f"'{task.title}'.\n\n"
                    f"Please remember to complete your task "
                    f"before the deadline.\n\n"
                    f"Regards,\n"
                    f"Intelligent Task Management System"
                )

                mail = app.extensions["mail"]

                mail.send(message)

                # Prevent duplicate reminders
                task.reminder_sent = True

                print(
                    f"GMAIL REMINDER SENT SUCCESSFULLY: "
                    f"{task.title}"
                )

            except Exception as error:

                import traceback

                print(
                    "========================================"
                )

                print(
                    f"GMAIL REMINDER ERROR: "
                    f"{task.title}"
                )

                print(
                    f"Error type: "
                    f"{type(error).__name__}"
                )

                print(
                    f"Error message: "
                    f"{repr(error)}"
                )

                traceback.print_exc()

                print(
                    "========================================"
                )

        db.session.commit()

        print(
            "Reminder scheduler finished."
        )