"""Base class for all scripts in the framework."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScriptConfig:
    """Configuration for a script."""
    name: str
    description: str
    version: str = "1.0.0"


@dataclass
class ScriptResult:
    """Standard result format for script execution."""
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "errors": self.errors
        }


class BaseScript(ABC):
    """Abstract base class for all scripts."""

    config: ScriptConfig

    @abstractmethod
    def run(self, verbose: bool = False, **kwargs) -> ScriptResult:
        """
        Execute the script.

        Args:
            verbose: If True, show detailed output
            **kwargs: Script-specific arguments

        Returns:
            ScriptResult with execution results
        """
        pass

    @classmethod
    def get_name(cls) -> str:
        """Get the script name."""
        return cls.config.name

    @classmethod
    def get_description(cls) -> str:
        """Get the script description."""
        return cls.config.description

    @classmethod
    def get_version(cls) -> str:
        """Get the script version."""
        return cls.config.version
