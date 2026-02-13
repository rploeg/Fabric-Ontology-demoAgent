# MQTT Simulator for Zava Manufacturing — Deployment Plan

## 1. Overview

Deploy a **configurable MQTT data simulator** as a Kubernetes pod on AKS (alongside Azure IoT Operations) that publishes realistic Zava factory telemetry to the IoT Operations MQTT broker. Data flows from the pod → MQTT broker → Azure IoT Operations data pipeline → Fabric Eventhouse, matching the exact schema already used in the Zava demo.

```
┌─────────────────────────────────────────────────────────────┐
│  AKS Edge Cluster                                           │
│                                                             │
│  ┌──────────────────┐     ┌──────────────────────────────┐  │
│  │  zava-simulator  │────▶│  Azure IoT Operations        │  │
│  │  (Pod)           │MQTT │  MQTT Broker (aio-broker)    │  │
│  └──────────────────┘     └──────────────┬───────────────┘  │
│                                          │                  │
└──────────────────────────────────────────┼──────────────────┘
                                           │ Data pipeline
                                           ▼
                              ┌─────────────────────────┐
                              │  Microsoft Fabric        │
                              │  Eventhouse / KQL DB     │
                              └─────────────────────────┘
```

---

## 2. Telemetry Streams (10 MQTT topics)

The simulator produces realistic factory data across 10 configurable streams. The first 4 match the existing Eventhouse CSV schemas exactly; the remaining 6 extend the demo with safety, maintenance, digital twin, material tracking, quality vision, and supply chain capabilities. Every stream can be individually enabled/disabled.

### 2.1 Equipment Telemetry (site-level)
- **Topic**: `zava/telemetry/equipment`
- **Frequency**: Every 30 seconds per equipment (configurable)
- **Equipment IDs**: Site-level — `EQP-001`, `EQP-002`, `EQP-003` (3 sites)
- **Payload (JSON)**:
  ```json
  {
    "Timestamp": "2026-02-13T10:30:00Z",
    "EquipmentId": "EQP-002",
    "EnergyConsumption": 448.3,
    "Humidity": 38.6,
    "ProductionRate": 12500.0
  }
  ```

### 2.2 Machine State Telemetry (WorkUnit-level)
- **Topic**: `zava/telemetry/machine-state`
- **Frequency**: Event-driven — state transitions every 5–300 seconds (configurable)
- **Equipment IDs**: `EQP-016` through `EQP-149` (134 WorkUnit machines across 11 weave lines)
- **Payload (JSON)**:
  ```json
  {
    "Timestamp": "2026-02-13T10:31:15Z",
    "EquipmentId": "EQP-051",
    "LineName": "WeaveLine-Delta",
    "Shift": "Day",
    "MachineState": "Running",
    "ErrorCode": "0",
    "DurationSec": 0,
    "BatchId": "BTC-011"
  }
  ```
- **States**: `Running`, `Stopped`, `Blocked`, `Waiting`, `Idle`
- **ErrorCodes**: `0` (none), `E101` (jam), `E202` (overheat), `E303` (sensor fault), `E404` (material empty)

### 2.3 Process Segment Telemetry
- **Topic**: `zava/telemetry/process-segment`
- **Frequency**: Every 30 seconds per active segment (configurable)
- **Segment IDs**: Active segments (`SEG-029`, `SEG-030`, plus dynamically generated new ones)
- **Payload (JSON)**:
  ```json
  {
    "Timestamp": "2026-02-13T10:30:00Z",
    "SegmentId": "SEG-029",
    "Temperature": 85.6,
    "MoistureContent": 3.9,
    "CycleTime": 109.3
  }
  ```

### 2.4 Production Counter Telemetry (WorkUnit-level)
- **Topic**: `zava/telemetry/production-counter`
- **Frequency**: Every ~30 seconds per machine (configurable)
- **Equipment IDs**: `EQP-016` through `EQP-149`
- **Payload (JSON)**:
  ```json
  {
    "Timestamp": "2026-02-13T10:30:00Z",
    "EquipmentId": "EQP-088",
    "LineName": "WeaveLine-Hotel",
    "SKU": "ZC Field Active",
    "Shift": "Day",
    "UnitCount": 1548200,
    "UnitCountDelta": 12,
    "FiberProducedGram": 45.6,
    "UnitsRejected": 0,
    "FiberRejectedGram": 0.0,
    "VOT": 1800.0,
    "LoadingTime": 20272.24,
    "OEE": 0.87,
    "BatchId": "BTC-011"
  }
  ```

### 2.5 Safety Incident Events (camera-detected)
- **Topic**: `zava/telemetry/safety-incident` (configurable)
- **Frequency**: Event-driven — random incidents every 1–30 minutes (configurable)
- **Source**: AI-powered cameras deployed across facility zones
- **Payload (JSON)**:
  ```json
  {
    "Timestamp": "2026-02-13T10:42:17Z",
    "IncidentId": "INC-20260213-104217-001",
    "CameraId": "CAM-WH-A-03",
    "EquipmentId": "EQP-002",
    "Zone": "Weave Hall A",
    "IncidentType": "ppe_violation",
    "Severity": "Warning",
    "Description": "Worker detected without safety goggles near WeaveLine-Alpha",
    "Confidence": 0.94,
    "ImageRef": "blob://safety-captures/2026/02/13/CAM-WH-A-03_104217.jpg"
  }
  ```
- **Incident Types**: `ppe_violation`, `unauthorized_zone_entry`, `spill_detected`, `blocked_exit`, `forklift_near_miss`, `fire_smoke_detected`, `fallen_object`, `person_down`
- **Severities**: `Info`, `Warning`, `Critical`

