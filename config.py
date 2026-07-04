import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "fitsync-dev-secret-change-me")
    JWT_SECRET = os.environ.get("JWT_SECRET", "fitsync-jwt-secret-change-me")
    JWT_EXP_HOURS = int(os.environ.get("JWT_EXP_HOURS", 12))

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "fitsync")
    MYSQL_SSL_CA = os.environ.get("MYSQL_SSL_CA", "")  # path to CA cert, e.g. for Aiven (local dev)
    MYSQL_SSL_CA_CONTENT = os.environ.get("MYSQL_SSL_CA_CONTENT", "")  # raw cert content (e.g. Render env var)
    MYSQL_POOL_SIZE = int(os.environ.get("MYSQL_POOL_SIZE", 5))

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "FitSync Gym")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
