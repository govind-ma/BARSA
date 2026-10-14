# Generic MCP Client Integration

BARSA fully complies with the Model Context Protocol (MCP) specification. Any MCP client (such as Cursor, Windsurf, Zed, Continue.dev, or custom Python/TypeScript agents) can connect to BARSA.

## Standard MCP Discovery

When a client connects to BARSA, the following tools are published:

| Tool Name | Parameters | Purpose |
| :--- | :--- | :--- |
| `barsa_resume` | `project_id`, `task_id`, `max_context_tokens`, `expected_revision` | Resumes project state and returns smart context package |
| `barsa_commit` | `project_id`, `branch`, `changes`, `message`, `expected_head` | Commits atomic memory mutations to the version DAG |
| `barsa_get_checkpoint` | `project_id`, `checkpoint_id` | Retrieves a specific checkpoint by ID |
| `barsa_get_history` | `project_id`, `limit` | Lists the commit history for a project |
| `barsa_propose_changes` | `project_id`, `branch`, `changes`, `title`, `description` | Creates a proposal for human or peer review |

## Cursor & Windsurf Setup

In `.cursor/mcp.json` or `.windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "barsa-memory": {
      "command": "python",
      "args": ["-m", "barsa.mcp.cli", "run"],
      "env": {
        "BARSA_DATA_DIR": "./.barsa_data"
      }
    }
  }
}
```

## Protocol Features Supported

- **Dynamic Resource Subscriptions:** Clients can subscribe to `barsa://projects/{id}/status` for real-time memory update notifications.
- **Structured Error Handling:** Standard JSON-RPC error codes (-32602 for invalid params, custom application error codes for authentication and concurrency conflicts).
