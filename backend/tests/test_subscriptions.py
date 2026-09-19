import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import Settings, app
from app.subscriptions import (
    MailSettings,
    SubscriptionRequest,
    confirm_subscription,
    create_subscription,
    initialize_database,
    send_confirmation,
)


def request(**values: object) -> SubscriptionRequest:
    return SubscriptionRequest(email="pessoa@example.org", consent=True, **values)


def test_database_subscription_and_confirmation(tmp_path):
    path = str(tmp_path / "subscriptions.sqlite3")
    initialize_database(path)
    data = request(politician_provider="camara", politician_id=1, politician_name="Maria")
    token, confirmed = create_subscription(path, data)
    assert not confirmed
    repeated, confirmed = create_subscription(path, data)
    assert repeated == token and not confirmed
    assert confirm_subscription(path, token)
    assert not confirm_subscription(path, "missing-token")
    repeated, confirmed = create_subscription(path, data)
    assert repeated == token and confirmed
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT email FROM subscriptions").fetchone() == (
            "pessoa@example.org",
        )


def test_validation_and_consent(tmp_path):
    with pytest.raises(ValidationError):
        SubscriptionRequest(email="invalid", consent=True)
    path = str(tmp_path / "subscriptions.sqlite3")
    initialize_database(path)
    with pytest.raises(ValueError, match="autorizar"):
        create_subscription(path, SubscriptionRequest(email="a@b.com", consent=False))


def test_confirmation_email():
    assert not send_confirmation(MailSettings(), "a@b.com", "token", "Assunto")
    smtp = MailSettings(
        host="smtp.example.org",
        username="user",
        password="secret",
        sender="oi@example.org",
        notification_email="admin@example.org",
    )
    with patch("app.subscriptions.smtplib.SMTP") as mocked:
        assert send_confirmation(smtp, "a@b.com", "token", "Assunto")
        server = mocked.return_value.__enter__.return_value
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("user", "secret")
        assert server.send_message.call_count == 2
    without_notice = MailSettings(
        host="smtp.example.org", username="user", password="secret", sender="oi@example.org"
    )
    with patch("app.subscriptions.smtplib.SMTP") as mocked:
        assert send_confirmation(without_notice, "a@b.com", "token", "Assunto")
        mocked.return_value.__enter__.return_value.send_message.assert_called_once()


def test_subscription_routes(tmp_path):
    path = str(tmp_path / "subscriptions.sqlite3")
    with TestClient(app) as client:
        app.state.settings = Settings(database_path=path)
        initialize_database(path)
        payload = {"email": "pessoa@example.org", "consent": True}
        response = client.post("/subscriptions", json=payload)
        assert response.status_code == 201
        assert "registrada" in response.json()["message"]
        with sqlite3.connect(path) as connection:
            token = connection.execute("SELECT confirmation_token FROM subscriptions").fetchone()[0]
        assert client.get(f"/subscriptions/confirm/{token}").status_code == 200
        assert client.post("/subscriptions", json=payload).json()["confirmation_required"] is False
        assert client.get("/subscriptions/confirm/short").status_code == 404
        assert client.get("/subscriptions/confirm/this-token-does-not-exist").status_code == 404


def test_route_reports_confirmation_email_sent(tmp_path):
    path = str(tmp_path / "subscriptions.sqlite3")
    with TestClient(app) as client:
        app.state.settings = Settings(database_path=path)
        initialize_database(path)
        with patch("app.main.send_confirmation", return_value=True):
            response = client.post(
                "/subscriptions",
                json={
                    "email": "pessoa@example.org",
                    "consent": True,
                    "politician_name": "Maria",
                },
            )
        assert "Enviamos" in response.json()["message"]
