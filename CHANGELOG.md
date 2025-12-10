# Changelog

## 2025.1.2.20251211

> 2025-12-11

### Added

- **Plugin CLI commands**: New `dify plugin` command group for plugin management
  - `dify plugin list`: List all installed plugins from a server
  - `dify plugin export`: Export installed plugins list to JSON file
  - `dify plugin import`: Import and install plugins from export file
- **Plugin API methods** in `ConsoleClient`:
  - `get_plugins()`: Get all installed plugins
  - `install_plugin_from_marketplace()`: Install plugins from Dify marketplace
  - `install_plugin_from_github()`: Install plugins from GitHub repository
  - `uninstall_plugin()`: Uninstall a plugin by installation ID
  - `get_plugin_tasks()`: Get plugin installation task status
  - `update_plugin_config()`: Update plugin configuration

### Features

- Support exporting plugin configurations with `--with-config` flag
- Support importing with version lock or latest version (`--latest` flag)
- Support skipping already installed plugins (`--skip-existing` flag)
- Support stdin/stdout for piping export to import between servers

## 2025.1.1.20251210

> 2025-12-10

- Init project
