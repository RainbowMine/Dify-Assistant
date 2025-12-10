"""
HTTP Client Unit Tests
"""

import pytest
from pydantic import SecretStr

from dify_assistant.client.base import (
    DifyClientConfig,
    build_headers,
    handle_error_response,
)
from dify_assistant.exceptions import (
    AuthenticationError,
    DifyAPIError,
    InvalidRequestError,
    NotFoundError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
)


class TestDifyClientConfig:
    """DifyClientConfig tests"""

    def test_basic_creation(self):
        """Test basic config creation"""
        config = DifyClientConfig(
            base_url="https://api.dify.ai/v1",
            api_key="app-xxx",
        )

        assert str(config.base_url) == "https://api.dify.ai/v1"
        assert isinstance(config.api_key, SecretStr)
        assert config.api_key.get_secret_value() == "app-xxx"
        assert config.timeout == 120.0

    def test_custom_timeout(self):
        """Test custom timeout"""
        config = DifyClientConfig(
            base_url="https://api.dify.ai/v1",
            api_key="app-xxx",
            timeout=60.0,
        )

        assert config.timeout == 60.0

    def test_base_url_str_removes_trailing_slash(self):
        """Test base_url_str removes trailing slash"""
        config = DifyClientConfig(
            base_url="https://api.dify.ai/v1/",
            api_key="app-xxx",
        )

        assert config.base_url_str == "https://api.dify.ai/v1"

    def test_base_url_str_without_trailing_slash(self):
        """Test base_url_str without trailing slash"""
        config = DifyClientConfig(
            base_url="https://api.dify.ai/v1",
            api_key="app-xxx",
        )

        assert config.base_url_str == "https://api.dify.ai/v1"

    def test_api_key_is_secret(self):
        """Test API key is stored as SecretStr"""
        config = DifyClientConfig(
            base_url="https://api.dify.ai/v1",
            api_key="super-secret-key",
        )

        # repr should not show the actual key
        repr_str = repr(config)
        assert "super-secret-key" not in repr_str
        assert "**********" in repr_str or "SecretStr" in repr_str

    def test_api_key_min_length(self):
        """Test API key minimum length validation"""
        with pytest.raises(Exception):  # ValidationError
            DifyClientConfig(
                base_url="https://api.dify.ai/v1",
                api_key="",
            )

    def test_timeout_must_be_positive(self):
        """Test timeout must be positive"""
        with pytest.raises(Exception):  # ValidationError
            DifyClientConfig(
                base_url="https://api.dify.ai/v1",
                api_key="app-xxx",
                timeout=0,
            )


class TestBuildHeaders:
    """build_headers function tests"""

    def test_basic_headers(self):
        """Test basic header building"""
        api_key = SecretStr("test-api-key")
        headers = build_headers(api_key)

        assert headers["Authorization"] == "Bearer test-api-key"
        assert headers["Content-Type"] == "application/json"

    def test_secret_str_value_extracted(self):
        """Test SecretStr value is properly extracted"""
        api_key = SecretStr("my-secret-token")
        headers = build_headers(api_key)

        assert "Bearer my-secret-token" == headers["Authorization"]


class TestHandleErrorResponse:
    """handle_error_response function tests"""

    def test_401_raises_authentication_error(self):
        """Test 401 raises AuthenticationError"""
        with pytest.raises(AuthenticationError) as exc_info:
            handle_error_response(401, {"message": "Invalid token"})

        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value)

    def test_404_raises_not_found_error(self):
        """Test 404 raises NotFoundError"""
        with pytest.raises(NotFoundError) as exc_info:
            handle_error_response(404, {"message": "Resource not found"})

        assert exc_info.value.status_code == 404

    def test_429_raises_rate_limit_error(self):
        """Test 429 raises RateLimitError"""
        with pytest.raises(RateLimitError) as exc_info:
            handle_error_response(429, {"message": "Too many requests", "retry_after": 60})

        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60

    def test_400_quota_exceeded_raises_quota_error(self):
        """Test 400 with quota_exceeded code raises QuotaExceededError"""
        with pytest.raises(QuotaExceededError) as exc_info:
            handle_error_response(400, {"message": "Quota exceeded", "code": "quota_exceeded"})

        assert exc_info.value.status_code == 400

    def test_400_with_quota_in_message_raises_quota_error(self):
        """Test 400 with 'quota' in message raises QuotaExceededError"""
        with pytest.raises(QuotaExceededError):
            handle_error_response(400, {"message": "Your quota has been exceeded"})

    def test_400_raises_invalid_request_error(self):
        """Test 400 raises InvalidRequestError"""
        with pytest.raises(InvalidRequestError) as exc_info:
            handle_error_response(400, {"message": "Invalid parameter", "code": "invalid_param"})

        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "invalid_param"

    def test_500_raises_server_error(self):
        """Test 500 raises ServerError"""
        with pytest.raises(ServerError) as exc_info:
            handle_error_response(500, {"message": "Internal error"})

        assert exc_info.value.status_code == 500

    def test_502_raises_server_error(self):
        """Test 502 raises ServerError"""
        with pytest.raises(ServerError) as exc_info:
            handle_error_response(502, {"message": "Bad gateway"})

        assert exc_info.value.status_code == 502

    def test_503_raises_server_error(self):
        """Test 503 raises ServerError"""
        with pytest.raises(ServerError) as exc_info:
            handle_error_response(503, {"message": "Service unavailable"})

        assert exc_info.value.status_code == 503

    def test_other_error_raises_dify_api_error(self):
        """Test other status codes raise DifyAPIError"""
        with pytest.raises(DifyAPIError) as exc_info:
            handle_error_response(418, {"message": "I'm a teapot", "code": "teapot"})

        assert exc_info.value.status_code == 418
        assert exc_info.value.error_code == "teapot"

    def test_empty_response_data(self):
        """Test handling empty response data"""
        with pytest.raises(DifyAPIError) as exc_info:
            handle_error_response(500, None)

        assert "Unknown error" in str(exc_info.value)

    def test_missing_message_uses_default(self):
        """Test missing message uses default"""
        with pytest.raises(DifyAPIError) as exc_info:
            handle_error_response(500, {})

        assert "Unknown error" in str(exc_info.value)
