"""Stream 6 — Predictive Maintenance Signals (WorkUnit-level)."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..utils import utcnow, rand_float, iter_machines
from .base import BaseStream

logger = logging.getLogger(__name__)


@dataclass
class MachineHealth:
    eqp_id: str
    line_name: str
    machine_name: str
    health_score: float = 1.0
    degrading: bool = False


class PredictiveMaintenanceStream(BaseStream):
    stream_slug = "predictive-maintenance"

    def __init__(self, cfg: SimulatorConfig, client: MqttClient) -> None:
        super().__init__(cfg, client)
        self._scfg = cfg.predictive_maintenance_signals
        self._machines: List[MachineHealth] = []

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    def _init_machines(self) -> None:
        if self._machines:
            return
        all_machines = list(iter_machines())

        if self._scfg.machines == "auto":
            selected = all_machines
        else:
            id_set = set(self._scfg.machines) if isinstance(self._scfg.machines, list) else set()
            selected = [m for m in all_machines if m[0] in id_set] or all_machines

        for eqp_id, line, name, _ in selected:
            self._machines.append(MachineHealth(eqp_id=eqp_id, line_name=line, machine_name=name))

        # Mark a subset as actively degrading
        deg = self._scfg.degradation
        if deg.enabled:
            degrading = random.sample(self._machines, min(deg.machines_with_degradation, len(self._machines)))
            for m in degrading:
                m.degrading = True
                m.health_score = rand_float(deg.warning_threshold, 1.0)

        logger.info("PredictiveMaintenanceStream: %d machines (%d degrading)",
                     len(self._machines), sum(1 for m in self._machines if m.degrading))

    # ------------------------------------------------------------------
    # Overrides (anomaly)
    # ------------------------------------------------------------------
    _vib_override: list[float] | None = None
    _bearing_override: list[float] | None = None
    _health_override: float | None = None

    def apply_overrides(self, overrides: dict) -> None:
        self._vib_override = overrides.get("vibrationRange")
        self._bearing_override = overrides.get("bearingTempRange")
        self._health_override = overrides.get("healthScoreOverride")

    def clear_overrides(self) -> None:
        self._vib_override = None
        self._bearing_override = None
        self._health_override = None

    # ------------------------------------------------------------------

    async def run(self) -> None:
        self._init_machines()
        interval = self._scfg.interval_sec
        deg_cfg = self._scfg.degradation
        deg_rate = deg_cfg.degradation_rate_per_hour / (3600 / interval) if deg_cfg.enabled else 0

        logger.info("PredictiveMaintenanceStream started — every %ds", interval)

        while True:
            for m in self._machines:
                # Degrade health
                if m.degrading and deg_cfg.enabled:
                    m.health_score = max(0.0, m.health_score - deg_rate)

                # Determine trend
                if m.health_score < deg_cfg.critical_threshold:
                    trend = "critical"
                elif m.health_score < deg_cfg.warning_threshold:
                    trend = "degrading"
                else:
                    trend = "stable"

                # Scale vibration / bearing temp inversely with health
                health = self._health_override if self._health_override is not None else m.health_score
                vr = self._vib_override or self._scfg.vibration_range
                br = self._bearing_override or self._scfg.bearing_temp_range

                # Higher vibration / temp for lower health
                health_factor = max(0.1, health)
                vib = rand_float(vr[0], vr[1] / health_factor)
                bear_t = rand_float(br[0], br[1] / health_factor)

                rul = max(0, int(m.health_score * 2000 + random.gauss(0, 50)))

                payload = {
                    "Timestamp": utcnow(),
                    "EquipmentId": m.eqp_id,
                    "LineName": m.line_name,
                    "MachineName": m.machine_name,
                    "VibrationMmS": round(min(vib, 20.0), 1),
                    "BearingTemperatureC": round(min(bear_t, 150.0), 1),
                    "AcousticDB": rand_float(self._scfg.acoustic_db_range[0], self._scfg.acoustic_db_range[1]),
                    "MotorCurrentA": rand_float(self._scfg.motor_current_range[0], self._scfg.motor_current_range[1]),
                    "SpindleSpeedRPM": round(rand_float(self._scfg.spindle_speed_range[0], self._scfg.spindle_speed_range[1], 0)),
                    "RemainingUsefulLifeHrs": rul,
                    "HealthScore": round(m.health_score, 2),
                    "DegradationTrend": trend,
                }

                await self.publish(
                    payload,
                    equipment_id=m.eqp_id,
                    line_name=m.line_name,
                    machine_name=m.machine_name,
                )

            await asyncio.sleep(interval)
