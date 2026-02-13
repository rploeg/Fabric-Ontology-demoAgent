# Golden Leaf Tea Co. - Tea Bag Manufacturing Demo (ISA-95 / OPC UA)

A Microsoft Fabric Ontology demo showcasing end-to-end traceability for tea bag manufacturing, aligned with ISA-95 (IEC 62264) equipment hierarchy and OPC UA information models.

---

## Overview

| Attribute | Value |
|-----------|-------|
| **Company** | Golden Leaf Tea Co. (fictional) |
| **Industry** | Food & Beverage - Tea Manufacturing |
| **Domain** | Make & Quality (ISA-95 L1) |
| **Standard** | ISA-95 / IEC 62264, OPC UA |
| **Entities** | 8 |
| **Relationships** | 10 |
| **Timeseries Entities** | 2 entities, 4 KQL tables (~20.5M rows) |
| **Demo Timeline** | July 2025 – July 2026 |

### Use Cases Demonstrated

1. **Batch-to-Estate Traceability** — Trace quality issues back through blending to source tea estates
2. **Supply Chain Risk Assessment** — Identify production impact from supplier disruptions (e.g., monsoon)
3. **Quality-Telemetry Correlation** — Correlate failed taste tests with OPC UA sensor anomalies (moisture, temperature)
4. **Full Production Genealogy** — Complete HACCP/BRC audit trail from finished goods to raw materials
5. **Inbound Logistics Tracking** — Track material shipments and identify delay risks for packing schedules

### ISA-95 Process Hierarchy (from Process Diagram)

```
L0: Supply Chain
└── L1: Make & Quality
    ├── L2: Blend Scheduling        → ProductionOrder, ProductBatch planning
    ├── L2: Tea Blending            → ProcessSegment [Blending]
    ├── L2: Packing Line Scheduling → ProductionOrder scheduling
    ├── L2: Packing Execution       → ProcessSegment [Filling, Sealing, Packaging]
    ├── L2: Quality Management      → QualityTest (taste, weight, moisture, contamination)
    ├── L2: Shop Floor Control      → Equipment telemetry (OPC UA)
    ├── L2: Materials Mgmt in Make  → Material, Shipment, inbound/outbound logistics
    └── L2: Plant Maintenance       → Equipment lifecycle
```

---

## Entity Summary

| Entity | ISA-95 Concept | Description | Key | Timeseries |
|--------|---------------|-------------|-----|------------|
| ProductBatch | Material Lot | Batch of finished tea bags (English Breakfast, Earl Grey, etc.) | BatchId | ❌ |
| ProcessSegment | Process Segment | Manufacturing step: Blending, Filling, Sealing, Packaging | SegmentId | ✅ Temperature, MoistureContent, CycleTime |
| Material | Material Definition | Raw materials (tea, herbs) and packaging (filter paper, boxes) | MaterialId | ❌ |
| Supplier | External Provider | Tea estates (Darjeeling, Assam, Ceylon) and packaging suppliers | SupplierId | ❌ |
| Equipment | Equipment Hierarchy | ISA-95 Sites, Areas, WorkCenters, WorkUnits — 160 items incl. 134 machines | EquipmentId | ✅ EnergyConsumption, Humidity, ProductionRate, MachineState, ErrorCode, BagCount, OEE, ... |
| ProductionOrder | Production Schedule | Work orders for tea bag production runs | OrderId | ❌ |
| QualityTest | Quality Test Ops | Taste tests, weight checks, moisture analysis, contamination tests | TestId | ❌ |
| Shipment | Logistics | Inbound raw materials and outbound finished goods | ShipmentId | ❌ |

---

## Folder Structure

```
TeaManufacturing-ISA95/
├── README.md                              # This file
├── demo-questions.md                      # 5 sample GQL queries
├── ontology-structure.md                  # Entity/relationship design
├── Bindings/
│   ├── bindings.yaml                      # Machine-readable bindings
│   ├── lakehouse-binding.md               # Lakehouse setup guide
│   └── eventhouse-binding.md              # Eventhouse (OPC UA telemetry) guide
├── Data/
│   ├── Lakehouse/                         # Dimension, Fact, Edge tables
│   │   ├── DimProductBatch.csv            # 20 tea bag production batches
│   │   ├── DimProcessSegment.csv          # 30 process segments (Blending→Packaging)
│   │   ├── DimMaterial.csv                # 25 materials (tea leaves, packaging)
│   │   ├── DimSupplier.csv                # 10 suppliers (estates + packaging)
│   │   ├── DimEquipment.csv               # 160 equipment items (ISA-95 full hierarchy incl. machines)
│   │   ├── DimProductionOrder.csv         # 20 production orders
│   │   ├── FactQualityTest.csv            # 30 quality tests (incl. 4 failures)
│   │   ├── FactShipment.csv               # 25 shipments (inbound + outbound)
│   │   ├── EdgeSegmentMaterial.csv        # Process → Material (many-to-many)
│   │   ├── EdgeShipmentMaterial.csv       # Shipment → Material (many-to-many)
│   │   ├── EdgeShipmentOrigin.csv         # Shipment → origin Equipment
│   │   └── EdgeShipmentDestination.csv    # Shipment → destination Equipment
│   └── Eventhouse/                        # OPC UA-style timeseries data
│       ├── ProcessSegmentTelemetry.csv    # 525K rows — Temperature, Moisture, CycleTime
│       ├── EquipmentTelemetry.csv         # 263K rows — Energy, Humidity, ProductionRate
│       ├── MachineStateTelemetry.csv      # 6.4M rows — Machine state transitions (real-scale)
│       └── ProductionCounterTelemetry.csv # 13.3M rows — Bag counts, OEE, waste (real-scale)
├── scripts/
│   └── transform_real_data.py             # Data transformation script (real → demo)
└── Ontology/
    ├── tea-manufacturing.ttl              # RDF/Turtle ontology (ISA-95 annotated)
    └── ontology-diagram-slide.html        # Interactive ER diagram
```

