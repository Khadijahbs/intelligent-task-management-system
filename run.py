from flask import Flask, redirect, url_for
from dotenv import load_dotenv
from flask_login import LoginManager
from flask_mail import Mail
import os
import threading
import time

from app.models.user import db, User
from app.routes.auth import auth
from app.reminder_scheduler import send_due_reminders


load_dotenv()


# =========================
# APPLICATION
# =========================

app = Flask(
    __name__,
    template_folder="app/templates"
)


# =========================
# APPLICATION CONFIGURATION
# =========================

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "development-secret-key"
)


# =========================
# DATABASE CONFIGURATION
# =========================
#
# Vercel's deployed filesystem is read-only.
# /tmp is writable on Vercel, but temporary.
#
# Local/Render:
#     SQLite database is stored normally.
#
# Vercel:
#     SQLite database is stored in /tmp.
#

if os.getenv("VERCEL") == "1":

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:////tmp/tasks.db"
    )

else:

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:///tasks.db"
    )


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# =========================
# GMAIL CONFIGURATION
# =========================

app.config["MAIL_SERVER"] = "smtp.gmail.com"

app.config["MAIL_PORT"] = 465

app.config["MAIL_USE_SSL"] = True

app.config["MAIL_USE_TLS"] = False

app.config["MAIL_USERNAME"] = os.getenv(
    "MAIL_USERNAME"
)

app.config["MAIL_PASSWORD"] = os.getenv(
    "MAIL_PASSWORD"
)

app.config["MAIL_DEFAULT_SENDER"] = os.getenv(
    "MAIL_USERNAME"
)


# =========================
# FLASK-MAIL
# =========================

mail = Mail()

mail.init_app(app)


# =========================
# LOGIN MANAGER
# =========================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id)
    )


# =========================
# DATABASE
# =========================

db.init_app(app)


# =========================
# BLUEPRINTS
# =========================

app.register_blueprint(auth)


# =========================
# HOME ROUTE
# =========================

@app.route("/")
def home():

    return redirect(
        url_for("auth.login")
    )


# =========================
# CREATE DATABASE TABLES
# =========================

with app.app_context():

    db.create_all()


# =========================
# BACKGROUND REMINDER SCHEDULER
# =========================
#
# The continuous scheduler works locally/Render.
#
# It is disabled on Vercel because Vercel
# Functions are serverless and should not run
# an infinite background thread.
#

def reminder_loop():

    while True:

        try:

            send_due_reminders(app)

        except Exception as e:

            print(
                f"Reminder scheduler error: {e}"
            )

        # Check every 30 seconds
        time.sleep(30)


if os.getenv("VERCEL") != "1":

    reminder_thread = threading.Thread(
        target=reminder_loop,
        daemon=True
    )

    reminder_thread.start()


# =========================
# RUN APPLICATION LOCALLY
# =========================

if __name__ == "__main__":

    print(
        "Starting Intelligent Task Management System..."
    )

    app.run(
        debug=True,
        use_reloader=False
    )