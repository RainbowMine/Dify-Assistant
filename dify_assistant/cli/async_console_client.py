"""
Async Dify Console API Client

Async HTTP client for Dify Console API with email/password authentication.
Supports parallel operations for batch export/import.
"""

import asyncio
from typing import Any, Optional, Union

import httpx
from loguru import logger
from pydantic import EmailStr, SecretStr, validate_call

from dify_assistant.constants import (
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_PAGE_LIMIT,
    DEFAULT_TIMEOUT,
)


class AsyncConsoleClient:
    """
    Async Dify Console API Client

    Provides async access to Dify Console API using email/password authentication.
    Supports parallel operations for improved performance on batch operations.

    Example:
        async with AsyncConsoleClient(
            base_url="https://api.dify.ai",
            email="user@example.com",
            password="password"
        ) as client:
            await client.login()
            apps = await client.get_apps()
    """

    @validate_call
    def __init__(
        self,
        base_url: str,
        email: EmailStr,
        password: Union[str, SecretStr],
        timeout: float = DEFAULT_TIMEOUT,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ) -> None:
        """
        Initialize async console client.

        Args:
            base_url: Dify server base URL
            email: Login email (validated as email format)
            password: Login password (stored securely using SecretStr)
            timeout: Request timeout in seconds (must be positive)
            max_concurrency: Maximum concurrent requests (default: 5)

        Raises:
            ValueError: If email format is invalid, timeout is not positive, or max_concurrency < 1
        """
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")

        self.base_url = base_url.rstrip("/")
        self.email = str(email)
        # Convert password to SecretStr if it's a plain string
        self._password = SecretStr(password) if isinstance(password, str) else password
        self.timeout = timeout
        self.max_concurrency = max_concurrency

        # Async-safe token storage (using asyncio.Lock)
        self._lock = asyncio.Lock()
        self._access_token: Optional[str] = None
        self._csrf_token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get async HTTP client instance (lazy loading)."""
        async with self._lock:
            if self._client is None or self._client.is_closed:
                headers = {"Content-Type": "application/json"}
                if self._access_token:
                    headers["Authorization"] = f"Bearer {self._access_token}"

                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    headers=headers,
                    timeout=httpx.Timeout(self.timeout),
                )
            return self._client

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get semaphore for concurrency control."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)
        return self._semaphore

    async def _update_auth_header(self) -> None:
        """Update authorization header after login."""
        async with self._lock:
            if self._client and self._access_token:
                self._client.headers["Authorization"] = f"Bearer {self._access_token}"

    async def close(self) -> None:
        """Close client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncConsoleClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def login(self) -> None:
        """
        Login with email and password.

        Obtains access token and stores it in memory.

        Raises:
            httpx.HTTPStatusError: On authentication failure
        """
        client = await self._get_client()
        logger.debug("Logging in to {} as {}", self.base_url, self.email)

        response = await client.post(
            "/console/api/login",
            json={
                "email": self.email,
                "password": self._password.get_secret_value(),
                "remember_me": True,
            },
        )
        response.raise_for_status()

        # Try to get token from response body first (web login style)
        data = response.json()
        if "data" in data and "access_token" in data["data"]:
            self._access_token = data["data"]["access_token"]
        else:
            # Try to get token from cookies (newer Dify versions)
            self._access_token = response.cookies.get("access_token")

        # Get CSRF token from cookies (required for newer Dify versions)
        self._csrf_token = response.cookies.get("csrf_token")

        if not self._access_token:
            raise ValueError("Failed to obtain access token from login response")

        await self._update_auth_header()
        logger.info("Successfully logged in to {}", self.base_url)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """
        Make authenticated request with concurrency control.

        Args:
            method: HTTP method
            path: API path
            **kwargs: Additional request arguments

        Returns:
            Response JSON data

        Raises:
            httpx.HTTPStatusError: On request failure
        """
        if not self._access_token:
            raise RuntimeError("Not logged in. Call login() first.")

        client = await self._get_client()
        semaphore = self._get_semaphore()

        # Add CSRF token header if available (required for newer Dify versions)
        if self._csrf_token:
            headers = kwargs.get("headers", {})
            headers["X-CSRF-Token"] = self._csrf_token
            kwargs["headers"] = headers

        async with semaphore:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()

            # Handle empty response
            if not response.content:
                return {}

            return response.json()

    async def get_tags(self, tag_type: str = "app") -> list[dict[str, Any]]:
        """
        Get all tags with full information.

        Args:
            tag_type: Tag type (default: "app")

        Returns:
            List of tag dictionaries with id, name, type, etc.
        """
        logger.debug("Getting tags of type: {}", tag_type)
        data = await self._request("GET", "/console/api/tags", params={"type": tag_type})

        # Return full tag info
        tags = data if isinstance(data, list) else data.get("data", [])
        return list(tags)

    async def get_tag_id_by_name(self, tag_name: str, tag_type: str = "app") -> Optional[str]:
        """
        Get tag ID by tag name.

        Args:
            tag_name: Name of the tag to find
            tag_type: Tag type (default: "app")

        Returns:
            Tag ID if found, None otherwise
        """
        tags = await self.get_tags(tag_type)
        for tag in tags:
            if isinstance(tag, dict) and tag.get("name") == tag_name:
                return tag.get("id")
        return None

    async def create_tag(self, name: str, tag_type: str = "app") -> dict[str, Any]:
        """
        Create a new tag.

        Args:
            name: Tag name
            tag_type: Tag type (default: "app")

        Returns:
            Created tag info with id, name, etc.
        """
        logger.debug("Creating tag: {} (type: {})", name, tag_type)
        payload = {"name": name, "type": tag_type}
        return dict(await self._request("POST", "/console/api/tags", json=payload))

    async def get_or_create_tag(self, name: str, tag_type: str = "app") -> str:
        """
        Get existing tag ID or create a new tag if it doesn't exist.

        Args:
            name: Tag name
            tag_type: Tag type (default: "app")

        Returns:
            Tag ID
        """
        tag_id = await self.get_tag_id_by_name(name, tag_type)
        if tag_id:
            logger.debug("Found existing tag '{}' with ID: {}", name, tag_id)
            return tag_id

        # Create new tag
        result = await self.create_tag(name, tag_type)
        new_tag_id = result.get("id")
        if not new_tag_id:
            raise ValueError(f"Failed to create tag '{name}': no ID returned")
        logger.info("Created new tag '{}' with ID: {}", name, new_tag_id)
        return str(new_tag_id)

    async def bind_tag_to_app(self, app_id: str, tag_id: str) -> None:
        """
        Bind a tag to an app.

        Args:
            app_id: App ID to bind tag to
            tag_id: Tag ID to bind
        """
        logger.debug("Binding tag {} to app {}", tag_id, app_id)
        payload = {"tag_ids": [tag_id], "target_id": app_id, "type": "app"}
        await self._request("POST", "/console/api/tag-bindings/create", json=payload)
        logger.info("Bound tag {} to app {}", tag_id, app_id)

    async def get_apps(
        self,
        tag: Optional[str] = None,
        page: int = 1,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[dict[str, Any]]:
        """
        Get apps list.

        Args:
            tag: Filter by tag name
            page: Page number
            limit: Items per page

        Returns:
            List of app info dictionaries
        """
        logger.debug("Getting apps, tag={}, page={}, limit={}", tag, page, limit)

        params: dict[str, Any] = {"page": page, "limit": limit}
        if tag:
            # Convert tag name to ID
            tag_id = await self.get_tag_id_by_name(tag)
            if tag_id:
                params["tag_ids"] = tag_id
                logger.debug("Resolved tag '{}' to ID: {}", tag, tag_id)
            else:
                logger.warning("Tag '{}' not found, ignoring tag filter", tag)

        data = await self._request("GET", "/console/api/apps", params=params)

        apps = data.get("data", [])

        # If we need more pages, fetch them
        has_more = data.get("has_more", False)
        while has_more:
            page += 1
            params["page"] = page
            more_data = await self._request("GET", "/console/api/apps", params=params)
            apps.extend(more_data.get("data", []))
            has_more = more_data.get("has_more", False)

        return list(apps)

    async def get_app(self, app_id: str) -> Optional[dict[str, Any]]:
        """
        Get single app info.

        Args:
            app_id: App ID

        Returns:
            App info dictionary or None
        """
        logger.debug("Getting app: {}", app_id)
        try:
            result = await self._request("GET", f"/console/api/apps/{app_id}")
            return dict(result) if result else None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def export_app(self, app_id: str, include_secret: bool = False) -> str:
        """
        Export app DSL as YAML.

        Args:
            app_id: App ID
            include_secret: Include sensitive information

        Returns:
            YAML content string
        """
        logger.debug("Exporting app: {}", app_id)
        params = {"include_secret": str(include_secret).lower()}
        data = await self._request("GET", f"/console/api/apps/{app_id}/export", params=params)

        # The YAML content is in the "data" field
        return str(data.get("data", ""))

    async def import_app(
        self,
        yaml_content: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon_type: Optional[str] = None,
        icon: Optional[str] = None,
        icon_background: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Import app from YAML DSL.

        Args:
            yaml_content: YAML DSL content
            name: Optional app name override
            description: Optional description override
            icon_type: Icon type
            icon: Icon value
            icon_background: Icon background color

        Returns:
            Import result with app info
        """
        logger.debug("Importing app from YAML")

        payload: dict[str, Any] = {
            "mode": "yaml-content",
            "yaml_content": yaml_content,
        }

        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if icon_type:
            payload["icon_type"] = icon_type
        if icon:
            payload["icon"] = icon
        if icon_background:
            payload["icon_background"] = icon_background

        return dict(await self._request("POST", "/console/api/apps/imports", json=payload))

    async def delete_app(self, app_id: str) -> bool:
        """
        Delete an app by ID.

        Args:
            app_id: App ID to delete

        Returns:
            True if deleted successfully

        Raises:
            httpx.HTTPStatusError: On request failure
        """
        logger.debug("Deleting app: {}", app_id)
        await self._request("DELETE", f"/console/api/apps/{app_id}")
        logger.info("Deleted app: {}", app_id)
        return True

    # === Parallel Batch Operations ===

    async def export_apps_parallel(
        self,
        app_ids: list[str],
        include_secret: bool = False,
    ) -> list[tuple[str, Optional[str], Optional[Exception]]]:
        """
        Export multiple apps in parallel.

        Args:
            app_ids: List of app IDs to export
            include_secret: Include sensitive information

        Returns:
            List of tuples: (app_id, yaml_content or None, exception or None)
        """
        logger.info("Exporting {} apps in parallel (max_concurrency={})", len(app_ids), self.max_concurrency)

        async def export_single(app_id: str) -> tuple[str, Optional[str], Optional[Exception]]:
            try:
                yaml_content = await self.export_app(app_id, include_secret)
                return (app_id, yaml_content, None)
            except Exception as e:
                logger.error("Failed to export app {}: {}", app_id, e)
                return (app_id, None, e)

        tasks = [export_single(app_id) for app_id in app_ids]
        results = await asyncio.gather(*tasks)
        return list(results)

    async def import_apps_parallel(
        self,
        yaml_contents: list[tuple[str, str]],
    ) -> list[tuple[str, Optional[dict[str, Any]], Optional[Exception]]]:
        """
        Import multiple apps in parallel.

        Args:
            yaml_contents: List of tuples: (filename, yaml_content)

        Returns:
            List of tuples: (filename, result dict or None, exception or None)
        """
        logger.info("Importing {} apps in parallel (max_concurrency={})", len(yaml_contents), self.max_concurrency)

        async def import_single(
            filename: str, yaml_content: str
        ) -> tuple[str, Optional[dict[str, Any]], Optional[Exception]]:
            try:
                result = await self.import_app(yaml_content)
                return (filename, result, None)
            except Exception as e:
                logger.error("Failed to import {}: {}", filename, e)
                return (filename, None, e)

        tasks = [import_single(filename, yaml_content) for filename, yaml_content in yaml_contents]
        results = await asyncio.gather(*tasks)
        return list(results)

    async def get_apps_info_parallel(
        self,
        app_ids: list[str],
    ) -> list[tuple[str, Optional[dict[str, Any]], Optional[Exception]]]:
        """
        Get info for multiple apps in parallel.

        Args:
            app_ids: List of app IDs

        Returns:
            List of tuples: (app_id, app_info or None, exception or None)
        """
        logger.debug("Getting info for {} apps in parallel", len(app_ids))

        async def get_single(app_id: str) -> tuple[str, Optional[dict[str, Any]], Optional[Exception]]:
            try:
                app_info = await self.get_app(app_id)
                return (app_id, app_info, None)
            except Exception as e:
                logger.error("Failed to get app {}: {}", app_id, e)
                return (app_id, None, e)

        tasks = [get_single(app_id) for app_id in app_ids]
        results = await asyncio.gather(*tasks)
        return list(results)

    async def delete_apps_parallel(
        self,
        app_ids: list[str],
    ) -> list[tuple[str, bool, Optional[Exception]]]:
        """
        Delete multiple apps in parallel.

        Args:
            app_ids: List of app IDs to delete

        Returns:
            List of tuples: (app_id, success, exception or None)
        """
        logger.info("Deleting {} apps in parallel (max_concurrency={})", len(app_ids), self.max_concurrency)

        async def delete_single(app_id: str) -> tuple[str, bool, Optional[Exception]]:
            try:
                await self.delete_app(app_id)
                return (app_id, True, None)
            except Exception as e:
                logger.error("Failed to delete app {}: {}", app_id, e)
                return (app_id, False, e)

        tasks = [delete_single(app_id) for app_id in app_ids]
        results = await asyncio.gather(*tasks)
        return list(results)
