"""Abstract base class for all simulator streams."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..state_registry import StateRegistry
from ..utils import resolve_uns_topic

logger = logging.getLogger(__name__)


class BaseStream(ABC):
    """
    Every stream subclass must implement:

    - ``stream_slug``  — e.g. ``"equipment"``
    - ``is_enabled()`` — check config flag
    - ``run()``        — the main asyncio publishing loop
    """

    def __init__(
        self,
        cfg: SimulatorConfig,
        client: MqttClient,
        *,
        registry: StateRegistry | None = None,
    ) -> None:
        self.cfg = cfg
        self.client = client
        self.registry: StateRegistry = registry or StateRegistry()

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def stream_slug(self) -> str:
        """Short kebab-case name used in topic paths (e.g. ``'machine-state'``)."""
        ...

    @abstractmethod
    def is_enabled(self) -> bool:
        ...

    @abstractmethod
    async def run(self) -> None:
        """Main coroutine — publish messages in a loop until cancelled."""
        ...

    # ------------------------------------------------------------------
    # Topic resolution helpers
    # ------------------------------------------------------------------

    def flat_topic(self) -> str:
        """Return the flat (single) topic configured for this stream."""
        # Each stream config has its own ``topic`` field.  Subclasses can
        # override if they decide the topic dynamically.
        return self._stream_topic_field()

    def uns_topic(
        self,
        *,
        equipment_id: str | None = None,
        line_name: str | None = None,
        machine_name: str | None = None,
        station_id: str | None = None,
        shipment_id: str | None = None,
    ) -> str:
        """Build the hierarchical UNS topic for a specific entity."""
        return resolve_uns_topic(
            self.cfg.uns,
            stream_slug=self.stream_slug,
            equipment_id_val=equipment_id,
            line_name=line_name,
            machine_name_val=machine_name,
            station_id=station_id,
            shipment_id=shipment_id,
        )

    def resolve_topic(
        self,
        *,
        equipment_id: str | None = None,
        line_name: str | None = None,
        machine_name: str | None = None,
        station_id: str | None = None,
        shipment_id: str | None = None,
    ) -> str:
        """
        Return the correct topic depending on ``topicMode``.

        * ``flat``  → the stream's configured topic string
        * ``uns``   → ISA-95 hierarchical path
        """
        if self.cfg.topic_mode == "uns":
            return self.uns_topic(
                equipment_id=equipment_id,
                line_name=line_name,
                machine_name=machine_name,
                station_id=station_id,
                shipment_id=shipment_id,
            )
        return self.flat_topic()

    # ------------------------------------------------------------------
    # Publishing helper
    # ------------------------------------------------------------------

    async def publish(
        self,
        payload: Dict[str, Any],
        *,
        topic: str | None = None,
        retain: bool = False,
        equipment_id: str | None = None,
        line_name: str | None = None,
        machine_name: str | None = None,
        station_id: str | None = None,
        shipment_id: str | None = None,
    ) -> None:
        """Resolve the topic and publish ``payload`` as JSON."""
        t = topic or self.resolve_topic(
            equipment_id=equipment_id,
            line_name=line_name,
            machine_name=machine_name,
            station_id=station_id,
            shipment_id=shipment_id,
        )
        await self.client.publish(t, payload, retain=retain)
        logger.debug("[%s] → %s", self.stream_slug, t)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _stream_topic_field(self) -> str:
        """Read the ``topic`` field from the per-stream config section."""
        # Convention: stream_slug maps to a config attribute with a ``topic`` field.
        mapping: Dict[str, str] = {
            "equipment": "equipment_telemetry",
            "machine-state": "machine_state_telemetry",
            "process-segment": "process_segment_telemetry",
            "production-counter": "production_counter_telemetry",
            "safety-incident": "safety_incident_events",
            "predictive-maintenance": "predictive_maintenance_signals",
            "digital-twin": "digital_twin_state_sync",
            "material-consumption": "material_consumption_events",
            "quality-vision": "quality_vision_events",
            "supply-chain": "supply_chain_alerts",
            "batch-lifecycle": "batch_lifecycle",
        }
        attr = mapping.get(self.stream_slug)
        if attr:
            section = getattr(self.cfg, attr, None)
            if section and hasattr(section, "topic"):
                return section.topic
        return f"{self.cfg.topic_prefix}/{self.stream_slug}"
