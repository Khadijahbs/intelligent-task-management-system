from flask import Flask, redirect, url_for, jsonify, request
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

app = Flask(
    __name__,
    template_folder="app/templates"
)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "development-secret-key"
)

# ---------------------------------------
# DATABASE CONFIGURATION
# ---------------------------------------

database_url = os.getenv("DATABASE_URL")

if database_url:

    # Make sure SQLAlchemy accepts older
    # postgres:// URLs
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1
        )

    # Explicitly use psycopg2 because the
    # project uses psycopg2-binary
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+psycopg2://",
            1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        database_url
    )

else:

    # Local development continues to use SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:///tasks.db"
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ---------------------------------------
# MAIL CONFIGURATION
# ---------------------------------------

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

mail = Mail()
mail.init_app(app)

# ---------------------------------------
# LOGIN MANAGER
# ---------------------------------------

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(
        User,
        int(user_id)
    )


# ---------------------------------------
# DATABASE INITIALISATION
# ---------------------------------------

db.init_app(app)

app.register_blueprint(auth)


@app.route("/")
def home():
    return redirect(
        url_for("auth.login")
    )


# ---------------------------------------
# SECURE REMINDER ENDPOINT
# ---------------------------------------

@app.route(
    "/api/cron/reminders",
    methods=["GET"]
)
def cron_reminders():

    cron_secret = os.getenv(
        "CRON_SECRET"
    )

    authorization = request.headers.get(
        "Authorization",
        ""
    )

    expected_authorization = (
        f"Bearer {cron_secret}"
    )

    if (
        not cron_secret
        or authorization != expected_authorization
    ):
        return jsonify({
            "error": "Unauthorized"
        }), 401

    try:

        send_due_reminders(app)

        return jsonify({
            "success": True,
            "message": (
                "Due reminders checked successfully."
            )
        }), 200

    except Exception as error:

        import traceback

        print(
            "========================================"
        )

        print(
            "CRON REMINDER ERROR:"
        )

        print(
            f"Error type: {type(error).__name__}"
        )

        print(
            f"Error message: {repr(error)}"
        )

        traceback.print_exc()

        print(
            "========================================"
        )

        return jsonify({
            "success": False,
            "error": "Reminder processing failed."
        }), 500


# Create database tables automatically
with app.app_context():
    db.create_all()


# ---------------------------------------
# LOCAL REMINDER SCHEDULER
# ---------------------------------------

def reminder_loop():

    while True:

        try:
            send_due_reminders(app)

        except Exception as e:

            print(
                f"Reminder scheduler error: {e}"
            )

        time.sleep(30)


# Run background reminders locally.
# Vercel uses serverless functions, so the
# background thread is disabled there.
if os.getenv("VERCEL") != "1":

    reminder_thread = threading.Thread(
        target=reminder_loop,
        daemon=True
    )

    reminder_thread.start()


# ---------------------------------------
# RUN APPLICATION
# ---------------------------------------

if __name__ == "__main__":

    print(
        "Starting Intelligent Task Management System..."
    )

    app.run(
        debug=True,
        use_reloader=False
    )