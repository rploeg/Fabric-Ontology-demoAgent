# NextGen Motors - Automotive Manufacturing & Supply Chain Demo

A Microsoft Fabric Ontology demo showcasing end-to-end traceability from raw materials through suppliers to finished vehicles.

---

## Overview

| Attribute | Value |
|-----------|-------|
| **Company** | NextGen Motors (fictional) |
| **Industry** | Automotive Manufacturing |
| **Domain** | Manufacturing + Supply Chain |
| **Entities** | 8 |
| **Relationships** | 10 |
| **Timeseries Entities** | 2 (Assembly, Facility) |

### Use Cases Demonstrated

1. **Defect-to-Supplier Traceability** - Trace quality issues back through assembly to component suppliers
2. **Supply Chain Risk Assessment** - Identify production impact from supplier disruptions
3. **Quality-Telemetry Correlation** - Correlate defects with manufacturing conditions
4. **Logistics Tracking** - Track inbound shipments and component provenance
5. **Vehicle Genealogy** - Complete manufacturing history for compliance

---

## Entity Summary

| Entity | Description | Key | Timeseries |
|--------|-------------|-----|------------|
| Vehicle | Final assembled vehicle with VIN | VehicleId | ❌ |
| Assembly | Major assemblies (Engine, Chassis, Body, Battery, Interior) | AssemblyId | ✅ Temperature, Torque, CycleTime |
| Component | Parts and sub-assemblies | ComponentId | ❌ |
| Supplier | Tier 1 and Tier 2 suppliers | SupplierId | ❌ |
| Facility | Plants, warehouses, distribution centers | FacilityId | ✅ EnergyConsumption, Humidity, ProductionRate |
| ProductionOrder | Work orders for production | OrderId | ❌ |
| QualityEvent | Inspections, defects, recalls | EventId | ❌ |
| Shipment | Logistics movements | ShipmentId | ❌ |

---

## Folder Structure

```
AutoManufacturing-SupplyChain/
├── README.md                          # This file
├── .demo-metadata.yaml                # Automation metadata
├── demo-questions.md                  # 5 sample GQL queries
├── ontology-structure.md              # Entity/relationship design
├── Bindings/
│   ├── bindings.yaml                  # Machine-readable bindings
│   ├── lakehouse-binding.md           # Lakehouse setup guide
│   └── eventhouse-binding.md          # Eventhouse setup guide
├── Data/
│   ├── Lakehouse/                     # Dimension, Fact, Edge tables
│   │   ├── DimVehicle.csv
│   │   ├── DimAssembly.csv
│   │   ├── DimComponent.csv
│   │   ├── DimSupplier.csv
│   │   ├── DimFacility.csv
│   │   ├── DimProductionOrder.csv
│   │   ├── FactQualityEvent.csv
│   │   ├── FactShipment.csv
│   │   ├── EdgeAssemblyComponent.csv
│   │   └── EdgeShipmentComponent.csv
│   └── Eventhouse/                    # Timeseries data
│       ├── AssemblyTelemetry.csv
│       └── FacilityTelemetry.csv
└── Ontology/
    ├── auto-manufacturing.ttl         # RDF/Turtle ontology
    └── ontology-diagram-slide.html    # Interactive diagram
```

---

## Prerequisites

Before deploying this demo, ensure you have:

- [ ] Microsoft Fabric workspace with capacity
- [ ] Lakehouse created
- [ ] Eventhouse and KQL database created
- [ ] Graph capability enabled in workspace
- [ ] OneLake security **DISABLED** on Lakehouse

---

## Quick Start

### Option 1: Automated Setup

```bash
# Navigate to demo folder
cd AutoManufacturing-SupplyChain

# Validate the demo package
python -m demo_automation validate .

# Deploy to Fabric (requires Fabric CLI authentication)
python -m demo_automation setup .
```

### Option 2: Manual Setup

1. **Upload Ontology**
   - Navigate to your Graph in Fabric
   - Import `Ontology/auto-manufacturing.ttl`

2. **Create Lakehouse Tables**
   - Upload all CSV files from `Data/Lakehouse/` to Lakehouse Files
   - Create tables from each CSV file

3. **Bind Lakehouse Entities**
   - Follow `Bindings/lakehouse-binding.md`
   - Bind all 8 entities and 10 relationships

4. **Create Eventhouse Tables**
   - Create KQL database `AutoManufacturingDB`
   - Ingest CSVs from `Data/Eventhouse/`
   - Follow `Bindings/eventhouse-binding.md`

5. **Test Queries**
   - Open Graph Explorer
   - Run queries from `demo-questions.md`

---

## Demo Scenarios

### Scenario 1: Defect Investigation (5 min)

**Setup**: A critical quality event (EVT-007) was logged for a brake system failure.

**Demo Flow**:
1. Show the quality event in the graph
2. Traverse to affected assembly (ASM-027)
3. Identify components used in that assembly
4. Find the responsible suppliers
5. Check supplier ratings and certification status

**Key Query**: See Question 1 in demo-questions.md

---

### Scenario 2: Supply Chain Disruption (5 min)

**Setup**: Supplier SUP-001 (VoltPower) announces a 2-week production halt.

**Demo Flow**:
1. Identify all components from SUP-001
2. Find assemblies depending on those components
3. Identify vehicles in-progress that are affected
4. Show production order timeline impact
5. Discuss alternative supplier options

**Key Query**: See Question 2 in demo-questions.md

---

### Scenario 3: Vehicle Compliance Audit (5 min)

**Setup**: Regulatory audit requires complete genealogy for VEH-001.

**Demo Flow**:
1. Start with vehicle VEH-001
2. Show production order and facility
3. Traverse to all assemblies (5 types)
4. For each assembly, show components and suppliers
5. Display any quality events
6. Export full genealogy report

**Key Query**: See Question 5 in demo-questions.md

---

## Known Limitations

1. **Property Name Length**: All property names are ≤26 characters
2. **No Decimal Type**: Uses double instead (decimal returns NULL in Graph)
3. **OneLake Security**: Must be disabled for bindings to work
4. **Lakehouse Schemas**: Must be disabled
5. **Entity Keys**: String or int only (no datetime keys)

---

## Data Volumes

| Table | Rows | Description |
|-------|------|-------------|
| DimVehicle | 20 | Vehicles across 4 models |
| DimAssembly | 30 | 5 assemblies per vehicle (6 vehicles) |
| DimComponent | 25 | Parts from 10 suppliers |
| DimSupplier | 10 | Tier 1 and Tier 2 suppliers |
| DimFacility | 15 | Assembly plants + supplier facilities |
| DimProductionOrder | 20 | One order per vehicle |
| FactQualityEvent | 30 | Quality events linked to assemblies |
| FactShipment | 25 | Inbound logistics |
| EdgeAssemblyComponent | 80 | Assembly-to-component mappings |
| EdgeShipmentComponent | 57 | Shipment-to-component mappings |
| AssemblyTelemetry | 50 | Timeseries for 10 assemblies |
| FacilityTelemetry | 50 | Timeseries for 2 facilities |

---

## Support

- **Validation Issues**: Run `python -m demo_automation validate .` for diagnostics
- **Binding Errors**: Check Bindings/*.md troubleshooting sections
- **GQL Syntax**: Reference demo-questions.md for working examples

---

## License

This demo is provided as-is for demonstration purposes. Generated by Fabric Ontology Demo Agent v3.3.

---

*Generated: January 2026*
