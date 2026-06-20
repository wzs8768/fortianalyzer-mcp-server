"""Device management tools for FortiAnalyzer MCP Server.

Tools for managing FortiAnalyzer device connections —
list, add, remove, health check, connection test.
"""
import asyncio
import logging
import time

from ..core.faz_client import FortiAnalyzerError
from .base import BaseTool

logger = logging.getLogger("fortianalyzer_mcp.tools.device")


class DeviceTools(BaseTool):
    """Device management operations."""

    async def list_devices(self) -> str:
        """List all configured FortiAnalyzer devices and their connection status.

        Returns:
            JSON: List of devices with name, host, port, adom, and connected status.
        """
        devices = []
        for name, client in self.faz_manager.clients.items():
            devices.append({
                "name": name,
                "host": client.host,
                "port": client.port,
                "adom": client.adom,
                "connected": client.is_connected,
            })
        return self._format_list(devices, "devices")

    async def get_device_status(self, device_id: str) -> str:
        """Get detailed status of a FortiAnalyzer device.

        Args:
            device_id: Device name as configured in config.json
                (e.g., ``"FAZ-01"``).

        Returns:
            JSON: Device status including session, adom, uptime, version.
        """
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/sys/status")
            status_data = result.get("result", [{}])[0] if result.get("result") else {}
            return self._format_success({
                "device": device_id,
                "host": faz.host,
                "connected": faz.is_connected,
                "adom": faz.adom,
                "status": status_data,
            })
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_error(str(e))

    async def test_device_connection(self, device_id: str) -> str:
        """Test connection to a FortiAnalyzer device by performing a simple API call.

        Args:
            device_id: Device name as configured in config.json
                (e.g., ``"FAZ-01"``).

        Returns:
            JSON: Connection test result with latency.
        """
        try:
            faz = await self._get_client(device_id)
            start = time.monotonic()
            await faz.execute("/sys/status")
            latency = (time.monotonic() - start) * 1000
            return self._format_success({
                "device": device_id,
                "host": faz.host,
                "connected": True,
                "latency_ms": round(latency, 1),
            })
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_error(f"Connection failed: {e}")
        except Exception as e:
            return self._format_error(f"Unexpected error: {e}")

    async def health_check(self) -> str:
        """Check health of all configured FortiAnalyzer devices concurrently.

        Returns:
            JSON: Health status of all devices with per-device latency.
        """
        devices = list(self.faz_manager.clients.keys())
        if not devices:
            return self._format_error("No devices configured")

        async def check_one(name: str) -> dict:
            try:
                faz = await self._get_client(name)
                start = time.monotonic()
                await faz.execute("/sys/status")
                latency = (time.monotonic() - start) * 1000
                return {"name": name, "healthy": True, "latency_ms": round(latency, 1)}
            except Exception as e:
                return {"name": name, "healthy": False, "error": str(e)}

        results = await asyncio.gather(
            *[check_one(d) for d in devices],
            return_exceptions=True,
        )

        healthy = all(r.get("healthy", False) for r in results if isinstance(r, dict))
        return self._format_success({
            "healthy": healthy,
            "devices": [r if isinstance(r, dict) else {"error": str(r)} for r in results],
        })

    async def get_server_info(self) -> str:
        """Get MCP server information — version, tool count, config summary.

        Returns:
            JSON: Server metadata.
        """
        from .. import __version__
        tool_count = len(self.faz_manager.mcp._tool_manager._tools) if self.faz_manager.mcp else 0
        return self._format_success({
            "server": "fortianalyzer-mcp-server",
            "version": __version__,
            "devices": len(self.faz_manager.clients),
            "tools": tool_count,
        })
