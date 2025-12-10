"""
Dify Console API Client

HTTP client for Dify Console API with email/password authentication.
"""

import threading
from typing import Any, Optional, Union

import httpx
from loguru import logger
from pydantic import EmailStr, SecretStr, validate_call

from dify_assistant.constants import DEFAULT_PAGE_LIMIT, DEFAULT_TIMEOUT


class ConsoleClient:
    """
    Dify Console API Client

    Provides access to Dify Console API using email/password authentication.
    Token is stored in memory during the session.

    Example:
        client = ConsoleClient(
            base_url="https://api.dify.ai",
            email="user@example.com",
            password="password"
        )
        client.login()
        apps = client.get_apps()
    """

    @validate_call
    def __init__(
        self,
        base_url: str,
        email: EmailStr,
        password: Union[str, SecretStr],
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Initialize console client.

        Args:
            base_url: Dify server base URL
            email: Login email (validated as email format)
            password: Login password (stored securely using SecretStr)
            timeout: Request timeout in seconds (must be positive)

        Raises:
            ValueError: If email format is invalid or timeout is not positive
        """
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self.base_url = base_url.rstrip("/")
        self.email = str(email)
        # Convert password to SecretStr if it's a plain string
        self._password = SecretStr(password) if isinstance(password, str) else password
        self.timeout = timeout

        # Thread-safe token storage
        self._lock = threading.Lock()
        self._access_token: Optional[str] = None
        self._csrf_token: Optional[str] = None
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get HTTP client instance (lazy loading)."""
        with self._lock:
            if self._client is None or self._client.is_closed:
                headers = {"Content-Type": "application/json"}
                if self._access_token:
                    headers["Authorization"] = f"Bearer {self._access_token}"

                self._client = httpx.Client(
                    base_url=self.base_url,
                    headers=headers,
                    timeout=httpx.Timeout(self.timeout),
                )
            return self._client

    def _update_auth_header(self) -> None:
        """Update authorization header after login."""
        with self._lock:
            if self._client and self._access_token:
                self._client.headers["Authorization"] = f"Bearer {self._access_token}"

    def close(self) -> None:
        """Close client connection."""
        if self._client and not self._client.is_closed:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ConsoleClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def login(self) -> None:
        """
        Login with email and password.

        Obtains access token and stores it in memory.

        Raises:
            httpx.HTTPStatusError: On authentication failure
        """
        client = self._get_client()
        logger.debug("Logging in to {} as {}", self.base_url, self.email)

        response = client.post(
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

        self._update_auth_header()
        logger.info("Successfully logged in to {}", self.base_url)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """
        Make authenticated request.

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

        client = self._get_client()

        # Add CSRF token header if available (required for newer Dify versions)
        if self._csrf_token:
            headers = kwargs.get("headers", {})
            headers["X-CSRF-Token"] = self._csrf_token
            kwargs["headers"] = headers

        response = client.request(method, path, **kwargs)
        response.raise_for_status()

        # Handle empty response
        if not response.content:
            return {}

        return response.json()

    def get_tags(self, tag_type: str = "app") -> list[dict[str, Any]]:
        """
        Get all tags with full information.

        Args:
            tag_type: Tag type (default: "app")

        Returns:
            List of tag dictionaries with id, name, type, etc.
        """
        logger.debug("Getting tags of type: {}", tag_type)
        data = self._request("GET", "/console/api/tags", params={"type": tag_type})

        # Return full tag info
        tags = data if isinstance(data, list) else data.get("data", [])
        return list(tags)

    def get_tag_id_by_name(self, tag_name: str, tag_type: str = "app") -> Optional[str]:
        """
        Get tag ID by tag name.

        Args:
            tag_name: Name of the tag to find
            tag_type: Tag type (default: "app")

        Returns:
            Tag ID if found, None otherwise
        """
        tags = self.get_tags(tag_type)
        for tag in tags:
            if isinstance(tag, dict) and tag.get("name") == tag_name:
                return tag.get("id")
        return None

    def create_tag(self, name: str, tag_type: str = "app") -> dict[str, Any]:
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
        return dict(self._request("POST", "/console/api/tags", json=payload))

    def get_or_create_tag(self, name: str, tag_type: str = "app") -> str:
        """
        Get existing tag ID or create a new tag if it doesn't exist.

        Args:
            name: Tag name
            tag_type: Tag type (default: "app")

        Returns:
            Tag ID
        """
        tag_id = self.get_tag_id_by_name(name, tag_type)
        if tag_id:
            logger.debug("Found existing tag '{}' with ID: {}", name, tag_id)
            return tag_id

        # Create new tag
        result = self.create_tag(name, tag_type)
        new_tag_id = result.get("id")
        if not new_tag_id:
            raise ValueError(f"Failed to create tag '{name}': no ID returned")
        logger.info("Created new tag '{}' with ID: {}", name, new_tag_id)
        return str(new_tag_id)

    def bind_tag_to_app(self, app_id: str, tag_id: str) -> None:
        """
        Bind a tag to an app.

        Args:
            app_id: App ID to bind tag to
            tag_id: Tag ID to bind
        """
        logger.debug("Binding tag {} to app {}", tag_id, app_id)
        payload = {"tag_ids": [tag_id], "target_id": app_id, "type": "app"}
        self._request("POST", "/console/api/tag-bindings/create", json=payload)
        logger.info("Bound tag {} to app {}", tag_id, app_id)

    def get_apps(
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
            tag_id = self.get_tag_id_by_name(tag)
            if tag_id:
                params["tag_ids"] = tag_id
                logger.debug("Resolved tag '{}' to ID: {}", tag, tag_id)
            else:
                logger.warning("Tag '{}' not found, ignoring tag filter", tag)

        data = self._request("GET", "/console/api/apps", params=params)

        apps = data.get("data", [])

        # If we need more pages, fetch them
        has_more = data.get("has_more", False)
        while has_more:
            page += 1
            params["page"] = page
            more_data = self._request("GET", "/console/api/apps", params=params)
            apps.extend(more_data.get("data", []))
            has_more = more_data.get("has_more", False)

        return list(apps)

    def get_app(self, app_id: str) -> Optional[dict[str, Any]]:
        """
        Get single app info.

        Args:
            app_id: App ID

        Returns:
            App info dictionary or None
        """
        logger.debug("Getting app: {}", app_id)
        try:
            result = self._request("GET", f"/console/api/apps/{app_id}")
            return dict(result) if result else None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def export_app(self, app_id: str, include_secret: bool = False) -> str:
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
        data = self._request("GET", f"/console/api/apps/{app_id}/export", params=params)

        # The YAML content is in the "data" field
        return str(data.get("data", ""))

    def import_app(
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

        return dict(self._request("POST", "/console/api/apps/imports", json=payload))

    def delete_app(self, app_id: str) -> bool:
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
        self._request("DELETE", f"/console/api/apps/{app_id}")
        logger.info("Deleted app: {}", app_id)
        return True

    # ==================== Plugin API ====================

    def get_plugins(self) -> list[dict[str, Any]]:
        """
        Get all installed plugins.

        Returns:
            List of plugin dictionaries
        """
        logger.debug("Getting plugins")
        data = self._request("GET", "/console/api/workspaces/current/plugin/list")

        plugins = data.get("plugins", [])
        return list(plugins)

    def install_plugin_from_marketplace(self, plugin_unique_identifiers: list[str]) -> dict[str, Any]:
        """
        Install plugins from marketplace.

        Args:
            plugin_unique_identifiers: List of plugin unique identifiers (e.g., ["langgenius/openai:1.2.0"])

        Returns:
            Installation task info
        """
        logger.debug("Installing plugins from marketplace: {}", plugin_unique_identifiers)
        payload = {"plugin_unique_identifiers": plugin_unique_identifiers}
        return dict(self._request("POST", "/console/api/workspaces/current/plugin/install/marketplace", json=payload))

    def install_plugin_from_github(
        self,
        plugin_unique_identifier: str,
        repo: str,
        version: str,
        package: str,
    ) -> dict[str, Any]:
        """
        Install plugin from GitHub.

        Args:
            plugin_unique_identifier: Plugin unique identifier
            repo: GitHub repository (owner/repo)
            version: Version tag (e.g., "v1.0.0")
            package: Package name

        Returns:
            Installation task info
        """
        logger.debug("Installing plugin from GitHub: {} @ {}", repo, version)
        payload = {
            "plugin_unique_identifier": plugin_unique_identifier,
            "repo": repo,
            "version": version,
            "package": package,
        }
        return dict(self._request("POST", "/console/api/workspaces/current/plugin/install/github", json=payload))

    def uninstall_plugin(self, plugin_installation_id: str) -> dict[str, Any]:
        """
        Uninstall a plugin.

        Args:
            plugin_installation_id: Plugin installation ID

        Returns:
            Uninstall result
        """
        logger.debug("Uninstalling plugin: {}", plugin_installation_id)
        payload = {"plugin_installation_id": plugin_installation_id}
        result = dict(self._request("POST", "/console/api/workspaces/current/plugin/uninstall", json=payload))
        logger.info("Uninstalled plugin: {}", plugin_installation_id)
        return result

    def get_plugin_tasks(self) -> list[dict[str, Any]]:
        """
        Get plugin installation tasks.

        Returns:
            List of installation task dictionaries
        """
        logger.debug("Getting plugin tasks")
        data = self._request("GET", "/console/api/workspaces/current/plugin/tasks")
        tasks = data.get("tasks", data) if isinstance(data, dict) else data
        return list(tasks) if isinstance(tasks, list) else []

    def update_plugin_config(self, plugin_installation_id: str, config: dict[str, Any]) -> dict[str, Any]:
        """
        Update plugin configuration.

        Args:
            plugin_installation_id: Plugin installation ID
            config: Configuration dictionary

        Returns:
            Update result
        """
        logger.debug("Updating plugin config: {}", plugin_installation_id)
        payload = config
        return dict(
            self._request(
                "PUT",
                f"/console/api/workspaces/current/plugin/instances/{plugin_installation_id}/config",
                json=payload,
            )
        )
