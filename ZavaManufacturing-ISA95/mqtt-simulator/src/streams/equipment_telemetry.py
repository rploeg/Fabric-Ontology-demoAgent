"""Stream 1 — Equipment Telemetry (site-level)."""

from __future__ import annotations

import asyncio
import logging

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..utils import utcnow, rand_float, rand_int
from .base import BaseStream

logger = logging.getLogger(__name__)


class EquipmentTelemetryStream(BaseStream):
    stream_slug = "equipment"

    def __init__(self, cfg: SimulatorConfig, client: MqttClient) -> None:
        super().__init__(cfg, client)
        self._scfg = cfg.equipment_telemetry

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    async def run(self) -> None:
        interval = self._scfg.interval_sec
        logger.info("EquipmentTelemetry started — %d equipment, every %ds", len(self._scfg.equipment), interval)

        while True:
            for eq in self._scfg.equipment:
                # Production rate can be a fixed int or a [lo, hi] range
                if isinstance(eq.production_rate, list):
                    prod_rate = rand_float(eq.production_rate[0], eq.production_rate[1], 1)
                else:
                    prod_rate = float(eq.production_rate)

                payload = {
                    "Timestamp": utcnow(),
                    "EquipmentId": eq.id,
                    "EnergyConsumption": rand_float(eq.energy_range[0], eq.energy_range[1]),
                    "Humidity": rand_float(eq.humidity_range[0], eq.humidity_range[1]),
                    "ProductionRate": prod_rate,
                }

                await self.publish(payload, equipment_id=eq.id)

            await asyncio.sleep(interval)