### 2.6 Predictive Maintenance Signals (WorkUnit-level)
- **Topic**: `zava/telemetry/predictive-maintenance` (configurable)
- **Frequency**: Every 10 seconds per machine (configurable)
- **Equipment IDs**: `EQP-016` through `EQP-149` (same WorkUnit machines)
- **Payload (JSON)**:
  ```json
  {
    "Timestamp": "2026-02-13T10:30:10Z",
    "EquipmentId": "EQP-034",
    "LineName": "WeaveLine-Bravo",
    "MachineName": "Bravo-FiberWeaver-02",
    "VibrationMmS": 2.8,
    "BearingTemperatureC": 68.4,
    "AcousticDB": 82.1,
    "MotorCurrentA": 14.7,
    "SpindleSpeedRPM": 3200,
    "RemainingUsefulLifeHrs": 1420,
    "HealthScore": 0.85,
    "DegradationTrend": "stable"
  }
  ```
- **Degradation Simulation**: Machines slowly degrade over configurable hours (vibration increases, bearing temp rises, health score drops). Triggers maintenance recommendations.
- **Trends**: `stable`, `degrading`, `critical`

### 2.7 Digital Twin State Sync
- **Topic**: `zava/telemetry/digital-twin` (configurable)
- **Frequency**: On state change + heartbeat every 60 seconds (configurable)
- **Equipment IDs**: All equipment (sites, work centers, work units)
- **Payload (JSON)**:
  ```json
  {
    "Timestamp": "2026-02-13T10:30:00Z",
    "EquipmentId": "EQP-034",
    "LineName": "WeaveLine-Bravo",
    "MachineName": "Bravo-FiberWeaver-02",
    "ISA95Status": "Producing",
    "SubStatus": "NormalRun",
    "CurrentBatchId": "BTC-011",
    "CurrentSKU": "ZC Field Standard",
    "Operator": "Shift-A-Op-07",
    "RecipeId": "RCP-FS-001",
    "TargetSpeedPct": 85,
    "PlannedDowntimeMin": 0,
    "LastStateChange": "2026-02-13T06:05:00Z"
  }
  ```
- **ISA-95 Status Model**: `Producing`, `ProducingAtRate`, `Idle`, `Setup`, `Maintenance`, `Changeover`, `Blocked`, `ScheduledDowntime`, `UnscheduledDowntime`
- **Retained Messages**: Published with MQTT retain flag so new subscribers get the latest state immediately

### 2.8 Material Consumption Events
- **Topic**: `zava/telemetry/material-consumption` (configurable)
- **Frequency**: Event-driven — on material draw events (every 30–120 seconds per active segment)
- **Payload (JSON)**:
  ```json
  {
    "Timestamp": "2026-02-13T10:31:45Z",
    "ConsumptionId": "CON-20260213-103145-001",
    "SegmentId": "SEG-029",
    "SegmentType": "Coating",
    "BatchId": "BTC-011",
    "MaterialId": "MAT-002",
    "MaterialName": "Silver Nanowire Solution",
    "EquipmentId": "EQP-034",
    "QuantityUsed": 0.45,
    "UnitOfMeasure": "kg",
    "CumulativeUsed": 12.8,
    "BOMExpected": 15.0,
    "VariancePct": -14.7,
    "LotNumber": "LOT-SNW-2026-0042"
  }
  ```
- **BOM Tracking**: Each consumption event compares actual vs. expected (from BOM). Agents can detect over-consumption or waste.

### 2.9 Quality Inspection Image Events (in-line vision)
- **Topic**: `zava/telemetry/quality-vision` (configurable)
- **Frequency**: Every 5–15 seconds per active inspection station (configurable)
- **Payload (JSON)**:
  ```json
  {
    "Timestamp": "2026-02-13T10:30:05Z",
    "InspectionId": "VIS-20260213-103005-001",
    "StationId": "VISC-WL-A-01",
    "EquipmentId": "EQP-020",
    "LineName": "WeaveLine-Alpha",
    "BatchId": "BTC-011",
    "UnitSerial": "ZF-STD-011-004821",
    "Result": "Fail",
    "DefectType": "fiber_tear",
    "DefectLocation": {"x": 124, "y": 87, "w": 35, "h": 22},
    "Confidence": 0.91,
    "ImageRef": "blob://quality-vision/2026/02/13/VISC-WL-A-01_103005.jpg",
    "ModelVersion": "yolov8-zava-defect-v3.2"
  }
  ```
- **Defect Types**: `fiber_tear`, `coating_gap`, `sensor_misalignment`, `delamination`, `contamination`, `mesh_distortion`, `solder_bridge`, `label_skew`
- **Result**: `Pass`, `Fail`, `Marginal`
- **Vision Stations**: One per weave line, placed after sensor embed stage

### 2.10 Supply Chain Inbound Alerts
- **Topic**: `zava/telemetry/supply-chain` (configurable)
- **Frequency**: Event-driven — status changes every 5–60 minutes per active shipment (configurable)
- **Payload (JSON)**:
  ```json
  {
    "Timestamp": "2026-02-13T10:45:00Z",
    "AlertId": "SCA-20260213-104500-001",
    "ShipmentId": "SHP-012",
    "TrackingNum": "TRK-2025-5012",
    "Carrier": "TaiwanCargo Express",
    "Status": "Delayed",
    "PreviousStatus": "InTransit",
    "OriginEquipmentId": "EQP-012",
    "DestEquipmentId": "EQP-001",
    "MaterialIds": ["MAT-004"],
    "OriginalETA": "2026-02-15T10:00:00Z",
    "RevisedETA": "2026-02-18T14:00:00Z",
    "DelayReason": "Port congestion at Taoyuan",
    "ImpactedBatches": ["BTC-014"],
    "RiskLevel": "High"
  }
  ```
