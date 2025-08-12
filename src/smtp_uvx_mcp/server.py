import os
import asyncio
from typing import List, Dict, Any, Optional

from email.message import EmailMessage
from email.utils import make_msgid

# MCP Python SDK (low-level stdio server)
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

import aiosmtplib

try:
    # Optional: load .env for local development
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


class EmailClient:
    def __init__(self) -> None:
        host = os.environ.get("SMTP_HOST")
        if not host:
            raise RuntimeError("SMTP_HOST is required")

        port_str = os.environ.get("SMTP_PORT", "587")
        try:
            port = int(port_str)
        except ValueError:
            port = 587

        secure = os.environ.get("SMTP_SECURE", "false").lower() == "true"
        self.host = host
        self.port = port
        self.use_tls = secure  # SMTPS (implicit TLS)
        self.username = os.environ.get("SMTP_USER")
        self.password = os.environ.get("SMTP_PASS")
        if not self.username or not self.password:
            raise RuntimeError("SMTP_USER and SMTP_PASS are required")
        self.from_addr = os.environ.get("SMTP_FROM") or self.username

    async def send_email(self, *, to: List[str], subject: str, text: str, html: Optional[str] = None) -> Dict[str, Any]:
        if not to:
            raise ValueError("At least one recipient is required")

        msg = EmailMessage()
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject

        # Generate a message-id for tracking (SMTP server may also add its own)
        msg_id = make_msgid()
        msg["Message-Id"] = msg_id

        if html:
            msg.set_content(text or "")
            msg.add_alternative(html, subtype="html")
        else:
            msg.set_content(text or "")

        # Connect and send
        # For SMTPS (implicit TLS, usually port 465): use_tls=True
        # For STARTTLS: use_tls=False + start_tls=True on send
        start_tls = not self.use_tls  # mirror common setup: 587 -> STARTTLS
        try:
            response = await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
                start_tls=start_tls,
            )
            code, info = response
            return {
                "messageId": msg_id,
                "accepted": to,
                "rejected": [],
                "responseCode": code,
                "responseInfo": info.decode() if hasattr(info, "decode") else str(info),
            }
        except Exception as e:
            # On failure, treat all recipients as rejected for parity
            return {
                "messageId": msg_id,
                "accepted": [],
                "rejected": to,
                "error": str(e),
            }


"""
MCP server over stdio compatible with StdioServerParameters.
"""
server = Server("email-mcp-server")
email_client = EmailClient()


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Advertise available tools to the client."""
    return [
        types.Tool(
            name="send_email",
            description="Send an email to a recipient",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of recipient email addresses",
                    },
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {
                        "type": "string",
                        "description": "Email body content (text/plain)",
                    },
                },
                "required": ["to", "subject", "body"],
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle tool invocations from the client."""
    if name != "send_email":
        raise ValueError(f"Unknown tool: {name}")

    to = arguments.get("to") or []
    subject = arguments.get("subject") or ""
    body = arguments.get("body") or ""
    if not isinstance(to, list) or not all(isinstance(x, str) for x in to):
        raise ValueError("'to' must be a list of strings")

    result = await email_client.send_email(to=to, subject=subject, text=body)
    import json as _json
    return [types.TextContent(type="text", text=_json.dumps(result))]


async def _run() -> None:
    """Run the MCP server over stdio."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="Email MCP Server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
