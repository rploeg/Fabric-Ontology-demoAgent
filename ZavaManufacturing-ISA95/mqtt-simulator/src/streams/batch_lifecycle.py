"""Stream 11 — Batch Lifecycle Simulation (coordinated cross-stream events).

Simulates the full lifecycle of a production batch:
  1. BatchStart   — batch is created, assigned to a line
  2. SegmentStart — first process segment begins (e.g. Coating)
  3. MaterialPull — materials are consumed
  4. SegmentEnd   — segment completes
  5. QualityCheck — vision inspection result (pass/marginal/fail)
  6. BatchEnd     — batch completes (or fails QA)

Events are published to ``zava/events/batch-lifecycle`` (flat) or the
UNS path under the ``events`` category.  Each event references the
batch, line, segment, and equipment involved so downstream consumers
can correlate across all streams.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..state_registry import StateRegistry
from ..utils import (
    utcnow, utcnow_dt, random_id, rand_float, rand_int,
    random_lot_number, material_name, random_serial,
    current_shift, iter_machines, equipment_id as fmt_eqp,
)
from .base import BaseStream

logger = logging.getLogger(__name__)

# Lifecycle phases in order
PHASES = [
    "BatchStart",
    "SegmentStart",
    "MaterialPull",
    "SegmentEnd",
    "QualityCheck",
    "BatchEnd",
]


@dataclass
class BatchRun:
    """Tracks a single batch as it progresses through its lifecycle."""
    batch_id: str
    sku: str
    product: str
    line_name: str
    eqp_id: str
    phase_idx: int = 0
    segment_idx: int = 0
    quality_result: str = ""
    total_segments: int = 1


class BatchLifecycleStream(BaseStream):
    stream_slug = "batch-lifecycle"

    def __init__(
        self,
        cfg: SimulatorConfig,
        client: MqttClient,
        *,
        registry: StateRegistry | None = None,
    ) -> None:
        super().__init__(cfg, client, registry=registry)
        self._scfg = cfg.batch_lifecycle
        self._runs: List[BatchRun] = []
        self._batch_counter = 100

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    def _new_batch(self) -> BatchRun:
        """Create a new batch run assigned to a random line."""
        batches = self.cfg.simulation.active_batches
        template = random.choice(batches) if batches else None
        self._batch_counter += 1
        batch_id = f"BTC-{self._batch_counter:03d}"
        sku = template.sku if template else "ZC Field Standard"
        product = template.product if template else "ZavaCore Field Standard"

        # Pick a random production line + equipment
        machines = list(iter_machines())
        if machines:
            eqp_id, line_name, _, _ = random.choice(machines)
        else:
            eqp_id, line_name = "EQP-016", "WeaveLine-Alpha"

        segments = self.cfg.process_segment_telemetry.segments
        total_segs = len(segments) if segments else 1

        return BatchRun(
            batch_id=batch_id,
            sku=sku,
            product=product,
            line_name=line_name,
            eqp_id=eqp_id,
            total_segments=total_segs,
        )

    async def run(self) -> None:
        scfg = self._scfg
        logger.info(
            "BatchLifecycleStream started — interval %ds, max concurrent %d",
            scfg.interval_sec,
            scfg.max_concurrent_batches,
        )

        while True:
            # Start new batches up to max_concurrent
            while len(self._runs) < scfg.max_concurrent_batches:
                self._runs.append(self._new_batch())

            # Advance each batch by one phase
            completed: List[BatchRun] = []
            for batch in self._runs:
                await self._advance(batch)
                if batch.phase_idx >= len(PHASES):
                    completed.append(batch)

            # Remove completed batches
            for b in completed:
                self._runs.remove(b)

            await asyncio.sleep(scfg.interval_sec)

    async def _advance(self, batch: BatchRun) -> None:
        """Execute the current phase for this batch."""
        if batch.phase_idx >= len(PHASES):
            return

        phase = PHASES[batch.phase_idx]
        now = utcnow_dt()
        segments = list(self.cfg.process_segment_telemetry.segments)
        seg = segments[batch.segment_idx % len(segments)] if segments else None
        materials = self.cfg.material_consumption_events.materials
        shift = current_shift(
            self.cfg.simulation.shifts.day_start,
            self.cfg.simulation.shifts.night_start,
        )

        base_payload = {
            "Timestamp": utcnow(),
            "EventId": random_id("BLC", now),
            "BatchId": batch.batch_id,
            "SKU": batch.sku,
            "Product": batch.product,
            "LineName": batch.line_name,
            "EquipmentId": batch.eqp_id,
            "Shift": shift,
            "Phase": phase,
        }

        if phase == "BatchStart":
            payload = {
                **base_payload,
                "TotalSegments": batch.total_segments,
                "PlannedDurationMin": rand_int(30, 120),
            }

        elif phase == "SegmentStart":
            payload = {
                **base_payload,
                "SegmentId": seg.id if seg else "SEG-000",
                "SegmentType": seg.type if seg else "Unknown",
                "SegmentIndex": batch.segment_idx + 1,
                "TotalSegments": batch.total_segments,
                "TargetTemperature": seg.temperature_range[1] if seg else 90,
            }

        elif phase == "MaterialPull":
            # Pick materials for this segment type
            seg_type = seg.type if seg else "Coating"
            bom = materials.get(seg_type, [])
            entry = random.choice(bom) if bom else None
            qty = round(entry.expected_per_batch * random.uniform(0.08, 0.15), 3) if entry else 0
            payload = {
                **base_payload,
                "SegmentId": seg.id if seg else "SEG-000",
                "MaterialId": entry.material_id if entry else "MAT-000",
                "MaterialName": material_name(entry.material_id) if entry else "Unknown",
                "QuantityUsed": qty,
                "UnitOfMeasure": "kg",
                "LotNumber": random_lot_number(entry.material_id) if entry else "",
            }
            # Record in registry for supply-chain correlation
            if entry:
                self.registry.record_consumption(batch.batch_id, seg.id if seg else "SEG-000", entry.material_id)

        elif phase == "SegmentEnd":
            payload = {
                **base_payload,
                "SegmentId": seg.id if seg else "SEG-000",
                "SegmentType": seg.type if seg else "Unknown",
                "ActualTemperature": rand_float(
                    seg.temperature_range[0], seg.temperature_range[1]
                ) if seg else 88.0,
                "ActualCycleTimeSec": rand_int(
                    int(seg.cycle_time_range[0]), int(seg.cycle_time_range[1])
                ) if seg else 110,
                "SegmentResult": "Pass",
            }

        elif phase == "QualityCheck":
            pass_rate = self.cfg.quality_vision_events.pass_rate
            roll = random.random()
            if roll < pass_rate:
                result = "Pass"
            elif roll < pass_rate + 0.03:
                result = "Marginal"
            else:
                result = "Fail"
            batch.quality_result = result

            defect = ""
            if result != "Pass":
                defect_types = self.cfg.quality_vision_events.defect_types
                if defect_types:
                    defect = random.choice(defect_types).type
            payload = {
                **base_payload,
                "InspectionResult": result,
                "DefectType": defect,
                "Confidence": rand_float(0.85, 0.99, 2),
                "UnitSerial": random_serial(batch.sku, batch.batch_id),
            }

        elif phase == "BatchEnd":
            status = "Completed" if batch.quality_result == "Pass" else "Rejected"
            payload = {
                **base_payload,
                "BatchStatus": status,
                "QualityResult": batch.quality_result,
                "SegmentsCompleted": batch.total_segments,
            }

        else:
            payload = base_payload

        await self.publish(
            payload,
            equipment_id=batch.eqp_id,
            line_name=batch.line_name,
        )

        batch.phase_idx += 1
