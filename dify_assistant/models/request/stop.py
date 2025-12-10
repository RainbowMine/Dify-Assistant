"""
Stop API Request Model
"""

from pydantic import BaseModel, Field


class StopRequest(BaseModel):
    """
    Stop Generation Request

    Used for POST /chat-messages/{task_id}/stop or /workflows/tasks/{task_id}/stop endpoint.

    Attributes:
        user: User identifier
    """

    user: str = Field(..., min_length=1, description="User identifier")

    def to_api_dict(self) -> dict[str, str]:
        """
        Convert to API request dictionary

        Returns:
            Dictionary format suitable for sending to API
        """
        return {
            "user": self.user,
        }