- **Statuses**: `Booked`, `PickedUp`, `InTransit`, `CustomsHold`, `Delayed`, `OutForDelivery`, `Delivered`, `Exception`
- **Risk Levels**: `Low`, `Medium`, `High`, `Critical`
- **Graph-aware**: Payload includes impacted downstream batches by traversing Shipment → Material → Segment → Batch

---

## 3. Configuration (`simulator-config.yaml`)

A single ConfigMap-mounted YAML file drives all simulator behaviour:

```yaml
# === MQTT Connection ===
mqtt:
  broker: "aio-broker.azure-iot-operations.svc.cluster.local"
  port: 1883                    # or 8883 for TLS
  useTls: false                 # enable for SAT/TLS auth
  authMethod: "serviceAccountToken"  # "none" | "serviceAccountToken" | "usernamePassword"
  username: ""                  # only if authMethod=usernamePassword
  password: ""                  # only if authMethod=usernamePassword
  clientId: "zava-simulator"
  keepAlive: 60
  reconnectDelaySec: 5
  qos: 1                       # 0 = at most once, 1 = at least once

# === Topic Configuration ===
topicPrefix: "zava/telemetry"   # default prefix; each stream can override with its own topic

topicMode: "uns"                # "flat" = single topic per stream | "uns" = ISA-95 hierarchical UNS

# UNS (Unified Namespace) settings — only used when topicMode=uns
uns:
  # ISA-95 hierarchy template: {enterprise}/{site}/{area}/{line}/{cell}/[telemetry|events|state]/{stream}
  enterprise: "zava"
  hierarchy:
    # Map equipment to UNS path segments
    sites:
      EQP-001:
        slug: "redmond-innovation"
        areas:
          EQP-004: "coating-dev-lab"
          EQP-007: "qa-testing-lab"
      EQP-002:
        slug: "portland-production"
        areas:
          EQP-005:
            slug: "weave-hall-a"
            lines:
              WeaveLine-Alpha: "weaveline-alpha"
              WeaveLine-Bravo: "weaveline-bravo"
              WeaveLine-Charlie: "weaveline-charlie"
              WeaveLine-Delta: "weaveline-delta"
              WeaveLine-Echo: "weaveline-echo"
          EQP-006:
            slug: "weave-hall-b"
            lines:
              WeaveLine-Foxtrot: "weaveline-foxtrot"
              WeaveLine-Golf: "weaveline-golf"
              WeaveLine-Hotel: "weaveline-hotel"
              WeaveLine-India: "weaveline-india"
              WeaveLine-Juliet: "weaveline-juliet"
              WeaveLine-Kilo: "weaveline-kilo"
      EQP-003:
        slug: "distribution-hub"
        areas:
          EQP-008: "finished-goods-warehouse"
  # Category mapping: which streams go under telemetry/, events/, or state/
  categories:
    telemetry: ["equipment", "machine-state", "process-segment", "production-counter", "predictive-maintenance"]
    events: ["safety-incident", "quality-vision", "material-consumption", "supply-chain"]
    state: ["digital-twin"]

  # Example resolved topics (auto-generated, shown for reference):
  #   UNS:  zava/portland-production/weave-hall-a/weaveline-bravo/bravo-fiberweaver-02/telemetry/machine-state
  #   UNS:  zava/portland-production/weave-hall-a/weaveline-alpha/visc-wl-a-01/events/quality-vision
  #   UNS:  zava/portland-production/weave-hall-b/weaveline-hotel/hotel-heatsealer-01/state/digital-twin
  #   UNS:  zava/redmond-innovation/coating-dev-lab/cam-coat-01/events/safety-incident
  #   UNS:  zava/supply-chain/inbound/shp-012/events/supply-chain
  #   Flat: zava/telemetry/machine-state  (all machines in one topic)

# === Simulation Behaviour ===
simulation:
  # Global time controls
  tickIntervalSec: 1            # main loop tick (how often the scheduler runs)
  timeMode: "realtime"          # "realtime" = wall-clock | "accelerated" = simulated time
  accelerationFactor: 10        # only used when timeMode=accelerated (10x faster)

  # Shift schedule (determines Day/Night in payloads)
  shifts:
    dayStart: "06:00"
    nightStart: "18:00"

  # Active batches (the simulator cycles production through these)
  activeBatches:
    - batchId: "BTC-011"
      product: "ZavaCore Field Standard"
      sku: "ZC Field Standard"
    - batchId: "BTC-012"
      product: "ZavaCore Field Slim"
      sku: "ZC Field Slim"
    - batchId: "BTC-013"
      product: "ZavaCore Systems Pro"
      sku: "ZC Systems Pro"

# === Stream: Equipment Telemetry (site-level) ===
equipmentTelemetry:
  enabled: true
  topic: "zava/telemetry/equipment"   # override per-stream topic (default: {topicPrefix}/equipment)
  intervalSec: 30               # publish every N seconds per equipment
  equipment:                    # which equipment IDs to simulate
    - id: "EQP-001"
      name: "Zava Redmond Innovation Center"
      energyRange: [200, 500]   # kWh range
      humidityRange: [35, 45]   # % range
      productionRate: 0         # R&D site — no production
    - id: "EQP-002"
      name: "Zava Portland Production Campus"
      energyRange: [800, 2500]
      humidityRange: [30, 50]
      productionRate: [10000, 15000]   # units/hr
    - id: "EQP-003"
      name: "Zava Distribution Hub"
      energyRange: [150, 400]
      humidityRange: [35, 45]
      productionRate: 0         # warehouse — no production

# === Stream: Machine State Telemetry (WorkUnit-level) ===
machineStateTelemetry:
  enabled: true
  topic: "zava/telemetry/machine-state"  # override per-stream topic
  lines:                        # which weave lines to simulate
    - name: "WeaveLine-Alpha"
      machinesPerLine: 12       # number of WorkUnit machines (from EQP range)
      equipmentIdStart: 16      # EQP-016 is first machine in Alpha
    - name: "WeaveLine-Bravo"
      machinesPerLine: 12
      equipmentIdStart: 28
    - name: "WeaveLine-Charlie"
      machinesPerLine: 14
      equipmentIdStart: 40
    # ... (all 11 lines configurable, or use "autoDiscover: true")
  autoDiscover: true            # auto-generate all 11 lines with 12-14 machines each
  totalMachines: 134            # override: total machines across all lines
  stateTransition:
    minDwellSec: 5              # minimum time in a state before transition
    maxDwellSec: 300            # maximum time in a state
    probabilities:              # transition probability weights
      Running: 0.70
      Stopped: 0.10
      Blocked: 0.05
      Waiting: 0.10
      Idle: 0.05
    errorProbability: 0.02      # chance of error code on Stopped/Blocked
    errorCodes: ["E101", "E202", "E303", "E404"]

# === Stream: Process Segment Telemetry ===
processSegmentTelemetry:
  enabled: true
  topic: "zava/telemetry/process-segment"  # override per-stream topic
  intervalSec: 30
  segments:
    - id: "SEG-029"
      type: "Coating"
      temperatureRange: [80, 95]
      moistureRange: [3.0, 5.0]
      cycleTimeRange: [100, 120]
    - id: "SEG-030"
      type: "Coating"
      temperatureRange: [80, 95]
      moistureRange: [3.0, 5.0]
      cycleTimeRange: [100, 120]
  autoGenerate:                 # optionally generate additional segments
    enabled: false
    count: 5
    types: ["Coating", "Weaving", "SensorEmbed", "Packaging"]

# === Stream: Production Counter Telemetry ===
productionCounterTelemetry:
  enabled: true
  topic: "zava/telemetry/production-counter"  # override per-stream topic
  intervalSec: 30               # publish every N seconds per machine
  unitCountIncrementRange: [0, 25]      # delta per interval
  fiberProducedGramRange: [0, 100]
  rejectRate: 0.02              # 2% reject probability
  oeeRange: [0.75, 0.95]
  votRange: [0, 1800]
  loadingTimeBase: 20000        # base loading time in seconds

# === Stream: Safety Incident Events (camera-detected) ===
safetyIncidentEvents:
  enabled: true
  topic: "zava/telemetry/safety-incident"  # override per-stream topic
  minIntervalSec: 60            # minimum seconds between incidents
  maxIntervalSec: 1800          # maximum seconds between incidents (30 min)
  cameras:
    - id: "CAM-WH-A-01"
      zone: "Weave Hall A"
      equipmentId: "EQP-005"
    - id: "CAM-WH-A-02"
      zone: "Weave Hall A"
      equipmentId: "EQP-005"
    - id: "CAM-WH-A-03"
      zone: "Weave Hall A"
      equipmentId: "EQP-005"
    - id: "CAM-WH-B-01"
      zone: "Weave Hall B"
      equipmentId: "EQP-006"
    - id: "CAM-WH-B-02"
      zone: "Weave Hall B"
      equipmentId: "EQP-006"
    - id: "CAM-QA-01"
      zone: "QA & Testing Laboratory"
      equipmentId: "EQP-007"
    - id: "CAM-WH-FG-01"
      zone: "Finished Goods Warehouse"
      equipmentId: "EQP-008"
    - id: "CAM-COAT-01"
      zone: "Coating Development Lab"
      equipmentId: "EQP-004"
  incidentTypes:
    - type: "ppe_violation"
      severity: "Warning"
      weight: 0.30              # probability weight
      descriptions:
        - "Worker detected without safety goggles near {zone}"
        - "Hard hat not detected on personnel in {zone}"
        - "Missing high-visibility vest detected in {zone}"
    - type: "unauthorized_zone_entry"
      severity: "Warning"
      weight: 0.15
      descriptions:
        - "Unauthorized badge detected entering restricted area in {zone}"
        - "Unregistered person detected in controlled zone {zone}"
    - type: "spill_detected"
      severity: "Warning"
      weight: 0.12
      descriptions:
        - "Liquid spill detected on floor near equipment in {zone}"
        - "Chemical spill detected — cleanup required in {zone}"
    - type: "blocked_exit"
      severity: "Critical"
      weight: 0.08
      descriptions:
        - "Emergency exit blocked by pallets in {zone}"
        - "Fire exit obstructed in {zone}"
    - type: "forklift_near_miss"
      severity: "Critical"
      weight: 0.10
      descriptions:
        - "Forklift near-miss with pedestrian detected in {zone}"
        - "Forklift speed violation in pedestrian area {zone}"
    - type: "fire_smoke_detected"
      severity: "Critical"
      weight: 0.05
      descriptions:
        - "Smoke detected by visual analytics in {zone}"
        - "Thermal anomaly with visible haze in {zone}"
    - type: "fallen_object"
      severity: "Warning"
      weight: 0.10
      descriptions:
        - "Object fallen from racking detected in {zone}"
        - "Unsecured load detected on upper shelf in {zone}"
    - type: "person_down"
      severity: "Critical"
      weight: 0.10
      descriptions:
        - "Person motionless on floor detected in {zone}"
        - "Possible injury — person down in {zone}"
  confidenceRange: [0.75, 0.99] # AI model confidence score range
  imageRefTemplate: "blob://safety-captures/{year}/{month}/{day}/{cameraId}_{timestamp}.jpg"

# === Stream: Predictive Maintenance Signals ===
predictiveMaintenanceSignals:
  enabled: true
  topic: "zava/telemetry/predictive-maintenance"
  intervalSec: 10               # publish every N seconds per machine
  machines: "auto"              # "auto" = all WorkUnit machines, or list specific EQP IDs
  vibrationRange: [0.5, 4.0]    # mm/s — normal operating range
  bearingTempRange: [40, 75]    # °C — normal range
  acousticDBRange: [65, 90]     # dB — normal range
  motorCurrentRange: [10, 20]   # Amps
  spindleSpeedRange: [2800, 3600]  # RPM
  degradation:
    enabled: true
    degradationRatePerHour: 0.002   # health score decrease per hour
    criticalThreshold: 0.40         # health score below this = critical
    warningThreshold: 0.60          # health score below this = degrading
    resetOnMaintenance: true        # reset health when machine enters Maintenance state
    machinesWithDegradation: 5      # how many machines are actively degrading

# === Stream: Digital Twin State Sync ===
digitalTwinStateSync:
  enabled: true
  topic: "zava/telemetry/digital-twin"
  heartbeatIntervalSec: 60      # publish heartbeat even if no state change
  retainMessages: true           # use MQTT retain flag
  statuses:
    - "Producing"
    - "ProducingAtRate"
    - "Idle"
    - "Setup"
    - "Maintenance"
    - "Changeover"
    - "Blocked"
    - "ScheduledDowntime"
    - "UnscheduledDowntime"
  transitionProbabilities:
    Producing: 0.60
    Idle: 0.10
    Setup: 0.08
    Maintenance: 0.05
    Changeover: 0.07
    Blocked: 0.04
    ScheduledDowntime: 0.03
    UnscheduledDowntime: 0.02
    ProducingAtRate: 0.01
  recipes:                       # recipe assignments per SKU
    - sku: "ZC Field Standard"
      recipeId: "RCP-FS-001"
      targetSpeedPct: 85
    - sku: "ZC Field Slim"
      recipeId: "RCP-SL-001"
      targetSpeedPct: 80
    - sku: "ZC Systems Pro"
      recipeId: "RCP-SP-001"
      targetSpeedPct: 75

# === Stream: Material Consumption Events ===
materialConsumptionEvents:
  enabled: true
  topic: "zava/telemetry/material-consumption"
  minIntervalSec: 30            # min seconds between draw events per segment
  maxIntervalSec: 120           # max seconds between draw events per segment
  materials:                     # BOM expected quantities per segment type (kg)
    Coating:
      - materialId: "MAT-002"
        expectedPerBatch: 15.0
      - materialId: "MAT-003"
        expectedPerBatch: 8.0
      - materialId: "MAT-005"
        expectedPerBatch: 10.0
    Weaving:
      - materialId: "MAT-011"
        expectedPerBatch: 5.0
      - materialId: "MAT-022"
        expectedPerBatch: 2.0
    SensorEmbed:
      - materialId: "MAT-012"
        expectedPerBatch: 3.0
      - materialId: "MAT-013"
        expectedPerBatch: 1.5
      - materialId: "MAT-014"
        expectedPerBatch: 2.5
    Packaging:
      - materialId: "MAT-015"
        expectedPerBatch: 4.0
      - materialId: "MAT-016"
        expectedPerBatch: 6.0
  variancePctRange: [-20, 10]   # simulate over/under consumption vs BOM

# === Stream: Quality Inspection Image Events ===
qualityVisionEvents:
  enabled: true
  topic: "zava/telemetry/quality-vision"
  intervalSec: 10               # one inspection every N seconds per station
  passRate: 0.92                # 92% of inspections pass
  marginalRate: 0.03            # 3% marginal (remaining 5% = fail)
  stations:                      # one vision station per line
    - id: "VISC-WL-A-01"
      lineName: "WeaveLine-Alpha"
      equipmentId: "EQP-020"
    - id: "VISC-WL-B-01"
      lineName: "WeaveLine-Bravo"
      equipmentId: "EQP-034"
    - id: "VISC-WL-C-01"
      lineName: "WeaveLine-Charlie"
      equipmentId: "EQP-048"
    - id: "VISC-WL-D-01"
      lineName: "WeaveLine-Delta"
      equipmentId: "EQP-054"
    - id: "VISC-WL-E-01"
      lineName: "WeaveLine-Echo"
      equipmentId: "EQP-066"
    - id: "VISC-WL-F-01"
      lineName: "WeaveLine-Foxtrot"
      equipmentId: "EQP-072"
    - id: "VISC-WL-G-01"
      lineName: "WeaveLine-Golf"
      equipmentId: "EQP-083"
    - id: "VISC-WL-H-01"
      lineName: "WeaveLine-Hotel"
      equipmentId: "EQP-088"
    - id: "VISC-WL-I-01"
      lineName: "WeaveLine-India"
      equipmentId: "EQP-100"
    - id: "VISC-WL-J-01"
      lineName: "WeaveLine-Juliet"
      equipmentId: "EQP-112"
    - id: "VISC-WL-K-01"
      lineName: "WeaveLine-Kilo"
      equipmentId: "EQP-124"
  defectTypes:
    - type: "fiber_tear"
      weight: 0.25
    - type: "coating_gap"
      weight: 0.20
    - type: "sensor_misalignment"
      weight: 0.15
    - type: "delamination"
      weight: 0.10
    - type: "contamination"
      weight: 0.10
    - type: "mesh_distortion"
      weight: 0.08
    - type: "solder_bridge"
      weight: 0.07
    - type: "label_skew"
      weight: 0.05
  confidenceRange: [0.70, 0.99]
  modelVersion: "yolov8-zava-defect-v3.2"
  imageRefTemplate: "blob://quality-vision/{year}/{month}/{day}/{stationId}_{timestamp}.jpg"

# === Stream: Supply Chain Inbound Alerts ===
supplyChainAlerts:
  enabled: true
  topic: "zava/telemetry/supply-chain"
  minIntervalSec: 300           # min seconds between status updates per shipment
  maxIntervalSec: 3600          # max seconds (1 hour)
  activeShipments:               # shipments currently being tracked
    - shipmentId: "SHP-011"
      trackingNum: "TRK-2025-5011"
      carrier: "EuroAir Cargo"
      originEquipmentId: "EQP-011"
      destEquipmentId: "EQP-001"
      materialIds: ["MAT-003"]
      initialStatus: "InTransit"
    - shipmentId: "SHP-012"
      trackingNum: "TRK-2025-5012"
      carrier: "TaiwanCargo Express"
      originEquipmentId: "EQP-012"
      destEquipmentId: "EQP-001"
      materialIds: ["MAT-004"]
      initialStatus: "InTransit"
    - shipmentId: "SHP-014"
      trackingNum: "TRK-2025-5014"
      carrier: "TransAtlantic Freight"
      originEquipmentId: "EQP-014"
      destEquipmentId: "EQP-002"
      materialIds: ["MAT-016", "MAT-017", "MAT-018", "MAT-019"]
      initialStatus: "Pending"
  statusFlow: ["Booked", "PickedUp", "InTransit", "CustomsHold", "OutForDelivery", "Delivered"]
  delayProbability: 0.15         # 15% chance of delay at any transition
  exceptionProbability: 0.03     # 3% chance of exception (lost, damaged)
  delayReasons:
    - "Port congestion"
    - "Customs inspection"
    - "Weather delay"
    - "Carrier equipment failure"
    - "Documentation missing"
    - "Capacity shortage"
  impactedBatchLookup: true      # resolve downstream impact via material → segment → batch

# === Anomaly Injection ===
anomalies:
  enabled: true
  defaultTopic: "zava/anomalies"   # default topic for anomaly events (overridable per scenario)
  scenarioIntervalMin: 15       # inject an anomaly scenario every N minutes
  scenarios:
    - name: "temperature_spike"
      enabled: true              # toggle this scenario on/off
      description: "Coating temperature exceeds safe range"
      topic: "zava/anomalies/process-segment"
      stream: "processSegmentTelemetry"
      durationSec: 120
      overrides:
        temperatureRange: [105, 130]
    - name: "oee_drop"
      enabled: true
      description: "OEE drops on a line due to machine issues"
      topic: "zava/anomalies/production-counter"
      stream: "productionCounterTelemetry"
      durationSec: 300
      overrides:
        oeeRange: [0.30, 0.50]
        rejectRate: 0.15
    - name: "machine_cascade_failure"
      enabled: true
      description: "Multiple machines on one line go to Stopped/Blocked"
      topic: "zava/anomalies/machine-state"
      stream: "machineStateTelemetry"
      durationSec: 180
      overrides:
        probabilities:
          Stopped: 0.50
          Blocked: 0.30
          Running: 0.10
          Waiting: 0.05
          Idle: 0.05
        errorProbability: 0.40
    - name: "bearing_failure_imminent"
      enabled: true
      description: "Rapid bearing degradation on a machine — health score drops to critical"
      topic: "zava/anomalies/predictive-maintenance"
      stream: "predictiveMaintenanceSignals"
      durationSec: 600
      overrides:
        vibrationRange: [6.0, 12.0]
        bearingTempRange: [90, 120]
        healthScoreOverride: 0.20
    - name: "material_overconsumption"
      enabled: true
      description: "A segment consumes 30%+ more material than BOM expected"
      topic: "zava/anomalies/material-consumption"
      stream: "materialConsumptionEvents"
      durationSec: 300
      overrides:
        variancePctRange: [25, 50]
    - name: "vision_defect_surge"
      enabled: true
      description: "Sudden spike in defect rate on a line (quality crisis)"
      topic: "zava/anomalies/quality-vision"
      stream: "qualityVisionEvents"
      durationSec: 240
      overrides:
        passRate: 0.55
        marginalRate: 0.15
    - name: "shipment_critical_delay"
      enabled: true
      description: "Key shipment delayed with high downstream impact"
      topic: "zava/anomalies/supply-chain"
      stream: "supplyChainAlerts"
      durationSec: 0             # single event, no duration
      overrides:
        forceStatus: "Delayed"
        delayDays: 5
        riskLevel: "Critical"

# === Logging & Observability ===
logging:
  level: "INFO"                 # DEBUG | INFO | WARNING | ERROR
  format: "json"                # "json" | "text"
  publishMetrics: true          # emit internal metrics to stdout
  metricsIntervalSec: 60        # print throughput stats every N seconds
```

