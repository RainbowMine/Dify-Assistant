"""
App Commands

Provides CLI commands for app management (tags, list, export, import).
Supports parallel operations for batch export/import.
"""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import anyio
import typer
from loguru import logger

from dify_assistant.cli.utils import (
    get_async_console_client,
    get_config,
    get_console_client,
)
from dify_assistant.constants import CLI_DEFAULT_CONCURRENCY

if TYPE_CHECKING:
    from dify_assistant.cli.console_client import ConsoleClient
    from dify_assistant.config import DifyServerConfig

app = typer.Typer(no_args_is_help=True)


@app.command("tags")
def tags(
    ctx: typer.Context,
    server: str = typer.Option(..., "--server", "-s", help="Server instance name"),
) -> None:
    """
    List all tags from a server.
    """
    config = get_config(ctx)
    server_config = config.get_server_by_name(server)

    if server_config is None:
        typer.echo(f"Error: Server '{server}' not found in config", err=True)
        raise typer.Exit(1)

    client = get_console_client(server_config)

    try:
        result = client.get_tags()
        if not result:
            typer.echo("No tags found")
            return

        typer.echo("Tags:")
        for tag in result:
            if isinstance(tag, dict):
                tag_name = tag.get("name", "unknown")
                tag_id = tag.get("id", "")
                typer.echo(f"  - {tag_name} (id: {tag_id})")
            else:
                typer.echo(f"  - {tag}")
    except Exception as e:
        logger.error("Failed to get tags: {}", e)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("list")
def list_apps(
    ctx: typer.Context,
    server: str = typer.Option(..., "--server", "-s", help="Server instance name"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
) -> None:
    """
    List apps from a server.
    """
    config = get_config(ctx)
    server_config = config.get_server_by_name(server)

    if server_config is None:
        typer.echo(f"Error: Server '{server}' not found in config", err=True)
        raise typer.Exit(1)

    client = get_console_client(server_config)

    try:
        apps = client.get_apps(tag=tag)
        if not apps:
            typer.echo("No apps found")
            return

        typer.echo(f"Apps ({len(apps)}):")
        for app_info in apps:
            app_id = app_info.get("id", "unknown")
            app_name = app_info.get("name", "unnamed")
            app_mode = app_info.get("mode", "unknown")
            # Extract tag names from tags list
            tags = app_info.get("tags", [])
            tag_names = [t.get("name", "") for t in tags if isinstance(t, dict) and t.get("name")]
            tag_str = f" [{', '.join(tag_names)}]" if tag_names else ""
            typer.echo(f"  [{app_mode}] {app_name} ({app_id}){tag_str}")
    except Exception as e:
        logger.error("Failed to list apps: {}", e)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("export")
def export_apps(
    ctx: typer.Context,
    server: str = typer.Option(..., "--server", "-s", help="Server instance name"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Export apps with specific tag"),
    app_id: Optional[str] = typer.Option(None, "--id", "-i", help="Export single app by id"),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory",
        file_okay=False,
        dir_okay=True,
    ),
    parallel: bool = typer.Option(True, "--parallel/--serial", "-p/-P", help="Enable parallel export (default: True)"),
    concurrency: int = typer.Option(CLI_DEFAULT_CONCURRENCY, "--concurrency", "-c", help="Max concurrent requests"),
) -> None:
    """
    Export apps from a server in YAML format.

    By default exports all apps in parallel. Use --tag to filter by tag or --id for a single app.
    Use --serial to disable parallel processing.
    """
    config = get_config(ctx)
    server_config = config.get_server_by_name(server)

    if server_config is None:
        typer.echo(f"Error: Server '{server}' not found in config", err=True)
        raise typer.Exit(1)

    # Ensure output directory exists
    output.mkdir(parents=True, exist_ok=True)

    try:
        if app_id:
            # Export single app (use sync client)
            client = get_console_client(server_config)
            _export_single_app(client, app_id, output)
        elif parallel:
            # Parallel export
            asyncio.run(_export_apps_parallel(server_config, tag, output, concurrency))
        else:
            # Serial export (original behavior)
            client = get_console_client(server_config)
            apps = client.get_apps(tag=tag)
            if not apps:
                typer.echo("No apps found to export")
                return

            typer.echo(f"Exporting {len(apps)} app(s) serially...")
            for app_info in apps:
                _export_single_app(client, app_info["id"], output)

        typer.echo(f"Export completed to {output}")
    except Exception as e:
        logger.error("Failed to export apps: {}", e)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


async def _export_apps_parallel(
    server_config: "DifyServerConfig",
    tag: Optional[str],
    output: Path,
    max_concurrency: int,
) -> None:
    """Export apps in parallel using async client."""

    async with get_async_console_client(server_config, max_concurrency) as client:
        await client.login()
        typer.echo("Logged in successfully")

        # Get apps list
        apps = await client.get_apps(tag=tag)
        if not apps:
            typer.echo("No apps found to export")
            return

        typer.echo(f"Exporting {len(apps)} app(s) in parallel (concurrency={max_concurrency})...")

        app_ids = [app["id"] for app in apps]

        # Export all apps in parallel
        results = await client.export_apps_parallel(app_ids)

        # Get app info for filenames (also in parallel)
        app_infos = await client.get_apps_info_parallel(app_ids)
        app_info_map = {app_id: info for app_id, info, _ in app_infos if info}

        # Save results
        success_count = 0
        error_count = 0
        for app_id, yaml_content, error in results:
            if error:
                typer.echo(f"  Failed: {app_id} - {error}", err=True)
                error_count += 1
            elif yaml_content is not None and yaml_content != "":
                # Get app name for filename
                app_info = app_info_map.get(app_id, {})
                app_name = app_info.get("name", app_id)
                safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in app_name)
                filename = f"{safe_name}_{app_id}.yaml"
                filepath = output / filename

                # Write file in thread pool to avoid blocking event loop
                await anyio.to_thread.run_sync(_write_file_sync, filepath, yaml_content)

                typer.echo(f"  Exported: {filename}")
                success_count += 1
            else:
                typer.echo(f"  Skipped: {app_id} (empty content)", err=True)
                error_count += 1

        typer.echo(f"Done: {success_count} exported, {error_count} failed")


