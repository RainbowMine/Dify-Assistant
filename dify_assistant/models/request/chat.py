"""
Chat API Request Model
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from dify_assistant.models.common import InputFile, ResponseMode


class ChatMessageRequest(BaseModel):
    """
    Chat Message Request

    Used for POST /chat-messages endpoint.

    Attributes:
        query: User input message content
        inputs: Application variable input (key-value pairs)
        response_mode: Response mode (blocking/streaming)
        user: User identifier
        conversation_id: Conversation ID (empty creates new conversation)
        files: File list (for multimodal)
        auto_generate_name: Whether to automatically generate conversation title
    """

    query: str = Field(..., min_length=1, description="User input message content")
    inputs: dict[str, Any] = Field(default_factory=dict, description="Application variable input")
    response_mode: ResponseMode = Field(default=ResponseMode.STREAMING, description="Response mode")
    user: str = Field(..., min_length=1, description="User identifier")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID")
    files: Optional[list[InputFile]] = Field(default=None, description="File list")
    auto_generate_name: bool = Field(default=True, description="Whether to automatically generate conversation title")

    def to_api_dict(self) -> dict[str, Any]:
        """
        Convert to API request dictionary

        Returns:
            Dictionary format suitable for sending to API
        """
        data: dict[str, Any] = {
            "query": self.query,
            "inputs": self.inputs,
            "response_mode": self.response_mode.value,
            "user": self.user,
            "auto_generate_name": self.auto_generate_name,
        }

        if self.conversation_id:
            data["conversation_id"] = self.conversation_id

        if self.files:
            data["files"] = [f.model_dump(exclude_none=True) for f in self.files]

        return data
