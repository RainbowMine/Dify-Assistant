"""
AsyncConsoleClient Unit Tests - Delete App Functionality
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from dify_assistant.cli.async_console_client import AsyncConsoleClient


@pytest.fixture
def mock_async_client():
    """Create a mock AsyncConsoleClient with login completed."""
    client = AsyncConsoleClient(
        base_url="https://api.dify.ai",
        email="test@example.com",
        password="test-password",
    )
    client._access_token = "test-token"
    client._csrf_token = "test-csrf"
    return client


class TestDeleteApp:
    """Tests for delete_app method"""

    @pytest.mark.asyncio
    async def test_delete_app_success(self, mock_async_client: AsyncConsoleClient):
        """Test successful app deletion"""
        with patch.object(mock_async_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {}

            result = await mock_async_client.delete_app("test-app-id")

            assert result is True
            mock_request.assert_called_once_with("DELETE", "/console/api/apps/test-app-id")

    @pytest.mark.asyncio
    async def test_delete_app_not_logged_in(self):
        """Test delete_app raises when not logged in"""
        client = AsyncConsoleClient(
            base_url="https://api.dify.ai",
            email="test@example.com",
            password="test-password",
        )

        with pytest.raises(RuntimeError, match="Not logged in"):
            await client.delete_app("test-app-id")

    @pytest.mark.asyncio
    async def test_delete_app_http_error(self, mock_async_client: AsyncConsoleClient):
        """Test delete_app propagates HTTP errors"""
        with patch.object(mock_async_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )

            with pytest.raises(httpx.HTTPStatusError):
                await mock_async_client.delete_app("nonexistent-app-id")


class TestDeleteAppsParallel:
    """Tests for delete_apps_parallel method"""

    @pytest.mark.asyncio
    async def test_delete_apps_parallel_success(self, mock_async_client: AsyncConsoleClient):
        """Test successful parallel app deletion"""
        with patch.object(mock_async_client, "delete_app", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True

            results = await mock_async_client.delete_apps_parallel(["app-1", "app-2", "app-3"])

            assert len(results) == 3
            assert all(success for _, success, _ in results)
            assert all(error is None for _, _, error in results)
            assert mock_delete.call_count == 3

    @pytest.mark.asyncio
    async def test_delete_apps_parallel_partial_failure(self, mock_async_client: AsyncConsoleClient):
        """Test parallel deletion with some failures"""
        async def mock_delete(app_id: str) -> bool:
            if app_id == "app-2":
                raise httpx.HTTPStatusError(
                    "Not Found",
                    request=MagicMock(),
                    response=MagicMock(status_code=404),
                )
            return True

        with patch.object(mock_async_client, "delete_app", side_effect=mock_delete):
            results = await mock_async_client.delete_apps_parallel(["app-1", "app-2", "app-3"])

            assert len(results) == 3

            # Check successful deletions
            app1_result = next(r for r in results if r[0] == "app-1")
            assert app1_result[1] is True
            assert app1_result[2] is None

            # Check failed deletion
            app2_result = next(r for r in results if r[0] == "app-2")
            assert app2_result[1] is False
            assert app2_result[2] is not None

            # Check another successful deletion
            app3_result = next(r for r in results if r[0] == "app-3")
            assert app3_result[1] is True
            assert app3_result[2] is None

    @pytest.mark.asyncio
    async def test_delete_apps_parallel_empty_list(self, mock_async_client: AsyncConsoleClient):
        """Test parallel deletion with empty list"""
        results = await mock_async_client.delete_apps_parallel([])
        assert results == []
