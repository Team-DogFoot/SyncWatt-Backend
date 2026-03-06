from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

VALID_UPDATE = {
    "update_id": 1,
    "message": {
        "message_id": 1,
        "chat": {"id": 123},
        "text": "hello",
        "from": {"id": 1, "is_bot": False, "first_name": "Test"},
    },
}


class TestWebhookAuth:
    """Tests for webhook secret token authentication."""

    @patch("app.api.webhook.settings")
    @patch("app.api.webhook.telegram_service")
    def test_invalid_token_returns_403(self, mock_service, mock_settings):
        """Requests with an invalid secret token must receive a 403 response."""
        mock_settings.WEBHOOK_SECRET_TOKEN = "correct-token"

        response = client.post(
            "/webhook/telegram",
            json=VALID_UPDATE,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-token"},
        )

        assert response.status_code == 403

    @patch("app.api.webhook.settings")
    @patch("app.api.webhook.telegram_service")
    def test_valid_token_returns_200(self, mock_service, mock_settings):
        """Requests with the correct secret token must receive a 200 response."""
        mock_settings.WEBHOOK_SECRET_TOKEN = "correct-token"

        response = client.post(
            "/webhook/telegram",
            json=VALID_UPDATE,
            headers={"X-Telegram-Bot-Api-Secret-Token": "correct-token"},
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True

    @patch("app.api.webhook.settings")
    @patch("app.api.webhook.telegram_service")
    def test_no_secret_configured_returns_200(self, mock_service, mock_settings):
        """When no secret token is configured, any request should be accepted."""
        mock_settings.WEBHOOK_SECRET_TOKEN = None

        response = client.post(
            "/webhook/telegram",
            json=VALID_UPDATE,
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True
