"""GitHub Actions workflow dispatch script - triggers and monitors workflows."""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from scripts.base import BaseScript, ScriptConfig, ScriptResult


class WorkflowDispatchScript(BaseScript):
    """Script to trigger GitHub Actions workflows and monitor their status."""

    config = ScriptConfig(
        name="workflow-dispatch",
        description="Trigger GitHub Actions workflows and monitor status",
        version="1.0.0"
    )

    # Default settings (can be overridden by config.yaml)
    DEFAULT_POLL_INTERVAL = 30
    DEFAULT_TIMEOUT = 3600
    DEFAULT_SHOW_PROGRESS = True

    def __init__(self):
        self.console = Console()
        self.projects_config: Dict[str, Any] = {}
        self.script_config: Dict[str, Any] = {}
        self._load_script_config()

    def _load_script_config(self) -> None:
        """Load script configuration from config.yaml."""
        config_paths = [
            Path("config.yaml"),
            Path("/app/config.yaml"),
            Path.home() / ".config" / "agents" / "config.yaml"
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        self.script_config = yaml.safe_load(f) or {}
                    return
                except Exception:
                    pass

    def _get_poll_interval(self) -> int:
        """Get poll interval from config."""
        return self.script_config.get("workflow", {}).get(
            "poll_interval", self.DEFAULT_POLL_INTERVAL
        )

    def _get_timeout(self) -> int:
        """Get timeout from config."""
        return self.script_config.get("workflow", {}).get(
            "timeout", self.DEFAULT_TIMEOUT
        )

    def _get_show_progress(self) -> bool:
        """Get show_progress setting from config."""
        return self.script_config.get("workflow", {}).get(
            "show_progress", self.DEFAULT_SHOW_PROGRESS
        )

    def run(self, verbose: bool = False, **kwargs) -> ScriptResult:
        """
        Trigger a workflow and wait for completion.

        Args:
            verbose: If True, show full workflow logs
            project: Project name from projects.yaml
            workflow: Override workflow file (optional)
            branch: Override branch (optional)
            params: Additional parameters as key=value pairs
            wait: Wait for workflow completion (default: True)

        Returns:
            ScriptResult with workflow run details
        """
        project = kwargs.get("project")
        workflow_override = kwargs.get("workflow")
        branch_override = kwargs.get("branch")
        params = kwargs.get("params", [])
        wait = kwargs.get("wait", True)

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
        branch = branch_override or project_cfg.get("branch", "main")
        defaults = project_cfg.get("defaults", {})

        # Merge default params with overrides
        final_params = dict(defaults)
        for param in params:
            if "=" in param:
                key, value = param.split("=", 1)
                final_params[key] = value

        # Check gh CLI authentication
        if not self._check_gh_auth():
            return ScriptResult(
                success=False,
                message="GitHub CLI not authenticated",
                errors=["Run 'gh auth login' to authenticate"]
            )

        # Trigger the workflow (silent)
        run_id = self._trigger_workflow(repo, workflow, branch, final_params)
        if not run_id:
            return ScriptResult(
                success=False,
                message="Failed to trigger workflow",
                errors=["Check gh CLI output for details"]
            )

        if not wait:
            # Show immediate result for --no-wait
            self._display_triggered(project, repo, workflow, branch, final_params, run_id)
            return ScriptResult(
                success=True,
                message="Workflow triggered (not waiting for completion)",
                data={"run_id": run_id, "repo": repo, "workflow": workflow}
            )

        # Wait for completion silently, then show final result
        final_status = self._wait_for_completion(repo, run_id, verbose)

        # Display final result
        self._display_final_result(
            project, repo, workflow, branch, final_params,
            run_id, final_status, verbose
        )

        return final_status

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

    def _check_gh_auth(self) -> bool:
        """Check if gh CLI is authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _trigger_workflow(self, repo: str, workflow: str, branch: str,
                          params: Dict[str, str]) -> Optional[str]:
        """Trigger the workflow and return the run ID."""
        cmd = ["gh", "workflow", "run", workflow, "-R", repo, "--ref", branch]

        for key, value in params.items():
            cmd.extend(["-f", f"{key}={value}"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.console.print(f"[red]gh error: {result.stderr.strip()}[/red]")
                return None

            # Wait for the run to be created
            time.sleep(3)

            # Get the most recent run ID
            return self._get_latest_run_id(repo, workflow)

        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            return None

    def _get_latest_run_id(self, repo: str, workflow: str) -> Optional[str]:
        """Get the most recent workflow run ID."""
        cmd = [
            "gh", "run", "list",
            "-R", repo,
            "-w", workflow,
            "--limit", "1",
            "--json", "databaseId"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                runs = json.loads(result.stdout)
                if runs:
                    return str(runs[0]["databaseId"])
        except Exception:
            pass

        return None

    def _wait_for_completion(self, repo: str, run_id: str, verbose: bool) -> ScriptResult:
        """Wait for the workflow to complete silently."""
        start_time = time.time()
        poll_interval = self._get_poll_interval()
        timeout = self._get_timeout()
        show_progress = self._get_show_progress()

        # Show minimal progress indicator
        if show_progress:
            self.console.print(f"[dim]Waiting for workflow {run_id} to complete (polling every {poll_interval}s)...[/dim]")

        while True:
            status_info = self._get_run_status(repo, run_id)

            if not status_info:
                return ScriptResult(
                    success=False,
                    message="Failed to get workflow status",
                    errors=["Could not retrieve run status"]
                )

            elapsed = int(time.time() - start_time)

            # Check for completion
            if status_info["status"] == "completed":
                conclusion = status_info.get("conclusion", "unknown")
                return ScriptResult(
                    success=(conclusion == "success"),
                    message=f"Workflow {conclusion}",
                    data={
                        "run_id": run_id,
                        "conclusion": conclusion,
                        "elapsed_seconds": elapsed,
                        "url": status_info.get("url", ""),
                        "status_info": status_info
                    }
                )

            # Check for timeout
            if timeout > 0 and elapsed > timeout:
                return ScriptResult(
                    success=False,
                    message="Workflow timed out",
                    data={
                        "run_id": run_id,
                        "elapsed_seconds": elapsed,
                        "url": status_info.get("url", "")
                    },
                    errors=[f"Timeout after {elapsed}s"]
                )

            # Show progress dot
            if show_progress:
                print(".", end="", flush=True)

            time.sleep(poll_interval)

    def _get_run_status(self, repo: str, run_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a workflow run."""
        cmd = [
            "gh", "run", "view", run_id,
            "-R", repo,
            "--json", "status,conclusion,url,name,createdAt,updatedAt"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass

        return None

    def _display_triggered(self, project: str, repo: str, workflow: str,
                           branch: str, params: Dict[str, str], run_id: str) -> None:
        """Display triggered workflow info (for --no-wait)."""
        self.console.print()
        table = Table(title=f"Workflow Triggered: {project}")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Repository", repo)
        table.add_row("Workflow", workflow)
        table.add_row("Branch", branch)
        table.add_row("Run ID", run_id)
        table.add_row("URL", f"https://github.com/{repo}/actions/runs/{run_id}")

        if params:
            params_str = ", ".join(f"{k}={v}" for k, v in params.items())
            table.add_row("Parameters", params_str)

        self.console.print(table)

    def _display_final_result(self, project: str, repo: str, workflow: str,
                              branch: str, params: Dict[str, str], run_id: str,
                              result: ScriptResult, verbose: bool) -> None:
        """Display the final workflow result."""
        # Clear progress dots
        print()

        conclusion = result.data.get("conclusion", "unknown")
        elapsed = result.data.get("elapsed_seconds", 0)
        url = result.data.get("url", f"https://github.com/{repo}/actions/runs/{run_id}")

        # Determine style based on conclusion
        if conclusion == "success":
            status_style = "green"
            status_text = "SUCCESS"
        elif conclusion == "failure":
            status_style = "red"
            status_text = "FAILURE"
        elif conclusion == "cancelled":
            status_style = "yellow"
            status_text = "CANCELLED"
        else:
            status_style = "white"
            status_text = conclusion.upper()

        elapsed_str = f"{elapsed // 60}m {elapsed % 60}s"

        # Build result table
        table = Table(title=f"Workflow Result: {project}", style=status_style)
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Status", f"[bold {status_style}]{status_text}[/bold {status_style}]")
        table.add_row("Repository", repo)
        table.add_row("Workflow", workflow)
        table.add_row("Branch", branch)
        table.add_row("Run ID", run_id)
        table.add_row("Duration", elapsed_str)
        table.add_row("URL", url)

        if params:
            params_str = ", ".join(f"{k}={v}" for k, v in params.items())
            table.add_row("Parameters", params_str)

        self.console.print()
        self.console.print(table)

        # Show logs if verbose or failed
        if verbose or conclusion == "failure":
            self._show_workflow_logs(repo, run_id, verbose)

    def _show_workflow_logs(self, repo: str, run_id: str, verbose: bool) -> None:
        """Show workflow logs."""
        self.console.print()

        if verbose:
            cmd = ["gh", "run", "view", run_id, "-R", repo, "--log"]
            title = "Full Workflow Logs"
        else:
            cmd = ["gh", "run", "view", run_id, "-R", repo, "--log-failed"]
            title = "Failed Job Logs"

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout:
                # Truncate if too long
                logs = result.stdout
                if len(logs) > 15000:
                    logs = logs[:15000] + "\n\n... (truncated, see GitHub for full logs)"

                self.console.print(Panel(logs, title=title, expand=False))
            elif not verbose:
                self.console.print("[dim]No failed job logs available[/dim]")
        except Exception as e:
            self.console.print(f"[red]Error fetching logs: {e}[/red]")
