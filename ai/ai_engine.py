"""
FitSync AI Engine
------------------
Self-contained, dependency-light AI features. No external API key is
required by default -- everything runs locally using rule-based logic
plus scikit-learn for the regression-based progress prediction. This
keeps the app fully functional out-of-the-box while still being easy
to swap for a hosted LLM (OpenAI/Gemini) later -- see `call_llm()`.

Exposed functions (all return plain dict/list, JSON-serialisable):
    generate_workout_plan(profile)
    generate_diet_plan(profile)
    suggest_progressive_overload(logs)
    detect_plateau(measurements)
    predict_progress(measurements, weeks_ahead=4)
"""
import os
import statistics
from datetime import date, timedelta

from utils.calculations import bmr_mifflin, tdee

# ------------------------------------------------------------------
# Optional hosted-LLM hook (OpenAI / Gemini). Disabled unless an API
# key is present in the environment -- the app works fully offline
# without it using the rule-based engine below.
# ------------------------------------------------------------------
def call_llm(prompt, system="You are a certified fitness and nutrition coach."):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content
    except Exception:
        return None


# ------------------------------------------------------------------
# 1. AI WORKOUT GENERATOR
# ------------------------------------------------------------------
SPLIT_TEMPLATES = {
    "weight_loss": ["Full Body", "Cardio + Core", "Full Body", "Cardio + Legs", "Active Recovery"],
    "muscle_gain": ["Chest & Triceps", "Back & Biceps", "Legs", "Shoulders & Core", "Full Body"],
    "general fitness": ["Upper Body", "Lower Body", "Cardio", "Core & Mobility", "Full Body"],
    "strength": ["Squat Focus", "Bench Focus", "Deadlift Focus", "Accessory / Core", "Full Body"],
    "endurance": ["Cardio Intervals", "Circuit Training", "Steady State Cardio", "Core", "Cardio + Mobility"],
}

EXERCISE_LIBRARY = {
    "Chest & Triceps": [("Bench Press", 4, 10), ("Incline Dumbbell Press", 3, 12), ("Cable Fly", 3, 15), ("Tricep Pushdown", 3, 15)],
    "Back & Biceps": [("Pull Ups", 4, 8), ("Barbell Row", 4, 10), ("Lat Pulldown", 3, 12), ("Bicep Curl", 3, 15)],
    "Legs": [("Barbell Squat", 4, 10), ("Leg Press", 3, 12), ("Romanian Deadlift", 3, 10), ("Calf Raise", 4, 15)],
    "Shoulders & Core": [("Overhead Press", 4, 10), ("Lateral Raise", 3, 15), ("Plank", 3, 60), ("Hanging Leg Raise", 3, 12)],
    "Full Body": [("Deadlift", 3, 8), ("Push Ups", 3, 15), ("Dumbbell Row", 3, 12), ("Kettlebell Swing", 3, 15)],
    "Upper Body": [("Push Ups", 4, 12), ("Dumbbell Shoulder Press", 3, 12), ("Seated Row", 3, 12), ("Tricep Dips", 3, 12)],
    "Lower Body": [("Goblet Squat", 4, 12), ("Walking Lunge", 3, 12), ("Leg Curl", 3, 12), ("Standing Calf Raise", 3, 15)],
    "Cardio": [("Treadmill Run", 1, 20), ("Cycling", 1, 20), ("Jump Rope", 3, 60)],
    "Cardio + Core": [("Rowing Machine", 1, 15), ("Mountain Climbers", 3, 30), ("Russian Twist", 3, 20)],
    "Cardio + Legs": [("Stair Climber", 1, 15), ("Bulgarian Split Squat", 3, 12), ("Jump Squat", 3, 15)],
    "Active Recovery": [("Light Walk", 1, 20), ("Stretching", 1, 15), ("Foam Rolling", 1, 10)],
    "Core & Mobility": [("Plank", 3, 45), ("Bird Dog", 3, 12), ("Cat-Cow Stretch", 2, 12)],
    "Squat Focus": [("Back Squat", 5, 5), ("Front Squat", 3, 8), ("Leg Extension", 3, 12)],
    "Bench Focus": [("Flat Bench Press", 5, 5), ("Incline Bench Press", 3, 8), ("Close Grip Bench", 3, 10)],
    "Deadlift Focus": [("Conventional Deadlift", 5, 5), ("Sumo Deadlift", 3, 6), ("Back Extension", 3, 12)],
    "Accessory / Core": [("Farmer Carry", 3, 30), ("Ab Wheel Rollout", 3, 10), ("Side Plank", 3, 30)],
    "Cardio Intervals": [("HIIT Sprints", 6, 30), ("Battle Ropes", 5, 30)],
    "Circuit Training": [("Burpees", 4, 15), ("Box Jumps", 4, 12), ("Kettlebell Swing", 4, 15)],
    "Steady State Cardio": [("Jogging", 1, 30), ("Cycling", 1, 30)],
}


