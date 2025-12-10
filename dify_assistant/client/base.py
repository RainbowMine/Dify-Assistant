"""
HTTP Client Base Configuration
"""

from typing import Any, Optional

from loguru import logger
from pydantic import BaseModel, Field, HttpUrl, SecretStr

from dify_assistant.constants import (
    DEFAULT_TIMEOUT,
    HTTP_BAD_REQUEST,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_NOT_FOUND,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_UNAUTHORIZED,
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


class DifyClientConfig(BaseModel):
    """
    Dify Client Configuration

    Attributes:
        base_url: API base URL
        api_key: API key (stored securely using SecretStr)
        timeout: Request timeout (seconds)

    Security:
        The api_key is stored using Pydantic's SecretStr type to prevent
        accidental exposure in logs, repr(), or serialization.
    """

    base_url: HttpUrl = Field(..., description="API base URL")
    api_key: SecretStr = Field(..., min_length=1, description="API key (stored securely)")
    timeout: float = Field(default=DEFAULT_TIMEOUT, gt=0, description="Request timeout (seconds)")

    @property
    def base_url_str(self) -> str:
        """Get base_url as string"""
        url = str(self.base_url)
        # Ensure no trailing slash
        return url.rstrip("/")


def build_headers(api_key: SecretStr) -> dict[str, str]:
    """
    Build request headers

    Args:
        api_key: API key (SecretStr for security)

    Returns:
        Request headers dictionary
    """
    return {
        "Authorization": f"Bearer {api_key.get_secret_value()}",
        "Content-Type": "application/json",
    }


def handle_error_response(status_code: int, response_data: Optional[dict[str, Any]] = None) -> None:
    """
    Handle error response

    Args:
        status_code: HTTP status code
        response_data: Response data

    Raises:
        DifyAPIError: Corresponding exception type
    """
    response_data = response_data or {}
    message = response_data.get("message", "Unknown error")
    error_code = response_data.get("code", "")

    logger.error(
        "API error response: status_code={}, error_code={}, message={}",
        status_code,
        error_code,
        message,
    )

    if status_code == HTTP_UNAUTHORIZED:
        raise AuthenticationError(message=message)

    if status_code == HTTP_NOT_FOUND:
        raise NotFoundError(message=message)

    if status_code == HTTP_TOO_MANY_REQUESTS:
        retry_after = response_data.get("retry_after")
        raise RateLimitError(message=message, retry_after=retry_after)

    if status_code == HTTP_BAD_REQUEST:
        # Check if it's a quota exceeded error
        if error_code == "quota_exceeded" or "quota" in message.lower():
            raise QuotaExceededError(message=message)
        raise InvalidRequestError(message=message, error_code=error_code, details=response_data)

    if status_code >= HTTP_INTERNAL_SERVER_ERROR:
        raise ServerError(message=message, status_code=status_code)

    # Other errors
    raise DifyAPIError(
        message=message,
        status_code=status_code,
        error_code=error_code,
        details=response_data,
    )
