"""
ConsoleClient Unit Tests - Delete App Functionality
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from dify_assistant.cli.console_client import ConsoleClient


@pytest.fixture
def mock_client():
    """Create a mock ConsoleClient with login completed."""
    client = ConsoleClient(
        base_url="https://api.dify.ai",
        email="test@example.com",
        password="test-password",
    )
    client._access_token = "test-token"
    client._csrf_token = "test-csrf"
    return client


class TestDeleteApp:
    """Tests for delete_app method"""

    def test_delete_app_success(self, mock_client: ConsoleClient):
        """Test successful app deletion"""
        with patch.object(mock_client, "_request") as mock_request:
            mock_request.return_value = {}

            result = mock_client.delete_app("test-app-id")

            assert result is True
            mock_request.assert_called_once_with("DELETE", "/console/api/apps/test-app-id")

    def test_delete_app_not_logged_in(self):
        """Test delete_app raises when not logged in"""
        client = ConsoleClient(
            base_url="https://api.dify.ai",
            email="test@example.com",
            password="test-password",
        )

        with pytest.raises(RuntimeError, match="Not logged in"):
            client.delete_app("test-app-id")

    def test_delete_app_http_error(self, mock_client: ConsoleClient):
        """Test delete_app propagates HTTP errors"""
        with patch.object(mock_client, "_request") as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )

            with pytest.raises(httpx.HTTPStatusError):
                mock_client.delete_app("nonexistent-app-id")
