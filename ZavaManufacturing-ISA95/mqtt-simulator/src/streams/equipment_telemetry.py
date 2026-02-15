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

    def __init__(self, cfg: SimulatorConfig, client: MqttClient, **kwargs) -> None:
        super().__init__(cfg, client, **kwargs)
        self._scfg = cfg.equipment_telemetry

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    # Override support (anomaly injection)
    _energy_override: list | None = None
    _humidity_override: list | None = None

    def apply_overrides(self, overrides: dict) -> None:
        self._energy_override = overrides.get("energyRange")
        self._humidity_override = overrides.get("humidityRange")

    def clear_overrides(self) -> None:
        self._energy_override = None
        self._humidity_override = None

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

                e_range = self._energy_override or eq.energy_range
                h_range = self._humidity_override or eq.humidity_range

                payload = {
                    "Timestamp": utcnow(),
                    "EquipmentId": eq.id,
                    "EnergyConsumption": rand_float(e_range[0], e_range[1]),
                    "Humidity": rand_float(h_range[0], h_range[1]),
                    "ProductionRate": prod_rate,
                }

                await self.publish(payload, equipment_id=eq.id)

            await asyncio.sleep(interval)
