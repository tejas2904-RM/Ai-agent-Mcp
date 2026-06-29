"""Application configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server connection."""

    name: str
    transport: Literal["stdio", "http"] = "stdio"
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    required_tools: list[str] = Field(default_factory=list)
    tool_aliases: dict[str, list[str]] = Field(default_factory=dict)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mcp_profile: Literal["local", "remote"] = "local"
    mcp_config_path: Path | None = None
    mcp_docs_server_url: str = "https://saksham-mcp-server-i1js.onrender.com"
    sample_data_dir: Path = DATA_DIR / "sample"
    normalized_data_dir: Path = DATA_DIR / "normalized"
    scrubbed_data_dir: Path = DATA_DIR / "scrubbed"
    analysis_data_dir: Path = DATA_DIR / "analysis"
    recency_weeks: int = 10
    log_level: str = "INFO"

    # Groq LLM (Phase 3+)
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    # Google Docs target (remote Saksham MCP append_to_doc)
    google_doc_id: str | None = None

    # Gmail draft recipient (remote Saksham MCP create_email_draft)
    gmail_recipient: str | None = None

    # Phase 9 API (Render backend)
    api_data_dir: Path = DATA_DIR / "api"
    cors_origins: str = "http://localhost:3000,https://groww-pulse.vercel.app"
    api_key: str | None = None
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Google OAuth (optional — remote MCP server holds credentials)
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None

    def resolve_mcp_config_path(self) -> Path:
        if self.mcp_config_path:
            return self.mcp_config_path
        filename = (
            "mcp_servers.local.json"
            if self.mcp_profile == "local"
            else "mcp_servers.remote.json"
        )
        return CONFIG_DIR / filename

    def resolved_api_data_dir(self) -> Path:
        return self.api_data_dir


def load_mcp_servers(config_path: Path | None = None) -> list[MCPServerConfig]:
    settings = Settings()
    path = config_path or settings.resolve_mcp_config_path()
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    servers: list[MCPServerConfig] = []
    for name, entry in raw.get("mcpServers", {}).items():
        servers.append(MCPServerConfig(name=name, **entry))
    return servers
