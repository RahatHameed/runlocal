"""Scripts package - collection of local automation scripts."""

from scripts.base import BaseScript, ScriptConfig, ScriptResult
from scripts.file_reader import FileReaderScript
from scripts.workflow_dispatch import WorkflowDispatchScript
from scripts.workflow_status import WorkflowStatusScript

# Registry of available scripts
SCRIPTS = {
    "file-reader": FileReaderScript,
    "workflow-dispatch": WorkflowDispatchScript,
    "workflow-status": WorkflowStatusScript,
}

__all__ = [
    "BaseScript",
    "ScriptConfig",
    "ScriptResult",
    "FileReaderScript",
    "WorkflowDispatchScript",
    "WorkflowStatusScript",
    "SCRIPTS",
]
