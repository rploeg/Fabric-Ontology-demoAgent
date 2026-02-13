# Simulator Dashboard

Web UI for controlling the Zava MQTT Simulator via MQTT commands.

The browser talks to a tiny FastAPI server which publishes/subscribes via paho-mqtt — **no WebSocket config needed on the broker**.

## Quick Start

```bash
cd ZavaManufacturing-ISA95/simulator-dashboard
pip install -r requirements.txt
python app.py
```

Open **http://localhost:8000** in your browser.

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--broker` | `localhost` | MQTT broker host |
| `--mqtt-port` | `1883` | MQTT broker port |
| `--username` | `mqtt` | MQTT username |
| `--password` | `mqtt` | MQTT password |
| `--host` | `0.0.0.0` | Web server bind address |
| `--port` | `8000` | Web server port |

### Examples

```bash
# Default (localhost broker, port 8000)
python app.py

# Custom broker
python app.py --broker 10.0.0.5

# Different web port
python app.py --port 8080
```

## Features

- **Quick Actions** — one-click Status, List Streams, List Anomalies
- **Stream Control** — enable/disable any of the 10 streams, change publish intervals
- **Anomaly Injection** — trigger any of the 7 anomaly scenarios
- **Config Override** — change any config path at runtime (anomaly interval, reject rate, OEE range, etc.)
- **Raw Command** — send arbitrary JSON to the command topic
- **Live Message Log** — real-time feed of all `zava/#` messages with topic filtering and tabs
- **Stream Status Table** — auto-populated from the latest status response
