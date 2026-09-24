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
    # Make sure SQLAlchemy accepts older postgres:// URLs
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

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


# Create database tables automatically
with app.app_context():
    db.create_all()


# ---------------------------------------
# REMINDER SCHEDULER
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