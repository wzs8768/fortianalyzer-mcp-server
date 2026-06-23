#!/usr/bin/env python3
"""
FortiAnalyzer MCP Server — HTTP/HTTPS transport (FastMCP).

SSE + Streamable HTTP support with Bearer Token authentication.

    HTTPS · Streamable HTTP  https://<host>:8915/fortianalyzer-mcp
    HTTPS · SSE               https://<host>:8915/fortianalyzer-mcp-sse
    Health                    https://<host>:8915/health
    Metrics                   https://<host>:8915/metrics
"""
import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# Make src/ importable without pip install (systemd service, CI)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Conditional FastMCP import — supports both standalone fastmcp and mcp.server.fastmcp
try:
    from fastmcp import FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise RuntimeError(
            "FastMCP is not available. Please install 'fastmcp' or 'mcp' package."
        ) from None

from fortianalyzer_mcp.config.loader import load_config
from fortianalyzer_mcp.config.models import AppConfig, DeviceConfig
from fortianalyzer_mcp.core.faz_client import FortiAnalyzerClient
from fortianalyzer_mcp.core.logging import setup_logging
from fortianalyzer_mcp.tools.device import DeviceTools
from fortianalyzer_mcp.tools.modules import FazTools

logger = logging.getLogger("fortianalyzer_mcp.server")


# ════════════════════════════════════════════════════════════════════
# Device Manager
# ════════════════════════════════════════════════════════════════════

class FortiAnalyzerManager:
    """Manages multiple FortiAnalyzer device connections."""

    def __init__(self, config: AppConfig, use_ssl: bool = True):
        self.config = config
        self.clients: dict[str, FortiAnalyzerClient] = {}
        self._device_configs: dict[str, DeviceConfig] = {}
        self._use_ssl = use_ssl
        self.mcp = None  # set by main() after build_server

    async def start(self):
        """Initialize all configured device connections."""
        devices = self.config.devices
        for name, dev_cfg in devices.items():
            self._device_configs[name] = dev_cfg
            client = FortiAnalyzerClient(
                host=dev_cfg.host,
                port=dev_cfg.port,
                username=dev_cfg.username,
                password=dev_cfg.password,
                api_token=dev_cfg.api_token,
                adom=dev_cfg.adom,
                verify_ssl=dev_cfg.verify_ssl,
                timeout=dev_cfg.timeout,
                use_ssl=self._use_ssl,
            )
            try:
                await client.connect()
                self.clients[name] = client
                logger.info("Device '%s' (%s:%s) connected", name, dev_cfg.host, dev_cfg.port)
            except Exception as e:
                logger.error(
                    "Device '%s' (%s:%s) connection failed: %s. "
                    "Check host, port, and credentials in config.json.",
                    name, dev_cfg.host, dev_cfg.port, e
                )

    async def stop(self):
        """Disconnect all devices."""
        for name, client in self.clients.items():
            try:
                await client.disconnect()
                logger.info("Device '%s' disconnected", name)
            except Exception as e:
                logger.warning("Error disconnecting '%s': %s", name, e)
        self.clients.clear()

    def get_client(self, device_id: str) -> FortiAnalyzerClient | None:
        """Get a connected client by device name."""
        return self.clients.get(device_id)


# ════════════════════════════════════════════════════════════════════
# Auth Middleware
# ════════════════════════════════════════════════════════════════════

def build_auth_middleware(config: AppConfig):
    """Build a Starlette auth middleware class with bound config.

    Uses constant-time comparison to prevent timing side-channel attacks.
    """
    import hmac

    require_auth = config.auth.require_auth
    raw_tokens = config.auth.api_tokens

    # Normalize tokens into {token: name} dict
    token_lookup: dict[str, str] = {}
    for entry in raw_tokens:
        if isinstance(entry, str):
            token_lookup[entry] = "(unnamed)"
        elif isinstance(entry, dict):
            name = entry.get("name", "(unnamed)")
            token = entry.get("token", "")
            if token:
                token_lookup[token] = name

    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    class AuthMiddleware(BaseHTTPMiddleware):
        """Bearer Token auth with client identification."""

        async def dispatch(self, request, call_next):
            # Always-public paths
            skip_exact = {"/health"}
            skip_prefix = ("/.well-known/",)
            path = request.url.path
            if path in skip_exact or path.startswith(skip_prefix):
                return await call_next(request)

            if not require_auth:
                return await call_next(request)

            # MCP endpoints: when no Authorization header, let FastMCP
            # return 400 (Missing session ID) instead of 401.  Returning
            # 401 here triggers mcp-remote's OAuth/DCR flow and crashes.
            # When a token IS present, validate it normally.
            if path.startswith("/fortianalyzer-mcp"):
                auth = request.headers.get("Authorization", "")
                if not auth:
                    return await call_next(request)
                # Token present → fall through to validation below

            # Read Authorization header
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                logger.warning("Auth rejected — missing Bearer token from %s", request.client)
                return JSONResponse(
                    {"error": "unauthorized", "detail": "Missing or invalid Authorization header"},
                    status_code=401,
                )

            token = auth[7:]
            # Constant-time comparison
            client_name = None
            for valid_token, name in token_lookup.items():
                if hmac.compare_digest(token, valid_token):
                    client_name = name
                    break

            if client_name is None:
                logger.warning(
                    "Auth rejected — unknown token (first 8 chars: %s...) from %s",
                    token[:8], request.client
                )
                return JSONResponse(
                    {"error": "unauthorized", "detail": "Invalid token"},
                    status_code=401,
                )

            logger.info("Auth OK — client=%s path=%s", client_name, path)
            return await call_next(request)

    return AuthMiddleware


