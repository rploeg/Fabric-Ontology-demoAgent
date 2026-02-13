#!/usr/bin/env python3
"""Combined test: subscribe + simulate, then show results."""
import asyncio
import json
import os
import sys
import time
import threading
from collections import defaultdict

import paho.mqtt.client as mqtt

sys.path.insert(0, os.path.dirname(__file__))

from src.config import load_config
from src.main import _setup_logging, _build_streams, _metrics_loop
from src.mqtt_client import MqttClient
from src.anomaly_engine import AnomalyEngine

import logging
logger = logging.getLogger("zava-test")

# ── Subscriber (runs in a thread) ──────────────────────────────
counts: dict[str, int] = defaultdict(int)
samples: dict[str, list] = defaultdict(list)

def subscriber_thread(duration: int):
    def on_connect(client, userdata, flags, rc, properties):
        if not rc.is_failure:
            client.subscribe("zava/#", qos=1)
            logger.info("[SUB] Subscribed to zava/#")

    def on_message(client, userdata, msg):
        topic = msg.topic
        counts[topic] += 1
        payload = json.loads(msg.payload)
        if len(samples[topic]) < 1:
            samples[topic].append(payload)

    c = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="test-sub",
        protocol=mqtt.MQTTv5,
    )
    c.username_pw_set("mqtt", "mqtt")
    c.on_connect = on_connect
    c.on_message = on_message
    c.connect("localhost", 1883, 10)
    c.loop_start()
    time.sleep(duration)
    c.loop_stop()
    c.disconnect()

# ── Simulator (async) ──────────────────────────────────────────
async def run_simulator(cfg, duration: int):
    client = MqttClient(cfg.mqtt)
    await client.connect()

    streams = _build_streams(cfg, client)
    enabled = {slug: s for slug, s in streams.items() if s.is_enabled()}

    logger.info("Enabled streams: %s", ", ".join(enabled.keys()))
    logger.info("Topic mode: %s", cfg.topic_mode)

    tasks = []
    for slug, stream in enabled.items():
        tasks.append(asyncio.create_task(stream.run(), name=f"stream-{slug}"))

    start = time.monotonic()
    await asyncio.sleep(duration)

    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.monotonic() - start
    rate = client.message_count / elapsed if elapsed > 0 else 0
    logger.info("Published %d messages in %.0fs (%.1f msg/s)",
                client.message_count, elapsed, rate)
    await client.disconnect()

# ── Main ───────────────────────────────────────────────────────
def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "test-local-config.yaml"
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    cfg = load_config(config_path)
    _setup_logging(cfg)

    logger.info("=" * 60)
    logger.info("MQTT SIMULATOR LOCAL TEST")
    logger.info("Broker: localhost:1883  |  Duration: %ds", duration)
    logger.info("=" * 60)

    # Start subscriber thread first
    sub = threading.Thread(target=subscriber_thread, args=(duration + 5,), daemon=True)
    sub.start()
    time.sleep(1)  # let subscriber connect

    # Run simulator
    asyncio.run(run_simulator(cfg, duration))

    # Wait for subscriber to drain
    time.sleep(3)

    # Report
    print()
    print("=" * 60)
    print("RECEIVED MESSAGES PER TOPIC")
    print("=" * 60)
    total = 0
    for topic in sorted(counts.keys()):
        n = counts[topic]
        total += n
        print(f"  {topic}: {n} messages")
    print(f"\n  TOTAL: {total} messages")

    if samples:
        print()
        print("=" * 60)
        print("SAMPLE PAYLOADS (first message per topic)")
        print("=" * 60)
        for topic in sorted(samples.keys()):
            payload = samples[topic][0]
            print(f"\n[{topic}]")
            print(json.dumps(payload, indent=2, default=str))

    # Pass/fail
    print()
    if total > 0:
        print("RESULT: PASS — messages flowing through local MQTT broker")
    else:
        print("RESULT: FAIL — no messages received")

if __name__ == "__main__":
    main()
