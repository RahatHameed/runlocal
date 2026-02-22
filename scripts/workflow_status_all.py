"""GitHub Actions workflow status all script - check status of all projects."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml
from rich.console import Console
from rich.table import Table

from scripts.base import BaseScript, ScriptConfig, ScriptResult


class WorkflowStatusAllScript(BaseScript):
    """Script to check the status of all configured projects."""

    config = ScriptConfig(
        name="workflow-status-all",
        description="Check status of all configured projects",
        version="1.0.0"
    )

    def __init__(self):
        self.console = Console()
        self.projects_config: Dict[str, Any] = {}

    def run(self, verbose: bool = False, **kwargs) -> ScriptResult:
        """
        Check status of all projects in parallel.

        Args:
            verbose: If True, show additional details

        Returns:
            ScriptResult with all project statuses
        """
        # Load projects configuration
        if not self._load_projects_config():
            return ScriptResult(
                success=False,
                message="Failed to load projects.yaml",
                errors=["projects.yaml not found or invalid"]
            )

        projects = self.projects_config.get("projects", {})
        if not projects:
            return ScriptResult(
                success=False,
                message="No projects configured",
                errors=["Add projects to projects.yaml"]
            )

        # Fetch status for all projects in parallel
        results = self._fetch_all_statuses(projects)

        # Display results
        self._display_status_table(results)

        # Determine overall success
        all_success = all(
            r.get("conclusion") == "success" or r.get("status") == "in_progress"
            for r in results.values() if r
        )

        return ScriptResult(
            success=all_success,
            message=f"Checked {len(results)} projects",
            data={"results": results}
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

    def _fetch_all_statuses(self, projects: Dict[str, Any]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Fetch status for all projects in parallel."""
        results = {}

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self._get_project_status, name, cfg): name
                for name, cfg in projects.items()
            }

            for future in as_completed(futures):
                project_name = futures[future]
                try:
                    results[project_name] = future.result()
                except Exception as e:
                    results[project_name] = {"error": str(e)}

        return results

    def _get_project_status(self, project_name: str, project_cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get status for a single project."""
        repo = project_cfg.get("repo")
        workflow = project_cfg.get("workflow", "workflow.yaml")
        branch = project_cfg.get("branch", "main")

        # Try both extensions
        for ext in ['.yml', '.yaml']:
            base_name = workflow.removesuffix('.yml').removesuffix('.yaml')
            test_workflow = base_name + ext

            run_info = self._get_last_run(repo, test_workflow, branch)
            if run_info:
                run_info["workflow"] = test_workflow
                return run_info

        return None

    def _get_last_run(self, repo: str, workflow: str, branch: str) -> Optional[Dict[str, Any]]:
        """Get the last workflow run for a specific branch."""
        cmd = [
            "gh", "run", "list",
            "-R", repo,
            "-w", workflow,
            "-b", branch,
            "--limit", "1",
            "--json", "databaseId,status,conclusion,createdAt,headBranch,event"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                runs = json.loads(result.stdout)
                if runs:
                    run = runs[0]
                    run["id"] = str(run["databaseId"])
                    run["repo"] = repo
                    return run
        except Exception:
            pass

        return None

    def _format_relative_time(self, timestamp: str) -> str:
        """Format timestamp as relative time."""
        try:
            created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = now - created

            if delta.total_seconds() < 60:
                return "just now"
            elif delta.total_seconds() < 3600:
                mins = int(delta.total_seconds() / 60)
                return f"{mins}m ago"
            elif delta.total_seconds() < 86400:
                hours = int(delta.total_seconds() / 3600)
                return f"{hours}h ago"
            else:
                days = int(delta.total_seconds() / 86400)
                return f"{days}d ago"
        except Exception:
            return timestamp[:10] if timestamp else "unknown"

    def _display_status_table(self, results: Dict[str, Optional[Dict[str, Any]]]) -> None:
        """Display status table for all projects."""
        table = Table(title="Workflow Status: All Projects")
        table.add_column("Project", style="cyan")
        table.add_column("Status")
        table.add_column("Branch")
        table.add_column("Last Run")

        for project_name, run_info in sorted(results.items()):
            if not run_info or "error" in run_info:
                error_msg = run_info.get("error", "No runs found") if run_info else "No runs found"
                table.add_row(
                    project_name,
                    "[dim]N/A[/dim]",
                    "-",
                    f"[red]{error_msg}[/red]"
                )
                continue

            status = run_info.get("status", "unknown")
            conclusion = run_info.get("conclusion", "")
            branch = run_info.get("headBranch", "")
            created = run_info.get("createdAt", "")

            # Format status
            if conclusion == "success":
                status_text = "[green]SUCCESS[/green]"
            elif conclusion == "failure":
                status_text = "[red]FAILURE[/red]"
            elif conclusion == "cancelled":
                status_text = "[yellow]CANCELLED[/yellow]"
            elif status == "in_progress":
                status_text = "[cyan]RUNNING[/cyan]"
            elif status == "queued":
                status_text = "[blue]QUEUED[/blue]"
            else:
                status_text = f"[white]{(conclusion or status).upper()}[/white]"

            relative_time = self._format_relative_time(created)

            table.add_row(project_name, status_text, branch, relative_time)

        self.console.print()
        self.console.print(table)
