# Dify Assistant User Guide

## Installation

```bash
pip install dify-assistant
```

Or with uv:

```bash
uv add dify-assistant
```

## Configuration

Create a configuration file `app.toml` in your working directory:

```toml
[servers.dev]
base_url = "https://dev.dify.example.com"
email = "admin"
password = "your-password"

[servers.prod]
base_url = "https://prod.dify.example.com"
email = "admin"
password = "your-password"
```

You can define multiple servers with different names (e.g., `dev`, `prod`, `staging`).

## CLI Commands

### Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--config` | `-c` | Config file path (default: `app.toml`) |
| `--help` | | Show help message |

### List Tags

List all tags from a server:

```bash
dify app tags -s <server>
```

**Examples:**

```bash
dify app tags -s dev
dify app tags --server prod
```

### List Apps

List apps from a server, optionally filtered by tag:

```bash
dify app list -s <server> [-t <tag>]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--tag` | `-t` | Filter by tag |

**Examples:**

```bash
# List all apps
dify app list -s dev

# List apps with specific tag
dify app list -s dev -t production
dify app list --server dev --tag staging
```

### Export Apps

Export apps from a server in YAML format:

```bash
dify app export -s <server> [-t <tag>] [-i <id>] [-o <dir>]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--tag` | `-t` | Export apps with specific tag |
| `--id` | `-i` | Export single app by ID |
| `--output` | `-o` | Output directory (default: `./`) |

By default, exports all apps. Use `--tag` to filter by tag or `--id` for a single app.

**Examples:**

```bash
# Export all apps to current directory
dify app export -s dev

# Export all apps to specific directory
dify app export -s dev -o ./backup/

# Export apps with specific tag
dify app export -s dev -t production
dify app export -s dev -t production -o ./backup/

# Export single app by ID
dify app export -s dev -i abc123
dify app export -s dev --id abc123 -o ./backup/
```

### Import Apps

Import apps to a server from YAML file or directory:

```bash
dify app import -s <server> -i <path> [-t <tag>]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--input` | `-i` | YAML file or directory to import (required) |
| `--tag` | `-t` | Tag to apply to all imported apps |
| `--parallel/--serial` | `-p/-P` | Enable/disable parallel import (default: parallel) |
| `--concurrency` | `-c` | Max concurrent requests (default: 16) |

**Examples:**

```bash
# Import single file
dify app import -s prod -i ./my-app.yaml

# Import all YAML files from directory
dify app import -s prod -i ./backup/
dify app import --server prod --input ./backup/

# Import and tag all imported apps
dify app import -s prod -i ./backup/ --tag imported-2024
dify app import -s prod -i ./my-app.yaml -t production

# Import with serial mode (disable parallel)
dify app import -s prod -i ./backup/ --serial
dify app import -s prod -i ./backup/ -P

# Import with custom concurrency
dify app import -s prod -i ./backup/ --concurrency 10
```

The `--tag` option will:

- Create the tag if it doesn't exist
- Apply the tag to all successfully imported apps
- Report tagging status for each app

### Delete Apps

Delete apps from a server by ID, tag, or all apps:

```bash
dify app delete -s <server> [--id <id> | --tag <tag> | --all] [-y]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--id` | `-i` | Delete single app by ID |
| `--tag` | `-t` | Delete apps with specific tag |
| `--all` | `-a` | Delete all apps (use with caution) |
| `--yes` | `-y` | Skip confirmation prompt |
| `--parallel/--serial` | `-p/-P` | Enable/disable parallel delete (default: parallel) |
| `--concurrency` | `-c` | Max concurrent requests (default: 16) |

You must specify exactly one of `--id`, `--tag`, or `--all`.

**Examples:**

```bash
# Delete single app by ID
dify app delete -s dev -i abc123
dify app delete -s dev --id abc123

# Delete all apps with specific tag
dify app delete -s dev -t deprecated
dify app delete -s dev --tag old-version

# Delete all apps (requires confirmation)
dify app delete -s dev --all
dify app delete -s dev -a

# Skip confirmation prompt
dify app delete -s dev -t deprecated --yes
dify app delete -s dev --all -y

# Delete with serial mode (disable parallel)
dify app delete -s dev -t deprecated --serial
dify app delete -s dev -t deprecated -P

# Delete with custom concurrency
dify app delete -s dev -t deprecated --concurrency 10
```

**Safety Features:**

- Confirmation prompt before deletion (bypass with `--yes`)
- Shows list of apps to be deleted before confirming
- Reports success/failure count after batch deletion

