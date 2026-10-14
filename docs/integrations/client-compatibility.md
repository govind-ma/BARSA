# Client Compatibility Matrix

BARSA supports a variety of AI model providers, client hosts, and runtime environments.

## Tested Client Environments

| Client Platform | Provider | Supported Transports | Tool Calling | Checkpoint Resumption | DAG Commits | Security Scopes |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Claude Desktop** | Anthropic | stdio | Full | Supported | Supported | Supported |
| **Claude Code (CLI)** | Anthropic | stdio | Full | Supported | Supported | Supported |
| **ChatGPT (Custom GPT)** | OpenAI | SSE / HTTPS | Full | Supported | Supported | Supported |
| **Cursor / Windsurf** | Multi-model | stdio / SSE | Full | Supported | Supported | Supported |
| **Zed Editor** | Multi-model | stdio | Full | Supported | Supported | Supported |
| **Custom Agent Scripts** | Any | In-Memory / REST | Full | Supported | Supported | Supported |

## Capability Support by Protocol

| Feature | MCP Tool Mapping | Direct REST API | BMS Package Export/Import |
| :--- | :--- | :--- | :--- |
| **Project Selection** | `barsa_resume` | `GET /api/v1/projects/{id}` | Direct file ingestion |
| **Task Continuation** | `barsa_resume` | `GET /api/v1/projects/{id}/checkpoints/latest` | Extracted from package |
| **DAG Commit** | `barsa_commit` | `POST /api/v1/projects/{id}/commits` | Replayed via commit DAG |
| **Proposals & Reviews**| `barsa_propose_changes` | `POST /api/v1/coordination/proposals` | Exported as proposals |
| **History & Provenance**| `barsa_get_history` | `GET /api/v1/projects/{id}/commits` | Retained in history |
