"""
Chat API Wrapper

Provides chat-related API operations.
"""

from typing import Any, AsyncIterator, Iterator, Optional, Union

from dify_assistant.api.base import AsyncBaseAPI, SyncBaseAPI
from dify_assistant.models import (
    ChatMessageRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    Rating,
    ResponseMode,
    StopRequest,
    StopResponse,
)
from dify_assistant.streaming import StreamEvent


class AsyncChatAPI(AsyncBaseAPI):
    """
    Asynchronous Chat API

    Provides chat message sending, generation stopping, message feedback and other functions.

    Example:
        # Blocking mode
        response = await chat.send_message(
            query="Hello",
            user="user-123",
            response_mode=ResponseMode.BLOCKING
        )
        print(response.answer)

        # Streaming mode
        async for event in chat.send_message(
            query="Write a poem",
            user="user-123"
        ):
            print(event)
    """

    async def send_message(
        self,
        query: str,
        user: str,
        inputs: Optional[dict[str, Any]] = None,
        response_mode: ResponseMode = ResponseMode.STREAMING,
        conversation_id: Optional[str] = None,
        auto_generate_name: bool = True,
    ) -> Union[ChatResponse, AsyncIterator[StreamEvent]]:
        """
        Send chat message

        Args:
            query: User message content
            user: User identifier
            inputs: Application variable input
            response_mode: Response mode
            conversation_id: Conversation ID (empty creates new conversation)
            auto_generate_name: Whether to automatically generate conversation title

        Returns:
            Blocking mode returns ChatResponse, streaming mode returns event iterator
        """
        request = ChatMessageRequest(
            query=query,
            user=user,
            inputs=inputs or {},
            response_mode=response_mode,
            conversation_id=conversation_id,
            auto_generate_name=auto_generate_name,
        )

        if response_mode == ResponseMode.BLOCKING:
            data = await self._client.post("/chat-messages", json=request.to_api_dict())
            return ChatResponse.model_validate(data)

        return self._stream_message(request)

    async def _stream_message(self, request: ChatMessageRequest) -> AsyncIterator[StreamEvent]:
        """Internal implementation for streaming message sending"""
        async for event in self._client.stream_post("/chat-messages", json=request.to_api_dict()):
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
        data = await self._client.post(f"/chat-messages/{task_id}/stop", json=request.to_api_dict())
        return StopResponse.model_validate(data)

    async def send_feedback(
        self,
        message_id: str,
        rating: Rating,
        user: str,
    ) -> FeedbackResponse:
        """
        Send message feedback

        Args:
            message_id: Message ID
            rating: Rating
            user: User identifier

        Returns:
            Feedback response
        """
        request = FeedbackRequest(rating=rating, user=user)
        data = await self._client.post(f"/messages/{message_id}/feedbacks", json=request.to_api_dict())
        return FeedbackResponse.model_validate(data)


class SyncChatAPI(SyncBaseAPI):
    """
    Synchronous Chat API

    Provides chat message sending, generation stopping, message feedback and other functions.

    Example:
        # Blocking mode
        response = chat.send_message(
            query="Hello",
            user="user-123",
            response_mode=ResponseMode.BLOCKING
        )
        print(response.answer)

        # Streaming mode
        for event in chat.send_message(
            query="Write a poem",
            user="user-123"
        ):
            print(event)
    """

    def send_message(
        self,
        query: str,
        user: str,
        inputs: Optional[dict[str, Any]] = None,
        response_mode: ResponseMode = ResponseMode.STREAMING,
        conversation_id: Optional[str] = None,
        auto_generate_name: bool = True,
    ) -> Union[ChatResponse, Iterator[StreamEvent]]:
        """
        Send chat message

        Args:
            query: User message content
            user: User identifier
            inputs: Application variable input
            response_mode: Response mode
            conversation_id: Conversation ID (empty creates new conversation)
            auto_generate_name: Whether to automatically generate conversation title

        Returns:
            Blocking mode returns ChatResponse, streaming mode returns event iterator
        """
        request = ChatMessageRequest(
            query=query,
            user=user,
            inputs=inputs or {},
            response_mode=response_mode,
            conversation_id=conversation_id,
            auto_generate_name=auto_generate_name,
        )

        if response_mode == ResponseMode.BLOCKING:
            data = self._client.post("/chat-messages", json=request.to_api_dict())
            return ChatResponse.model_validate(data)

        return self._stream_message(request)

    def _stream_message(self, request: ChatMessageRequest) -> Iterator[StreamEvent]:
        """Internal implementation for streaming message sending"""
        for event in self._client.stream_post("/chat-messages", json=request.to_api_dict()):
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
        data = self._client.post(f"/chat-messages/{task_id}/stop", json=request.to_api_dict())
        return StopResponse.model_validate(data)

    def send_feedback(
        self,
        message_id: str,
        rating: Rating,
        user: str,
    ) -> FeedbackResponse:
        """
        Send message feedback

        Args:
            message_id: Message ID
            rating: Rating
            user: User identifier

        Returns:
            Feedback response
        """
        request = FeedbackRequest(rating=rating, user=user)
        data = self._client.post(f"/messages/{message_id}/feedbacks", json=request.to_api_dict())
        return FeedbackResponse.model_validate(data)
