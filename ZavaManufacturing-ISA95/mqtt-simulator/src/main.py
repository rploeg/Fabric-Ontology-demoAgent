"""Zava MQTT Simulator — main entrypoint.

Usage:
    python -m src.main                              # default config path
    python -m src.main --config /etc/simulator/simulator-config.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from .config import SimulatorConfig, load_config
from .mqtt_client import MqttClient
from .eventhub_client import EventHubClient
from .anomaly_engine import AnomalyEngine
from .command_handler import CommandHandler
from .state_registry import StateRegistry
from .site_cloner import clone_config_for_site
from .streams.base import BaseStream, MessageSink
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
from .streams.batch_lifecycle import BatchLifecycleStream

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


def _build_streams(
    cfg: SimulatorConfig,
    client: MessageSink,
    registry: StateRegistry,
) -> Dict[str, BaseStream]:
    """Instantiate all stream classes, keyed by stream_slug."""
    all_streams: List[BaseStream] = [
        EquipmentTelemetryStream(cfg, client, registry=registry),
        MachineStateTelemetryStream(cfg, client, registry=registry),
        ProcessSegmentTelemetryStream(cfg, client, registry=registry),
        ProductionCounterTelemetryStream(cfg, client, registry=registry),
        SafetyIncidentStream(cfg, client, registry=registry),
        PredictiveMaintenanceStream(cfg, client, registry=registry),
        DigitalTwinStream(cfg, client, registry=registry),
        MaterialConsumptionStream(cfg, client, registry=registry),
        QualityVisionStream(cfg, client, registry=registry),
        SupplyChainStream(cfg, client, registry=registry),
        BatchLifecycleStream(cfg, client, registry=registry),
    ]
    return {s.stream_slug: s for s in all_streams}


def _file_hash(path: Path) -> Optional[str]:
    """Return SHA-256 hex digest of a file, or None if unreadable."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


async def _config_watcher(
    config_path: Optional[Path],
    reload_event: asyncio.Event,
    *,
    poll_sec: float = 2.0,
) -> None:
    """Poll the config file for changes and signal a reload when it changes."""
    if config_path is None or not config_path.exists():
        return  # no file to watch

    last_hash = _file_hash(config_path)
    logger.info("Config watcher: monitoring %s (poll every %.0fs)", config_path, poll_sec)

    while True:
        await asyncio.sleep(poll_sec)
        current_hash = _file_hash(config_path)
        if current_hash and current_hash != last_hash:
            logger.info(
                "Config watcher: %s changed on disk — triggering reload",
                config_path,
            )
            reload_event.set()
            return


async def _metrics_loop(cfg: SimulatorConfig, client: MessageSink, start: float) -> None:
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


async def run(cfg: SimulatorConfig, config_path: Optional[Path] = None) -> bool:
    """Core async entrypoint.

    Returns ``True`` if the simulator should reload with a fresh config,
    ``False`` for a normal shutdown.
    """
    reload_event = asyncio.Event()

    # ------ Choose output sink based on outputMode ------
    client: MessageSink
    if cfg.output_mode == "eventHub":
        logger.info("Output mode: Azure Event Hub")
        client = EventHubClient(cfg.eventhub)
    else:
        logger.info("Output mode: MQTT broker")
        client = MqttClient(cfg.mqtt)
    await client.connect()

    registry = StateRegistry()
    streams = _build_streams(cfg, client, registry)
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

    # Start enabled streams (primary site)
    for slug in enabled:
        stream = streams[slug]
        tasks.append(asyncio.create_task(stream.run(), name=f"stream-{slug}"))

    # ── Multi-site: clone streams for each additional site ────────
    site_streams: Dict[str, Dict[str, BaseStream]] = {}
    if cfg.multi_site.enabled and cfg.multi_site.sites:
        for site_prof in cfg.multi_site.sites:
            site_cfg = clone_config_for_site(cfg, site_prof)
            site_reg = StateRegistry()
            s_streams = _build_streams(site_cfg, client, site_reg)
            site_streams[site_prof.site_id] = s_streams

            # Filter by enabledStreams if specified
            allowed = set(site_prof.enabled_streams) if site_prof.enabled_streams else None
            s_enabled = [
                slug for slug, s in s_streams.items()
                if s.is_enabled() and (allowed is None or slug in allowed)
            ]
            for slug in s_enabled:
                tasks.append(asyncio.create_task(
                    s_streams[slug].run(),
                    name=f"site-{site_prof.site_id}-{slug}",
                ))
            logger.info(
                "Multi-site '%s': %d streams started (offset=%d, scale=%.1f)",
                site_prof.site_id, len(s_enabled),
                site_prof.equipment_id_offset, site_prof.scale,
            )

    # Start anomaly engine
    if anomaly.is_enabled():
        tasks.append(asyncio.create_task(anomaly.run(), name="anomaly-engine"))

    # Start metrics logger
    tasks.append(asyncio.create_task(_metrics_loop(cfg, client, start_time), name="metrics"))

    # Start command handler
    tasks.append(asyncio.create_task(cmd_handler.run(), name="command-handler"))

    # Start config file watcher (triggers auto-reload on save)
    tasks.append(asyncio.create_task(
        _config_watcher(config_path, reload_event), name="config-watcher",
    ))

    logger.info("Simulator running — %d tasks started", len(tasks))

    # Handle shutdown
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    # Wait for either a shutdown signal or a config-reload trigger
    done, _ = await asyncio.wait(
        [
            asyncio.create_task(stop.wait(), name="wait-stop"),
            asyncio.create_task(reload_event.wait(), name="wait-reload"),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )

    is_reload = reload_event.is_set() and not stop.is_set()

    if is_reload:
        logger.info("=" * 60)
        logger.info("Config changed — reloading simulator...")
        logger.info("=" * 60)
    else:
        logger.info("Shutting down (no reload)")

    # C3: Graceful shutdown — cancel tasks and wait for them to finish
    logger.info("Stopping %d tasks...", len(tasks))
    for t in tasks:
        t.cancel()

    # Wait for all tasks to complete their cancellation (up to 5s)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for t, result in zip(tasks, results):
        if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
            logger.warning("Task %s raised during shutdown: %s", t.get_name(), result)

    # Drain the output queue (MQTT only — Event Hub flushes in disconnect)
    if isinstance(client, MqttClient) and client._client is not None:
        try:
            # Give paho time to flush outgoing messages
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    await client.disconnect()

    if is_reload:
        logger.info("Simulator stopped — will restart with new config")
    else:
        logger.info("Simulator stopped")

    return is_reload


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

    # ── Reload loop: re-read config and restart on file changes ──
    while True:
        if config_path and config_path.exists():
            logger.info("Loading config from %s", config_path)
            cfg = load_config(config_path)
        else:
            logger.warning("No config file found — using defaults")
            cfg = SimulatorConfig()

        _setup_logging(cfg)

        logger.info("=" * 60)
        logger.info("Zava MQTT Simulator starting")
        logger.info("Output mode: %s", cfg.output_mode)
        if cfg.output_mode == "mqtt":
            logger.info("Broker: %s:%d", cfg.mqtt.broker, cfg.mqtt.port)
        else:
            logger.info("Event Hub: %s", cfg.eventhub.eventhub_name or "(from connection string)")
        logger.info("Topic mode: %s", cfg.topic_mode)
        logger.info("=" * 60)

        should_reload = asyncio.run(run(cfg, config_path))

        if not should_reload:
            break  # normal shutdown (Ctrl-C / SIGTERM)

        logger.info("Reloading in 1 second...")
        time.sleep(1)  # brief pause before restart


if __name__ == "__main__":
    main()
