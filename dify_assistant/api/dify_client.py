"""
Dify Unified Client

Provides unified client entry point, integrating all API functionality.
"""

from typing import Any, Union

from pydantic import HttpUrl, SecretStr

from dify_assistant.api.chat import AsyncChatAPI, SyncChatAPI
from dify_assistant.api.completion import AsyncCompletionAPI, SyncCompletionAPI
from dify_assistant.api.conversation import AsyncConversationAPI, SyncConversationAPI
from dify_assistant.api.file import AsyncFileAPI, SyncFileAPI
from dify_assistant.api.workflow import AsyncWorkflowAPI, SyncWorkflowAPI
from dify_assistant.client import AsyncDifyClient, DifyClientConfig, SyncDifyClient
from dify_assistant.constants import DEFAULT_TIMEOUT


class DifyClient:
    """
    Dify Unified Client

    Unified entry point integrating all API functionality, supporting both synchronous and asynchronous operations.

    Example:
        # Create client
        client = DifyClient(
            base_url="https://api.dify.ai/v1",
            api_key="app-xxx"
        )

        # Synchronous usage
        response = client.chat.send_message(
            query="Hello",
            user="user-123",
            response_mode=ResponseMode.BLOCKING
        )

        # Asynchronous usage
        response = await client.async_chat.send_message(
            query="Hello",
            user="user-123"
        )

        # Close client
        client.close()
        await client.aclose()

    Attributes:
        chat: Synchronous Chat API
        completion: Synchronous Completion API
        workflow: Synchronous Workflow API
        conversation: Synchronous Conversation API
        file: Synchronous File API
        async_chat: Asynchronous Chat API
        async_completion: Asynchronous Completion API
        async_workflow: Asynchronous Workflow API
        async_conversation: Asynchronous Conversation API
        async_file: Asynchronous File API
    """

    def __init__(
        self,
        base_url: str,
        api_key: Union[str, SecretStr],
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Initialize Dify client

        Args:
            base_url: API base URL
            api_key: API key (str or SecretStr)
            timeout: Request timeout (seconds)
        """
        # Convert api_key to SecretStr if it's a plain string
        if isinstance(api_key, str):
            api_key = SecretStr(api_key)

        self.config = DifyClientConfig(
            base_url=HttpUrl(base_url),
            api_key=api_key,
            timeout=timeout,
        )

        # Create underlying clients
        self._sync_client = SyncDifyClient(self.config)
        self._async_client = AsyncDifyClient(self.config)

        # Synchronous API
        self.chat = SyncChatAPI(self._sync_client)
        self.completion = SyncCompletionAPI(self._sync_client)
        self.workflow = SyncWorkflowAPI(self._sync_client)
        self.conversation = SyncConversationAPI(self._sync_client)
        self.file = SyncFileAPI(self._sync_client)

        # Asynchronous API
        self.async_chat = AsyncChatAPI(self._async_client)
        self.async_completion = AsyncCompletionAPI(self._async_client)
        self.async_workflow = AsyncWorkflowAPI(self._async_client)
        self.async_conversation = AsyncConversationAPI(self._async_client)
        self.async_file = AsyncFileAPI(self._async_client)

    def close(self) -> None:
        """Close synchronous client connection"""
        self._sync_client.close()

    async def aclose(self) -> None:
        """Close asynchronous client connection"""
        await self._async_client.close()

    def __enter__(self) -> "DifyClient":
        """Synchronous context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Synchronous context manager exit"""
        self.close()

    async def __aenter__(self) -> "DifyClient":
        """Asynchronous context manager entry"""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Asynchronous context manager exit"""
        await self.aclose()
