"""
Constants and default values for the Dify Assistant library.

This module centralizes all magic numbers, default values, and constants
to improve maintainability and make configuration more explicit.
"""

from http import HTTPStatus

# HTTP Status Codes (using stdlib for clarity)
HTTP_BAD_REQUEST = HTTPStatus.BAD_REQUEST  # 400
HTTP_UNAUTHORIZED = HTTPStatus.UNAUTHORIZED  # 401
HTTP_NOT_FOUND = HTTPStatus.NOT_FOUND  # 404
HTTP_TOO_MANY_REQUESTS = HTTPStatus.TOO_MANY_REQUESTS  # 429
HTTP_INTERNAL_SERVER_ERROR = HTTPStatus.INTERNAL_SERVER_ERROR  # 500

# Default timeout values (in seconds)
DEFAULT_TIMEOUT = 120.0
DEFAULT_SSE_TIMEOUT = 60.0

# Default pagination
DEFAULT_PAGE_LIMIT = 100

# Default concurrency
DEFAULT_MAX_CONCURRENCY = 5
CLI_DEFAULT_CONCURRENCY = 16

# Plugin marketplace concurrency (API limit is 3)
PLUGIN_MARKETPLACE_CONCURRENCY = 3

# Default config file path
DEFAULT_CONFIG_FILE = "app.toml"
