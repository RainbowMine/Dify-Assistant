"""
CLI Utilities

Helper functions for CLI commands.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from dify_assistant.config import AppConfig, ConfigLoader
from dify_assistant.constants import DEFAULT_CONFIG_FILE

if TYPE_CHECKING:
    from dify_assistant.cli.async_console_client import AsyncConsoleClient
    from dify_assistant.cli.console_client import ConsoleClient
    from dify_assistant.config import DifyServerConfig


def get_config(ctx: typer.Context) -> AppConfig:
    """
    Get configuration from context.

    Args:
        ctx: Typer context

    Returns:
        AppConfig instance
    """
    config_path: Path = ctx.obj.get("config", Path(DEFAULT_CONFIG_FILE))

    if not config_path.exists():
        typer.echo(f"Error: Config file not found: {config_path}", err=True)
        raise typer.Exit(1)

    return ConfigLoader.from_file(AppConfig, config_path)


def get_console_client(server_config: "DifyServerConfig") -> "ConsoleClient":
    """
    Get console client for server.

    Creates a new client and authenticates for each call.
    This ensures fresh authentication and avoids token/password caching issues.

    Args:
        server_config: Server configuration

    Returns:
        ConsoleClient instance (authenticated)
    """
    from dify_assistant.cli.console_client import ConsoleClient

    client = ConsoleClient(
        base_url=str(server_config.base_url),
        email=server_config.email,
        password=server_config.password.get_secret_value(),
    )
    client.login()
    return client


def get_async_console_client(
    server_config: "DifyServerConfig",
    max_concurrency: int = 5,
) -> "AsyncConsoleClient":
    """
    Get async console client for server.

    Note: The returned client is NOT authenticated. Call `await client.login()` after.

    Args:
        server_config: Server configuration
        max_concurrency: Maximum concurrent requests (default: 5)

    Returns:
        AsyncConsoleClient instance (not authenticated, call login() after)
    """
    from dify_assistant.cli.async_console_client import AsyncConsoleClient

    return AsyncConsoleClient(
        base_url=str(server_config.base_url),
        email=server_config.email,
        password=server_config.password.get_secret_value(),
        max_concurrency=max_concurrency,
    )
