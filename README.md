# Dify Assistant

A Python client library and CLI tool for [Dify](https://dify.ai/) - an LLM application development platform.

## Features

- **Python Client Library**: Sync/async API clients with streaming support
- **CLI Tool**: Manage apps and plugins across multiple Dify servers
- **Type Safety**: Full Pydantic model validation with type hints

## Installation

```bash
pip install dify-assistant
```

Or with uv:

```bash
uv add dify-assistant
```

## Quick Start

### Python Client

```python
from dify_assistant import DifyClient, ResponseMode

with DifyClient(
    base_url="https://api.dify.ai/v1",
    api_key="app-xxx"
) as client:
    response = client.chat.send_message(
        query="Hello!",
        user="user-123",
        response_mode=ResponseMode.BLOCKING
    )
    print(response.answer)
```

### CLI Tool

```bash
# List apps
dify app list -s dev

# Export/import apps
dify app export -s dev -o ./backup/
dify app import -s prod -i ./backup/

# Migrate plugins between servers
dify plugin export -s dev | dify plugin import -s prod
```

## Documentation

See [User Guide](docs/user-guide.md) for complete documentation.

## Development

```bash
uv sync
pytest
```

## License

MIT License - see [LICENSE](LICENSE) for details.
