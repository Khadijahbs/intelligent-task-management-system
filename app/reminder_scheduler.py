from datetime import datetime

from flask_mail import Message
from app.models.user import db
from app.models.task import Task


def send_due_reminders(app):
    """
    Check for due task reminders and send Gmail notifications.
    """

    with app.app_context():

        now = datetime.now()

        due_tasks = Task.query.filter(
            Task.reminder_at.isnot(None),
            Task.reminder_at <= now,
            Task.reminder_sent == False,
            Task.status != "Completed"
        ).all()

        for task in due_tasks:

            user = task.user

            try:

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

                # Send the email
                mail = app.extensions["mail"]
                mail.send(message)

                # Prevent duplicate reminders
                task.reminder_sent = True

                print(
                    f"Gmail reminder sent for task: "
                    f"{task.title}"
                )

            except Exception as e:

                print(
                    f"Failed to send Gmail reminder for "
                    f"'{task.title}': {e}"
                )

        db.session.commit()