"""
Feedback API Response Model
"""

from pydantic import BaseModel, Field


class FeedbackResponse(BaseModel):
    """
    Message Feedback Response

    Response for POST /messages/{message_id}/feedbacks endpoint.

    Attributes:
        result: Operation result
    """

    result: str = Field(..., description="Operation result")
