"""Stream 3 — Process Segment Telemetry."""

from __future__ import annotations

import asyncio
import logging
import random

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..utils import utcnow, rand_float
from .base import BaseStream

logger = logging.getLogger(__name__)


class ProcessSegmentTelemetryStream(BaseStream):
    stream_slug = "process-segment"

    def __init__(self, cfg: SimulatorConfig, client: MqttClient, **kwargs) -> None:
        super().__init__(cfg, client, **kwargs)
        self._scfg = cfg.process_segment_telemetry
        self._segments: list[dict] = []

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    def _init_segments(self) -> None:
        if self._segments:
            return

        # Explicit segments from config
        for s in self._scfg.segments:
            self._segments.append({
                "id": s.id,
                "type": s.type,
                "tempRange": s.temperature_range,
                "moistRange": s.moisture_range,
                "cycleRange": s.cycle_time_range,
            })

        # Auto-generated segments
        ag = self._scfg.auto_generate
        if ag.enabled:
            for i in range(ag.count):
                seg_id = f"SEG-{100 + i:03d}"
                seg_type = random.choice(ag.types)
                self._segments.append({
                    "id": seg_id,
                    "type": seg_type,
                    "tempRange": [80, 95],
                    "moistRange": [3.0, 5.0],
                    "cycleRange": [100, 120],
                })

        logger.info("ProcessSegmentTelemetry has %d active segments", len(self._segments))

    # ------------------------------------------------------------------
    # Overrides (anomaly injection)
    # ------------------------------------------------------------------
    _temp_override: list[float] | None = None

    def apply_overrides(self, overrides: dict) -> None:
        if "temperatureRange" in overrides:
            self._temp_override = overrides["temperatureRange"]

    def clear_overrides(self) -> None:
        self._temp_override = None

    # ------------------------------------------------------------------

    async def run(self) -> None:
        self._init_segments()
        interval = self._scfg.interval_sec
        logger.info("ProcessSegmentTelemetry started — every %ds", interval)

        while True:
            for seg in self._segments:
                tr = self._temp_override or seg["tempRange"]
                payload = {
                    "Timestamp": utcnow(),
                    "SegmentId": seg["id"],
                    "Temperature": rand_float(tr[0], tr[1]),
                    "MoistureContent": rand_float(seg["moistRange"][0], seg["moistRange"][1]),
                    "CycleTime": rand_float(seg["cycleRange"][0], seg["cycleRange"][1]),
                }
                await self.publish(payload, equipment_id=None)

            await asyncio.sleep(interval)
