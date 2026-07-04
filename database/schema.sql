-- ============================================================
-- FitSync - Gym Management System
-- MySQL Database Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS fitsync CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fitsync;

-- ------------------------------------------------------------
-- ROLES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO roles (role_name) VALUES ('admin'), ('trainer'), ('member')
ON DUPLICATE KEY UPDATE role_name = role_name;

-- ------------------------------------------------------------
-- USERS (base auth table for all roles)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    role_id INT NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    profile_image VARCHAR(255) DEFAULT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(role_id)
);

-- ------------------------------------------------------------
-- MEMBERSHIP PLANS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS membership_plans (
    plan_id INT AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(100) NOT NULL,
    description TEXT,
    duration_months INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- TRAINERS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trainers (
    trainer_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    specialization VARCHAR(150),
    experience_years INT DEFAULT 0,
    bio TEXT,
    salary DECIMAL(10,2) DEFAULT 0,
    joined_date DATE DEFAULT (CURRENT_DATE),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- MEMBERS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS members (
    member_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    trainer_id INT DEFAULT NULL,
    plan_id INT DEFAULT NULL,
    gender ENUM('male','female','other') DEFAULT NULL,
    dob DATE DEFAULT NULL,
    address VARCHAR(255),
    goal VARCHAR(150) DEFAULT 'General Fitness',
    height_cm DECIMAL(5,2) DEFAULT NULL,
    join_date DATE DEFAULT (CURRENT_DATE),
    membership_start DATE DEFAULT NULL,
    membership_end DATE DEFAULT NULL,
    status ENUM('active','inactive','expired') DEFAULT 'active',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id) ON DELETE SET NULL,
    FOREIGN KEY (plan_id) REFERENCES membership_plans(plan_id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- PAYMENTS / FEES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    plan_id INT DEFAULT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    paid_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    outstanding_amount DECIMAL(10,2) GENERATED ALWAYS AS (total_amount - paid_amount) STORED,
    due_date DATE,
    payment_date DATE DEFAULT NULL,
    payment_method ENUM('cash','card','upi','bank_transfer','other') DEFAULT 'cash',
    status ENUM('paid','partial','unpaid','overdue') DEFAULT 'unpaid',
    invoice_no VARCHAR(50),
    notes VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES membership_plans(plan_id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- ATTENDANCE
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    check_in DATETIME NOT NULL,
    check_out DATETIME DEFAULT NULL,
    attendance_date DATE NOT NULL,
    method ENUM('manual','qr') DEFAULT 'manual',
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
    UNIQUE KEY uniq_member_day (member_id, attendance_date)
);

-- ------------------------------------------------------------
-- WORKOUT SESSIONS (a session groups multiple logs on a date)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workout_sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    trainer_id INT DEFAULT NULL,
    session_date DATE NOT NULL,
    title VARCHAR(150) DEFAULT 'Workout Session',
    total_duration_min INT DEFAULT 0,
    total_calories DECIMAL(7,2) DEFAULT 0,
    trainer_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
    FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- WORKOUT LOGS (exercise level detail within a session)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workout_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    muscle_group VARCHAR(80) NOT NULL,
    exercise_name VARCHAR(150) NOT NULL,
    sets INT DEFAULT 0,
    reps INT DEFAULT 0,
    weight_kg DECIMAL(6,2) DEFAULT 0,
    duration_min INT DEFAULT 0,
    calories_burned DECIMAL(7,2) DEFAULT 0,
    trainer_notes VARCHAR(255),
    FOREIGN KEY (session_id) REFERENCES workout_sessions(session_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- BODY MEASUREMENTS / PROGRESS TRACKING
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS body_measurements (
    measurement_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    record_date DATE NOT NULL,
    weight_kg DECIMAL(5,2) DEFAULT NULL,
    bmi DECIMAL(5,2) DEFAULT NULL,
    body_fat_percent DECIMAL(5,2) DEFAULT NULL,
    chest_cm DECIMAL(5,2) DEFAULT NULL,
    waist_cm DECIMAL(5,2) DEFAULT NULL,
    arms_cm DECIMAL(5,2) DEFAULT NULL,
    legs_cm DECIMAL(5,2) DEFAULT NULL,
    is_pr TINYINT(1) DEFAULT 0,
    pr_note VARCHAR(150) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- DIET PLANS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS diet_plans (
    diet_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    trainer_id INT DEFAULT NULL,
    title VARCHAR(150) DEFAULT 'Diet Plan',
    goal VARCHAR(100),
    daily_calories INT DEFAULT NULL,
    protein_g INT DEFAULT NULL,
    carbs_g INT DEFAULT NULL,
    fat_g INT DEFAULT NULL,
    meal_plan TEXT,
    notes VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
    FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- NOTIFICATIONS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    message VARCHAR(500) NOT NULL,
    type ENUM('info','warning','success','danger') DEFAULT 'info',
    is_read TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- AI PREDICTIONS (stores AI generated outputs for auditing / reuse)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_predictions (
    prediction_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    prediction_type ENUM('workout_plan','diet_plan','progressive_overload','progress_prediction','plateau_detection') NOT NULL,
    input_data JSON DEFAULT NULL,
    output_data JSON DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- INDEXES
-- ------------------------------------------------------------
CREATE INDEX idx_members_trainer ON members(trainer_id);
CREATE INDEX idx_payments_member ON payments(member_id);
CREATE INDEX idx_attendance_member_date ON attendance(member_id, attendance_date);
CREATE INDEX idx_sessions_member ON workout_sessions(member_id);
CREATE INDEX idx_logs_session ON workout_logs(session_id);
CREATE INDEX idx_measurements_member ON body_measurements(member_id);
