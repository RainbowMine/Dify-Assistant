"""
ConfigLoader Unit Tests
"""

import os
import stat
import threading
import warnings
from pathlib import Path

import pytest
from pydantic import BaseModel

from dify_assistant.config.loader import ConfigLoader, InsecureConfigWarning


class SampleConfig(BaseModel):
    """Sample configuration model for testing"""

    name: str
    value: int


class ServerConfig(BaseModel):
    """Another configuration model for testing"""

    host: str
    port: int


@pytest.fixture(autouse=True)
def reset_loader():
    """Reset loader state before and after each test"""
    ConfigLoader.reset()
    yield
    ConfigLoader.reset()


class TestConfigLoaderBasic:
    """Basic functionality tests"""

    def test_basic_load(self, tmp_path: Path):
        """Test basic loading functionality"""
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "test"\nvalue = 42')

        config = ConfigLoader.from_file(SampleConfig, config_file)

        assert config.name == "test"
        assert config.value == 42

    def test_load_method(self, tmp_path: Path):
        """Test load method"""
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "direct"\nvalue = 100')

        loader = ConfigLoader(SampleConfig)
        config = loader.load(config_file)

        assert config.name == "direct"
        assert config.value == 100

    def test_get(self, tmp_path: Path):
        """Test get method"""
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "getter"\nvalue = 200')

        loader = ConfigLoader(SampleConfig)
        loader.load(config_file)

        config = loader.get()
        assert config.name == "getter"
        assert config.value == 200

    def test_get_not_loaded(self):
        """Test calling get when config not loaded"""
        loader = ConfigLoader(SampleConfig)

        with pytest.raises(RuntimeError, match="not loaded"):
            loader.get()


class TestSingletonPattern:
    """Singleton pattern tests"""

    def test_singleton_same_type(self):
        """Test same config type returns same instance"""
        loader1 = ConfigLoader(SampleConfig)
        loader2 = ConfigLoader(SampleConfig)

        assert loader1 is loader2

    def test_singleton_different_types(self):
        """Test different config types return different instances"""
        loader1 = ConfigLoader(SampleConfig)
        loader2 = ConfigLoader(ServerConfig)

        assert loader1 is not loader2

    def test_from_file_returns_same_config(self, tmp_path: Path):
        """Test from_file returns same config for same file"""
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "singleton"\nvalue = 1')

        config1 = ConfigLoader.from_file(SampleConfig, config_file)
        config2 = ConfigLoader.from_file(SampleConfig, config_file)

        assert config1 is config2


