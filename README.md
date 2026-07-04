# FitSync — Gym Management System

A full-stack gym management platform built with **Flask (Python)**, **MySQL**,
and **HTML/CSS/JS (Bootstrap 5 + Chart.js)**. Includes role-based dashboards
for Admin, Trainer, and Member, plus a self-contained **AI engine** (workout
generation, diet recommendations, progressive overload suggestions, plateau
detection, and progress prediction via scikit-learn) that works out of the
box with no external API key required.

## Tech Stack
- **Backend:** Flask 3 (Python), session-based auth + JWT issuance
- **Database:** MySQL (13 tables — see `database/schema.sql`)
- **Frontend:** Server-rendered Jinja2 templates, Bootstrap 5, Chart.js, vanilla JS
- **AI:** Rule-based engine + scikit-learn Linear Regression (`ai/ai_engine.py`).
  Optional hosted LLM hook for OpenAI is included but disabled unless
  `OPENAI_API_KEY` is set.

## 1. Setup

```bash
cd fitsync
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure environment

```bash
cp .env.example .env
# edit .env and set your MySQL credentials
```

## 3. Create the database

```bash
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql      # membership plans only
python seed.py                            # creates demo Admin/Trainer/Member + sample data
```

## 4. Run the app

```bash
python app.py
```

Visit **http://localhost:5000**

## Demo Logins (after `python seed.py`)

| Role    | Email                | Password    |
|---------|-----------------------|-------------|
| Admin   | admin@fitsync.com     | Admin@123   |
| Trainer | trainer@fitsync.com   | Trainer@123 |
| Member  | member@fitsync.com    | Member@123  |

## Project Structure

```
fitsync/
├── app.py                 # Flask application factory / entry point
├── config.py               # Environment-driven configuration
├── seed.py                 # Creates demo accounts + sample data
├── requirements.txt
├── .env.example
├── database/
│   ├── schema.sql          # All 13 tables (users, roles, members, trainers,
│   │                          membership_plans, payments, attendance,
│   │                          workout_sessions, workout_logs,
│   │                          body_measurements, diet_plans,
│   │                          notifications, ai_predictions)
│   └── seed.sql             # Default membership plans
├── routes/
│   ├── auth.py              # Login / Register / Logout
│   ├── admin.py              # Admin dashboard + all admin CRUD
│   ├── trainer.py            # Trainer dashboard, workout/diet/progress
│   └── member.py             # Member dashboard, history, progress, payments
├── ai/
│   └── ai_engine.py          # Workout generator, diet recommender,
│                                progressive overload, plateau detection,
│                                progress prediction (scikit-learn)
├── utils/
│   ├── db.py                 # MySQL connection pool + query helpers
│   ├── auth_utils.py          # Session/JWT auth + role decorators
│   └── calculations.py        # BMI, calories, BMR/TDEE, invoice numbers
├── templates/                # Jinja2 templates (base + admin/trainer/member/auth)
└── static/
    ├── css/style.css          # Custom modern UI theme
    └── js/app.js               # Shared front-end helpers (AI fetch, dynamic rows)
```

## Feature Summary

**Admin:** dashboard KPIs, member/trainer CRUD, membership plans, fee &
payment tracking with outstanding alerts, attendance check-in/out,
notifications broadcast.

**Trainer:** assigned member roster, record workout sessions
(sets/reps/weight/duration/calories/notes), log body measurements, create
diet plans, view workout history, AI-assisted workout & diet generation,
AI plateau detection per member.

**Member:** dashboard, membership status, workout plan/history, diet plan,
attendance history + self check-in, progress charts (weight/BMI trend) with
AI progress prediction and plateau detection, payment history.

## Notes
- Passwords are hashed with Werkzeug's `generate_password_hash` (PBKDF2).
- The AI engine runs 100% locally by default (no API key needed). To use a
  hosted LLM instead, set `OPENAI_API_KEY` in `.env` — `ai/ai_engine.py`
  exposes a `call_llm()` hook for this.
- Calorie estimates use standard MET-based formulas; BMI/BMR/TDEE use the
  Mifflin-St Jeor equation.
- This is a learning/demo-grade implementation. For production, add CSRF
  protection, rate limiting, input validation hardening, and HTTPS.
