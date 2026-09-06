"""Sends transactional email. Without SMTP configured, links are logged to the console."""

import smtplib
from email.message import EmailMessage

from app.core.config import settings


def _send(to: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        print(f"\n--- EMAIL (SMTP not configured) ---\nTo: {to}\n{subject}\n\n{body}\n---\n")
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)


def send_verification_email(to: str, name: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    _send(
        to,
        "Verify your DronaAI.fit account",
        f"Hi {name},\n\nConfirm your email address to activate your account:\n\n{link}\n\n"
        "This link expires in 24 hours.\n\nIf you didn't sign up, you can ignore this email.",
    )


def send_password_reset_email(to: str, name: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    _send(
        to,
        "Reset your DronaAI.fit password",
        f"Hi {name},\n\nReset your password here:\n\n{link}\n\n"
        "This link expires in 1 hour.\n\nIf you didn't request this, you can ignore this email.",
    )
