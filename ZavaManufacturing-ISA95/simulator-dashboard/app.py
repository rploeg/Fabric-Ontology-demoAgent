"""Zava Manufacturing Simulator Dashboard — FastAPI micro-app for sending MQTT commands.

Run:
    pip install -r requirements.txt
    python app.py                        # default: localhost:1883
    python app.py --broker 10.0.0.5      # custom broker
    python app.py --port 8080            # custom web port

Opens http://localhost:8000 in the browser.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
import paho.mqtt.client as mqtt
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# ---------------------------------------------------------------------------
# API key authentication (optional — set DASHBOARD_API_KEY env var to enable)
# ---------------------------------------------------------------------------

_API_KEY: str | None = os.environ.get("DASHBOARD_API_KEY")

# ---------------------------------------------------------------------------
# MQTT bridge
# ---------------------------------------------------------------------------

COMMAND_TOPIC = "zava/simulator/command"
STATUS_TOPIC = "zava/simulator/status"

_mqtt_client: Optional[mqtt.Client] = None
_config_path: Optional[Path] = None  # set by CLI --config
_responses: List[Dict[str, Any]] = []
_responses_lock = threading.Lock()
MAX_RESPONSES = 200

# Separate store for latest simulator state (survives telemetry flood)
_latest_state: Dict[str, Any] = {}
_latest_state_lock = threading.Lock()

# D1: Throughput metrics — rolling window of (timestamp, msg_count) samples
_metrics_history: List[Dict[str, Any]] = []
_metrics_lock = threading.Lock()
_msg_total = 0
_metrics_started = 0.0

# D2: Anomaly timeline — recent anomaly START/END events
_anomaly_events: List[Dict[str, Any]] = []
_anomaly_lock = threading.Lock()
MAX_ANOMALY_EVENTS = 100


def _on_connect(client, userdata, flags, rc, properties):
    if not rc.is_failure:
        client.subscribe(STATUS_TOPIC, qos=1)
        client.subscribe("zava/#", qos=1)
        print(f"[mqtt] Connected to {userdata['broker']}:{userdata['port']}")
    else:
        print(f"[mqtt] Connection failed: {rc}")


def _on_message(client, userdata, msg):
    global _msg_total
    try:
        payload = json.loads(msg.payload.decode())
    except Exception:
        payload = {"raw": msg.payload.decode()[:500]}
    entry = {
        "topic": msg.topic,
        "payload": payload,
        "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with _responses_lock:
        _responses.insert(0, entry)
        while len(_responses) > MAX_RESPONSES:
            _responses.pop()

    # D1: Count every message for throughput metrics
    _msg_total += 1

    # Persist latest status / list-anomalies for the overview panel
    if msg.topic == STATUS_TOPIC and isinstance(payload, dict):
        action = payload.get("action")
        if action in ("status", "list-anomalies"):
            with _latest_state_lock:
                _latest_state[action] = payload

    # D2: Capture anomaly START/END events
    if "anomalies" in msg.topic and isinstance(payload, dict):
        phase = payload.get("Phase")
        if phase in ("START", "END"):
            evt = {
                "timestamp": payload.get("Timestamp", entry["received_at"]),
                "anomalyId": payload.get("AnomalyId", ""),
                "scenario": payload.get("Scenario", ""),
                "stream": payload.get("Stream", ""),
                "phase": phase,
                "durationSec": payload.get("DurationSec", 0),
                "description": payload.get("Description", ""),
            }
            with _anomaly_lock:
                _anomaly_events.insert(0, evt)
                while len(_anomaly_events) > MAX_ANOMALY_EVENTS:
                    _anomaly_events.pop()


def init_mqtt(broker: str, port: int, username: str, password: str):
    global _mqtt_client, _metrics_started
    _metrics_started = time.monotonic()
    _mqtt_client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"dashboard-{uuid.uuid4().hex[:8]}",
        protocol=mqtt.MQTTv5,
        userdata={"broker": broker, "port": port},
    )
    if username:
        _mqtt_client.username_pw_set(username, password)
    _mqtt_client.on_connect = _on_connect
    _mqtt_client.on_message = _on_message
    _mqtt_client.connect(broker, port, 60)
    _mqtt_client.loop_start()


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(title="Zava Manufacturing Simulator Dashboard")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Protect /api/* routes with a bearer token when DASHBOARD_API_KEY is set."""
    if _API_KEY and request.url.path.startswith("/api/"):
        # Allow the auth-status probe without a token
        if request.url.path == "/api/auth-status":
            return await call_next(request)
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if token != _API_KEY:
            return JSONResponse(
                {"error": "unauthorized", "detail": "Invalid or missing API key"},
                status_code=401,
            )
    return await call_next(request)


@app.get("/api/auth-status")
async def auth_status():
    """Tell the frontend whether auth is required (no secret leaked)."""
    return {"authRequired": _API_KEY is not None}


