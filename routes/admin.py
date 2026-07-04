from datetime import date, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash

from utils.db import query_all, query_one, execute
from utils.auth_utils import roles_required
from utils.calculations import generate_invoice_no

bp = Blueprint("admin", __name__, url_prefix="/admin")


# ------------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------------
@bp.route("/dashboard")
@roles_required("admin")
def dashboard():
    total_members = query_one("SELECT COUNT(*) c FROM members")["c"]
    active_members = query_one("SELECT COUNT(*) c FROM members WHERE status='active'")["c"]
    total_trainers = query_one("SELECT COUNT(*) c FROM trainers")["c"]

    revenue = query_one("SELECT COALESCE(SUM(paid_amount),0) r FROM payments")["r"]
    outstanding = query_one("SELECT COALESCE(SUM(outstanding_amount),0) o FROM payments WHERE status IN ('unpaid','partial','overdue')")["o"]

    today_attendance = query_one(
        "SELECT COUNT(*) c FROM attendance WHERE attendance_date = %s", (date.today(),)
    )["c"]

    outstanding_list = query_all(
        """SELECT p.payment_id, u.full_name, p.outstanding_amount, p.due_date, p.status
           FROM payments p
           JOIN members m ON p.member_id = m.member_id
           JOIN users u ON m.user_id = u.user_id
           WHERE p.outstanding_amount > 0
           ORDER BY p.due_date ASC LIMIT 10"""
    )

    recent_members = query_all(
        """SELECT m.member_id, u.full_name, u.email, m.join_date, m.status
           FROM members m JOIN users u ON m.user_id = u.user_id
           ORDER BY m.join_date DESC LIMIT 8"""
    )

    week_ago = date.today() - timedelta(days=6)
    attendance_trend = query_all(
        """SELECT attendance_date, COUNT(*) c FROM attendance
           WHERE attendance_date >= %s GROUP BY attendance_date ORDER BY attendance_date""",
        (week_ago,),
    )

    return render_template(
        "admin/dashboard.html",
        total_members=total_members,
        active_members=active_members,
        total_trainers=total_trainers,
        revenue=revenue,
        outstanding=outstanding,
        today_attendance=today_attendance,
        outstanding_list=outstanding_list,
        recent_members=recent_members,
        attendance_trend=attendance_trend,
    )


# ------------------------------------------------------------------
# MEMBER MANAGEMENT
# ------------------------------------------------------------------
@bp.route("/members")
@roles_required("admin")
def members():
    search = request.args.get("q", "").strip()
    if search:
        rows = query_all(
            """SELECT m.*, u.full_name, u.email, u.phone, t.trainer_id AS t_id,
                      tu.full_name AS trainer_name, mp.plan_name
               FROM members m
               JOIN users u ON m.user_id = u.user_id
               LEFT JOIN trainers t ON m.trainer_id = t.trainer_id
               LEFT JOIN users tu ON t.user_id = tu.user_id
               LEFT JOIN membership_plans mp ON m.plan_id = mp.plan_id
               WHERE u.full_name LIKE %s OR u.email LIKE %s
               ORDER BY m.member_id DESC""",
            (f"%{search}%", f"%{search}%"),
        )
    else:
        rows = query_all(
            """SELECT m.*, u.full_name, u.email, u.phone, t.trainer_id AS t_id,
                      tu.full_name AS trainer_name, mp.plan_name
               FROM members m
               JOIN users u ON m.user_id = u.user_id
               LEFT JOIN trainers t ON m.trainer_id = t.trainer_id
               LEFT JOIN users tu ON t.user_id = tu.user_id
               LEFT JOIN membership_plans mp ON m.plan_id = mp.plan_id
               ORDER BY m.member_id DESC"""
        )

    trainers = query_all(
        "SELECT t.trainer_id, u.full_name FROM trainers t JOIN users u ON t.user_id=u.user_id"
    )
    plans = query_all("SELECT * FROM membership_plans WHERE is_active = 1")

    return render_template("admin/members.html", members=rows, trainers=trainers, plans=plans, search=search)


