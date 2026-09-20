from flask import Flask, redirect, url_for
from dotenv import load_dotenv
from flask_login import LoginManager
import os

from app.models.user import db, User
from app.routes.auth import auth


load_dotenv()


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

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///tasks.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


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
# RUN APPLICATION
# =========================

if __name__ == "__main__":

    print(
        "Starting Intelligent Task Management System..."
    )

    app.run(
        debug=True,
        use_reloader=False
    )