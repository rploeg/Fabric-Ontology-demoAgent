"""Zava Simulator Dashboard — FastAPI micro-app for sending MQTT commands.

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
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

import paho.mqtt.client as mqtt
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

# ---------------------------------------------------------------------------
# MQTT bridge
# ---------------------------------------------------------------------------

COMMAND_TOPIC = "zava/simulator/command"
STATUS_TOPIC = "zava/simulator/status"

_mqtt_client: Optional[mqtt.Client] = None
_responses: List[Dict[str, Any]] = []
_responses_lock = threading.Lock()
MAX_RESPONSES = 200


def _on_connect(client, userdata, flags, rc, properties):
    if not rc.is_failure:
        client.subscribe(STATUS_TOPIC, qos=1)
        client.subscribe("zava/#", qos=1)
        print(f"[mqtt] Connected to {userdata['broker']}:{userdata['port']}")
    else:
        print(f"[mqtt] Connection failed: {rc}")


def _on_message(client, userdata, msg):
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


def init_mqtt(broker: str, port: int, username: str, password: str):
    global _mqtt_client
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

app = FastAPI(title="Zava Simulator Dashboard")


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


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTML_PAGE


# ---------------------------------------------------------------------------
# Embedded HTML/JS dashboard
# ---------------------------------------------------------------------------

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zava Simulator Dashboard</title>
<style>
  :root {
    --bg: #0f1117; --surface: #1a1d27; --border: #2a2d3a;
    --text: #e1e4ed; --muted: #8b8fa3; --accent: #6366f1;
    --accent-hover: #818cf8; --green: #22c55e; --red: #ef4444;
    --orange: #f59e0b; --blue: #3b82f6;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg); color: var(--text); min-height: 100vh; }
  .header { background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 16px 24px; display: flex; align-items: center; gap: 16px; }
  .header h1 { font-size: 18px; font-weight: 600; }
  .header .badge { font-size: 11px; padding: 3px 8px; border-radius: 12px;
    background: var(--green); color: #000; font-weight: 600; }
  .header .badge.disconnected { background: var(--red); color: #fff; }
  .container { max-width: 1400px; margin: 0 auto; padding: 24px;
    display: grid; grid-template-columns: 360px 1fr; gap: 24px; }
  @media (max-width: 900px) { .container { grid-template-columns: 1fr; } }

  /* Cards */
  .card { background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px; }
  .card h2 { font-size: 14px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.5px; color: var(--muted); margin-bottom: 16px; }

  /* Controls */
  .section { margin-bottom: 20px; }
  .section h3 { font-size: 13px; color: var(--accent); margin-bottom: 8px; font-weight: 600; }
  label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
  select, input[type="text"], input[type="number"] {
    width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border);
    background: var(--bg); color: var(--text); font-size: 13px; outline: none; }
  select:focus, input:focus { border-color: var(--accent); }
  .row { display: flex; gap: 8px; align-items: flex-end; }
  .row > * { flex: 1; }

  button { cursor: pointer; border: none; border-radius: 8px; padding: 9px 16px;
    font-size: 13px; font-weight: 600; transition: all 0.15s; }
  .btn-primary { background: var(--accent); color: #fff; width: 100%; margin-top: 12px; }
  .btn-primary:hover { background: var(--accent-hover); }
  .btn-sm { padding: 6px 12px; font-size: 12px; }
  .btn-green { background: var(--green); color: #000; }
  .btn-red { background: var(--red); color: #fff; }
  .btn-orange { background: var(--orange); color: #000; }
  .btn-blue { background: var(--blue); color: #fff; }
  .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
  .btn-outline:hover { border-color: var(--accent); color: var(--accent); }

  /* Quick actions grid */
  .quick-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

  /* Stream table */
  .stream-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .stream-table th { text-align: left; padding: 8px; color: var(--muted);
    border-bottom: 1px solid var(--border); font-weight: 500; font-size: 12px; }
  .stream-table td { padding: 8px; border-bottom: 1px solid var(--border); }
  .stream-table tr:hover { background: rgba(99,102,241,0.05); }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
  .status-dot.on { background: var(--green); }
  .status-dot.off { background: var(--red); }

  /* Log panel */
  .log-panel { max-height: 600px; overflow-y: auto; }
  .log-entry { padding: 10px 12px; border-bottom: 1px solid var(--border);
    font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; }
  .log-entry:hover { background: rgba(99,102,241,0.05); }
  .log-topic { color: var(--accent); font-weight: 500; }
  .log-time { color: var(--muted); font-size: 11px; float: right; }
  .log-payload { color: var(--text); white-space: pre-wrap; word-break: break-all;
    margin-top: 4px; line-height: 1.5; }
  .log-status-ok { color: var(--green); }
  .log-status-error { color: var(--red); }

  /* Tabs */
  .tabs { display: flex; gap: 0; margin-bottom: 16px; }
  .tab { padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer;
    border-bottom: 2px solid transparent; color: var(--muted); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  .tab:hover { color: var(--text); }

  /* JSON preview */
  .json-preview { background: var(--bg); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px; font-family: monospace; font-size: 12px;
    white-space: pre-wrap; color: var(--muted); margin-top: 8px; max-height: 100px;
    overflow-y: auto; }

  /* Toast */
  .toast { position: fixed; bottom: 24px; right: 24px; padding: 12px 20px;
    border-radius: 8px; font-size: 13px; font-weight: 500; z-index: 1000;
    transform: translateY(100px); opacity: 0; transition: all 0.3s; }
  .toast.show { transform: translateY(0); opacity: 1; }
  .toast.success { background: var(--green); color: #000; }
  .toast.error { background: var(--red); color: #fff; }

  .filter-row { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
  .filter-row input { flex: 1; }
  .msg-count { font-size: 12px; color: var(--muted); }
</style>
</head>
<body>

<div class="header">
  <h1>Zava Simulator Dashboard</h1>
  <span id="conn-badge" class="badge">Connected</span>
  <span style="flex:1"></span>
  <span id="msg-rate" style="font-size:12px; color:var(--muted)"></span>
</div>

<div class="container">
  <!-- LEFT: Command Panel -->
  <div>
    <!-- Quick Actions -->
    <div class="card" style="margin-bottom:16px">
      <h2>Quick Actions</h2>
      <div class="quick-grid">
        <button class="btn-sm btn-blue" onclick="sendQuick('status')">Get Status</button>
        <button class="btn-sm btn-blue" onclick="sendQuick('list-streams')">List Streams</button>
        <button class="btn-sm btn-blue" onclick="sendQuick('list-anomalies')">List Anomalies</button>
        <button class="btn-sm btn-outline" onclick="clearLog()">Clear Log</button>
      </div>
    </div>

    <!-- Stream Control -->
    <div class="card" style="margin-bottom:16px">
      <h2>Stream Control</h2>
      <div class="section">
        <label>Stream</label>
        <select id="stream-select">
          <option value="equipment">equipment</option>
          <option value="machine-state">machine-state</option>
          <option value="process-segment">process-segment</option>
          <option value="production-counter">production-counter</option>
          <option value="safety-incident">safety-incident</option>
          <option value="predictive-maintenance">predictive-maintenance</option>
          <option value="digital-twin">digital-twin</option>
          <option value="material-consumption">material-consumption</option>
          <option value="quality-vision">quality-vision</option>
          <option value="supply-chain">supply-chain</option>
        </select>
      </div>
      <div class="row" style="margin-bottom:8px">
        <button class="btn-sm btn-green" onclick="sendStream('enable')">Enable</button>
        <button class="btn-sm btn-red" onclick="sendStream('disable')">Disable</button>
      </div>
      <div class="section" style="margin-top:12px">
        <label>Set Interval (seconds)</label>
        <div class="row">
          <input type="number" id="interval-val" value="5" min="1" max="3600">
          <button class="btn-sm btn-orange" onclick="sendInterval()">Set</button>
        </div>
      </div>
    </div>

    <!-- Anomaly Injection -->
    <div class="card" style="margin-bottom:16px">
      <h2>Anomaly Injection</h2>
      <div class="section">
        <label>Scenario</label>
        <select id="anomaly-select">
          <option value="temperature_spike">temperature_spike (120s)</option>
          <option value="oee_drop">oee_drop (300s)</option>
          <option value="machine_cascade_failure">machine_cascade_failure (180s)</option>
          <option value="bearing_failure_imminent">bearing_failure_imminent (600s)</option>
          <option value="material_overconsumption">material_overconsumption (300s)</option>
          <option value="vision_defect_surge">vision_defect_surge (240s)</option>
          <option value="shipment_critical_delay">shipment_critical_delay (instant)</option>
          <option value="energy_spike">energy_spike (180s)</option>
          <option value="cascading_line_failure">cascading_line_failure (300s)</option>
          <option value="safety_zone_breach">safety_zone_breach (120s)</option>
          <option value="quality_model_degradation">quality_model_degradation (300s)</option>
        </select>
      </div>
      <button class="btn-primary btn-red" onclick="triggerAnomaly()">Trigger Anomaly</button>
    </div>

    <!-- Config Set -->
    <div class="card" style="margin-bottom:16px">
      <h2>Config Override</h2>
      <div class="section">
        <label>Config Path</label>
        <select id="config-path">
          <option value="anomalies.scenario_interval_min">anomalies.scenario_interval_min</option>
          <option value="anomalies.enabled">anomalies.enabled</option>
          <option value="production_counter_telemetry.reject_rate">production_counter_telemetry.reject_rate</option>
          <option value="production_counter_telemetry.oee_range">production_counter_telemetry.oee_range</option>
          <option value="custom">Custom path...</option>
        </select>
        <input type="text" id="config-path-custom" placeholder="e.g. anomalies.enabled" style="display:none; margin-top:6px">
      </div>
      <div class="section">
        <label>Value (JSON)</label>
        <input type="text" id="config-value" placeholder='e.g. 15, true, [0.4, 0.6]'>
      </div>
      <button class="btn-primary" onclick="sendConfigSet()">Apply</button>
      <div class="json-preview" id="cmd-preview">{}</div>
    </div>

    <!-- Raw JSON -->
    <div class="card">
      <h2>Raw Command</h2>
      <div class="section">
        <label>JSON Payload</label>
        <textarea id="raw-json" rows="4" style="width:100%; padding:8px 10px; border-radius:8px;
          border:1px solid var(--border); background:var(--bg); color:var(--text);
          font-family:monospace; font-size:12px; resize:vertical;">{"action": "status"}</textarea>
      </div>
      <button class="btn-primary" onclick="sendRaw()">Send Raw</button>
    </div>
  </div>

  <!-- RIGHT: Response Log -->
  <div>
    <!-- Stream Status Table -->
    <div class="card" id="stream-status-card" style="margin-bottom:16px; display:none">
      <h2>Stream Status</h2>
      <table class="stream-table">
        <thead><tr><th>Stream</th><th>Status</th><th>Interval</th><th>Actions</th></tr></thead>
        <tbody id="stream-status-body"></tbody>
      </table>
    </div>

    <!-- Messages -->
    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px">
        <h2 style="margin:0">Message Log</h2>
        <span class="msg-count" id="msg-count">0 messages</span>
      </div>
      <div class="tabs">
        <div class="tab active" data-filter="">All</div>
        <div class="tab" data-filter="zava/simulator/status">Status</div>
        <div class="tab" data-filter="zava/telemetry">Telemetry</div>
      </div>
      <div class="filter-row">
        <input type="text" id="topic-filter" placeholder="Filter by topic...">
        <button class="btn-sm btn-outline" onclick="togglePause()">
          <span id="pause-label">Pause</span>
        </button>
      </div>
      <div class="log-panel" id="log-panel"></div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
// ---- State ----
let paused = false;
let activeFilter = '';
let topicFilter = '';
let messages = [];
let pollInterval = null;

// ---- API helpers ----
async function api(method, url, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  return r.json();
}

async function sendCommand(cmd) {
  updatePreview(cmd);
  try {
    const r = await api('POST', '/api/command', cmd);
    toast(`Sent: ${cmd.action}`, 'success');
    return r;
  } catch (e) {
    toast(`Failed: ${e.message}`, 'error');
  }
}

// ---- Command builders ----
function sendQuick(action) { sendCommand({ action }); }

function sendStream(action) {
  const stream = document.getElementById('stream-select').value;
  sendCommand({ action, stream });
}

function sendInterval() {
  const stream = document.getElementById('stream-select').value;
  const sec = parseInt(document.getElementById('interval-val').value);
  sendCommand({ action: 'set-interval', stream, intervalSec: sec });
}

function triggerAnomaly() {
  const scenario = document.getElementById('anomaly-select').value;
  sendCommand({ action: 'trigger-anomaly', scenario });
}

function sendConfigSet() {
  const pathSel = document.getElementById('config-path').value;
  const path = pathSel === 'custom'
    ? document.getElementById('config-path-custom').value
    : pathSel;
  let value;
  try { value = JSON.parse(document.getElementById('config-value').value); }
  catch { value = document.getElementById('config-value').value; }
  sendCommand({ action: 'set', path, value });
}

function sendRaw() {
  try {
    const cmd = JSON.parse(document.getElementById('raw-json').value);
    sendCommand(cmd);
  } catch (e) {
    toast('Invalid JSON', 'error');
  }
}

// ---- Preview ----
function updatePreview(cmd) {
  document.getElementById('cmd-preview').textContent = JSON.stringify(cmd, null, 2);
}

// ---- Stream status table ----
function updateStreamTable(data) {
  const card = document.getElementById('stream-status-card');
  const body = document.getElementById('stream-status-body');
  if (!data.streams) return;
  card.style.display = '';
  let html = '';
  for (const [slug, info] of Object.entries(data.streams)) {
    const dot = info.enabled ? 'on' : 'off';
    const label = info.enabled ? 'Enabled' : 'Disabled';
    const interval = info.intervalSec != null ? info.intervalSec + 's' : '—';
    html += `<tr>
      <td><span class="status-dot ${dot}"></span>${slug}</td>
      <td>${label}</td>
      <td>${interval}</td>
      <td>
        <button class="btn-sm ${info.enabled ? 'btn-red' : 'btn-green'}"
          onclick="sendCommand({action:'${info.enabled ? 'disable' : 'enable'}',stream:'${slug}'})"
          style="padding:3px 8px;font-size:11px">${info.enabled ? 'Disable' : 'Enable'}</button>
      </td>
    </tr>`;
  }
  body.innerHTML = html;
}

// ---- Log rendering ----
function renderLog() {
  const panel = document.getElementById('log-panel');
  let filtered = messages;
  if (activeFilter) filtered = filtered.filter(m => m.topic.includes(activeFilter));
  if (topicFilter) filtered = filtered.filter(m => m.topic.toLowerCase().includes(topicFilter.toLowerCase()));
  const shown = filtered.slice(0, 100);

  panel.innerHTML = shown.map(m => {
    const p = m.payload;
    const statusClass = p.status === 'ok' ? 'log-status-ok' : p.status === 'error' ? 'log-status-error' : '';
    const payloadStr = JSON.stringify(p, null, 2);
    return `<div class="log-entry">
      <span class="log-topic">${m.topic}</span>
      <span class="log-time">${m.received_at}</span>
      <div class="log-payload ${statusClass}">${escHtml(payloadStr)}</div>
    </div>`;
  }).join('');

  document.getElementById('msg-count').textContent = `${messages.length} messages (showing ${shown.length})`;

  // Auto-update stream table from status responses
  const lastStatus = messages.find(m => m.topic === 'zava/simulator/status' && m.payload.action === 'status');
  if (lastStatus) updateStreamTable(lastStatus.payload);
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ---- Polling ----
async function poll() {
  if (paused) return;
  try {
    const data = await api('GET', `/api/responses?limit=200&topic=${encodeURIComponent(topicFilter)}`);
    messages = data;
    renderLog();
  } catch (e) { /* ignore transient errors */ }
}

function togglePause() {
  paused = !paused;
  document.getElementById('pause-label').textContent = paused ? 'Resume' : 'Pause';
}

function clearLog() {
  api('GET', '/api/responses/clear').then(() => { messages = []; renderLog(); });
}

// ---- Toast ----
function toast(msg, type) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast show ${type}`;
  setTimeout(() => el.className = 'toast', 2500);
}

// ---- Tabs ----
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    activeFilter = tab.dataset.filter;
    renderLog();
  });
});

// ---- Topic filter ----
document.getElementById('topic-filter').addEventListener('input', e => {
  topicFilter = e.target.value;
  renderLog();
});

// ---- Custom config path toggle ----
document.getElementById('config-path').addEventListener('change', e => {
  document.getElementById('config-path-custom').style.display =
    e.target.value === 'custom' ? '' : 'none';
});

// ---- Init ----
pollInterval = setInterval(poll, 1000);
poll();

// Auto-fetch status on load
setTimeout(() => sendQuick('status'), 500);
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Zava Simulator Dashboard")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", default="mqtt", help="MQTT username")
    parser.add_argument("--password", default="mqtt", help="MQTT password")
    parser.add_argument("--host", default="0.0.0.0", help="Web server bind address")
    parser.add_argument("--port", type=int, default=8000, help="Web server port")
    args = parser.parse_args()

    init_mqtt(args.broker, args.mqtt_port, args.username, args.password)
    print(f"[web] Starting dashboard at http://localhost:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