---

## 4. Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | **Python 3.12** | Matches existing demo tooling; rich MQTT libraries |
| MQTT Client | **paho-mqtt v2** | Industry standard, supports MQTTv5, TLS, SAT auth |
| Config | **PyYAML + Pydantic** | Type-safe config parsing with validation |
| Container | **python:3.12-slim** | Small image (~150MB) |
| Orchestration | **asyncio** | Non-blocking I/O for concurrent stream publishing |

---

## 5. Project Structure

```
ZavaManufacturing-ISA95/mqtt-simulator/
├── PLAN.md                          ← this document
├── Dockerfile
├── requirements.txt
├── simulator-config.yaml            ← default configuration
├── src/
│   ├── __init__.py
│   ├── main.py                      ← entrypoint: load config, start streams
│   ├── config.py                    ← Pydantic models for config validation
│   ├── mqtt_client.py               ← MQTT connection management (connect, reconnect, TLS, SAT)
│   ├── streams/
│   │   ├── __init__.py
│   │   ├── base.py                  ← abstract base stream class
│   │   ├── equipment_telemetry.py   ← site-level energy/humidity/production
│   │   ├── machine_state.py         ← state machine for WorkUnit machines
│   │   ├── process_segment.py       ← coating/weaving/sensor/packaging telemetry
│   │   ├── production_counter.py    ← OEE, unit counts, fiber production
│   │   ├── safety_incident.py       ← camera-based safety incident events
│   │   ├── predictive_maintenance.py ← vibration, bearing temp, health score
│   │   ├── digital_twin.py          ← ISA-95 state sync with retain flag
│   │   ├── material_consumption.py  ← real-time BOM tracking per segment
│   │   ├── quality_vision.py        ← in-line defect detection results
│   │   └── supply_chain.py          ← inbound shipment status & delay alerts
│   ├── anomaly_engine.py            ← periodic anomaly injection (per-scenario enable/disable)
│   └── utils.py                     ← shift calculation, random helpers
└── k8s/
    ├── namespace.yaml               ← optional: dedicated namespace
    ├── configmap.yaml               ← mounts simulator-config.yaml
    ├── deployment.yaml              ← Pod spec with resource limits
    ├── service-account.yaml         ← SAT auth for MQTT broker (if needed)
    └── kustomization.yaml           ← single "kubectl apply -k" deployment
```

