"""
Dify API Exception Module

Provides unified exception handling mechanisms.
"""

from dify_assistant.exceptions.errors import (
    AuthenticationError,
    ConfigurationError,
    ConversationNotFoundError,
    DifyAPIError,
    DifyError,
    FileTooLargeError,
    FileUploadError,
    GatewayTimeoutError,
    InvalidRequestError,
    MessageNotFoundError,
    NotFoundError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    StreamingConnectionError,
    StreamingError,
    StreamingTimeoutError,
    UnsupportedFileTypeError,
    ValidationError,
)

__all__ = [
    "AuthenticationError",
    "ConfigurationError",
    "ConversationNotFoundError",
    "DifyAPIError",
    "DifyError",
    "FileTooLargeError",
    "FileUploadError",
    "GatewayTimeoutError",
    "InvalidRequestError",
    "MessageNotFoundError",
    "NotFoundError",
    "QuotaExceededError",
    "RateLimitError",
    "ServerError",
    "ServiceUnavailableError",
    "StreamingConnectionError",
    "StreamingError",
    "StreamingTimeoutError",
    "UnsupportedFileTypeError",
    "ValidationError",
]
