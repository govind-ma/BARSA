# Barsa MCP Server — Client Setup Guide

This guide describes how to configure AI desktop clients, CLI tools, and development environments to connect to the Barsa MCP server.

---

## 1. Prerequisites

- Python 3.12+ (or 3.14 virtual environment) installed.
- BARSA installed in editable or package mode:
  ```bash
  pip install -e .
  ```
- Verify CLI is working:
  ```bash
  barsa info
  ```

---

## 2. Claude Desktop Setup

Edit your Claude Desktop configuration file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add the `barsa` MCP server:

```json
{
  "mcpServers": {
    "barsa": {
      "command": "d:\\projects\\BARSA\\.venv\\Scripts\\barsa.exe",
      "args": ["mcp", "serve", "--transport", "stdio"],
      "env": {
        "BARSA_ENVIRONMENT": "development",
        "BARSA_DATA_DIR": "d:\\projects\\BARSA\\.barsa_data",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

*Note:* Ensure the absolute path to your virtual environment's `barsa.exe` (or `python -m barsa.cli`) is used.

---

## 3. Testing with Official MCP Inspector

You can test and explore all 12 tools and 5 resources interactively in your browser using the official Anthropic MCP Inspector:

```bash
npx @modelcontextprotocol/inspector d:\projects\BARSA\.venv\Scripts\barsa.exe mcp serve --transport stdio
```

The inspector will launch an interactive UI on `http://localhost:5173`, allowing you to execute tools, view schemas, and inspect resources in real-time.

---

## 4. Cursor / Windsurf / VS Code Setup

In Cursor / Windsurf settings, navigate to **Features > MCP Servers** and add:
- **Name:** `barsa`
- **Type:** `command`
- **Command:** `d:\projects\BARSA\.venv\Scripts\barsa.exe mcp serve --transport stdio`

---

## 5. Network / HTTP Transports (Streamable-HTTP & SSE)

For multi-host or remote deployments, Barsa supports network transports:

### Streamable-HTTP
```bash
barsa mcp serve --transport streamable-http --host 127.0.0.1 --port 8765
```

### Server-Sent Events (SSE)
```bash
barsa mcp serve --transport sse --host 127.0.0.1 --port 8765
```
Connect your client using endpoint URL: `http://127.0.0.1:8765/sse`.