---

## 6. Kubernetes Deployment

### 6.1 Resource Requirements
- **CPU**: 100m request / 500m limit (single pod is sufficient)
- **Memory**: 128Mi request / 256Mi limit
- **Replicas**: 1 (single instance; no scaling needed for simulation)

### 6.2 MQTT Broker Connection
The Azure IoT Operations MQTT broker is typically available at:
- **In-cluster**: `aio-broker.azure-iot-operations.svc.cluster.local:1883` (non-TLS) or `:8883` (TLS)
- **Authentication**: Service Account Token (SAT) — the pod's Kubernetes service account is mapped to an IoT Operations `BrokerAuthorization` policy

### 6.3 Deployment Command
```bash
# Deploy everything with Kustomize
kubectl apply -k ZavaManufacturing-ISA95/mqtt-simulator/k8s/

# Or individual resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/service-account.yaml
kubectl apply -f k8s/deployment.yaml
```

### 6.4 Runtime Controls
```bash
# Check simulator logs
kubectl logs -f deployment/zava-simulator -n zava-simulator

# Update config on the fly (ConfigMap update + pod restart)
kubectl create configmap zava-simulator-config \
  --from-file=simulator-config.yaml=simulator-config.yaml \
  -n zava-simulator --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/zava-simulator -n zava-simulator

# Scale down to stop simulation
kubectl scale deployment zava-simulator --replicas=0 -n zava-simulator
```