def generate_workout_plan(profile):
    """
    profile: {goal, fitness_level, days_per_week, weight_kg}
    Returns a 5-day (or fewer) structured plan.
    """
    goal = (profile.get("goal") or "general fitness").lower()
    days = int(profile.get("days_per_week") or 5)
    level = (profile.get("fitness_level") or "beginner").lower()

    template = SPLIT_TEMPLATES.get(goal, SPLIT_TEMPLATES["general fitness"])[:max(1, min(days, 5))]

    level_multiplier = {"beginner": 0.8, "intermediate": 1.0, "advanced": 1.2}.get(level, 1.0)

    plan = []
    for day_num, focus in enumerate(template, start=1):
        exercises = []
        for name, sets, reps in EXERCISE_LIBRARY.get(focus, [("Full Body Circuit", 3, 12)]):
            adj_sets = max(2, round(sets * level_multiplier))
            exercises.append({"exercise": name, "sets": adj_sets, "reps": reps, "muscle_group": focus})
        plan.append({"day": day_num, "focus": focus, "exercises": exercises})

    return {
        "goal": goal,
        "level": level,
        "days_per_week": len(template),
        "plan": plan,
        "note": "Rest 60-90s between sets. Increase weight gradually week over week (progressive overload).",
    }


# ------------------------------------------------------------------
# 2. AI DIET RECOMMENDATION
# ------------------------------------------------------------------
def generate_diet_plan(profile):
    """
    profile: {weight_kg, height_cm, age, gender, goal, activity_level}
    Returns macro targets + a sample meal structure.
    """
    weight = profile.get("weight_kg")
    height = profile.get("height_cm")
    age = profile.get("age")
    gender = profile.get("gender")
    goal = (profile.get("goal") or "general fitness").lower()
    activity = profile.get("activity_level") or "moderate"

    bmr = bmr_mifflin(weight, height, age, gender)
    maintenance = tdee(bmr, activity) if bmr else None

    calories = maintenance
    if maintenance:
        if goal == "weight_loss":
            calories = round(maintenance * 0.8)
        elif goal == "muscle_gain":
            calories = round(maintenance * 1.12)
        else:
            calories = round(maintenance)
    else:
        calories = 2000  # fallback default

    if weight:
        protein_g = round(float(weight) * (2.0 if goal == "muscle_gain" else 1.6))
    else:
        protein_g = 120

    fat_g = round((calories * 0.25) / 9)
    protein_cal = protein_g * 4
    carbs_g = max(0, round((calories - protein_cal - fat_g * 9) / 4))

    meals = {
        "breakfast": "High-protein breakfast: eggs/oats/greek yogurt + fruit",
        "mid_morning_snack": "Handful of nuts or a protein shake",
        "lunch": "Lean protein (chicken/paneer/tofu/fish) + whole grains + vegetables",
        "evening_snack": "Fruit or sprouts salad",
        "dinner": "Lean protein + salad + light carbs",
    }

    return {
        "goal": goal,
        "bmr": bmr,
        "maintenance_calories": maintenance,
        "target_calories": calories,
        "macros": {"protein_g": protein_g, "carbs_g": carbs_g, "fat_g": fat_g},
        "meal_structure": meals,
        "note": "Adjust portions weekly based on progress. Stay hydrated (3+ litres/day).",
    }


