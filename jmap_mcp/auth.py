"""Simple authentication wrapper for JMAP using jmapc library."""

import logging
from typing import Optional

from jmapc import Client

from jmap_mcp.config import config

logger = logging.getLogger(__name__)


class FastmailAuth:
    """Simple wrapper around jmapc Client for authentication."""

    def __init__(self):
        self.auth_token: str = config.fastmail.auth_token
        self.jmap_host: str = self._extract_host_from_url(config.fastmail.jmap_base_url)
        self._client: Optional[Client] = None

    def _extract_host_from_url(self, url: str) -> str:
        """Extract host from JMAP base URL."""
        # Remove protocol and path, keep just the host
        if "://" in url:
            url = url.split("://")[1]
        if "/" in url:
            url = url.split("/")[0]
        return url

    async def __aenter__(self):
        """Create jmapc client."""
        self._client = Client.create_with_api_token(
            host=self.jmap_host, api_token=self.auth_token
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup jmapc client."""
        if self._client:
            # jmapc handles cleanup automatically
            pass

    def get_client(self) -> Client:
        """Get the jmapc client instance."""
        if not self._client:
            raise Exception(
                "Auth client not initialized - use as async context manager"
            )
        return self._client

    async def get_valid_token(self) -> str:
        """Get the auth token (for compatibility with existing code)."""
        if not self.auth_token:
            raise Exception("No auth token configured")
        return self.auth_token
