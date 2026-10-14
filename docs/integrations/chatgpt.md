# ChatGPT & OpenAI Integration

BARSA interfaces with OpenAI GPT-4o, ChatGPT Custom GPT Actions, and Python OpenAI SDK scripts.

## Transport Modes

1. **Local MCP-Bridge (stdio):**
   Used by developer tools like Cursor, Windsurf, or local CLI agents calling OpenAI models.
2. **Server-Sent Events (SSE / HTTPS):**
   Used by remote OpenAI Custom GPT Actions or web assistants via an MCP SSE gateway.

## Configuration for OpenAI SDK Agents

```python
from barsa.integrations.adapter import MCPClientAdapter
from barsa.integrations.models import AIProvider, ClientSessionConfig
from barsa.integrations.session import AgentSession
from barsa.mcp.server import create_mcp_server

config = ClientSessionConfig(
    client_id="openai-gpt4o-agent",
    provider=AIProvider.OPENAI,
    model="gpt-4o",
    api_key="your_barsa_scoped_agent_key",
)
adapter = MCPClientAdapter(config, server)
session = AgentSession(config, adapter)

# Resume project state
handoff_context = await session.start("proj-spring-auth")
```

## Known Limitations & Best Practices

- **Context Window Utilization:** While GPT-4o has a 128k context window, injecting raw file logs degrades instruction following. Always use `barsa_resume` to retrieve the compressed, ranked smart context (~100-500 tokens).
- **JSON Schema Strictness:** Ensure changes submitted to `barsa_commit` adhere strictly to BMS v0.1 record schemas.
