import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class FastmailConfig(BaseModel):
    """Fastmail API configuration."""

    auth_token: str = Field(..., description="Fastmail API auth token")

    # Fastmail JMAP API endpoints
    jmap_base_url: str = Field(
        default="https://api.fastmail.com/jmap/api/", description="JMAP API base URL"
    )


class MCPConfig(BaseModel):
    """MCP server configuration."""

    host: str = Field(default="localhost", description="MCP server host")
    port: int = Field(default=3000, description="MCP server port")


class Config:
    """Main configuration class combining all sub-configurations."""

    def __init__(
        self,
        fastmail: FastmailConfig,
        mcp: MCPConfig,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
    ):
        self.fastmail = fastmail
        self.mcp = mcp
        self.log_level = log_level
        self.log_file = log_file


def load_config() -> Config:
    """Load configuration from environment variables."""

    # Support both our env var names and jmapc's expected names
    auth_token = os.getenv("FASTMAIL_AUTH_TOKEN") or os.getenv("JMAP_API_TOKEN") or ""

    jmap_base_url = os.getenv("FASTMAIL_JMAP_BASE_URL") or os.getenv(
        "JMAP_HOST", "api.fastmail.com"
    )

    # If we got just a host from JMAP_HOST, make it a full URL
    if not jmap_base_url.startswith("http"):
        jmap_base_url = f"https://{jmap_base_url}/jmap/api/"
    elif not jmap_base_url.endswith("/"):
        jmap_base_url += "/"

    fastmail_config = FastmailConfig(
        auth_token=auth_token,
        jmap_base_url=jmap_base_url,
    )

    mcp_config = MCPConfig(
        host=os.getenv("MCP_HOST", "localhost"),
        port=int(os.getenv("MCP_PORT", "3000")),
    )

    return Config(
        fastmail=fastmail_config,
        mcp=mcp_config,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE"),
    )


# Global configuration instance
config = load_config()
