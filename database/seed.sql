USE fitsync;

-- Default membership plans
INSERT INTO membership_plans (plan_name, description, duration_months, amount) VALUES
('Basic Monthly', 'Gym floor access, locker facility', 1, 1500.00),
('Quarterly', 'Gym floor access + group classes', 3, 4000.00),
('Half Yearly', 'Full access + 1 free trainer session/month', 6, 7500.00),
('Annual Gold', 'Full access + personal trainer + diet plan', 12, 14000.00);

-- NOTE: The default Admin account is created by running `python seed.py`
-- (see project root) which hashes the password securely with Werkzeug
-- instead of hardcoding a hash here.