class TestPathNormalization:
    """Path normalization tests"""

    def test_relative_and_absolute_path(self, tmp_path: Path, monkeypatch):
        """Test relative and absolute paths pointing to same file"""
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "path"\nvalue = 10')

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        config1 = ConfigLoader.from_file(SampleConfig, config_file)
        # Reset to test different path forms
        ConfigLoader.reset()
        config2 = ConfigLoader.from_file(SampleConfig, "config.toml")

        assert config1.name == config2.name
        assert config1.value == config2.value

    def test_path_with_dots(self, tmp_path: Path, monkeypatch):
        """Test paths with . and .."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "dots"\nvalue = 20')

        monkeypatch.chdir(subdir)

        config = ConfigLoader.from_file(SampleConfig, "../config.toml")
        assert config.name == "dots"


class TestReload:
    """Reload tests"""

    def test_reload_updates_config(self, tmp_path: Path):
        """Test reload updates configuration"""
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "original"\nvalue = 1')

        loader = ConfigLoader(SampleConfig)
        config1 = loader.load(config_file)
        assert config1.name == "original"

        # Modify file content
        config_file.write_text('name = "updated"\nvalue = 2')

        config2 = loader.reload()
        assert config2.name == "updated"
        assert config2.value == 2

    def test_reload_without_loaded_file(self):
        """Test calling reload without loaded file"""
        loader = ConfigLoader(SampleConfig)

        with pytest.raises(RuntimeError, match="No loaded config file"):
            loader.reload()


class TestCache:
    """Cache functionality tests"""

    def test_clear_cache(self, tmp_path: Path):
        """Test clearing cache"""
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "cache"\nvalue = 100')

        loader = ConfigLoader(SampleConfig)
        loader.load(config_file)

        # Clear cache
        ConfigLoader.clear_cache()

        # Config should be cleared
        assert loader.config is None
        assert loader.loaded_file_path is None

    def test_reset_clears_instances(self, tmp_path: Path):
        """Test reset clears all instances"""
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "reset"\nvalue = 50')

        loader1 = ConfigLoader(SampleConfig)
        loader1.load(config_file)

        ConfigLoader.reset()

        # Create new instance, should be different object
        loader2 = ConfigLoader(SampleConfig)
        assert loader1 is not loader2


class TestErrorHandling:
    """Error handling tests"""

    def test_file_not_found(self, tmp_path: Path):
        """Test file not found error"""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            ConfigLoader.from_file(SampleConfig, tmp_path / "nonexistent.toml")

    def test_not_a_file(self, tmp_path: Path):
        """Test path is not a file error"""
        with pytest.raises(ValueError, match="Path is not a file"):
            ConfigLoader.from_file(SampleConfig, tmp_path)

    def test_empty_file(self, tmp_path: Path):
        """Test empty file error"""
        config_file = tmp_path / "empty.toml"
        config_file.write_text("")

        with pytest.raises(ValueError, match="Config file is empty"):
            ConfigLoader.from_file(SampleConfig, config_file)

    def test_invalid_toml(self, tmp_path: Path):
        """Test invalid TOML format error"""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text("this is not valid toml [[[")

        with pytest.raises(ValueError, match="TOML parse error"):
            ConfigLoader.from_file(SampleConfig, config_file)

    def test_validation_error(self, tmp_path: Path):
        """Test Pydantic validation error"""
        config_file = tmp_path / "config.toml"
        # Missing required field
        config_file.write_text('name = "test"')

        with pytest.raises(Exception):  # pydantic.ValidationError
            ConfigLoader.from_file(SampleConfig, config_file)


class TestThreadSafety:
    """Thread safety tests"""

    def test_concurrent_singleton_creation(self):
        """Test concurrent singleton creation"""
        results = []
        errors = []

        def create_loader():
            try:
                loader = ConfigLoader(SampleConfig)
                results.append(loader)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_loader) for _ in range(100)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 100
        # All results should be the same object
        assert all(r is results[0] for r in results)

    def test_concurrent_load(self, tmp_path: Path):
        """Test concurrent config loading"""
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "concurrent"\nvalue = 42')

        results = []
        errors = []

        def load_config():
            try:
                config = ConfigLoader.from_file(SampleConfig, config_file)
                results.append(config)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=load_config) for _ in range(100)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 100
        # All config values should be equal
        assert all(r.name == "concurrent" and r.value == 42 for r in results)

    def test_concurrent_different_types(self, tmp_path: Path):
        """Test concurrent loading of different config types"""
        config1 = tmp_path / "config1.toml"
        config1.write_text('name = "type1"\nvalue = 1')

        config2 = tmp_path / "config2.toml"
        config2.write_text('host = "localhost"\nport = 8080')

        results_sample = []
        results_server = []
        errors = []

        def load_sample_config():
            try:
                config = ConfigLoader.from_file(SampleConfig, config1)
                results_sample.append(config)
            except Exception as e:
                errors.append(e)

        def load_server_config():
            try:
                config = ConfigLoader.from_file(ServerConfig, config2)
                results_server.append(config)
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(50):
            threads.append(threading.Thread(target=load_sample_config))
            threads.append(threading.Thread(target=load_server_config))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results_sample) == 50
        assert len(results_server) == 50
        # Verify config values are correct
        assert all(r.name == "type1" and r.value == 1 for r in results_sample)
        assert all(r.host == "localhost" and r.port == 8080 for r in results_server)


class TestFilePermissions:
    """File permission security tests"""

    @pytest.mark.skipif(os.name != "posix", reason="File permissions only apply to POSIX systems")
    def test_secure_permissions_no_warning(self, tmp_path: Path):
        """Test secure file permissions (600) don't produce warning"""
        config_file = tmp_path / "secure_config.toml"
        config_file.write_text('name = "secure"\nvalue = 42')
        os.chmod(config_file, stat.S_IRUSR | stat.S_IWUSR)  # 600

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = ConfigLoader.from_file(SampleConfig, config_file)

            # No InsecureConfigWarning should be raised
            insecure_warnings = [x for x in w if issubclass(x.category, InsecureConfigWarning)]
            assert len(insecure_warnings) == 0
            assert config.name == "secure"

    @pytest.mark.skipif(os.name != "posix", reason="File permissions only apply to POSIX systems")
    def test_group_readable_produces_warning(self, tmp_path: Path):
        """Test group-readable file produces warning"""
        config_file = tmp_path / "group_readable.toml"
        config_file.write_text('name = "group"\nvalue = 1')
        os.chmod(config_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)  # 640

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ConfigLoader.from_file(SampleConfig, config_file)

            # Should have InsecureConfigWarning
            insecure_warnings = [x for x in w if issubclass(x.category, InsecureConfigWarning)]
            assert len(insecure_warnings) == 1
            assert "insecure permissions" in str(insecure_warnings[0].message)

    @pytest.mark.skipif(os.name != "posix", reason="File permissions only apply to POSIX systems")
    def test_world_readable_produces_warning(self, tmp_path: Path):
        """Test world-readable file produces warning"""
        config_file = tmp_path / "world_readable.toml"
        config_file.write_text('name = "world"\nvalue = 2')
        os.chmod(config_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IROTH)  # 604

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ConfigLoader.from_file(SampleConfig, config_file)

            insecure_warnings = [x for x in w if issubclass(x.category, InsecureConfigWarning)]
            assert len(insecure_warnings) == 1

    @pytest.mark.skipif(os.name != "posix", reason="File permissions only apply to POSIX systems")
    def test_skip_permission_check(self, tmp_path: Path):
        """Test skip permission check option"""
        config_file = tmp_path / "world_readable_skip.toml"
        config_file.write_text('name = "skip"\nvalue = 3')
        os.chmod(config_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IROTH)  # 604

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            loader = ConfigLoader(SampleConfig)
            config = loader.load(config_file, check_permissions=False)

            # No warning when check_permissions=False
            insecure_warnings = [x for x in w if issubclass(x.category, InsecureConfigWarning)]
            assert len(insecure_warnings) == 0
            assert config.name == "skip"
