import os
import pytest
from unittest.mock import patch, MagicMock

from jmapc import Client

from jmap_mcp.auth import FastmailAuth
from jmap_mcp.config import FastmailConfig


class TestFastmailAuth:
    """Test FastmailAuth authentication."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch("jmap_mcp.auth.config") as mock_config:
            mock_config.fastmail = FastmailConfig(
                auth_token="test_token_123",
                jmap_base_url="https://api.fastmail.com/jmap/api/",
            )
            yield mock_config

    @pytest.fixture
    def auth_client(self, mock_config):
        """FastmailAuth instance for testing."""
        return FastmailAuth()

    def test_init(self, auth_client, mock_config):
        """Test FastmailAuth initialization."""
        assert auth_client.auth_token == "test_token_123"
        assert auth_client.jmap_host == "api.fastmail.com"
        assert auth_client._client is None

    def test_extract_host_from_url(self, auth_client):
        """Test URL host extraction."""
        assert (
            auth_client._extract_host_from_url("https://api.fastmail.com/jmap/api/")
            == "api.fastmail.com"
        )
        assert (
            auth_client._extract_host_from_url("api.fastmail.com") == "api.fastmail.com"
        )
        assert (
            auth_client._extract_host_from_url("https://custom.host.com/path")
            == "custom.host.com"
        )

    @patch("jmap_mcp.auth.Client.create_with_api_token")
    async def test_context_manager(self, mock_create_client, mock_config):
        """Test FastmailAuth as async context manager."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        async with FastmailAuth() as auth:
            assert auth.auth_token == "test_token_123"
            assert auth._client == mock_client

        mock_create_client.assert_called_once_with(
            host="api.fastmail.com", api_token="test_token_123"
        )

    @patch("jmap_mcp.auth.Client.create_with_api_token")
    def test_get_client_success(self, mock_create_client, auth_client):
        """Test getting client when initialized."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        auth_client._client = mock_client

        result = auth_client.get_client()
        assert result == mock_client

    def test_get_client_not_initialized(self, auth_client):
        """Test getting client when not initialized."""
        with pytest.raises(Exception) as exc_info:
            auth_client.get_client()
        assert "Auth client not initialized" in str(exc_info.value)

    async def test_get_valid_token_success(self, auth_client):
        """Test getting valid token when token is configured."""
        token = await auth_client.get_valid_token()
        assert token == "test_token_123"

    async def test_get_valid_token_no_token(self, mock_config):
        """Test getting valid token with no token configured."""
        mock_config.fastmail.auth_token = ""
        auth_client = FastmailAuth()

        with pytest.raises(Exception) as exc_info:
            await auth_client.get_valid_token()
        assert "No auth token configured" in str(exc_info.value)


class TestRealTokenIntegration:
    """Integration tests for real token validation.

    Set FASTMAIL_AUTH_TOKEN_TEST environment variable to test with your real token.
    This is optional and will be skipped if not provided.
    """

    @pytest.fixture
    def real_token(self):
        """Get real token from environment if available."""
        return os.getenv("FASTMAIL_AUTH_TOKEN_TEST")

    @pytest.fixture
    def real_auth_client(self, real_token):
        """Create auth client with real token if available."""
        if not real_token:
            pytest.skip("FASTMAIL_AUTH_TOKEN_TEST not set - skipping real token tests")

        with patch("jmap_mcp.auth.config") as mock_config:
            mock_config.fastmail = FastmailConfig(
                auth_token=real_token,
                jmap_base_url="https://api.fastmail.com/jmap/api/",
            )
            return FastmailAuth()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_token_client_creation(self, real_auth_client):
        """Test client creation with real Fastmail token."""
        async with real_auth_client:
            client = real_auth_client.get_client()
            assert isinstance(client, Client)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_get_valid_token(self, real_auth_client):
        """Test getting valid token with real Fastmail token."""
        async with real_auth_client:
            token = await real_auth_client.get_valid_token()
            assert token is not None
            assert len(token) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_jmapc_basic_request(self, real_auth_client):
        """Test making a basic jmapc request with real token."""
        from jmapc.methods import MailboxQuery, MailboxGet
        from jmapc import Ref

        async with real_auth_client:
            client = real_auth_client.get_client()

            # Make a real request using jmapc following the examples pattern
            try:
                results = client.request(
                    [
                        MailboxQuery(),  # Query all mailboxes
                        MailboxGet(
                            ids=Ref("/ids")
                        ),  # Get details using result reference
                    ]
                )
                assert len(results) == 2
                assert results[1].response is not None
                print(
                    f"Successfully retrieved {len(results[1].response.data)} mailboxes"
                )
            except Exception as e:
                pytest.fail(f"Real jmapc request failed: {e}")
