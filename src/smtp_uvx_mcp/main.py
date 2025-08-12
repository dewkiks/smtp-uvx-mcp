"""Console entrypoint for the SMTP UVX MCP server."""

import asyncio
from .server import _run


def main() -> None:
    """Start the MCP stdio server."""
    asyncio.run(_run())
