"""GitHub Actions workflow list script - list available workflows and their inputs."""

import base64
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from scripts.base import BaseScript, ScriptConfig, ScriptResult


class WorkflowListScript(BaseScript):
    """Script to list available workflows and their input options."""

    config = ScriptConfig(
        name="workflow-list",
        description="List available workflows and their input options",
        version="1.0.0"
    )

    def __init__(self):
        self.console = Console()
        self.projects_config: Dict[str, Any] = {}

    def run(self, verbose: bool = False, **kwargs) -> ScriptResult:
        """
        List available workflows and their inputs.

        Args:
            verbose: If True, show detailed input descriptions
            project: Project name from projects.yaml

        Returns:
            ScriptResult with workflow list
        """
        project = kwargs.get("project")

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
        branch = project_cfg.get("branch", "main")

        # Get workflows
        workflows = self._get_workflows(repo, branch)
        if not workflows:
            return ScriptResult(
                success=False,
                message="No workflows found",
                errors=[f"No workflows found in {repo}"]
            )

        # Display workflows
        self._display_workflows(project, repo, workflows, verbose)

        return ScriptResult(
            success=True,
            message=f"Found {len(workflows)} workflows",
            data={"workflows": workflows}
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

    def _get_workflows(self, repo: str, branch: str) -> List[Dict[str, Any]]:
        """Get list of workflows from repository."""
        cmd = ["gh", "workflow", "list", "-R", repo, "--json", "name,path,state"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                workflows = json.loads(result.stdout)
                # Fetch inputs for each workflow
                for wf in workflows:
                    wf["inputs"] = self._get_workflow_inputs(repo, wf.get("path", ""), branch)
                return workflows
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

        return []

    def _get_workflow_inputs(self, repo: str, workflow_path: str, branch: str = None) -> Dict[str, Any]:
        """Fetch inputs for a specific workflow."""
        if not workflow_path:
            return {}

        try:
            # Get workflow content from GitHub
            api_url = f"repos/{repo}/contents/{workflow_path}"
            if branch:
                api_url += f"?ref={branch}"
            cmd = ["gh", "api", api_url, "--jq", ".content"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {}

            content = base64.b64decode(result.stdout.strip()).decode('utf-8')
            workflow_yaml = yaml.safe_load(content)

            inputs = {}
            # Handle 'on' key - YAML parses 'on' as boolean True, so check both
            on_config = workflow_yaml.get("on") or workflow_yaml.get(True, {})
            if isinstance(on_config, dict):
                dispatch_inputs = on_config.get("workflow_dispatch", {})
                if isinstance(dispatch_inputs, dict):
                    dispatch_inputs = dispatch_inputs.get("inputs", {})
                else:
                    dispatch_inputs = {}
            else:
                dispatch_inputs = {}

            for name, config in dispatch_inputs.items():
                if isinstance(config, dict):
                    inputs[name] = {
                        "type": config.get("type", "string"),
                        "options": config.get("options", []),
                        "default": config.get("default"),
                        "required": config.get("required", False),
                        "description": config.get("description", "")
                    }
            return inputs
        except Exception:
            return {}

    def _display_workflows(self, project: str, repo: str, workflows: List[Dict[str, Any]], verbose: bool) -> None:
        """Display workflows and their inputs."""
        self.console.print()
        self.console.print(f"[bold cyan]Workflows for {project}[/bold cyan] ({repo})")
        self.console.print()

        for wf in workflows:
            name = wf.get("name", "Unknown")
            path = wf.get("path", "").split("/")[-1]  # Just filename
            state = wf.get("state", "unknown")
            inputs = wf.get("inputs", {})

            state_style = "green" if state == "active" else "yellow"
            self.console.print(f"  [bold]{path}[/bold] [{state_style}]{state}[/{state_style}]")

            if inputs:
                for input_name, input_cfg in inputs.items():
                    input_type = input_cfg.get("type", "string")
                    options = input_cfg.get("options", [])
                    default = input_cfg.get("default")
                    required = input_cfg.get("required", False)
                    description = input_cfg.get("description", "")

                    # Format input line
                    req_mark = "*" if required else ""
                    if options:
                        options_str = f"[{', '.join(options)}]"
                        self.console.print(f"    [cyan]{input_name}{req_mark}[/cyan]: {options_str}")
                    else:
                        self.console.print(f"    [cyan]{input_name}{req_mark}[/cyan]: ({input_type})")

                    if default:
                        self.console.print(f"      [dim]default: {default}[/dim]")

                    if verbose and description:
                        self.console.print(f"      [dim]{description}[/dim]")
            else:
                self.console.print("    [dim]No workflow_dispatch inputs[/dim]")

            self.console.print()
