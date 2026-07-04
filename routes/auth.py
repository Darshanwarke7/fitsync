from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

from utils.db import query_one, execute
from utils.auth_utils import login_user_session, logout_user_session, current_user

bp = Blueprint("auth", __name__)


@bp.route("/")
def index():
    if current_user():
        return redirect(url_for("auth.dashboard_redirect"))
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = query_one(
            """SELECT u.*, r.role_name FROM users u
               JOIN roles r ON u.role_id = r.role_id
               WHERE u.email = %s""",
            (email,),
        )

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        if not user["is_active"]:
            flash("Your account has been deactivated. Contact admin.", "danger")
            return render_template("auth/login.html")

        login_user_session(user)
        flash(f"Welcome back, {user['full_name']}!", "success")
        return redirect(url_for("auth.dashboard_redirect"))

    return render_template("auth/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Self-registration for new Members. Plan & trainer are assigned later by an Admin."""
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        gender = request.form.get("gender") or None
        goal = request.form.get("goal") or "General Fitness"

        if not (full_name and email and password):
            flash("Please fill all required fields.", "danger")
            return render_template("auth/register.html")

        existing = query_one("SELECT user_id FROM users WHERE email = %s", (email,))
        if existing:
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html")

        member_role = query_one("SELECT role_id FROM roles WHERE role_name = 'member'")
        pw_hash = generate_password_hash(password)

        user_id = execute(
            """INSERT INTO users (role_id, full_name, email, phone, password_hash)
               VALUES (%s, %s, %s, %s, %s)""",
            (member_role["role_id"], full_name, email, phone, pw_hash),
            return_id=True,
        )

        execute(
            """INSERT INTO members (user_id, gender, goal, status)
               VALUES (%s, %s, %s, 'active')""",
            (user_id, gender, goal),
        )

        flash("Registration successful! Please log in. Your plan will be assigned by the gym admin.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@bp.route("/logout")
def logout():
    logout_user_session()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/dashboard")
def dashboard_redirect():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if user["role"] == "admin":
        return redirect(url_for("admin.dashboard"))
    elif user["role"] == "trainer":
        return redirect(url_for("trainer.dashboard"))
    else:
        return redirect(url_for("member.dashboard"))
