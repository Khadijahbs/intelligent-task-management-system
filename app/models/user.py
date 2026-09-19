from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )

    gender = db.Column(
        db.String(10),
        nullable=False,
        default="Female"
    )

    # =========================
    # PROFILE PHOTO
    # =========================
    profile_photo = db.Column(
        db.String(255),
        nullable=True
    )

    # =========================
    # EMAIL VERIFICATION
    # =========================
    is_verified = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    otp_code = db.Column(
        db.String(6),
        nullable=True
    )

    otp_created_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # =========================
    # USER PREFERENCES
    # =========================
    email_notifications = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    task_reminders = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    # =========================
    # USER TASKS
    # =========================
    tasks = db.relationship(
        "Task",
        backref="user",
        lazy=True
    )

    def __repr__(self):
        return f"<User {self.username}>"