# Barsa Worked Examples & Scenarios

Concrete walkthroughs showing how different AI agents interact with Barsa MCP tools in real-world scenarios.

---

## Scenario: Architecture-to-Implementation Handoff

### Session 1: Architect Agent (e.g. Claude 3.7 Sonnet)

1. **User Request:**
   > *"I need an auth engine for our e-commerce platform. Design it and create the initial task."*

2. **Agent Discovers Project:**
   ```json
   // Call: barsa_get_project(project_id="proj-ecom-auth")
   // Response:
   {
     "project_id": "proj-ecom-auth",
     "project_name": "E-Commerce Auth Engine",
     "current_main_commit": "7a8b9c..."
   }
   ```

3. **Agent Designs and Saves Records via MCP:**
   The agent formulates a Decision, a Task, and an initial Checkpoint:
   ```json
   // Call: barsa_commit(
   //   project_id="proj-ecom-auth",
   //   branch="main",
   //   expected_head="7a8b9c...",
   //   changes=[
   //     {
   //       "operation": "create",
   //       "record_id": "dec-jwt-auth",
   //       "record_type": "decision",
   //       "after_state": {
   //         "id": "dec-jwt-auth",
   //         "project_id": "proj-ecom-auth",
   //         "record_type": "decision",
   //         "title": "Use RS256 JWT with Asymmetric Key Pairs",
   //         "decision": "Issue short-lived RS256 JWT access tokens with Redis refresh token rotation.",
   //         "rationale": "Enables stateless microservice token verification while permitting fast revocation.",
   //         "status": "approved",
   //         "created_by": "claude-architect",
   //         "created_at": "2026-10-14T15:00:00Z"
   //       }
   //     },
   //     {
   //       "operation": "create",
   //       "record_id": "task-impl-jwt",
   //       "record_type": "task",
   //       "after_state": {
   //         "id": "task-impl-jwt",
   //         "project_id": "proj-ecom-auth",
   //         "record_type": "task",
   //         "title": "Implement RS256 Token Issuer & Key Generator",
   //         "status": "in_progress",
   //         "priority": "critical",
   //         "assigned_agent_id": "coding-agent",
   //         "dependencies": [],
   //         "created_at": "2026-10-14T15:05:00Z"
   //       }
   //     },
   //     {
   //       "operation": "create",
   //       "record_id": "cp-auth-init",
   //       "record_type": "checkpoint",
   //       "after_state": {
   //         "id": "cp-auth-init",
   //         "project_id": "proj-ecom-auth",
   //         "record_type": "checkpoint",
   //         "task_id": "task-impl-jwt",
   //         "status": "active",
   //         "completed_actions": ["Architecture design approved", "Decision dec-jwt-auth documented"],
   //         "pending_actions": ["Write JWT issuer module", "Add RSA key generation utility"],
   //         "next_action": "Implement RSA key generator utility in src/auth/keys.py",
   //         "decision_refs": ["dec-jwt-auth"],
   //         "base_revision": "7a8b9c...",
   //         "created_by": "claude-architect",
   //         "created_at": "2026-10-14T15:10:00Z"
   //       }
   //     }
   //   ],
   //   message="feat(auth): specify RS256 JWT architecture and initial checkpoint"
   // )
   // Response: {"commit_id": "b1c2d3...", "status": "COMMITTED"}
   ```

4. **Agent Concludes Session:**
   > *"I have documented the architecture in decision `dec-jwt-auth` and saved checkpoint `cp-auth-init`. The next agent can resume from commit `b1c2d3...` with next action: 'Implement RSA key generator utility in src/auth/keys.py'."*

---

### Session 2: Implementation Agent (e.g. ChatGPT / Roo-Code)

1. **User Request in a completely fresh window:**
   > *"Continue my e-commerce auth project using Barsa."*

2. **Agent Resumes Context:**
   ```json
   // Call: barsa_resume(project_id="proj-ecom-auth")
   // Response:
   {
     "project_identity": {"project_id": "proj-ecom-auth", "status": "active"},
     "authoritative_revision": "b1c2d3...",
     "current_task": {"id": "task-impl-jwt", "title": "Implement RS256 Token Issuer & Key Generator"},
     "latest_checkpoint": {
       "checkpoint_id": "cp-auth-init",
       "next_action": "Implement RSA key generator utility in src/auth/keys.py",
       "completed_actions": ["Architecture design approved", "Decision dec-jwt-auth documented"],
       "pending_actions": ["Write JWT issuer module", "Add RSA key generation utility"]
     },
     "relevant_decisions": [
       {"id": "dec-jwt-auth", "decision": "Issue short-lived RS256 JWT access tokens..."}
     ]
   }
   ```

3. **Agent Executes and Updates Progress:**
   The agent writes `src/auth/keys.py`, runs tests, and commits the updated progress:
   ```json
   // Call: barsa_commit(
   //   project_id="proj-ecom-auth",
   //   branch="main",
   //   expected_head="b1c2d3...",
   //   changes=[
   //     {
   //       "operation": "update",
   //       "record_id": "task-impl-jwt",
   //       "record_type": "task",
   //       "after_state": { "status": "completed", ... }
   //     },
   //     {
   //       "operation": "create",
   //       "record_id": "cp-auth-done",
   //       "record_type": "checkpoint",
   //       "after_state": {
   //         "task_id": "task-impl-jwt",
   //         "status": "active",
   //         "completed_actions": [..., "Implemented RSA key generator utility", "All unit tests passing"],
   //         "pending_actions": ["Wire into FastAPI route"],
   //         "next_action": "Create FastAPI route in src/api/routes.py",
   //         "base_revision": "b1c2d3..."
   //       }
   //     }
   //   ],
   //   message="feat(keys): complete RSA key generation utility and tests"
   // )
   // Response: {"commit_id": "c3d4e5...", "status": "COMMITTED"}
   ```

4. **Agent Briefs User:**
   > *"I resumed from commit `b1c2d3...`, implemented the RSA key generation module as instructed by the checkpoint, verified all tests pass, and committed progress to commit `c3d4e5...`. The next action is to create the FastAPI route."*
