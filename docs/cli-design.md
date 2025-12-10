# Dify Assistant CLI Design

## Overview

Command-line interface for managing Dify servers, including app and plugin migration.

## Configuration

Default configuration file: `app.toml`

```toml
[servers.dev]
base_url = "https://dev.dify.example.com"
email = "admin@example.com"
password = "xxx"

[servers.prod]
base_url = "https://prod.dify.example.com"
email = "admin@example.com"
password = "yyy"
```

## Command Structure

```text
dify
├── app
│   ├── tags      # List tags
│   ├── list      # List apps
│   ├── export    # Export apps to YAML
│   ├── import    # Import apps from YAML
│   └── delete    # Delete apps
└── plugin
    ├── list      # List installed plugins
    ├── export    # Export plugin list to JSON
    └── import    # Import and install plugins from JSON
```

## Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--config` | `-c` | Config file path (default: `app.toml`) |

## App Commands

### dify app tags

List all tags from a server.

```bash
dify app tags -s <server>
```

### dify app list

List apps, optionally filtered by tag.

```bash
dify app list -s <server> [-t <tag>]
```

### dify app export

Export apps in YAML format.

```bash
dify app export -s <server> [-t <tag>] [-i <id>] [-o <dir>]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--tag` | `-t` | Export apps with specific tag |
| `--id` | `-i` | Export single app by ID |
| `--output` | `-o` | Output directory (default: `./`) |

### dify app import

Import apps from YAML file or directory.

```bash
dify app import -s <server> -i <path> [-t <tag>] [-p|-P] [-c <n>]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--input` | `-i` | YAML file or directory (required) |
| `--tag` | `-t` | Tag to apply to imported apps |
| `--parallel/--serial` | `-p/-P` | Parallel or serial import |
| `--concurrency` | `-c` | Max concurrent requests (default: 16) |

### dify app delete

Delete apps by ID, tag, or all.

```bash
dify app delete -s <server> [--id <id> | --tag <tag> | --all] [-y]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--id` | `-i` | Delete single app by ID |
| `--tag` | `-t` | Delete apps with specific tag |
| `--all` | `-a` | Delete all apps |
| `--yes` | `-y` | Skip confirmation |

## Plugin Commands

### dify plugin list

List all installed plugins.

```bash
dify plugin list -s <server> [-f <format>]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--format` | `-f` | Output format: `table` or `json` (default: table) |

### dify plugin export

Export installed plugins list to JSON.

```bash
dify plugin export -s <server> [-o <file>] [--with-config]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--output` | `-o` | Output file (default: stdout) |
| `--with-config` | | Include plugin configurations |

Export format:

```json
{
  "version": "1.0",
  "exported_at": "2025-01-15T10:30:00Z",
  "source_server": "dev",
  "include_config": false,
  "plugins": [
    {
      "name": "langgenius/openai",
      "plugin_unique_identifier": "langgenius/openai:1.2.0@hash",
      "source": "marketplace",
      "version": "1.2.0",
      "installation_id": "xxx-xxx-xxx"
    }
  ]
}
```

### dify plugin import

Import and install plugins from JSON file.

```bash
dify plugin import -s <server> [-i <file>] [--latest] [--with-config] [--skip-existing]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--input` | `-i` | Input file (default: stdin) |
| `--latest` | | Install latest version instead of exported version |
| `--with-config` | | Apply plugin configurations |
| `--skip-existing` | | Skip already installed plugins |

## Authentication

Uses email/password from config file. Access token is obtained at runtime and kept in memory.
