from run import app
from app.models.user import db, User

with app.app_context():
    user = User.query.first()

    if user:
        user.is_verified = True
        user.otp_code = None
        user.otp_created_at = None

        db.session.commit()

        print("Existing user marked as verified.")
        print("Email:", user.email)
    else:
        print("No user found.")