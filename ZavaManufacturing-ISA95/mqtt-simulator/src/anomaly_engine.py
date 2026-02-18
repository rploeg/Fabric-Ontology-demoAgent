"""Anomaly Engine — periodic injection of anomaly scenarios across streams."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Dict, List

from .config import AnomalyConfig, AnomalyScenario, SimulatorConfig
from .streams.base import MessageSink
from .streams.base import BaseStream
from .utils import utcnow, random_id, utcnow_dt

logger = logging.getLogger(__name__)

# Maps scenario.stream → config attribute name → stream class
_STREAM_ATTR_MAP: Dict[str, str] = {
    "equipmentTelemetry": "equipment",
    "processSegmentTelemetry": "process-segment",
    "productionCounterTelemetry": "production-counter",
    "machineStateTelemetry": "machine-state",
    "predictiveMaintenanceSignals": "predictive-maintenance",
    "materialConsumptionEvents": "material-consumption",
    "qualityVisionEvents": "quality-vision",
    "supplyChainAlerts": "supply-chain",
    "safetyIncidentEvents": "safety-incident",
    "batchLifecycle": "batch-lifecycle",
}


class AnomalyEngine:
    """
    Periodically picks an enabled anomaly scenario, applies overrides to
    the target stream for the configured duration, publishes an anomaly
    event to the anomaly topic, then reverts.
    """

    def __init__(
        self,
        cfg: SimulatorConfig,
        client: MessageSink,
        streams: Dict[str, BaseStream],
    ) -> None:
        self._cfg = cfg
        self._client = client
        self._streams = streams  # keyed by stream_slug
        self._acfg: AnomalyConfig = cfg.anomalies

    def is_enabled(self) -> bool:
        return self._acfg.enabled

    async def run(self) -> None:
        if not self.is_enabled():
            return

        enabled_scenarios = [s for s in self._acfg.scenarios if s.enabled]
        if not enabled_scenarios:
            logger.info("AnomalyEngine: no enabled scenarios — exiting")
            return

        interval = self._acfg.scenario_interval_min * 60
        logger.info(
            "AnomalyEngine started — %d scenarios enabled, interval %d min",
            len(enabled_scenarios),
            self._acfg.scenario_interval_min,
        )

        while True:
            # Wait for the next anomaly window
            jitter = random.randint(0, max(1, interval // 4))
            await asyncio.sleep(interval + jitter)

            # Pick a random enabled scenario
            scenario = random.choice(enabled_scenarios)
            await self._execute_scenario(scenario)

    async def _execute_scenario(self, scenario: AnomalyScenario) -> None:
        stream_slug = _STREAM_ATTR_MAP.get(scenario.stream, scenario.stream)
        stream = self._streams.get(stream_slug)

        logger.warning(
            "ANOMALY [%s]: %s — duration %ds, target stream=%s",
            scenario.name,
            scenario.description,
            scenario.duration_sec,
            stream_slug,
        )

        # Publish anomaly start event
        topic = scenario.topic or self._acfg.default_topic
        now = utcnow_dt()
        event = {
            "Timestamp": utcnow(),
            "AnomalyId": random_id("ANO", now),
            "Scenario": scenario.name,
            "Description": scenario.description,
            "Stream": stream_slug,
            "DurationSec": scenario.duration_sec,
            "Phase": "START",
            "Overrides": scenario.overrides,
        }
        await self._client.publish(topic, event)

        # Apply overrides to the stream (Q9: uses BaseStream ABC method)
        if stream:
            stream.apply_overrides(scenario.overrides)

        # For duration-based scenarios, wait then revert
        if scenario.duration_sec > 0:
            await asyncio.sleep(scenario.duration_sec)

            if stream:
                stream.clear_overrides()

            # Publish anomaly end event
            end_event = {
                "Timestamp": utcnow(),
                "AnomalyId": event["AnomalyId"],
                "Scenario": scenario.name,
                "Description": scenario.description,
                "Stream": stream_slug,
                "DurationSec": scenario.duration_sec,
                "Phase": "END",
                "Overrides": {},
            }
            await self._client.publish(topic, end_event)

            logger.info("ANOMALY [%s]: ended — overrides reverted", scenario.name)
