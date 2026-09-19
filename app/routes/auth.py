from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    current_app,
    jsonify
)

from datetime import datetime, timedelta

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from flask_login import (
    login_user,
    login_required,
    current_user,
    logout_user
)

from flask_mail import Message

from app.models.user import db, User

from app.models.task import (
    Task,
    recommend_priority,
    calculate_deadline_risk,
    get_deadline_risk_reason,
    calculate_productivity_score
)

from app.ml.productivity_model import predict_productivity


auth = Blueprint("auth", __name__)


# =========================
# REGISTER
# =========================
@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        gender = request.form["gender"]

        # Gmail-only registration
        if not email.endswith("@gmail.com"):
            return "Please use a valid Gmail address."

        # Check if username already exists
        if User.query.filter_by(
            username=username
        ).first():

            return "Username already exists."

        # Check if email already exists
        if User.query.filter_by(
            email=email
        ).first():

            return "Email already registered."

        hashed_password = generate_password_hash(
            password
        )

        # Generate a 6-digit OTP
        import secrets

        otp = str(
            secrets.randbelow(900000) + 100000
        )

        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            gender=gender,
            is_verified=False,
            otp_code=otp,
            otp_created_at=datetime.utcnow()
        )

        db.session.add(new_user)
        db.session.commit()

        # Send OTP email
        msg = Message(
            subject=(
                "Task Management System - "
                "Email Verification"
            ),
            sender=current_app.config[
                "MAIL_USERNAME"
            ],
            recipients=[email],
            body=f"""Hello {username},

Thank you for registering for the Intelligent Task Management System.

Your email verification code is:

{otp}

Please enter this code on the verification page to verify your account.

This code is valid for 10 minutes.

If you did not create this account, please ignore this email.

Regards,
Intelligent Task Management System
"""
        )

        current_app.extensions[
            "mail"
        ].send(msg)

        return redirect(
            url_for(
                "auth.verify_otp",
                email=email
            )
        )

    return render_template(
        "register.html"
    )


# =========================
# VERIFY OTP
# =========================
@auth.route(
    "/verify-otp",
    methods=["GET", "POST"]
)
def verify_otp():

    email = (
        request.args.get("email")
        or request.form.get("email")
    )

    if not email:

        return redirect(
            url_for("auth.register")
        )

    email = email.lower()

    user = User.query.filter_by(
        email=email
    ).first()

    if not user:

        return "Account not found."

    if request.method == "POST":

        otp = request.form[
            "otp"
        ].strip()

        if not user.otp_code:

            return (
                "No verification code found. "
                "Please register again."
            )

        # Check OTP expiration
        if not user.otp_created_at:

            return (
                "Verification code has expired."
            )

        elapsed_time = (
            datetime.utcnow()
            - user.otp_created_at
        )

        # OTP expires after 10 minutes
        if elapsed_time.total_seconds() > 600:

            return (
                "Verification code has expired. "
                "Please register again."
            )

        # Check OTP
        if otp != user.otp_code:

            return "Invalid verification code."

        # Verify account
        user.is_verified = True
        user.otp_code = None
        user.otp_created_at = None

        db.session.commit()

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "verify_otp.html",
        email=email
    )


# =========================
# LOGIN
# =========================
@auth.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form[
            "email"
        ].strip().lower()

        password = request.form[
            "password"
        ]

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            # Prevent unverified users
            # from logging in
            if not user.is_verified:

                return redirect(
                    url_for(
                        "auth.verify_otp",
                        email=user.email
                    )
                )

            login_user(user)

            return redirect(
                url_for("auth.dashboard")
            )

        return "Invalid email or password!"

    return render_template(
        "login.html"
    )


# =========================
# LOGOUT
# =========================
@auth.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("auth.login")
    )


