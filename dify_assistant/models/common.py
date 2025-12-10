"""
Common Data Models

Provides common data structures used across APIs.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ResponseMode(str, Enum):
    """
    Response Mode

    Controls how API returns results.
    """

    BLOCKING = "blocking"
    """Blocking mode: waits for complete response before returning"""

    STREAMING = "streaming"
    """Streaming mode: returns real-time via SSE"""


class Rating(str, Enum):
    """
    Message Rating

    Used for feedback API.
    """

    LIKE = "like"
    """Thumbs up"""

    DISLIKE = "dislike"
    """Thumbs down"""

    NULL = "null"
    """Revoke rating"""


class FileType(str, Enum):
    """
    File Type

    Supported file types.
    """

    IMAGE = "image"
    """Image file"""

    DOCUMENT = "document"
    """Document file"""

    AUDIO = "audio"
    """Audio file"""

    VIDEO = "video"
    """Video file"""


class TransferMethod(str, Enum):
    """
    File Transfer Method
    """

    REMOTE_URL = "remote_url"
    """Remote URL"""

    LOCAL_FILE = "local_file"
    """Local file (must be uploaded first)"""


class InputFile(BaseModel):
    """
    Input File

    Used for file input in Chat/Completion APIs.

    Attributes:
        type: File type
        transfer_method: Transfer method
        url: File URL (for remote_url method)
        upload_file_id: Uploaded file ID (for local_file method)
    """

    type: FileType
    transfer_method: TransferMethod
    url: Optional[str] = None
    upload_file_id: Optional[str] = None

    def model_post_init(self, __context: object) -> None:
        """Validate file configuration"""
        if self.transfer_method == TransferMethod.REMOTE_URL and not self.url:
            raise ValueError("url is required when transfer_method is remote_url")
        if self.transfer_method == TransferMethod.LOCAL_FILE and not self.upload_file_id:
            raise ValueError("upload_file_id is required when transfer_method is local_file")


class Usage(BaseModel):
    """
    Token Usage

    Attributes:
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        total_tokens: Total number of tokens
    """

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class RetrieverResource(BaseModel):
    """
    Knowledge Base Retrieval Resource

    Citation source returned in RAG scenarios.

    Attributes:
        position: Citation position index
        dataset_id: Dataset ID
        dataset_name: Dataset name
        document_id: Document ID
        document_name: Document name
        segment_id: Segment ID
        score: Relevance score
        content: Citation content
    """

    position: int
    dataset_id: str
    dataset_name: str
    document_id: str
    document_name: str
    segment_id: str
    score: float = Field(ge=0.0, le=1.0)
    content: str
