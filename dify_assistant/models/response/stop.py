"""
Stop API Response Model
"""

from pydantic import BaseModel, Field


class StopResponse(BaseModel):
    """
    Stop Generation Response

    Response for POST /chat-messages/{task_id}/stop or /workflows/tasks/{task_id}/stop endpoint.

    Attributes:
        result: Operation result
    """

    result: str = Field(..., description="Operation result")
