"""Stream 7 — Digital Twin State Sync (retained MQTT messages)."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Dict, List

from ..config import SimulatorConfig
from ..mqtt_client import MqttClient
from ..utils import utcnow, utcnow_dt, random_operator, weighted_choice, iter_machines, equipment_id as fmt_eqp
from .base import BaseStream

logger = logging.getLogger(__name__)


@dataclass
class TwinState:
    eqp_id: str
    line_name: str
    machine_name: str
    status: str = "Producing"
    sub_status: str = "NormalRun"
    last_change: str = ""


class DigitalTwinStream(BaseStream):
    stream_slug = "digital-twin"

    def __init__(self, cfg: SimulatorConfig, client: MqttClient, **kwargs) -> None:
        super().__init__(cfg, client, **kwargs)
        self._scfg = cfg.digital_twin_state_sync
        self._twins: List[TwinState] = []

    def is_enabled(self) -> bool:
        return self._scfg.enabled

    def _init_twins(self) -> None:
        if self._twins:
            return

        # Site-level equipment (EQP-001, 002, 003)
        for n in [1, 2, 3]:
            eid = fmt_eqp(n)
            self._twins.append(TwinState(
                eqp_id=eid, line_name="", machine_name=eid,
                status="Producing", last_change=utcnow(),
            ))

        # WorkUnit machines
        for eqp_id, line, name, _ in iter_machines():
            self._twins.append(TwinState(
                eqp_id=eqp_id, line_name=line, machine_name=name,
                status="Producing", last_change=utcnow(),
            ))

        logger.info("DigitalTwinStream: tracking %d entities", len(self._twins))

    async def run(self) -> None:
        self._init_twins()
        interval = self._scfg.heartbeat_interval_sec
        retain = self._scfg.retain_messages

        batches = self.cfg.simulation.active_batches
        recipes = {r.sku: r for r in self._scfg.recipes}

        probs = self._scfg.transition_probabilities
        states = list(probs.keys())
        weights = [probs[s] for s in states]

        _sub_statuses = {
            "Producing": "NormalRun",
            "ProducingAtRate": "RateOptimised",
            "Idle": "AwaitMaterial",
            "Setup": "RecipeLoad",
            "Maintenance": "PreventiveMaint",
            "Changeover": "ProductSwitch",
            "Blocked": "DownstreamFull",
            "ScheduledDowntime": "PlannedBreak",
            "UnscheduledDowntime": "FaultRecovery",
        }

        logger.info("DigitalTwinStream started — heartbeat every %ds, retain=%s", interval, retain)

        while True:
            for tw in self._twins:
                # Mirror state from machine-state stream via registry (B2: cross-stream correlation)
                reg_state = self.registry.get_machine_state(tw.eqp_id)
                if reg_state is not None:
                    machine_state = reg_state.state
                    # Map machine-state names to ISA-95 digital-twin statuses
                    _state_map = {
                        "Running": "Producing",
                        "Stopped": "UnscheduledDowntime",
                        "Blocked": "Blocked",
                        "Waiting": "Idle",
                        "Idle": "Idle",
                        "Maintenance": "Maintenance",
                    }
                    new_status = _state_map.get(machine_state, machine_state)
                    if new_status != tw.status:
                        tw.status = new_status
                        tw.sub_status = _sub_statuses.get(tw.status, "Unknown")
                        tw.last_change = utcnow()
                else:
                    # No machine-state data yet — use random transitions as before
                    if random.random() < 0.08:
                        tw.status = weighted_choice(states, weights)
                        tw.sub_status = _sub_statuses.get(tw.status, "Unknown")
                        tw.last_change = utcnow()

                batch = random.choice(batches) if batches else None
                sku = batch.sku if batch else "ZC Field Standard"
                recipe = recipes.get(sku)

                payload = {
                    "Timestamp": utcnow(),
                    "EquipmentId": tw.eqp_id,
                    "LineName": tw.line_name,
                    "MachineName": tw.machine_name,
                    "ISA95Status": tw.status,
                    "SubStatus": tw.sub_status,
                    "CurrentBatchId": batch.batch_id if batch else "",
                    "CurrentSKU": sku,
                    "Operator": random_operator(),
                    "RecipeId": recipe.recipe_id if recipe else "",
                    "TargetSpeedPct": recipe.target_speed_pct if recipe else 85,
                    "PlannedDowntimeMin": 0,
                    "LastStateChange": tw.last_change,
                }

                await self.publish(
                    payload,
                    retain=retain,
                    equipment_id=tw.eqp_id,
                    line_name=tw.line_name,
                    machine_name=tw.machine_name,
                )

            await asyncio.sleep(interval)
