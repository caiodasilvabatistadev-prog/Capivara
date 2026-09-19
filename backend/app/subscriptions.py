import hashlib
import secrets
import smtplib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path

from pydantic import BaseModel, Field


class SubscriptionRequest(BaseModel):
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=254)
    consent: bool
    politician_provider: str | None = Field(default=None, max_length=40)
    politician_id: int | None = Field(default=None, ge=1)
    politician_name: str | None = Field(default=None, max_length=150)


class SubscriptionResponse(BaseModel):
    message: str
    confirmation_required: bool = True


@dataclass(frozen=True)
class MailSettings:
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    sender: str = ""
    notification_email: str = ""
    public_url: str = "http://localhost:3000"


def initialize_database(path: str) -> None:
    database = Path(path)
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                email_hash TEXT NOT NULL,
                confirmation_token TEXT NOT NULL UNIQUE,
                confirmed_at TEXT,
                politician_provider TEXT,
                politician_id INTEGER,
                politician_name TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(email_hash, politician_provider, politician_id)
            )
            """
        )
        connection.commit()


def create_subscription(path: str, data: SubscriptionRequest) -> tuple[str, bool]:
    if not data.consent:
        raise ValueError("É necessário autorizar o envio de e-mails")
    email = str(data.email).strip().lower()
    email_hash = hashlib.sha256(email.encode()).hexdigest()
    token = secrets.token_urlsafe(32)
    created_at = datetime.now(UTC).isoformat()
    with closing(sqlite3.connect(path)) as connection:
        existing = connection.execute(
            """SELECT confirmation_token, confirmed_at FROM subscriptions
               WHERE email_hash = ? AND politician_provider IS ? AND politician_id IS ?""",
            (email_hash, data.politician_provider, data.politician_id),
        ).fetchone()
        if existing:
            return str(existing[0]), existing[1] is not None
        connection.execute(
            """INSERT INTO subscriptions
               (email, email_hash, confirmation_token, politician_provider, politician_id,
                politician_name, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                email,
                email_hash,
                token,
                data.politician_provider,
                data.politician_id,
                data.politician_name,
                created_at,
            ),
        )
        connection.commit()
    return token, False


def confirm_subscription(path: str, token: str) -> bool:
    with closing(sqlite3.connect(path)) as connection:
        result = connection.execute(
            "UPDATE subscriptions SET confirmed_at = ? WHERE confirmation_token = ?",
            (datetime.now(UTC).isoformat(), token),
        )
        connection.commit()
    return result.rowcount > 0


def send_confirmation(settings: MailSettings, recipient: str, token: str, subject: str) -> bool:
    if not all((settings.host, settings.username, settings.password, settings.sender)):
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.sender
    message["To"] = recipient
    message.set_content(
        "Confirme sua inscrição no Puxando a Capivara:\n\n"
        f"{settings.public_url}/confirmar-inscricao?token={token}\n\n"
        "Se você não solicitou este alerta, ignore esta mensagem."
    )
    with smtplib.SMTP(settings.host, settings.port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(settings.username, settings.password)
        smtp.send_message(message)
        if settings.notification_email:
            notice = EmailMessage()
            notice["Subject"] = "Nova inscrição no Puxando a Capivara"
            notice["From"] = settings.sender
            notice["To"] = settings.notification_email
            notice.set_content(f"Nova inscrição pendente de confirmação: {recipient}")
            smtp.send_message(notice)
    return True
