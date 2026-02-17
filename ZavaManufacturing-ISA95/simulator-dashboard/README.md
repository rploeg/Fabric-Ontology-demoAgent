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
| `--config` | *(auto-detected)* | Path to `simulator-config.yaml` |

### Examples

```bash
# Default (localhost broker, port 8000)
python app.py

# Custom broker
python app.py --broker 10.0.0.5

# Different web port
python app.py --port 8080

# Custom config path
python app.py --config /path/to/simulator-config.yaml
```

## Features

- **Quick Actions** — one-click Status, List Streams, List Anomalies
- **Stream Control** — enable/disable any of the 10 streams, change publish intervals
- **Anomaly Injection** — trigger any of the 7 anomaly scenarios
- **Config Override** — change any config path at runtime (anomaly interval, reject rate, OEE range, etc.)
- **Raw Command** — send arbitrary JSON to the command topic
- **Live Message Log** — real-time feed of all `zava/#` messages with topic filtering and tabs
- **Stream Status Table** — auto-populated from the latest status response
- **Configuration Page** — edit `simulator-config.yaml` via a form editor or raw YAML editor; changes are saved to disk and the simulator auto-reloads within ~2 seconds

### Configuration Page

The dashboard includes a **Configuration** page (toggle in the top-right) that lets
you edit the full `simulator-config.yaml` without leaving the browser:

- **Form Editor** — structured fields for output mode, MQTT settings, Event Hub
  settings, topic mode, simulation parameters, and per-stream enable/disable
- **YAML Editor** — raw YAML for advanced editing
- **Save & Reload** — saves to disk; the simulator detects the change and
  automatically restarts with the new config (no container restart needed)

> **Note:** Secrets (e.g., `AZURE_CLIENT_SECRET`) are managed via `.env`, not
> through the dashboard. See [LOCAL-SETUP.md](../mqtt-simulator/LOCAL-SETUP.md)
> for details.
