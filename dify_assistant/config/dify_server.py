"""
Dify Server Configuration Model

Provides configuration information needed for Dify Server connection, including server address and authentication credentials.
"""

from pydantic import BaseModel, HttpUrl, SecretStr

__all__ = ["DifyServerConfig"]


class DifyServerConfig(BaseModel):
    """
    Dify Server Configuration

    Stores configuration information needed to connect to Dify Server.

    Attributes:
        name: Server name, used to distinguish different Dify Servers
        base_url: Dify Server URL address
        email: Login email or username
        password: Login password (stored securely using SecretStr)

    Security:
        The password is stored using Pydantic's SecretStr type to prevent
        accidental exposure in logs, repr(), or serialization.

    Example:
        Corresponding TOML file format::

            [servers.production]
            base_url = "https://api.dify.ai"
            email = "user@example.com"
            password = "your-password"
    """

    name: str = ""
    base_url: HttpUrl
    email: str
    password: SecretStr