def _write_file_sync(filepath: Path, content: str) -> None:
    """Write file synchronously (called from thread pool)."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def _read_file_sync(filepath: Path) -> str:
    """Read file synchronously (called from thread pool)."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _export_single_app(client: "ConsoleClient", app_id: str, output: Path) -> None:
    """Export a single app to YAML file."""

    yaml_content = client.export_app(app_id)
    # Get app info for filename
    app_info = client.get_app(app_id)
    app_name = app_info.get("name", app_id) if app_info else app_id
    # Sanitize filename
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in app_name)
    filename = f"{safe_name}_{app_id}.yaml"
    filepath = output / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    typer.echo(f"  Exported: {filename}")


@app.command("import")
def import_apps(
    ctx: typer.Context,
    server: str = typer.Option(..., "--server", "-s", help="Server instance name"),
    path: Path = typer.Option(..., "--input", "-i", help="YAML file or directory to import", exists=True),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Tag to apply to all imported apps"),
    parallel: bool = typer.Option(True, "--parallel/--serial", "-p/-P", help="Enable parallel import (default: True)"),
    concurrency: int = typer.Option(CLI_DEFAULT_CONCURRENCY, "--concurrency", "-c", help="Max concurrent requests"),
) -> None:
    """
    Import apps to a server from YAML file or directory.

    By default imports in parallel when importing multiple files.
    Use --serial to disable parallel processing.
    Use --tag to apply a tag to all imported apps.
    """
    config = get_config(ctx)
    server_config = config.get_server_by_name(server)

    if server_config is None:
        typer.echo(f"Error: Server '{server}' not found in config", err=True)
        raise typer.Exit(1)

    try:
        if path.is_file():
            # Import single file (use sync client)
            client = get_console_client(server_config)
            _import_single_file(client, path, tag)
        elif path.is_dir():
            # Import all YAML files in directory
            yaml_files = list(path.glob("*.yaml")) + list(path.glob("*.yml"))
            if not yaml_files:
                typer.echo("No YAML files found in directory")
                return

            if parallel and len(yaml_files) > 1:
                # Parallel import
                asyncio.run(_import_apps_parallel(server_config, yaml_files, concurrency, tag))
            else:
                # Serial import
                client = get_console_client(server_config)
                typer.echo(f"Importing {len(yaml_files)} file(s) serially...")
                for yaml_file in yaml_files:
                    _import_single_file(client, yaml_file, tag)
        else:
            typer.echo(f"Error: Path '{path}' is not a file or directory", err=True)
            raise typer.Exit(1)

        typer.echo("Import completed")
    except Exception as e:
        logger.error("Failed to import apps: {}", e)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


async def _import_apps_parallel(
    server_config: "DifyServerConfig",
    yaml_files: list[Path],
    max_concurrency: int,
    tag: Optional[str] = None,
) -> None:
    """Import apps in parallel using async client."""
    async with get_async_console_client(server_config, max_concurrency) as client:
        await client.login()

        # Get or create tag if specified
        tag_id: Optional[str] = None
        if tag:
            typer.echo(f"Getting or creating tag '{tag}'...")
            tag_id = await client.get_or_create_tag(tag)

        typer.echo(f"Importing {len(yaml_files)} file(s) in parallel (concurrency={max_concurrency})...")

        # Read all YAML files in thread pool to avoid blocking event loop
        yaml_contents: list[tuple[str, str]] = []
        for yaml_file in yaml_files:
            content = await anyio.to_thread.run_sync(_read_file_sync, yaml_file)
            yaml_contents.append((yaml_file.name, content))

        # Import all files in parallel
        results = await client.import_apps_parallel(yaml_contents)

        # Report results and bind tags
        success_count = 0
        error_count = 0
        for filename, result, error in results:
            if error:
                typer.echo(f"  Failed: {filename} - {error}", err=True)
                error_count += 1
            elif result:
                app_name = result.get("name", filename)
                app_id = result.get("app_id", "unknown")
                typer.echo(f"  Imported: {app_name} ({app_id})")
                success_count += 1

                # Bind tag if specified
                if tag_id and app_id != "unknown":
                    try:
                        await client.bind_tag_to_app(app_id, tag_id)
                        typer.echo(f"    Tagged with '{tag}'")
                    except Exception as e:
                        typer.echo(f"    Failed to tag: {e}", err=True)

        typer.echo(f"Done: {success_count} imported, {error_count} failed")