---

## 7. Key Design Decisions

| Decision | Choice | Alternatives Considered |
|----------|--------|------------------------|
| **Single pod vs DaemonSet** | Single pod | DaemonSet would spread load but is unnecessary for simulation |
| **Async vs Threading** | asyncio | Threads add complexity; asyncio handles I/O-bound MQTT well |
| **Config format** | YAML ConfigMap | ENV vars (too verbose), JSON (less readable) |
| **Message format** | JSON | Avro/Protobuf (over-engineering for demo), CSV (poor MQTT fit) |
| **Time mode** | Realtime + Accelerated | Allows both demo (fast) and realistic (wall-clock) usage |
| **Anomaly injection** | Built-in engine | External chaos tools (too heavy for demo) |

---

## 8. Configurable Parameters Summary

| Parameter | What It Controls | Default |
|-----------|-----------------|---------|
| `mqtt.broker` | MQTT broker hostname | `aio-broker...svc.cluster.local` |
| `mqtt.port` | Broker port | `1883` |
| `mqtt.useTls` / `mqtt.authMethod` | Security configuration | `false` / `serviceAccountToken` |
| `mqtt.qos` | Delivery guarantee | `1` |
| `topicPrefix` | Default MQTT topic prefix (flat mode) | `zava/telemetry` |
| `topicMode` | Topic structure: `flat` or `uns` | `uns` |
| `uns.enterprise` | UNS root enterprise name | `zava` |
| `uns.hierarchy` | ISA-95 site/area/line mapping for UNS paths | Per equipment |
| `uns.categories` | Which streams map to telemetry/events/state | Per stream |
| `<stream>.topic` | Per-stream topic override (flat mode only) | `{topicPrefix}/{stream-name}` |
| `simulation.tickIntervalSec` | Scheduler resolution | `1` sec |
| `simulation.timeMode` | Real-time vs accelerated | `realtime` |
| `simulation.accelerationFactor` | Speed multiplier in accelerated mode | `10` |
| `equipmentTelemetry.intervalSec` | Site telemetry frequency | `30` sec |
| `equipmentTelemetry.equipment[]` | Which sites + value ranges | 3 sites |
| `machineStateTelemetry.lines[]` | Which lines + machine count | 11 lines, 134 machines |
| `machineStateTelemetry.stateTransition.*` | State machine behaviour | 70% Running |
| `processSegmentTelemetry.intervalSec` | Segment telemetry frequency | `30` sec |
| `processSegmentTelemetry.segments[]` | Active segments + ranges | 2 segments |
| `productionCounterTelemetry.intervalSec` | Counter frequency | `30` sec |
| `productionCounterTelemetry.*Range` | OEE, fiber, reject ranges | Per field |
| `safetyIncidentEvents.enabled` | Toggle safety incident stream | `true` |
| `safetyIncidentEvents.topic` | Safety incident MQTT topic | `zava/telemetry/safety-incident` |
| `safetyIncidentEvents.min/maxIntervalSec` | Incident frequency range | `60`–`1800` sec |
| `safetyIncidentEvents.cameras[]` | Camera IDs, zones, equipment mapping | 8 cameras |
| `safetyIncidentEvents.incidentTypes[]` | Incident types, severity, weights | 8 types |
| `safetyIncidentEvents.confidenceRange` | AI model confidence score | `[0.75, 0.99]` |
| `predictiveMaintenanceSignals.enabled` | Toggle predictive maintenance stream | `true` |
| `predictiveMaintenanceSignals.topic` | Predictive maintenance MQTT topic | `zava/telemetry/predictive-maintenance` |
| `predictiveMaintenanceSignals.intervalSec` | Sensor reading frequency | `10` sec |
| `predictiveMaintenanceSignals.degradation.*` | Degradation curve settings | 5 machines degrading |
| `digitalTwinStateSync.enabled` | Toggle digital twin stream | `true` |
| `digitalTwinStateSync.topic` | Digital twin MQTT topic | `zava/telemetry/digital-twin` |
| `digitalTwinStateSync.retainMessages` | Use MQTT retain flag | `true` |
| `digitalTwinStateSync.heartbeatIntervalSec` | Heartbeat frequency | `60` sec |
| `materialConsumptionEvents.enabled` | Toggle material consumption stream | `true` |
| `materialConsumptionEvents.topic` | Material consumption MQTT topic | `zava/telemetry/material-consumption` |
| `materialConsumptionEvents.materials` | BOM expected quantities per segment type | Per material |
| `qualityVisionEvents.enabled` | Toggle quality vision stream | `true` |
| `qualityVisionEvents.topic` | Quality vision MQTT topic | `zava/telemetry/quality-vision` |
| `qualityVisionEvents.passRate` | Inspection pass rate | `0.92` |
| `qualityVisionEvents.stations[]` | Vision stations per line | 11 stations |
| `supplyChainAlerts.enabled` | Toggle supply chain stream | `true` |
| `supplyChainAlerts.topic` | Supply chain MQTT topic | `zava/telemetry/supply-chain` |
| `supplyChainAlerts.delayProbability` | Chance of delay per status transition | `0.15` |
| `supplyChainAlerts.activeShipments[]` | Shipments to track | 3 shipments |
| `anomalies.enabled` | Toggle anomaly injection | `true` |
| `anomalies.defaultTopic` | Default MQTT topic for anomaly events | `zava/anomalies` |
| `anomalies.scenarioIntervalMin` | How often anomalies fire | `15` min |
| `anomalies.scenarios[].topic` | Per-scenario topic override | `{defaultTopic}/{stream}` |
| `anomalies.scenarios[].enabled` | Toggle individual anomaly scenarios | `true` |
| `anomalies.scenarios[]` | Customisable anomaly types | 7 built-in |
| `logging.level` | Log verbosity | `INFO` |

