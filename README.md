# BARSA — Universal AI Memory and Collaboration Infrastructure

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)

BARSA allows users to switch between different AI systems (ChatGPT, Claude, Gemini, coding agents, etc.) while preserving shared project knowledge, context, decisions, and work progress.

---

## Architecture Overview (Phase 1)

BARSA is built around a **local-first and storage-independent** design. It decouples the data standard from storage backends, ensuring users and organizations retain sovereignty over their data without incurring mandatory managed-storage fees.

```
┌────────────────────────────────────────────────────────┐
│               AI Systems & Agents                      │
│     (Claude, ChatGPT, Gemini, Coding Assistants)        │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP REST / Future MCP
┌──────────────────────────▼─────────────────────────────┐
│                   Barsa Runtime                        │
│          FastAPI App · Core Config · Logging           │
└──────────────────────────┬─────────────────────────────┘
                           │ Protocol Interface
┌──────────────────────────▼─────────────────────────────┐
│               Storage Adapter Layer                    │
│    (Local Filesystem, Future S3 / Git / Cloud / etc.)  │
└────────────────────────────────────────────────────────┘
```

---

## Getting Started

### Prerequisites

- Python 3.12+ (Python 3.12 to 3.14 supported)
- Git

### Installation

1. Clone or open the repository:
   ```powershell
   git clone <repo-url> barsa
   cd barsa
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install Barsa in editable mode with development dependencies:
   ```powershell
   pip install -e ".[dev]"
   ```

4. Create your local environment configuration:
   ```powershell
   Copy-Item .env.example .env
   ```

---

## Running the Application

Start the FastAPI application with Uvicorn:

```powershell
uvicorn barsa.main:app --reload --host 127.0.0.1 --port 8000
```

Once running, explore:
- **Interactive OpenAPI Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Platform Info Endpoint**: [http://127.0.0.1:8000/api/v1/info](http://127.0.0.1:8000/api/v1/info)

---

## Development & Verification

### Running Tests

Execute the automated test suite using `pytest`:

```powershell
pytest
```

### Running Lint and Code Style Checks

Execute `ruff` for linting and code formatting validation:

```powershell
ruff check .
ruff format --check .
```

---

## Project Structure

```text
barsa/
├── README.md                 # Project documentation and quickstart
├── pyproject.toml            # Project metadata, dependencies, and tool configs
├── .gitignore                # Git ignore rules (secrets, venv, data)
├── .env.example              # Example environment configuration
├── docs/                     # Architectural specs, decisions, and roadmap
│   ├── architecture.md
│   ├── roadmap.md
│   └── decisions/
├── src/
│   └── barsa/
│       ├── __init__.py       # Package init and version
│       ├── main.py           # FastAPI entry point
│       ├── api/              # API routes and error handlers
│       ├── core/             # Configuration, logging, exception definitions
│       ├── models/           # Domain schemas and BMS models
│       ├── storage/          # Storage provider protocols and abstractions
│       ├── versioning/       # Versioning interfaces (commits, diffs, branches)
│       ├── graph/            # Knowledge graph interfaces
│       ├── context/          # Context engine interfaces
│       ├── agents/           # Agent coordinator interfaces
│       ├── security/         # Security and authorization primitives
│       └── integrations/     # AI clients and external tool connectors
└── tests/
    ├── conftest.py           # Test fixtures and test client setup
    └── test_health.py        # Health and Info endpoint tests
```

---

## Phase 1 Limitations

- Phase 1 delivers the foundational runtime, settings, logging, API contracts, and storage protocols.
- Concrete storage adapters (S3, Git-backed remote repositories), graph database engines (FalkorDB), and the MCP server are scheduled for subsequent phases.

---

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.
