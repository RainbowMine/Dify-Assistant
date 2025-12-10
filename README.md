# Dify Assistant

A CLI tool for managing [Dify](https://dify.ai/) apps and plugins across multiple servers.

## Features

- Manage apps and plugins across multiple Dify servers
- Export/import for backup and migration
- Full type safety with Pydantic models

## Installation

```bash
git clone <repo-url>
cd dify-assistant
uv sync
```

## CLI Usage

```bash
# List apps
uv run dify app list -s dev

# Export/import apps
uv run dify app export -s dev -o ./backup/
uv run dify app import -s prod -i ./backup/

# Migrate plugins between servers
uv run dify plugin export -s dev | uv run dify plugin import -s prod
```

## Documentation

See [User Guide](docs/user-guide.md) for complete documentation.

## Development

```bash
uv sync
uv run pytest
```

## License

MIT License - see [LICENSE](LICENSE) for details.
