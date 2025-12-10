"""
File API Wrapper

Provides file upload related API operations.
"""

from typing import Any

from dify_assistant.api.base import AsyncBaseAPI, SyncBaseAPI


class UploadedFile:
    """
    Uploaded File Information

    Attributes:
        id: File ID
        name: File name
        size: File size (bytes)
        extension: File extension
        mime_type: MIME type
        created_by: Creator ID
        created_at: Creation timestamp
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.size: int = data.get("size", 0)
        self.extension: str = data.get("extension", "")
        self.mime_type: str = data.get("mime_type", "")
        self.created_by: str = data.get("created_by", "")
        self.created_at: int = data.get("created_at", 0)


class AsyncFileAPI(AsyncBaseAPI):
    """
    Asynchronous File API

    Provides file upload functionality.

    Example:
        # Upload file
        file_info = await file.upload(
            file_path="/path/to/image.png",
            user="user-123"
        )
        print(file_info.id)
    """

    async def upload(self, file_path: str, user: str) -> UploadedFile:
        """
        Upload file

        Args:
            file_path: Local file path
            user: User identifier

        Returns:
            Uploaded file information
        """
        data = await self._client.upload_file("/files/upload", file_path, user)
        return UploadedFile(data)


class SyncFileAPI(SyncBaseAPI):
    """
    Synchronous File API

    Provides file upload functionality.

    Example:
        # Upload file
        file_info = file.upload(
            file_path="/path/to/image.png",
            user="user-123"
        )
        print(file_info.id)
    """

    def upload(self, file_path: str, user: str) -> UploadedFile:
        """
        Upload file

        Args:
            file_path: Local file path
            user: User identifier

        Returns:
            Uploaded file information
        """
        data = self._client.upload_file("/files/upload", file_path, user)
        return UploadedFile(data)
