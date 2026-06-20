"""Structured logging for FortiAnalyzer MCP server."""
import logging
import sys


def setup_logging(
    level: str = "INFO",
    fmt: str | None = None,
    log_file: str | None = None,
    console: bool = True,
):
    """Configure logging for the MCP server.

    Args:
        level: Log level name (DEBUG, INFO, WARNING, ERROR).
        fmt: Log format string.
        log_file: Optional file path for log output.
        console: Whether to log to stdout.
    """
    if fmt is None:
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    root = logging.getLogger("fortianalyzer_mcp")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    if console:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(handler)

    if log_file:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(handler)
