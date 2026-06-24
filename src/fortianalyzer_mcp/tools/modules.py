"""FAZ tools — covers all tested working FortiAnalyzer API endpoints.

API docs reference: /home/wzhongshuai/FortiAnalyzerAPI/
Auth: admin session (password) for log/fortiview, Bearer token for dvmdb/sys.

Endpoint verification table (all tested 2026-06-21):
✅ dvmdb/adom, device, folder, group
✅ eventmgmt/alerts, alerts/count
✅ fazsys/forticare/licinfo, storage-info, monitor/*/status
✅ incidentmgmt/incidents, incidents/count
✅ ioc/license/state
✅ report/config/schedule
✅ sys/ha/status, logout
✅ logview/adom/root/logstats, logfiles/state, logfiles/data
⚠️  fortiview/adom/root/top-*/run — needs adom in URL path
⚠️  sys/status — admin session returns -11 (use hermes Bearer token)
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from ..core.faz_client import FortiAnalyzerError
from .base import BaseTool

logger = logging.getLogger("fortianalyzer_mcp.tools.modules")


class FazTools(BaseTool):
    """FortiAnalyzer tools — ADOMs, devices, events, logs, FortiView, system, reports."""

    # ═══════════════════════════════════════════════════════════════════
    # ADOM & Device Management
    # ═══════════════════════════════════════════════════════════════════

    async def list_adoms(self, device_id: str) -> str:
        """List all ADOMs on FortiAnalyzer.
        Args: device_id: Device name (e.g. ``"FAZ-01"``).
        Returns: JSON list of ADOMs with name, mode, devices count."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/dvmdb/adom")
            return self._format_list(result.get("result", []), "adoms")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def get_adom_detail(self, device_id: str, adom: str = "root") -> str:
        """Get detailed information about a specific ADOM.
        Args: device_id, adom (default ``"root"``).
        Returns: JSON ADOM details (devices, storage, policies)."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/dvmdb/adom", extra_params={"adom": adom})
            rows = result.get("result", [])
            if rows:
                return self._format_success(rows[0])
            return self._format_error(f"ADOM '{adom}' not found")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def create_adom(
        self, device_id: str, name: str, mode: str = "normal",
        description: str | None = None,
    ) -> str:
        """Create a new ADOM.
        Args: device_id, name, mode (``"normal"``/``"backup"``), description.
        Returns: JSON creation result."""
        try:
            faz = await self._get_client(device_id)
            data = [{"name": name, "mode": mode}]
            if description:
                data[0]["description"] = description
            result = await faz.execute("/dvmdb/adom", data=data, method="add")
            return self._format_success(result.get("result", []), f"ADOM '{name}' created")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def delete_adom(self, device_id: str, name: str) -> str:
        """Delete an ADOM. ⚠ Cannot be undone.
        Args: device_id, name — ADOM name to delete.
        Returns: JSON deletion result."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute(f"/dvmdb/adom/{name}", method="delete")
            return self._format_success(result.get("result", []), f"ADOM '{name}' deleted")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def list_adom_devices(self, device_id: str, adom: str = "root") -> str:
        """List all managed devices in an ADOM.
        Args: device_id, adom (default ``"root"``).
        Returns: JSON list with name, IP, serial, status, version."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/dvmdb/device", extra_params={"adom": adom})
            return self._format_list(result.get("result", []), "devices")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def list_folders(self, device_id: str, adom: str = "root") -> str:
        """List device folders in an ADOM.
        Args: device_id, adom (default ``"root"``).
        Returns: JSON folder list."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/dvmdb/folder", extra_params={"adom": adom})
            return self._format_list(result.get("result", []), "folders")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def list_device_groups(self, device_id: str, adom: str = "root") -> str:
        """List device groups in an ADOM.
        Args: device_id, adom (default ``"root"``).
        Returns: JSON group list."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/dvmdb/group", extra_params={"adom": adom})
            return self._format_list(result.get("result", []), "groups")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    # ═══════════════════════════════════════════════════════════════════
    # Event & Alert Management
    # ═══════════════════════════════════════════════════════════════════

    async def list_alerts(
        self, device_id: str, adom: str = "root",
        limit: int = 50, time_range: str | None = None,
    ) -> str:
        """List alerts/events from FortiAnalyzer.
        Args: device_id, adom, limit (default 50), time_range (e.g. ``"last-24h"``).
        Returns: JSON alert list with severity, source, message, timestamp."""
        try:
            faz = await self._get_client(device_id)
            data: dict[str, Any] = {"limit": limit}
            if time_range:
                data["time_range"] = time_range
            result = await faz.execute(
                "/eventmgmt/alerts", data=data, extra_params={"adom": adom},
            )
            alerts = result.get("result", [])
            return self._format_list(alerts[:limit], "alerts")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def get_alert_count(
        self, device_id: str, adom: str = "root",
    ) -> str:
        """Get total alert count.
        Args: device_id, adom.
        Returns: JSON count."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute(
                "/eventmgmt/alerts/count", extra_params={"adom": adom},
            )
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def list_incidents(
        self, device_id: str, adom: str = "root",
        limit: int = 50, status: str | None = None,
    ) -> str:
        """List incidents from FortiAnalyzer.
        Args: device_id, adom, limit, status (``"open"``/``"closed"``/``"all"``).
        Returns: JSON incident list with ID, title, severity, status."""
        try:
            faz = await self._get_client(device_id)
            data: dict[str, Any] = {"limit": limit}
            if status:
                data["status"] = status
            result = await faz.execute(
                "/incidentmgmt/incidents", data=data, extra_params={"adom": adom},
            )
            incidents = result.get("result", [])
            return self._format_list(incidents[:limit], "incidents")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def get_incident_count(
        self, device_id: str, adom: str = "root",
    ) -> str:
        """Get total incident count.
        Args: device_id, adom.
        Returns: JSON count."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute(
                "/incidentmgmt/incidents/count", extra_params={"adom": adom},
            )
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    # ═══════════════════════════════════════════════════════════════════
    # Log View (async search, stats, log files)
    # ═══════════════════════════════════════════════════════════════════

    async def get_log_stats(
        self, device_id: str, adom: str = "root", log_type: str = "traffic",
    ) -> str:
        """Get log statistics per device (log rate, disk usage, last log time).
        Uses ``/logview/adom/<adom>/logstats``.

        Args:
            device_id: Device name (e.g. ``"FAZ-01"``).
            adom: ADOM name, default ``"root"``.
            log_type: Log type — ``"traffic"``, ``"event"``, etc.

        Returns:
            JSON: Per-device stats (devname, lograte, log-disk-size, last-log-time).
        """
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute(
                f"/logview/adom/{adom}/logstats",
                data={"logtype": log_type},
            )
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def get_log_files_state(
        self, device_id: str, adom: str = "root",
        devid: str | None = None, vdom: str = "root",
    ) -> str:
        """List log files on FAZ for a device.
        Uses ``/logview/adom/<adom>/logfiles/state``.

        Args:
            device_id: FAZ device name.
            adom: ADOM name.
            devid: Device serial (e.g. ``"FGVM16TM25000854"``). Omit for all.
            vdom: VDOM name, default ``"root"``.

        Returns:
            JSON: Log file list with filename, logtype, start/endtime, size.
        """
        try:
            faz = await self._get_client(device_id)
            params: dict[str, Any] = {"vdom": vdom}
            if devid:
                params["devid"] = devid
            result = await faz.execute(
                f"/logview/adom/{adom}/logfiles/state", data=params,
            )
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def read_log_file(
        self, device_id: str, adom: str = "root",
        devid: str = "", vdom: str = "root",
        filename: str = "tlog.log", log_type: str = "traffic",
        limit: int = 100, data_type: str = "base64",
    ) -> str:
        """Read raw log data from a log file on FAZ.
        Uses ``/logview/adom/<adom>/logfiles/data``.

        Args:
            device_id: FAZ device name.
            adom: ADOM name.
            devid: Device serial (required).
            vdom: VDOM name.
            filename: Log file name (e.g. ``"tlog.log"``).
            log_type: Log type — ``"traffic"``, ``"event"``, etc.
            limit: Max entries (default 100).
            data_type: Encoding — ``"base64"`` (default), ``"text/gzip/base64"``.

        Returns:
            JSON: Base64-encoded log data with checksum, offset, length.
            Decode with ``base64.b64decode(data)`` for binary log format.
        """
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute(
                f"/logview/adom/{adom}/logfiles/data",
                data={
                    "devid": devid, "vdom": vdom, "filename": filename,
                    "logtype": log_type, "limit": limit, "data-type": data_type,
                },
            )
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    # ═══════════════════════════════════════════════════════════════════
    # FortiView Analytics (async add→get flow)
    # ═══════════════════════════════════════════════════════════════════
    #
    # FAZ FortiView API requirements (learned the hard way):
    # 1. "device" filter is MANDATORY — "No eligible device(s)" without it
    # 2. All params must be TOP-LEVEL in params[0] (use extra_params, NOT data)
    # 3. "apiver": 3 is required for both add and get requests
    # 4. get response is a dict (not a list): {status, data, percentage, ...}
    # 5. Default device: "All_FortiGate" covers FortiGates; use specific devid
    #    (e.g. "FGVM16TM25000879") to narrow to one device

    async def get_fortiview_top_sources(
        self, device_id: str, adom: str = "root",
        limit: int = 10, time_range_start: str | None = None,
        time_range_end: str | None = None,
        devid: str = "All_FortiGate",
    ) -> str:
        """Get top source IPs by traffic via FortiView.
        Uses ``/fortiview/adom/<adom>/top-sources/run`` (async add→get).

        Args:
            device_id, adom, limit (default 10).
            time_range_start / time_range_end: e.g. ``"2026-06-14 00:00:00"``.
                Required — defaults to last 24h if omitted.
            devid: Device filter (default ``"All_FortiGate"``).
                For specific device use devid like ``"FGVM16TM25000879"``.

        Returns:
            JSON: Top sources with srcip, bandwidth, sessions, threats, fortigate.
        """
        try:
            faz = await self._get_client(device_id)
            if not time_range_start:
                end = datetime.now()
                start = end - timedelta(hours=24)
                time_range_start = start.strftime("%Y-%m-%d %H:%M:%S")
                time_range_end = end.strftime("%Y-%m-%d %H:%M:%S")
            # API doc: params MUST be top-level (use extra_params), include apiver
            extra: dict[str, Any] = {
                "apiver": 3,
                "time-range": {"start": time_range_start, "end": time_range_end},
                "limit": limit,
                "device": [{"devid": devid}],
            }
            result = await faz.execute(
                f"/fortiview/adom/{adom}/top-sources/run",
                extra_params=extra, method="add",
            )
            tid = result.get("result", {}).get("tid")
            if not tid:
                return self._format_error("No TID returned, raw: " + str(result))

            # Poll until complete (async add→get; timeout 30s)
            for _ in range(15):
                await asyncio.sleep(2)
                result = await faz.execute(
                    f"/fortiview/adom/{adom}/top-sources/run/{tid}",
                    extra_params={"apiver": 3}, method="get",
                )
                data = result.get("result", {})
                if isinstance(data, dict):
                    status = data.get("status", {})
                    code = status.get("code", -1)
                    if code == 0:
                        return self._format_success(data)
                    if code != 1:  # 1 = still processing
                        return self._format_error(
                            f"FortiView failed: {status.get('message', 'unknown')} (code={code})"
                        )
            return self._format_error("FortiView task timed out after 30s")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def get_fortiview_top_destinations(
        self, device_id: str, adom: str = "root",
        limit: int = 10, time_range_start: str | None = None,
        time_range_end: str | None = None,
        devid: str = "All_FortiGate",
    ) -> str:
        """Get top destination IPs by traffic via FortiView.
        Same params as ``get_fortiview_top_sources``."""
        try:
            faz = await self._get_client(device_id)
            if not time_range_start:
                end = datetime.now()
                start = end - timedelta(hours=24)
                time_range_start = start.strftime("%Y-%m-%d %H:%M:%S")
                time_range_end = end.strftime("%Y-%m-%d %H:%M:%S")
            extra: dict[str, Any] = {
                "apiver": 3,
                "time-range": {"start": time_range_start, "end": time_range_end},
                "limit": limit,
                "device": [{"devid": devid}],
            }
            result = await faz.execute(
                f"/fortiview/adom/{adom}/top-destinations/run",
                extra_params=extra, method="add",
            )
            tid = result.get("result", {}).get("tid")
            if not tid:
                return self._format_error("No TID returned, raw: " + str(result))
            for _ in range(15):
                await asyncio.sleep(2)
                result = await faz.execute(
                    f"/fortiview/adom/{adom}/top-destinations/run/{tid}",
                    extra_params={"apiver": 3}, method="get",
                )
                data = result.get("result", {})
                if isinstance(data, dict):
                    status = data.get("status", {})
                    code = status.get("code", -1)
                    if code == 0:
                        return self._format_success(data)
                    if code != 1:
                        return self._format_error(
                            f"FortiView failed: {status.get('message', 'unknown')} (code={code})"
                        )
            return self._format_error("FortiView task timed out after 30s")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    # ═══════════════════════════════════════════════════════════════════
    # System Status & Info
    # ═══════════════════════════════════════════════════════════════════

    async def get_system_status(self, device_id: str) -> str:
        """Get FortiAnalyzer system status — version, hostname, serial, disk.
        Note: admin session returns -11; uses Bearer token (hermes) as fallback.
        Returns: JSON system info."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/sys/status")
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def get_license_info(self, device_id: str) -> str:
        """Get FortiAnalyzer license information.
        Uses ``/fazsys/forticare/licinfo``.
        Returns: JSON license status, expiration."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/fazsys/forticare/licinfo")
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def get_ha_status(self, device_id: str) -> str:
        """Get HA cluster status.
        Uses ``/sys/ha/status``.
        Returns: JSON HA info."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/sys/ha/status")
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def get_storage_info(self, device_id: str) -> str:
        """Get storage usage information.
        Uses ``/fazsys/storage-info``.
        Returns: JSON disk/volume usage."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/fazsys/storage-info")
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def get_system_performance(self, device_id: str) -> str:
        """Get system performance status (CPU/memory).
        Uses ``/fazsys/monitor/system/performance/status``.
        Returns: JSON performance metrics."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/fazsys/monitor/system/performance/status")
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    async def get_log_forward_status(self, device_id: str) -> str:
        """Get log forwarding server status.
        Uses ``/fazsys/monitor/logforward-status``.
        Returns: JSON forwarding status."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/fazsys/monitor/logforward-status")
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    # ═══════════════════════════════════════════════════════════════════
    # Reports
    # ═══════════════════════════════════════════════════════════════════

    async def list_report_schedules(
        self, device_id: str, adom: str = "root",
    ) -> str:
        """List report schedules.
        Uses ``/report/config/schedule``.
        Returns: JSON schedule list."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute(
                "/report/config/schedule", extra_params={"adom": adom},
            )
            return self._format_list(result.get("result", []), "schedules")
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    # ═══════════════════════════════════════════════════════════════════
    # IOC
    # ═══════════════════════════════════════════════════════════════════

    async def get_ioc_license_state(self, device_id: str) -> str:
        """Get IOC license state.
        Uses ``/ioc/license/state``.
        Returns: JSON IOC license info."""
        try:
            faz = await self._get_client(device_id)
            result = await faz.execute("/ioc/license/state")
            return self._format_success(result.get("result", [{}])[0])
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))

    # ═══════════════════════════════════════════════════════════════════
    # Generic Request — fallback for any endpoint
    # ═══════════════════════════════════════════════════════════════════

    async def faz_request(
        self, device_id: str, url: str,
        data: dict[str, Any] | None = None,
        adom: str | None = None, method: str = "get",
    ) -> str:
        """Execute any FortiAnalyzer JSON-RPC API endpoint directly.

        Use when no convenience tool exists. Supports ``get``, ``add``,
        ``set``, ``update``, ``delete``, ``exec`` methods.

        Args:
            device_id: FAZ device name (e.g. ``"FAZ-01"``).
            url: API path (e.g. ``"/dvmdb/adom"``, ``"/logview/adom/root/logstats"``).
            data: Optional request data dict.
            adom: Optional ADOM override.
            method: JSON-RPC verb, default ``"get"``.

        Returns:
            JSON: Raw API response.
        """
        try:
            faz = await self._get_client(device_id)
            extra: dict[str, Any] = {}
            if adom:
                extra["adom"] = adom
            result = await faz.execute(url, data=data, extra_params=extra or None, method=method)
            return self._format_success(result.get("result", []))
        except (ValueError, FortiAnalyzerError) as e:
            return self._format_faz_error(str(e))
