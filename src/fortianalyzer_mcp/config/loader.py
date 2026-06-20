"""Configuration loader for FortiAnalyzer MCP Server.

Loads ``config/config.json``, validates with Pydantic models,
merges environment variables.
"""
import json
import logging
from pathlib import Path

from .models import AppConfig

logger = logging.getLogger("fortianalyzer_mcp.config")


def load_config(config_path: str | None = None) -> AppConfig:
    """Load and validate configuration from a JSON file.

    Priority:
        1. Explicit ``config_path`` argument
        2. ``FORTIANALYZER_MCP_CONFIG`` environment variable
        3. ``config/config.json`` in the project directory
    """
    if config_path is None:
        import os
        config_path = os.environ.get(
            "FORTIANALYZER_MCP_CONFIG",
            str(Path(__file__).resolve().parents[3] / "config" / "config.json"),
        )

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_file}\n"
            f"Copy config/config.example.json to {config_file} and edit it."
        )

    raw = json.loads(config_file.read_text())
    config = AppConfig(**raw)
    logger.info("Config loaded from %s: %d device(s)", config_file, len(config.devices))
    return config


def create_example_config(output_path: str | None = None) -> dict:
    """Generate a default example configuration dict.

    Args:
        output_path: If provided, write the example config to this file.
            Defaults to ``config/config.example.json``.
    """
    example = {
        "_comment": "FortiAnalyzer MCP Server — 设备连接与服务器运行配置（示例，请复制为 config.json 后修改）",
        "server": {
            "host": "0.0.0.0",
            "port": 8915,
            "name": "fortianalyzer-mcp-server",
            "version": "1.0.0",
        },
        "fortianalyzer": {
            "devices": {
                "FAZ-01": {
                    "host": "192.168.1.100",
                    "port": 443,
                    "username": "admin",
                    "password": "your-password-here",
                    "api_token": "your-api-token-here",
                    "adom": "root",
                    "verify_ssl": False,
                    "timeout": 60,
                }
            }
        },
        "auth": {
            "require_auth": True,
            "api_tokens": [
                {"name": "client-1", "token": "replace-with-strong-token"}
            ],
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": None,
            "console": True,
        },
    }

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(example, indent=2, ensure_ascii=False) + "\n")
        logger.info("Example config written to %s", out)

    return example
