"""
SSE Parser

Parses Server-Sent Events streaming responses.
"""

import asyncio
import json
from typing import Any, AsyncIterator, Iterator, Optional

import httpx
from loguru import logger
from pydantic import BaseModel

from dify_assistant.exceptions import (
    StreamingConnectionError,
    StreamingError,
    StreamingTimeoutError,
)
from dify_assistant.streaming.events import (
    AgentMessageEvent,
    AgentThoughtEvent,
    ErrorEvent,
    MessageEndEvent,
    MessageEvent,
    MessageFileEvent,
    MessageReplaceEvent,
    NodeFinishedEvent,
    NodeStartedEvent,
    ParallelBranchFinishedEvent,
    ParallelBranchStartedEvent,
    PingEvent,
    StreamEvent,
    TtsMessageEndEvent,
    TtsMessageEvent,
    WorkflowFinishedEvent,
    WorkflowStartedEvent,
)


class SSEParser:
    """
    SSE Streaming Response Parser

    Parses text/event-stream format responses and converts them to typed event objects.

    Attributes:
        event_timeout: Timeout in seconds to wait for the next event (default: 60.0)
        max_reconnect_attempts: Maximum number of reconnection attempts (default: 3)

    Example:
        async with client.stream("POST", url, json=data) as response:
            parser = SSEParser(event_timeout=30.0)
            async for event in parser.parse_async(response):
                if event.event == StreamEventType.MESSAGE:
                    print(event.answer, end="")
    """

    # Mapping of event types to model classes
    EVENT_MODELS: dict[str, type[BaseModel]] = {
        "message": MessageEvent,
        "message_end": MessageEndEvent,
        "message_file": MessageFileEvent,
        "message_replace": MessageReplaceEvent,
        "agent_message": AgentMessageEvent,
        "agent_thought": AgentThoughtEvent,
        "tts_message": TtsMessageEvent,
        "tts_message_end": TtsMessageEndEvent,
        "workflow_started": WorkflowStartedEvent,
        "workflow_finished": WorkflowFinishedEvent,
        "node_started": NodeStartedEvent,
        "node_finished": NodeFinishedEvent,
        "parallel_branch_started": ParallelBranchStartedEvent,
        "parallel_branch_finished": ParallelBranchFinishedEvent,
        "error": ErrorEvent,
        "ping": PingEvent,
    }

    def __init__(
        self,
        event_timeout: float = 60.0,
        max_reconnect_attempts: int = 3,
    ) -> None:
        """
        Initialize SSE parser.

        Args:
            event_timeout: Timeout in seconds to wait for the next event
            max_reconnect_attempts: Maximum number of reconnection attempts
        """
        self.event_timeout = event_timeout
        self.max_reconnect_attempts = max_reconnect_attempts
        self._last_event_id: Optional[str] = None
        self._reconnect_attempts = 0

    def _parse_event_line(self, line: str) -> tuple[str, str]:
        """
        Parse single SSE data line

        Args:
            line: SSE data line

        Returns:
            (field_name, field_value) tuple
        """
        if ":" in line:
            field, _, value = line.partition(":")
            # SSE spec: space after colon should be ignored
            if value.startswith(" "):
                value = value[1:]
            return field, value
        return line, ""

    def _create_event(self, event_type: str, data: str) -> StreamEvent:
        """
        Create corresponding event object based on event type

        Args:
            event_type: Event type string
            data: JSON data string

        Returns:
            Typed event object

        Raises:
            StreamingError: When parsing fails
        """
        try:
            # Parse JSON data
            event_data: dict[str, Any]
            if data:
                event_data = json.loads(data)
            else:
                event_data = {}

            # Get corresponding model class
            model_class = self.EVENT_MODELS.get(event_type)
            if model_class:
                # Type-safe return, all classes in EVENT_MODELS are StreamEvent subtypes
                result: StreamEvent = model_class.model_validate(event_data)  # type: ignore[assignment]
                return result

            # Unknown event type, try to get event field from data
            if "event" in event_data:
                actual_type = event_data["event"]
                model_class = self.EVENT_MODELS.get(actual_type)
                if model_class:
                    result = model_class.model_validate(event_data)  # type: ignore[assignment]
                    return result

            # Default to ping event
            logger.debug("Unknown event type '{}', returning PingEvent", event_type)
            return PingEvent()

        except json.JSONDecodeError as e:
            logger.error("Failed to parse SSE event JSON: {}", e)
            raise StreamingError(f"Failed to parse event data: {e}", event_data=data) from e
        except Exception as e:
            logger.error("Failed to create SSE event: {}", e)
            raise StreamingError(f"Failed to create event: {e}", event_data=data) from e

    async def parse_async(self, response: httpx.Response) -> AsyncIterator[StreamEvent]:
        """
        Asynchronously parse SSE response stream

        Args:
            response: httpx response object

        Yields:
            Parsed event objects

        Raises:
            StreamingError: When parsing fails
            StreamingTimeoutError: When waiting for event times out
            StreamingConnectionError: When connection is lost
        """
        event_type = ""
        event_id = ""
        data_lines: list[str] = []

        try:
            async for line in self._iter_lines_with_timeout(response):
                line = line.strip()

                # Empty line indicates end of event
                if not line:
                    if data_lines:
                        data = "\n".join(data_lines)
                        if event_id:
                            self._last_event_id = event_id
                        yield self._create_event(event_type or "message", data)
                        event_type = ""
                        event_id = ""
                        data_lines = []
                        self._reconnect_attempts = 0  # Reset on successful event
                    continue

                # Parse field
                field, value = self._parse_event_line(line)

                if field == "event":
                    event_type = value
                elif field == "data":
                    data_lines.append(value)
                elif field == "id":
                    event_id = value
                # Ignore other fields (retry, comment, etc.)

            # Process last event (if no empty line at end)
            if data_lines:
                data = "\n".join(data_lines)
                yield self._create_event(event_type or "message", data)

        except asyncio.TimeoutError as e:
            logger.error("SSE stream timeout after {}s", self.event_timeout)
            raise StreamingTimeoutError(
                message=f"Stream timeout waiting for data after {self.event_timeout}s",
                timeout_seconds=self.event_timeout,
            ) from e
        except httpx.ReadError as e:
            self._reconnect_attempts += 1
            logger.error(
                "SSE stream connection error (attempt {}/{}): {}",
                self._reconnect_attempts,
                self.max_reconnect_attempts,
                e,
            )
            raise StreamingConnectionError(
                message=f"Stream connection lost: {e}",
                reconnect_attempts=self._reconnect_attempts,
            ) from e

    async def _iter_lines_with_timeout(self, response: httpx.Response) -> AsyncIterator[str]:
        """
        Iterate over response lines with timeout.

        Args:
            response: httpx response object

        Yields:
            Lines from the response

        Raises:
            asyncio.TimeoutError: When timeout is exceeded
        """
        async for line in response.aiter_lines():
            yield line

    def parse_sync(self, response: httpx.Response) -> Iterator[StreamEvent]:
        """
        Synchronously parse SSE response stream

        Args:
            response: httpx response object

        Yields:
            Parsed event objects

        Raises:
            StreamingError: When parsing fails
            StreamingConnectionError: When connection is lost
        """
        event_type = ""
        event_id = ""
        data_lines: list[str] = []

        try:
            for line in response.iter_lines():
                line = line.strip()

                # Empty line indicates end of event
                if not line:
                    if data_lines:
                        data = "\n".join(data_lines)
                        if event_id:
                            self._last_event_id = event_id
                        yield self._create_event(event_type or "message", data)
                        event_type = ""
                        event_id = ""
                        data_lines = []
                        self._reconnect_attempts = 0  # Reset on successful event
                    continue

                # Parse field
                field, value = self._parse_event_line(line)

                if field == "event":
                    event_type = value
                elif field == "data":
                    data_lines.append(value)
                elif field == "id":
                    event_id = value

            # Process last event
            if data_lines:
                data = "\n".join(data_lines)
                yield self._create_event(event_type or "message", data)

        except httpx.ReadError as e:
            self._reconnect_attempts += 1
            logger.error(
                "SSE stream connection error (attempt {}/{}): {}",
                self._reconnect_attempts,
                self.max_reconnect_attempts,
                e,
            )
            raise StreamingConnectionError(
                message=f"Stream connection lost: {e}",
                reconnect_attempts=self._reconnect_attempts,
            ) from e

    @property
    def last_event_id(self) -> Optional[str]:
        """
        Get the last received event ID.

        This can be used for reconnection to resume from the last event.

        Returns:
            The last event ID, or None if no events have been received
        """
        return self._last_event_id

    def reset(self) -> None:
        """
        Reset the parser state.

        Clears the last event ID and reconnect attempt counter.
        """
        self._last_event_id = None
        self._reconnect_attempts = 0
