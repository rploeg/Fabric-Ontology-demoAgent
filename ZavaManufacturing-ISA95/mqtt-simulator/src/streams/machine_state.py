"""Stream 2 — Machine State Telemetry (WorkUnit-level state machine)."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..utils import (
    utcnow, current_shift, weighted_choice, rand_int,
    iter_machines, equipment_id as fmt_eqp,
)
from .base import BaseStream

logger = logging.getLogger(__name__)


@dataclass
class MachineRuntime:
    eqp_id: str
    line_name: str
    machine_name: str
    state: str = "Running"
    dwell_remaining: float = 0.0
    error_code: str = "0"
    duration_sec: int = 0


class MachineStateTelemetryStream(BaseStream):
    stream_slug = "machine-state"

    def __init__(self, cfg: SimulatorConfig, client: MqttClient, **kwargs) -> None:
        super().__init__(cfg, client, **kwargs)
        self._scfg = cfg.machine_state_telemetry
        self._machines: List[MachineRuntime] = []

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def _init_machines(self) -> None:
        """Populate machine list (auto-discover or from config)."""
        if self._machines:
            return

        if self._scfg.auto_discover:
            for eqp_id, line, name, _ in iter_machines():
                m = MachineRuntime(eqp_id=eqp_id, line_name=line, machine_name=name)
                self._assign_initial_dwell(m)
                self._machines.append(m)
        else:
            for line_cfg in self._scfg.lines:
                for i in range(line_cfg.machines_per_line):
                    eqp = fmt_eqp(line_cfg.equipment_id_start + i)
                    from ..utils import machine_name as mk_name
                    name = mk_name(line_cfg.name, i)
                    m = MachineRuntime(eqp_id=eqp, line_name=line_cfg.name, machine_name=name)
                    self._assign_initial_dwell(m)
                    self._machines.append(m)

        logger.info("Initialised %d machines across %d lines", len(self._machines),
                     len({m.line_name for m in self._machines}))

    def _assign_initial_dwell(self, m: MachineRuntime) -> None:
        st = self._scfg.state_transition
        m.dwell_remaining = rand_int(st.min_dwell_sec, st.max_dwell_sec)

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _transition(self, m: MachineRuntime) -> None:
        st = self._scfg.state_transition
        probs = st.probabilities
        states = list(probs.keys())
        weights = [probs[s] for s in states]
        m.state = weighted_choice(states, weights)
        m.dwell_remaining = rand_int(st.min_dwell_sec, st.max_dwell_sec)
        m.duration_sec = 0

        # Error codes only on Stopped/Blocked
        if m.state in ("Stopped", "Blocked") and random.random() < st.error_probability:
            m.error_code = random.choice(st.error_codes)
        else:
            m.error_code = "0"

    # ------------------------------------------------------------------
    # Overrides (anomaly injection support)
    # ------------------------------------------------------------------

    _override_probs: Dict[str, float] | None = None
    _override_error_prob: float | None = None

    def apply_overrides(self, overrides: Dict) -> None:
        if "probabilities" in overrides:
            self._override_probs = overrides["probabilities"]
        if "errorProbability" in overrides:
            self._override_error_prob = overrides["errorProbability"]

    def clear_overrides(self) -> None:
        self._override_probs = None
        self._override_error_prob = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        self._init_machines()
        tick = self.cfg.simulation.tick_interval_sec
        batches = self.cfg.simulation.active_batches
        batch_ids = [b.batch_id for b in batches] if batches else ["BTC-000"]

        logger.info("MachineStateTelemetry started — %d machines, tick %ds", len(self._machines), tick)

        while True:
            for m in self._machines:
                m.dwell_remaining -= tick
                m.duration_sec += tick

                if m.dwell_remaining <= 0:
                    self._transition(m)

                    shift = current_shift(
                        self.cfg.simulation.shifts.day_start,
                        self.cfg.simulation.shifts.night_start,
                    )
                    batch_id = random.choice(batch_ids)

                    payload = {
                        "Timestamp": utcnow(),
                        "EquipmentId": m.eqp_id,
                        "LineName": m.line_name,
                        "Shift": shift,
                        "MachineState": m.state,
                        "ErrorCode": m.error_code,
                        "DurationSec": m.duration_sec,
                        "BatchId": batch_id,
                    }

                    # Publish state to shared registry for cross-stream correlation
                    self.registry.update_machine_state(
                        eqp_id=m.eqp_id,
                        state=m.state,
                        error_code=m.error_code,
                        line_name=m.line_name,
                        batch_id=batch_id,
                    )

                    await self.publish(
                        payload,
                        equipment_id=m.eqp_id,
                        line_name=m.line_name,
                        machine_name=m.machine_name,
                    )

            await asyncio.sleep(tick)
