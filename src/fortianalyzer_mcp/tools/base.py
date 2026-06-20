"""Base class for FortiAnalyzer MCP tools.

Provides error handling, formatting, and common patterns
shared across all tool categories.
"""
import json
import logging
from typing import Any

logger = logging.getLogger("fortianalyzer_mcp.tools")


class BaseTool:
    """Base class with shared error handling and formatting.

    Tool implementations extend this class and call ``self.faz``
    to access the connected FortiAnalyzer client.
    """

    def __init__(self, faz_manager):
        self.faz_manager = faz_manager

    async def _get_client(self, device_id: str):
        """Get a connected FortiAnalyzer client, auto-reconnecting if needed.

        Args:
            device_id: Device name as configured in config.json
                (e.g., ``"FAZ-01"``).

        Returns:
            FortiAnalyzerClient instance.

        Raises:
            ValueError: If device not found or not connected.
        """
        client = self.faz_manager.get_client(device_id)
        if client is None:
            available = list(self.faz_manager.clients.keys())
            raise ValueError(
                f"Device '{device_id}' not found or not connected. "
                f"Available: {available}"
            )
        # Auto-reconnect if session dropped (rstierli/fortianalyzer-mcp pattern)
        await client.ensure_connected()
        return client

    @staticmethod
    def _format_success(data: Any, message: str = "OK") -> str:
        """Format a successful response."""
        result = {"status": "success", "message": message}
        if data is not None:
            result["data"] = data
        return json.dumps(result, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def _format_error(message: str) -> str:
        """Format an error response."""
        return json.dumps(
            {"status": "error", "message": message},
            indent=2, ensure_ascii=False,
        )

    @staticmethod
    def _format_list(items: list[Any], label: str = "items") -> str:
        """Format a list of items."""
        return json.dumps({
            "status": "success",
            "count": len(items),
            label: items,
        }, indent=2, ensure_ascii=False, default=str)
