"""
SSE Parser Unit Tests
"""

import pytest

from dify_assistant.exceptions import StreamingConnectionError, StreamingError
from dify_assistant.streaming.events import (
    ErrorEvent,
    MessageEndEvent,
    MessageEvent,
    PingEvent,
    WorkflowStartedEvent,
)
from dify_assistant.streaming.sse_parser import SSEParser


class MockSyncResponse:
    """Mock synchronous response for testing"""

    def __init__(self, lines: list[str]):
        self._lines = lines

    def iter_lines(self):
        for line in self._lines:
            yield line


class MockAsyncResponse:
    """Mock asynchronous response for testing"""

    def __init__(self, lines: list[str]):
        self._lines = lines

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class TestSSEParserInit:
    """SSEParser initialization tests"""

    def test_default_values(self):
        """Test default initialization values"""
        parser = SSEParser()
        assert parser.event_timeout == 60.0
        assert parser.max_reconnect_attempts == 3
        assert parser.last_event_id is None

    def test_custom_values(self):
        """Test custom initialization values"""
        parser = SSEParser(event_timeout=30.0, max_reconnect_attempts=5)
        assert parser.event_timeout == 30.0
        assert parser.max_reconnect_attempts == 5


class TestSSEParserParseEventLine:
    """SSEParser._parse_event_line tests"""

    def test_parse_event_type(self):
        """Test parsing event type line"""
        parser = SSEParser()
        field, value = parser._parse_event_line("event: message")
        assert field == "event"
        assert value == "message"

    def test_parse_data_line(self):
        """Test parsing data line"""
        parser = SSEParser()
        field, value = parser._parse_event_line('data: {"key": "value"}')
        assert field == "data"
        assert value == '{"key": "value"}'

    def test_parse_line_with_space_after_colon(self):
        """Test parsing line with space after colon"""
        parser = SSEParser()
        field, value = parser._parse_event_line("data:  extra space")
        assert field == "data"
        assert value == " extra space"  # Only first space is removed

    def test_parse_line_without_colon(self):
        """Test parsing line without colon"""
        parser = SSEParser()
        field, value = parser._parse_event_line("nocolon")
        assert field == "nocolon"
        assert value == ""


class TestSSEParserCreateEvent:
    """SSEParser._create_event tests"""

    def test_create_message_event(self):
        """Test creating message event"""
        parser = SSEParser()
        data = '{"event": "message", "answer": "Hello", "conversation_id": "123", "message_id": "456", "task_id": "789", "created_at": 1234567890}'
        event = parser._create_event("message", data)

        assert isinstance(event, MessageEvent)
        assert event.answer == "Hello"
        assert event.conversation_id == "123"

    def test_create_message_end_event(self):
        """Test creating message end event"""
        parser = SSEParser()
        data = '{"event": "message_end", "conversation_id": "123", "message_id": "456", "task_id": "789"}'
        event = parser._create_event("message_end", data)

        assert isinstance(event, MessageEndEvent)
        assert event.conversation_id == "123"

    def test_create_error_event(self):
        """Test creating error event"""
        parser = SSEParser()
        data = '{"event": "error", "message": "Something went wrong", "code": "internal_error", "status": 500, "task_id": "123", "message_id": "456"}'
        event = parser._create_event("error", data)

        assert isinstance(event, ErrorEvent)
        assert event.message == "Something went wrong"

    def test_create_ping_event(self):
        """Test creating ping event"""
        parser = SSEParser()
        event = parser._create_event("ping", "{}")

        assert isinstance(event, PingEvent)

    def test_unknown_event_type_returns_ping(self):
        """Test unknown event type returns PingEvent"""
        parser = SSEParser()
        event = parser._create_event("unknown_type", "{}")

        assert isinstance(event, PingEvent)

    def test_invalid_json_raises_error(self):
        """Test invalid JSON raises StreamingError"""
        parser = SSEParser()

        with pytest.raises(StreamingError, match="Failed to parse"):
            parser._create_event("message", "not valid json")


