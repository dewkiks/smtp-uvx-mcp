"""SMTP UVX MCP package.

Provides an MCP stdio server for sending emails via SMTP.
"""

from .server import EmailClient  # re-export for public API

__all__ = [
    "EmailClient",
]

__version__ = "0.1.0"
