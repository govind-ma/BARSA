# Claude Desktop & Claude Code Integration

Anthropic's Claude Desktop and Claude Code CLI can directly connect to the BARSA MCP server.

## Claude Desktop Configuration

Add the following to your `claude_desktop_config.json` (located at `%APPDATA%\Claude\claude_desktop_config.json` on Windows or `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "barsa": {
      "command": "python",
      "args": ["-m", "barsa.mcp.cli", "run"],
      "env": {
        "BARSA_DATA_DIR": "C:\\Users\\<YourUser>\\.barsa\\data",
        "BARSA_AGENT_KEY": "barsa_key_your_scoped_agent_key_here"
      }
    }
  }
}
```

## Recommended Workflow

1. **Start of Session:**
   Ask Claude: `"Please resume project proj-spring-auth using the Barsa memory tools."`
   Claude will execute `barsa_resume` to retrieve authoritative checkpoints, decisions, and active files.

2. **During Development:**
   Claude reads and writes project artifacts. As key architectural decisions are finalized, ask Claude:
   `"Record our decision to use HMAC-SHA256 for token verification in Barsa."`

3. **End of Task / Handoff:**
   Ask Claude: `"Commit our work and save a checkpoint for the next developer."`
   Claude calls `barsa_commit` with an updated `ResumeCheckpoint`, guaranteeing that any subsequent agent or engineer can resume with zero information loss.