# ------------------------------------------------------------------
# 3. AI PROGRESSIVE OVERLOAD SUGGESTIONS
# ------------------------------------------------------------------
def suggest_progressive_overload(logs):
    """
    logs: list of dicts ordered oldest->newest for ONE exercise:
          [{date, sets, reps, weight_kg}, ...]
    Returns a suggestion dict.
    """
    if not logs or len(logs) < 2:
        return {"status": "insufficient_data", "message": "Log at least 2 sessions of this exercise for a suggestion."}

    weights = [float(l["weight_kg"] or 0) for l in logs]
    reps = [int(l["reps"] or 0) for l in logs]

    last_weight = weights[-1]
    prev_weight = weights[-2]
    last_reps = reps[-1]

    trend_up = last_weight >= prev_weight

    # simple rule set mirroring common coaching heuristics
    if trend_up and last_reps >= 12:
        new_weight = round(last_weight * 1.05, 1)
        return {
            "status": "increase",
            "message": f"You hit {last_reps} reps at {last_weight}kg. Increase load to ~{new_weight}kg next session.",
            "suggested_weight_kg": new_weight,
        }
    elif last_reps < 8:
        return {
            "status": "hold",
            "message": f"Reps ({last_reps}) are below target range. Keep weight at {last_weight}kg and focus on form until you reach 8-12 reps.",
            "suggested_weight_kg": last_weight,
        }
    else:
        new_weight = round(last_weight * 1.025, 1)
        return {
            "status": "slight_increase",
            "message": f"Steady progress. Try a small bump to ~{new_weight}kg while maintaining {last_reps}+ reps.",
            "suggested_weight_kg": new_weight,
        }


# ------------------------------------------------------------------
# 4. AI PLATEAU DETECTION
# ------------------------------------------------------------------
def detect_plateau(measurements, metric="weight_kg", window=4, threshold_pct=1.0):
    """
    measurements: list of dicts ordered oldest->newest:
        [{record_date, weight_kg, bmi, body_fat_percent}, ...]
    Flags a plateau if the metric hasn't changed by more than
    threshold_pct% over the last `window` records.
    """
    values = [float(m[metric]) for m in measurements if m.get(metric) is not None]
    if len(values) < window:
        return {"plateau": False, "message": "Not enough data points yet to assess a plateau.", "data_points": len(values)}

    recent = values[-window:]
    change_pct = abs((recent[-1] - recent[0]) / recent[0]) * 100 if recent[0] else 0
    std_dev = statistics.pstdev(recent)

    is_plateau = change_pct < threshold_pct

    return {
        "plateau": is_plateau,
        "metric": metric,
        "change_percent": round(change_pct, 2),
        "std_dev": round(std_dev, 3),
        "message": (
            f"Plateau detected: {metric.replace('_', ' ')} has changed only {round(change_pct,2)}% "
            f"over the last {window} records. Consider adjusting training volume, intensity, or calories."
            if is_plateau else
            f"Good progress: {metric.replace('_', ' ')} changed {round(change_pct,2)}% over the last {window} records."
        ),
    }


# ------------------------------------------------------------------
# 5. AI PROGRESS PREDICTION (Linear Regression)
# ------------------------------------------------------------------
def predict_progress(measurements, metric="weight_kg", weeks_ahead=4):
    """
    measurements: list of dicts ordered oldest->newest with 'record_date' (date/str) and metric.
    Fits a simple linear regression over time (days) to project future values.
    """
    try:
        import numpy as np
        from sklearn.linear_model import LinearRegression
    except ImportError:
        return {"status": "error", "message": "scikit-learn not available"}

    points = []
    for m in measurements:
        val = m.get(metric)
        rd = m.get("record_date")
        if val is None or rd is None:
            continue
        if isinstance(rd, str):
            from datetime import datetime
            rd = datetime.strptime(rd[:10], "%Y-%m-%d").date()
        points.append((rd, float(val)))

    if len(points) < 3:
        return {"status": "insufficient_data", "message": "Need at least 3 measurements to predict a trend."}

    points.sort(key=lambda p: p[0])
    base_date = points[0][0]
    X = np.array([[(p[0] - base_date).days] for p in points])
    y = np.array([p[1] for p in points])

    model = LinearRegression()
    model.fit(X, y)

    last_day = (points[-1][0] - base_date).days
    future_day = last_day + weeks_ahead * 7
    predicted_value = float(model.predict([[future_day]])[0])
    slope_per_week = float(model.coef_[0]) * 7

    trend = "increasing" if slope_per_week > 0.05 else ("decreasing" if slope_per_week < -0.05 else "stable")

    target_date = base_date + timedelta(days=future_day)

    return {
        "status": "ok",
        "metric": metric,
        "current_value": points[-1][1],
        "predicted_value": round(predicted_value, 2),
        "predicted_date": target_date.isoformat(),
        "weekly_rate_of_change": round(slope_per_week, 3),
        "trend": trend,
        "r_squared": round(model.score(X, y), 3),
    }
