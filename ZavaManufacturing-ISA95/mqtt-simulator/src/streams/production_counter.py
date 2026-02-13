"""Stream 4 — Production Counter Telemetry (WorkUnit-level)."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Dict, List

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..utils import (
    utcnow, current_shift, rand_float, rand_int,
    iter_machines, equipment_id as fmt_eqp, machine_name as mk_name,
)
from .base import BaseStream

logger = logging.getLogger(__name__)


@dataclass
class CounterState:
    eqp_id: str
    line_name: str
    machine_name: str
    unit_count: int = 0


class ProductionCounterTelemetryStream(BaseStream):
    stream_slug = "production-counter"

    def __init__(self, cfg: SimulatorConfig, client: MqttClient) -> None:
        super().__init__(cfg, client)
        self._scfg = cfg.production_counter_telemetry
        self._counters: List[CounterState] = []

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    def _init_counters(self) -> None:
        if self._counters:
            return

        # Share machine list with machine-state config:
        # if machine-state uses explicit lines, production counter does too.
        ms_cfg = self.cfg.machine_state_telemetry
        if ms_cfg.auto_discover:
            machines = list(iter_machines())
        else:
            machines = []
            for line_cfg in ms_cfg.lines:
                for i in range(line_cfg.machines_per_line):
                    eqp = fmt_eqp(line_cfg.equipment_id_start + i)
                    name = mk_name(line_cfg.name, i)
                    machines.append((eqp, line_cfg.name, name, i))

        for eqp_id, line, name, _ in machines:
            # Random starting unit count (simulates in-progress production)
            c = CounterState(
                eqp_id=eqp_id,
                line_name=line,
                machine_name=name,
                unit_count=random.randint(100_000, 2_000_000),
            )
            self._counters.append(c)

    # ------------------------------------------------------------------
    # Overrides (anomaly injection)
    # ------------------------------------------------------------------
    _oee_override: list[float] | None = None
    _reject_override: float | None = None

    def apply_overrides(self, overrides: dict) -> None:
        if "oeeRange" in overrides:
            self._oee_override = overrides["oeeRange"]
        if "rejectRate" in overrides:
            self._reject_override = overrides["rejectRate"]

    def clear_overrides(self) -> None:
        self._oee_override = None
        self._reject_override = None

    # ------------------------------------------------------------------

    async def run(self) -> None:
        self._init_counters()
        interval = self._scfg.interval_sec
        batches = self.cfg.simulation.active_batches
        batch_map = {b.batch_id: b for b in batches} if batches else {}
        batch_ids = list(batch_map.keys()) or ["BTC-000"]
        skus = [b.sku for b in batches] if batches else ["ZC Field Standard"]

        logger.info("ProductionCounterTelemetry started — %d machines, every %ds",
                     len(self._counters), interval)

        while True:
            shift = current_shift(
                self.cfg.simulation.shifts.day_start,
                self.cfg.simulation.shifts.night_start,
            )

            for c in self._counters:
                delta = rand_int(
                    self._scfg.unit_count_increment_range[0],
                    self._scfg.unit_count_increment_range[1],
                )
                c.unit_count += delta

                fiber = rand_float(
                    self._scfg.fiber_produced_gram_range[0],
                    self._scfg.fiber_produced_gram_range[1],
                )

                rr = self._reject_override if self._reject_override is not None else self._scfg.reject_rate
                rejected = 1 if random.random() < rr else 0
                fiber_rejected = round(fiber * 0.3, 1) if rejected else 0.0

                oee_range = self._oee_override or self._scfg.oee_range
                oee = rand_float(oee_range[0], oee_range[1], 2)
                vot = rand_float(self._scfg.vot_range[0], self._scfg.vot_range[1], 1)

                batch_id = random.choice(batch_ids)
                sku = batch_map[batch_id].sku if batch_id in batch_map else random.choice(skus)

                payload = {
                    "Timestamp": utcnow(),
                    "EquipmentId": c.eqp_id,
                    "LineName": c.line_name,
                    "SKU": sku,
                    "Shift": shift,
                    "UnitCount": c.unit_count,
                    "UnitCountDelta": delta,
                    "FiberProducedGram": fiber,
                    "UnitsRejected": rejected,
                    "FiberRejectedGram": fiber_rejected,
                    "VOT": vot,
                    "LoadingTime": rand_float(
                        self._scfg.loading_time_base * 0.9,
                        self._scfg.loading_time_base * 1.1,
                        2,
                    ),
                    "OEE": oee,
                    "BatchId": batch_id,
                }

                await self.publish(
                    payload,
                    equipment_id=c.eqp_id,
                    line_name=c.line_name,
                    machine_name=c.machine_name,
                )

            await asyncio.sleep(interval)
