from run import app, db
from sqlalchemy import inspect, text

with app.app_context():
    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("user")}

    print("Current columns:", columns)

    if "is_verified" not in columns:
        db.session.execute(
            text("ALTER TABLE user ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 0")
        )
        print("Added is_verified")

    if "otp_code" not in columns:
        db.session.execute(
            text("ALTER TABLE user ADD COLUMN otp_code VARCHAR(6)")
        )
        print("Added otp_code")

    if "otp_created_at" not in columns:
        db.session.execute(
            text("ALTER TABLE user ADD COLUMN otp_created_at DATETIME")
        )
        print("Added otp_created_at")

    db.session.commit()

    print("USER TABLE UPDATED SUCCESSFULLY")