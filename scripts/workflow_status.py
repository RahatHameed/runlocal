"""GitHub Actions workflow status script - check status of last workflow run."""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

import yaml
from rich.console import Console
from rich.table import Table

from scripts.base import BaseScript, ScriptConfig, ScriptResult


class WorkflowStatusScript(BaseScript):
    """Script to check the status of the last workflow run."""

    config = ScriptConfig(
        name="workflow-status",
        description="Check status of last workflow run",
        version="1.0.0"
    )

    def __init__(self):
        self.console = Console()
        self.projects_config: Dict[str, Any] = {}

    def run(self, verbose: bool = False, **kwargs) -> ScriptResult:
        """
        Check status of the last workflow run.

        Args:
            verbose: If True, show workflow logs
            project: Project name from projects.yaml
            workflow: Override workflow file (optional)

        Returns:
            ScriptResult with workflow status
        """
        project = kwargs.get("project")
        workflow_override = kwargs.get("workflow")

        # Load projects configuration
        if not self._load_projects_config():
            return ScriptResult(
                success=False,
                message="Failed to load projects.yaml",
                errors=["projects.yaml not found or invalid"]
            )

        # Get project configuration
        if project not in self.projects_config.get("projects", {}):
            available = list(self.projects_config.get("projects", {}).keys())
            return ScriptResult(
                success=False,
                message=f"Project '{project}' not found",
                errors=[f"Available projects: {', '.join(available)}"]
            )

        project_cfg = self.projects_config["projects"][project]
        repo = project_cfg["repo"]
        workflow = workflow_override or project_cfg.get("workflow", "workflow.yaml")

        # Get last run
        run_info = self._get_last_run(repo, workflow)
        if not run_info:
            return ScriptResult(
                success=False,
                message="No workflow runs found",
                errors=[f"No runs found for {workflow} in {repo}"]
            )

        # Display status
        self._display_status(project, repo, workflow, run_info)

        # Show logs if verbose
        if verbose:
            self._show_logs(repo, run_info["id"])

        conclusion = run_info.get("conclusion", "")
        status = run_info.get("status", "")

        return ScriptResult(
            success=(conclusion == "success" or status == "in_progress"),
            message=f"Status: {conclusion or status}",
            data=run_info
        )

    def _load_projects_config(self) -> bool:
        """Load projects configuration from yaml file."""
        config_paths = [
            Path("projects.yaml"),
            Path("/app/projects.yaml"),
            Path.home() / ".config" / "agents" / "projects.yaml"
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        self.projects_config = yaml.safe_load(f)
                    return True
                except Exception:
                    return False

        return False

    def _get_last_run(self, repo: str, workflow: str) -> Optional[Dict[str, Any]]:
        """Get the last workflow run."""
        cmd = [
            "gh", "run", "list",
            "-R", repo,
            "-w", workflow,
            "--limit", "1",
            "--json", "databaseId,status,conclusion,createdAt,updatedAt,headBranch,event,name"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                runs = json.loads(result.stdout)
                if runs:
                    run = runs[0]
                    run["id"] = str(run["databaseId"])
                    run["url"] = f"https://github.com/{repo}/actions/runs/{run['id']}"
                    return run
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

        return None

    def _display_status(self, project: str, repo: str, workflow: str, run_info: Dict[str, Any]) -> None:
        """Display the workflow status."""
        status = run_info.get("status", "unknown")
        conclusion = run_info.get("conclusion", "")

        # Determine style
        if conclusion == "success":
            style = "green"
            status_text = "SUCCESS"
        elif conclusion == "failure":
            style = "red"
            status_text = "FAILURE"
        elif conclusion == "cancelled":
            style = "yellow"
            status_text = "CANCELLED"
        elif status == "in_progress":
            style = "cyan"
            status_text = "IN PROGRESS"
        elif status == "queued":
            style = "blue"
            status_text = "QUEUED"
        else:
            style = "white"
            status_text = (conclusion or status).upper()

        table = Table(title=f"Workflow Status: {project}", style=style)
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Status", f"[bold {style}]{status_text}[/bold {style}]")
        table.add_row("Repository", repo)
        table.add_row("Workflow", workflow)
        table.add_row("Run ID", run_info.get("id", ""))
        table.add_row("Branch", run_info.get("headBranch", ""))
        table.add_row("Event", run_info.get("event", ""))
        table.add_row("Created", run_info.get("createdAt", ""))
        table.add_row("URL", run_info.get("url", ""))

        self.console.print(table)

    def _show_logs(self, repo: str, run_id: str) -> None:
        """Show workflow logs."""
        self.console.print()
        self.console.print("[cyan]Fetching logs...[/cyan]")

        cmd = ["gh", "run", "view", run_id, "-R", repo, "--log"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout:
                logs = result.stdout
                if len(logs) > 15000:
                    logs = logs[:15000] + "\n\n... (truncated)"
                self.console.print(logs)
        except Exception as e:
            self.console.print(f"[red]Error fetching logs: {e}[/red]")