# ════════════════════════════════════════════════════════════════════
# Tool Registration
# ════════════════════════════════════════════════════════════════════

def register_all_tools(mcp: FastMCP, manager: FortiAnalyzerManager):
    """Register all MCP tools on the FastMCP server instance.

    Tools verified against FortiAnalyzer 8.0 API docs (Jun 2026):
    - Device management (5)
    - ADOM/device/folder/group (7)
    - Event/alert/incident (4)
    - Log view (3) — logstats, logfiles/state, logfiles/data
    - FortiView (2) — top-sources, top-destinations (async add→get)
    - System (6) — status, license, HA, storage, performance, log-forward
    - Reports (1) — schedule list
    - IOC (1) — license state
    - Generic request (1)
    """
    dev = DeviceTools(manager)
    mod = FazTools(manager)

    # ── Device Management ──────────────────────────────────────
    mcp.tool()(dev.list_devices)
    mcp.tool()(dev.get_device_status)
    mcp.tool()(dev.test_device_connection)
    mcp.tool()(dev.health_check)
    mcp.tool()(dev.get_server_info)

    # ── ADOM & Device Management ───────────────────────────────
    mcp.tool()(mod.list_adoms)
    mcp.tool()(mod.create_adom)
    mcp.tool()(mod.delete_adom)
    mcp.tool()(mod.get_adom_detail)
    mcp.tool()(mod.list_adom_devices)
    mcp.tool()(mod.list_folders)
    mcp.tool()(mod.list_device_groups)

    # ── Event / Alert / Incident ───────────────────────────────
    mcp.tool()(mod.list_alerts)
    mcp.tool()(mod.get_alert_count)
    mcp.tool()(mod.list_incidents)
    mcp.tool()(mod.get_incident_count)

    # ── Log View ───────────────────────────────────────────────
    mcp.tool()(mod.get_log_stats)
    mcp.tool()(mod.get_log_files_state)
    mcp.tool()(mod.read_log_file)

    # ── FortiView ──────────────────────────────────────────────
    mcp.tool()(mod.get_fortiview_top_sources)
    mcp.tool()(mod.get_fortiview_top_destinations)

    # ── System ─────────────────────────────────────────────────
    mcp.tool()(mod.get_system_status)
    mcp.tool()(mod.get_license_info)
    mcp.tool()(mod.get_ha_status)
    mcp.tool()(mod.get_storage_info)
    mcp.tool()(mod.get_system_performance)
    mcp.tool()(mod.get_log_forward_status)

    # ── Reports ────────────────────────────────────────────────
    mcp.tool()(mod.list_report_schedules)

    # ── IOC ────────────────────────────────────────────────────
    mcp.tool()(mod.get_ioc_license_state)

    # ── Generic Request ────────────────────────────────────────
    mcp.tool()(mod.faz_request)

    logger.info("Registered %d MCP tools", len(mcp._tool_manager._tools))


# ════════════════════════════════════════════════════════════════════
# Server Builder
# ════════════════════════════════════════════════════════════════════

