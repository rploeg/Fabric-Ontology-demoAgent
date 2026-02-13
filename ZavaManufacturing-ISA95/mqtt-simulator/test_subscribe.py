#!/usr/bin/env python3
"""Subscribe to zava/# and print incoming messages for 40 seconds."""
import json
import time
import paho.mqtt.client as mqtt

counts = {}

def on_message(client, userdata, msg):
    topic = msg.topic
    counts[topic] = counts.get(topic, 0) + 1
    payload = json.loads(msg.payload)
    if counts[topic] <= 2:
        keys = list(payload.keys())
        preview = {k: payload[k] for k in keys[:4]}
        print(f"[{topic}] #{counts[topic]} {preview}")

def on_connect(client, userdata, flags, rc, properties):
    if not rc.is_failure:
        client.subscribe("zava/#", qos=1)
        print("Subscribed to zava/# — waiting for messages...")

c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="test-sub", protocol=mqtt.MQTTv5)
c.username_pw_set("mqtt", "mqtt")
c.on_connect = on_connect
c.on_message = on_message
c.connect("localhost", 1883, 10)
c.loop_start()
time.sleep(40)
c.loop_stop()
c.disconnect()
print()
print("=== Message counts per topic ===")
for t, n in sorted(counts.items()):
    print(f"  {t}: {n} messages")
print(f"Total: {sum(counts.values())} messages")
