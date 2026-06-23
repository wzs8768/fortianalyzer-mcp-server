"""Pydantic configuration models for FortiAnalyzer MCP Server.

FortiAnalyzer API uses JSON-RPC style POST requests:
    POST https://<faz>/jsonrpc
    Body: {"method": "exec", "params": [{"url": "/dvmdb/adom", "data": {...}}]}
"""

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """MCP server configuration."""
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8915, description="Server port")
    name: str = Field(default="fortianalyzer-mcp-server", description="Server name")
    version: str = Field(default="1.0.0", description="Server version")


class DeviceConfig(BaseModel):
    """FortiAnalyzer device connection configuration.

    Supports api_token (recommended) or username/password.
    When both are present, api_token takes precedence.
    """
    host: str = Field(..., description="FortiAnalyzer IP or hostname")
    port: int = Field(default=443, description="HTTPS port")
    username: str | None = Field(default=None, description="Admin username")
    password: str | None = Field(default=None, description="Admin password")
    api_token: str | None = Field(
        default=None,
        description="API token (takes precedence over username/password)",
    )
    adom: str = Field(default="root", description="Default ADOM")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificate")
    timeout: int = Field(default=60, description="Request timeout in seconds")


class AuthConfig(BaseModel):
    """MCP server authentication configuration.

    ``api_tokens`` accepts two shapes (backward compatible):

        # Named tokens (recommended) — logs show which client connected
        [{"name": "hermes-local", "token": "..."}]

        # Bare strings — treated as unnamed tokens
        ["token1", "token2"]
    """
    require_auth: bool = Field(default=True, description="Whether authentication is required")
    api_tokens: list[str | dict[str, str]] = Field(
        default_factory=list,
        description="Valid API tokens (bare strings or {name, token} objects)",
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )
    file: str | None = Field(default=None, description="Log file path")
    console: bool = Field(default=True, description="Log to console")


class AppConfig(BaseModel):
    """Top-level application configuration.

    Maps to ``config/config.json``:

        {
          "server": {...},
          "fortianalyzer": {"devices": {"FAZ-01": {...}}},
          "auth": {...},
          "logging": {...}
        }
    """
    server: ServerConfig = Field(default_factory=ServerConfig)
    fortianalyzer: dict[str, dict[str, DeviceConfig]] = Field(
        default_factory=lambda: {"devices": {}},
        description="FortiAnalyzer devices keyed by name",
    )
    auth: AuthConfig = Field(default_factory=AuthConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @property
    def devices(self) -> dict[str, DeviceConfig]:
        """Convenience accessor for fortianalyzer.devices."""
        return self.fortianalyzer.get("devices", {})

    model_config = {"extra": "ignore"}
