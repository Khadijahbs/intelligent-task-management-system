from run import app
from app.models.user import db
from sqlalchemy import inspect, text


with app.app_context():

    inspector = inspect(db.engine)

    columns = [
        column["name"]
        for column in inspector.get_columns("user")
    ]

    if "profile_photo" in columns:
        print("profile_photo column already exists.")
    else:
        db.session.execute(
            text(
                "ALTER TABLE user "
                "ADD COLUMN profile_photo VARCHAR(255)"
            )
        )

        db.session.commit()

        print("profile_photo column added successfully.")