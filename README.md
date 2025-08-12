# Email MCP Server

An MCP (Model Context Protocol) server for sending emails via SMTP.

## Configuration

Set these environment variables:
- `SMTP_HOST`: SMTP server hostname (e.g., smtp.gmail.com)
- `SMTP_PORT`: SMTP server port (e.g., 587)
- `SMTP_SECURE`: Use SSL/TLS (true/false)
- `SMTP_USER`: Your email username
- `SMTP_PASS`: Your email app password

## Usage with uvx

```bash
uvx --from git+https://github.com/your-username/email-mcp-server.git email-mcp