@bp.route("/members/add", methods=["POST"])
@roles_required("admin")
def add_member():
    full_name = request.form.get("full_name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password") or "member123"
    gender = request.form.get("gender") or None
    goal = request.form.get("goal") or "General Fitness"
    plan_id = request.form.get("plan_id") or None
    trainer_id = request.form.get("trainer_id") or None
    height_cm = request.form.get("height_cm") or None

    if query_one("SELECT user_id FROM users WHERE email=%s", (email,)):
        flash("Email already registered.", "danger")
        return redirect(url_for("admin.members"))

    role = query_one("SELECT role_id FROM roles WHERE role_name='member'")
    user_id = execute(
        "INSERT INTO users (role_id, full_name, email, phone, password_hash) VALUES (%s,%s,%s,%s,%s)",
        (role["role_id"], full_name, email, phone, generate_password_hash(password)),
        return_id=True,
    )

    m_start = date.today()
    m_end = None
    if plan_id:
        plan = query_one("SELECT duration_months FROM membership_plans WHERE plan_id=%s", (plan_id,))
        if plan:
            m_end = m_start + timedelta(days=30 * plan["duration_months"])

    member_id = execute(
        """INSERT INTO members (user_id, trainer_id, plan_id, gender, goal, height_cm,
                                 membership_start, membership_end, status)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'active')""",
        (user_id, trainer_id or None, plan_id or None, gender, goal, height_cm, m_start, m_end),
        return_id=True,
    )

    if plan_id:
        plan = query_one("SELECT amount FROM membership_plans WHERE plan_id=%s", (plan_id,))
        if plan:
            execute(
                """INSERT INTO payments (member_id, plan_id, total_amount, paid_amount, due_date, status, invoice_no)
                   VALUES (%s,%s,%s,0,%s,'unpaid',%s)""",
                (member_id, plan_id, plan["amount"], m_start + timedelta(days=7), generate_invoice_no()),
            )

    flash("Member added successfully.", "success")
    return redirect(url_for("admin.members"))


@bp.route("/members/<int:member_id>/edit", methods=["POST"])
@roles_required("admin")
def edit_member(member_id):
    full_name = request.form.get("full_name")
    phone = request.form.get("phone")
    trainer_id = request.form.get("trainer_id") or None
    plan_id = request.form.get("plan_id") or None
    status = request.form.get("status")
    goal = request.form.get("goal")

    member = query_one("SELECT user_id FROM members WHERE member_id=%s", (member_id,))
    if not member:
        flash("Member not found.", "danger")
        return redirect(url_for("admin.members"))

    execute("UPDATE users SET full_name=%s, phone=%s WHERE user_id=%s", (full_name, phone, member["user_id"]))
    execute(
        "UPDATE members SET trainer_id=%s, plan_id=%s, status=%s, goal=%s WHERE member_id=%s",
        (trainer_id, plan_id, status, goal, member_id),
    )
    flash("Member updated.", "success")
    return redirect(url_for("admin.members"))


@bp.route("/members/<int:member_id>/delete", methods=["POST"])
@roles_required("admin")
def delete_member(member_id):
    member = query_one("SELECT user_id FROM members WHERE member_id=%s", (member_id,))
    if member:
        execute("DELETE FROM users WHERE user_id=%s", (member["user_id"],))
        flash("Member deleted.", "info")
    return redirect(url_for("admin.members"))


# ------------------------------------------------------------------
# TRAINER MANAGEMENT
# ------------------------------------------------------------------
@bp.route("/trainers")
@roles_required("admin")
def trainers():
    rows = query_all(
        """SELECT t.*, u.full_name, u.email, u.phone,
                  (SELECT COUNT(*) FROM members m WHERE m.trainer_id = t.trainer_id) AS member_count
           FROM trainers t JOIN users u ON t.user_id = u.user_id
           ORDER BY t.trainer_id DESC"""
    )
    return render_template("admin/trainers.html", trainers=rows)


@bp.route("/trainers/add", methods=["POST"])
@roles_required("admin")
def add_trainer():
    full_name = request.form.get("full_name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password") or "trainer123"
    specialization = request.form.get("specialization")
    experience_years = request.form.get("experience_years") or 0
    salary = request.form.get("salary") or 0

    if query_one("SELECT user_id FROM users WHERE email=%s", (email,)):
        flash("Email already registered.", "danger")
        return redirect(url_for("admin.trainers"))

    role = query_one("SELECT role_id FROM roles WHERE role_name='trainer'")
    user_id = execute(
        "INSERT INTO users (role_id, full_name, email, phone, password_hash) VALUES (%s,%s,%s,%s,%s)",
        (role["role_id"], full_name, email, phone, generate_password_hash(password)),
        return_id=True,
    )
    execute(
        "INSERT INTO trainers (user_id, specialization, experience_years, salary) VALUES (%s,%s,%s,%s)",
        (user_id, specialization, experience_years, salary),
    )
    flash("Trainer added successfully.", "success")
    return redirect(url_for("admin.trainers"))


