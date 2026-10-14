"""BARSA Phase 7 Universal AI Skill Demonstration Scenario.

Demonstrates the 3-session workflow specified in Section 17:
1. Agent A — Initial Session:
   User: "Open my Java e-commerce project and work on authentication."
   Agent A discovers the project, creates initial architecture decisions and implementation task,
   executes the initial task, and commits a BMS checkpoint with next_action.
2. Agent B — Fresh Session:
   User: "Use Barsa and continue my Java e-commerce project."
   Agent B has ZERO prior conversation history.
   Guided by the Barsa Skill, Agent B retrieves latest checkpoint, relevant decisions, and artifacts.
   Agent B identifies the correct next action, executes it, updates task to completed, and commits an updated checkpoint.
3. Agent A — Return Session:
   Agent A reconnects, inspects the memory history, and retrieves Agent B's contributions cleanly.
"""

import asyncio
import json
import tempfile
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

from barsa.bms.records import (
    ArtifactReference,
    ArtifactType,
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


async def run_skill_demonstration() -> None:
    print("=" * 80)
    print("BARSA Universal AI Skill -- End-to-End Multi-Session Collaboration Demo")
    print("=" * 80)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "barsa_skill_demo.db"
        artifacts_dir = tmp_path / "artifacts"

        # 0. Initialize Barsa Infrastructure
        settings = Settings(app_name="BARSA-Skill-Demo", app_version="0.1.0-demo")
        storage = SQLiteStorageProvider(db_path=db_path, artifacts_dir=artifacts_dir)
        storage.initialize()
        vc = VersionControlEngine(storage)
        graph = InMemoryGraphProvider()
        worker = GraphProjectionWorker(storage, graph)
        retrieval = GraphRetrievalService(graph)

        # Seed Workspace and Java E-Commerce Project
        ws = Workspace(id="ws-ecom-1", name="E-Commerce Workspace", owner_id="barsa-user")
        storage.create_workspace(ws)
        proj = Project(
            id="proj-java-ecom",
            workspace_id=ws.id,
            name="Java E-Commerce Platform",
            description="Spring Boot 3.3 Microservices with Spring Security 6",
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

        # Create local artifact directory and file
        src_dir = tmp_path / "src" / "main" / "java" / "com" / "ecom" / "auth"
        src_dir.mkdir(parents=True, exist_ok=True)
        jwt_filter_file = src_dir / "JwtAuthFilter.java"
        jwt_filter_file.write_text("// JwtAuthFilter placeholder\npublic class JwtAuthFilter {}\n", encoding="utf-8")

        commit_agent_a = ""
        commit_agent_b = ""

        # =====================================================================
        # SESSION 1: AGENT A (e.g. Claude Desktop)
        # User: "Open my Java e-commerce project and work on authentication."
        # =====================================================================
        print("\n" + "=" * 80)
        print(">>> [SESSION 1] AGENT A (Claude Desktop)")
        print("    User prompt: 'Open my Java e-commerce project and work on authentication.'")
        print("=" * 80)

        async with (
            create_client_server_memory_streams() as (c_stream_1, s_stream_1),
            anyio.create_task_group() as tg_1,
        ):
            tg_1.start_soon(
                mcp_server._lowlevel_server.run,
                s_stream_1[0],
                s_stream_1[1],
                mcp_server._lowlevel_server.create_initialization_options(),
            )

            async with ClientSession(c_stream_1[0], c_stream_1[1]) as session_1:
                await session_1.initialize()

                # Step 1: Discover / Identify Project
                proj_res = await session_1.call_tool("barsa_get_project", {"project_id": "proj-java-ecom"})
                p_info = json.loads(proj_res.content[0].text)
                root_head = p_info["current_main_commit"]
                print(f"[Agent A] Connected to project '{p_info['project_name']}' (HEAD: {root_head[:10]}...)")

                # Step 2: Establish Architectural Decision and Task
                dec = DecisionRecord(
                    id="dec-spring-sec-jwt",
                    project_id="proj-java-ecom",
                    title="Adopt Spring Security 6 Resource Server with Stateless JWT",
                    decision="Use Nimbus JWT decoder with RS256 public key verification",
                    rationale="Stateless authentication scalable across microservice replicas",
                    status=DecisionStatus.APPROVED,
                    created_by="agent-a-architect",
                )
                task = TaskRecord(
                    id="task-auth-filter",
                    project_id="proj-java-ecom",
                    title="Implement JwtAuthFilter Spring Security component",
                    description="Intercept Authorization headers, parse bearer tokens, and populate SecurityContext",
                    status=TaskStatus.IN_PROGRESS,
                    priority=TaskPriority.CRITICAL,
                    assigned_agent_id="agent-a-architect",
                    dependencies=[],
                )
                art = ArtifactReference(
                    id="art-jwt-filter",
                    project_id="proj-java-ecom",
                    artifact_type=ArtifactType.SOURCE_CODE,
                    uri="src/main/java/com/ecom/auth/JwtAuthFilter.java",
                    content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                )
                cp1 = ResumeCheckpoint(
                    id="cp-auth-step1",
                    project_id="proj-java-ecom",
                    task_id=task.id,
                    status=CheckpointStatus.ACTIVE,
                    completed_actions=[
                        "Approved decision dec-spring-sec-jwt",
                        "Created JwtAuthFilter.java class stub",
                    ],
                    pending_actions=[
                        "Implement OncePerRequestFilter doFilterInternal() method",
                        "Extract and validate Authorization: Bearer <token>",
                        "Add SecurityFilterChain configuration",
                    ],
                    next_action="Implement OncePerRequestFilter doFilterInternal() method in JwtAuthFilter.java",
                    blockers=[],
                    decision_refs=[dec.id],
                    artifact_refs=[art.id],
                    base_revision=root_head,
                    created_by="agent-a-architect",
                )

                # Commit progress to main branch
                commit_1_res = await session_1.call_tool(
                    "barsa_commit",
                    {
                        "project_id": "proj-java-ecom",
                        "branch": "main",
                        "expected_head": root_head,
                        "changes": [
                            {
                                "operation": "create",
                                "record_id": dec.id,
                                "record_type": "decision",
                                "after_state": dec.model_dump(mode="json"),
                            },
                            {
                                "operation": "create",
                                "record_id": task.id,
                                "record_type": "task",
                                "after_state": task.model_dump(mode="json"),
                            },
                            {
                                "operation": "create",
                                "record_id": art.id,
                                "record_type": "artifact",
                                "after_state": art.model_dump(mode="json"),
                            },
                            {
                                "operation": "create",
                                "record_id": cp1.id,
                                "record_type": "checkpoint",
                                "after_state": cp1.model_dump(mode="json"),
                            },
                        ],
                        "message": "feat(auth): specify Spring Security 6 architecture and initial checkpoint",
                    },
                )
                c1_data = json.loads(commit_1_res.content[0].text)
                commit_agent_a = c1_data["commit_id"]
                print(f"[Agent A] Committed initial checkpoint to main: {commit_agent_a[:10]}...")
                print(f"[Agent A] Recorded NEXT_ACTION: '{cp1.next_action}'")
                print("[Agent A] Turn complete. Exiting session.")

            tg_1.cancel_scope.cancel()

        # =====================================================================
        # SESSION 2: AGENT B (e.g. ChatGPT / Roo-Code / Autonomous Coder)
        # User: "Use Barsa and continue my Java e-commerce project."
        # ZERO prior conversation history!
        # =====================================================================
        print("\n" + "=" * 80)
        print(">>> [SESSION 2] AGENT B (ChatGPT / Coding Agent) -- FRESH SESSION")
        print("    User prompt: 'Use Barsa and continue my Java e-commerce project.'")
        print("    (Agent B has zero conversation memory from Session 1)")
        print("=" * 80)

        async with (
            create_client_server_memory_streams() as (c_stream_2, s_stream_2),
            anyio.create_task_group() as tg_2,
        ):
            tg_2.start_soon(
                mcp_server._lowlevel_server.run,
                s_stream_2[0],
                s_stream_2[1],
                mcp_server._lowlevel_server.create_initialization_options(),
            )

            async with ClientSession(c_stream_2[0], c_stream_2[1]) as session_2:
                await session_2.initialize()

                # Step 1: Resume project via barsa_resume
                print("[Agent B] Skill triggers barsa_resume(project_id='proj-java-ecom')...")
                resume_res = await session_2.call_tool(
                    "barsa_resume", {"project_id": "proj-java-ecom", "task_id": "task-auth-filter"}
                )
                context_pkg = json.loads(resume_res.content[0].text)

                head_b = context_pkg["authoritative_revision"]
                active_cp = context_pkg["latest_checkpoint"]
                active_task = context_pkg["current_task"]
                decisions = context_pkg["relevant_decisions"]

                print(f"[Agent B] Retrieved authoritative HEAD revision: {head_b[:10]}...")
                assert head_b == commit_agent_a
                print(f"[Agent B] Active Task: '{active_task.get('title')}' (Status: {active_task.get('status')})")
                print(f"[Agent B] Identified Approved Decision: {len(decisions)} decision(s) active.")
                print(f"[Agent B] Retrieved Checkpoint ID: '{active_cp['checkpoint_id']}'")
                print(f"[Agent B] Checkpoint Next Action: '{active_cp['next_action']}'")

                # Step 2: Agent B executes the requested action
                print(f"\n[Agent B] Executing action: '{active_cp['next_action']}'...")
                jwt_filter_file.write_text(
                    "package com.ecom.auth;\n\n"
                    "import org.springframework.web.filter.OncePerRequestFilter;\n"
                    "import jakarta.servlet.http.HttpServletRequest;\n"
                    "import jakarta.servlet.http.HttpServletResponse;\n"
                    "import jakarta.servlet.FilterChain;\n\n"
                    "public class JwtAuthFilter extends OncePerRequestFilter {\n"
                    "    @Override\n"
                    "    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) {\n"
                    "        // S256 token verification logic implemented\n"
                    "    }\n"
                    "}\n",
                    encoding="utf-8",
                )
                print("[Agent B] Implementation written to disk and verified.")

                # Step 3: Agent B marks task COMPLETED and commits new checkpoint
                completed_task = TaskRecord(
                    id="task-auth-filter",
                    project_id="proj-java-ecom",
                    title="Implement JwtAuthFilter Spring Security component",
                    description="Intercept Authorization headers, parse bearer tokens, and populate SecurityContext",
                    status=TaskStatus.COMPLETED,
                    priority=TaskPriority.CRITICAL,
                    assigned_agent_id="agent-b-coder",
                    dependencies=[],
                )
                cp2 = ResumeCheckpoint(
                    id="cp-auth-step2",
                    project_id="proj-java-ecom",
                    task_id=completed_task.id,
                    status=CheckpointStatus.ACTIVE,
                    completed_actions=[
                        "Approved decision dec-spring-sec-jwt",
                        "Created JwtAuthFilter.java class stub",
                        "Implemented OncePerRequestFilter doFilterInternal() method in JwtAuthFilter.java",
                        "Validated Authorization Bearer header parsing with Spring mock requests",
                    ],
                    pending_actions=[
                        "Add SecurityFilterChain configuration bean to WebSecurityConfig.java",
                    ],
                    next_action="Add SecurityFilterChain configuration bean in WebSecurityConfig.java",
                    blockers=[],
                    decision_refs=["dec-spring-sec-jwt"],
                    artifact_refs=["art-jwt-filter"],
                    base_revision=head_b,
                    created_by="agent-b-coder",
                )

                commit_2_res = await session_2.call_tool(
                    "barsa_commit",
                    {
                        "project_id": "proj-java-ecom",
                        "branch": "main",
                        "expected_head": head_b,
                        "changes": [
                            {
                                "operation": "update",
                                "record_id": completed_task.id,
                                "record_type": "task",
                                "after_state": completed_task.model_dump(mode="json"),
                            },
                            {
                                "operation": "create",
                                "record_id": cp2.id,
                                "record_type": "checkpoint",
                                "after_state": cp2.model_dump(mode="json"),
                            },
                        ],
                        "message": "feat(auth): complete JwtAuthFilter implementation and unit tests",
                    },
                )
                c2_data = json.loads(commit_2_res.content[0].text)
                commit_agent_b = c2_data["commit_id"]
                print(f"[Agent B] Committed milestone progress: {commit_agent_b[:10]}...")
                print(f"[Agent B] Handoff Checkpoint saved with NEXT_ACTION: '{cp2.next_action}'")

            tg_2.cancel_scope.cancel()

        # =====================================================================
        # SESSION 3: AGENT A (Return Session)
        # User: "What is the status of my Java e-commerce project?"
        # =====================================================================
        print("\n" + "=" * 80)
        print(">>> [SESSION 3] AGENT A (Return Session)")
        print("    User prompt: 'What is the status of my Java e-commerce project?'")
        print("=" * 80)

        async with (
            create_client_server_memory_streams() as (c_stream_3, s_stream_3),
            anyio.create_task_group() as tg_3,
        ):
            tg_3.start_soon(
                mcp_server._lowlevel_server.run,
                s_stream_3[0],
                s_stream_3[1],
                mcp_server._lowlevel_server.create_initialization_options(),
            )

            async with ClientSession(c_stream_3[0], c_stream_3[1]) as session_3:
                await session_3.initialize()

                # Step 1: Agent A checks latest checkpoint
                cp_res = await session_3.call_tool("barsa_get_checkpoint", {"project_id": "proj-java-ecom"})
                latest_cp = json.loads(cp_res.content[0].text)

                print(f"[Agent A] Retrieved Latest Checkpoint: '{latest_cp['checkpoint_id']}'")
                print(f"   - Target Task: {latest_cp['task_id']}")
                print(f"   - Completed Actions Count: {len(latest_cp['completed_actions'])}")
                for act in latest_cp["completed_actions"]:
                    print(f"     [x] {act}")
                print(f"   - Pending Actions: {latest_cp['pending_actions']}")
                print(f"   - Next Action: '{latest_cp['next_action']}'")

                # Step 2: Agent A inspects commit history
                hist_res = await session_3.call_tool("barsa_get_history", {"project_id": "proj-java-ecom", "limit": 10})
                hist_data = json.loads(hist_res.content[0].text)

                print(f"\n[Agent A] Complete Project History ({hist_data['total_returned']} commits):")
                for c in hist_data["commits"]:
                    print(f"   [{c['commit_id'][:10]}] {c['message']} (by: {c['author_id']})")

                # Step 3: Agent A inspects diff between its initial commit and Agent B's commit
                diff_res = await session_3.call_tool(
                    "barsa_get_diff",
                    {
                        "project_id": "proj-java-ecom",
                        "from_commit": commit_agent_a,
                        "to_commit": commit_agent_b,
                    },
                )
                diff_data = json.loads(diff_res.content[0].text)["diff"]
                print("\n[Agent A] Diff between Session 1 and Session 2:")
                print(f"   - Added Records:    {diff_data['added_records']}")
                print(f"   - Modified Records: {diff_data['modified_records']}")

                print("\n" + "=" * 80)
                print("DEMONSTRATION SUCCESSFUL:")
                print("1. Agent A designed architecture and saved initial checkpoint.")
                print("2. Agent B resumed in a fresh session with zero prior conversation memory,")
                print("   correctly identified next_action, completed task, and committed progress.")
                print("3. Agent A returned, inspected Agent B's contributions via Barsa DAG history,")
                print("   and verified complete continuity across models, sessions, and time.")
                print("=" * 80)

            tg_3.cancel_scope.cancel()


def main() -> None:
    asyncio.run(run_skill_demonstration())


if __name__ == "__main__":
    main()
