"""Stream 5 — Safety Incident Events (camera-detected)."""

from __future__ import annotations

import asyncio
import logging
import random

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..utils import utcnow, utcnow_dt, random_id, rand_float, weighted_choice
from .base import BaseStream

logger = logging.getLogger(__name__)


class SafetyIncidentStream(BaseStream):
    stream_slug = "safety-incident"

    def __init__(self, cfg: SimulatorConfig, client: MqttClient) -> None:
        super().__init__(cfg, client)
        self._scfg = cfg.safety_incident_events

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    # Override support (anomaly injection — burst mode)
    _burst_count: int | None = None
    _min_override: int | None = None
    _max_override: int | None = None

    def apply_overrides(self, overrides: dict) -> None:
        self._burst_count = overrides.get("burstCount")
        self._min_override = overrides.get("minIntervalSec")
        self._max_override = overrides.get("maxIntervalSec")

    def clear_overrides(self) -> None:
        self._burst_count = None
        self._min_override = None
        self._max_override = None

    async def run(self) -> None:
        logger.info("SafetyIncidentStream started — %d cameras, interval %d–%ds",
                     len(self._scfg.cameras), self._scfg.min_interval_sec, self._scfg.max_interval_sec)

        while True:
            min_iv = self._min_override if self._min_override is not None else self._scfg.min_interval_sec
            max_iv = self._max_override if self._max_override is not None else self._scfg.max_interval_sec
            burst = self._burst_count or 1
            for _ in range(burst):
                wait = random.randint(min_iv, max(min_iv, max_iv))
                await asyncio.sleep(wait)

            if not self._scfg.cameras or not self._scfg.incident_types:
                continue

            camera = random.choice(self._scfg.cameras)
            now = utcnow_dt()

            # Weighted incident type selection
            types = self._scfg.incident_types
            incident = weighted_choice(
                [t.type for t in types],
                [t.weight for t in types],
            )
            incident_def = next(t for t in types if t.type == incident)

            # Pick description and fill in zone
            desc = random.choice(incident_def.descriptions) if incident_def.descriptions else incident
            desc = desc.replace("{zone}", camera.zone)

            confidence = rand_float(
                self._scfg.confidence_range[0],
                self._scfg.confidence_range[1],
                2,
            )

            image_ref = self._scfg.image_ref_template.format(
                year=now.strftime("%Y"),
                month=now.strftime("%m"),
                day=now.strftime("%d"),
                cameraId=camera.id,
                timestamp=now.strftime("%H%M%S"),
            )

            payload = {
                "Timestamp": utcnow(),
                "IncidentId": random_id("INC", now),
                "CameraId": camera.id,
                "EquipmentId": camera.equipment_id,
                "Zone": camera.zone,
                "IncidentType": incident,
                "Severity": incident_def.severity,
                "Description": desc,
                "Confidence": confidence,
                "ImageRef": image_ref,
            }

            await self.publish(payload, equipment_id=camera.equipment_id)
