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
        branch = project_cfg.get("branch")

        # Get last run
        run_info = self._get_last_run(repo, workflow, branch)
        if not run_info:
            return ScriptResult(
                success=False,
                message="No workflow runs found",
                errors=[f"No runs found for {workflow} in {repo}"]
            )

        # Display status
        self._display_status(project, repo, workflow, run_info)

        # Show failed jobs if workflow failed
        conclusion = run_info.get("conclusion", "")
        if conclusion == "failure":
            self._show_failed_jobs(repo, run_info["id"])

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

    def _get_last_run(self, repo: str, workflow: str, branch: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the last workflow run."""
        cmd = [
            "gh", "run", "list",
            "-R", repo,
            "-w", workflow,
            "--limit", "1",
            "--json", "databaseId,status,conclusion,createdAt,updatedAt,headBranch,event,name"
        ]
        if branch:
            cmd.extend(["--branch", branch])

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

    def _show_failed_jobs(self, repo: str, run_id: str) -> None:
        """Show failed jobs for a workflow run."""
        cmd = [
            "gh", "run", "view", run_id,
            "-R", repo,
            "--json", "jobs"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                jobs = data.get("jobs", [])
                failed_jobs = [j for j in jobs if j.get("conclusion") == "failure"]

                if failed_jobs:
                    self.console.print()
                    self.console.print("[bold red]Failed Jobs:[/bold red]")
                    for job in failed_jobs:
                        job_name = job.get("name", "Unknown")
                        job_id = job.get("databaseId", "")
                        self.console.print(f"  [red]✗[/red] {job_name}")

                        # Show failed steps
                        steps = job.get("steps", [])
                        failed_steps = [s for s in steps if s.get("conclusion") == "failure"]
                        for step in failed_steps:
                            step_name = step.get("name", "Unknown")
                            self.console.print(f"      [dim]→ {step_name}[/dim]")

                        # Fetch and show error message from logs
                        if job_id:
                            self._show_error_from_logs(repo, str(job_id))
        except Exception as e:
            self.console.print(f"[red]Error fetching job details: {e}[/red]")

    def _show_error_from_logs(self, repo: str, job_id: str) -> None:
        """Extract and show error message from job logs."""
        cmd = [
            "gh", "api",
            f"repos/{repo}/actions/jobs/{job_id}/logs"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                logs = result.stdout
                error_msg = self._extract_error_message(logs)
                if error_msg:
                    self.console.print()
                    self.console.print("[bold yellow]Error Details:[/bold yellow]")
                    self.console.print(f"[red]{error_msg}[/red]")
            elif result.stderr:
                # Try alternative: gh run view with --log-failed
                self._show_error_from_run_log(repo, job_id)
        except Exception:
            # Try alternative method
            self._show_error_from_run_log(repo, job_id)

    def _show_error_from_run_log(self, repo: str, job_id: str) -> None:
        """Alternative method to get error from failed run logs."""
        cmd = [
            "gh", "run", "view",
            "--repo", repo,
            "--job", job_id,
            "--log-failed"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                logs = result.stdout
                error_msg = self._extract_error_message(logs)
                if error_msg:
                    self.console.print()
                    self.console.print("[bold yellow]Error Details:[/bold yellow]")
                    self.console.print(f"[red]{error_msg}[/red]")
        except Exception:
            pass

    def _extract_error_message(self, logs: str) -> str:
        """Extract meaningful error message from logs."""
        import re

        lines = logs.split('\n')
        error_lines = []
        capture = False
        capture_count = 0
        script_error = None

        for line in lines:
            # Remove job/step prefix from --log-failed format (e.g., "job_name\tSTEP_NAME\t...")
            clean_line = re.sub(r'^[^\t]+\t[^\t]+\t', '', line)
            # Remove timestamp prefix
            clean_line = re.sub(r'^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*', '', clean_line)
            # Remove ANSI codes
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', clean_line)
            # Remove ##[error] prefix
            clean_line = re.sub(r'^##\[error\]\s*', '', clean_line)

            # Capture script error messages (e.g., "Script phpstan ... returned with error code 1")
            if 'returned with error code' in clean_line and not script_error:
                script_error = clean_line.strip()

            # Look for failure indicators
            if any(pattern in clean_line for pattern in [
                'FAILURES!', 'There was 1 failure:', 'There were',
                'Fail ', 'FAILED', 'Error:', 'Exception:',
                'PHPStan found', 'error(s)', 'fatal error',
                '[ERROR]', 'Fatal error', 'Parse error'
            ]):
                capture = True
                capture_count = 0

            if capture:
                # Skip empty lines at start
                if not error_lines and not clean_line.strip():
                    continue
                error_lines.append(clean_line)
                capture_count += 1
                # Capture up to 15 lines of context
                if capture_count >= 15:
                    break

        if error_lines:
            return '\n'.join(error_lines).strip()

        # Fall back to script error if no detailed error found
        if script_error:
            return script_error

        return ""

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
