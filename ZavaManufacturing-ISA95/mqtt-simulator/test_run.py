#!/usr/bin/env python3
"""Run the simulator for a limited duration (for testing)."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.config import load_config
from src.main import run, _setup_logging

import logging
logger = logging.getLogger("zava-simulator")

async def timed_run(cfg, duration=25):
    """Run the simulator and stop after `duration` seconds."""
    task = asyncio.create_task(run(cfg))
    await asyncio.sleep(duration)
    # Send cancellation
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "test-local-config.yaml"
    cfg = load_config(config_path)
    _setup_logging(cfg)
    logger.info("=== LOCAL TEST RUN (25 seconds) ===")
    logger.info("Broker: %s:%d", cfg.mqtt.broker, cfg.mqtt.port)
    asyncio.run(timed_run(cfg, 25))
    logger.info("=== TEST COMPLETE ===")
