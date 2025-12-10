"""
Workflow API Wrapper

Provides workflow execution related API operations.
"""

from typing import Any, AsyncIterator, Iterator, Optional, Union

from dify_assistant.api.base import AsyncBaseAPI, SyncBaseAPI
from dify_assistant.models import (
    ResponseMode,
    StopRequest,
    StopResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from dify_assistant.streaming import StreamEvent


class AsyncWorkflowAPI(AsyncBaseAPI):
    """
    Asynchronous Workflow API

    Provides workflow execution functionality.

    Example:
        # Blocking mode
        response = await workflow.run(
            inputs={"query": "translate this", "target_lang": "English"},
            user="user-123",
            response_mode=ResponseMode.BLOCKING
        )
        print(response.data.outputs)

        # Streaming mode
        async for event in workflow.run(
            inputs={"query": "translate this"},
            user="user-123"
        ):
            print(event)
    """

    async def run(
        self,
        user: str,
        inputs: Optional[dict[str, Any]] = None,
        response_mode: ResponseMode = ResponseMode.STREAMING,
    ) -> Union[WorkflowRunResponse, AsyncIterator[StreamEvent]]:
        """
        Execute workflow

        Args:
            user: User identifier
            inputs: Workflow variable input
            response_mode: Response mode

        Returns:
            Blocking mode returns WorkflowRunResponse, streaming mode returns event iterator
        """
        request = WorkflowRunRequest(
            inputs=inputs or {},
            user=user,
            response_mode=response_mode,
        )

        if response_mode == ResponseMode.BLOCKING:
            data = await self._client.post("/workflows/run", json=request.to_api_dict())
            return WorkflowRunResponse.model_validate(data)

        return self._stream_workflow(request)

    async def _stream_workflow(self, request: WorkflowRunRequest) -> AsyncIterator[StreamEvent]:
        """Internal implementation for streaming workflow execution"""
        async for event in self._client.stream_post("/workflows/run", json=request.to_api_dict()):
            yield event

    async def stop(self, task_id: str, user: str) -> StopResponse:
        """
        Stop workflow execution

        Args:
            task_id: Task ID
            user: User identifier

        Returns:
            Stop response
        """
        request = StopRequest(user=user)
        data = await self._client.post(f"/workflows/tasks/{task_id}/stop", json=request.to_api_dict())
        return StopResponse.model_validate(data)


class SyncWorkflowAPI(SyncBaseAPI):
    """
    Synchronous Workflow API

    Provides workflow execution functionality.

    Example:
        # Blocking mode
        response = workflow.run(
            inputs={"query": "translate this", "target_lang": "English"},
            user="user-123",
            response_mode=ResponseMode.BLOCKING
        )
        print(response.data.outputs)

        # Streaming mode
        for event in workflow.run(
            inputs={"query": "translate this"},
            user="user-123"
        ):
            print(event)
    """

    def run(
        self,
        user: str,
        inputs: Optional[dict[str, Any]] = None,
        response_mode: ResponseMode = ResponseMode.STREAMING,
    ) -> Union[WorkflowRunResponse, Iterator[StreamEvent]]:
        """
        Execute workflow

        Args:
            user: User identifier
            inputs: Workflow variable input
            response_mode: Response mode

        Returns:
            Blocking mode returns WorkflowRunResponse, streaming mode returns event iterator
        """
        request = WorkflowRunRequest(
            inputs=inputs or {},
            user=user,
            response_mode=response_mode,
        )

        if response_mode == ResponseMode.BLOCKING:
            data = self._client.post("/workflows/run", json=request.to_api_dict())
            return WorkflowRunResponse.model_validate(data)

        return self._stream_workflow(request)

    def _stream_workflow(self, request: WorkflowRunRequest) -> Iterator[StreamEvent]:
        """Internal implementation for streaming workflow execution"""
        for event in self._client.stream_post("/workflows/run", json=request.to_api_dict()):
            yield event

    def stop(self, task_id: str, user: str) -> StopResponse:
        """
        Stop workflow execution

        Args:
            task_id: Task ID
            user: User identifier

        Returns:
            Stop response
        """
        request = StopRequest(user=user)
        data = self._client.post(f"/workflows/tasks/{task_id}/stop", json=request.to_api_dict())
        return StopResponse.model_validate(data)