class TestSSEParserParseSync:
    """SSEParser.parse_sync tests"""

    def test_parse_single_event(self):
        """Test parsing single event"""
        parser = SSEParser()
        lines = [
            "event: message",
            'data: {"event": "message", "answer": "Hi", "conversation_id": "c1", "message_id": "m1", "task_id": "t1", "created_at": 1234567890}',
            "",
        ]
        response = MockSyncResponse(lines)

        events = list(parser.parse_sync(response))

        assert len(events) == 1
        assert isinstance(events[0], MessageEvent)
        assert events[0].answer == "Hi"

    def test_parse_multiple_events(self):
        """Test parsing multiple events"""
        parser = SSEParser()
        lines = [
            "event: message",
            'data: {"event": "message", "answer": "First", "conversation_id": "c1", "message_id": "m1", "task_id": "t1", "created_at": 1234567890}',
            "",
            "event: message",
            'data: {"event": "message", "answer": "Second", "conversation_id": "c1", "message_id": "m2", "task_id": "t1", "created_at": 1234567891}',
            "",
            "event: message_end",
            'data: {"event": "message_end", "conversation_id": "c1", "message_id": "m2", "task_id": "t1"}',
            "",
        ]
        response = MockSyncResponse(lines)

        events = list(parser.parse_sync(response))

        assert len(events) == 3
        assert events[0].answer == "First"
        assert events[1].answer == "Second"
        assert isinstance(events[2], MessageEndEvent)

    def test_parse_event_with_id(self):
        """Test parsing event with ID"""
        parser = SSEParser()
        lines = [
            "event: message",
            "id: event-001",
            'data: {"event": "message", "answer": "Test", "conversation_id": "c1", "message_id": "m1", "task_id": "t1", "created_at": 1234567890}',
            "",
        ]
        response = MockSyncResponse(lines)

        events = list(parser.parse_sync(response))

        assert len(events) == 1
        assert parser.last_event_id == "event-001"

    def test_parse_multiline_data(self):
        """Test parsing event without trailing empty line"""
        parser = SSEParser()
        lines = [
            "event: message",
            'data: {"event": "message", "answer": "No empty line", "conversation_id": "c1", "message_id": "m1", "task_id": "t1", "created_at": 1234567890}',
        ]
        response = MockSyncResponse(lines)

        events = list(parser.parse_sync(response))

        assert len(events) == 1
        assert events[0].answer == "No empty line"


class TestSSEParserParseAsync:
    """SSEParser.parse_async tests"""

    @pytest.mark.asyncio
    async def test_parse_single_event_async(self):
        """Test async parsing single event"""
        parser = SSEParser()
        lines = [
            "event: message",
            'data: {"event": "message", "answer": "Async Hi", "conversation_id": "c1", "message_id": "m1", "task_id": "t1", "created_at": 1234567890}',
            "",
        ]
        response = MockAsyncResponse(lines)

        events = []
        async for event in parser.parse_async(response):
            events.append(event)

        assert len(events) == 1
        assert isinstance(events[0], MessageEvent)
        assert events[0].answer == "Async Hi"

    @pytest.mark.asyncio
    async def test_parse_multiple_events_async(self):
        """Test async parsing multiple events"""
        parser = SSEParser()
        lines = [
            "event: workflow_started",
            'data: {"event": "workflow_started", "workflow_run_id": "w1", "task_id": "t1"}',
            "",
            "event: message",
            'data: {"event": "message", "answer": "Result", "conversation_id": "c1", "message_id": "m1", "task_id": "t1", "created_at": 1234567890}',
            "",
        ]
        response = MockAsyncResponse(lines)

        events = []
        async for event in parser.parse_async(response):
            events.append(event)

        assert len(events) == 2
        assert isinstance(events[0], WorkflowStartedEvent)
        assert isinstance(events[1], MessageEvent)

    @pytest.mark.asyncio
    async def test_parse_event_with_id_async(self):
        """Test async parsing event with ID"""
        parser = SSEParser()
        lines = [
            "event: message",
            "id: async-event-001",
            'data: {"event": "message", "answer": "With ID", "conversation_id": "c1", "message_id": "m1", "task_id": "t1", "created_at": 1234567890}',
            "",
        ]
        response = MockAsyncResponse(lines)

        events = []
        async for event in parser.parse_async(response):
            events.append(event)

        assert len(events) == 1
        assert parser.last_event_id == "async-event-001"


class TestSSEParserReset:
    """SSEParser.reset tests"""

    def test_reset_clears_state(self):
        """Test reset clears parser state"""
        parser = SSEParser()
        parser._last_event_id = "some-id"
        parser._reconnect_attempts = 5

        parser.reset()

        assert parser.last_event_id is None
        assert parser._reconnect_attempts == 0


class TestSSEParserEventTypes:
    """Test all event type parsing"""

    def test_all_event_types_have_models(self):
        """Test all defined event types have corresponding models"""
        expected_types = {
            "message",
            "message_end",
            "message_file",
            "message_replace",
            "agent_message",
            "agent_thought",
            "tts_message",
            "tts_message_end",
            "workflow_started",
            "workflow_finished",
            "node_started",
            "node_finished",
            "parallel_branch_started",
            "parallel_branch_finished",
            "error",
            "ping",
        }

        assert set(SSEParser.EVENT_MODELS.keys()) == expected_types