@bp.route("/trainers/<int:trainer_id>/delete", methods=["POST"])
@roles_required("admin")
def delete_trainer(trainer_id):
    trainer = query_one("SELECT user_id FROM trainers WHERE trainer_id=%s", (trainer_id,))
    if trainer:
        execute("DELETE FROM users WHERE user_id=%s", (trainer["user_id"],))
        flash("Trainer removed.", "info")
    return redirect(url_for("admin.trainers"))


# ------------------------------------------------------------------
# MEMBERSHIP PLANS
# ------------------------------------------------------------------
@bp.route("/plans")
@roles_required("admin")
def plans():
    rows = query_all("SELECT * FROM membership_plans ORDER BY plan_id")
    return render_template("admin/plans.html", plans=rows)


@bp.route("/plans/add", methods=["POST"])
@roles_required("admin")
def add_plan():
    execute(
        """INSERT INTO membership_plans (plan_name, description, duration_months, amount)
           VALUES (%s,%s,%s,%s)""",
        (request.form.get("plan_name"), request.form.get("description"),
         request.form.get("duration_months"), request.form.get("amount")),
    )
    flash("Plan created.", "success")
    return redirect(url_for("admin.plans"))


@bp.route("/plans/<int:plan_id>/toggle", methods=["POST"])
@roles_required("admin")
def toggle_plan(plan_id):
    plan = query_one("SELECT is_active FROM membership_plans WHERE plan_id=%s", (plan_id,))
    if plan:
        execute("UPDATE membership_plans SET is_active=%s WHERE plan_id=%s", (0 if plan["is_active"] else 1, plan_id))
    return redirect(url_for("admin.plans"))


# ------------------------------------------------------------------
# FEES / PAYMENTS
# ------------------------------------------------------------------
@bp.route("/payments")
@roles_required("admin")
def payments():
    rows = query_all(
        """SELECT p.*, u.full_name, u.email FROM payments p
           JOIN members m ON p.member_id = m.member_id
           JOIN users u ON m.user_id = u.user_id
           ORDER BY p.created_at DESC"""
    )
    members = query_all(
        "SELECT m.member_id, u.full_name FROM members m JOIN users u ON m.user_id=u.user_id"
    )
    return render_template("admin/payments.html", payments=rows, members=members)


