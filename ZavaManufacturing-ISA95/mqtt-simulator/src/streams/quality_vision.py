"""Stream 9 — Quality Vision Inspection Events."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Dict, List

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..utils import (
    utcnow, utcnow_dt, random_id, rand_float, random_serial,
    weighted_choice,
)
from .base import BaseStream

logger = logging.getLogger(__name__)


class QualityVisionStream(BaseStream):
    stream_slug = "quality-vision"

    def __init__(self, cfg: SimulatorConfig, client: MqttClient, **kwargs) -> None:
        super().__init__(cfg, client, **kwargs)
        self._scfg = cfg.quality_vision_events

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    # Override support
    _pass_override: float | None = None
    _marginal_override: float | None = None
    _confidence_override: list | None = None

    def apply_overrides(self, overrides: dict) -> None:
        self._pass_override = overrides.get("passRate")
        self._marginal_override = overrides.get("marginalRate")
        self._confidence_override = overrides.get("confidenceRange")

    def clear_overrides(self) -> None:
        self._pass_override = None
        self._marginal_override = None
        self._confidence_override = None

    async def run(self) -> None:
        scfg = self._scfg
        batches = self.cfg.simulation.active_batches
        batch_ids = [b.batch_id for b in batches] if batches else ["BTC-000"]
        skus = [b.sku for b in batches] if batches else ["ZC Field Standard"]

        defect_types = scfg.defect_types
        defect_names = [d.type for d in defect_types]
        defect_weights = [d.weight for d in defect_types]

        logger.info("QualityVisionStream started — %d stations, every %ds",
                     len(scfg.stations), scfg.interval_sec)

        while True:
            for station in scfg.stations:
                now = utcnow_dt()
                batch_id = random.choice(batch_ids)
                sku = random.choice(skus)

                # Determine result
                pass_rate = self._pass_override if self._pass_override is not None else scfg.pass_rate
                marginal_rate = self._marginal_override if self._marginal_override is not None else scfg.marginal_rate
                roll = random.random()
                if roll < pass_rate:
                    result = "Pass"
                elif roll < pass_rate + marginal_rate:
                    result = "Marginal"
                else:
                    result = "Fail"

                defect_type = ""
                defect_location: Dict | None = None
                if result in ("Fail", "Marginal"):
                    defect_type = weighted_choice(defect_names, defect_weights) if defect_names else "unknown"
                    defect_location = {
                        "x": random.randint(0, 640),
                        "y": random.randint(0, 480),
                        "w": random.randint(10, 80),
                        "h": random.randint(10, 60),
                    }

                conf_range = self._confidence_override or scfg.confidence_range
                confidence = rand_float(
                    conf_range[0], conf_range[1], 2
                )

                image_ref = scfg.image_ref_template.format(
                    year=now.strftime("%Y"),
                    month=now.strftime("%m"),
                    day=now.strftime("%d"),
                    stationId=station.id,
                    timestamp=now.strftime("%H%M%S"),
                )

                payload = {
                    "Timestamp": utcnow(),
                    "InspectionId": random_id("VIS", now),
                    "StationId": station.id,
                    "EquipmentId": station.equipment_id,
                    "LineName": station.line_name,
                    "BatchId": batch_id,
                    "UnitSerial": random_serial(sku, batch_id),
                    "Result": result,
                    "DefectType": defect_type,
                    "DefectLocation": defect_location,
                    "Confidence": confidence,
                    "ImageRef": image_ref,
                    "ModelVersion": scfg.model_version,
                }

                await self.publish(
                    payload,
                    equipment_id=station.equipment_id,
                    line_name=station.line_name,
                    station_id=station.id,
                )

            await asyncio.sleep(scfg.interval_sec)
