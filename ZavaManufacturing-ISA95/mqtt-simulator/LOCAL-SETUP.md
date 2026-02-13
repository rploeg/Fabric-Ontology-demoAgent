# Running the Zava MQTT Simulator Locally

## Prerequisites

- **Docker Desktop** (macOS/Windows) — for running the simulator container
- **MQTT broker** running on your machine (e.g. [Mosquitto](https://mosquitto.org/), [EMQX](https://www.emqx.io/), or any MQTTv5-compatible broker)

## 1. Start your MQTT broker

Make sure your broker is running on port **1883** with username `mqtt` and 

Example with Mosquitto:

```bash
# mosquitto.conf
listener 1883
allow_anonymous false
password_file /path/to/passwordfile

# Then run:
mosquitto -c mosquitto.conf
```

Or with a Docker-based broker:

```bash
docker run -d --name mosquitto -p 1883:1883 eclipse-mosquitto:2
```

## 2. Configure the simulator

Edit `simulator-config.yaml` — the `mqtt` section should point to your local broker:

```yaml
mqtt:
  broker: "host.docker.internal"   # Docker → host machine
  port: 1883
  useTls: false
  authMethod: "usernamePassword"
  username: "mqtt"
  password: "mqtt"
```

> **Note:** `host.docker.internal` resolves to your host machine from inside a Docker container on macOS/Windows. On Linux, use `--add-host=host.docker.internal:host-gateway` when running the container.

### Topic mode

| Mode | Description | Example topic |
|------|-------------|---------------|
| `flat` | One topic per stream | `zava/telemetry/machine-state` |
| `uns` | ISA-95 hierarchical (Unified Namespace) | `zava/portland-production/production-floor/WeaveLine-Alpha/EQP-016/telemetry/machine-state` |

Set `topicMode` in the config:

```yaml
topicMode: "uns"    # or "flat"
```

### Enable/disable streams

Each stream section has an `enabled` flag:

```yaml
equipmentTelemetry:
  enabled: true          # site-level energy, humidity, production rate

machineStateTelemetry:
  enabled: true          # per-machine state (Running, Stopped, etc.)

processSegmentTelemetry:
  enabled: true          # temperature, moisture, cycle time

productionCounterTelemetry:
  enabled: true          # OEE, unit counts, fiber production

safetyIncidentEvents:
  enabled: true          # camera-detected safety incidents

predictiveMaintenanceSignals:
  enabled: true          # vibration, health scores, degradation

digitalTwinStateSync:
  enabled: true          # ISA-95 status model, retained messages

materialConsumptionEvents:
  enabled: true          # BOM tracking, cumulative consumption

qualityVisionEvents:
  enabled: true          # pass/marginal/fail inspection results

supplyChainAlerts:
  enabled: true          # shipment lifecycle, delays, exceptions
```

## 3. Build the Docker image

```bash
cd ZavaManufacturing-ISA95/mqtt-simulator
docker build -t zava-simulator:latest .
```

## 4. Run the simulator

```bash
docker run --rm \
  --name zava-simulator \
  --add-host=host.docker.internal:host-gateway \
  zava-simulator:latest
```

The container uses the baked-in `simulator-config.yaml` by default.

To override with a local config file:

```bash
docker run --rm \
  --name zava-simulator \
  --add-host=host.docker.internal:host-gateway \
  -v "$(pwd)/simulator-config.yaml:/etc/simulator/simulator-config.yaml:ro" \
  zava-simulator:latest
```

## 5. Verify messages

Subscribe to all Zava topics using any MQTT client:

```bash
# Using mosquitto_sub
mosquitto_sub -h localhost -p 1883 -u mqtt -P mqtt -t 'zava/#' -v
```

Or use a GUI client like [MQTTX](https://mqttx.app/) — subscribe to `zava/#`.

### Expected output (UNS mode)

```
zava/portland-production/production-floor/WeaveLine-Alpha/EQP-016/telemetry/machine-state
  {"Timestamp":"2026-02-13T17:40:42Z","EquipmentId":"EQP-016","LineName":"WeaveLine-Alpha","Shift":"Day","MachineState":"Running",...}

zava/redmond-innovation/innovation-lab/telemetry/equipment
  {"Timestamp":"2026-02-13T17:40:42Z","EquipmentId":"EQP-001","EnergyConsumption":334.0,"Humidity":43.8,"ProductionRate":0.0}

zava/portland-production/production-floor/WeaveLine-Alpha/EQP-016/telemetry/production-counter
  {"Timestamp":"2026-02-13T17:40:42Z","EquipmentId":"EQP-016","LineName":"WeaveLine-Alpha","SKU":"ZC Field Standard",...}
```

### Expected output (flat mode)

```
zava/telemetry/machine-state       {"Timestamp":"...","EquipmentId":"EQP-016",...}
zava/telemetry/equipment           {"Timestamp":"...","EquipmentId":"EQP-001",...}
zava/telemetry/production-counter  {"Timestamp":"...","EquipmentId":"EQP-016",...}
```

## 6. Stop the simulator

```bash
docker stop zava-simulator
```

## Running without Docker (Python directly)

```bash
cd ZavaManufacturing-ISA95/mqtt-simulator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Edit simulator-config.yaml: set broker to "localhost"
python -m src.main --config simulator-config.yaml
```

## Full config reference

| Stream | Default interval | Machines/entities | Payload keys |
|--------|-----------------|-------------------|--------------|
| equipment | 30s | 3 sites | Timestamp, EquipmentId, EnergyConsumption, Humidity, ProductionRate |
| machine-state | 1s tick | 134 machines (11 lines) | Timestamp, EquipmentId, LineName, Shift, MachineState, ErrorCode, DurationSec, BatchId |
| process-segment | 30s | 2 segments | Timestamp, SegmentId, Temperature, MoistureContent, CycleTime |
| production-counter | 30s | 134 machines | Timestamp, EquipmentId, LineName, SKU, Shift, UnitCount, UnitCountDelta, FiberProducedGram, UnitsRejected, FiberRejectedGram, VOT, LoadingTime, OEE, BatchId |
| safety-incident | 60–1800s | 8 cameras | Timestamp, IncidentId, CameraId, EquipmentId, Zone, IncidentType, Severity, Description, Confidence, ImageRef |
| predictive-maintenance | 10s | 134 machines | Timestamp, EquipmentId, LineName, VibrationMmS, TemperatureC, HealthScore, RULHours, DegradationMode, AlertLevel |
| digital-twin | 60s heartbeat | 137 entities | Timestamp, EntityId, EntityType, Status, ParentId, Properties |
| material-consumption | 30s | 4 segment types | Timestamp, SegmentId, MaterialId, MaterialName, LotNumber, QuantityUsed, UnitOfMeasure, CumulativeUsed, PlannedQuantity, VariancePct |
| quality-vision | 10s | 11 stations | Timestamp, StationId, EquipmentId, LineName, InspectionResult, DefectType, DefectCount, Confidence, ImageRef, BatchId |
| supply-chain | 300–3600s | 3 shipments | Timestamp, ShipmentId, Origin, Destination, Status, CarrierRef, ETAHours, DelayHours, ExceptionType |
