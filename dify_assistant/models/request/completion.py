"""
Completion API Request Model
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from dify_assistant.models.common import InputFile, ResponseMode


class CompletionRequest(BaseModel):
    """
    Text Generation Request

    Used for POST /completion-messages endpoint.

    Attributes:
        inputs: Application variable input (key-value pairs)
        response_mode: Response mode (blocking/streaming)
        user: User identifier
        files: File list (for multimodal)
    """

    inputs: dict[str, Any] = Field(..., description="Application variable input")
    response_mode: ResponseMode = Field(default=ResponseMode.STREAMING, description="Response mode")
    user: str = Field(..., min_length=1, description="User identifier")
    files: Optional[list[InputFile]] = Field(default=None, description="File list")

    def to_api_dict(self) -> dict[str, Any]:
        """
        Convert to API request dictionary

        Returns:
            Dictionary format suitable for sending to API
        """
        data: dict[str, Any] = {
            "inputs": self.inputs,
            "response_mode": self.response_mode.value,
            "user": self.user,
        }

        if self.files:
            data["files"] = [f.model_dump(exclude_none=True) for f in self.files]

        return data
