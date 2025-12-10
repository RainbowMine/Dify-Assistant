"""
API Base Class
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dify_assistant.client import AsyncDifyClient, SyncDifyClient


class AsyncBaseAPI:
    """
    Asynchronous API Base Class
    """

    def __init__(self, client: "AsyncDifyClient") -> None:
        """
        Initialize API

        Args:
            client: Asynchronous HTTP client
        """
        self._client = client


class SyncBaseAPI:
    """
    Synchronous API Base Class
    """

    def __init__(self, client: "SyncDifyClient") -> None:
        """
        Initialize API

        Args:
            client: Synchronous HTTP client
        """
        self._client = client
