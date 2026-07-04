"""
Authentication utilities: password hashing, JWT issue/verify, and
role-based route decorators. Uses Flask session as the primary auth
mechanism (simple + reliable for a server-rendered app) while also
issuing a JWT that is available for any pure-API / mobile consumers.
"""
from functools import wraps
from datetime import datetime, timedelta, timezone

import jwt
from flask import session, redirect, url_for, request, jsonify, current_app, flash


def generate_token(user):
    payload = {
        "user_id": user["user_id"],
        "role": user["role_name"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=current_app.config["JWT_EXP_HOURS"]),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def decode_token(token):
    try:
        return jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def login_user_session(user):
    session["user_id"] = user["user_id"]
    session["role"] = user["role_name"]
    session["full_name"] = user["full_name"]
    session["token"] = generate_token(user)


def logout_user_session():
    session.clear()


def current_user():
    if "user_id" not in session:
        return None
    return {
        "user_id": session.get("user_id"),
        "role": session.get("role"),
        "full_name": session.get("full_name"),
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("auth.login"))
            if session.get("role") not in roles:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Forbidden"}), 403
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("auth.dashboard_redirect"))
            return view(*args, **kwargs)
        return wrapped
    return decorator
