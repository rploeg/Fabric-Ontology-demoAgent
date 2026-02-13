"""Stream 10 — Supply Chain Inbound Alerts."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..utils import utcnow, utcnow_dt, random_id, rand_float
from .base import BaseStream

logger = logging.getLogger(__name__)


@dataclass
class ShipmentRuntime:
    shipment_id: str
    tracking_num: str
    carrier: str
    origin_eqp: str
    dest_eqp: str
    material_ids: List[str]
    status: str
    original_eta: datetime
    revised_eta: datetime | None = None


class SupplyChainStream(BaseStream):
    stream_slug = "supply-chain"

    def __init__(self, cfg: SimulatorConfig, client: MqttClient) -> None:
        super().__init__(cfg, client)
        self._scfg = cfg.supply_chain_alerts
        self._shipments: List[ShipmentRuntime] = []

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    def _init_shipments(self) -> None:
        if self._shipments:
            return
        now = utcnow_dt()
        for s in self._scfg.active_shipments:
            eta = now + timedelta(days=random.randint(1, 7))
            self._shipments.append(ShipmentRuntime(
                shipment_id=s.shipment_id,
                tracking_num=s.tracking_num,
                carrier=s.carrier,
                origin_eqp=s.origin_equipment_id,
                dest_eqp=s.dest_equipment_id,
                material_ids=list(s.material_ids),
                status=s.initial_status,
                original_eta=eta,
            ))

    # Override support
    _force_status: str | None = None
    _force_risk: str | None = None

    def apply_overrides(self, overrides: dict) -> None:
        self._force_status = overrides.get("forceStatus")
        self._force_risk = overrides.get("riskLevel")

    def clear_overrides(self) -> None:
        self._force_status = None
        self._force_risk = None

    async def run(self) -> None:
        self._init_shipments()
        scfg = self._scfg
        status_flow = scfg.status_flow
        batches = self.cfg.simulation.active_batches
        batch_ids = [b.batch_id for b in batches] if batches else []

        logger.info("SupplyChainStream started — %d shipments, interval %d–%ds",
                     len(self._shipments), scfg.min_interval_sec, scfg.max_interval_sec)

        while True:
            wait = random.randint(scfg.min_interval_sec, scfg.max_interval_sec)
            await asyncio.sleep(wait)

            if not self._shipments:
                continue

            ship = random.choice(self._shipments)
            now = utcnow_dt()
            prev_status = ship.status

            # Determine next status
            if self._force_status:
                new_status = self._force_status
            else:
                try:
                    idx = status_flow.index(ship.status)
                    if idx < len(status_flow) - 1:
                        new_status = status_flow[idx + 1]
                    else:
                        # Delivered → restart cycle
                        new_status = status_flow[0]
                        ship.original_eta = now + timedelta(days=random.randint(2, 8))
                        ship.revised_eta = None
                except ValueError:
                    new_status = random.choice(status_flow)

            # Delay injection
            delay_reason = ""
            revised_eta = ship.revised_eta
            if random.random() < scfg.delay_probability and new_status not in ("Delivered", "Booked"):
                new_status = "Delayed"
                delay_reason = random.choice(scfg.delay_reasons)
                delay_days = random.randint(1, 5)
                revised_eta = (ship.revised_eta or ship.original_eta) + timedelta(days=delay_days)
                ship.revised_eta = revised_eta

            # Exception injection
            if random.random() < scfg.exception_probability:
                new_status = "Exception"

            ship.status = new_status

            # Risk level
            if self._force_risk:
                risk = self._force_risk
            elif new_status == "Exception":
                risk = "Critical"
            elif new_status == "Delayed":
                risk = "High"
            elif new_status in ("CustomsHold",):
                risk = "Medium"
            else:
                risk = "Low"

            # Impacted batches (simplified lookup)
            impacted = batch_ids[:2] if new_status in ("Delayed", "Exception") and batch_ids else []

            payload = {
                "Timestamp": utcnow(),
                "AlertId": random_id("SCA", now),
                "ShipmentId": ship.shipment_id,
                "TrackingNum": ship.tracking_num,
                "Carrier": ship.carrier,
                "Status": new_status,
                "PreviousStatus": prev_status,
                "OriginEquipmentId": ship.origin_eqp,
                "DestEquipmentId": ship.dest_eqp,
                "MaterialIds": ship.material_ids,
                "OriginalETA": ship.original_eta.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "RevisedETA": revised_eta.strftime("%Y-%m-%dT%H:%M:%SZ") if revised_eta else None,
                "DelayReason": delay_reason,
                "ImpactedBatches": impacted,
                "RiskLevel": risk,
            }

            await self.publish(payload, shipment_id=ship.shipment_id)
