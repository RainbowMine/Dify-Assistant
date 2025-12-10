"""
Conversation API Wrapper

Provides conversation management related API operations.
"""

from typing import Any, List, Optional

from dify_assistant.api.base import AsyncBaseAPI, SyncBaseAPI
from dify_assistant.models import ConversationInfo, MessageInfo


class AsyncConversationAPI(AsyncBaseAPI):
    """
    Asynchronous Conversation API

    Provides conversation list, message history, conversation management and other functions.

    Example:
        # Get conversation list
        conversations = await conversation.list(user="user-123")

        # Get message history
        messages = await conversation.get_messages(
            conversation_id="conv-xxx",
            user="user-123"
        )

        # Delete conversation
        await conversation.delete(
            conversation_id="conv-xxx",
            user="user-123"
        )
    """

    async def list(
        self,
        user: str,
        last_id: Optional[str] = None,
        limit: int = 20,
        sort_by: str = "-updated_at",
    ) -> List[ConversationInfo]:
        """
        Get conversation list

        Args:
            user: User identifier
            last_id: ID of the last record from previous page (for pagination)
            limit: Number of records per page
            sort_by: Sort field (default descending by update time)

        Returns:
            Conversation list
        """
        params: dict[str, Any] = {
            "user": user,
            "limit": limit,
            "sort_by": sort_by,
        }
        if last_id:
            params["last_id"] = last_id

        data = await self._client.get("/conversations", params=params)
        conversations = data.get("data", [])
        return [ConversationInfo.model_validate(c) for c in conversations]

    async def get_messages(
        self,
        conversation_id: str,
        user: str,
        first_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[MessageInfo]:
        """
        Get conversation message history

        Args:
            conversation_id: Conversation ID
            user: User identifier
            first_id: First message ID (for pagination)
            limit: Number of records per page

        Returns:
            Message list
        """
        params: dict[str, Any] = {
            "user": user,
            "conversation_id": conversation_id,
            "limit": limit,
        }
        if first_id:
            params["first_id"] = first_id

        data = await self._client.get("/messages", params=params)
        messages = data.get("data", [])
        return [MessageInfo.model_validate(m) for m in messages]

    async def delete(self, conversation_id: str, user: str) -> bool:
        """
        Delete conversation

        Args:
            conversation_id: Conversation ID
            user: User identifier

        Returns:
            Whether deletion was successful
        """
        data = await self._client.delete(
            f"/conversations/{conversation_id}",
            params={"user": user},
        )
        return data.get("result") == "success"

    async def rename(
        self,
        conversation_id: str,
        name: str,
        user: str,
        auto_generate: bool = False,
    ) -> ConversationInfo:
        """
        Rename conversation

        Args:
            conversation_id: Conversation ID
            name: New name
            user: User identifier
            auto_generate: Whether to auto-generate name

        Returns:
            Updated conversation information
        """
        data = await self._client.post(
            f"/conversations/{conversation_id}/name",
            json={
                "name": name,
                "user": user,
                "auto_generate": auto_generate,
            },
        )
        return ConversationInfo.model_validate(data)


class SyncConversationAPI(SyncBaseAPI):
    """
    Synchronous Conversation API

    Provides conversation list, message history, conversation management and other functions.

    Example:
        # Get conversation list
        conversations = conversation.list(user="user-123")

        # Get message history
        messages = conversation.get_messages(
            conversation_id="conv-xxx",
            user="user-123"
        )

        # Delete conversation
        conversation.delete(
            conversation_id="conv-xxx",
            user="user-123"
        )
    """

    def list(
        self,
        user: str,
        last_id: Optional[str] = None,
        limit: int = 20,
        sort_by: str = "-updated_at",
    ) -> List[ConversationInfo]:
        """
        Get conversation list

        Args:
            user: User identifier
            last_id: ID of the last record from previous page (for pagination)
            limit: Number of records per page
            sort_by: Sort field (default descending by update time)

        Returns:
            Conversation list
        """
        params: dict[str, Any] = {
            "user": user,
            "limit": limit,
            "sort_by": sort_by,
        }
        if last_id:
            params["last_id"] = last_id

        data = self._client.get("/conversations", params=params)
        conversations = data.get("data", [])
        return [ConversationInfo.model_validate(c) for c in conversations]

    def get_messages(
        self,
        conversation_id: str,
        user: str,
        first_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[MessageInfo]:
        """
        Get conversation message history

        Args:
            conversation_id: Conversation ID
            user: User identifier
            first_id: First message ID (for pagination)
            limit: Number of records per page

        Returns:
            Message list
        """
        params: dict[str, Any] = {
            "user": user,
            "conversation_id": conversation_id,
            "limit": limit,
        }
        if first_id:
            params["first_id"] = first_id

        data = self._client.get("/messages", params=params)
        messages = data.get("data", [])
        return [MessageInfo.model_validate(m) for m in messages]

    def delete(self, conversation_id: str, user: str) -> bool:
        """
        Delete conversation

        Args:
            conversation_id: Conversation ID
            user: User identifier

        Returns:
            Whether deletion was successful
        """
        data = self._client.delete(
            f"/conversations/{conversation_id}",
            params={"user": user},
        )
        return data.get("result") == "success"

    def rename(
        self,
        conversation_id: str,
        name: str,
        user: str,
        auto_generate: bool = False,
    ) -> ConversationInfo:
        """
        Rename conversation

        Args:
            conversation_id: Conversation ID
            name: New name
            user: User identifier
            auto_generate: Whether to auto-generate name

        Returns:
            Updated conversation information
        """
        data = self._client.post(
            f"/conversations/{conversation_id}/name",
            json={
                "name": name,
                "user": user,
                "auto_generate": auto_generate,
            },
        )
        return ConversationInfo.model_validate(data)
