from flask import Flask, redirect, url_for
from flask_mail import Mail, Message
from dotenv import load_dotenv
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler

from datetime import datetime
import os

from app.models.user import db, User
from app.models.task import Task
from app.routes.auth import auth


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# CREATE FLASK APP
# =========================================================

app = Flask(
    __name__,
    template_folder="app/templates"
)


# =========================================================
# FLASK CONFIGURATION
# =========================================================

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "development-secret-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///tasks.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# =========================================================
# EMAIL CONFIGURATION
# =========================================================

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USE_SSL"] = True
app.config["MAIL_USERNAME"] = os.getenv(
    "MAIL_USERNAME"
)
app.config["MAIL_PASSWORD"] = os.getenv(
    "MAIL_PASSWORD"
)

mail = Mail(app)


# =========================================================
# LOGIN MANAGER
# =========================================================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id)
    )


# =========================================================
# CONNECT DATABASE
# =========================================================

db.init_app(app)


# =========================================================
# REGISTER AUTHENTICATION ROUTES
# =========================================================

app.register_blueprint(auth)


# =========================================================
# HOME ROUTE
# =========================================================

@app.route("/")
def home():

    return redirect(
        url_for("auth.login")
    )


# =========================================================
# AUTOMATIC TASK REMINDER SYSTEM
# =========================================================

def send_due_reminders():

    print(
        "Checking for due task reminders..."
    )

    with app.app_context():

        now = datetime.now()

        due_tasks = Task.query.filter(
            Task.reminder_at.isnot(None),
            Task.reminder_at <= now,
            Task.reminder_sent == False,
            Task.status != "Completed"
        ).all()

        print(
            f"Due reminders found: {len(due_tasks)}"
        )

        for task in due_tasks:

            try:

                user = db.session.get(
                    User,
                    task.user_id
                )

                if not user:

                    print(
                        f"User not found for task: "
                        f"{task.title}"
                    )

                    continue

                # =================================================
                # CHECK USER PREFERENCES
                # =================================================

                if not user.task_reminders:

                    print(
                        f"Task reminders disabled for user: "
                        f"{user.username}"
                    )

                    continue

                if not user.email_notifications:

                    print(
                        f"Email notifications disabled for user: "
                        f"{user.username}"
                    )

                    continue

                # =================================================
                # CHECK EMAIL ADDRESS
                # =================================================

                if not user.email:

                    print(
                        f"No email address for user "
                        f"of task: {task.title}"
                    )

                    continue

                # =================================================
                # CREATE REMINDER EMAIL
                # =================================================

                message = Message(
                    subject=(
                        f"Task Reminder: "
                        f"{task.title}"
                    ),
                    sender=app.config[
                        "MAIL_USERNAME"
                    ],
                    recipients=[
                        user.email
                    ],
                    body=(
                        f"Hello {user.username},\n\n"
                        f"This is a reminder for your "
                        f"task.\n\n"
                        f"Task: {task.title}\n"
                        f"Priority: {task.priority}\n"
                        f"Importance: {task.importance}\n"
                        f"Deadline: "
                        f"{task.deadline.strftime('%Y-%m-%d %I:%M %p')}\n\n"
                        f"Please remember to complete "
                        f"the task before its deadline.\n\n"
                        f"TaskFlow\n"
                        f"Intelligent Task Management System"
                    )
                )

                print(
                    f"Sending reminder email for: "
                    f"{task.title}"
                )

                mail.send(message)

                # =================================================
                # MARK AS SENT ONLY AFTER SUCCESSFUL EMAIL
                # =================================================

                task.reminder_sent = True

                db.session.commit()

                print(
                    f"Reminder email sent successfully "
                    f"for: {task.title}"
                )

            except Exception as error:

                db.session.rollback()

                print(
                    f"ERROR sending reminder for "
                    f"'{task.title}': {error}"
                )


# =========================================================
# APSCHEDULER
# =========================================================

scheduler = BackgroundScheduler()


scheduler.add_job(
    func=send_due_reminders,
    trigger="interval",
    minutes=1,
    id="task_reminder_job",
    replace_existing=True
)


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

with app.app_context():

    db.create_all()


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    print(
        "Starting TaskFlow reminder scheduler..."
    )

    scheduler.start()

    print(
        "Task reminder scheduler started successfully."
    )

    app.run(
        debug=True,
        use_reloader=False
    )