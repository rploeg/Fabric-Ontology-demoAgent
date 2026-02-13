# MQTT Simulator — Remote Commands

Publish JSON to **`zava/simulator/command`** and receive responses on **`zava/simulator/status`**.

---

## Status & Info

### Get simulator status

```json
{"action": "status"}
```

### List all streams

```json
{"action": "list-streams"}
```

### List all anomaly scenarios

```json
{"action": "list-anomalies"}
```

---

## Stream Control

### Enable a stream

```json
{"action": "enable", "stream": "equipment"}
```

```json
{"action": "enable", "stream": "machine-state"}
```

```json
{"action": "enable", "stream": "process-segment"}
```

```json
{"action": "enable", "stream": "production-counter"}
```

```json
{"action": "enable", "stream": "safety-incident"}
```

```json
{"action": "enable", "stream": "predictive-maintenance"}
```

```json
{"action": "enable", "stream": "digital-twin"}
```

```json
{"action": "enable", "stream": "material-consumption"}
```

```json
{"action": "enable", "stream": "quality-vision"}
```

```json
{"action": "enable", "stream": "supply-chain"}
```

### Disable a stream

```json
{"action": "disable", "stream": "equipment"}
```

```json
{"action": "disable", "stream": "machine-state"}
```

```json
{"action": "disable", "stream": "process-segment"}
```

```json
{"action": "disable", "stream": "production-counter"}
```

```json
{"action": "disable", "stream": "safety-incident"}
```

```json
{"action": "disable", "stream": "predictive-maintenance"}
```

```json
{"action": "disable", "stream": "digital-twin"}
```

```json
{"action": "disable", "stream": "material-consumption"}
```

```json
{"action": "disable", "stream": "quality-vision"}
```

```json
{"action": "disable", "stream": "supply-chain"}
```

### Change stream publish interval

```json
{"action": "set-interval", "stream": "equipment", "intervalSec": 5}
```

```json
{"action": "set-interval", "stream": "process-segment", "intervalSec": 10}
```

```json
{"action": "set-interval", "stream": "production-counter", "intervalSec": 10}
```

```json
{"action": "set-interval", "stream": "predictive-maintenance", "intervalSec": 5}
```

```json
{"action": "set-interval", "stream": "quality-vision", "intervalSec": 5}
```

---

## Anomaly Injection

### Trigger an anomaly manually

```json
{"action": "trigger-anomaly", "scenario": "temperature_spike"}
```

```json
{"action": "trigger-anomaly", "scenario": "oee_drop"}
```

```json
{"action": "trigger-anomaly", "scenario": "machine_cascade_failure"}
```

```json
{"action": "trigger-anomaly", "scenario": "bearing_failure_imminent"}
```

```json
{"action": "trigger-anomaly", "scenario": "material_overconsumption"}
```

```json
{"action": "trigger-anomaly", "scenario": "vision_defect_surge"}
```

```json
{"action": "trigger-anomaly", "scenario": "shipment_critical_delay"}
```

```json
{"action": "trigger-anomaly", "scenario": "energy_spike"}
```

```json
{"action": "trigger-anomaly", "scenario": "cascading_line_failure"}
```

```json
{"action": "trigger-anomaly", "scenario": "safety_zone_breach"}
```

```json
{"action": "trigger-anomaly", "scenario": "quality_model_degradation"}
```

---

## General Config Changes

### Change anomaly interval (minutes)

```json
{"action": "set", "path": "anomalies.scenario_interval_min", "value": 1}
```

```json
{"action": "set", "path": "anomalies.scenario_interval_min", "value": 15}
```

### Enable/disable all anomalies

```json
{"action": "set", "path": "anomalies.enabled", "value": true}
```

```json
{"action": "set", "path": "anomalies.enabled", "value": false}
```

### Change reject rate (production counter)

```json
{"action": "set", "path": "production_counter_telemetry.reject_rate", "value": 0.10}
```

```json
{"action": "set", "path": "production_counter_telemetry.reject_rate", "value": 0.02}
```

### Change OEE range (production counter)

```json
{"action": "set", "path": "production_counter_telemetry.oee_range", "value": [0.40, 0.55]}
```

```json
{"action": "set", "path": "production_counter_telemetry.oee_range", "value": [0.75, 0.95]}
```

---

## Stream Slugs Reference

| Slug | Stream |
|------|--------|
| `equipment` | Equipment Telemetry (site-level) |
| `machine-state` | Machine State Telemetry |
| `process-segment` | Process Segment Telemetry |
| `production-counter` | Production Counter Telemetry |
| `safety-incident` | Safety Incident Events |
| `predictive-maintenance` | Predictive Maintenance Signals |
| `digital-twin` | Digital Twin State Sync |
| `material-consumption` | Material Consumption Events |
| `quality-vision` | Quality Vision Events |
| `supply-chain` | Supply Chain Alerts |

## Anomaly Scenarios Reference

| Scenario | Target Stream | Duration |
|----------|--------------|----------|
| `temperature_spike` | process-segment | 120s |
| `oee_drop` | production-counter | 300s |
| `machine_cascade_failure` | machine-state | 180s |
| `bearing_failure_imminent` | predictive-maintenance | 600s |
| `material_overconsumption` | material-consumption | 300s |
| `vision_defect_surge` | quality-vision | 240s |
| `shipment_critical_delay` | supply-chain | instant |
| `energy_spike` | equipment | 180s |
| `cascading_line_failure` | machine-state | 300s |
| `safety_zone_breach` | safety-incident | 120s |
| `quality_model_degradation` | quality-vision | 300s |
