"""Basic tests for FortiAnalyzer MCP Server — config loading + client."""
import json
import tempfile
from pathlib import Path

import pytest


class TestConfigLoading:
    """Validate config loader with minimal fixtures."""

    def test_load_example_config(self):
        """Example config parses without error."""
        from fortianalyzer_mcp.config.loader import load_config
        example = Path(__file__).resolve().parent.parent / "config" / "config.example.json"
        config = load_config(str(example))
        assert config.server.port == 8915
        assert config.auth.require_auth is True
        assert len(config.auth.api_tokens) >= 1

    def test_default_fills_auth(self):
        """Missing config gets safe defaults."""
        from fortianalyzer_mcp.config.loader import load_config
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"server": {"port": 9999}}, f)
            path = f.name
        try:
            config = load_config(path)
            assert config.server.port == 9999
            assert config.auth.require_auth is True  # default
            assert isinstance(config.auth.api_tokens, list)
        finally:
            Path(path).unlink()

    def test_device_config_parses(self):
        """Device config fields are correctly loaded."""
        from fortianalyzer_mcp.config.loader import load_config
        example = Path(__file__).resolve().parent.parent / "config" / "config.example.json"
        config = load_config(str(example))
        devices = config.devices
        assert "FAZ-01" in devices
        faz = devices["FAZ-01"]
        assert faz.host == "192.168.1.100"
        assert faz.port == 443
        assert faz.adom == "root"


class TestFazClientConstruction:
    """FortiAnalyzerClient can be instantiated without connecting."""

    def test_client_defaults(self):
        from fortianalyzer_mcp.core.faz_client import FortiAnalyzerClient
        client = FortiAnalyzerClient(host="10.0.0.1")
        assert client.host == "10.0.0.1"
        assert client.port == 443
        assert client._scheme == "https"  # default use_ssl=True
        assert not client.is_connected

    def test_client_http_mode(self):
        from fortianalyzer_mcp.core.faz_client import FortiAnalyzerClient
        client = FortiAnalyzerClient(host="10.0.0.1", port=8080, use_ssl=False)
        assert client._scheme == "http"
        assert "http://" in client.base_url

    def test_path_validation_allows_uppercase_adom(self):
        from fortianalyzer_mcp.core.faz_client import FortiAnalyzerClient
        client = FortiAnalyzerClient(host="10.0.0.1")
        # previously rejected uppercase; fix #6
        assert client._validate_path("/dvmdb/adom/PROD/device") == "dvmdb/adom/PROD/device"
        assert client._validate_path("/fortiview/adom/root/top-sources/run") == "fortiview/adom/root/top-sources/run"

    def test_path_validation_rejects_traversal(self):
        from fortianalyzer_mcp.core.faz_client import FortiAnalyzerClient
        client = FortiAnalyzerClient(host="10.0.0.1")
        with pytest.raises(ValueError):
            client._validate_path("/../../../etc/passwd")