## Common Workflows

### Migrate Apps Between Servers

Export from source server and import to target server:

```bash
# Export all apps from dev
dify app export -s dev -o ./migration/

# Import to prod with a migration tag
dify app import -s prod ./migration/ --tag migrated-from-dev
```

### Backup Apps by Tag

```bash
# Backup production apps
dify app export -s prod -t production -o ./backup/production/

# Backup staging apps
dify app export -s prod -t staging -o ./backup/staging/
```

### Import and Organize with Tags

```bash
# Import apps and tag them for organization
dify app import -s prod ./new-features/ --tag feature-release-v2
dify app import -s prod ./hotfixes/ --tag hotfix-2024-01
```

### Clean Up Old Apps

```bash
# Delete apps with deprecated tag
dify app delete -s dev -t deprecated -y

# Delete all apps from a test server
dify app delete -s test --all -y
```

### Replace Apps by Tag

Export, delete, and re-import apps with the same tag:

```bash
# Backup current apps
dify app export -s prod -t my-feature -o ./backup/

# Delete old versions
dify app delete -s prod -t my-feature -y

# Import updated versions
dify app import -s prod ./updated/ -t my-feature
```

### Use Custom Config File

```bash
dify -c /path/to/config.toml app list -s dev
dify --config ./my-config.toml app export -s dev
```

## Authentication

Authentication uses email/password from the config file. The access token is obtained at runtime and kept in memory during command execution.

## Plugin Management

### List Plugins

List all installed plugins from a server:

```bash
dify plugin list -s <server> [-f <format>]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--format` | `-f` | Output format: `table` or `json` (default: table) |

**Examples:**

```bash
# List plugins as table
dify plugin list -s dev

# List plugins as JSON
dify plugin list -s dev -f json
dify plugin list --server prod --format json
```

### Export Plugins

Export installed plugins list from a server:

```bash
dify plugin export -s <server> [-o <file>] [--with-config]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--output` | `-o` | Output file path (default: stdout) |
| `--with-config` | | Include plugin configurations (may contain sensitive data) |

This exports the list of installed plugins (not the plugin packages themselves).

**Examples:**

```bash
# Export to stdout
dify plugin export -s dev

# Export to file
dify plugin export -s dev -o plugins.json

# Export with configurations
dify plugin export -s dev -o plugins.json --with-config
```

**Export File Format:**

```json
{
  "version": "1.0",
  "exported_at": "2025-01-15T10:30:00Z",
  "source_server": "dev",
  "include_config": false,
  "plugins": [
    {
      "name": "langgenius/openai",
      "plugin_unique_identifier": "langgenius/openai:1.2.0@abc123",
      "source": "marketplace",
      "version": "1.2.0",
      "installation_id": "xxx-xxx-xxx"
    }
  ]
}
```

### Import Plugins

Import and install plugins to a server from an export file:

```bash
dify plugin import -s <server> [-i <file>] [--latest] [--with-config] [--skip-existing]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | `-s` | Server name (required) |
| `--input` | `-i` | Input file path (default: stdin) |
| `--latest` | | Install latest version instead of exported version |
| `--with-config` | | Apply plugin configurations (export must include config) |
| `--skip-existing` | | Skip already installed plugins |

By default, installs the exact version from the export file.

**Examples:**

```bash
# Import from file
dify plugin import -s prod -i plugins.json

# Import from stdin (pipe)
dify plugin export -s dev | dify plugin import -s prod

# Install latest versions
dify plugin import -s prod -i plugins.json --latest

# Apply configurations
dify plugin import -s prod -i plugins.json --with-config

# Skip already installed plugins
dify plugin import -s prod -i plugins.json --skip-existing

# Combined options
dify plugin import -s prod -i plugins.json --latest --skip-existing
```

## Plugin Workflows

### Migrate Plugins Between Servers

Export from source server and import to target server:

```bash
# Method 1: Using files
dify plugin export -s dev -o plugins.json
dify plugin import -s prod -i plugins.json

# Method 2: Using pipe (direct transfer)
dify plugin export -s dev | dify plugin import -s prod
```

### Sync Plugins with Latest Versions

```bash
# Export current plugins and import latest versions
dify plugin export -s dev -o plugins.json
dify plugin import -s prod -i plugins.json --latest --skip-existing
```

### Backup and Restore Plugin Configurations

```bash
# Backup with configurations
dify plugin export -s prod -o plugins-backup.json --with-config

# Restore with configurations
dify plugin import -s prod -i plugins-backup.json --with-config
```