# =========================
# DASHBOARD
# =========================
@auth.route("/dashboard")
@login_required
def dashboard():

    tasks = Task.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Task.created_at.desc()
    ).all()

    # Existing productivity score
    productivity_score = (
        calculate_productivity_score(
            tasks
        )
    )

    # =========================
    # ML PRODUCTIVITY CLASSIFICATION
    # =========================

    total_task_count = len(tasks)

    completed_task_list = [
        task
        for task in tasks
        if task.status == "Completed"
    ]

    completed_task_count = len(
        completed_task_list
    )

    pending_task_count = (
        total_task_count
        - completed_task_count
    )

    # Calculate completion rate
    # and pending rate
    if total_task_count > 0:

        completion_rate = (
            completed_task_count
            / total_task_count
        ) * 100

        pending_rate = (
            pending_task_count
            / total_task_count
        ) * 100

    else:

        completion_rate = 0
        pending_rate = 0

    # Calculate on-time completion rate
    if completed_task_count > 0:

        on_time_task_count = len([

            task

            for task in completed_task_list

            if task.completed_at
            and task.completed_at <= task.deadline

        ])

        on_time_rate = (
            on_time_task_count
            / completed_task_count
        ) * 100

    else:

        on_time_rate = 0

    # Only classify productivity when
    # sufficient task history is available.
    if completed_task_count >= 10:

        productivity_prediction = (
            predict_productivity(
                completion_rate,
                on_time_rate,
                pending_rate,
                total_task_count
            )
        )

    else:

        productivity_prediction = (
            "Not enough data"
        )

    # =========================
    # DEADLINE RISK
    # =========================

    for task in tasks:

        task.deadline_risk = (
            calculate_deadline_risk(
                task.deadline,
                task.status
            )
        )

    total_tasks = len(tasks)

    completed_tasks = Task.query.filter_by(
        user_id=current_user.id,
        status="Completed"
    ).count()

    pending_tasks = Task.query.filter_by(
        user_id=current_user.id,
        status="Pending"
    ).count()

    # =========================
    # DYNAMIC TIME-BASED GREETING
    # =========================

    current_hour = datetime.now().hour

    if current_hour < 12:

        greeting = "Good morning"

    elif current_hour < 17:

        greeting = "Good afternoon"

    elif current_hour < 21:

        greeting = "Good evening"

    else:

        greeting = "Good night"

    # =========================
    # GENDER-BASED GREETING ICON
    # =========================

    if current_user.gender == "Female":

        greeting_icon = "🌷"

    else:

        greeting_icon = "👋"

    return render_template(
        "dashboard.html",
        tasks=tasks,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        productivity_score=productivity_score,
        productivity_prediction=(
            productivity_prediction
        ),
        greeting=greeting,
        greeting_icon=greeting_icon
    )


# =========================
# MY TASKS
# =========================
@auth.route("/my-tasks")
@login_required
def my_tasks():

    tasks = Task.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Task.created_at.desc()
    ).all()

    # Calculate deadline risk
    # for each task
    for task in tasks:

        task.deadline_risk = (
            calculate_deadline_risk(
                task.deadline,
                task.status
            )
        )

    return render_template(
        "my_tasks.html",
        tasks=tasks
    )


# =========================
# ADD TASK
# =========================
@auth.route(
    "/add-task",
    methods=["GET", "POST"]
)
@login_required
def add_task():

    if request.method == "POST":

        title = request.form[
            "title"
        ]

        description = request.form[
            "description"
        ]

        importance = request.form[
            "importance"
        ]

        deadline = datetime.strptime(
            request.form["deadline"],
            "%Y-%m-%dT%H:%M"
        )

        # =========================
        # GET REMINDER
        # =========================

        reminder_value = request.form.get(
            "reminder_at",
            ""
        ).strip()

        reminder_at = None

        if reminder_value:

            reminder_at = datetime.strptime(
                reminder_value,
                "%Y-%m-%dT%H:%M"
            )

            # Reminder should not be
            # after the task deadline.
            if reminder_at > deadline:

                return render_template(
                    "add_task.html",
                    error_message=(
                        "Reminder time cannot be "
                        "after the task deadline."
                    )
                )

            # Reminder should not be
            # in the past.
            if reminder_at < datetime.now():

                return render_template(
                    "add_task.html",
                    error_message=(
                        "Reminder time cannot be "
                        "in the past."
                    )
                )

        # =========================
        # AUTOMATICALLY RECOMMEND PRIORITY
        # =========================

        recommended_priority = (
            recommend_priority(
                deadline,
                importance
            )
        )

        # =========================
        # CREATE TASK
        # =========================

        new_task = Task(
            title=title,
            description=description,
            importance=importance,
            priority=recommended_priority,
            deadline=deadline,
            reminder_at=reminder_at,
            reminder_sent=False,
            user_id=current_user.id
        )

        db.session.add(new_task)

        db.session.commit()

        return redirect(
            url_for("auth.dashboard")
        )

    return render_template(
        "add_task.html"
    )


