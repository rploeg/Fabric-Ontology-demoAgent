# Running the Zava MQTT Simulator Locally

## Prerequisites

- **Docker Desktop** (macOS/Windows) — for running the simulator container
- **Python 3.12+** — for running without Docker
- **MQTT broker** (e.g. [Mosquitto](https://mosquitto.org/)) — only needed when `outputMode: "mqtt"`
- **Azure CLI** (`az login`) — only needed for Event Hub with `defaultCredential` (no Docker)
- **Azure Service Principal** — only needed for Event Hub via Docker (see [Step 2b](#2b-configure-event-hub-output))

## Output modes

The simulator supports two output targets — choose one via `outputMode` in the config:

| Mode | Target | Best for |
|------|--------|----------|
| `mqtt` (default) | MQTT broker | Local dev, AIO integration |
| `eventHub` | Azure Event Hub | Direct-to-Fabric pipeline |

## 1. Start your MQTT broker (mqtt mode only)

Skip this step if you're using `outputMode: "eventHub"`.

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

### 2a. MQTT output (default)

Edit `simulator-config.yaml` — the `mqtt` section should point to your local broker:

```yaml
outputMode: "mqtt"

mqtt:
  broker: "host.docker.internal"   # Docker → host machine (use "localhost" without Docker)
  port: 1883
  useTls: false
  authMethod: "usernamePassword"
  username: "mqtt"
  password: "mqtt"
```

> **Note:** `host.docker.internal` resolves to your host machine from inside a Docker container on macOS/Windows. On Linux, use `--add-host=host.docker.internal:host-gateway` when running the container.

### 2b. Event Hub output

Edit `simulator-config.yaml`:

```yaml
outputMode: "eventHub"

eventHub:
  fullyQualifiedNamespace: "<your-namespace>.servicebus.windows.net"
  eventhubName: "<your-hub-name>"
  credential: "defaultCredential"
  maxBatchSize: 100
  maxWaitTimeSec: 1.0
  partitionKeyMode: "topic"
```

**Authentication depends on how you run:**

| Running via | How `defaultCredential` resolves |
|-------------|----------------------------------|
| Python (no Docker) | Azure CLI — run `az login` first |
| Docker | Service principal env vars (see below) |

**Docker + Event Hub setup:**

1. Create a service principal (one-time):
   ```bash
   az ad sp create-for-rbac --name "zava-simulator"
   ```
2. Assign the `Azure Event Hubs Data Sender` role:
   ```bash
   az role assignment create \
     --role "Azure Event Hubs Data Sender" \
     --assignee <appId from step 1> \
     --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.EventHub/namespaces/<ns>
   ```
3. Create a `.env` file (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
4. Fill in the values:
   ```dotenv
   AZURE_TENANT_ID=<tenant from step 1>
   AZURE_CLIENT_ID=<appId from step 1>
   AZURE_CLIENT_SECRET=<password from step 1>
   ```

> The `.env` file is in `.gitignore` — secrets never get committed.

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

### MQTT mode

```bash
docker run --rm \
  --name zava-simulator \
  --add-host=host.docker.internal:host-gateway \
  -v "$(pwd)/simulator-config.yaml:/app/simulator-config.yaml" \
  zava-simulator:latest
```

> **Tip:** Always mount the config file (`-v`) so the simulator can detect
> changes and auto-reload (see [Config hot-reload](#config-hot-reload) below).

### Event Hub mode

Pass the service principal credentials via `--env-file`:

```bash
docker run --rm \
  --name zava-simulator \
  --env-file .env \
  -v "$(pwd)/simulator-config.yaml:/app/simulator-config.yaml" \
  zava-simulator:latest
```

> Make sure `outputMode: "eventHub"` is set in your config and `.env` has the
> `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` values filled in.

### Config hot-reload

The simulator **automatically detects changes** to `simulator-config.yaml`
while running. When you save the file (e.g., from the web dashboard or a text
editor), the simulator will:

1. Detect the file change within ~2 seconds
2. Gracefully stop all running streams and disconnect from the current output
3. Re-read the updated config
4. Restart with the new settings (new output mode, broker, Event Hub, streams, etc.)

This means you can **switch between MQTT and Event Hub** without restarting the
container — just change `outputMode` in the config and save.

> **Important:** The config file must be bind-mounted (`-v`) for hot-reload to
> work. If the container uses the baked-in config, changes on the host won't
> be visible inside the container.
>
> **Note:** Environment variables (`.env`) are **not** hot-reloaded. If you
> change the service principal credentials, you must restart the container.

## 5. Verify messages

### MQTT mode

Subscribe to all Zava topics using any MQTT client:

```bash
# Using mosquitto_sub
mosquitto_sub -h localhost -p 1883 -u mqtt -P mqtt -t 'zava/#' -v
```

Or use a GUI client like [MQTTX](https://mqttx.app/) — subscribe to `zava/#`.

### Event Hub mode

Check the simulator logs for `Flushed N events to Event Hub` messages:

```bash
docker logs zava-simulator
# Look for: "Flushed 1 events to Event Hub"
```

Or verify via Azure Monitor:

```bash
az monitor metrics list \
  --resource /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.EventHub/namespaces/<ns> \
  --metric IncomingMessages --interval PT1M --output table
```

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
```

### MQTT mode

```bash
# Edit simulator-config.yaml: set broker to "localhost", outputMode to "mqtt"
python -m src.main --config simulator-config.yaml
```

### Event Hub mode

```bash
# Log in to Azure (DefaultAzureCredential picks up the CLI token)
az login

# Edit simulator-config.yaml: set outputMode to "eventHub", fill in eventHub section
python -m src.main --config simulator-config.yaml
```

> No service principal or env vars needed — `DefaultAzureCredential` uses your
> Azure CLI session directly.

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
