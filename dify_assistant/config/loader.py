"""
Configuration Loader

Provides thread-safe singleton pattern configuration management with TOML file loading and Pydantic model validation.
"""

from __future__ import annotations

import os
import stat
import threading
import tomllib
import warnings
from pathlib import Path
from typing import Any, ClassVar, Dict, Generic, Optional, Type, TypeVar, Union

from pydantic import BaseModel

__all__ = ["ConfigLoader", "InsecureConfigWarning"]

T = TypeVar("T", bound=BaseModel)


class InsecureConfigWarning(UserWarning):
    """Warning raised when configuration file has insecure permissions."""

    pass


class ConfigLoader(Generic[T]):
    """
    Thread-safe Configuration Loader

    Loads configuration from TOML files and serializes them to specified Pydantic model types.
    Supports singleton pattern to ensure only one configuration instance per type in the application.

    Simplest usage::

        app_config = ConfigLoader.from_file(AppConfig, "config.toml")

    Thread Safety:
        All public methods are thread-safe and can be used in multi-threaded environments.
    """

    # Class variables
    _instances: ClassVar[Dict[Type[BaseModel], ConfigLoader[Any]]] = {}
    _file_cache: ClassVar[Dict[str, Dict[str, Any]]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    # Instance variables (declaration only, no default values)
    config_type: Type[T]
    config: Optional[T]
    loaded_file_path: Optional[str]

    def __new__(cls, config_type: Type[T]) -> ConfigLoader[T]:
        """
        Implements thread-safe singleton pattern, one instance per config type

        Args:
            config_type: Configuration type, must be a class inheriting from BaseModel

        Returns:
            ConfigLoader instance for the corresponding config type
        """
        with cls._lock:
            if config_type not in cls._instances:
                instance = super().__new__(cls)
                instance.config_type = config_type
                instance.config = None
                instance.loaded_file_path = None
                cls._instances[config_type] = instance
            return cls._instances[config_type]  # type: ignore[return-value]

    def __init__(self, config_type: Type[T]) -> None:
        """
        Initialize configuration loader

        Note: Due to singleton pattern, __init__ may be called multiple times,
        but state is only initialized once in __new__.

        Args:
            config_type: Configuration type, must be a class inheriting from BaseModel
        """
        # State initialization is done in __new__, no action needed here

    @staticmethod
    def _normalize_path(file_path: Union[str, Path]) -> str:
        """
        Normalize file path to absolute path

        Args:
            file_path: Original file path

        Returns:
            Normalized absolute path string
        """
        return str(Path(file_path).resolve())

    @staticmethod
    def _check_file_permissions(file_path: str, warn_only: bool = True) -> None:
        """
        Check configuration file permissions for security

        On Unix-like systems, warns if the file is readable by group or others,
        as configuration files may contain sensitive data like API keys and passwords.

        Args:
            file_path: Path to the configuration file
            warn_only: If True, only emit a warning; if False, raise an exception

        Raises:
            PermissionError: If warn_only is False and file has insecure permissions
        """
        # Skip permission check on Windows
        if os.name != "posix":
            return

        try:
            file_stat = os.stat(file_path)
            mode = file_stat.st_mode

            # Check if file is readable by group or others
            is_group_readable = bool(mode & stat.S_IRGRP)
            is_others_readable = bool(mode & stat.S_IROTH)

            if is_group_readable or is_others_readable:
                message = (
                    f"Configuration file '{file_path}' has insecure permissions "
                    f"(mode: {oct(mode)[-3:]}). "
                    f"Consider restricting access with: chmod 600 {file_path}"
                )
                if warn_only:
                    warnings.warn(message, InsecureConfigWarning, stacklevel=4)
                else:
                    raise PermissionError(message)
        except OSError:
            # If we can't stat the file, let the load operation handle the error
            pass

    @classmethod
    def from_file(cls, config_type: Type[T], file_path: Union[str, Path]) -> T:
        """
        Load configuration from file (recommended usage)

        This is the simplest and most straightforward way to use::

            app_config = ConfigLoader.from_file(AppConfig, "config.toml")

        Automatically handles:

        - Singleton pattern: Only one instance per config type
        - File caching: Same file is read only once
        - Smart loading: If same file already loaded, returns cached config
        - Thread safety: All operations are thread-safe

        Args:
            config_type: Configuration type, must be a class inheriting from BaseModel
            file_path: TOML file path

        Returns:
            Configuration object

        Raises:
            FileNotFoundError: File does not exist
            ValueError: TOML parse error or file is empty
            pydantic.ValidationError: Configuration validation error
        """
        loader = cls(config_type)
        normalized_path = cls._normalize_path(file_path)

        with cls._lock:
            # If same file already loaded, return directly
            if loader.config is not None and loader.loaded_file_path == normalized_path:
                return loader.config

        # Otherwise load configuration
        return loader.load(file_path)

    def load(self, file_path: Union[str, Path], check_permissions: bool = True) -> T:
        """
        Load configuration from TOML file

        Args:
            file_path: TOML file path
            check_permissions: Whether to check file permissions (default: True)

        Returns:
            Configuration object

        Raises:
            FileNotFoundError: File does not exist
            ValueError: TOML parse error or file is empty
            pydantic.ValidationError: Configuration validation error

        Warnings:
            InsecureConfigWarning: If file has insecure permissions (readable by group/others)
        """
        normalized_path = self._normalize_path(file_path)
        path = Path(normalized_path)

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {normalized_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {normalized_path}")

        # Check file permissions for security
        if check_permissions:
            self._check_file_permissions(normalized_path)

        with self._lock:
            # Check file cache
            if normalized_path not in self._file_cache:
                try:
                    with open(normalized_path, "rb") as f:
                        toml_dict = tomllib.load(f)
                except tomllib.TOMLDecodeError as e:
                    raise ValueError(f"TOML parse error ({normalized_path}): {e}") from e

                if not toml_dict:
                    raise ValueError(f"Config file is empty: {normalized_path}")

                self._file_cache[normalized_path] = toml_dict
            else:
                toml_dict = self._file_cache[normalized_path]

            # Parse TOML data using Pydantic model
            self.config = self.config_type.model_validate(toml_dict)
            self.loaded_file_path = normalized_path
            return self.config

    def get(self) -> T:
        """
        Get configuration object

        Returns:
            Configuration object

        Raises:
            RuntimeError: Configuration not loaded
        """
        with self._lock:
            if self.config is None:
                raise RuntimeError(
                    f"{self.config_type.__name__} configuration not loaded, please call load method first"
                )
            return self.config

    def reload(self) -> T:
        """
        Reload configuration file

        If the configuration file has been modified, call this method to reload.
        This operation clears the file cache and re-reads the file.

        Returns:
            Reloaded configuration object

        Raises:
            RuntimeError: If no file has been loaded
        """
        with self._lock:
            if self.loaded_file_path is None:
                raise RuntimeError("No loaded config file, cannot reload")

            # Clear file cache, force re-read
            self._file_cache.pop(self.loaded_file_path, None)
            current_path = self.loaded_file_path

        return self.load(current_path)

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear all file caches and loaded configuration instance states

        Use when testing or when forced reload of all configurations is needed.
        This operation is thread-safe.
        """
        with cls._lock:
            cls._file_cache.clear()
            # Clear all loaded configs in singleton instances so they can be reloaded
            for instance in cls._instances.values():
                instance.config = None
                instance.loaded_file_path = None

    @classmethod
    def reset(cls) -> None:
        """
        Completely reset ConfigLoader state

        Clears all caches and singleton instances. Mainly used for testing scenarios.
        """
        with cls._lock:
            cls._file_cache.clear()
            cls._instances.clear()
