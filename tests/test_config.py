import os
import pytest
from unittest.mock import patch

from jmap_mcp.config import Config, FastmailConfig, MCPConfig, load_config


class TestConfig:
    """Test configuration loading and validation."""

    def test_fastmail_config_validation(self):
        """Test Fastmail configuration validation."""
        config = FastmailConfig(auth_token="test_auth_token")

        assert config.auth_token == "test_auth_token"
        assert config.jmap_base_url == "https://api.fastmail.com/jmap/api/"

    def test_mcp_config_defaults(self):
        """Test MCP configuration defaults."""
        config = MCPConfig()

        assert config.host == "localhost"
        assert config.port == 3000

    @patch.dict(
        os.environ,
        {
            "FASTMAIL_AUTH_TOKEN": "env_auth_token",
            "MCP_HOST": "0.0.0.0",
            "MCP_PORT": "8080",
            "LOG_LEVEL": "DEBUG",
        },
        clear=True,
    )
    def test_load_config_from_env_our_format(self):
        """Test loading configuration from environment variables (our format)."""
        config = load_config()

        assert config.fastmail.auth_token == "env_auth_token"
        assert config.mcp.host == "0.0.0.0"
        assert config.mcp.port == 8080
        assert config.log_level == "DEBUG"

    @patch.dict(
        os.environ,
        {
            "JMAP_API_TOKEN": "jmapc_auth_token",
            "JMAP_HOST": "api.fastmail.com",
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": "9000",
            "LOG_LEVEL": "WARNING",
        },
        clear=True,
    )
    def test_load_config_from_env_jmapc_format(self):
        """Test loading configuration from environment variables (jmapc format)."""
        config = load_config()

        assert config.fastmail.auth_token == "jmapc_auth_token"
        assert config.fastmail.jmap_base_url == "https://api.fastmail.com/jmap/api/"
        assert config.mcp.host == "127.0.0.1"
        assert config.mcp.port == 9000
        assert config.log_level == "WARNING"

    @patch.dict(
        os.environ,
        {
            "FASTMAIL_AUTH_TOKEN": "our_token",
            "JMAP_API_TOKEN": "jmapc_token",
            "JMAP_HOST": "custom.host.com",
        },
        clear=True,
    )
    def test_load_config_precedence(self):
        """Test that our format takes precedence over jmapc format."""
        config = load_config()

        # Our token should take precedence
        assert config.fastmail.auth_token == "our_token"
        # But jmapc host should still be used
        assert config.fastmail.jmap_base_url == "https://custom.host.com/jmap/api/"

    @patch.dict(
        os.environ,
        {
            "FASTMAIL_JMAP_BASE_URL": "https://custom.example.com/jmap/",
            "JMAP_API_TOKEN": "test_token",
        },
        clear=True,
    )
    def test_load_config_custom_base_url(self):
        """Test loading with custom JMAP base URL."""
        config = load_config()

        assert config.fastmail.auth_token == "test_token"
        assert config.fastmail.jmap_base_url == "https://custom.example.com/jmap/"

    @patch.dict(
        os.environ,
        {"JMAP_HOST": "custom.host.example.com", "JMAP_API_TOKEN": "test_token"},
        clear=True,
    )
    def test_jmap_host_url_conversion(self):
        """Test that JMAP_HOST gets converted to full URL."""
        config = load_config()

        assert (
            config.fastmail.jmap_base_url == "https://custom.host.example.com/jmap/api/"
        )

    @patch.dict(
        os.environ,
        {
            "FASTMAIL_JMAP_BASE_URL": "https://example.com/jmap",  # No trailing slash
            "JMAP_API_TOKEN": "test_token",
        },
        clear=True,
    )
    def test_url_trailing_slash_added(self):
        """Test that trailing slash is added to URLs."""
        config = load_config()

        assert config.fastmail.jmap_base_url == "https://example.com/jmap/"

    def test_config_validation_error(self):
        """Test configuration validation with missing required fields."""
        with pytest.raises(ValueError):
            FastmailConfig()  # Missing auth_token

    def test_fastmail_config_with_custom_base_url(self):
        """Test Fastmail configuration with custom base URL."""
        config = FastmailConfig(
            auth_token="test_token", jmap_base_url="https://custom.example.com/jmap/"
        )

        assert config.auth_token == "test_token"
        assert config.jmap_base_url == "https://custom.example.com/jmap/"

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_empty_env(self):
        """Test loading config with empty environment."""
        config = load_config()

        # Should get empty auth token and default values
        assert config.fastmail.auth_token == ""
        assert config.fastmail.jmap_base_url == "https://api.fastmail.com/jmap/api/"
        assert config.mcp.host == "localhost"
        assert config.mcp.port == 3000
        assert config.log_level == "INFO"
