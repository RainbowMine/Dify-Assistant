"""
Synchronous HTTP Client
"""

import json
from typing import Any, Iterator, Optional, cast

import httpx
from loguru import logger

from dify_assistant.client.base import (
    DifyClientConfig,
    build_headers,
    handle_error_response,
)
from dify_assistant.streaming import SSEParser, StreamEvent


class SyncDifyClient:
    """
    Synchronous Dify API Client

    Provides synchronous HTTP communication with Dify API.

    Example:
        config = DifyClientConfig(
            base_url="https://api.dify.ai/v1",
            api_key="app-xxx"
        )
        client = SyncDifyClient(config)

        # Blocking mode request
        response = client.post("/chat-messages", json={"query": "hello"})

        # Streaming mode request
        for event in client.stream_post("/chat-messages", json=data):
            print(event)
    """

    def __init__(self, config: DifyClientConfig) -> None:
        """
        Initialize synchronous client

        Args:
            config: Client configuration
        """
        self.config = config
        self._client: Optional[httpx.Client] = None
        self._sse_parser = SSEParser()

    def _get_client(self) -> httpx.Client:
        """
        Get HTTP client instance (lazy loading)

        Returns:
            httpx.Client instance
        """
        if self._client is None or self._client.is_closed:
            logger.debug("Creating new sync HTTP client for {}", self.config.base_url_str)
            self._client = httpx.Client(
                base_url=self.config.base_url_str,
                headers=build_headers(self.config.api_key),
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    def close(self) -> None:
        """Close client connection"""
        if self._client and not self._client.is_closed:
            logger.debug("Closing sync HTTP client")
            self._client.close()
            self._client = None

    def __enter__(self) -> "SyncDifyClient":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.close()

    def request(
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
        client = self._get_client()
        logger.debug("Sending {} request to {}", method, path)
        response = client.request(method, path, **kwargs)

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"message": response.text}
            handle_error_response(response.status_code, error_data)

        logger.debug("Request {} {} completed with status {}", method, path, response.status_code)
        return cast(dict[str, Any], response.json())

    def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """
        Send GET request

        Args:
            path: API path
            **kwargs: Other parameters passed to httpx

        Returns:
            Response JSON data
        """
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """
        Send POST request

        Args:
            path: API path
            **kwargs: Other parameters passed to httpx

        Returns:
            Response JSON data
        """
        return self.request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """
        Send DELETE request

        Args:
            path: API path
            **kwargs: Other parameters passed to httpx

        Returns:
            Response JSON data
        """
        return self.request("DELETE", path, **kwargs)

    def stream_request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Iterator[StreamEvent]:
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
        client = self._get_client()
        logger.debug("Starting streaming {} request to {}", method, path)

        with client.stream(method, path, **kwargs) as response:
            if response.status_code >= 400:
                # Read error response
                error_text = response.read()
                try:
                    error_data = json.loads(error_text.decode())
                except Exception:
                    error_data = {"message": error_text.decode()}
                handle_error_response(response.status_code, error_data)

            for event in self._sse_parser.parse_sync(response):
                yield event

        logger.debug("Streaming {} request to {} completed", method, path)

    def stream_post(self, path: str, **kwargs: Any) -> Iterator[StreamEvent]:
        """
        Send streaming POST request

        Args:
            path: API path
            **kwargs: Other parameters passed to httpx

        Yields:
            Stream event objects
        """
        for event in self.stream_request("POST", path, **kwargs):
            yield event

    def upload_file(
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
        client = self._get_client()
        logger.debug("Uploading file {} to {}", file_path, path)

        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"user": user}

            # Don't use JSON content-type when uploading files
            headers = {"Authorization": f"Bearer {self.config.api_key.get_secret_value()}"}

            response = client.post(path, files=files, data=data, headers=headers)

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"message": response.text}
            handle_error_response(response.status_code, error_data)

        logger.debug("File upload completed with status {}", response.status_code)
        return cast(dict[str, Any], response.json())
