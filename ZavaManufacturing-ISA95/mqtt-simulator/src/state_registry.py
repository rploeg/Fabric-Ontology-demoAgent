"""Shared state registry for cross-stream correlation.

Streams publish state updates here so other streams can read them.
This avoids direct coupling between stream classes while enabling
realistic correlated behaviour (e.g. digital twin mirroring machine
state, predictive maintenance resetting on Maintenance events).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class MachineState:
    """Last known state of a WorkUnit, published by MachineStateTelemetryStream."""
    eqp_id: str
    state: str = "Running"
    error_code: str = "0"
    line_name: str = ""
    batch_id: str = ""


class StateRegistry:
    """Thread-safe (asyncio single-thread) registry of cross-stream state.

    All stream coroutines run on the same event loop so no locking is needed.
    """

    def __init__(self) -> None:
        # Machine state by equipment_id  (published by machine_state stream)
        self._machine_states: Dict[str, MachineState] = {}
        # Maintenance events — set of eqp_ids currently in Maintenance
        self._in_maintenance: set[str] = set()
        # Batch→segment→material tracking for supply-chain traversal
        self._batch_segments: Dict[str, list[str]] = {}   # batch_id → [segment_ids]
        self._segment_materials: Dict[str, list[str]] = {}  # segment_id → [material_ids]

    # ------------------------------------------------------------------
    # Machine state (published by machine_state stream)
    # ------------------------------------------------------------------

    def update_machine_state(
        self,
        eqp_id: str,
        state: str,
        error_code: str = "0",
        line_name: str = "",
        batch_id: str = "",
    ) -> None:
        prev = self._machine_states.get(eqp_id)
        was_maintenance = eqp_id in self._in_maintenance

        self._machine_states[eqp_id] = MachineState(
            eqp_id=eqp_id,
            state=state,
            error_code=error_code,
            line_name=line_name,
            batch_id=batch_id,
        )

        # Track maintenance transitions
        if state == "Maintenance":
            self._in_maintenance.add(eqp_id)
        elif was_maintenance:
            self._in_maintenance.discard(eqp_id)

    def get_machine_state(self, eqp_id: str) -> Optional[MachineState]:
        return self._machine_states.get(eqp_id)

    def entered_maintenance(self, eqp_id: str) -> bool:
        """True if machine is *currently* in Maintenance state."""
        return eqp_id in self._in_maintenance

    def all_machine_states(self) -> Dict[str, MachineState]:
        return dict(self._machine_states)

    # ------------------------------------------------------------------
    # Batch-material tracking (published by material_consumption stream)
    # ------------------------------------------------------------------

    def record_consumption(
        self,
        batch_id: str,
        segment_id: str,
        material_id: str,
    ) -> None:
        """Record that *batch_id* used *material_id* in *segment_id*."""
        segs = self._batch_segments.setdefault(batch_id, [])
        if segment_id not in segs:
            segs.append(segment_id)
        mats = self._segment_materials.setdefault(segment_id, [])
        if material_id not in mats:
            mats.append(material_id)

    def batches_for_materials(self, material_ids: list[str]) -> list[str]:
        """Return batch_ids whose segments consumed any of *material_ids*."""
        mat_set = set(material_ids)
        result: list[str] = []
        for batch_id, seg_ids in self._batch_segments.items():
            for seg_id in seg_ids:
                seg_mats = self._segment_materials.get(seg_id, [])
                if mat_set & set(seg_mats):
                    result.append(batch_id)
                    break
        return result
