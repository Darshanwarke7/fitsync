"""
Email utility — sends real emails via SMTP (works with Gmail's free SMTP
relay, or any other SMTP provider). Configure via environment variables:

    MAIL_SERVER=smtp.gmail.com
    MAIL_PORT=587
    MAIL_USE_TLS=true
    MAIL_USERNAME=youraddress@gmail.com
    MAIL_PASSWORD=your_16_char_app_password   (NOT your normal Gmail password)
    MAIL_FROM_NAME=FitSync Gym

For Gmail specifically, you must create an "App Password":
  Google Account -> Security -> 2-Step Verification -> App passwords
  (regular account passwords are blocked by Google for SMTP login)

If MAIL_USERNAME / MAIL_PASSWORD are not set, send_email() silently no-ops
so the app keeps working without email configured (in-app notifications
still work regardless).
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app


def is_email_configured():
    return bool(current_app.config.get("MAIL_USERNAME") and current_app.config.get("MAIL_PASSWORD"))


def send_email(to_email, subject, body_html, body_text=None):
    """Returns True on success, False on failure (never raises)."""
    if not is_email_configured():
        current_app.logger.info("Email not configured — skipping send to %s", to_email)
        return False

    server_host = current_app.config["MAIL_SERVER"]
    server_port = current_app.config["MAIL_PORT"]
    username = current_app.config["MAIL_USERNAME"]
    password = current_app.config["MAIL_PASSWORD"]
    from_name = current_app.config.get("MAIL_FROM_NAME", "FitSync Gym")
    use_tls = current_app.config.get("MAIL_USE_TLS", True)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{username}>"
    msg["To"] = to_email

    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        if use_tls:
            with smtplib.SMTP(server_host, server_port, timeout=10) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(username, password)
                server.sendmail(username, [to_email], msg.as_string())
        else:
            with smtplib.SMTP_SSL(server_host, server_port, timeout=10) as server:
                server.login(username, password)
                server.sendmail(username, [to_email], msg.as_string())
        return True
    except Exception as e:
        current_app.logger.error("Failed to send email to %s: %s", to_email, e)
        return False


def notification_email_html(title, message, recipient_name):
    return f"""
    <div style="font-family:Arial,sans-serif; max-width:520px; margin:auto; padding:24px; border:1px solid #eee; border-radius:12px;">
      <div style="font-weight:800; font-size:1.2rem; color:#4834d4; margin-bottom:4px;">FitSync</div>
      <p>Hi {recipient_name},</p>
      <h3 style="margin-bottom:4px;">{title}</h3>
      <p style="color:#333;">{message}</p>
      <p style="margin-top:24px; font-size:0.8rem; color:#888;">This is an automated message from your gym's FitSync account. Log in to your dashboard for more details.</p>
    </div>
    """
