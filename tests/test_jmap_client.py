import os
import pytest
from unittest.mock import patch, MagicMock

from jmapc.methods import (
    MailboxGetResponse,
    EmailQueryResponse,
    EmailGetResponse,
    MailboxQueryResponse,
)

from jmap_mcp.jmap_client import JMAPClient, JMAPError
from jmap_mcp.config import FastmailConfig


class TestJMAPClient:
    """Test JMAPClient functionality."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch("jmap_mcp.jmap_client.config") as mock_config:
            mock_config.fastmail = FastmailConfig(
                auth_token="test_token_123",
                jmap_base_url="https://api.fastmail.com/jmap/api/",
            )
            yield mock_config

    @pytest.fixture
    def mock_auth(self):
        """Mock FastmailAuth for testing."""
        with patch("jmap_mcp.jmap_client.FastmailAuth") as mock_auth_class:
            mock_auth = MagicMock()
            mock_client = MagicMock()
            mock_auth.get_client.return_value = mock_client
            mock_auth_class.return_value = mock_auth
            yield mock_auth, mock_client

    @pytest.fixture
    def jmap_client(self, mock_config, mock_auth):
        """JMAPClient instance for testing."""
        return JMAPClient()

    def test_init(self, jmap_client):
        """Test JMAPClient initialization."""
        assert jmap_client._auth is not None
        assert jmap_client._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_config, mock_auth):
        """Test JMAPClient as async context manager."""
        mock_auth_instance, mock_client = mock_auth

        async with JMAPClient() as client:
            assert client._client == mock_client

        mock_auth_instance.__aenter__.assert_called_once()
        mock_auth_instance.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_mailboxes_success(self, jmap_client, mock_auth):
        """Test successful mailbox retrieval."""
        mock_auth_instance, mock_client = mock_auth
        jmap_client._client = mock_client

        # Create mock mailbox data
        mock_mailbox = MagicMock()
        mock_mailbox.id = "mb1"
        mock_mailbox.name = "Inbox"
        mock_mailbox.role = "inbox"
        mock_mailbox.total_emails = 42
        mock_mailbox.unread_emails = 5

        # Create mock query response (first method)
        mock_query_response = MagicMock(spec=MailboxQueryResponse)
        mock_query_response.ids = ["mb1"]
        mock_query_invocation = MagicMock()
        mock_query_invocation.response = mock_query_response

        # Create mock get response (second method)
        mock_get_response = MagicMock(spec=MailboxGetResponse)
        mock_get_response.data = [mock_mailbox]
        mock_get_invocation = MagicMock()
        mock_get_invocation.response = mock_get_response

        # Return both responses
        mock_client.request.return_value = [mock_query_invocation, mock_get_invocation]

        result = await jmap_client.get_mailboxes()

        assert len(result) == 1
        assert result[0]["id"] == "mb1"
        assert result[0]["name"] == "Inbox"
        assert result[0]["role"] == "inbox"
        assert result[0]["totalEmails"] == 42
        assert result[0]["unreadEmails"] == 5

    @pytest.mark.asyncio
    async def test_get_mailboxes_not_initialized(self, jmap_client):
        """Test mailbox retrieval when client not initialized."""
        with pytest.raises(JMAPError) as exc_info:
            await jmap_client.get_mailboxes()
        assert "Client not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_emails_success(self, jmap_client, mock_auth):
        """Test successful email search."""
        mock_auth_instance, mock_client = mock_auth
        jmap_client._client = mock_client

        # Create mock response
        mock_response = MagicMock(spec=EmailQueryResponse)
        mock_response.ids = ["email1", "email2"]
        mock_response.total = 2
        mock_response.limit = 50
        mock_response.position = 0

        # Create mock invocation response
        mock_invocation = MagicMock()
        mock_invocation.response = mock_response

        mock_client.request.return_value = [mock_invocation]

        result = await jmap_client.search_emails(
            filter_conditions={"text": "test"}, limit=10
        )

        assert result["ids"] == ["email1", "email2"]
        assert result["total"] == 2
        assert result["limit"] == 50
        assert result["position"] == 0

    @pytest.mark.asyncio
    async def test_get_emails_success(self, jmap_client, mock_auth):
        """Test successful email retrieval."""
        mock_auth_instance, mock_client = mock_auth
        jmap_client._client = mock_client

        # Create mock email data
        mock_email = MagicMock()
        mock_email.id = "email1"
        mock_email.subject = "Test Subject"
        mock_email.mail_from = [MagicMock(email="sender@example.com", name="Sender")]
        mock_email.to = [MagicMock(email="recipient@example.com", name="Recipient")]
        mock_email.cc = None
        mock_email.bcc = None
        mock_email.received_at = None
        mock_email.size = 1024
        mock_email.preview = "Email preview"

        # Create mock response
        mock_response = MagicMock(spec=EmailGetResponse)
        mock_response.data = [mock_email]

        # Create mock invocation response without an error attribute
        mock_invocation = MagicMock()
        mock_invocation.response = mock_response
        mock_invocation.error = None  # Explicitly set error to None

        mock_client.request.return_value = [mock_invocation]

        result = await jmap_client.get_emails(["email1"])

        assert len(result) == 1
        assert result[0]["id"] == "email1"
        assert result[0]["subject"] == "Test Subject"
        assert result[0]["from"][0]["email"] == "sender@example.com"
        assert result[0]["to"][0]["email"] == "recipient@example.com"

    @pytest.mark.asyncio
    async def test_create_draft_not_implemented(self, jmap_client, mock_auth):
        """Test that create_draft is properly implemented."""
        mock_auth_instance, mock_client = mock_auth
        jmap_client._client = mock_client

        # Mock the mailbox query for Drafts
        mock_mailbox = MagicMock()
        mock_mailbox.id = "drafts_id"

        mock_mailbox_response = MagicMock(spec=MailboxGetResponse)
        mock_mailbox_response.data = [mock_mailbox]

        mock_mailbox_invocation = MagicMock()
        mock_mailbox_invocation.response = mock_mailbox_response

        # Mock identity get
        mock_identity = MagicMock()
        mock_identity.email = "user@example.com"
        mock_identity.name = "User"

        from jmapc.methods import IdentityGetResponse

        mock_identity_response = MagicMock(spec=IdentityGetResponse)
        mock_identity_response.data = [mock_identity]

        mock_identity_invocation = MagicMock()
        mock_identity_invocation.response = mock_identity_response

        # Mock email creation
        mock_created_email = MagicMock()
        mock_created_email.id = "draft_email_id"

        mock_email_set_response = MagicMock()
        mock_email_set_response.created = {"draft": mock_created_email}

        mock_email_set_invocation = MagicMock()
        mock_email_set_invocation.response = mock_email_set_response

        # Set up the client to return different responses for different calls
        mock_client.request.side_effect = [
            [mock_mailbox_invocation, mock_mailbox_invocation],  # Drafts mailbox query
            [mock_identity_invocation],  # Identity get
            [mock_email_set_invocation],  # Email creation
        ]

        result = await jmap_client.create_draft(
            subject="Test Subject",
            to_addresses=[{"email": "recipient@example.com", "name": "Recipient"}],
            text_body="Test body",
        )

        assert result == "draft_email_id"


class TestJMAPClientIntegration:
    """Integration tests for JMAP client with real token.

    Set FASTMAIL_AUTH_TOKEN_TEST environment variable to test with your real token.
    """

    @pytest.fixture
    def real_token(self):
        """Get real token from environment if available."""
        return os.getenv("FASTMAIL_AUTH_TOKEN_TEST")

    @pytest.fixture
    def real_jmap_client(self, real_token):
        """Create JMAP client with real token if available."""
        if not real_token:
            pytest.skip("FASTMAIL_AUTH_TOKEN_TEST not set - skipping real JMAP tests")

        with patch("jmap_mcp.jmap_client.config") as mock_config:
            mock_config.fastmail = FastmailConfig(
                auth_token=real_token,
                jmap_base_url="https://api.fastmail.com/jmap/api/",
            )
            return JMAPClient()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_get_mailboxes(self, real_jmap_client):
        """Test getting mailboxes with real Fastmail token."""
        async with real_jmap_client as client:
            mailboxes = await client.get_mailboxes()

            assert isinstance(mailboxes, list)
            assert len(mailboxes) > 0

            # Check that we have expected fields
            inbox = next((mb for mb in mailboxes if mb["name"] == "Inbox"), None)
            assert inbox is not None
            assert "id" in inbox
            assert "totalEmails" in inbox
            assert "unreadEmails" in inbox

            print(f"Found {len(mailboxes)} mailboxes")
            print(
                f"Inbox has {inbox['totalEmails']} emails, {inbox['unreadEmails']} unread"
            )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_search_emails(self, real_jmap_client):
        """Test searching emails with real Fastmail token."""
        async with real_jmap_client as client:
            # Search for recent emails in inbox
            result = await client.search_emails(limit=5)

            assert "ids" in result
            assert "total" in result
            assert "limit" in result
            assert "position" in result

            print(
                f"Found {result['total']} total emails, returning {len(result['ids'])} IDs"
            )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_get_emails(self, real_jmap_client):
        """Test getting email details with real Fastmail token."""
        async with real_jmap_client as client:
            # First search for some emails
            search_result = await client.search_emails(limit=2)

            if search_result["ids"]:
                # Get details for the first email
                emails = await client.get_emails(search_result["ids"][:1])

                assert len(emails) <= 1
                if emails:
                    email = emails[0]
                    assert "id" in email
                    assert "subject" in email
                    assert "from" in email

                    print(f"Retrieved email: {email['subject']}")
            else:
                print("No emails found to test with")
