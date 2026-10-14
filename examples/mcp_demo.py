"""BARSA Phase 6 Model Context Protocol (MCP) Demonstration Scenario.

Demonstrates cross-session continuity:
1. Session A (e.g. Planning / Architect Agent in Claude):
   - Connects to Barsa MCP Server via MCP ClientSession.
   - Discovers project and reads initial state.
   - Proposes and commits architecture decisions, tasks, and an initial resume checkpoint.
   - Disconnects after completing its turn.
2. Session B (e.g. Implementation / Coding Agent in ChatGPT / Gemini):
   - Connects independently to Barsa MCP Server.
   - Retrieves latest checkpoint and resumes context via `barsa_resume`.
   - Inspects diff and revision history.
   - Makes progress, updates task, and commits a new checkpoint.
   - Verifies complete cross-agent memory preservation and zero provider lock-in.
"""

import asyncio
import json
import tempfile
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

from barsa.bms.records import (
    CheckpointStatus,
    DecisionRecord,
    DecisionStatus,
    Project,
    ProjectStatus,
    ResumeCheckpoint,
    TaskPriority,
    TaskRecord,
    TaskStatus,
    Workspace,
)
from barsa.core.config import Settings
from barsa.graph.memory import InMemoryGraphProvider
from barsa.graph.projection import GraphProjectionWorker
from barsa.graph.retrieval import GraphRetrievalService
from barsa.mcp.server import create_mcp_server
from barsa.storage.sqlite import SQLiteStorageProvider
from barsa.versioning.engine import VersionControlEngine


