"""
Feedback API Request Model
"""

from pydantic import BaseModel, Field

from dify_assistant.models.common import Rating


class FeedbackRequest(BaseModel):
    """
    Message Feedback Request

    Used for POST /messages/{message_id}/feedbacks endpoint.

    Attributes:
        rating: Rating (like/dislike/null)
        user: User identifier
    """

    rating: Rating = Field(..., description="Rating")
    user: str = Field(..., min_length=1, description="User identifier")

    def to_api_dict(self) -> dict[str, str]:
        """
        Convert to API request dictionary

        Returns:
            Dictionary format suitable for sending to API
        """
        return {
            "rating": self.rating.value,
            "user": self.user,
        }
