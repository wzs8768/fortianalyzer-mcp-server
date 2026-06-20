#!/usr/bin/env python3
"""
FortiAnalyzer API client — asynchronous JSON-RPC HTTP client.

Dual authentication:
- Bearer token (REST API admin) for general API (dvmdb, sys, …)
- Session (username/password login) for log APIs (/log/*)
"""
import asyncio
import logging
import re

import httpx

logger = logging.getLogger("fortianalyzer_mcp.client")

class FortiAnalyzerError(Exception):
    def __init__(self, message, status_code=None, error_info=None):
        super().__init__(message)
        self.status_code = status_code
        self.error_info = error_info or {}

class FortiAnalyzerClient:
    """Async API client for FortiAnalyzer.

    Session resilience: if the FAZ server drops the connection (HTTP errors,
    -11 permission errors on a previously working session), the client
    automatically reconnects once and retries.

    Dual auth: Bearer token for most APIs, session-based auth for /log/*.
    """

    # FAZ error codes that mean the session is gone — revive once.
    _RECONNECTABLE_CODES = frozenset({-2, -11, -20, -21})

    def __init__(self, host, port=443, username=None, password=None,
                 api_token=None, adom="root", verify_ssl=True, timeout=60,
                 use_ssl=True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.api_token = api_token
        self.adom = adom
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._scheme = "https" if use_ssl else "http"
        self._session_id = None       # session from username/password login
        self._bearer_token = None     # Bearer token for non-log APIs
        self._request_id = 0
        self._client = None
        self._connected = False
        self._ever_connected = False

    @property
    def base_url(self):
        return self._scheme + "://" + self.host + ":" + str(self.port)

    @property
    def jsonrpc_url(self):
        return self.base_url + "/jsonrpc"

    @property
    def _auth_headers(self):
        """Headers for API key (Bearer) authentication."""
        if self._bearer_token:
            return {"Authorization": f"Bearer {self._bearer_token}"}
        return {}

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()

    async def connect(self):
        """Establish connection and authenticate with both methods."""
        if self._connected:
            return
        self._client = httpx.AsyncClient(
            verify=self.verify_ssl,
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        await self._login()

    async def disconnect(self):
        if self._client:
            try:
                await self._logout()
            except Exception:
                pass
            await self._client.aclose()
            self._client = None
            self._connected = False
            self._session_id = None
            self._bearer_token = None

    async def ensure_connected(self):
        if self.is_connected:
            return
        logger.warning("FAZ %s: session dropped; reconnecting once", self.host)
        await self.connect()

    async def _force_reconnect(self):
        logger.info("FAZ %s: forcing reconnect", self.host)
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
        self._client = None
        self._connected = False
        self._session_id = None
        self._bearer_token = None
        await self.connect()

    async def _login(self):
        """Authenticate to FortiAnalyzer.

        Runs Bearer token probe and username/password login concurrently.
        At least one must succeed.
        """
        bearer_ok = False
        session_ok = False

        async def _try_bearer():
            nonlocal bearer_ok
            if not self.api_token:
                return
            test_body = {
                "jsonrpc": "2.0",
                "method": "get",
                "params": [{"url": "/sys/status"}],
                "id": 1,
            }
            try:
                resp = await self._client.post(
                    self.jsonrpc_url,
                    json=test_body,
                    headers={"Authorization": f"Bearer {self.api_token}"},
                )
                resp.raise_for_status()
                result = resp.json()
                r = result.get("result", [{}])[0] if isinstance(result.get("result"), list) else result.get("result", {})
                code = r.get("status", {}).get("code", 0)

                if code in (0, -11):
                    self._bearer_token = self.api_token
                    bearer_ok = True
                    level = "info" if code == 0 else "warning"
                    getattr(logger, level)(
                        "FAZ %s: Bearer token OK (code=%s)", self.host, code
                    )
                elif code == -22:
                    raise FortiAnalyzerError(f"FAZ {self.host}: invalid API token")
            except FortiAnalyzerError:
                raise
            except Exception as e:
                logger.debug("FAZ %s: Bearer auth check failed: %s", self.host, e)

        async def _try_session():
            nonlocal session_ok
            if not (self.username and self.password):
                return
            creds = {"user": self.username, "passwd": self.password}
            login_body = {
                "jsonrpc": "2.0",
                "method": "exec",
                "params": [{"url": "/sys/login/user", "data": creds}],
                "id": 1,
            }
            try:
                resp = await self._client.post(self.jsonrpc_url, json=login_body)
                resp.raise_for_status()
                result = resp.json()
                session = None
                if isinstance(result, dict):
                    session = result.get("session")
                    if not session and "result" in result:
                        r = result["result"]
                        if isinstance(r, list) and len(r) > 0 and isinstance(r[0], dict):
                            session = r[0].get("session")
                if session:
                    self._session_id = session
                    session_ok = True
                    logger.info("FAZ %s: session login OK (user=%s)", self.host, self.username[:8] + "...")
                else:
                    logger.warning(
                        "FAZ %s: session login failed — no session in response. Code: %s",
                        self.host,
                        result.get("result", [{}])[0].get("status", {}).get("code", "?")
                        if isinstance(result.get("result"), list) else "?",
                    )
            except httpx.HTTPStatusError as e:
                logger.warning("FAZ %s: session login HTTP %s", self.host, e.response.status_code)
            except Exception as e:
                logger.debug("FAZ %s: session login failed: %s", self.host, e)

        await asyncio.gather(_try_bearer(), _try_session())

        if bearer_ok or session_ok:
            self._connected = True
            self._ever_connected = True
            logger.info(
                "FAZ %s: connected (bearer=%s, session=%s)",
                self.host, bearer_ok, session_ok,
            )
            return

        raise FortiAnalyzerError(
            f"FAZ {self.host}: no valid credentials. "
            "Configure api_token and/or username + password."
        )

    async def _logout(self):
        if self._session_id:
            try:
                await self._client.post(self.jsonrpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "exec", "params": [{"url": "/sys/logout"}],
                    "session": self._session_id, "id": self._next_id(),
                })
            except Exception:
                pass
        self._session_id = None
        self._bearer_token = None

    def _next_id(self):
        self._request_id += 1
        return self._request_id

    def _validate_path(self, path):
        clean = path.strip("/")
        if ".." in clean:
            raise ValueError("Invalid path: " + path)
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9._/-]*$', clean):
            raise ValueError("Invalid path: " + path)
        return clean

    def _is_log_endpoint(self, url: str) -> bool:
        """Check if URL targets a log API that needs session auth."""
        clean = url.strip("/")
        return clean.startswith("log/") or clean.startswith("logview/")

    async def execute(self, url, data=None, extra_params=None, method="get"):
        """Execute a JSON-RPC request with auto-reconnect on session drop."""
        reconnect_left = 1 if self._ever_connected else 0

        while True:
            try:
                return await self._execute_once(url, data, extra_params, method)
            except FortiAnalyzerError as e:
                if reconnect_left > 0 and e.error_info.get("code") in self._RECONNECTABLE_CODES:
                    reconnect_left -= 1
                    logger.warning(
                        "FAZ %s: session error (code %s); reconnecting once and retrying",
                        self.host, e.error_info.get("code"),
                    )
                    await self._force_reconnect()
                    continue
                raise
            except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError) as e:
                if reconnect_left > 0:
                    reconnect_left -= 1
                    logger.warning(
                        "FAZ %s: network error (%s); reconnecting once and retrying",
                        self.host, type(e).__name__,
                    )
                    await self._force_reconnect()
                    continue
                raise FortiAnalyzerError(f"FAZ {self.host}: network error: {e}")

    async def _execute_once(self, url, data=None, extra_params=None, method="get"):
        """Single JSON-RPC request — uses session auth for /log/*, Bearer otherwise."""
        if self._client is None:
            raise FortiAnalyzerError(f"FAZ {self.host}: not connected")
        clean_url = "/" + self._validate_path(url)
        param = {"url": clean_url}
        if data is not None:
            param["data"] = data
        if extra_params:
            param.update(extra_params)
        body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [param],
            "id": self._next_id(),
        }

        # Choose auth mode: prefer session for everything, Bearer as fallback
        headers = {}
        if self._session_id:
            body["session"] = self._session_id
        elif self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"

        resp = await self._client.post(
            self.jsonrpc_url,
            json=body,
            headers=headers,
        )
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, dict) and result.get("result"):
            r = result["result"]
            if isinstance(r, list) and len(r) > 0 and isinstance(r[0], dict):
                status = r[0].get("status", {})
                if isinstance(status, dict) and status.get("code", 0) != 0:
                    raise FortiAnalyzerError(
                        f"FAZ {self.host}: API error "
                        f"{status.get('code')}: {status.get('message', '')}"
                        f" [{clean_url}]",
                        error_info=status,
                    )
        return result

    async def execute_raw(self, url, data=None, method="get"):
        """Execute a raw JSON-RPC request (returns httpx Response)."""
        if self._client is None:
            raise FortiAnalyzerError(f"FAZ {self.host}: not connected")
        clean_url = "/" + self._validate_path(url)
        param = {"url": clean_url}
        if data is not None:
            param["data"] = data
        body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [param],
            "id": self._next_id(),
        }

        # Prefer session, Bearer as fallback
        headers = {}
        if self._session_id:
            body["session"] = self._session_id
        elif self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"

        return await self._client.post(
            self.jsonrpc_url,
            json=body,
            headers=headers,
        )