# =========================
# EDIT TASK
# =========================
@auth.route(
    "/edit-task/<int:task_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_task(task_id):

    task = Task.query.get_or_404(
        task_id
    )

    if task.user_id != current_user.id:

        return "Unauthorized", 403

    if request.method == "POST":

        task.title = request.form[
            "title"
        ]

        task.description = request.form[
            "description"
        ]

        importance = request.form[
            "importance"
        ]

        task.importance = importance

        # =========================
        # UPDATE DEADLINE
        # =========================

        deadline = datetime.strptime(
            request.form["deadline"],
            "%Y-%m-%dT%H:%M"
        )

        task.deadline = deadline

        # =========================
        # GET REMINDER
        # =========================

        reminder_value = request.form.get(
            "reminder_at",
            ""
        ).strip()

        reminder_at = None

        if reminder_value:

            reminder_at = datetime.strptime(
                reminder_value,
                "%Y-%m-%dT%H:%M"
            )

            # Reminder cannot be
            # after deadline
            if reminder_at > deadline:

                return render_template(
                    "edit_task.html",
                    task=task,
                    error_message=(
                        "Reminder time cannot be "
                        "after the task deadline."
                    )
                )

            # Reminder cannot be
            # in the past
            if reminder_at < datetime.now():

                return render_template(
                    "edit_task.html",
                    task=task,
                    error_message=(
                        "Reminder time cannot be "
                        "in the past."
                    )
                )

        # =========================
        # UPDATE REMINDER
        # =========================

        task.reminder_at = reminder_at

        # Reset reminder status whenever
        # the reminder is added or changed.
        task.reminder_sent = False

        # =========================
        # AUTOMATICALLY RECALCULATE
        # PRIORITY
        # =========================

        task.priority = recommend_priority(
            task.deadline,
            task.importance
        )

        db.session.commit()

        return redirect(
            url_for("auth.my_tasks")
        )

    return render_template(
        "edit_task.html",
        task=task
    )


# =========================
# DELETE TASK
# =========================
@auth.route(
    "/delete-task/<int:task_id>",
    methods=["POST"]
)
@login_required
def delete_task(task_id):

    task = Task.query.get_or_404(
        task_id
    )

    # Make sure the task belongs
    # to the logged-in user
    if task.user_id != current_user.id:

        return "Unauthorized", 403

    db.session.delete(task)

    db.session.commit()

    return redirect(
        url_for("auth.my_tasks")
    )


# =========================
# COMPLETE TASK
# =========================
@auth.route(
    "/complete-task/<int:task_id>",
    methods=["POST"]
)
@login_required
def complete_task(task_id):

    task = Task.query.get_or_404(
        task_id
    )

    # Make sure the task belongs
    # to the logged-in user
    if task.user_id != current_user.id:

        return "Unauthorized", 403

    task.status = "Completed"

    task.completed_at = datetime.utcnow()

    db.session.commit()

    return redirect(
        url_for("auth.my_tasks")
    )


# =========================
# DEADLINE RISK
# =========================
@auth.route("/deadline-risk")
@login_required
def deadline_risk():

    tasks = Task.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Task.deadline.asc()
    ).all()

    for task in tasks:

        task.deadline_risk = (
            calculate_deadline_risk(
                task.deadline,
                task.status
            )
        )

        task.risk_reason = (
            get_deadline_risk_reason(
                task.deadline,
                task.status
            )
        )

    high_risk_tasks = [
        task
        for task in tasks
        if task.deadline_risk == "High"
    ]

    medium_risk_tasks = [
        task
        for task in tasks
        if task.deadline_risk == "Medium"
    ]

    low_risk_tasks = [
        task
        for task in tasks
        if task.deadline_risk == "Low"
    ]

    return render_template(
        "deadline_risk.html",
        high_risk_tasks=high_risk_tasks,
        medium_risk_tasks=medium_risk_tasks,
        low_risk_tasks=low_risk_tasks,
        total_tasks=len(tasks)
    )