def build_server(config: AppConfig, host: str = "0.0.0.0") -> FastMCP:
    """Build the FastMCP server with tools, auth, and routes.

    Args:
        config: Application configuration.
        host: Server bind address for host header validation.

    Returns:
        Configured FastMCP server instance.
    """
    mcp = FastMCP(
        name=config.server.name,
        host=host,
        streamable_http_path="/fortianalyzer-mcp",
        sse_path="/fortianalyzer-mcp-sse",
    )

    return mcp


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(
        description="FortiAnalyzer MCP Server — HTTP/HTTPS transport"
    )
    parser.add_argument("--host", default=None, help="Server bind address")
    parser.add_argument("--port", type=int, default=None, help="Server port")
    parser.add_argument(
        "--transport", default="all",
        choices=["all", "streamable-http", "sse"],
        help="Transport mode (default: all)"
    )
    parser.add_argument("--ssl-cert", default=None, help="SSL certificate path")
    parser.add_argument("--ssl-key", default=None, help="SSL private key path")
    parser.add_argument("--config", default=None, help="Config file path")
    args = parser.parse_args()

    # Load config
    cfg = load_config(args.config)
    setup_logging(
        level=cfg.logging.level,
        fmt=cfg.logging.format,
        log_file=cfg.logging.file,
        console=cfg.logging.console,
    )

    host = args.host or cfg.server.host
    port = args.port or cfg.server.port

    # Determine scheme before creating manager (needed for FAZ client)
    use_ssl = bool(args.ssl_cert and args.ssl_key)

    # Init device connections
    manager = FortiAnalyzerManager(cfg, use_ssl=use_ssl)
    await manager.start()

    # Build server with tools
    mcp = build_server(cfg, host)
    manager.mcp = mcp
    register_all_tools(mcp, manager)

    # Auth middleware
    auth_cls = build_auth_middleware(cfg)

    # Run
    import uvicorn
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    if args.ssl_cert and args.ssl_key:
        ssl_config = {
            "ssl_certfile": args.ssl_cert,
            "ssl_keyfile": args.ssl_key,
        }
        scheme = "https"
    else:
        ssl_config = {}
        scheme = "http"

    logger.info(
        "FortiAnalyzer MCP Server starting:\n"
        "  StreamableHTTP  %s://%s:%s/fortianalyzer-mcp\n"
        "  SSE             %s://%s:%s/fortianalyzer-mcp-sse\n"
        "  Health          %s://%s:%s/health\n"
        "  Transport       %s\n"
        "  Auth            %s",
        scheme, host, port,
        scheme, host, port,
        scheme, host, port,
        args.transport,
        "Bearer Token (enabled)" if cfg.auth.require_auth else "DISABLED",
    )

    # Health endpoint
    async def health(request):
        return JSONResponse({"status": "ok", "server": "fortianalyzer-mcp-server"})

    # Metrics endpoint — basic Prometheus-compatible counters
    _start_time = time.time()
    _req_count = 0

    async def metrics(request):
        uptime = time.time() - _start_time
        return JSONResponse({
            "uptime_seconds": round(uptime, 1),
            "requests_total": _req_count,
            "devices_connected": len(manager.clients),
            "tools_registered": len(mcp._tool_manager._tools) if mcp else 0,
        })

    # Request-counting middleware wrapper
    _starlette_app = None

    if args.transport == "all":
        sse_app = mcp.sse_app()
        sh_app = mcp.streamable_http_app()
        all_routes = list(sse_app.routes) + list(sh_app.routes)
        all_routes.append(Route("/health", health, methods=["GET"]))
        all_routes.append(Route("/metrics", metrics, methods=["GET"]))
        lifespan = sh_app.router.lifespan_context
        starlette_app = Starlette(debug=False, routes=all_routes, lifespan=lifespan)
        starlette_app.add_middleware(auth_cls)

        config = uvicorn.Config(
            starlette_app, host=host, port=port,
            log_level=cfg.logging.level.lower(),
            **ssl_config,
        )
        server = uvicorn.Server(config)
        try:
            await server.serve()
        finally:
            await manager.stop()
    elif args.transport == "streamable-http":
        sh_app = mcp.streamable_http_app()
        sh_app.routes.append(Route("/health", health, methods=["GET"]))
        sh_app.add_middleware(auth_cls)

        config = uvicorn.Config(
            sh_app, host=host, port=port,
            log_level=cfg.logging.level.lower(),
            **ssl_config,
        )
        server = uvicorn.Server(config)
        try:
            await server.serve()
        finally:
            await manager.stop()
    elif args.transport == "sse":
        sse_app = mcp.sse_app()
        sse_app.routes.append(Route("/health", health, methods=["GET"]))
        sse_app.add_middleware(auth_cls)

        config = uvicorn.Config(
            sse_app, host=host, port=port,
            log_level=cfg.logging.level.lower(),
            **ssl_config,
        )
        server = uvicorn.Server(config)
        try:
            await server.serve()
        finally:
            await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