---

## Prerequisites

Before deploying this demo, ensure you have:

1. **Microsoft Fabric workspace** with:
   - Lakehouse capability
   - Eventhouse / KQL Database capability
   - Ontology (Graph) capability
2. **Workspace permissions**: Admin or Contributor role
3. **OneLake Security**: Must be **DISABLED** on the Lakehouse

---

## Quick Start

### Step 1: Create Lakehouse
1. Create a new Lakehouse named `TeaManufacturing_Lakehouse`
2. Upload all CSV files from `Data/Lakehouse/` to the `Files/` folder
3. Create tables from each CSV file (right-click → "Load to Table")

### Step 2: Create Eventhouse
1. Create a new Eventhouse named `TeaManufacturing_Telemetry`
2. Create KQL database `TeaManufacturingDB`
3. Follow instructions in `Bindings/eventhouse-binding.md`

### Step 3: Upload Ontology
1. Create a new Graph (Ontology) item
2. Upload `Ontology/tea-manufacturing.ttl`
3. Verify 8 entity types appear

### Step 4: Bind Data
1. Follow `Bindings/lakehouse-binding.md` for entity + relationship bindings
2. Follow `Bindings/eventhouse-binding.md` for timeseries bindings
3. Verify all 10 relationships are bound

### Step 5: Test Queries
1. Open the Graph query editor
2. Run queries from `demo-questions.md`
3. Verify results match expected outputs

---

## Data Summary

| Category | Count | Details |
|----------|-------|---------|
| **Tea Products** | 8 | English Breakfast, Earl Grey, Green Tea, Chamomile, Darjeeling, Kenyan Bold, Nilgiri Frost, Sencha Green |
| **Suppliers** | 10 | 6 tea estates (India, Sri Lanka, China, Egypt, Kenya) + 4 packaging suppliers (Germany, USA, UK, Italy) |
| **Materials** | 25 | 10 raw materials (teas, herbs, oils) + 15 packaging materials |
| **Process Steps** | 4 | Blending → Filling → Sealing → Packaging |
| **Equipment** | 160 | 3 sites, 4 areas, 2+11 work centers, 134 work-unit machines, 8 supplier depots |
| **Quality Tests** | 30 | Including 4 failures (taste, moisture, weight, visual seal defect) |

---

## Key Differences from Automotive Demo

| Aspect | Automotive (NextGen Motors) | Tea Manufacturing (Golden Leaf) |
|--------|---------------------------|--------------------------------|
| **Standard** | General manufacturing | ISA-95 / OPC UA |
| **Product** | Vehicles (discrete) | Tea bag batches (process/batch) |
| **Assembly → Process** | Assembly (Engine, Chassis, Body) | ProcessSegment (Blending, Filling, Sealing, Packaging) |
| **Component → Material** | Components (parts) | Materials (tea leaves, packaging) with ISA-95 Material Class |
| **Facility → Equipment** | Facilities (plants) | Equipment with ISA-95 hierarchy levels (Site/Area/WorkCenter) |
| **Quality** | QualityEvent (inspection, defect) | QualityTest (taste test, moisture analysis, contamination) |
| **Telemetry** | Vehicle sensor data | OPC UA PLC tags (temperature, moisture, energy) + real-scale machine state (6.4M rows) and production counters/OEE (13.3M rows) |
| **Traceability** | VIN-based vehicle genealogy | Batch-based HACCP/BRC compliance |

---

## OPC UA Information Model

The timeseries properties reference OPC UA NodeIds in the ontology TTL, simulating how real manufacturing data would flow from PLCs:

```
Tea Blender PLC (OPC UA Server)
├── ns=2;s=Segment.Temperature      → 65-90°C depending on tea type
├── ns=2;s=Segment.MoistureContent  → 1.5-9% (critical for quality)
└── ns=2;s=Segment.CycleTime        → 1-142 seconds per cycle

Site/Area PLCs (OPC UA Server)
├── ns=2;s=Equipment.EnergyConsumption → kWh per hour
├── ns=2;s=Equipment.Humidity          → Controlled environment 20-75%
└── ns=2;s=Equipment.ProductionRate    → 0-160 bags/hour

Packing Line MES / Machine PLCs (OPC UA Server)
├── ns=2;s=Equipment.State.MachineState → Running, Stopped, Blocked, Waiting, Idle
├── ns=2;s=Equipment.State.ErrorCode    → PLC alarm codes
├── ns=2;s=Equipment.State.DurationSec  → State duration in seconds
├── ns=2;s=Equipment.Counter.BagCount   → Cumulative bag count
├── ns=2;s=Equipment.Counter.OEE        → Overall Equipment Effectiveness %
├── ns=2;s=Equipment.Counter.VOT        → Valuable Operating Time
└── ns=2;s=Equipment.Counter.LoadingTime → Scheduled production time
```