def _import_single_file(client: "ConsoleClient", filepath: Path, tag: Optional[str] = None) -> None:
    """Import a single YAML file."""

    with open(filepath, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    result = client.import_app(yaml_content)
    app_name = result.get("name", filepath.stem)
    app_id = result.get("app_id", "unknown")
    typer.echo(f"  Imported: {app_name} ({app_id})")

    # Bind tag if specified
    if tag and app_id != "unknown":
        try:
            tag_id = client.get_or_create_tag(tag)
            client.bind_tag_to_app(app_id, tag_id)
            typer.echo(f"    Tagged with '{tag}'")
        except Exception as e:
            typer.echo(f"    Failed to tag: {e}", err=True)


@app.command("delete")
def delete_apps(
    ctx: typer.Context,
    server: str = typer.Option(..., "--server", "-s", help="Server instance name"),
    app_id: Optional[str] = typer.Option(None, "--id", "-i", help="Delete single app by id"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Delete apps with specific tag"),
    all_apps: bool = typer.Option(False, "--all", "-a", help="Delete all apps (requires confirmation)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    parallel: bool = typer.Option(True, "--parallel/--serial", "-p/-P", help="Enable parallel delete (default: True)"),
    concurrency: int = typer.Option(CLI_DEFAULT_CONCURRENCY, "--concurrency", "-c", help="Max concurrent requests"),
) -> None:
    """
    Delete apps from a server.

    Must specify one of: --id (single app), --tag (apps with tag), or --all (all apps).
    Use --yes to skip confirmation prompt for batch deletion.
    """
    config = get_config(ctx)
    server_config = config.get_server_by_name(server)

    if server_config is None:
        typer.echo(f"Error: Server '{server}' not found in config", err=True)
        raise typer.Exit(1)

    # Validate options: exactly one of app_id, tag, or all_apps must be specified
    options_set = sum([bool(app_id), bool(tag), all_apps])
    if options_set == 0:
        typer.echo("Error: Must specify one of --id, --tag, or --all", err=True)
        raise typer.Exit(1)
    if options_set > 1:
        typer.echo("Error: Can only specify one of --id, --tag, or --all", err=True)
        raise typer.Exit(1)

    try:
        if app_id:
            # Delete single app
            if not yes:
                confirm = typer.confirm(f"Delete app {app_id}?")
                if not confirm:
                    typer.echo("Aborted")
                    raise typer.Exit(0)

            client = get_console_client(server_config)
            client.delete_app(app_id)
            typer.echo(f"Deleted app: {app_id}")
        else:
            # Delete multiple apps (by tag or all)
            client = get_console_client(server_config)
            apps = client.get_apps(tag=tag)

            if not apps:
                typer.echo("No apps found to delete")
                return

            # Show apps to be deleted
            typer.echo(f"Apps to be deleted ({len(apps)}):")
            for app_info in apps:
                aid = app_info.get("id", "unknown")
                aname = app_info.get("name", "unnamed")
                typer.echo(f"  - {aname} ({aid})")

            # Confirm deletion
            if not yes:
                if all_apps:
                    confirm = typer.confirm(f"Delete ALL {len(apps)} app(s)? This cannot be undone!")
                else:
                    confirm = typer.confirm(f"Delete {len(apps)} app(s) with tag '{tag}'?")
                if not confirm:
                    typer.echo("Aborted")
                    raise typer.Exit(0)

            app_ids = [a["id"] for a in apps]

            if parallel and len(app_ids) > 1:
                # Parallel delete
                asyncio.run(_delete_apps_parallel(server_config, app_ids, concurrency))
            else:
                # Serial delete
                typer.echo(f"Deleting {len(app_ids)} app(s) serially...")
                for aid in app_ids:
                    client.delete_app(aid)
                    typer.echo(f"  Deleted: {aid}")
                typer.echo(f"Done: {len(app_ids)} deleted")

    except typer.Exit:
        raise
    except Exception as e:
        logger.error("Failed to delete apps: {}", e)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


async def _delete_apps_parallel(
    server_config: "DifyServerConfig",
    app_ids: list[str],
    max_concurrency: int,
) -> None:
    """Delete apps in parallel using async client."""
    async with get_async_console_client(server_config, max_concurrency) as client:
        await client.login()
        typer.echo(f"Deleting {len(app_ids)} app(s) in parallel (concurrency={max_concurrency})...")

        results = await client.delete_apps_parallel(app_ids)

        success_count = 0
        error_count = 0
        for aid, success, error in results:
            if error:
                typer.echo(f"  Failed: {aid} - {error}", err=True)
                error_count += 1
            else:
                typer.echo(f"  Deleted: {aid}")
                success_count += 1

        typer.echo(f"Done: {success_count} deleted, {error_count} failed")
