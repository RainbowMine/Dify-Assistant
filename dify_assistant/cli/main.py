"""
CLI Main Entry Point

Provides the main Typer application and global options.
"""

from pathlib import Path
from typing import Optional

import typer

from dify_assistant.cli import app_cmd, plugin_cmd
from dify_assistant.constants import DEFAULT_CONFIG_FILE

app = typer.Typer(
    name="dify",
    help="Dify Assistant CLI - App migration tool for Dify servers",
    no_args_is_help=True,
)

# Register sub-commands
app.add_typer(app_cmd.app, name="app", help="App management commands")
app.add_typer(plugin_cmd.app, name="plugin", help="Plugin management commands")


@app.callback()
def main(
    ctx: typer.Context,
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help=f"Config file path (default: {DEFAULT_CONFIG_FILE})",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
) -> None:
    """
    Dify Assistant CLI - App migration tool for Dify servers.
    """
    # Store config path in context for sub-commands
    ctx.ensure_object(dict)
    ctx.obj["config"] = config or Path(DEFAULT_CONFIG_FILE)


if __name__ == "__main__":
    app()
