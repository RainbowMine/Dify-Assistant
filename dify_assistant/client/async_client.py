"""
Asynchronous HTTP Client
"""

import json
from typing import Any, AsyncIterator, Optional, cast

import anyio
import httpx
from loguru import logger

from dify_assistant.client.base import (
    DifyClientConfig,
    build_headers,
    handle_error_response,
)
from dify_assistant.streaming import SSEParser, StreamEvent


class AsyncDifyClient:
    """
    Asynchronous Dify API Client

    Provides asynchronous HTTP communication with Dify API.

    Example:
        config = DifyClientConfig(
            base_url="https://api.dify.ai/v1",
            api_key="app-xxx"
        )
        client = AsyncDifyClient(config)

        # Blocking mode request
        response = await client.post("/chat-messages", json={"query": "hello"})

        # Streaming mode request
        async for event in client.stream_post("/chat-messages", json=data):
            print(event)
    """

    def __init__(self, config: DifyClientConfig) -> None:
        """
        Initialize asynchronous client

        Args:
            config: Client configuration
        """
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._sse_parser = SSEParser()

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get HTTP client instance (lazy loading)

        Returns:
            httpx.AsyncClient instance
        """
        if self._client is None or self._client.is_closed:
            logger.debug("Creating new async HTTP client for {}", self.config.base_url_str)
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url_str,
                headers=build_headers(self.config.api_key),
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close client connection"""
        if self._client and not self._client.is_closed:
            logger.debug("Closing async HTTP client")
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncDifyClient":
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        await self.close()

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send HTTP request

        Args:
            method: HTTP method
            path: API path
            **kwargs: Other parameters passed to httpx

        Returns:
            Response JSON data

        Raises:
            DifyAPIError: API error
        """
        client = await self._get_client()
        logger.debug("Sending async {} request to {}", method, path)
        response = await client.request(method, path, **kwargs)

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"message": response.text}
            handle_error_response(response.status_code, error_data)

        logger.debug("Async request {} {} completed with status {}", method, path, response.status_code)
        return cast(dict[str, Any], response.json())

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """
        Send GET request

        Args:
            path: API path
            **kwargs: Other parameters passed to httpx

        Returns:
            Response JSON data
        """
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """
        Send POST request

        Args:
            path: API path
            **kwargs: Other parameters passed to httpx

        Returns:
            Response JSON data
        """
        return await self.request("POST", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """
        Send DELETE request

        Args:
            path: API path
            **kwargs: Other parameters passed to httpx

        Returns:
            Response JSON data
        """
        return await self.request("DELETE", path, **kwargs)

    async def stream_request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        """
        Send streaming request

        Args:
            method: HTTP method
            path: API path
            **kwargs: Other parameters passed to httpx

        Yields:
            Stream event objects

        Raises:
            DifyAPIError: API error
        """
        client = await self._get_client()
        logger.debug("Starting async streaming {} request to {}", method, path)

        async with client.stream(method, path, **kwargs) as response:
            if response.status_code >= 400:
                # Read error response
                error_text = await response.aread()
                try:
                    error_data = json.loads(error_text.decode())
                except Exception:
                    error_data = {"message": error_text.decode()}
                handle_error_response(response.status_code, error_data)

            async for event in self._sse_parser.parse_async(response):
                yield event

        logger.debug("Async streaming {} request to {} completed", method, path)

    async def stream_post(self, path: str, **kwargs: Any) -> AsyncIterator[StreamEvent]:
        """
        Send streaming POST request

        Args:
            path: API path
            **kwargs: Other parameters passed to httpx

        Yields:
            Stream event objects
        """
        async for event in self.stream_request("POST", path, **kwargs):
            yield event

    async def upload_file(
        self,
        path: str,
        file_path: str,
        user: str,
    ) -> dict[str, Any]:
        """
        Upload file

        Args:
            path: API path
            file_path: Local file path
            user: User identifier

        Returns:
            Response JSON data
        """
        client = await self._get_client()
        logger.debug("Uploading file {} to {} (async)", file_path, path)

        # Read file content in thread pool to avoid blocking event loop
        file_content = await anyio.to_thread.run_sync(self._read_file_sync, file_path)

        files = {"file": (file_path, file_content)}
        data = {"user": user}

        # Don't use JSON content-type when uploading files
        headers = {"Authorization": f"Bearer {self.config.api_key.get_secret_value()}"}

        response = await client.post(path, files=files, data=data, headers=headers)

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"message": response.text}
            handle_error_response(response.status_code, error_data)

        logger.debug("Async file upload completed with status {}", response.status_code)
        return cast(dict[str, Any], response.json())

    @staticmethod
    def _read_file_sync(file_path: str) -> bytes:
        """Read file synchronously (called from thread pool)."""
        with open(file_path, "rb") as f:
            return f.read()
