"""Stream 8 — Material Consumption Events."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..utils import (
    utcnow, utcnow_dt, random_id, rand_float, random_lot_number,
    material_name, iter_machines,
)
from .base import BaseStream

logger = logging.getLogger(__name__)


@dataclass
class MaterialTracker:
    """Cumulative consumption tracker per (segment, material)."""
    cumulative: float = 0.0


class MaterialConsumptionStream(BaseStream):
    stream_slug = "material-consumption"

    def __init__(self, cfg: SimulatorConfig, client: MqttClient, **kwargs) -> None:
        super().__init__(cfg, client, **kwargs)
        self._scfg = cfg.material_consumption_events
        self._trackers: Dict[str, MaterialTracker] = {}

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    # Override support
    _variance_override: list[float] | None = None

    def apply_overrides(self, overrides: dict) -> None:
        self._variance_override = overrides.get("variancePctRange")

    def clear_overrides(self) -> None:
        self._variance_override = None

    async def run(self) -> None:
        scfg = self._scfg
        segments = list(self.cfg.process_segment_telemetry.segments)
        batches = self.cfg.simulation.active_batches
        batch_ids = [b.batch_id for b in batches] if batches else ["BTC-000"]

        # Build a quick eqp lookup for segments
        machines = list(iter_machines())
        eqp_pool = [m[0] for m in machines[:20]]  # first 20 machines as segment hosts

        logger.info("MaterialConsumptionStream started — %d segment types", len(scfg.materials))

        while True:
            wait = random.randint(scfg.min_interval_sec, scfg.max_interval_sec)
            await asyncio.sleep(wait)

            if not segments or not scfg.materials:
                continue

            seg = random.choice(segments)
            seg_type = seg.type
            bom_entries = scfg.materials.get(seg_type, [])
            if not bom_entries:
                continue

            entry = random.choice(bom_entries)
            now = utcnow_dt()
            batch_id = random.choice(batch_ids)
            eqp = random.choice(eqp_pool)

            # Quantity with variance
            var_range = self._variance_override or scfg.variance_pct_range
            variance_pct = rand_float(var_range[0], var_range[1])
            qty = round(entry.expected_per_batch * (1 + variance_pct / 100) * random.uniform(0.01, 0.1), 3)

            key = f"{seg.id}:{entry.material_id}"
            tracker = self._trackers.setdefault(key, MaterialTracker())
            tracker.cumulative += qty
            cum_pct = ((tracker.cumulative / entry.expected_per_batch) - 1) * 100 if entry.expected_per_batch else 0

            payload = {
                "Timestamp": utcnow(),
                "ConsumptionId": random_id("CON", now),
                "SegmentId": seg.id,
                "SegmentType": seg_type,
                "BatchId": batch_id,
                "MaterialId": entry.material_id,
                "MaterialName": material_name(entry.material_id),
                "EquipmentId": eqp,
                "QuantityUsed": qty,
                "UnitOfMeasure": "kg",
                "CumulativeUsed": round(tracker.cumulative, 2),
                "BOMExpected": entry.expected_per_batch,
                "VariancePct": round(cum_pct, 1),
                "LotNumber": random_lot_number(entry.material_id),
            }

            # B3: Record consumption in registry for supply-chain traversal
            self.registry.record_consumption(
                batch_id=batch_id,
                segment_id=seg.id,
                material_id=entry.material_id,
            )

            await self.publish(payload, equipment_id=eqp)
