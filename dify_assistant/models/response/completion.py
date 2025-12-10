"""
Completion API Response Model
"""

from typing import Optional

from pydantic import BaseModel, Field

from dify_assistant.models.common import RetrieverResource, Usage


class CompletionMetadata(BaseModel):
    """
    Text Generation Response Metadata

    Attributes:
        usage: Token usage
        retriever_resources: Knowledge base retrieval resource list
    """

    usage: Optional[Usage] = None
    retriever_resources: Optional[list[RetrieverResource]] = None


class CompletionResponse(BaseModel):
    """
    Text Generation Response (Blocking Mode)

    Blocking mode response for POST /completion-messages endpoint.

    Attributes:
        message_id: Unique message ID
        mode: Application mode
        answer: Generated text content
        metadata: Metadata
        created_at: Creation timestamp
    """

    message_id: str = Field(..., description="Unique message ID")
    mode: str = Field(..., description="Application mode")
    answer: str = Field(..., description="Generated text content")
    metadata: CompletionMetadata = Field(default_factory=CompletionMetadata, description="Metadata")
    created_at: int = Field(..., description="Creation timestamp")
