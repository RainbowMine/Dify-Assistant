"""
Dify API Exception Classes

Layered exception design for fine-grained error handling by callers.
"""

from typing import Any, Optional


class DifyError(Exception):
    """
    Dify Base Exception

    Parent class for all Dify-related exceptions.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DifyAPIError(DifyError):
    """
    Dify API Error

    Represents an error response returned by the API.

    Attributes:
        message: Error message
        status_code: HTTP status code
        error_code: Dify API error code
        request_id: Request ID (if available)
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.request_id = request_id
        self.details = details or {}

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"status_code={self.status_code}")
        if self.error_code:
            parts.append(f"error_code={self.error_code}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return " | ".join(parts)


class AuthenticationError(DifyAPIError):
    """
    Authentication Error

    Raised when API key is invalid or missing.
    """

    def __init__(
        self,
        message: str = "Invalid or missing API key",
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code="authentication_error",
            request_id=request_id,
        )


class InvalidRequestError(DifyAPIError):
    """
    Invalid Request Error

    Raised when request parameters are invalid.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code=error_code or "invalid_request",
            request_id=request_id,
            details=details,
        )


class NotFoundError(DifyAPIError):
    """
    Resource Not Found Error

    Raised when the requested resource (conversation, message, etc.) does not exist.
    """

    def __init__(
        self,
        message: str = "Resource not found",
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=404,
            error_code="not_found",
            request_id=request_id,
        )


class ConversationNotFoundError(NotFoundError):
    """
    Conversation Not Found Error

    Raised when the specified conversation does not exist.
    """

    def __init__(
        self,
        conversation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        message = "Conversation not found"
        if conversation_id:
            message = f"Conversation not found: {conversation_id}"
        super().__init__(message=message, request_id=request_id)
        self.conversation_id = conversation_id


class MessageNotFoundError(NotFoundError):
    """
    Message Not Found Error

    Raised when the specified message does not exist.
    """

    def __init__(
        self,
        message_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        msg = "Message not found"
        if message_id:
            msg = f"Message not found: {message_id}"
        super().__init__(message=msg, request_id=request_id)
        self.message_id = message_id


class RateLimitError(DifyAPIError):
    """
    Rate Limit Error

    Raised when request frequency exceeds the limit.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=429,
            error_code="rate_limit_exceeded",
            request_id=request_id,
            details={"retry_after": retry_after} if retry_after else None,
        )
        self.retry_after = retry_after


class QuotaExceededError(DifyAPIError):
    """
    Quota Exceeded Error

    Raised when account quota is exhausted.
    """

    def __init__(
        self,
        message: str = "Quota exceeded",
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="quota_exceeded",
            request_id=request_id,
        )


class ServerError(DifyAPIError):
    """
    Server Error

    Raised when Dify server encounters an error.
    """

    def __init__(
        self,
        message: str = "Internal server error",
        status_code: int = 500,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            error_code="server_error",
            request_id=request_id,
        )


class ServiceUnavailableError(ServerError):
    """
    Service Unavailable Error

    Raised when the Dify service is temporarily unavailable (503).
    """

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        retry_after: Optional[int] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=503,
            request_id=request_id,
        )
        self.retry_after = retry_after


class GatewayTimeoutError(ServerError):
    """
    Gateway Timeout Error

    Raised when the server times out (504).
    """

    def __init__(
        self,
        message: str = "Gateway timeout",
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=504,
            request_id=request_id,
        )


class ValidationError(DifyError):
    """
    Data Validation Error

    Raised when local data validation fails (not an API error).
    """

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.field = field


class StreamingError(DifyError):
    """
    Streaming Error

    Raised when an error occurs during SSE streaming response processing.
    """

    def __init__(self, message: str, event_data: Optional[str] = None) -> None:
        super().__init__(message)
        self.event_data = event_data


class StreamingTimeoutError(StreamingError):
    """
    Streaming Timeout Error

    Raised when the SSE stream times out waiting for data.
    """

    def __init__(
        self,
        message: str = "Stream timeout waiting for data",
        timeout_seconds: Optional[float] = None,
    ) -> None:
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class StreamingConnectionError(StreamingError):
    """
    Streaming Connection Error

    Raised when the SSE stream connection is lost.
    """

    def __init__(
        self,
        message: str = "Stream connection lost",
        reconnect_attempts: int = 0,
    ) -> None:
        super().__init__(message)
        self.reconnect_attempts = reconnect_attempts


class ConfigurationError(DifyError):
    """
    Configuration Error

    Raised when there is an error in the configuration.
    """

    def __init__(self, message: str, config_key: Optional[str] = None) -> None:
        super().__init__(message)
        self.config_key = config_key


class FileUploadError(DifyAPIError):
    """
    File Upload Error

    Raised when file upload fails.
    """

    def __init__(
        self,
        message: str = "File upload failed",
        file_path: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="file_upload_error",
            request_id=request_id,
        )
        self.file_path = file_path


class FileTooLargeError(FileUploadError):
    """
    File Too Large Error

    Raised when the uploaded file exceeds the size limit.
    """

    def __init__(
        self,
        message: str = "File size exceeds limit",
        file_path: Optional[str] = None,
        max_size_bytes: Optional[int] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, file_path=file_path, request_id=request_id)
        self.max_size_bytes = max_size_bytes


class UnsupportedFileTypeError(FileUploadError):
    """
    Unsupported File Type Error

    Raised when the uploaded file type is not supported.
    """

    def __init__(
        self,
        message: str = "File type not supported",
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        supported_types: Optional[list[str]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, file_path=file_path, request_id=request_id)
        self.file_type = file_type
        self.supported_types = supported_types or []