# =========================
# CALENDAR
# =========================
@auth.route("/calendar")
@login_required
def calendar():

    tasks = Task.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Task.deadline.asc()
    ).all()

    return render_template(
        "calendar.html",
        tasks=tasks
    )


# =========================
# PRODUCTIVITY ANALYTICS
# =========================
@auth.route("/productivity")
@login_required
def productivity():

    # =========================
    # GET ALL USER TASKS
    # =========================

    tasks = Task.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Task.created_at.asc()
    ).all()


    # =========================
    # OVERALL STATISTICS
    # =========================

    total_tasks = len(tasks)

    completed_tasks = [
        task
        for task in tasks
        if task.status == "Completed"
    ]

    completed_count = len(
        completed_tasks
    )

    pending_count = (
        total_tasks
        - completed_count
    )


    # =========================
    # OVERALL COMPLETION RATE
    # =========================

    if total_tasks > 0:

        completion_rate = round(
            (
                completed_count
                / total_tasks
            ) * 100
        )

    else:

        completion_rate = 0


    # =========================
    # OVERALL ON-TIME RATE
    # =========================

    if completed_count > 0:

        on_time_count = len([

            task

            for task in completed_tasks

            if task.completed_at
            and task.completed_at <= task.deadline

        ])

        on_time_rate = round(
            (
                on_time_count
                / completed_count
            ) * 100
        )

    else:

        on_time_rate = 0


    # =========================
    # OVERALL PENDING RATE
    # =========================

    if total_tasks > 0:

        pending_rate = round(
            (
                pending_count
                / total_tasks
            ) * 100
        )

    else:

        pending_rate = 0


    # =========================
    # MACHINE-LEARNING
    # PRODUCTIVITY CLASSIFICATION
    # =========================

    if completed_count >= 10:

        productivity_prediction = (
            predict_productivity(
                completion_rate,
                on_time_rate,
                pending_rate,
                total_tasks
            )
        )

    else:

        productivity_prediction = (
            "Not enough data"
        )


    # =========================
    # PRODUCTIVITY SCORE
    # =========================

    productivity_score = (
        calculate_productivity_score(
            tasks
        )
    )


    # =========================
    # SELECT STATISTICS PERIOD
    # =========================

    selected_period = request.args.get(
        "period",
        "weekly"
    ).lower()

    if selected_period not in [
        "weekly",
        "monthly",
        "yearly"
    ]:

        selected_period = "weekly"


    # =========================
    # CURRENT DATE AND TIME
    # =========================

    now = datetime.now()


    # =========================
    # DETERMINE PERIOD START
    # =========================

    if selected_period == "weekly":

        # Start of current week:
        # Monday at 12:00 AM

        period_start = (
            now - timedelta(
                days=now.weekday()
            )
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        period_name = "This Week"


    elif selected_period == "monthly":

        # First day of current month

        period_start = datetime(
            now.year,
            now.month,
            1
        )

        period_name = "This Month"


    else:

        # First day of current year

        period_start = datetime(
            now.year,
            1,
            1
        )

        period_name = "This Year"


    # =========================
    # FILTER TASKS FOR PERIOD
    # =========================

    period_tasks = [

        task

        for task in tasks

        if task.created_at

        and task.created_at >= period_start

        and task.created_at <= now

    ]


    # =========================
    # PERIOD TOTAL TASKS
    # =========================

    period_total = len(
        period_tasks
    )


    # =========================
    # PERIOD COMPLETED TASKS
    # =========================

    period_completed_tasks = [

        task

        for task in period_tasks

        if task.status == "Completed"

    ]

    period_completed = len(
        period_completed_tasks
    )


    # =========================
    # PERIOD PENDING TASKS
    # =========================

    period_pending = (
        period_total
        - period_completed
    )


    # =========================
    # PERIOD COMPLETION RATE
    # =========================

    if period_total > 0:

        period_completion_rate = round(
            (
                period_completed
                / period_total
            ) * 100
        )

    else:

        period_completion_rate = 0


    # =========================
    # PERIOD ON-TIME COMPLETION
    # =========================

    if period_completed > 0:

        period_on_time_count = len([

            task

            for task in period_completed_tasks

            if task.completed_at
            and task.completed_at <= task.deadline

        ])

        period_on_time_rate = round(
            (
                period_on_time_count
                / period_completed
            ) * 100
        )

    else:

        period_on_time_rate = 0


    # =========================
    # PERIOD PENDING RATE
    # =========================

    if period_total > 0:

        period_pending_rate = round(
            (
                period_pending
                / period_total
            ) * 100
        )

    else:

        period_pending_rate = 0


    # =========================
    # DISPLAY PRODUCTIVITY PAGE
    # =========================

    return render_template(

        "productivity.html",

        # Overall statistics
        total_tasks=total_tasks,

        completed_count=completed_count,

        pending_count=pending_count,

        completion_rate=completion_rate,

        on_time_rate=on_time_rate,

        pending_rate=pending_rate,

        # Productivity
        productivity_score=(
            productivity_score
        ),

        productivity_prediction=(
            productivity_prediction
        ),

        # Period statistics
        selected_period=(
            selected_period
        ),

        period_name=(
            period_name
        ),

        period_total=(
            period_total
        ),

        period_completed=(
            period_completed
        ),

        period_pending=(
            period_pending
        ),

        period_completion_rate=(
            period_completion_rate
        ),

        period_on_time_rate=(
            period_on_time_rate
        ),

        period_pending_rate=(
            period_pending_rate
        )
    )


# =========================
# SETTINGS
# =========================
@auth.route(
    "/settings",
    methods=["GET", "POST"]
)
@login_required
def settings():

    if request.method == "POST":

        old_username = (
            current_user.username
        )

        # =========================
        # GET USERNAME
        # =========================

        username = request.form.get(
            "username",
            ""
        ).strip()

        # =========================
        # VALIDATION
        # =========================

        if not username:

            return render_template(
                "settings.html",
                error_message=(
                    "Username cannot be empty."
                )
            )

        # =========================
        # CHECK USERNAME
        # =========================

        existing_username = User.query.filter(
            User.username == username,
            User.id != current_user.id
        ).first()

        if existing_username:

            return render_template(
                "settings.html",
                error_message=(
                    "That username is already taken."
                )
            )

        # =========================
        # UPDATE USERNAME
        # =========================

        current_user.username = username

        db.session.commit()

        # =========================
        # SUCCESS MESSAGE
        # =========================

        if old_username != username:

            message = (
                "Username changed successfully."
            )

        else:

            message = (
                "No changes were made."
            )

        return render_template(
            "settings.html",
            success_message=message
        )

    # =========================
    # GET SETTINGS PAGE
    # =========================

    return render_template(
        "settings.html"
    )


# =========================
# UPDATE PREFERENCES
# =========================
@auth.route(
    "/update-preferences",
    methods=["POST"]
)
@login_required
def update_preferences():

    # =========================
    # EMAIL NOTIFICATIONS
    # =========================

    current_user.email_notifications = (
        request.form.get(
            "email_notifications"
        ) == "on"
    )

    # =========================
    # TASK REMINDERS
    # =========================

    current_user.task_reminders = (
        request.form.get(
            "task_reminders"
        ) == "on"
    )

    db.session.commit()

    return render_template(
        "settings.html",
        success_message=(
            "Preferences updated successfully."
        )
    )


# =========================
# CHANGE PASSWORD
# =========================
@auth.route(
    "/change-password",
    methods=["POST"]
)
@login_required
def change_password():

    current_password = request.form.get(
        "current_password",
        ""
    )

    new_password = request.form.get(
        "new_password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )

    # =========================
    # CHECK CURRENT PASSWORD
    # =========================

    if not check_password_hash(
        current_user.password,
        current_password
    ):

        return render_template(
            "settings.html",
            error_message=(
                "Current password is incorrect."
            )
        )

    # =========================
    # CHECK NEW PASSWORD
    # =========================

    if not new_password:

        return render_template(
            "settings.html",
            error_message=(
                "New password cannot be empty."
            )
        )

    # =========================
    # PASSWORD LENGTH
    # =========================

    if len(new_password) < 8:

        return render_template(
            "settings.html",
            error_message=(
                "New password must be at least "
                "8 characters long."
            )
        )

    # =========================
    # CONFIRM PASSWORD
    # =========================

    if new_password != confirm_password:

        return render_template(
            "settings.html",
            error_message=(
                "New passwords do not match."
            )
        )

    # =========================
    # PREVENT SAME PASSWORD
    # =========================

    if check_password_hash(
        current_user.password,
        new_password
    ):

        return render_template(
            "settings.html",
            error_message=(
                "Your new password must be "
                "different from your current password."
            )
        )

    # =========================
    # HASH NEW PASSWORD
    # =========================

    current_user.password = (
        generate_password_hash(
            new_password
        )
    )

    db.session.commit()

    # =========================
    # SUCCESS MESSAGE
    # =========================

    return render_template(
        "settings.html",
        success_message=(
            "Password changed successfully."
        )
    )


# =========================
# PROFILE PHOTO
# =========================
@auth.route(
    "/profile-photo",
    methods=["POST"]
)
@login_required
def profile_photo():

    uploaded_file = request.files.get(
        "profile_photo"
    )

    # =========================
    # CHECK FILE
    # =========================

    if not uploaded_file:

        return render_template(
            "settings.html",
            error_message=(
                "Please select a profile photo."
            )
        )

    if not uploaded_file.filename:

        return render_template(
            "settings.html",
            error_message=(
                "Please select a profile photo."
            )
        )

    # =========================
    # CHECK FILE EXTENSION
    # =========================

    allowed_extensions = {
        "jpg",
        "jpeg",
        "png",
        "webp",
        "gif"
    }

    if "." not in uploaded_file.filename:

        return render_template(
            "settings.html",
            error_message=(
                "Invalid image format. "
                "Use JPG, JPEG, PNG, WEBP or GIF."
            )
        )

    extension = (
        uploaded_file.filename
        .rsplit(".", 1)[1]
        .lower()
    )

    if extension not in allowed_extensions:

        return render_template(
            "settings.html",
            error_message=(
                "Invalid image format. "
                "Use JPG, JPEG, PNG, WEBP or GIF."
            )
        )

    # =========================
    # CHECK FILE SIZE
    # =========================

    uploaded_file.seek(
        0,
        2
    )

    file_size = uploaded_file.tell()

    uploaded_file.seek(0)

    # Maximum 2 MB
    if file_size > 2 * 1024 * 1024:

        return render_template(
            "settings.html",
            error_message=(
                "Profile photo must be 2 MB or smaller."
            )
        )

    # =========================
    # CREATE UPLOAD FOLDER
    # =========================

    upload_folder = (
        current_app.config.get(
            "PROFILE_PHOTO_FOLDER"
        )
    )

    if not upload_folder:

        import os

        upload_folder = os.path.join(
            current_app.static_folder,
            "uploads",
            "profile_photos"
        )

    import os

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    # =========================
    # CREATE UNIQUE FILE NAME
    # =========================

    filename = (
        f"user_{current_user.id}"
        f"_profile.{extension}"
    )

    file_path = os.path.join(
        upload_folder,
        filename
    )

    # =========================
    # DELETE OLD PHOTO
    # =========================

    if current_user.profile_photo:

        old_photo_path = os.path.join(
            upload_folder,
            current_user.profile_photo
        )

        if (
            os.path.exists(old_photo_path)
            and old_photo_path != file_path
        ):

            os.remove(
                old_photo_path
            )

    # =========================
    # SAVE NEW PHOTO
    # =========================

    uploaded_file.save(
        file_path
    )

    # =========================
    # SAVE FILE NAME
    # =========================

    current_user.profile_photo = (
        filename
    )

    db.session.commit()

    # =========================
    # SUCCESS MESSAGE
    # =========================

    return render_template(
        "settings.html",
        success_message=(
            "Profile photo updated successfully."
        )
    )


# =========================
# CHECK REMINDERS
# =========================
@auth.route("/check-reminders")
@login_required
def check_reminders():

    now = datetime.now()

    due_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.reminder_at.isnot(None),
        Task.reminder_at <= now,
        Task.reminder_sent == False,
        Task.status != "Completed"
    ).all()

    notifications = []

    for task in due_tasks:

        notifications.append({
            "title": task.title,
            "message": (
                f"Reminder: You planned to work on "
                f"'{task.title}'."
            )
        })

        # IMPORTANT:
        # Do NOT set reminder_sent = True here.
        #
        # reminder_sent is reserved for automatic
        # email reminders.
        #
        # APScheduler sets it to True only after
        # the email is successfully sent.

    # This route only displays
    # due in-app notifications.

    return jsonify({
        "notifications": notifications
    })
