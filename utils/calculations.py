"""Small numeric/business-logic helpers shared across routes."""
import random
import string
from datetime import date


def calculate_bmi(weight_kg, height_cm):
    if not weight_kg or not height_cm:
        return None
    height_m = float(height_cm) / 100
    if height_m <= 0:
        return None
    return round(float(weight_kg) / (height_m ** 2), 2)


def bmi_category(bmi):
    if bmi is None:
        return "Unknown"
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def estimate_calories(met, weight_kg, duration_min):
    """Standard MET formula: kcal = MET * weight(kg) * duration(hr)."""
    if not weight_kg or not duration_min:
        return 0
    hours = float(duration_min) / 60.0
    return round(float(met) * float(weight_kg) * hours, 2)


MUSCLE_GROUP_MET = {
    "chest": 5.0, "back": 5.0, "legs": 6.0, "shoulders": 4.5,
    "arms": 4.0, "core": 4.0, "cardio": 8.0, "full body": 6.5,
}


def calories_for_exercise(muscle_group, weight_kg, duration_min):
    met = MUSCLE_GROUP_MET.get((muscle_group or "").lower(), 5.0)
    return estimate_calories(met, weight_kg, duration_min)


def generate_invoice_no():
    today = date.today().strftime("%Y%m%d")
    rand = "".join(random.choices(string.digits, k=4))
    return f"INV-{today}-{rand}"


def bmr_mifflin(weight_kg, height_cm, age, gender):
    """Mifflin-St Jeor equation for Basal Metabolic Rate."""
    if not (weight_kg and height_cm and age):
        return None
    base = 10 * float(weight_kg) + 6.25 * float(height_cm) - 5 * float(age)
    if (gender or "").lower() == "male":
        return round(base + 5, 1)
    elif (gender or "").lower() == "female":
        return round(base - 161, 1)
    return round(base - 78, 1)  # neutral average offset for 'other'


ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2, "light": 1.375, "moderate": 1.55,
    "active": 1.725, "very_active": 1.9,
}


def tdee(bmr, activity_level="moderate"):
    if bmr is None:
        return None
    mult = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    return round(bmr * mult, 1)
