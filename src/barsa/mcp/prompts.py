"""Standard MCP prompt definitions for Barsa."""

from mcp.server.mcpserver import MCPServer


def register_prompts(server: MCPServer) -> None:
    """Register reusable helper prompts on the server instance."""

    @server.prompt("barsa_resume_project")
    def resume_project_prompt(project_id: str, task_id: str = "") -> str:
        """Prompt guiding the AI agent to resume active work on a project or task."""
        target = f" on task '{task_id}'" if task_id else ""
        return (
            f"You are continuing work on project '{project_id}'{target}.\n"
            f"First, call the 'barsa_resume' tool with project_id='{project_id}'"
            + (f" and task_id='{task_id}'" if task_id else "")
            + " to retrieve current state, checkpoint actions, decisions, and blockers.\n"
            "Review the latest checkpoint's 'next_action' and verify that any required dependencies are met before making changes."
        )

    @server.prompt("barsa_save_checkpoint")
    def save_checkpoint_prompt(project_id: str, task_id: str, summary: str) -> str:
        """Prompt guiding the AI agent to persist a structured checkpoint."""
        return (
            f"You have made progress on task '{task_id}' in project '{project_id}'.\n"
            f"Prepare to save a checkpoint with summary: '{summary}'.\n"
            "Ensure you structure:\n"
            "1. completed_actions: list of concrete steps finished.\n"
            "2. pending_actions: remaining items to complete.\n"
            "3. next_action: immediate next step for the next agent or session.\n"
            "4. blockers: any unresolved issues preventing progress.\n"
            "Then commit the checkpoint using 'barsa_commit'."
        )

    @server.prompt("barsa_review_changes")
    def review_changes_prompt(project_id: str, from_commit: str, to_commit: str) -> str:
        """Prompt guiding the AI agent to inspect and review memory diffs."""
        return (
            f"Please review memory changes in project '{project_id}' between commits '{from_commit}' and '{to_commit}'.\n"
            f"1. Call 'barsa_get_diff' with from_commit='{from_commit}' and to_commit='{to_commit}'.\n"
            "2. Inspect modified records for architectural alignment, schema compliance, and potential merge conflicts.\n"
            "3. Confirm if any superseded decisions or unresolved dependencies exist."
        )
