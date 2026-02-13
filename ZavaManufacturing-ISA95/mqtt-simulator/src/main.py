"""Zava MQTT Simulator — main entrypoint.

Usage:
    python -m src.main                              # default config path
    python -m src.main --config /etc/simulator/simulator-config.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List

from .config import SimulatorConfig, load_config
from .mqtt_client import MqttClient
from .anomaly_engine import AnomalyEngine
from .command_handler import CommandHandler
from .streams.base import BaseStream
from .streams.equipment_telemetry import EquipmentTelemetryStream
from .streams.machine_state import MachineStateTelemetryStream
from .streams.process_segment import ProcessSegmentTelemetryStream
from .streams.production_counter import ProductionCounterTelemetryStream
from .streams.safety_incident import SafetyIncidentStream
from .streams.predictive_maintenance import PredictiveMaintenanceStream
from .streams.digital_twin import DigitalTwinStream
from .streams.material_consumption import MaterialConsumptionStream
from .streams.quality_vision import QualityVisionStream
from .streams.supply_chain import SupplyChainStream

logger = logging.getLogger("zava-simulator")

# Default config search paths
_CONFIG_SEARCH = [
    Path("/etc/simulator/simulator-config.yaml"),
    Path("simulator-config.yaml"),
]


def _setup_logging(cfg: SimulatorConfig) -> None:
    level = getattr(logging, cfg.logging.level, logging.INFO)
    fmt = cfg.logging.format

    if fmt == "json":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        ))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        })


def _build_streams(cfg: SimulatorConfig, client: MqttClient) -> Dict[str, BaseStream]:
    """Instantiate all stream classes, keyed by stream_slug."""
    all_streams: List[BaseStream] = [
        EquipmentTelemetryStream(cfg, client),
        MachineStateTelemetryStream(cfg, client),
        ProcessSegmentTelemetryStream(cfg, client),
        ProductionCounterTelemetryStream(cfg, client),
        SafetyIncidentStream(cfg, client),
        PredictiveMaintenanceStream(cfg, client),
        DigitalTwinStream(cfg, client),
        MaterialConsumptionStream(cfg, client),
        QualityVisionStream(cfg, client),
        SupplyChainStream(cfg, client),
    ]
    return {s.stream_slug: s for s in all_streams}


async def _metrics_loop(cfg: SimulatorConfig, client: MqttClient, start: float) -> None:
    """Periodically log throughput metrics."""
    if not cfg.logging.publish_metrics:
        return
    interval = cfg.logging.metrics_interval_sec
    while True:
        await asyncio.sleep(interval)
        elapsed = time.monotonic() - start
        rate = client.message_count / elapsed if elapsed > 0 else 0
        logger.info(
            "Metrics: %d messages sent (%.1f msg/s, uptime %.0fs)",
            client.message_count,
            rate,
            elapsed,
        )


async def run(cfg: SimulatorConfig) -> None:
    """Core async entrypoint."""
    client = MqttClient(cfg.mqtt)
    await client.connect()

    streams = _build_streams(cfg, client)
    anomaly = AnomalyEngine(cfg, client, streams)
    cmd_handler = CommandHandler(cfg, client, streams, anomaly, start_time=time.monotonic())

    # Log which streams are enabled
    enabled = [slug for slug, s in streams.items() if s.is_enabled()]
    disabled = [slug for slug, s in streams.items() if not s.is_enabled()]
    logger.info("Enabled streams (%d): %s", len(enabled), ", ".join(enabled))
    if disabled:
        logger.info("Disabled streams (%d): %s", len(disabled), ", ".join(disabled))
    logger.info("Topic mode: %s", cfg.topic_mode)

    tasks: List[asyncio.Task] = []
    start_time = time.monotonic()

    # Start enabled streams
    for slug in enabled:
        stream = streams[slug]
        tasks.append(asyncio.create_task(stream.run(), name=f"stream-{slug}"))

    # Start anomaly engine
    if anomaly.is_enabled():
        tasks.append(asyncio.create_task(anomaly.run(), name="anomaly-engine"))

    # Start metrics logger
    tasks.append(asyncio.create_task(_metrics_loop(cfg, client, start_time), name="metrics"))

    # Start command handler
    tasks.append(asyncio.create_task(cmd_handler.run(), name="command-handler"))

    logger.info("Simulator running — %d tasks started", len(tasks))

    # Handle shutdown
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await stop.wait()

    # Cancel all tasks
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    await client.disconnect()
    logger.info("Simulator stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Zava MQTT Simulator")
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to simulator-config.yaml",
    )
    args = parser.parse_args()

    # Find config
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = next((p for p in _CONFIG_SEARCH if p.exists()), None)

    if config_path and config_path.exists():
        logger.info("Loading config from %s", config_path)
        cfg = load_config(config_path)
    else:
        logger.warning("No config file found — using defaults")
        cfg = SimulatorConfig()

    _setup_logging(cfg)

    logger.info("=" * 60)
    logger.info("Zava MQTT Simulator starting")
    logger.info("Broker: %s:%d", cfg.mqtt.broker, cfg.mqtt.port)
    logger.info("Topic mode: %s", cfg.topic_mode)
    logger.info("=" * 60)

    asyncio.run(run(cfg))


if __name__ == "__main__":
    main()
