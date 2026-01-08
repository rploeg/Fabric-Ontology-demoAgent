"""
Setup State Manager for resume capability.

Manages setup progress state persistence to enable resuming
after partial failures or interruptions.
"""

import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any

import yaml


logger = logging.getLogger(__name__)


# State file name (gitignored)
STATE_FILE_NAME = ".setup-state.yaml"


class StepStatus(Enum):
    """Status of a single setup step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SetupStatus(Enum):
    """Overall setup status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StepState:
    """State of a single setup step."""
    name: str
    status: StepStatus = StepStatus.PENDING
    artifact_id: Optional[str] = None
    artifact_name: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result = {
            "status": self.status.value,
        }
        if self.artifact_id:
            result["artifact_id"] = self.artifact_id
        if self.artifact_name:
            result["artifact_name"] = self.artifact_name
        if self.started_at:
            result["started_at"] = self.started_at
        if self.completed_at:
            result["completed_at"] = self.completed_at
        if self.error_message:
            result["error_message"] = self.error_message
        if self.details:
            result["details"] = self.details
        return result

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "StepState":
        """Create from dictionary."""
        return cls(
            name=name,
            status=StepStatus(data.get("status", "pending")),
            artifact_id=data.get("artifact_id"),
            artifact_name=data.get("artifact_name"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            error_message=data.get("error_message"),
            details=data.get("details", {}),
        )


@dataclass
class SetupState:
    """Complete setup state for a demo."""
    setup_id: str
    demo_name: str
    workspace_id: str
    started_at: str
    status: SetupStatus = SetupStatus.PENDING
    completed_at: Optional[str] = None
    steps: Dict[str, StepState] = field(default_factory=dict)
    
    # Resource IDs discovered during setup
    lakehouse_id: Optional[str] = None
    lakehouse_name: Optional[str] = None
    eventhouse_id: Optional[str] = None
    eventhouse_name: Optional[str] = None
    kql_database_id: Optional[str] = None
    kql_database_name: Optional[str] = None
    ontology_id: Optional[str] = None
    ontology_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result = {
            "setup_id": self.setup_id,
            "demo_name": self.demo_name,
            "workspace_id": self.workspace_id,
            "started_at": self.started_at,
            "status": self.status.value,
            "steps": {name: step.to_dict() for name, step in self.steps.items()},
        }
        if self.completed_at:
            result["completed_at"] = self.completed_at
        
        # Add resource IDs
        resources = {}
        if self.lakehouse_id:
            resources["lakehouse"] = {
                "id": self.lakehouse_id,
                "name": self.lakehouse_name,
            }
        if self.eventhouse_id:
            resources["eventhouse"] = {
                "id": self.eventhouse_id,
                "name": self.eventhouse_name,
            }
        if self.kql_database_id:
            resources["kql_database"] = {
                "id": self.kql_database_id,
                "name": self.kql_database_name,
            }
        if self.ontology_id:
            resources["ontology"] = {
                "id": self.ontology_id,
                "name": self.ontology_name,
            }
        if resources:
            result["resources"] = resources
            
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SetupState":
        """Create from dictionary."""
        state = cls(
            setup_id=data.get("setup_id", str(uuid.uuid4())),
            demo_name=data.get("demo_name", ""),
            workspace_id=data.get("workspace_id", ""),
            started_at=data.get("started_at", ""),
            status=SetupStatus(data.get("status", "pending")),
            completed_at=data.get("completed_at"),
        )
        
        # Load steps
        for name, step_data in data.get("steps", {}).items():
            state.steps[name] = StepState.from_dict(name, step_data)
        
        # Load resource IDs
        resources = data.get("resources", {})
        if "lakehouse" in resources:
            state.lakehouse_id = resources["lakehouse"].get("id")
            state.lakehouse_name = resources["lakehouse"].get("name")
        if "eventhouse" in resources:
            state.eventhouse_id = resources["eventhouse"].get("id")
            state.eventhouse_name = resources["eventhouse"].get("name")
        if "kql_database" in resources:
            state.kql_database_id = resources["kql_database"].get("id")
            state.kql_database_name = resources["kql_database"].get("name")
        if "ontology" in resources:
            state.ontology_id = resources["ontology"].get("id")
            state.ontology_name = resources["ontology"].get("name")
            
        return state

    def get_completed_steps(self) -> List[str]:
        """Get list of completed step names."""
        return [
            name for name, step in self.steps.items()
            if step.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        ]

    def get_pending_steps(self) -> List[str]:
        """Get list of pending step names."""
        return [
            name for name, step in self.steps.items()
            if step.status == StepStatus.PENDING
        ]

    def get_failed_step(self) -> Optional[str]:
        """Get the name of the failed step, if any."""
        for name, step in self.steps.items():
            if step.status == StepStatus.FAILED:
                return name
        return None

    def can_resume(self) -> bool:
        """Check if this setup can be resumed."""
        # Can resume if in_progress or failed (not completed or cancelled)
        return self.status in (SetupStatus.IN_PROGRESS, SetupStatus.FAILED)


class SetupStateManager:
    """
    Manages setup state persistence for resume capability.
    
    State is saved to `.setup-state.yaml` in the demo folder after each step.
    On startup, existing state is loaded to enable resuming from where we left off.
    """

    def __init__(self, demo_path: Path, workspace_id: str, demo_name: str):
        """
        Initialize the state manager.
        
        Args:
            demo_path: Path to the demo folder
            workspace_id: Fabric workspace ID
            demo_name: Name of the demo
        """
        self.demo_path = Path(demo_path)
        self.state_file = self.demo_path / STATE_FILE_NAME
        self.workspace_id = workspace_id
        self.demo_name = demo_name
        self._state: Optional[SetupState] = None

    @property
    def state(self) -> SetupState:
        """Get or create the current state."""
        if self._state is None:
            self._state = self._create_new_state()
        return self._state

    def _create_new_state(self) -> SetupState:
        """Create a new setup state."""
        return SetupState(
            setup_id=str(uuid.uuid4()),
            demo_name=self.demo_name,
            workspace_id=self.workspace_id,
            started_at=datetime.now(timezone.utc).isoformat(),
            status=SetupStatus.PENDING,
        )

    def has_existing_state(self) -> bool:
        """Check if there's an existing state file."""
        return self.state_file.exists()

    def load_state(self) -> Optional[SetupState]:
        """
        Load existing state from file.
        
        Returns:
            SetupState if file exists, None otherwise
        """
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if not data:
                return None
            
            self._state = SetupState.from_dict(data)
            logger.info(f"Loaded existing state: {self._state.setup_id}")
            return self._state
            
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}")
            return None

    def save_state(self) -> None:
        """Save current state to file."""
        if self._state is None:
            return
        
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.state.to_dict(),
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )
            logger.debug(f"Saved state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def clear_state(self) -> None:
        """Remove the state file."""
        if self.state_file.exists():
            self.state_file.unlink()
            logger.info(f"Cleared state file: {self.state_file}")
        self._state = None

    def start_setup(self) -> None:
        """Mark setup as started."""
        self.state.status = SetupStatus.IN_PROGRESS
        self.state.started_at = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def complete_setup(self, success: bool = True) -> None:
        """Mark setup as completed or failed."""
        self.state.status = SetupStatus.COMPLETED if success else SetupStatus.FAILED
        self.state.completed_at = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def cancel_setup(self) -> None:
        """Mark setup as cancelled."""
        self.state.status = SetupStatus.CANCELLED
        self.state.completed_at = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def start_step(self, step_name: str) -> None:
        """Mark a step as started."""
        if step_name not in self.state.steps:
            self.state.steps[step_name] = StepState(name=step_name)
        
        step = self.state.steps[step_name]
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def complete_step(
        self,
        step_name: str,
        artifact_id: Optional[str] = None,
        artifact_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark a step as completed."""
        if step_name not in self.state.steps:
            self.state.steps[step_name] = StepState(name=step_name)
        
        step = self.state.steps[step_name]
        step.status = StepStatus.COMPLETED
        step.completed_at = datetime.now(timezone.utc).isoformat()
        if artifact_id:
            step.artifact_id = artifact_id
        if artifact_name:
            step.artifact_name = artifact_name
        if details:
            step.details.update(details)
        self.save_state()

    def skip_step(
        self,
        step_name: str,
        artifact_id: Optional[str] = None,
        artifact_name: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Mark a step as skipped."""
        if step_name not in self.state.steps:
            self.state.steps[step_name] = StepState(name=step_name)
        
        step = self.state.steps[step_name]
        step.status = StepStatus.SKIPPED
        step.completed_at = datetime.now(timezone.utc).isoformat()
        if artifact_id:
            step.artifact_id = artifact_id
        if artifact_name:
            step.artifact_name = artifact_name
        if reason:
            step.details["skip_reason"] = reason
        self.save_state()

    def fail_step(self, step_name: str, error_message: str) -> None:
        """Mark a step as failed."""
        if step_name not in self.state.steps:
            self.state.steps[step_name] = StepState(name=step_name)
        
        step = self.state.steps[step_name]
        step.status = StepStatus.FAILED
        step.completed_at = datetime.now(timezone.utc).isoformat()
        step.error_message = error_message
        self.save_state()

    def is_step_completed(self, step_name: str) -> bool:
        """Check if a step is already completed."""
        if step_name not in self.state.steps:
            return False
        return self.state.steps[step_name].status in (
            StepStatus.COMPLETED,
            StepStatus.SKIPPED,
        )

    def get_step_artifact_id(self, step_name: str) -> Optional[str]:
        """Get the artifact ID from a completed step."""
        if step_name not in self.state.steps:
            return None
        return self.state.steps[step_name].artifact_id

    def update_resource_ids(
        self,
        lakehouse_id: Optional[str] = None,
        lakehouse_name: Optional[str] = None,
        eventhouse_id: Optional[str] = None,
        eventhouse_name: Optional[str] = None,
        kql_database_id: Optional[str] = None,
        kql_database_name: Optional[str] = None,
        ontology_id: Optional[str] = None,
        ontology_name: Optional[str] = None,
    ) -> None:
        """Update resource IDs in state."""
        if lakehouse_id:
            self.state.lakehouse_id = lakehouse_id
        if lakehouse_name:
            self.state.lakehouse_name = lakehouse_name
        if eventhouse_id:
            self.state.eventhouse_id = eventhouse_id
        if eventhouse_name:
            self.state.eventhouse_name = eventhouse_name
        if kql_database_id:
            self.state.kql_database_id = kql_database_id
        if kql_database_name:
            self.state.kql_database_name = kql_database_name
        if ontology_id:
            self.state.ontology_id = ontology_id
        if ontology_name:
            self.state.ontology_name = ontology_name
        self.save_state()

    def get_resume_summary(self) -> Dict[str, Any]:
        """Get a summary of what will be resumed."""
        completed = self.state.get_completed_steps()
        pending = self.state.get_pending_steps()
        failed = self.state.get_failed_step()
        
        return {
            "setup_id": self.state.setup_id,
            "started_at": self.state.started_at,
            "status": self.state.status.value,
            "completed_steps": completed,
            "pending_steps": pending,
            "failed_step": failed,
            "can_resume": self.state.can_resume(),
            "resources": {
                "lakehouse": self.state.lakehouse_id,
                "eventhouse": self.state.eventhouse_id,
                "ontology": self.state.ontology_id,
            },
        }
