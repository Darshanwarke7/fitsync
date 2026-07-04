from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session

from utils.db import query_all, query_one, execute
from utils.auth_utils import roles_required
from utils.calculations import calculate_bmi, calories_for_exercise
from ai.ai_engine import generate_workout_plan, generate_diet_plan, suggest_progressive_overload, detect_plateau

bp = Blueprint("trainer", __name__, url_prefix="/trainer")


def _get_trainer_id():
    row = query_one("SELECT trainer_id FROM trainers WHERE user_id=%s", (session["user_id"],))
    return row["trainer_id"] if row else None


@bp.route("/dashboard")
@roles_required("trainer")
def dashboard():
    trainer_id = _get_trainer_id()
    members = query_all(
        """SELECT m.member_id, u.full_name, u.email, m.goal, m.status
           FROM members m JOIN users u ON m.user_id = u.user_id
           WHERE m.trainer_id = %s ORDER BY u.full_name""",
        (trainer_id,),
    )
    today_sessions = query_all(
        """SELECT ws.*, u.full_name FROM workout_sessions ws
           JOIN members m ON ws.member_id = m.member_id
           JOIN users u ON m.user_id = u.user_id
           WHERE ws.trainer_id=%s AND ws.session_date = %s""",
        (trainer_id, date.today()),
    )
    return render_template("trainer/dashboard.html", members=members, today_sessions=today_sessions, member_count=len(members))


@bp.route("/members")
@roles_required("trainer")
def members():
    trainer_id = _get_trainer_id()
    rows = query_all(
        """SELECT m.*, u.full_name, u.email, u.phone FROM members m
           JOIN users u ON m.user_id = u.user_id WHERE m.trainer_id = %s ORDER BY u.full_name""",
        (trainer_id,),
    )
    return render_template("trainer/members.html", members=rows)


@bp.route("/members/<int:member_id>")
@roles_required("trainer")
def member_detail(member_id):
    member = query_one(
        """SELECT m.*, u.full_name, u.email, u.phone FROM members m
           JOIN users u ON m.user_id = u.user_id WHERE m.member_id=%s""",
        (member_id,),
    )
    measurements = query_all(
        "SELECT * FROM body_measurements WHERE member_id=%s ORDER BY record_date", (member_id,)
    )
    sessions = query_all(
        "SELECT * FROM workout_sessions WHERE member_id=%s ORDER BY session_date DESC LIMIT 10", (member_id,)
    )
    diet_plans = query_all("SELECT * FROM diet_plans WHERE member_id=%s ORDER BY created_at DESC", (member_id,))

    plateau = None
    if len(measurements) >= 4:
        plateau = detect_plateau(measurements)

    return render_template(
        "trainer/member_detail.html",
        member=member, measurements=measurements, sessions=sessions,
        diet_plans=diet_plans, plateau=plateau,
    )


# ------------------------------------------------------------------
# WORKOUT SESSIONS / LOGS
# ------------------------------------------------------------------
@bp.route("/workout/record", methods=["GET", "POST"])
@roles_required("trainer")
def record_workout():
    trainer_id = _get_trainer_id()
    members = query_all(
        """SELECT m.member_id, u.full_name FROM members m JOIN users u ON m.user_id=u.user_id
           WHERE m.trainer_id=%s""",
        (trainer_id,),
    )

    if request.method == "POST":
        member_id = request.form.get("member_id")
        session_date = request.form.get("session_date") or date.today()
        title = request.form.get("title") or "Workout Session"
        notes = request.form.get("trainer_notes")

        member = query_one("SELECT * FROM members WHERE member_id=%s", (member_id,))
        latest_weight = query_one(
            "SELECT weight_kg FROM body_measurements WHERE member_id=%s ORDER BY record_date DESC LIMIT 1",
            (member_id,),
        )
        weight_kg = latest_weight["weight_kg"] if latest_weight else 70

        session_id = execute(
            """INSERT INTO workout_sessions (member_id, trainer_id, session_date, title, trainer_notes)
               VALUES (%s,%s,%s,%s,%s)""",
            (member_id, trainer_id, session_date, title, notes),
            return_id=True,
        )

        muscle_groups = request.form.getlist("muscle_group[]")
        exercise_names = request.form.getlist("exercise_name[]")
        sets_list = request.form.getlist("sets[]")
        reps_list = request.form.getlist("reps[]")
        weight_list = request.form.getlist("weight_kg[]")
        duration_list = request.form.getlist("duration_min[]")

        total_calories = 0
        total_duration = 0
        for i in range(len(exercise_names)):
            if not exercise_names[i]:
                continue
            duration = int(duration_list[i] or 0)
            calories = calories_for_exercise(muscle_groups[i], weight_kg, duration)
            total_calories += calories
            total_duration += duration
            execute(
                """INSERT INTO workout_logs (session_id, muscle_group, exercise_name, sets, reps,
                                              weight_kg, duration_min, calories_burned, trainer_notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (session_id, muscle_groups[i], exercise_names[i], sets_list[i] or 0, reps_list[i] or 0,
                 weight_list[i] or 0, duration, calories, notes),
            )

        execute(
            "UPDATE workout_sessions SET total_duration_min=%s, total_calories=%s WHERE session_id=%s",
            (total_duration, total_calories, session_id),
        )

        flash("Workout session recorded.", "success")
        return redirect(url_for("trainer.member_detail", member_id=member_id))

    return render_template("trainer/record_workout.html", members=members)


@bp.route("/workout/history/<int:member_id>")
@roles_required("trainer")
def workout_history(member_id):
    sessions = query_all(
        "SELECT * FROM workout_sessions WHERE member_id=%s ORDER BY session_date DESC", (member_id,)
    )
    logs_by_session = {}
    for s in sessions:
        logs_by_session[s["session_id"]] = query_all(
            "SELECT * FROM workout_logs WHERE session_id=%s", (s["session_id"],)
        )
    member = query_one(
        "SELECT m.*, u.full_name FROM members m JOIN users u ON m.user_id=u.user_id WHERE m.member_id=%s",
        (member_id,),
    )
    return render_template("trainer/workout_history.html", sessions=sessions, logs_by_session=logs_by_session, member=member)


# ------------------------------------------------------------------
# PROGRESS UPDATE
# ------------------------------------------------------------------
@bp.route("/progress/<int:member_id>/update", methods=["POST"])
@roles_required("trainer")
def update_progress(member_id):
    member = query_one("SELECT height_cm FROM members WHERE member_id=%s", (member_id,))
    weight = request.form.get("weight_kg") or None
    bmi = calculate_bmi(weight, member["height_cm"]) if weight and member["height_cm"] else None

    execute(
        """INSERT INTO body_measurements (member_id, record_date, weight_kg, bmi, body_fat_percent,
                                           chest_cm, waist_cm, arms_cm, legs_cm, is_pr, pr_note)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (member_id, request.form.get("record_date") or date.today(), weight, bmi,
         request.form.get("body_fat_percent") or None, request.form.get("chest_cm") or None,
         request.form.get("waist_cm") or None, request.form.get("arms_cm") or None,
         request.form.get("legs_cm") or None, 1 if request.form.get("is_pr") else 0,
         request.form.get("pr_note") or None),
    )
    flash("Progress updated.", "success")
    return redirect(url_for("trainer.member_detail", member_id=member_id))


