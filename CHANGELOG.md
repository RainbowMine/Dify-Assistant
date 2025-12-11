# Changelog

## 2025.1.2.20251211

> 2025-12-11

### Added

- **Plugin CLI commands**: New `dify plugin` command group for plugin management
  - `dify plugin list`: List all installed plugins from a server
  - `dify plugin export`: Export installed plugins list to JSON file
  - `dify plugin import`: Import and install plugins from export file
  - `dify plugin upgrade`: Upgrade installed plugins to latest versions
- **Plugin API methods** in `ConsoleClient` and `AsyncConsoleClient`:
  - `get_plugins()`: Get all installed plugins
  - `install_plugin_from_marketplace()`: Install plugins from Dify marketplace
  - `install_plugin_from_github()`: Install plugins from GitHub repository
  - `uninstall_plugin()`: Uninstall a plugin by installation ID
  - `get_plugin_tasks()`: Get plugin installation task status
  - `update_plugin_config()`: Update plugin configuration
  - `install_plugins_parallel()`: Install multiple plugins in parallel
  - `uninstall_plugins_parallel()`: Uninstall multiple plugins in parallel

### Features

- Support exporting plugin configurations with `--with-config` flag
- Support importing with version lock or latest version (`--latest` flag)
- Support skipping already installed plugins (`--skip-existing`, enabled by default)
- Support stdin/stdout for piping export to import between servers
- Support parallel and serial modes for import/upgrade operations
- Marketplace concurrency limit enforcement (default: 3 concurrent requests)
- Automatic latest version lookup from marketplace when using `--latest` flag
- Upgrade command with dry-run mode to preview changes before applying

### Changed

- `--skip-existing` is now enabled by default for plugin import (use `--no-skip-existing` to disable)
- Default concurrency for plugin operations reduced to 3 to respect marketplace limits

### Fixed

- Fixed plugin import failing with 400 errors when plugins are already installed
- Fixed `--latest` flag not correctly fetching full plugin identifier from marketplace
- Fixed parallel import attempting all requests simultaneously instead of respecting concurrency limit

## 2025.1.1.20251210

> 2025-12-10

- Init project