@app.post("/api/command")
async def send_command(body: dict):
    """Publish a JSON command to the simulator via MQTT."""
    if not _mqtt_client:
        return {"status": "error", "error": "MQTT not connected"}
    payload = json.dumps(body)
    info = _mqtt_client.publish(COMMAND_TOPIC, payload, qos=1)
    return {"status": "ok", "mid": info.mid, "command": body}


@app.get("/api/responses")
async def get_responses(limit: int = 50, topic: str = ""):
    """Return recent messages received from the broker."""
    with _responses_lock:
        msgs = list(_responses)
    if topic:
        msgs = [m for m in msgs if topic in m["topic"]]
    return msgs[:limit]


@app.get("/api/responses/clear")
async def clear_responses():
    with _responses_lock:
        _responses.clear()
    return {"status": "ok"}


@app.get("/api/overview")
async def get_overview():
    """Return latest cached status + anomalies for the overview panel."""
    with _latest_state_lock:
        return dict(_latest_state)


@app.get("/api/metrics")
async def get_metrics():
    """Return throughput metrics: current rate and 5-min history for sparkline."""
    now = time.monotonic()
    elapsed = now - _metrics_started if _metrics_started else 1
    rate = round(_msg_total / elapsed, 1) if elapsed > 0 else 0

    # Sample the current rate into a rolling history (kept server-side)
    sample = {"t": time.strftime("%H:%M:%S", time.gmtime()), "rate": rate, "total": _msg_total}
    with _metrics_lock:
        _metrics_history.append(sample)
        # Keep last 300 samples (~5 min at 1s poll)
        while len(_metrics_history) > 300:
            _metrics_history.pop(0)
        history = list(_metrics_history)

    return {"rate": rate, "total": _msg_total, "history": history}


@app.get("/api/anomaly-events")
async def get_anomaly_events(limit: int = 50):
    """Return recent anomaly START/END events for the timeline."""
    with _anomaly_lock:
        return list(_anomaly_events[:limit])


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTML_PAGE


# ---------------------------------------------------------------------------
# Config file API  (read / write simulator-config.yaml)
# ---------------------------------------------------------------------------

def _resolve_config_path() -> Path:
    """Return the current config path or a sensible default."""
    if _config_path and _config_path.exists():
        return _config_path
    # Fallback: look in the sibling mqtt-simulator directory
    fallback = Path(__file__).resolve().parent.parent / "mqtt-simulator" / "simulator-config.yaml"
    if fallback.exists():
        return fallback
    raise FileNotFoundError("No simulator-config.yaml found")


@app.get("/api/config")
async def get_config():
    """Return the current simulator-config.yaml as JSON."""
    try:
        p = _resolve_config_path()
        data = yaml.safe_load(p.read_text())
        return {"ok": True, "config": data, "path": str(p)}
    except FileNotFoundError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@app.get("/api/config/raw")
async def get_config_raw():
    """Return simulator-config.yaml as raw text."""
    try:
        p = _resolve_config_path()
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(p.read_text())
    except FileNotFoundError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)


@app.post("/api/config")
async def save_config(request: Request):
    """Overwrite simulator-config.yaml.

    Accepts either:
    - Content-Type: application/json → converts JSON to YAML
    - Content-Type: text/yaml (or text/plain) → writes raw YAML directly
    """
    try:
        p = _resolve_config_path()
        ct = request.headers.get("content-type", "")
        if "yaml" in ct or "plain" in ct:
            raw = (await request.body()).decode("utf-8")
            # Validate it's parseable YAML
            yaml.safe_load(raw)
            p.write_text(raw)
        else:
            body = await request.json()
            yaml_str = yaml.dump(
                body, default_flow_style=False, sort_keys=False, allow_unicode=True,
            )
            p.write_text(yaml_str)
        return {"ok": True, "path": str(p)}
    except FileNotFoundError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


# ---------------------------------------------------------------------------
# HTML dashboard template (loaded from external file — Q4)
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _load_html_page() -> str:
    """Read the dashboard HTML from templates/dashboard.html."""
    path = _TEMPLATE_DIR / "dashboard.html"
    if not path.exists():
        return "<h1>Error: templates/dashboard.html not found</h1>"
    return path.read_text(encoding="utf-8")


HTML_PAGE = _load_html_page()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    global _config_path
    parser = argparse.ArgumentParser(description="Zava Manufacturing Simulator Dashboard")
    parser.add_argument("--broker", default="127.0.0.1", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", default="mqtt", help="MQTT username")
    parser.add_argument("--password", default="mqtt", help="MQTT password")
    parser.add_argument("--host", default="0.0.0.0", help="Web server bind address")
    parser.add_argument("--port", type=int, default=8000, help="Web server port")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to simulator-config.yaml (auto-detected if omitted)",
    )
    args = parser.parse_args()

    if args.config:
        _config_path = Path(args.config).resolve()

    init_mqtt(args.broker, args.mqtt_port, args.username, args.password)
    print(f"[web] Starting dashboard at http://localhost:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