async def run_mcp_demonstration() -> None:
    print("=" * 76)
    print("BARSA Model Context Protocol (MCP) — Cross-Session Collaboration Demo")
    print("=" * 76)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "barsa_mcp_demo.db"
        artifacts_dir = tmp_path / "artifacts"

        # 0. Initialize Barsa Engine Components
        settings = Settings(app_name="BARSA-MCP-Demo", app_version="0.1.0-demo")
        storage = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
        storage.initialize()
        vc = VersionControlEngine(storage)
        graph = InMemoryGraphProvider()
        worker = GraphProjectionWorker(storage, graph)
        retrieval = GraphRetrievalService(graph)

        # Create Workspace and Project
        ws = Workspace(id="ws-demo-1", name="Global AI Workspace", owner_id="barsa-user")
        storage.create_workspace(ws)
        proj = Project(
            id="proj-auth-engine",
            workspace_id=ws.id,
            name="OAuth2 Auth Engine",
            description="High-security OAuth2 microservice with PKCE support",
            status=ProjectStatus.ACTIVE,
        )
        storage.create_project(proj)
        vc.initialize_project_main_branch(proj.id, author_id="barsa-user")
        worker.process_pending_events(proj.id)

        # Create authoritative MCP Server
        mcp_server = create_mcp_server(
            settings=settings,
            storage=storage,
            vc=vc,
            worker=worker,
            retrieval=retrieval,
            graph=graph,
        )

        initial_commit = ""
        session_a_commit = ""

        # ---------------------------------------------------------------------
        # SESSION A: Architect Agent (e.g. Claude Desktop)
        # ---------------------------------------------------------------------
        print("\n" + "-" * 76)
        print(">>> SESSION A: Architecture Agent (Client: Claude) connects to MCP Server")
        print("-" * 76)

        async with (
            create_client_server_memory_streams() as (c_stream_a, s_stream_a),
            anyio.create_task_group() as tg_a,
        ):
            tg_a.start_soon(
                mcp_server._lowlevel_server.run,
                s_stream_a[0],
                s_stream_a[1],
                mcp_server._lowlevel_server.create_initialization_options(),
            )

            async with ClientSession(c_stream_a[0], c_stream_a[1]) as session_a:
                await session_a.initialize()
                print("[Session A] Connected and initialized protocol session.")

                # 1. Discover authorized projects
                proj_list_res = await session_a.call_tool("barsa_list_projects", {})
                projects_data = json.loads(proj_list_res.content[0].text)
                print(f"[Session A] Discovered {projects_data['total_count']} project(s):")
                for p in projects_data["projects"]:
                    print(f"   - ID: {p['project_id']}, Name: {p['project_name']}, Status: {p['status']}")

                # 2. Inspect project overview
                proj_res = await session_a.call_tool("barsa_get_project", {"project_id": "proj-auth-engine"})
                proj_info = json.loads(proj_res.content[0].text)
                initial_commit = proj_info["current_main_commit"]
                print(f"[Session A] Project HEAD Commit: {initial_commit}")

                # 3. Architect Agent decides on PKCE implementation and creates a task
                decision = DecisionRecord(
                    id="dec-pkce-oauth",
                    project_id="proj-auth-engine",
                    title="Adopt PKCE for OAuth2 Authorization Code Flow",
                    decision="Enforce S256 code challenge for all public and confidential clients",
                    rationale="Mitigates authorization code injection and interception attacks",
                    status=DecisionStatus.APPROVED,
                    created_by="claude-architect",
                )
                task = TaskRecord(
                    id="task-implement-pkce",
                    project_id="proj-auth-engine",
                    title="Implement S256 PKCE Code Verifier Validation",
                    description="Write cryptographic verifier checks and unit tests",
                    status=TaskStatus.IN_PROGRESS,
                    priority=TaskPriority.CRITICAL,
                    assigned_agent_id="coding-agent",
                    dependencies=[],
                )
                checkpoint_a = ResumeCheckpoint(
                    id="cp-pkce-init",
                    project_id="proj-auth-engine",
                    task_id=task.id,
                    status=CheckpointStatus.ACTIVE,
                    completed_actions=[
                        "Requirement and security RFC review completed",
                        "Decision dec-pkce-oauth approved and documented",
                    ],
                    pending_actions=[
                        "Implement S256 verifier computation module",
                        "Add RFC 7636 test vectors",
                        "Wire into token exchange route",
                    ],
                    next_action="Implement S256 verifier computation module in auth/pkce.py",
                    blockers=[],
                    decision_refs=[decision.id],
                    artifact_refs=[],
                    base_revision=initial_commit,
                    created_by="claude-architect",
                )

                # 4. Propose changes first to feature branch
                print("[Session A] Proposing changes on feature branch 'feature/pkce-spec'...")
                changes_payload = [
                    {
                        "operation": "create",
                        "record_id": decision.id,
                        "record_type": "decision",
                        "after_state": decision.model_dump(mode="json"),
                    },
                    {
                        "operation": "create",
                        "record_id": task.id,
                        "record_type": "task",
                        "after_state": task.model_dump(mode="json"),
                    },
                    {
                        "operation": "create",
                        "record_id": checkpoint_a.id,
                        "record_type": "checkpoint",
                        "after_state": checkpoint_a.model_dump(mode="json"),
                    },
                ]
                proposal_res = await session_a.call_tool(
                    "barsa_propose_changes",
                    {
                        "project_id": "proj-auth-engine",
                        "branch": "feature/pkce-spec",
                        "base_commit": initial_commit,
                        "changes": changes_payload,
                        "message": "Specify PKCE architecture, implementation task, and initial checkpoint",
                    },
                )
                proposal_data = json.loads(proposal_res.content[0].text)
                print(
                    f"[Session A] Proposal created on branch '{proposal_data['branch']}'. "
                    f"Validated BMS records: {proposal_data['change_count']}"
                )

                # 5. Commit directly to main after review/approval
                print("[Session A] Committing approved changes to 'main' branch...")
                commit_res = await session_a.call_tool(
                    "barsa_commit",
                    {
                        "project_id": "proj-auth-engine",
                        "branch": "main",
                        "expected_head": initial_commit,
                        "changes": changes_payload,
                        "message": "feat(auth): specify PKCE architecture and initial task checkpoint",
                    },
                )
                commit_data = json.loads(commit_res.content[0].text)
                session_a_commit = commit_data["commit_id"]
                print(f"[Session A] Successfully committed to main: {session_a_commit}")

                # 6. Read latest checkpoint resource
                cp_resource = await session_a.read_resource("barsa://projects/proj-auth-engine/checkpoints/latest")
                cp_res_data = json.loads(cp_resource.contents[0].text)
                print(f"[Session A] Read latest checkpoint resource: {cp_res_data['latest_checkpoint']['id']}")
                print("[Session A] Session finished. Handing off work across sessions.")

            tg_a.cancel_scope.cancel()

        # ---------------------------------------------------------------------
        # SESSION B: Coding Agent (e.g. ChatGPT / Gemini / Roo-Code)
        # ---------------------------------------------------------------------
        print("\n" + "-" * 76)
        print(">>> SESSION B: Implementation Agent (Client: ChatGPT/Gemini) connects to MCP Server")
        print("-" * 76)

        async with (
            create_client_server_memory_streams() as (c_stream_b, s_stream_b),
            anyio.create_task_group() as tg_b,
        ):
            tg_b.start_soon(
                mcp_server._lowlevel_server.run,
                s_stream_b[0],
                s_stream_b[1],
                mcp_server._lowlevel_server.create_initialization_options(),
            )

            async with ClientSession(c_stream_b[0], c_stream_b[1]) as session_b:
                await session_b.initialize()
                print("[Session B] Connected to Barsa MCP Server independently.")

                # 1. Inspect System Information Resource
                sys_res = await session_b.read_resource("barsa://system/info")
                sys_info = json.loads(sys_res.contents[0].text)
                print(f"[Session B] Connected to system: {sys_info['application']} (v{sys_info['version']})")

                # 2. Retrieve checkpoint to discover where previous agent stopped
                cp_res = await session_b.call_tool("barsa_get_checkpoint", {"project_id": "proj-auth-engine"})
                cp_data = json.loads(cp_res.content[0].text)
                print(f"[Session B] Retrieved Active Checkpoint: {cp_data['checkpoint_id']}")
                print(f"   - Target Task: {cp_data['task_id']}")
                print(f"   - Completed So Far: {cp_data['completed_actions']}")
                print(f"   - Pending Actions: {cp_data['pending_actions']}")
                print(f"   - NEXT ACTION: '{cp_data['next_action']}'")

                # 3. Call `barsa_resume` for complete context package
                print("\n[Session B] Calling barsa_resume to acquire complete context package...")
                resume_res = await session_b.call_tool(
                    "barsa_resume",
                    {"project_id": "proj-auth-engine", "task_id": "task-implement-pkce"},
                )
                resume_pkg = json.loads(resume_res.content[0].text)
                print(f"[Session B] Authoritative Revision: {resume_pkg['authoritative_revision']}")
                assert resume_pkg["authoritative_revision"] == session_a_commit
                print(f"[Session B] Verified authoritative HEAD matches Session A: {session_a_commit[:12]}...")

                # 4. Inspect Diff between initial commit and Session A's commit
                print("\n[Session B] Inspecting memory diff between initial commit and Session A commit...")
                diff_res = await session_b.call_tool(
                    "barsa_get_diff",
                    {
                        "project_id": "proj-auth-engine",
                        "from_commit": initial_commit,
                        "to_commit": session_a_commit,
                    },
                )
                diff_data = json.loads(diff_res.content[0].text)["diff"]
                print(f"[Session B] Diff Summary: {len(diff_data['added_records'])} record(s) added.")
                for rec_id in diff_data["added_records"]:
                    print(f"   + Record added: {rec_id}")

                # 5. Implementation Agent completes the action and updates task + checkpoint
                print("\n[Session B] Executing next action: 'Implement S256 verifier computation module'...")
                updated_task = TaskRecord(
                    id="task-implement-pkce",
                    project_id="proj-auth-engine",
                    title="Implement S256 PKCE Code Verifier Validation",
                    description="Write cryptographic verifier checks and unit tests",
                    status=TaskStatus.COMPLETED,
                    priority=TaskPriority.CRITICAL,
                    assigned_agent_id="coding-agent",
                    dependencies=[],
                )
                checkpoint_b = ResumeCheckpoint(
                    id="cp-pkce-done",
                    project_id="proj-auth-engine",
                    task_id="task-implement-pkce",
                    status=CheckpointStatus.ACTIVE,
                    completed_actions=[
                        "Requirement and security RFC review completed",
                        "Decision dec-pkce-oauth approved and documented",
                        "Implemented S256 verifier computation module with SHA256 base64url encoding",
                        "Validated against RFC 7636 Appendix B test vectors (all tests green)",
                    ],
                    pending_actions=[
                        "Wire into token exchange route (assigned to next sprint)",
                    ],
                    next_action="Integrate PKCE validator into /token endpoint handler",
                    blockers=[],
                    decision_refs=["dec-pkce-oauth"],
                    artifact_refs=[],
                    base_revision=session_a_commit,
                    created_by="chatgpt-coder",
                )

                # Commit progress from Session B
                commit_b_res = await session_b.call_tool(
                    "barsa_commit",
                    {
                        "project_id": "proj-auth-engine",
                        "branch": "main",
                        "expected_head": session_a_commit,
                        "changes": [
                            {
                                "operation": "update",
                                "record_id": updated_task.id,
                                "record_type": "task",
                                "after_state": updated_task.model_dump(mode="json"),
                            },
                            {
                                "operation": "create",
                                "record_id": checkpoint_b.id,
                                "record_type": "checkpoint",
                                "after_state": checkpoint_b.model_dump(mode="json"),
                            },
                        ],
                        "message": "feat(pkce): complete S256 verifier implementation and unit tests",
                    },
                )
                commit_b_data = json.loads(commit_b_res.content[0].text)
                print(f"[Session B] Successfully committed progress to main: {commit_b_data['commit_id']}")

                # 6. Read History to confirm linear DAG
                hist_res = await session_b.call_tool(
                    "barsa_get_history", {"project_id": "proj-auth-engine", "branch": "main"}
                )
                hist_data = json.loads(hist_res.content[0].text)
                print(f"\n[Session B] Complete Commit History ({hist_data['total_returned']} commits):")
                for c in hist_data["commits"]:
                    print(f"   * [{c['commit_id'][:8]}] {c['message']} (by {c['author_id']})")

                print("\n" + "=" * 76)
                print("SUCCESS: Session B retrieved Session A's memory faithfully, continued")
                print("the work without data loss or model confusion, and committed new progress!")
                print("=" * 76)

            tg_b.cancel_scope.cancel()


def main() -> None:
    asyncio.run(run_mcp_demonstration())


if __name__ == "__main__":
    main()
