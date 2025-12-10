"""
Exception Unit Tests
"""

import pytest

from dify_assistant.exceptions import (
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


class TestDifyError:
    """DifyError base class tests"""

    def test_basic_creation(self):
        """Test basic exception creation"""
        error = DifyError("Test error message")
        assert error.message == "Test error message"
        assert str(error) == "Test error message"

    def test_inheritance(self):
        """Test inheritance from Exception"""
        error = DifyError("Test")
        assert isinstance(error, Exception)


class TestDifyAPIError:
    """DifyAPIError tests"""

    def test_full_initialization(self):
        """Test full initialization with all parameters"""
        error = DifyAPIError(
            message="API Error",
            status_code=400,
            error_code="bad_request",
            request_id="req-123",
            details={"field": "value"},
        )

        assert error.message == "API Error"
        assert error.status_code == 400
        assert error.error_code == "bad_request"
        assert error.request_id == "req-123"
        assert error.details == {"field": "value"}

    def test_str_representation(self):
        """Test string representation"""
        error = DifyAPIError(
            message="Test",
            status_code=500,
            error_code="server_error",
            request_id="req-456",
        )

        error_str = str(error)
        assert "Test" in error_str
        assert "status_code=500" in error_str
        assert "error_code=server_error" in error_str
        assert "request_id=req-456" in error_str

    def test_minimal_initialization(self):
        """Test minimal initialization"""
        error = DifyAPIError(message="Minimal")
        assert error.message == "Minimal"
        assert error.status_code is None
        assert error.error_code is None
        assert error.request_id is None
        assert error.details == {}


class TestAuthenticationError:
    """AuthenticationError tests"""

    def test_default_message(self):
        """Test default error message"""
        error = AuthenticationError()
        assert "Invalid or missing API key" in error.message
        assert error.status_code == 401
        assert error.error_code == "authentication_error"

    def test_custom_message(self):
        """Test custom error message"""
        error = AuthenticationError(message="Token expired")
        assert error.message == "Token expired"
        assert error.status_code == 401


class TestInvalidRequestError:
    """InvalidRequestError tests"""

    def test_creation(self):
        """Test error creation"""
        error = InvalidRequestError(
            message="Invalid parameter",
            error_code="invalid_param",
            details={"param": "query"},
        )

        assert error.message == "Invalid parameter"
        assert error.status_code == 400
        assert error.error_code == "invalid_param"
        assert error.details == {"param": "query"}


class TestNotFoundError:
    """NotFoundError tests"""

    def test_default_message(self):
        """Test default error message"""
        error = NotFoundError()
        assert error.message == "Resource not found"
        assert error.status_code == 404
        assert error.error_code == "not_found"

    def test_custom_message(self):
        """Test custom error message"""
        error = NotFoundError(message="User not found")
        assert error.message == "User not found"


class TestConversationNotFoundError:
    """ConversationNotFoundError tests"""

    def test_with_conversation_id(self):
        """Test error with conversation ID"""
        error = ConversationNotFoundError(conversation_id="conv-123")
        assert "conv-123" in error.message
        assert error.conversation_id == "conv-123"
        assert error.status_code == 404

    def test_without_conversation_id(self):
        """Test error without conversation ID"""
        error = ConversationNotFoundError()
        assert error.message == "Conversation not found"
        assert error.conversation_id is None


class TestMessageNotFoundError:
    """MessageNotFoundError tests"""

    def test_with_message_id(self):
        """Test error with message ID"""
        error = MessageNotFoundError(message_id="msg-456")
        assert "msg-456" in error.message
        assert error.message_id == "msg-456"
        assert error.status_code == 404

    def test_without_message_id(self):
        """Test error without message ID"""
        error = MessageNotFoundError()
        assert error.message == "Message not found"
        assert error.message_id is None


class TestRateLimitError:
    """RateLimitError tests"""

    def test_with_retry_after(self):
        """Test error with retry_after"""
        error = RateLimitError(retry_after=60)
        assert error.status_code == 429
        assert error.retry_after == 60
        assert error.details == {"retry_after": 60}

    def test_without_retry_after(self):
        """Test error without retry_after"""
        error = RateLimitError()
        assert error.retry_after is None


class TestQuotaExceededError:
    """QuotaExceededError tests"""

    def test_creation(self):
        """Test error creation"""
        error = QuotaExceededError()
        assert error.status_code == 400
        assert error.error_code == "quota_exceeded"


class TestServerError:
    """ServerError tests"""

    def test_default_status_code(self):
        """Test default status code"""
        error = ServerError()
        assert error.status_code == 500
        assert error.error_code == "server_error"

    def test_custom_status_code(self):
        """Test custom status code"""
        error = ServerError(status_code=502, message="Bad gateway")
        assert error.status_code == 502


class TestServiceUnavailableError:
    """ServiceUnavailableError tests"""

    def test_creation(self):
        """Test error creation"""
        error = ServiceUnavailableError(retry_after=30)
        assert error.status_code == 503
        assert error.retry_after == 30


class TestGatewayTimeoutError:
    """GatewayTimeoutError tests"""

    def test_creation(self):
        """Test error creation"""
        error = GatewayTimeoutError()
        assert error.status_code == 504
        assert "Gateway timeout" in error.message


class TestValidationError:
    """ValidationError tests"""

    def test_with_field(self):
        """Test error with field"""
        error = ValidationError(message="Invalid email", field="email")
        assert error.message == "Invalid email"
        assert error.field == "email"

    def test_without_field(self):
        """Test error without field"""
        error = ValidationError(message="Validation failed")
        assert error.field is None


class TestStreamingError:
    """StreamingError tests"""

    def test_with_event_data(self):
        """Test error with event data"""
        error = StreamingError(message="Parse error", event_data='{"event": "test"}')
        assert error.message == "Parse error"
        assert error.event_data == '{"event": "test"}'

    def test_without_event_data(self):
        """Test error without event data"""
        error = StreamingError(message="Connection lost")
        assert error.event_data is None


class TestStreamingTimeoutError:
    """StreamingTimeoutError tests"""

    def test_with_timeout(self):
        """Test error with timeout"""
        error = StreamingTimeoutError(timeout_seconds=30.0)
        assert error.timeout_seconds == 30.0
        assert "timeout" in error.message.lower()

    def test_default_message(self):
        """Test default error message"""
        error = StreamingTimeoutError()
        assert "timeout" in error.message.lower()


class TestStreamingConnectionError:
    """StreamingConnectionError tests"""

    def test_with_reconnect_attempts(self):
        """Test error with reconnect attempts"""
        error = StreamingConnectionError(reconnect_attempts=3)
        assert error.reconnect_attempts == 3
        assert "connection" in error.message.lower()


class TestConfigurationError:
    """ConfigurationError tests"""

    def test_with_config_key(self):
        """Test error with config key"""
        error = ConfigurationError(message="Invalid config", config_key="api_key")
        assert error.message == "Invalid config"
        assert error.config_key == "api_key"


class TestFileUploadError:
    """FileUploadError tests"""

    def test_with_file_path(self):
        """Test error with file path"""
        error = FileUploadError(message="Upload failed", file_path="/tmp/file.txt")
        assert error.file_path == "/tmp/file.txt"
        assert error.status_code == 400
        assert error.error_code == "file_upload_error"


class TestFileTooLargeError:
    """FileTooLargeError tests"""

    def test_with_max_size(self):
        """Test error with max size"""
        error = FileTooLargeError(
            file_path="/tmp/large.zip",
            max_size_bytes=10485760,  # 10MB
        )
        assert error.max_size_bytes == 10485760
        assert error.file_path == "/tmp/large.zip"


class TestUnsupportedFileTypeError:
    """UnsupportedFileTypeError tests"""

    def test_with_supported_types(self):
        """Test error with supported types"""
        error = UnsupportedFileTypeError(
            file_type=".exe",
            supported_types=[".pdf", ".txt", ".doc"],
        )
        assert error.file_type == ".exe"
        assert error.supported_types == [".pdf", ".txt", ".doc"]


class TestExceptionHierarchy:
    """Exception hierarchy tests"""

    def test_api_errors_inherit_from_dify_error(self):
        """Test API errors inherit from DifyError"""
        assert issubclass(DifyAPIError, DifyError)
        assert issubclass(AuthenticationError, DifyAPIError)
        assert issubclass(InvalidRequestError, DifyAPIError)
        assert issubclass(NotFoundError, DifyAPIError)
        assert issubclass(RateLimitError, DifyAPIError)
        assert issubclass(QuotaExceededError, DifyAPIError)
        assert issubclass(ServerError, DifyAPIError)

    def test_not_found_subclasses(self):
        """Test NotFoundError subclasses"""
        assert issubclass(ConversationNotFoundError, NotFoundError)
        assert issubclass(MessageNotFoundError, NotFoundError)

    def test_server_error_subclasses(self):
        """Test ServerError subclasses"""
        assert issubclass(ServiceUnavailableError, ServerError)
        assert issubclass(GatewayTimeoutError, ServerError)

    def test_streaming_error_subclasses(self):
        """Test StreamingError subclasses"""
        assert issubclass(StreamingTimeoutError, StreamingError)
        assert issubclass(StreamingConnectionError, StreamingError)

    def test_file_upload_error_subclasses(self):
        """Test FileUploadError subclasses"""
        assert issubclass(FileTooLargeError, FileUploadError)
        assert issubclass(UnsupportedFileTypeError, FileUploadError)

    def test_can_catch_base_exception(self):
        """Test catching base exception catches all subclasses"""
        errors = [
            AuthenticationError(),
            InvalidRequestError("test"),
            NotFoundError(),
            ConversationNotFoundError(),
            ServerError(),
            StreamingError("test"),
        ]

        for error in errors:
            assert isinstance(error, DifyError)