---

## 9. IoT Operations → Fabric Eventhouse Integration

The simulator only concerns the **edge side** (pod → MQTT broker). The remaining data pipeline is configured in Azure IoT Operations:

1. **Data flow** in IoT Operations routes MQTT topics to Fabric Eventhouse
2. **Topic mapping** — each topic maps to one Eventhouse table:
   | MQTT Topic | Eventhouse Table |
   |------------|-----------------|
   | `zava/telemetry/equipment` | `EquipmentTelemetry` |
   | `zava/telemetry/machine-state` | `MachineStateTelemetry` |
   | `zava/telemetry/process-segment` | `ProcessSegmentTelemetry` |
   | `zava/telemetry/production-counter` | `ProductionCounterTelemetry` |
   | `zava/telemetry/safety-incident` | `SafetyIncidentEvents` |
   | `zava/telemetry/predictive-maintenance` | `PredictiveMaintenanceTelemetry` |
   | `zava/telemetry/digital-twin` | `DigitalTwinState` |
   | `zava/telemetry/material-consumption` | `MaterialConsumptionEvents` |
   | `zava/telemetry/quality-vision` | `QualityVisionEvents` |
   | `zava/telemetry/supply-chain` | `SupplyChainAlerts` |
3. **Schema alignment** — JSON payloads use the exact column names from the existing CSVs, so Eventhouse ingestion mapping is 1:1

