"""Simple state management for resumability."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set


class StateManager:
    """Simple state management for resumability.

    State is persisted to a .state.json file in the demo folder,
    allowing setup to resume from the last successful step after
    failures.
    """

    STATE_FILENAME = ".state.json"

    def __init__(self, demo_path: Path | str):
        """Initialize state manager.

        Args:
            demo_path: Path to the demo package folder
        """
        self.demo_path = Path(demo_path)
        self.state_file = self.demo_path / self.STATE_FILENAME
        self._state = self._load()

    def _load(self) -> dict:
        """Load state from file or create new."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # Corrupted state file, start fresh
                pass

        return {
            "run_id": f"setup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            "workspace_id": None,
            "status": "pending",
            "completed": [],
            "resources": {
                "lakehouse_id": None,
                "eventhouse_id": None,
                "kql_database_id": None,
                "ontology_id": None,
            },
            "error": None,
            "started_at": None,
            "completed_at": None,
        }

    def save(self) -> None:
        """Save state to file."""
        self.state_file.write_text(
            json.dumps(self._state, indent=2, default=str), encoding="utf-8"
        )

    def delete(self) -> None:
        """Delete state file (for force restart)."""
        if self.state_file.exists():
            self.state_file.unlink()
        self._state = self._load()

    # --- Properties ---

    @property
    def completed(self) -> Set[str]:
        """Set of completed step names."""
        return set(self._state["completed"])

    @property
    def status(self) -> str:
        """Current status: pending, in_progress, completed, failed."""
        return self._state["status"]

    @property
    def resources(self) -> dict:
        """Dictionary of created resource IDs."""
        return self._state["resources"]

    @property
    def run_id(self) -> str:
        """Unique run identifier."""
        return self._state["run_id"]

    @property
    def workspace_id(self) -> Optional[str]:
        """Target workspace ID."""
        return self._state["workspace_id"]

    @property
    def error(self) -> Optional[str]:
        """Last error message if failed."""
        return self._state.get("error")

    # --- Methods ---

    def set_workspace(self, workspace_id: str) -> None:
        """Set workspace and start setup.

        Args:
            workspace_id: Target Fabric workspace ID
        """
        self._state["workspace_id"] = workspace_id
        self._state["status"] = "in_progress"
        self._state["started_at"] = datetime.now(timezone.utc).isoformat()
        self.save()

    def mark_done(self, step: str, resource_id: Optional[str] = None) -> None:
        """Mark step as completed.

        Args:
            step: The step name
            resource_id: Optional resource ID created by this step
        """
        if step not in self._state["completed"]:
            self._state["completed"].append(step)

        # Store resource ID based on step name
        if resource_id:
            if "lakehouse" in step.lower() and "create" in step.lower():
                self._state["resources"]["lakehouse_id"] = resource_id
            elif "eventhouse" in step.lower() and "create" in step.lower():
                self._state["resources"]["eventhouse_id"] = resource_id
            elif "kql" in step.lower() and "create" in step.lower():
                self._state["resources"]["kql_database_id"] = resource_id
            elif "ontology" in step.lower() and "create" in step.lower():
                self._state["resources"]["ontology_id"] = resource_id

        self.save()

    def is_done(self, step: str) -> bool:
        """Check if step is completed.

        Args:
            step: The step name

        Returns:
            True if step is in completed list
        """
        return step in self._state["completed"]

    def set_error(self, error: str) -> None:
        """Record error and mark as failed.

        Args:
            error: Error message
        """
        self._state["error"] = error
        self._state["status"] = "failed"
        self.save()

    def mark_completed(self) -> None:
        """Mark entire setup as completed."""
        self._state["status"] = "completed"
        self._state["error"] = None
        self._state["completed_at"] = datetime.now(timezone.utc).isoformat()
        self.save()

    def get_summary(self) -> str:
        """Get human-readable status summary.

        Returns:
            Formatted status string
        """
        lines = [
            f"Run ID: {self.run_id}",
            f"Status: {self.status}",
            f"Workspace: {self.workspace_id or 'Not set'}",
            f"Completed steps: {len(self.completed)}",
        ]

        if self.completed:
            lines.append("Steps:")
            for step in self._state["completed"]:
                lines.append(f"  ✅ {step}")

        if self._state["resources"]:
            resources_with_values = {
                k: v for k, v in self._state["resources"].items() if v
            }
            if resources_with_values:
                lines.append("Resources:")
                for key, value in resources_with_values.items():
                    lines.append(f"  {key}: {value}")

        if self.error:
            lines.append(f"Error: {self.error}")

        return "\n".join(lines)
