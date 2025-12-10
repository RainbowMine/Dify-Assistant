"""
Completion API Wrapper

Provides text generation related API operations.
"""

from typing import Any, AsyncIterator, Iterator, Union

from dify_assistant.api.base import AsyncBaseAPI, SyncBaseAPI
from dify_assistant.models import (
    CompletionRequest,
    CompletionResponse,
    ResponseMode,
    StopRequest,
    StopResponse,
)
from dify_assistant.streaming import StreamEvent


class AsyncCompletionAPI(AsyncBaseAPI):
    """
    Asynchronous Completion API

    Provides text generation functionality.

    Example:
        # Blocking mode
        response = await completion.create(
            inputs={"topic": "artificial intelligence"},
            user="user-123",
            response_mode=ResponseMode.BLOCKING
        )
        print(response.answer)

        # Streaming mode
        async for event in completion.create(
            inputs={"topic": "artificial intelligence"},
            user="user-123"
        ):
            print(event)
    """

    async def create(
        self,
        inputs: dict[str, Any],
        user: str,
        response_mode: ResponseMode = ResponseMode.STREAMING,
    ) -> Union[CompletionResponse, AsyncIterator[StreamEvent]]:
        """
        Create text generation

        Args:
            inputs: Application variable input
            user: User identifier
            response_mode: Response mode

        Returns:
            Blocking mode returns CompletionResponse, streaming mode returns event iterator
        """
        request = CompletionRequest(
            inputs=inputs,
            user=user,
            response_mode=response_mode,
        )

        if response_mode == ResponseMode.BLOCKING:
            data = await self._client.post("/completion-messages", json=request.to_api_dict())
            return CompletionResponse.model_validate(data)

        return self._stream_completion(request)

    async def _stream_completion(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]:
        """Internal implementation for streaming generation"""
        async for event in self._client.stream_post("/completion-messages", json=request.to_api_dict()):
            yield event

    async def stop_generation(self, task_id: str, user: str) -> StopResponse:
        """
        Stop generation

        Args:
            task_id: Task ID
            user: User identifier

        Returns:
            Stop response
        """
        request = StopRequest(user=user)
        data = await self._client.post(f"/completion-messages/{task_id}/stop", json=request.to_api_dict())
        return StopResponse.model_validate(data)


class SyncCompletionAPI(SyncBaseAPI):
    """
    Synchronous Completion API

    Provides text generation functionality.

    Example:
        # Blocking mode
        response = completion.create(
            inputs={"topic": "artificial intelligence"},
            user="user-123",
            response_mode=ResponseMode.BLOCKING
        )
        print(response.answer)

        # Streaming mode
        for event in completion.create(
            inputs={"topic": "artificial intelligence"},
            user="user-123"
        ):
            print(event)
    """

    def create(
        self,
        inputs: dict[str, Any],
        user: str,
        response_mode: ResponseMode = ResponseMode.STREAMING,
    ) -> Union[CompletionResponse, Iterator[StreamEvent]]:
        """
        Create text generation

        Args:
            inputs: Application variable input
            user: User identifier
            response_mode: Response mode

        Returns:
            Blocking mode returns CompletionResponse, streaming mode returns event iterator
        """
        request = CompletionRequest(
            inputs=inputs,
            user=user,
            response_mode=response_mode,
        )

        if response_mode == ResponseMode.BLOCKING:
            data = self._client.post("/completion-messages", json=request.to_api_dict())
            return CompletionResponse.model_validate(data)

        return self._stream_completion(request)

    def _stream_completion(self, request: CompletionRequest) -> Iterator[StreamEvent]:
        """Internal implementation for streaming generation"""
        for event in self._client.stream_post("/completion-messages", json=request.to_api_dict()):
            yield event

    def stop_generation(self, task_id: str, user: str) -> StopResponse:
        """
        Stop generation

        Args:
            task_id: Task ID
            user: User identifier

        Returns:
            Stop response
        """
        request = StopRequest(user=user)
        data = self._client.post(f"/completion-messages/{task_id}/stop", json=request.to_api_dict())
        return StopResponse.model_validate(data)
