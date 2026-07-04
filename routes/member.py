from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session

from utils.db import query_all, query_one, execute
from utils.auth_utils import roles_required
from ai.ai_engine import predict_progress, detect_plateau

bp = Blueprint("member", __name__, url_prefix="/member")


def _get_member():
    return query_one(
        """SELECT m.*, u.full_name, u.email FROM members m
           JOIN users u ON m.user_id = u.user_id WHERE m.user_id=%s""",
        (session["user_id"],),
    )


@bp.route("/dashboard")
@roles_required("member")
def dashboard():
    member = _get_member()
    plan = query_one("SELECT * FROM membership_plans WHERE plan_id=%s", (member["plan_id"],)) if member["plan_id"] else None
    trainer = query_one(
        "SELECT u.full_name, u.phone FROM trainers t JOIN users u ON t.user_id=u.user_id WHERE t.trainer_id=%s",
        (member["trainer_id"],),
    ) if member["trainer_id"] else None

    outstanding = query_one(
        "SELECT COALESCE(SUM(outstanding_amount),0) o FROM payments WHERE member_id=%s", (member["member_id"],)
    )["o"]

    attendance_count = query_one(
        """SELECT COUNT(*) c FROM attendance WHERE member_id=%s
           AND MONTH(attendance_date)=MONTH(CURDATE()) AND YEAR(attendance_date)=YEAR(CURDATE())""",
        (member["member_id"],),
    )["c"]

    latest_measurement = query_one(
        "SELECT * FROM body_measurements WHERE member_id=%s ORDER BY record_date DESC LIMIT 1",
        (member["member_id"],),
    )

    recent_sessions = query_all(
        "SELECT * FROM workout_sessions WHERE member_id=%s ORDER BY session_date DESC LIMIT 5",
        (member["member_id"],),
    )

    unread_notifications = query_all(
        "SELECT * FROM notifications WHERE user_id=%s AND is_read=0 ORDER BY created_at DESC LIMIT 5",
        (session["user_id"],),
    )

    return render_template(
        "member/dashboard.html", member=member, plan=plan, trainer=trainer,
        outstanding=outstanding, attendance_count=attendance_count,
        latest_measurement=latest_measurement, recent_sessions=recent_sessions,
        unread_notifications=unread_notifications,
    )


@bp.route("/workout")
@roles_required("member")
def workout():
    member = _get_member()
    sessions = query_all(
        "SELECT * FROM workout_sessions WHERE member_id=%s ORDER BY session_date DESC", (member["member_id"],)
    )
    logs_by_session = {}
    for s in sessions:
        logs_by_session[s["session_id"]] = query_all(
            "SELECT * FROM workout_logs WHERE session_id=%s", (s["session_id"],)
        )
    return render_template("member/workout.html", sessions=sessions, logs_by_session=logs_by_session)


@bp.route("/diet")
@roles_required("member")
def diet():
    member = _get_member()
    plans = query_all(
        "SELECT * FROM diet_plans WHERE member_id=%s ORDER BY created_at DESC", (member["member_id"],)
    )
    return render_template("member/diet.html", plans=plans)


@bp.route("/attendance")
@roles_required("member")
def attendance():
    member = _get_member()
    records = query_all(
        "SELECT * FROM attendance WHERE member_id=%s ORDER BY attendance_date DESC", (member["member_id"],)
    )
    return render_template("member/attendance.html", records=records)


@bp.route("/attendance/checkin", methods=["POST"])
@roles_required("member")
def self_checkin():
    member = _get_member()
    now = datetime.now()
    existing = query_one(
        "SELECT * FROM attendance WHERE member_id=%s AND attendance_date=%s", (member["member_id"], now.date())
    )
    if existing:
        flash("You already checked in today.", "warning")
    else:
        execute(
            "INSERT INTO attendance (member_id, check_in, attendance_date) VALUES (%s,%s,%s)",
            (member["member_id"], now, now.date()),
        )
        flash("Checked in successfully!", "success")
    return redirect(url_for("member.attendance"))


@bp.route("/progress")
@roles_required("member")
def progress():
    member = _get_member()
    measurements = query_all(
        "SELECT * FROM body_measurements WHERE member_id=%s ORDER BY record_date", (member["member_id"],)
    )
    prediction = None
    plateau = None
    if len(measurements) >= 3:
        prediction = predict_progress(measurements, metric="weight_kg", weeks_ahead=4)
    if len(measurements) >= 4:
        plateau = detect_plateau(measurements)

    return render_template("member/progress.html", measurements=measurements, prediction=prediction, plateau=plateau)


@bp.route("/payments")
@roles_required("member")
def payments():
    member = _get_member()
    rows = query_all(
        "SELECT * FROM payments WHERE member_id=%s ORDER BY created_at DESC", (member["member_id"],)
    )
    return render_template("member/payments.html", payments=rows)


@bp.route("/notifications/mark-read/<int:notification_id>", methods=["POST"])
@roles_required("member")
def mark_read(notification_id):
    execute("UPDATE notifications SET is_read=1 WHERE notification_id=%s AND user_id=%s", (notification_id, session["user_id"]))
    return jsonify({"status": "ok"})