---

## 10. Implementation Phases

### Phase 1 — Core Simulator (this PR)
- [ ] Python project with asyncio-based stream publishers
- [ ] Pydantic config model + YAML loading with per-stream `enabled` flags
- [ ] 4 core telemetry streams (Equipment, MachineState, ProcessSegment, ProductionCounter)
- [ ] Safety Incident Events stream
- [ ] MQTT client with reconnect logic + retain support
- [ ] Dockerfile + K8s manifests

### Phase 2 — Advanced Streams
- [ ] Predictive Maintenance Signals (with degradation curves)
- [ ] Digital Twin State Sync (retained MQTT messages, ISA-95 status model)
- [ ] Material Consumption Events (BOM tracking + variance)
- [ ] Quality Inspection Image Events (vision-based defect detection)
- [ ] Supply Chain Inbound Alerts (shipment lifecycle + downstream impact)

### Phase 3 — Anomaly Engine
- [ ] Scheduled anomaly injection with per-scenario `enabled` toggle
- [ ] 7 built-in scenarios across all streams
- [ ] Anomalies publish to separate topic tree

### Phase 4 — Observability & Polish
- [ ] Structured JSON logging with throughput metrics per stream
- [ ] Health check endpoint (optional HTTP liveness probe)
- [ ] Helm chart (optional, for parameterised deployment)

---

## 11. Validation Checklist

After deployment, verify:

1. **Pod is running**: `kubectl get pods -n zava-simulator`
2. **Logs show publishing**: `kubectl logs -f deployment/zava-simulator`
3. **MQTT messages arrive**: Use `mqttui` or `mosquitto_sub` on the cluster to subscribe to `zava/telemetry/#` and `zava/anomalies/#`
4. **Data in Eventhouse**: Query all 10 telemetry tables in Fabric KQL DB and confirm rows with recent timestamps
5. **Digital Twin retained**: Subscribe to `zava/telemetry/digital-twin` — should receive latest state immediately
6. **Anomaly scenarios**: Wait for scenario interval and verify anomaly events on `zava/anomalies/#`
5. **Schema match**: Verify column names and types match the existing Eventhouse table definitions
