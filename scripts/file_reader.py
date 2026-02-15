"""File reader script - reads and displays files matching a pattern."""

import os
from pathlib import Path
from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from scripts.base import BaseScript, ScriptConfig, ScriptResult


class FileReaderScript(BaseScript):
    """Script to read and display files matching a glob pattern."""

    config = ScriptConfig(
        name="file-reader",
        description="Read and display files matching a glob pattern",
        version="1.0.0"
    )

    def __init__(self):
        self.console = Console()

    def run(self, verbose: bool = False, **kwargs) -> ScriptResult:
        """
        Read files matching the given pattern.

        Args:
            verbose: If True, show full file contents
            path: Directory to search in (default: current directory)
            pattern: Glob pattern to match files (default: "*")

        Returns:
            ScriptResult with list of files and their contents
        """
        path = kwargs.get("path", ".")
        pattern = kwargs.get("pattern", "*")

        base_path = Path(path)
        if not base_path.exists():
            return ScriptResult(
                success=False,
                message=f"Path does not exist: {path}",
                errors=[f"Directory not found: {path}"]
            )

        if not base_path.is_dir():
            return ScriptResult(
                success=False,
                message=f"Path is not a directory: {path}",
                errors=[f"Not a directory: {path}"]
            )

        # Find matching files
        files = self._find_files(base_path, pattern)

        if not files:
            self.console.print(f"[yellow]No files found matching pattern: {pattern}[/yellow]")
            return ScriptResult(
                success=True,
                message=f"No files found matching pattern: {pattern}",
                data={"files": [], "count": 0}
            )

        # Display results
        file_data = self._process_files(files, verbose)

        return ScriptResult(
            success=True,
            message=f"Found {len(files)} file(s) matching pattern: {pattern}",
            data={"files": file_data, "count": len(files)}
        )

    def _find_files(self, base_path: Path, pattern: str) -> List[Path]:
        """Find all files matching the pattern."""
        files = []
        for file_path in base_path.glob(pattern):
            if file_path.is_file():
                files.append(file_path)
        return sorted(files)

    def _process_files(self, files: List[Path], verbose: bool) -> List[Dict[str, Any]]:
        """Process and display files."""
        file_data = []

        if verbose:
            # Show full file contents
            for file_path in files:
                file_info = self._read_file(file_path)
                file_data.append(file_info)
                self._display_file_content(file_path, file_info)
        else:
            # Show summary table
            self._display_file_table(files)
            for file_path in files:
                file_data.append({
                    "path": str(file_path),
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "extension": file_path.suffix
                })

        return file_data

    def _read_file(self, file_path: Path) -> Dict[str, Any]:
        """Read a single file and return its info."""
        try:
            content = file_path.read_text(encoding="utf-8")
            return {
                "path": str(file_path),
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "extension": file_path.suffix,
                "content": content,
                "lines": len(content.splitlines()),
                "error": None
            }
        except UnicodeDecodeError:
            return {
                "path": str(file_path),
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "extension": file_path.suffix,
                "content": None,
                "lines": 0,
                "error": "Binary file or encoding error"
            }
        except Exception as e:
            return {
                "path": str(file_path),
                "name": file_path.name,
                "size": 0,
                "extension": file_path.suffix,
                "content": None,
                "lines": 0,
                "error": str(e)
            }

    def _display_file_table(self, files: List[Path]) -> None:
        """Display files in a summary table."""
        table = Table(title="Files Found")
        table.add_column("Name", style="cyan")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Extension", style="yellow")
        table.add_column("Path", style="dim")

        for file_path in files:
            size = file_path.stat().st_size
            size_str = self._format_size(size)
            table.add_row(
                file_path.name,
                size_str,
                file_path.suffix or "-",
                str(file_path.parent)
            )

        self.console.print(table)

    def _display_file_content(self, file_path: Path, file_info: Dict[str, Any]) -> None:
        """Display full file content with syntax highlighting."""
        if file_info["error"]:
            self.console.print(Panel(
                f"[red]Error: {file_info['error']}[/red]",
                title=f"[bold]{file_path.name}[/bold]",
                subtitle=f"Size: {self._format_size(file_info['size'])}"
            ))
            return

        # Try to determine language for syntax highlighting
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sh": "bash",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
            ".php": "php",
            ".xml": "xml",
        }
        lang = ext_to_lang.get(file_path.suffix.lower(), "text")

        syntax = Syntax(
            file_info["content"],
            lang,
            theme="monokai",
            line_numbers=True,
            word_wrap=True
        )

        self.console.print(Panel(
            syntax,
            title=f"[bold cyan]{file_path.name}[/bold cyan]",
            subtitle=f"Lines: {file_info['lines']} | Size: {self._format_size(file_info['size'])}"
        ))

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
