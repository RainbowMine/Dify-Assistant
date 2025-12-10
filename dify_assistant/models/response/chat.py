"""
Chat API Response Model
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from dify_assistant.models.common import RetrieverResource, Usage


class ResponseMetadata(BaseModel):
    """
    Response Metadata

    Attributes:
        usage: Token usage
        retriever_resources: Knowledge base retrieval resource list
    """

    usage: Optional[Usage] = None
    retriever_resources: Optional[list[RetrieverResource]] = None


class ChatResponse(BaseModel):
    """
    Chat Response (Blocking Mode)

    Blocking mode response for POST /chat-messages endpoint.

    Attributes:
        message_id: Unique message ID
        conversation_id: Conversation ID
        mode: Application mode
        answer: AI reply content
        metadata: Metadata
        created_at: Creation timestamp
    """

    message_id: str = Field(..., description="Unique message ID")
    conversation_id: str = Field(..., description="Conversation ID")
    mode: str = Field(..., description="Application mode")
    answer: str = Field(..., description="AI reply content")
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata, description="Metadata")
    created_at: int = Field(..., description="Creation timestamp")


class MessageInfo(BaseModel):
    """
    Message Information

    Used for message list API.

    Attributes:
        id: Message ID
        conversation_id: Conversation ID
        inputs: Input variables
        query: User message
        answer: AI reply
        message_files: Message files
        feedback: Feedback information
        retriever_resources: Retrieval resources
        created_at: Creation timestamp
    """

    id: str
    conversation_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    query: str
    answer: str
    message_files: list[dict[str, Any]] = Field(default_factory=list)
    feedback: Optional[dict[str, Any]] = None
    retriever_resources: Optional[list[RetrieverResource]] = None
    created_at: int


class ConversationInfo(BaseModel):
    """
    Conversation Information

    Used for conversation list API.

    Attributes:
        id: Conversation ID
        name: Conversation name
        inputs: Input variables
        status: Conversation status
        introduction: Introduction
        created_at: Creation timestamp
        updated_at: Update timestamp
    """

    id: str
    name: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    status: str
    introduction: str = ""
    created_at: int
    updated_at: int
