"""
Application Configuration Model

Provides application-level configuration containing multiple Dify Server configurations.
"""

from typing import Dict, Optional

from pydantic import BaseModel, model_validator

from dify_assistant.config.dify_server import DifyServerConfig

__all__ = ["AppConfig"]


class AppConfig(BaseModel):
    """
    Application Configuration

    Contains multiple Dify Server configurations, supports finding specific servers by name.

    Attributes:
        servers: Dify Server configuration dictionary, keyed by server name

    Example:
        Loading configuration from TOML file::

            from dify_assistant.config import ConfigLoader, AppConfig

            config = ConfigLoader.from_file(AppConfig, "config.toml")

            # Get all servers
            for name, server in config.servers.items():
                print(f"{name}: {server.base_url}")

            # Find server by name
            prod_server = config.get_server_by_name("production")

        Corresponding TOML file format::

            [servers.production]
            base_url = "https://api.dify.ai"
            email = "prod@example.com"
            password = "prod-password"

            [servers.development]
            base_url = "https://dev.dify.ai"
            email = "dev@example.com"
            password = "dev-password"
    """

    servers: Dict[str, DifyServerConfig]

    @model_validator(mode="after")
    def populate_server_names(self) -> "AppConfig":
        """Populate server name from dictionary key"""
        for name, server in self.servers.items():
            server.name = name
        return self

    def get_server_by_name(self, name: str) -> Optional[DifyServerConfig]:
        """
        Find Dify Server configuration by name

        Args:
            name: Server name

        Returns:
            Matching server configuration, or None if not found
        """
        return self.servers.get(name)
