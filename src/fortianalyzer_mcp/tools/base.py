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

    # FAZ error codes → user-friendly messages
    _FAZ_ERROR_TRANSLATIONS = {
        -9:  "命令对该 URL 无效（ADOM 功能未启用，或请求数据格式不正确）",
        -3:  "对象不存在",
        -11: "权限不足（当前认证方式无权访问此 API，尝试使用其他账号或开启对应权限）",
        -1:  "操作被拒绝",
        -4:  "名称已存在（重复创建）",
        -5:  "名称无效",
        -6:  "参数无效",
        -8:  "资源冲突",
    }

    @classmethod
    def _translate_faz_error(cls, message: str) -> str:
        """Translate raw FAZ API error codes to user-friendly Chinese messages.

        Parses ``FAZ <host>: API error <code>: <text>`` format and appends
        the human-readable translation when the code is known.
        """
        import re
        match = re.search(r'API error (-?\d+): (.+)$', message)
        if not match:
            return message
        code = int(match.group(1))
        translation = cls._FAZ_ERROR_TRANSLATIONS.get(code)
        if translation:
            return f"{message}\n  → {translation}"
        return message

    @staticmethod
    def _format_error(message: str) -> str:
        """Format an error response (raw message; use _format_faz_error for translations)."""
        return json.dumps(
            {"status": "error", "message": message},
            indent=2, ensure_ascii=False,
        )

    @classmethod
    def _format_faz_error(cls, message: str) -> str:
        """Format an error with FAZ code translation."""
        return cls._format_error(cls._translate_faz_error(message))

    @staticmethod
    def _format_list(items: list[Any], label: str = "items") -> str:
        """Format a list of items."""
        return json.dumps({
            "status": "success",
            "count": len(items),
            label: items,
        }, indent=2, ensure_ascii=False, default=str)
