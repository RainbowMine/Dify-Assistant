"""
Plugin Commands

Provides CLI commands for plugin management (list, export, import, upgrade).
Supports parallel operations for batch install/upgrade.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
import typer
from loguru import logger

from dify_assistant.cli.utils import (
    get_async_console_client,
    get_config,
    get_console_client,
)
from dify_assistant.constants import PLUGIN_MARKETPLACE_CONCURRENCY

app = typer.Typer(no_args_is_help=True)

# Marketplace API base URL
MARKETPLACE_API_BASE = "https://marketplace.dify.ai/api/v1"


def _get_latest_plugin_version(plugin_name: str) -> Optional[str]:
    """
    Fetch the latest version's unique_identifier from marketplace.

    Args:
        plugin_name: Plugin name in format "org/name" (e.g., "langgenius/openai")

    Returns:
        The unique_identifier for the latest version, or None if not found.
        Format: "org/name:version@checksum"
    """
    if "/" not in plugin_name:
        logger.warning(f"Invalid plugin name format: {plugin_name}")
        return None

    org, name = plugin_name.split("/", 1)
    url = f"{MARKETPLACE_API_BASE}/plugins/{org}/{name}/versions"

    try:
        response = httpx.get(url, params={"page": 1, "page_size": 1}, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        if data.get("code") == 0 and data.get("data", {}).get("versions"):
            latest = data["data"]["versions"][0]
            unique_id = latest.get("unique_identifier")
            return str(unique_id) if unique_id else None
        else:
            logger.warning(f"No versions found for plugin: {plugin_name}")
            return None

    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error fetching latest version for {plugin_name}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching latest version for {plugin_name}: {e}")
        return None


async def _get_latest_plugin_version_async(plugin_name: str) -> Optional[str]:
    """
    Async version: Fetch the latest version's unique_identifier from marketplace.

    Args:
        plugin_name: Plugin name in format "org/name" (e.g., "langgenius/openai")

    Returns:
        The unique_identifier for the latest version, or None if not found.
    """
    if "/" not in plugin_name:
        logger.warning(f"Invalid plugin name format: {plugin_name}")
        return None

    org, name = plugin_name.split("/", 1)
    url = f"{MARKETPLACE_API_BASE}/plugins/{org}/{name}/versions"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={"page": 1, "page_size": 1})
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 0 and data.get("data", {}).get("versions"):
                latest = data["data"]["versions"][0]
                unique_id = latest.get("unique_identifier")
                return str(unique_id) if unique_id else None
            else:
                logger.warning(f"No versions found for plugin: {plugin_name}")
                return None

    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error fetching latest version for {plugin_name}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching latest version for {plugin_name}: {e}")
        return None


def _format_table(plugins: list[dict[str, Any]]) -> str:
    """Format plugins as a table."""
    if not plugins:
        return "No plugins found"

    # Define columns
    headers = ["Name", "Version", "Source", "Installation ID"]
    rows: list[list[str]] = []

    for plugin in plugins:
        # plugin_id is "author/name", version is separate field
        name = plugin.get("plugin_id", "")
        version = plugin.get("version", "")
        source = plugin.get("source", "unknown")
        installation_id = plugin.get("id", plugin.get("installation_id", ""))

        rows.append([name, version, source, installation_id])

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    # Build table
    lines: list[str] = []

    # Header
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("-" * len(header_line))

    # Rows
    for row in rows:
        row_line = " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row))
        lines.append(row_line)

    return "\n".join(lines)


@app.command("list")
def list_plugins(
    ctx: typer.Context,
    server: str = typer.Option(..., "--server", "-s", help="Server instance name"),
    format_: str = typer.Option("table", "--format", "-f", help="Output format: table or json"),
) -> None:
    """
    List all installed plugins from a server.
    """
    config = get_config(ctx)
    server_config = config.get_server_by_name(server)

    if server_config is None:
        typer.echo(f"Error: Server '{server}' not found in config", err=True)
        raise typer.Exit(1)

    client = get_console_client(server_config)

    try:
        plugins = client.get_plugins()

        if format_ == "json":
            typer.echo(json.dumps(plugins, indent=2, ensure_ascii=False))
        else:
            typer.echo(f"Server: {server} ({server_config.base_url})")
            typer.echo(f"Total: {len(plugins)} plugin(s)\n")
            typer.echo(_format_table(plugins))

    except Exception as e:
        logger.error("Failed to list plugins: {}", e)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("export")
def export_plugins(
    ctx: typer.Context,
    server: str = typer.Option(..., "--server", "-s", help="Server instance name"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path (default: stdout)"),
    with_config: bool = typer.Option(False, "--with-config", help="Include plugin configurations"),
) -> None:
    """
    Export installed plugins list from a server.

    Exports the list of installed plugins (not the plugin packages themselves).
    Use --with-config to include plugin configurations (may contain sensitive data).
    """
    config = get_config(ctx)
    server_config = config.get_server_by_name(server)

    if server_config is None:
        typer.echo(f"Error: Server '{server}' not found in config", err=True)
        raise typer.Exit(1)

    client = get_console_client(server_config)

    try:
        plugins = client.get_plugins()

        if not plugins:
            typer.echo("No plugins found to export", err=True)
            raise typer.Exit(0)

        # Build export data
        export_data: dict[str, Any] = {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "source_server": server,
            "include_config": with_config,
            "plugins": [],
        }

        for plugin in plugins:
            # plugin_unique_identifier contains version and hash: "author/name:version@hash"
            # plugin_id is just "author/name"
            plugin_unique_id = plugin.get("plugin_unique_identifier", "")
            plugin_id = plugin.get("plugin_id", "")
            installation_id = plugin.get("id", plugin.get("installation_id", ""))
            version = plugin.get("version", "")

            # Use plugin_id as name (without version)
            name = plugin_id

            plugin_export: dict[str, Any] = {
                "name": name,
                "plugin_unique_identifier": plugin_unique_id,
                "source": plugin.get("source", "marketplace"),
                "version": version,
                "installation_id": installation_id,
            }

            # Include GitHub info if available
            github_info = plugin.get("github")
            if github_info:
                plugin_export["github"] = github_info

            # Include config if requested
            if with_config:
                plugin_config = plugin.get("config") or plugin.get("settings")
                plugin_export["config"] = plugin_config

            export_data["plugins"].append(plugin_export)

        # Output
        json_output = json.dumps(export_data, indent=2, ensure_ascii=False)

        if output:
            output.write_text(json_output, encoding="utf-8")
            typer.echo(f"Exported {len(plugins)} plugin(s) to {output}")
        else:
            typer.echo(json_output)

    except typer.Exit:
        raise
    except Exception as e:
        logger.error("Failed to export plugins: {}", e)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("import")
def import_plugins(
    ctx: typer.Context,
    server: str = typer.Option(..., "--server", "-s", help="Server instance name"),
    input_: Optional[Path] = typer.Option(None, "--input", "-i", help="Input file path (default: stdin)"),
    latest: bool = typer.Option(False, "--latest", help="Install latest version instead of exported version"),
    with_config: bool = typer.Option(False, "--with-config", help="Apply plugin configurations"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip-existing", help="Skip already installed plugins (default: True)"),
    parallel: bool = typer.Option(True, "--parallel/--serial", "-p/-P", help="Enable parallel install (default: True)"),
    concurrency: int = typer.Option(
        PLUGIN_MARKETPLACE_CONCURRENCY, "--concurrency", "-c", help="Max concurrent requests (marketplace limit: 3)"
    ),
) -> None:
    """
    Import and install plugins to a server from an export file.

    By default installs the exact version from the export file using parallel mode.
    Use --latest to install the latest available version.
    Use --with-config to apply configurations (export file must include config).
    Use --serial to disable parallel processing.
    """
    config = get_config(ctx)
    server_config = config.get_server_by_name(server)

    if server_config is None:
        typer.echo(f"Error: Server '{server}' not found in config", err=True)
        raise typer.Exit(1)

    # Read input
    try:
        if input_:
            import_data = json.loads(input_.read_text(encoding="utf-8"))
        else:
            # Read from stdin
            import_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        typer.echo(f"Error: Invalid JSON input: {e}", err=True)
        raise typer.Exit(1)

    # Validate import data
    if "plugins" not in import_data:
        typer.echo("Error: Invalid import file format (missing 'plugins' field)", err=True)
        raise typer.Exit(1)

    plugins_to_import = import_data.get("plugins", [])
    if not plugins_to_import:
        typer.echo("No plugins to import")
        raise typer.Exit(0)

    # Use parallel or serial mode
    if parallel and len(plugins_to_import) > 1:
        # Parallel import
        asyncio.run(
            _import_plugins_parallel(
                server_config, plugins_to_import, latest, with_config, skip_existing, concurrency, server
            )
        )
    else:
        # Serial import
        _import_plugins_serial(server_config, plugins_to_import, latest, with_config, skip_existing, server)


def _import_plugins_serial(
    server_config: Any,
    plugins_to_import: list[dict[str, Any]],
    latest: bool,
    with_config: bool,
    skip_existing: bool,
    server: str,
) -> None:
    """Import plugins serially using sync client."""
    client = get_console_client(server_config)

    try:
        # Get existing plugins if skip_existing is enabled
        existing_plugins: set[str] = set()
        if skip_existing:
            installed = client.get_plugins()
            for p in installed:
                pid = p.get("plugin_id", "")
                existing_plugins.add(pid)
                if ":" in pid:
                    existing_plugins.add(pid.rsplit(":", 1)[0])

        typer.echo(f"Server: {server} ({server_config.base_url})")
        typer.echo(f"Importing {len(plugins_to_import)} plugin(s) serially...\n")

        installed_count = 0
        skipped_count = 0
        failed_count = 0
        config_applied_count = 0

        for plugin in plugins_to_import:
            name = plugin.get("name", "")
            plugin_id = plugin.get("plugin_unique_identifier", "")
            source = plugin.get("source", "marketplace")
            version = plugin.get("version", "")

            # Determine identifier to install
            if latest:
                # For marketplace plugins, fetch latest version's unique_identifier
                if source == "marketplace":
                    latest_id = _get_latest_plugin_version(name)
                    if latest_id:
                        install_id = latest_id
                    else:
                        typer.echo(f"  [FAIL] {name} - Could not fetch latest version from marketplace", err=True)
                        failed_count += 1
                        continue
                else:
                    install_id = name
            else:
                install_id = plugin_id if plugin_id else f"{name}:{version}" if version else name

            # Check if already installed
            if skip_existing and (install_id in existing_plugins or name in existing_plugins):
                typer.echo(f"  [SKIP] {name} (already installed)")
                skipped_count += 1
                continue

            # Install based on source
            try:
                if source == "github" and "github" in plugin:
                    github_info = plugin["github"]
                    client.install_plugin_from_github(
                        plugin_unique_identifier=install_id,
                        repo=github_info.get("repo", ""),
                        version=github_info.get("version", ""),
                        package=github_info.get("package", ""),
                    )
                else:
                    client.install_plugin_from_marketplace([install_id])

                status_parts = ["installed"]

                # Apply config if requested and available
                if with_config and plugin.get("config"):
                    installation_id = plugin.get("installation_id")
                    if installation_id:
                        try:
                            client.update_plugin_config(installation_id, plugin["config"])
                            status_parts.append("config applied")
                            config_applied_count += 1
                        except Exception as config_err:
                            status_parts.append(f"config failed: {config_err}")

                typer.echo(f"  [OK] {name}:{version if not latest else 'latest'} ({', '.join(status_parts)})")
                installed_count += 1

            except httpx.HTTPStatusError as install_err:
                error_detail = ""
                try:
                    error_body = install_err.response.json()
                    error_detail = error_body.get("message", "") or error_body.get("error", "")
                except Exception:
                    pass

                if install_err.response.status_code == 400 and (
                    "already" in error_detail.lower()
                    or "installed" in error_detail.lower()
                    or "exist" in error_detail.lower()
                ):
                    typer.echo(f"  [SKIP] {name}:{version} (already installed)")
                    skipped_count += 1
                else:
                    error_msg = error_detail if error_detail else str(install_err)
                    typer.echo(f"  [FAIL] {name}:{version} - {error_msg}", err=True)
                    failed_count += 1

            except Exception as install_err:
                typer.echo(f"  [FAIL] {name}:{version} - {install_err}", err=True)
                failed_count += 1

        # Summary
        typer.echo(f"\nSummary: {installed_count} installed, {skipped_count} skipped, {failed_count} failed")
        if with_config:
            typer.echo(f"         {config_applied_count} configs applied")

    except typer.Exit:
        raise
    except Exception as e:
        logger.error("Failed to import plugins: {}", e)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


async def _import_plugins_parallel(
    server_config: Any,
    plugins_to_import: list[dict[str, Any]],
    latest: bool,
    with_config: bool,
    skip_existing: bool,
    max_concurrency: int,
    server: str,
) -> None:
    """Import plugins in parallel using async client."""
    async with get_async_console_client(server_config, max_concurrency) as client:
        await client.login()

        # Get existing plugins if skip_existing is enabled
        existing_plugins: set[str] = set()
        if skip_existing:
            installed = await client.get_plugins()
            for p in installed:
                pid = p.get("plugin_id", "")
                existing_plugins.add(pid)
                if ":" in pid:
                    existing_plugins.add(pid.rsplit(":", 1)[0])

        # Filter plugins to install
        plugins_filtered: list[dict[str, Any]] = []
        skipped_count = 0
        failed_count = 0

        for plugin in plugins_to_import:
            name = plugin.get("name", "")
            plugin_id = plugin.get("plugin_unique_identifier", "")
            source = plugin.get("source", "marketplace")
            version = plugin.get("version", "")

            # Determine identifier to install
            if latest:
                # For marketplace plugins, fetch latest version's unique_identifier
                if source == "marketplace":
                    latest_id = await _get_latest_plugin_version_async(name)
                    if latest_id:
                        install_id = latest_id
                    else:
                        typer.echo(f"  [FAIL] {name} - Could not fetch latest version from marketplace", err=True)
                        failed_count += 1
                        continue
                else:
                    install_id = name
            else:
                install_id = plugin_id if plugin_id else f"{name}:{version}" if version else name

            # Check if already installed
            if skip_existing and (install_id in existing_plugins or name in existing_plugins):
                typer.echo(f"  [SKIP] {name} (already installed)")
                skipped_count += 1
                continue

            # Prepare plugin for parallel install
            plugin_copy = plugin.copy()
            plugin_copy["plugin_unique_identifier"] = install_id
            plugins_filtered.append(plugin_copy)

        if not plugins_filtered:
            typer.echo(f"\nSummary: 0 installed, {skipped_count} skipped, {failed_count} failed")
            return

        typer.echo(f"Server: {server} ({server_config.base_url})")
        typer.echo(f"Installing {len(plugins_filtered)} plugin(s) in parallel (concurrency={max_concurrency})...\n")

        # Install plugins in parallel
        results = await client.install_plugins_parallel(plugins_filtered)

        # Process results
        installed_count = 0
        # Keep failed_count from earlier (fetching latest version failures)

        for plugin, (name, success, error) in zip(plugins_filtered, results):
            version = plugin.get("version", "latest" if latest else "")
            if success:
                typer.echo(f"  [OK] {name}:{version} (installed)")
                installed_count += 1
            else:
                error_msg = str(error) if error else "Unknown error"
                # Check for "already installed" error
                if "already" in error_msg.lower() or "installed" in error_msg.lower() or "exist" in error_msg.lower():
                    typer.echo(f"  [SKIP] {name}:{version} (already installed)")
                    skipped_count += 1
                else:
                    typer.echo(f"  [FAIL] {name}:{version} - {error_msg}", err=True)
                    failed_count += 1

        # Apply configs if requested (must be done serially after install)
        config_applied_count = 0
        if with_config:
            sync_client = get_console_client(server_config)
            for plugin in plugins_filtered:
                if plugin.get("config"):
                    installation_id = plugin.get("installation_id")
                    if installation_id:
                        try:
                            sync_client.update_plugin_config(installation_id, plugin["config"])
                            config_applied_count += 1
                        except Exception as config_err:
                            logger.warning("Failed to apply config for {}: {}", plugin.get("name"), config_err)

        # Summary
        typer.echo(f"\nSummary: {installed_count} installed, {skipped_count} skipped, {failed_count} failed")
        if with_config:
            typer.echo(f"         {config_applied_count} configs applied")


@app.command("upgrade")
def upgrade_plugins(
    ctx: typer.Context,
    server: str = typer.Option(..., "--server", "-s", help="Server instance name"),
    name: Optional[list[str]] = typer.Option(None, "--name", "-n", help="Plugin names to upgrade (can be repeated)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be upgraded without making changes"),
    parallel: bool = typer.Option(
        True, "--parallel/--serial", "-p/-P", help="Enable parallel operations (default: True)"
    ),
    concurrency: int = typer.Option(
        PLUGIN_MARKETPLACE_CONCURRENCY, "--concurrency", "-c", help="Max concurrent requests (marketplace limit: 3)"
    ),
) -> None:
    """
    Upgrade installed plugins to latest versions.

    By default upgrades all installed marketplace plugins.
    Use --name to specify particular plugins to upgrade.
    Use --dry-run to preview upgrades without making changes.

    Note: Only marketplace plugins can be upgraded. GitHub plugins need manual upgrade.
    """
    config = get_config(ctx)
    server_config = config.get_server_by_name(server)

    if server_config is None:
        typer.echo(f"Error: Server '{server}' not found in config", err=True)
        raise typer.Exit(1)

    client = get_console_client(server_config)

    try:
        # Get currently installed plugins
        installed_plugins = client.get_plugins()

        if not installed_plugins:
            typer.echo("No plugins installed")
            raise typer.Exit(0)

        typer.echo(f"Server: {server} ({server_config.base_url})")
        typer.echo(f"Checking {len(installed_plugins)} installed plugin(s) for upgrades...\n")

        # Filter plugins to upgrade
        plugins_to_check: list[dict[str, Any]] = []
        skipped_github = 0

        for plugin in installed_plugins:
            plugin_id = plugin.get("plugin_id", "")
            source = plugin.get("source", "marketplace")

            # Skip non-marketplace plugins
            if source != "marketplace":
                skipped_github += 1
                continue

            # If specific names provided, filter by them
            if name and plugin_id not in name:
                continue

            plugins_to_check.append(plugin)

        if not plugins_to_check:
            if name:
                typer.echo(f"No matching marketplace plugins found for: {', '.join(name)}")
            else:
                typer.echo("No marketplace plugins available for upgrade")
            if skipped_github > 0:
                typer.echo(f"  ({skipped_github} GitHub plugin(s) skipped - upgrade manually)")
            raise typer.Exit(0)

        # For upgrade, we reinstall with latest version
        # This is done by using the plugin name only (without version)
        plugins_to_upgrade: list[dict[str, Any]] = []

        for plugin in plugins_to_check:
            plugin_id = plugin.get("plugin_id", "")
            current_version = plugin.get("version", "unknown")
            installation_id = plugin.get("id", plugin.get("installation_id", ""))

            # Prepare upgrade info
            plugins_to_upgrade.append(
                {
                    "name": plugin_id,
                    "plugin_unique_identifier": plugin_id,  # Without version = latest
                    "current_version": current_version,
                    "installation_id": installation_id,
                    "source": "marketplace",
                }
            )

        if not plugins_to_upgrade:
            typer.echo("No plugins need upgrading")
            raise typer.Exit(0)

        # Display upgrade plan
        typer.echo(f"Plugins to upgrade ({len(plugins_to_upgrade)}):")
        for p in plugins_to_upgrade:
            typer.echo(f"  - {p['name']} (current: {p['current_version']} -> latest)")

        if dry_run:
            typer.echo("\n[DRY RUN] No changes made")
            if skipped_github > 0:
                typer.echo(f"  ({skipped_github} GitHub plugin(s) skipped - upgrade manually)")
            raise typer.Exit(0)

        typer.echo("")

        # Execute upgrade
        if parallel and len(plugins_to_upgrade) > 1:
            asyncio.run(_upgrade_plugins_parallel(server_config, plugins_to_upgrade, concurrency))
        else:
            _upgrade_plugins_serial(server_config, plugins_to_upgrade)

        if skipped_github > 0:
            typer.echo(f"\nNote: {skipped_github} GitHub plugin(s) skipped - upgrade manually")

    except typer.Exit:
        raise
    except Exception as e:
        logger.error("Failed to upgrade plugins: {}", e)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def _upgrade_plugins_serial(
    server_config: Any,
    plugins_to_upgrade: list[dict[str, Any]],
) -> None:
    """Upgrade plugins serially - each plugin is upgraded atomically with rollback on failure."""
    client = get_console_client(server_config)

    upgraded_count = 0
    failed_count = 0

    for plugin in plugins_to_upgrade:
        name = plugin["name"]
        current_version = plugin["current_version"]
        installation_id = plugin.get("installation_id")
        old_id = plugin.get("plugin_unique_identifier", name)

        # Get latest version's unique_identifier from marketplace
        latest_id = _get_latest_plugin_version(name)
        if not latest_id:
            typer.echo(f"  [FAIL] {name} - Could not fetch latest version from marketplace", err=True)
            failed_count += 1
            continue

        try:
            # Step 1: Uninstall old version
            if installation_id:
                client.uninstall_plugin(installation_id)

            # Step 2: Install latest version with full identifier
            client.install_plugin_from_marketplace([latest_id])

            typer.echo(f"  [OK] {name} (upgraded from {current_version})")
            upgraded_count += 1

        except Exception as e:
            error_msg = str(e)
            typer.echo(f"  [FAIL] {name} - {error_msg}", err=True)

            # Try to rollback - reinstall old version
            if installation_id:
                try:
                    client.install_plugin_from_marketplace([old_id])
                    typer.echo(f"  [ROLLBACK] {name} restored to {current_version}")
                except Exception as rollback_err:
                    typer.echo(f"  [ROLLBACK FAILED] {name} - {rollback_err}", err=True)

            failed_count += 1

    typer.echo(f"\nSummary: {upgraded_count} upgraded, {failed_count} failed")


async def _upgrade_plugins_parallel(
    server_config: Any,
    plugins_to_upgrade: list[dict[str, Any]],
    max_concurrency: int,
) -> None:
    """Upgrade plugins in parallel - each plugin is upgraded atomically (uninstall->install)."""
    async with get_async_console_client(server_config, max_concurrency) as client:
        await client.login()

        typer.echo(f"Upgrading {len(plugins_to_upgrade)} plugin(s) in parallel (concurrency={max_concurrency})...\n")

        # Pre-fetch all latest versions in parallel
        async def get_latest_id(name: str) -> tuple[str, Optional[str]]:
            latest_id = await _get_latest_plugin_version_async(name)
            return (name, latest_id)

        latest_tasks = [get_latest_id(p["name"]) for p in plugins_to_upgrade]
        latest_results = await asyncio.gather(*latest_tasks)
        latest_map = {name: latest_id for name, latest_id in latest_results}

        async def upgrade_single(plugin: dict[str, Any]) -> tuple[str, bool, Optional[Exception]]:
            """Upgrade a single plugin atomically: uninstall old -> install new."""
            name = plugin["name"]
            installation_id = plugin.get("installation_id")

            # Get pre-fetched latest version
            latest_id = latest_map.get(name)
            if not latest_id:
                return (name, False, Exception("Could not fetch latest version from marketplace"))

            try:
                # Step 1: Uninstall old version
                if installation_id:
                    await client.uninstall_plugin(installation_id)

                # Step 2: Install latest version with full identifier
                await client.install_plugin_from_marketplace([latest_id])

                return (name, True, None)
            except Exception as e:
                logger.error("Failed to upgrade plugin {}: {}", name, e)
                # Try to reinstall old version if we uninstalled it
                if installation_id:
                    old_id = plugin.get("plugin_unique_identifier", name)
                    try:
                        await client.install_plugin_from_marketplace([old_id])
                        logger.info("Rolled back plugin {} to previous version", name)
                    except Exception as rollback_err:
                        logger.error("Failed to rollback plugin {}: {}", name, rollback_err)
                return (name, False, e)

        # Execute upgrades with concurrency control (semaphore in client handles this)
        tasks = [upgrade_single(plugin) for plugin in plugins_to_upgrade]
        results = await asyncio.gather(*tasks)

        # Process results
        upgraded_count = 0
        failed_count = 0

        for plugin, (name, success, error) in zip(plugins_to_upgrade, results):
            current_version = plugin["current_version"]
            if success:
                typer.echo(f"  [OK] {name} (upgraded from {current_version})")
                upgraded_count += 1
            else:
                error_msg = str(error) if error else "Unknown error"
                typer.echo(f"  [FAIL] {name} - {error_msg}", err=True)
                failed_count += 1

        typer.echo(f"\nSummary: {upgraded_count} upgraded, {failed_count} failed")
