# Zava Inc. — Smart Textile Manufacturing (ISA-95 / OPC UA)

> **Ontology-driven demo** for Microsoft Fabric GraphQL, Lakehouse, and Eventhouse
> using the `Demo-automation` CLI tool.

## Company Overview

**Zava Inc.** is a smart textiles manufacturer headquartered in Redmond, WA.
The company produces **ZavaCore™** smart mesh products — conductive fiber textiles
embedded with micro-sensors for applications ranging from consumer athletic wear
to enterprise structural health monitoring.

## Manufacturing Domain

| Concept | Description |
|---------|-------------|
| **Product Line** | ZavaCore Field (consumer) & ZavaCore Systems (enterprise) |
| **Products** | Field Standard, Field Slim, Field Micro, Field Active, Field Flex, Systems Pro, Systems Elite, Systems Compact, Systems Max, Systems Nano |
| **Process Steps** | Coating → Weaving → SensorEmbed → Packaging |
| **Raw Materials** | Graphite fiber, silver nanowire, copper trace ink, FR-4 substrate, conductive polymer coating, carbon nanotube dispersion, PVDF film, TPU film, elastane/nylon yarn |
| **Components** | Sensor modules, flex PCB connectors, micro solder paste, conductive adhesive |
| **Quality Tests** | ConductivityTest, TensileStrength, MeshGaugeCheck, ContaminationTest, VisualInspection, Audit |

## ISA-95 Equipment Hierarchy

```
Site: Zava Redmond Innovation Center (R&D / Coating)
  ├─ Area: Coating Development Lab
  └─ Area: QA & Testing Laboratory

Site: Zava Portland Production Campus
  ├─ WorkCenter: Weave Hall A
  ├─ WorkCenter: Weave Hall B
  │   └─ WorkCenter: WeaveLine-Alpha through WeaveLine-Kilo (11 lines)
  │       └─ WorkUnit: FiberWeaver, Laminator, SensorPlacer, ConductivityTester, ...
  └─ Area: Finished Goods Warehouse

Site: Zava Distribution Hub (Portland)
```

## Ontology Summary

| Metric | Value |
|--------|-------|
| OWL Classes | 8 |
| Object Properties (Relationships) | 10 |
| Datatype Properties | 69 |
| Namespace | `http://example.com/zava-manufacturing-isa95#` |
| TTL File | `Ontology/zava-manufacturing.ttl` |

## Data Summary

### Lakehouse (12 tables)
| Table | Rows | Description |
|-------|------|-------------|
| DimProductBatch | 20 | Smart mesh production batches |
| DimProcessSegment | 30 | Manufacturing steps (Coating/Weaving/SensorEmbed/Packaging) |
| DimMaterial | 25 | Raw materials + components + packaging |
| DimSupplier | 10 | Material suppliers (Japan, S. Korea, Germany, Taiwan, USA, UK, Netherlands) |
| DimEquipment | 160 | Full ISA-95 equipment hierarchy |
| DimProductionOrder | 20 | Work orders |
| FactQualityTest | 30 | Quality test results |
| FactShipment | 25 | Inbound/outbound shipments |
| EdgeSegmentMaterial | 95 | Segment ↔ Material M:N |
| EdgeShipmentMaterial | 58 | Shipment ↔ Material M:N |
| EdgeShipmentOrigin | 25 | Shipment origin FK |
| EdgeShipmentDestination | 25 | Shipment destination FK |

### Eventhouse (4 telemetry tables)
| Table | Seed Rows | Full Rows | Description |
|-------|-----------|-----------|-------------|
| ProcessSegmentTelemetry | 260,640 | 260,640 | Temperature, moisture, cycle time |
| EquipmentTelemetry | 130,320 | 130,320 | Energy, humidity, production rate |
| MachineStateTelemetry | 75,000 | 3,275,601 | Machine state transitions |
| ProductionCounterTelemetry | 50,000 | 6,540,075 | OEE, unit counts, rejection rates |

## Quick Start

```bash
# From the Demo-automation directory
cd ../Demo-automation

# Validate the demo structure
python3 -m demo_automation validate ../ZavaManufacturing-ISA95 --show-details

# Deploy to a Fabric workspace
python3 -m demo_automation setup ../ZavaManufacturing-ISA95

# Run individual steps
python3 -m demo_automation run-step create_lakehouse ../ZavaManufacturing-ISA95
python3 -m demo_automation run-step create_eventhouse ../ZavaManufacturing-ISA95
python3 -m demo_automation run-step upload_ontology ../ZavaManufacturing-ISA95
python3 -m demo_automation run-step bind_entities ../ZavaManufacturing-ISA95
python3 -m demo_automation run-step bind_relationships ../ZavaManufacturing-ISA95
```

## Suppliers

| ID | Name | Tier | Country | Materials |
|----|------|------|---------|-----------|
| SUP-001 | Toray Carbon Fibers | 1 | Japan | Graphite fiber, TPU film |
| SUP-002 | NanoSilver Tech Korea | 1 | South Korea | Silver nanowire |
| SUP-003 | CopperTrace GmbH | 1 | Germany | Copper trace ink |
| SUP-004 | FR4-Global Inc | 1 | Taiwan | FR-4 substrate |
| SUP-005 | PolyCoat Industries | 2 | USA | Sensor modules, barrier film, labels, desiccant, nitrogen, seals |
| SUP-006 | FlexConnect Ltd | 2 | UK | Anti-static bags, cartons, ESD wrap, pallet wrap, certificates |
| SUP-007 | SensorPak GmbH | 1 | Germany | Conductive coating, elastane yarn, nylon yarn |
| SUP-008 | CleanRoom Supplies BV | 2 | Netherlands | Carbon nanotube dispersion |
| SUP-009 | PackSafe Industries | 1 | USA | PVDF film |
| SUP-010 | ShieldTech Corp | 2 | USA | Flex PCB, micro solder paste |
