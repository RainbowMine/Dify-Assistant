"""
Plugin Commands

Provides CLI commands for plugin management (list, export, import).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
import typer
from loguru import logger

from dify_assistant.cli.utils import get_config, get_console_client

app = typer.Typer(no_args_is_help=True)


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
    skip_existing: bool = typer.Option(False, "--skip-existing", help="Skip already installed plugins"),
) -> None:
    """
    Import and install plugins to a server from an export file.

    By default installs the exact version from the export file.
    Use --latest to install the latest available version.
    Use --with-config to apply configurations (export file must include config).
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

    client = get_console_client(server_config)

    try:
        # Get existing plugins if skip_existing is enabled
        existing_plugins: set[str] = set()
        if skip_existing:
            installed = client.get_plugins()
            for p in installed:
                pid = p.get("plugin_id", "")
                # Store both full identifier and name-only
                existing_plugins.add(pid)
                if ":" in pid:
                    existing_plugins.add(pid.rsplit(":", 1)[0])

        typer.echo(f"Server: {server} ({server_config.base_url})")
        typer.echo(f"Importing {len(plugins_to_import)} plugin(s)...\n")

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
                # Use name only for latest version
                install_id = name
            else:
                # Use full identifier with version
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
                    # Default to marketplace
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
                # Check if it's an "already installed" error
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
