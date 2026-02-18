"""MQTT Command Handler — remote control of the simulator via MQTT commands.

Subscribe to ``zava/simulator/command`` and respond on ``zava/simulator/status``.

Supported commands (JSON payloads published to the command topic):

    {"action": "status"}
    {"action": "enable",  "stream": "equipment"}
    {"action": "disable", "stream": "equipment"}
    {"action": "set-interval", "stream": "equipment", "intervalSec": 5}
    {"action": "trigger-anomaly", "scenario": "temperature_spike"}
    {"action": "set", "path": "anomalies.scenarioIntervalMin", "value": 1}
    {"action": "list-streams"}
    {"action": "list-anomalies"}
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from .config import SimulatorConfig
from .streams.base import MessageSink
from .streams.base import BaseStream
from .anomaly_engine import AnomalyEngine
from .utils import utcnow

logger = logging.getLogger(__name__)

COMMAND_TOPIC = "zava/simulator/command"
STATUS_TOPIC = "zava/simulator/status"

# Maps stream slug → config attribute name on SimulatorConfig
_SLUG_TO_ATTR: Dict[str, str] = {
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


class CommandHandler:
    """Listens for MQTT commands and adjusts simulator behaviour at runtime."""

    def __init__(
        self,
        cfg: SimulatorConfig,
        client: MessageSink,
        streams: Dict[str, BaseStream],
        anomaly: AnomalyEngine,
        start_time: float,
    ) -> None:
        self._cfg = cfg
        self._client = client
        self._streams = streams
        self._anomaly = anomaly
        self._start_time = start_time
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stream_tasks: Dict[str, asyncio.Task] = {}  # B2: track re-enabled tasks

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Subscribe to the command topic and start processing."""
        self._client.subscribe(COMMAND_TOPIC, callback=self._on_message)
        logger.info("CommandHandler listening on %s", COMMAND_TOPIC)

    async def run(self) -> None:
        """Process commands from the queue forever."""
        self._loop = asyncio.get_running_loop()  # B1: own loop reference
        await self.start()
        while True:
            cmd = await self._queue.get()
            try:
                resp = await self._handle(cmd)
                await self._client.publish(STATUS_TOPIC, resp)
            except Exception as exc:
                logger.error("Command error: %s", exc)
                await self._client.publish(STATUS_TOPIC, {
                    "Timestamp": utcnow(),
                    "status": "error",
                    "error": str(exc),
                    "command": cmd,
                })

    # ------------------------------------------------------------------
    # MQTT callback (runs on paho thread)
    # ------------------------------------------------------------------

    def _on_message(self, payload_str: str) -> None:
        """Called from the paho thread — put work into the async queue."""
        try:
            cmd = json.loads(payload_str)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON command received: %s", payload_str[:200])
            return
        # Schedule on the event loop (B1: use own _loop, not client._loop)
        loop = self._loop
        if loop:
            loop.call_soon_threadsafe(self._queue.put_nowait, cmd)

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    async def _handle(self, cmd: dict) -> dict:
        action = cmd.get("action", "").lower().strip()
        handler = {
            "status": self._cmd_status,
            "list-streams": self._cmd_list_streams,
            "list-anomalies": self._cmd_list_anomalies,
            "enable": self._cmd_enable,
            "disable": self._cmd_disable,
            "set-interval": self._cmd_set_interval,
            "trigger-anomaly": self._cmd_trigger_anomaly,
            "set": self._cmd_set,
        }.get(action)

        if handler is None:
            return {
                "Timestamp": utcnow(),
                "status": "error",
                "error": f"Unknown action: {action!r}",
                "availableActions": list({
                    "status", "list-streams", "list-anomalies",
                    "enable", "disable", "set-interval",
                    "trigger-anomaly", "set",
                }),
            }
        return await handler(cmd)

    # ------------------------------------------------------------------
    # Individual command handlers
    # ------------------------------------------------------------------

    async def _cmd_status(self, _cmd: dict) -> dict:
        elapsed = time.monotonic() - self._start_time
        stream_info = {}
        for slug, s in self._streams.items():
            attr = _SLUG_TO_ATTR.get(slug)
            scfg = getattr(self._cfg, attr) if attr else None
            interval = getattr(scfg, "interval_sec", None)
            stream_info[slug] = {
                "enabled": s.is_enabled(),
                **({"intervalSec": interval} if interval is not None else {}),
            }

        return {
            "Timestamp": utcnow(),
            "status": "ok",
            "action": "status",
            "uptime_sec": round(elapsed),
            "messages_published": self._client.message_count,
            "msg_per_sec": round(self._client.message_count / elapsed, 1) if elapsed > 0 else 0,
            "topic_mode": self._cfg.topic_mode,
            "broker": f"{self._cfg.mqtt.broker}:{self._cfg.mqtt.port}",
            "anomalies_enabled": self._cfg.anomalies.enabled,
            "anomaly_interval_min": self._cfg.anomalies.scenario_interval_min,
            "streams": stream_info,
        }

    async def _cmd_list_streams(self, _cmd: dict) -> dict:
        streams = []
        for slug, s in self._streams.items():
            attr = _SLUG_TO_ATTR.get(slug)
            scfg = getattr(self._cfg, attr) if attr else None
            streams.append({
                "slug": slug,
                "enabled": s.is_enabled(),
                "topic": getattr(scfg, "topic", None),
                "intervalSec": getattr(scfg, "interval_sec", None),
            })
        return {
            "Timestamp": utcnow(),
            "status": "ok",
            "action": "list-streams",
            "streams": streams,
        }

    async def _cmd_list_anomalies(self, _cmd: dict) -> dict:
        scenarios = []
        for s in self._cfg.anomalies.scenarios:
            scenarios.append({
                "name": s.name,
                "enabled": s.enabled,
                "stream": s.stream,
                "durationSec": s.duration_sec,
                "description": s.description,
            })
        return {
            "Timestamp": utcnow(),
            "status": "ok",
            "action": "list-anomalies",
            "anomalies_enabled": self._cfg.anomalies.enabled,
            "interval_min": self._cfg.anomalies.scenario_interval_min,
            "scenarios": scenarios,
        }

    async def _cmd_enable(self, cmd: dict) -> dict:
        slug = cmd.get("stream", "")
        attr = _SLUG_TO_ATTR.get(slug)
        if not attr:
            return self._err(f"Unknown stream: {slug!r}", cmd)

        scfg = getattr(self._cfg, attr)
        if scfg.enabled:
            return {
                "Timestamp": utcnow(), "status": "ok", "action": "enable",
                "stream": slug, "message": "already enabled",
            }

        scfg.enabled = True
        # Restart the stream task
        stream = self._streams.get(slug)
        if stream:
            task = asyncio.create_task(stream.safe_run(), name=f"stream-{slug}")
            self._stream_tasks[slug] = task
            logger.info("Stream %s enabled and restarted", slug)

        return {
            "Timestamp": utcnow(), "status": "ok", "action": "enable",
            "stream": slug, "message": "enabled",
        }

    async def _cmd_disable(self, cmd: dict) -> dict:
        slug = cmd.get("stream", "")
        attr = _SLUG_TO_ATTR.get(slug)
        if not attr:
            return self._err(f"Unknown stream: {slug!r}", cmd)

        scfg = getattr(self._cfg, attr)
        if not scfg.enabled:
            return {
                "Timestamp": utcnow(), "status": "ok", "action": "disable",
                "stream": slug, "message": "already disabled",
            }

        scfg.enabled = False
        # Cancel running task
        for task in asyncio.all_tasks():
            if task.get_name() == f"stream-{slug}":
                task.cancel()
                logger.info("Stream %s disabled and cancelled", slug)
                break

        return {
            "Timestamp": utcnow(), "status": "ok", "action": "disable",
            "stream": slug, "message": "disabled",
        }

    async def _cmd_set_interval(self, cmd: dict) -> dict:
        slug = cmd.get("stream", "")
        interval = cmd.get("intervalSec")
        if interval is None:
            return self._err("Missing 'intervalSec'", cmd)

        attr = _SLUG_TO_ATTR.get(slug)
        if not attr:
            return self._err(f"Unknown stream: {slug!r}", cmd)

        scfg = getattr(self._cfg, attr)

        # Resolve the correct interval field name for this stream
        if hasattr(scfg, "interval_sec"):
            field = "interval_sec"
        elif hasattr(scfg, "heartbeat_interval_sec"):
            field = "heartbeat_interval_sec"
        elif hasattr(scfg, "min_interval_sec"):
            # Event-based streams (safety-incident, material-consumption, supply-chain)
            old_min = scfg.min_interval_sec
            old_max = scfg.max_interval_sec
            scfg.min_interval_sec = int(interval)
            scfg.max_interval_sec = max(int(interval), scfg.max_interval_sec)
            logger.info("Stream %s interval changed: %d–%ds → %d–%ds",
                        slug, old_min, old_max, scfg.min_interval_sec, scfg.max_interval_sec)
            return {
                "Timestamp": utcnow(), "status": "ok", "action": "set-interval",
                "stream": slug,
                "old_min_interval_sec": old_min, "old_max_interval_sec": old_max,
                "new_min_interval_sec": scfg.min_interval_sec,
                "new_max_interval_sec": scfg.max_interval_sec,
                "note": "Takes effect at next publish cycle",
            }
        else:
            return self._err(f"Stream {slug!r} does not have an interval setting", cmd)

        old = getattr(scfg, field)
        setattr(scfg, field, int(interval))
        new = getattr(scfg, field)
        logger.info("Stream %s %s changed: %ds → %ds", slug, field, old, new)

        return {
            "Timestamp": utcnow(), "status": "ok", "action": "set-interval",
            "stream": slug, "old_interval_sec": old, "new_interval_sec": new,
            "note": "Takes effect at next publish cycle",
        }

    async def _cmd_trigger_anomaly(self, cmd: dict) -> dict:
        scenario_name = cmd.get("scenario", "")
        scenario = next(
            (s for s in self._cfg.anomalies.scenarios if s.name == scenario_name),
            None,
        )
        if not scenario:
            available = [s.name for s in self._cfg.anomalies.scenarios]
            return self._err(
                f"Unknown scenario: {scenario_name!r}. Available: {available}", cmd
            )

        # Fire the anomaly in the background
        asyncio.create_task(
            self._anomaly._execute_scenario(scenario),
            name=f"manual-anomaly-{scenario_name}",
        )
        logger.warning("Manual anomaly triggered: %s", scenario_name)

        return {
            "Timestamp": utcnow(), "status": "ok", "action": "trigger-anomaly",
            "scenario": scenario_name,
            "duration_sec": scenario.duration_sec,
            "message": f"Anomaly '{scenario_name}' triggered — will run for {scenario.duration_sec}s",
        }

    async def _cmd_set(self, cmd: dict) -> dict:
        path = cmd.get("path", "")
        value = cmd.get("value")
        if not path or value is None:
            return self._err("Missing 'path' and/or 'value'", cmd)

        # Navigate the dot-separated path
        parts = path.split(".")
        obj: Any = self._cfg
        for part in parts[:-1]:
            obj = getattr(obj, part, None)
            if obj is None:
                return self._err(f"Invalid path: {path!r} (no attr '{part}')", cmd)

        final = parts[-1]
        if not hasattr(obj, final):
            return self._err(f"Invalid path: {path!r} (no attr '{final}')", cmd)

        old = getattr(obj, final)
        # B3: safe type coercion — only coerce scalars, pass through
        # lists/dicts/None as-is to avoid type(old)(value) crashes.
        if old is None or isinstance(old, (list, dict)):
            new_value = value
        else:
            try:
                new_value = type(old)(value)
            except (TypeError, ValueError) as exc:
                return self._err(
                    f"Cannot convert {value!r} to {type(old).__name__}: {exc}", cmd
                )
        setattr(obj, final, new_value)
        new = getattr(obj, final)
        logger.info("Config set: %s = %s (was %s)", path, new, old)

        return {
            "Timestamp": utcnow(), "status": "ok", "action": "set",
            "path": path, "old_value": old, "new_value": new,
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _err(msg: str, cmd: dict) -> dict:
        return {"Timestamp": utcnow(), "status": "error", "error": msg, "command": cmd}
