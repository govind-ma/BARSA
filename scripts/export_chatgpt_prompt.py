"""Export the exact token-optimized BARSA handover prompt for ChatGPT Desktop."""

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from barsa.core.config import get_settings
from barsa.graph.factory import get_graph_provider
from barsa.graph.projection import GraphProjectionWorker
from barsa.graph.retrieval import GraphRetrievalService
from barsa.mcp.tools import graph_resume_tool, resume_tool
from barsa.storage.factory import get_storage_provider
from barsa.versioning.engine import VersionControlEngine

PROJECT_ID = "proj-nexus"

def generate_chatgpt_prompt():
    settings = get_settings()
    storage = get_storage_provider(settings)
    graph = get_graph_provider(settings)
    vc = VersionControlEngine(storage)
    worker = GraphProjectionWorker(storage, graph)
    retrieval = GraphRetrievalService(graph)

    # 1. FalkorDB Graph Resume
    gr = graph_resume_tool(storage, retrieval, worker, PROJECT_ID)
    rec_task = gr.get("recommended_task", {})

    # 2. Storage Resume Package
    r = resume_tool(storage, retrieval, worker, vc, PROJECT_ID)
    cp = r.get("latest_checkpoint", {})
    proj = r.get("project_identity", {})
    decisions = r.get("relevant_decisions", [])

    prompt = f"""Connect to my BARSA memory and locate Project NEXUS.
I was developing this project with Claude, but that session is now unavailable.
You do not have access to Claude's conversation.
Use BARSA's memory standard to authenticate, retrieve the latest approved checkpoint, inspect relevant decisions and task dependencies, and identify the exact next unfinished development task.

================================================================================
BARSA VERIFIED MEMORY PACKAGE (v0.1)
================================================================================
Project: {proj.get('name', 'Project NEXUS')} ({PROJECT_ID})
Authoritative Revision: {r.get('authoritative_revision')}

[LATEST APPROVED CHECKPOINT: {cp.get('checkpoint_id', 'CP-NX-002')}]
- Task: {cp.get('task_id', 'TASK-NX-003')} (FastAPI Incident Ingestion & Service Dependency Endpoints)
- Status: Completed by claude-backend
- Completed Actions: {cp.get('completed_actions', [])}
- Next Action: {cp.get('next_action')}

[FALKORDB GRAPH REASONING & TASK DISCOVERY]
- Next Eligible Task: {rec_task.get('task_id')} — {rec_task.get('title')}
- Priority: {rec_task.get('priority')}
- Reason: {rec_task.get('readiness_reason')}
- Upstream Satisfied Dependencies: {rec_task.get('completed_dependencies')}

[ACTIVE ARCHITECTURAL DECISIONS (ADRs)]
- ADR-NX-001: FalkorDB Graph Traversal for Downstream Cascade Analysis (Multi-hop DEPENDS_ON Cypher)
- ADR-NX-002: Dynamic Severity Derivation from Dependency Criticality (Tier-0 / Tier-1 blast radius)

================================================================================
YOUR INSTRUCTION:
Continue implementing {rec_task.get('task_id')} ({rec_task.get('title')}).
Design the Dynamic Severity & Recovery Priority Calculation Engine.
Ensure downstream blast radius rules from ADR-NX-002 are strictly honored.
Save the verified progress back to BARSA as Checkpoint CP-NX-003.
"""
    print(prompt)
    with open(ROOT_DIR / "CHATGPT_DESKTOP_PROMPT.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    print("\n[SUCCESS] Saved exact prompt to CHATGPT_DESKTOP_PROMPT.txt!")

if __name__ == "__main__":
    generate_chatgpt_prompt()