@bp.route("/payments/add", methods=["POST"])
@roles_required("admin")
def add_payment():
    member_id = request.form.get("member_id")
    total_amount = request.form.get("total_amount")
    paid_amount = request.form.get("paid_amount") or 0
    due_date = request.form.get("due_date")
    method = request.form.get("payment_method") or "cash"

    status = "unpaid"
    if float(paid_amount) >= float(total_amount):
        status = "paid"
    elif float(paid_amount) > 0:
        status = "partial"

    execute(
        """INSERT INTO payments (member_id, total_amount, paid_amount, due_date, payment_date,
                                  payment_method, status, invoice_no)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (member_id, total_amount, paid_amount, due_date,
         date.today() if float(paid_amount) > 0 else None,
         method, status, generate_invoice_no()),
    )
    flash("Payment record added.", "success")
    return redirect(url_for("admin.payments"))


@bp.route("/payments/<int:payment_id>/record", methods=["POST"])
@roles_required("admin")
def record_payment(payment_id):
    amount = float(request.form.get("amount") or 0)
    payment = query_one("SELECT * FROM payments WHERE payment_id=%s", (payment_id,))
    if payment:
        new_paid = float(payment["paid_amount"]) + amount
        status = "paid" if new_paid >= float(payment["total_amount"]) else "partial"
        execute(
            "UPDATE payments SET paid_amount=%s, status=%s, payment_date=%s WHERE payment_id=%s",
            (new_paid, status, date.today(), payment_id),
        )
        flash("Payment recorded.", "success")
    return redirect(url_for("admin.payments"))


# ------------------------------------------------------------------
# ATTENDANCE
# ------------------------------------------------------------------
@bp.route("/attendance")
@roles_required("admin")
def attendance():
    today = date.today()
    rows = query_all(
        """SELECT a.*, u.full_name FROM attendance a
           JOIN members m ON a.member_id = m.member_id
           JOIN users u ON m.user_id = u.user_id
           WHERE a.attendance_date = %s ORDER BY a.check_in DESC""",
        (today,),
    )
    members = query_all("SELECT m.member_id, u.full_name FROM members m JOIN users u ON m.user_id=u.user_id WHERE m.status='active'")
    return render_template("admin/attendance.html", records=rows, members=members, today=today)


@bp.route("/attendance/checkin", methods=["POST"])
@roles_required("admin")
def checkin():
    member_id = request.form.get("member_id")
    from datetime import datetime
    now = datetime.now()
    existing = query_one(
        "SELECT * FROM attendance WHERE member_id=%s AND attendance_date=%s", (member_id, now.date())
    )
    if existing:
        flash("Member already checked in today.", "warning")
    else:
        execute(
            "INSERT INTO attendance (member_id, check_in, attendance_date) VALUES (%s,%s,%s)",
            (member_id, now, now.date()),
        )
        flash("Checked in.", "success")
    return redirect(url_for("admin.attendance"))


@bp.route("/attendance/<int:attendance_id>/checkout", methods=["POST"])
@roles_required("admin")
def checkout(attendance_id):
    from datetime import datetime
    execute("UPDATE attendance SET check_out=%s WHERE attendance_id=%s", (datetime.now(), attendance_id))
    flash("Checked out.", "success")
    return redirect(url_for("admin.attendance"))


# ------------------------------------------------------------------
# NOTIFICATIONS
# ------------------------------------------------------------------
@bp.route("/notifications")
@roles_required("admin")
def notifications():
    rows = query_all(
        """SELECT n.*, u.full_name FROM notifications n JOIN users u ON n.user_id=u.user_id
           ORDER BY n.created_at DESC LIMIT 100"""
    )
    members = query_all("SELECT m.member_id, u.user_id, u.full_name FROM members m JOIN users u ON m.user_id=u.user_id")
    return render_template("admin/notifications.html", notifications=rows, members=members)


@bp.route("/notifications/send", methods=["POST"])
@roles_required("admin")
def send_notification():
    user_id = request.form.get("user_id")
    title = request.form.get("title")
    message = request.form.get("message")
    ntype = request.form.get("type") or "info"

    from utils.email_utils import send_email, notification_email_html, is_email_configured

    email_sent_count = 0

    if user_id == "all_members":
        member_users = query_all(
            """SELECT u.user_id, u.full_name, u.email FROM users u
               JOIN roles r ON u.role_id=r.role_id WHERE r.role_name='member'"""
        )
        for row in member_users:
            execute(
                "INSERT INTO notifications (user_id, title, message, type) VALUES (%s,%s,%s,%s)",
                (row["user_id"], title, message, ntype),
            )
            if send_email(row["email"], title, notification_email_html(title, message, row["full_name"])):
                email_sent_count += 1
    else:
        row = query_one("SELECT user_id, full_name, email FROM users WHERE user_id=%s", (user_id,))
        execute(
            "INSERT INTO notifications (user_id, title, message, type) VALUES (%s,%s,%s,%s)",
            (user_id, title, message, ntype),
        )
        if row and send_email(row["email"], title, notification_email_html(title, message, row["full_name"])):
            email_sent_count += 1

    if is_email_configured():
        flash(f"Notification sent. Email delivered to {email_sent_count} recipient(s).", "success")
    else:
        flash("Notification saved in-app. Email is not configured yet (set MAIL_USERNAME/MAIL_PASSWORD in .env to enable real emails).", "warning")

    return redirect(url_for("admin.notifications"))


# ------------------------------------------------------------------
# SETTINGS / ADMIN MANAGEMENT
# ------------------------------------------------------------------
@bp.route("/settings")
@roles_required("admin")
def settings():
    admins = query_all(
        """SELECT u.user_id, u.full_name, u.email, u.phone, u.created_at
           FROM users u JOIN roles r ON u.role_id = r.role_id
           WHERE r.role_name = 'admin' ORDER BY u.user_id"""
    )
    return render_template("admin/settings.html", admins=admins)


@bp.route("/settings/add-admin", methods=["POST"])
@roles_required("admin")
def add_admin():
    full_name = request.form.get("full_name")
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone")
    password = request.form.get("password")

    if not (full_name and email and password):
        flash("Please fill all required fields.", "danger")
        return redirect(url_for("admin.settings"))

    if query_one("SELECT user_id FROM users WHERE email=%s", (email,)):
        flash("Email already registered.", "danger")
        return redirect(url_for("admin.settings"))

    role = query_one("SELECT role_id FROM roles WHERE role_name='admin'")
    execute(
        "INSERT INTO users (role_id, full_name, email, phone, password_hash) VALUES (%s,%s,%s,%s,%s)",
        (role["role_id"], full_name, email, phone, generate_password_hash(password)),
    )
    flash("New admin account created.", "success")
    return redirect(url_for("admin.settings"))