# ------------------------------------------------------------------
# DIET PLANS
# ------------------------------------------------------------------
@bp.route("/diet/<int:member_id>/create", methods=["POST"])
@roles_required("trainer")
def create_diet_plan(member_id):
    trainer_id = _get_trainer_id()
    execute(
        """INSERT INTO diet_plans (member_id, trainer_id, title, goal, daily_calories,
                                    protein_g, carbs_g, fat_g, meal_plan, notes)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (member_id, trainer_id, request.form.get("title") or "Diet Plan", request.form.get("goal"),
         request.form.get("daily_calories") or None, request.form.get("protein_g") or None,
         request.form.get("carbs_g") or None, request.form.get("fat_g") or None,
         request.form.get("meal_plan"), request.form.get("notes")),
    )
    flash("Diet plan created.", "success")
    return redirect(url_for("trainer.member_detail", member_id=member_id))


# ------------------------------------------------------------------
# AI-assisted quick actions (JSON)
# ------------------------------------------------------------------
@bp.route("/api/ai/workout/<int:member_id>")
@roles_required("trainer")
def ai_workout(member_id):
    member = query_one("SELECT * FROM members WHERE member_id=%s", (member_id,))
    latest = query_one(
        "SELECT weight_kg FROM body_measurements WHERE member_id=%s ORDER BY record_date DESC LIMIT 1",
        (member_id,),
    )
    profile = {
        "goal": member["goal"],
        "fitness_level": request.args.get("level", "beginner"),
        "days_per_week": request.args.get("days", 5),
        "weight_kg": latest["weight_kg"] if latest else 70,
    }
    plan = generate_workout_plan(profile)
    execute(
        "INSERT INTO ai_predictions (member_id, prediction_type, input_data, output_data) VALUES (%s,'workout_plan',%s,%s)",
        (member_id, str(profile), str(plan)),
    )
    return jsonify(plan)


@bp.route("/api/ai/diet/<int:member_id>")
@roles_required("trainer")
def ai_diet(member_id):
    member = query_one("SELECT * FROM members WHERE member_id=%s", (member_id,))
    latest = query_one(
        "SELECT weight_kg FROM body_measurements WHERE member_id=%s ORDER BY record_date DESC LIMIT 1",
        (member_id,),
    )
    import datetime as _dt
    age = None
    if member.get("dob"):
        today = date.today()
        dob = member["dob"]
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    profile = {
        "weight_kg": latest["weight_kg"] if latest else 70,
        "height_cm": member["height_cm"],
        "age": age or 28,
        "gender": member["gender"],
        "goal": member["goal"],
        "activity_level": request.args.get("activity", "moderate"),
    }
    plan = generate_diet_plan(profile)
    return jsonify(plan)


@bp.route("/api/ai/overload/<int:member_id>/<exercise_name>")
@roles_required("trainer")
def ai_overload(member_id, exercise_name):
    logs = query_all(
        """SELECT wl.* FROM workout_logs wl JOIN workout_sessions ws ON wl.session_id = ws.session_id
           WHERE ws.member_id=%s AND wl.exercise_name=%s ORDER BY ws.session_date""",
        (member_id, exercise_name),
    )
    result = suggest_progressive_overload(logs)
    return jsonify(result)
