"""
Run this once after creating the database & running schema.sql / seed.sql:

    python seed.py

Creates:
  - 1 Admin        : admin@fitsync.com     / Admin@123
  - 1 Trainer      : trainer@fitsync.com   / Trainer@123
  - 1 Member       : member@fitsync.com    / Member@123
  - Sample body-measurement history + a workout session for the demo
    member so the dashboards / charts / AI features have data to show.
"""
from datetime import date, timedelta
import random

from werkzeug.security import generate_password_hash

from app import create_app
from utils.db import query_one, execute, query_all

app = create_app()


def get_or_create_role(name):
    row = query_one("SELECT role_id FROM roles WHERE role_name=%s", (name,))
    if row:
        return row["role_id"]
    return execute("INSERT INTO roles (role_name) VALUES (%s)", (name,), return_id=True)


def create_user(role_id, full_name, email, phone, password):
    existing = query_one("SELECT user_id FROM users WHERE email=%s", (email,))
    if existing:
        return existing["user_id"], False
    uid = execute(
        "INSERT INTO users (role_id, full_name, email, phone, password_hash) VALUES (%s,%s,%s,%s,%s)",
        (role_id, full_name, email, phone, generate_password_hash(password)),
        return_id=True,
    )
    return uid, True


def run():
    with app.app_context():
        admin_role = get_or_create_role("admin")
        trainer_role = get_or_create_role("trainer")
        member_role = get_or_create_role("member")

        admin_id, created = create_user(admin_role, "System Admin", "admin@fitsync.com", "9999999999", "Admin@123")
        print(f"Admin user_id={admin_id} (created={created})")

        trainer_user_id, created = create_user(trainer_role, "Alex Trainer", "trainer@fitsync.com", "8888888888", "Trainer@123")
        print(f"Trainer user_id={trainer_user_id} (created={created})")
        trainer_row = query_one("SELECT trainer_id FROM trainers WHERE user_id=%s", (trainer_user_id,))
        if not trainer_row:
            trainer_id = execute(
                "INSERT INTO trainers (user_id, specialization, experience_years, salary) VALUES (%s,%s,%s,%s)",
                (trainer_user_id, "Strength & Conditioning", 5, 35000),
                return_id=True,
            )
        else:
            trainer_id = trainer_row["trainer_id"]
        print(f"Trainer trainer_id={trainer_id}")

        plans = query_all("SELECT * FROM membership_plans LIMIT 1")
        plan_id = plans[0]["plan_id"] if plans else None

        member_user_id, created = create_user(member_role, "Sam Member", "member@fitsync.com", "7777777777", "Member@123")
        print(f"Member user_id={member_user_id} (created={created})")
        member_row = query_one("SELECT member_id FROM members WHERE user_id=%s", (member_user_id,))
        if not member_row:
            member_id = execute(
                """INSERT INTO members (user_id, trainer_id, plan_id, gender, goal, height_cm,
                                         membership_start, membership_end, status)
                   VALUES (%s,%s,%s,'male','muscle_gain',178,%s,%s,'active')""",
                (member_user_id, trainer_id, plan_id, date.today() - timedelta(days=60),
                 date.today() + timedelta(days=305)),
                return_id=True,
            )
        else:
            member_id = member_row["member_id"]
        print(f"Member member_id={member_id}")

        # Sample payment
        if not query_all("SELECT * FROM payments WHERE member_id=%s", (member_id,)):
            execute(
                """INSERT INTO payments (member_id, plan_id, total_amount, paid_amount, due_date,
                                          payment_date, payment_method, status, invoice_no)
                   VALUES (%s,%s,14000,10000,%s,%s,'upi','partial','INV-DEMO-0001')""",
                (member_id, plan_id, date.today() + timedelta(days=10), date.today() - timedelta(days=55)),
            )
            print("Sample payment added")

        # Sample body measurements (8 weeks of gradually improving data)
        existing_measurements = query_all("SELECT * FROM body_measurements WHERE member_id=%s", (member_id,))
        if not existing_measurements:
            base_weight = 82.0
            for week in range(8):
                d = date.today() - timedelta(weeks=(7 - week))
                weight = round(base_weight - week * 0.4 + random.uniform(-0.2, 0.2), 1)
                bmi = round(weight / (1.78 ** 2), 2)
                execute(
                    """INSERT INTO body_measurements
                       (member_id, record_date, weight_kg, bmi, body_fat_percent, chest_cm, waist_cm, arms_cm, legs_cm)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (member_id, d, weight, bmi, round(22 - week * 0.3, 1), 102 + week * 0.2,
                     90 - week * 0.5, 34 + week * 0.1, 56 + week * 0.1),
                )
            print("Sample body measurements added (8 weeks)")

        # Sample workout session
        if not query_all("SELECT * FROM workout_sessions WHERE member_id=%s", (member_id,)):
            session_id = execute(
                """INSERT INTO workout_sessions (member_id, trainer_id, session_date, title, trainer_notes)
                   VALUES (%s,%s,%s,'Chest & Triceps','Great session, focus on form for incline press')""",
                (member_id, trainer_id, date.today() - timedelta(days=2)),
            )
            session_id = query_one("SELECT LAST_INSERT_ID() id")["id"]
            logs = [
                ("Chest & Triceps", "Bench Press", 4, 10, 60, 20, 250),
                ("Chest & Triceps", "Incline Dumbbell Press", 3, 12, 22, 15, 180),
                ("Chest & Triceps", "Tricep Pushdown", 3, 15, 25, 10, 90),
            ]
            for mg, ex, sets, reps, wt, dur, cal in logs:
                execute(
                    """INSERT INTO workout_logs (session_id, muscle_group, exercise_name, sets, reps,
                                                  weight_kg, duration_min, calories_burned)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (session_id, mg, ex, sets, reps, wt, dur, cal),
                )
            execute(
                "UPDATE workout_sessions SET total_duration_min=45, total_calories=520 WHERE session_id=%s",
                (session_id,),
            )
            print("Sample workout session added")

        # Sample diet plan
        if not query_all("SELECT * FROM diet_plans WHERE member_id=%s", (member_id,)):
            execute(
                """INSERT INTO diet_plans (member_id, trainer_id, title, goal, daily_calories,
                                            protein_g, carbs_g, fat_g, meal_plan, notes)
                   VALUES (%s,%s,'Lean Bulk Plan','muscle_gain',2600,160,280,80,
                           'Breakfast: Oats+eggs | Lunch: Chicken+rice | Dinner: Fish+veggies',
                           'Increase water intake, avoid processed sugar')""",
                (member_id, trainer_id),
            )
            print("Sample diet plan added")

        print("\nSeed complete. Demo logins:")
        print("  Admin:   admin@fitsync.com   / Admin@123")
        print("  Trainer: trainer@fitsync.com / Trainer@123")
        print("  Member:  member@fitsync.com  / Member@123")


if __name__ == "__main__":
    run()
