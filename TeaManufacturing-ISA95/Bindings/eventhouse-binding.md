# Eventhouse Binding Guide - Tea Bag Manufacturing (ISA-95 / OPC UA)

This guide walks through binding Eventhouse (KQL) tables for timeseries data to ontology entities. The timeseries data simulates OPC UA PLC tag values collected via OPC UA PubSub, including real-scale machine state and production counter data derived from actual tea factory operations.

**Demo timeline: July 2025 – July 2026** (12 months of continuous data)

---

## Overview

Four Eventhouse tables bind timeseries data to two ontology entities:

| Entity | KQL Table | Rows | Properties | OPC UA Tags |
|--------|-----------|------|------------|-------------|
| ProcessSegment | ProcessSegmentTelemetry | 525,600 | Temperature, MoistureContent, CycleTime | `ns=2;s=Segment.*` |
| Equipment | EquipmentTelemetry | 262,800 | EnergyConsumption, Humidity, ProductionRate | `ns=2;s=Equipment.*` |
| Equipment | MachineStateTelemetry | 6,442,346 | MachineState, ErrorCode, DurationSec | `ns=2;s=Equipment.State.*` |
| Equipment | ProductionCounterTelemetry | 13,261,954 | BagCount, BagCountDelta, TeaProducedGram, BagsRejected, OEE, VOT, LoadingTime | `ns=2;s=Equipment.Counter.*` |

**Total timeseries rows:** ~20.5M

---

## Prerequisites

1. ✅ Eventhouse created in Fabric workspace
2. ✅ KQL database created (TeaManufacturingDB)
3. ✅ Entity static bindings completed in Lakehouse first
4. ✅ CSV files ready for ingestion

---

## ProcessSegment Timeseries Binding

### Configuration Summary

| Setting | Value |
|---------|-------|
| Entity | ProcessSegment |
| KQL Table | ProcessSegmentTelemetry |
| Key Column | SegmentId |
| Timestamp Column | Timestamp |
| Source File | Data/Eventhouse/ProcessSegmentTelemetry.csv |

### Timeseries Property Mappings

| Ontology Property | KQL Column | Type | Unit | OPC UA NodeId |
|-------------------|------------|------|------|---------------|
| Temperature | Temperature | double | °C | `ns=2;s=Segment.Temperature` |
| MoistureContent | MoistureContent | double | % | `ns=2;s=Segment.MoistureContent` |
| CycleTime | CycleTime | double | seconds | `ns=2;s=Segment.CycleTime` |

### Step-by-Step Instructions

1. **Create KQL Table**
   ```kql
   .create table ProcessSegmentTelemetry (
       Timestamp: datetime,
       SegmentId: string,
       Temperature: real,
       MoistureContent: real,
       CycleTime: real
   )
   ```

2. **Ingest CSV Data**
   ```kql
   .ingest into table ProcessSegmentTelemetry (
       h'<blob-url-or-local-path>/ProcessSegmentTelemetry.csv'
   ) with (
       format = 'csv',
       ignoreFirstRecord = true
   )
   ```

   Or use the Fabric UI:
   - Navigate to KQL database
   - Select "Get data" → "Local file"
   - Upload ProcessSegmentTelemetry.csv
   - Map columns appropriately

3. **Bind to Ontology**
   - Go to Ontology → Data Binding
   - Select entity "ProcessSegment"
   - Add timeseries binding
   - Choose Eventhouse as source
   - Select database: TeaManufacturingDB
   - Select table: ProcessSegmentTelemetry
   - Map key: SegmentId → SegmentId
   - Map timestamp: Timestamp
   - Map properties:
     - Temperature → Temperature
     - MoistureContent → MoistureContent
     - CycleTime → CycleTime
   - Save binding

### Sample Data Ranges

| SegmentId | Segment_Type | Temperature (°C) | MoistureContent (%) | CycleTime (s) |
|-----------|-------------|-------------------|---------------------|----------------|
| SEG-001 | Blending (EB) | 80 – 90 | 4.0 – 6.0 | 100 – 140 |
| SEG-002 | Filling | 22 – 28 | 4.5 – 5.5 | 2.5 – 4.0 |
| SEG-003 | Sealing | 180 – 220 | 1.5 – 3.0 | 1.0 – 2.5 |
| SEG-013 | Blending (EG) ⚠️ | 70 – 80 (drops) | 6.0 – 8.0 (spikes) | 130 – 142 |
| SEG-025 | Blending (CH) ⚠️ | 80 – 90 | 7.0 – 9.0 (spikes) | 100 – 130 |

> ⚠️ SEG-013 and SEG-025 have injected anomalies (temperature drops, moisture spikes) correlating with quality test failures (TST-010 and TST-020).

> **Data volume:** 525,600 rows — one reading every 30 minutes for all 30 segments across 12 months.

---

## Equipment Timeseries Binding

### Configuration Summary

| Setting | Value |
|---------|-------|
| Entity | Equipment |
| KQL Table | EquipmentTelemetry |
| Key Column | EquipmentId |
| Timestamp Column | Timestamp |
| Source File | Data/Eventhouse/EquipmentTelemetry.csv |

### Timeseries Property Mappings

| Ontology Property | KQL Column | Type | Unit | OPC UA NodeId |
|-------------------|------------|------|------|---------------|
| EnergyConsumption | EnergyConsumption | double | kWh | `ns=2;s=Equipment.EnergyConsumption` |
| Humidity | Humidity | double | % | `ns=2;s=Equipment.Humidity` |
| ProductionRate | ProductionRate | double | bags/hr | `ns=2;s=Equipment.ProductionRate` |

### Step-by-Step Instructions

1. **Create KQL Table**
   ```kql
   .create table EquipmentTelemetry (
       Timestamp: datetime,
       EquipmentId: string,
       EnergyConsumption: real,
       Humidity: real,
       ProductionRate: real
   )
   ```

2. **Ingest CSV Data**
   ```kql
   .ingest into table EquipmentTelemetry (
       h'<blob-url-or-local-path>/EquipmentTelemetry.csv'
   ) with (
       format = 'csv',
       ignoreFirstRecord = true
   )
   ```

3. **Bind to Ontology**
   - Go to Ontology → Data Binding
   - Select entity "Equipment"
   - Add timeseries binding
   - Choose Eventhouse as source
   - Select database: TeaManufacturingDB
   - Select table: EquipmentTelemetry
   - Map key: EquipmentId → EquipmentId
   - Map timestamp: Timestamp
   - Map properties:
     - EnergyConsumption → EnergyConsumption
     - Humidity → Humidity
     - ProductionRate → ProductionRate
   - Save binding

### Sample Data Ranges

| EquipmentId | Equipment_Name | EnergyConsumption (kWh) | Humidity (%) | ProductionRate |
|-------------|----------------|------------------------|--------------|----------------|
| EQP-001 | London Blendery | 500 – 3,500 | 38 – 44 | 0 – 145 kg/hr |
| EQP-002 | Manchester Packing | 800 – 5,500 | 38 – 44 | 0 – 160 bags/hr |
| EQP-005 | Packing Line 1 | 600 – 4,000 | 37 – 43 | 0 – 150 bags/hr |

> **Data volume:** 262,800 rows — one reading every 30 minutes for 15 equipment items across 12 months.
> Includes production patterns: weekday vs weekend, day vs night, seasonal energy variation.

---

## Machine State Telemetry Binding (NEW — real-scale)

### Configuration Summary

| Setting | Value |
|---------|-------|
| Entity | Equipment (WorkUnit level) |
| KQL Table | MachineStateTelemetry |
| Key Column | EquipmentId |
| Timestamp Column | Timestamp |
| Source File | Data/Eventhouse/MachineStateTelemetry.csv |
| Row Count | 6,442,346 |

### Timeseries Property Mappings

| Ontology Property | KQL Column | Type | Description | OPC UA NodeId |
|-------------------|------------|------|-------------|---------------|
| MachineState | MachineState | string | Running, Stopped, Blocked, Waiting, Idle | `ns=2;s=Equipment.State.MachineState` |
| ErrorCode | ErrorCode | string | PLC alarm/error code | `ns=2;s=Equipment.State.ErrorCode` |
| DurationSec | DurationSec | real | Duration of state in seconds | `ns=2;s=Equipment.State.DurationSec` |

### Additional Columns

| Column | Type | Description |
|--------|------|-------------|
| LineName | string | Packing line (e.g. PackLine-Alpha, PackLine-Hotel) |
| Shift | string | Day or Night |
| BatchId | string | FK to ProductBatch |

### Step-by-Step Instructions

1. **Create KQL Table**
   ```kql
   .create table MachineStateTelemetry (
       Timestamp: datetime,
       EquipmentId: string,
       LineName: string,
       Shift: string,
       MachineState: string,
       ErrorCode: string,
       DurationSec: real,
       BatchId: string
   )
   ```

2. **Ingest CSV Data**
   ```kql
   .ingest into table MachineStateTelemetry (
       h'<blob-url-or-local-path>/MachineStateTelemetry.csv'
   ) with (
       format = 'csv',
       ignoreFirstRecord = true
   )
   ```
   > ⚠️ Large file (449 MB, 6.4M rows). Consider splitting or using Fabric pipeline for ingestion.

3. **Bind to Ontology**
   - Select entity "Equipment"
   - Add timeseries binding → MachineStateTelemetry
   - Map key: EquipmentId → EquipmentId
   - Map timestamp: Timestamp
   - Map properties: MachineState, ErrorCode, DurationSec

### Sample Data

| Timestamp | EquipmentId | LineName | MachineState | ErrorCode | DurationSec |
|-----------|-------------|----------|--------------|-----------|-------------|
| 2025-07-01T01:46:47 | EQP-016 | PackLine-Bravo | Running | 0 | 667 |
| 2025-09-15T14:22:10 | EQP-034 | PackLine-Charlie | Stopped | 102 | 245 |
| 2026-01-08T08:05:33 | EQP-051 | PackLine-Hotel | Blocked | 0 | 1200 |

### Machine Types Covered (11 production lines, 134 machines)

| Machine Type | Count | ISA-95 Role |
|-------------|-------|-------------|
| TeaBagFormer | 50+ | Tea bag forming & filling |
| Cartoner | 8 | Carton folding & insertion |
| CasePacker | 11 | Case packing |
| Overwrapper | 4 | Film overwrapping |
| BulkPacker | 2 | Bulk packaging |
| EnvelopeMachine | 2 | Envelope wrapping |
| BoxFormer | 2 | Box forming |
| SealingUnit | 6 | Sealing |
| ConveyorBelt | 5 | Material transport |
| MetalDetector | 4 | Quality control inline |
| PackingRobot | 1 | Automated packing |
| CartoonPacker | 2 | Cartoon packing |
| LabelApplicator | 1 | Label application |
| FilmWrapper | 2 | Film wrapping |
| TrayFormer | 2 | Tray forming |
| Others | 5+ | PouchSealer, FoilWrapper, StackerUnit |

---

## Production Counter / OEE Telemetry Binding (NEW — real-scale)

### Configuration Summary

| Setting | Value |
|---------|-------|
| Entity | Equipment (WorkUnit level) |
| KQL Table | ProductionCounterTelemetry |
| Key Column | EquipmentId |
| Timestamp Column | Timestamp |
| Source File | Data/Eventhouse/ProductionCounterTelemetry.csv |
| Row Count | 13,261,954 |

### Timeseries Property Mappings

| Ontology Property | KQL Column | Type | Unit | OPC UA NodeId |
|-------------------|------------|------|------|---------------|
| BagCount | BagCount | int | count | `ns=2;s=Equipment.Counter.BagCount` |
| BagCountDelta | BagCountDelta | int | count | `ns=2;s=Equipment.Counter.BagCountDelta` |
| TeaProducedGram | TeaProducedGram | real | grams | `ns=2;s=Equipment.Counter.TeaProducedGram` |
| BagsRejected | BagsRejected | int | count | `ns=2;s=Equipment.Counter.BagsRejected` |
| OEE | OEE | real | % | `ns=2;s=Equipment.Counter.OEE` |
| VOT | VOT | real | seconds | `ns=2;s=Equipment.Counter.VOT` |
| LoadingTime | LoadingTime | real | seconds | `ns=2;s=Equipment.Counter.LoadingTime` |

### Additional Columns

| Column | Type | Description |
|--------|------|-------------|
| LineName | string | Packing line name |
| SKU | string | Product being manufactured (Golden Leaf product name) |
| Shift | string | Day or Night |
| TeaRejectedGram | real | Tea wasted in grams |
| BatchId | string | FK to ProductBatch |

### Step-by-Step Instructions

1. **Create KQL Table**
   ```kql
   .create table ProductionCounterTelemetry (
       Timestamp: datetime,
       EquipmentId: string,
       LineName: string,
       SKU: string,
       Shift: string,
       BagCount: long,
       BagCountDelta: long,
       TeaProducedGram: real,
       BagsRejected: long,
       TeaRejectedGram: real,
       VOT: real,
       LoadingTime: real,
       OEE: real,
       BatchId: string
   )
   ```

2. **Ingest CSV Data**
   ```kql
   .ingest into table ProductionCounterTelemetry (
       h'<blob-url-or-local-path>/ProductionCounterTelemetry.csv'
   ) with (
       format = 'csv',
       ignoreFirstRecord = true
   )
   ```
   > ⚠️ Large file (1.3 GB, 13.3M rows). Use Fabric pipeline or split into chunks for ingestion.

3. **Bind to Ontology**
   - Select entity "Equipment"
   - Add timeseries binding → ProductionCounterTelemetry
   - Map key: EquipmentId → EquipmentId
   - Map timestamp: Timestamp
   - Map properties: BagCount, BagCountDelta, TeaProducedGram, BagsRejected, OEE, VOT, LoadingTime

---

## OPC UA Integration Notes

In a production deployment, the telemetry data would flow from OPC UA-enabled PLCs via:

```
PLC/SCADA → OPC UA Server → OPC UA PubSub → Azure IoT Hub → Eventhouse (KQL)
```

The OPC UA NodeIds referenced in the ontology TTL comments (e.g., `ns=2;s=Segment.Temperature`) would map directly to the KQL column names via an ingestion mapping.

### Example OPC UA PubSub Configuration

```json
{
  "DataSetWriterName": "BlenderUnit1",
  "PublishedDataItems": [
    { "NodeId": "ns=2;s=Segment.Temperature", "FieldName": "Temperature" },
    { "NodeId": "ns=2;s=Segment.MoistureContent", "FieldName": "MoistureContent" },
    { "NodeId": "ns=2;s=Segment.CycleTime", "FieldName": "CycleTime" }
  ]
}
```

---

## Verification Queries

After ingestion, verify data with these KQL queries:

### Process Segment Telemetry
```kql
ProcessSegmentTelemetry
| summarize count(), min(Timestamp), max(Timestamp), dcount(SegmentId) by SegmentId
| order by SegmentId asc
```

### Equipment Telemetry
```kql
EquipmentTelemetry
| summarize count(), min(Timestamp), max(Timestamp),
    avg(EnergyConsumption), avg(Humidity), avg(ProductionRate)
  by EquipmentId
| order by EquipmentId asc
```

### Machine State Telemetry — State Distribution
```kql
MachineStateTelemetry
| summarize count() by MachineState
| order by count_ desc
```

### Machine State Telemetry — Per Line Summary
```kql
MachineStateTelemetry
| summarize 
    Events = count(),
    Machines = dcount(EquipmentId),
    AvgDuration = avg(DurationSec),
    MinTime = min(Timestamp),
    MaxTime = max(Timestamp)
  by LineName
| order by Events desc
```

### Production Counter — Daily OEE by Line
```kql
ProductionCounterTelemetry
| where OEE > 0
| summarize AvgOEE = avg(OEE), TotalBags = sum(BagCountDelta) by LineName, bin(Timestamp, 1d)
| order by Timestamp asc, LineName asc
| take 50
```

### Production Counter — Top Producing Machines
```kql
ProductionCounterTelemetry
| summarize 
    TotalBags = sum(BagCountDelta),
    TotalRejected = sum(BagsRejected),
    AvgOEE = avg(OEE)
  by EquipmentId
| where TotalBags > 0
| top 20 by TotalBags desc
```

### Anomaly Detection (Quality Correlation)
```kql
ProcessSegmentTelemetry
| where SegmentId in ("SEG-013", "SEG-025")
| project Timestamp, SegmentId, Temperature, MoistureContent
| order by SegmentId, Timestamp asc
```

### Cross-Table: Machine Downtime vs Production Loss
```kql
let downtime = MachineStateTelemetry
| where MachineState == "Stopped" and DurationSec > 600
| summarize StoppedEvents = count(), TotalDowntimeSec = sum(DurationSec) by LineName, bin(Timestamp, 1d);
let production = ProductionCounterTelemetry
| where BagCountDelta > 0
| summarize DailyBags = sum(BagCountDelta) by LineName, bin(Timestamp, 1d);
downtime
| join kind=inner production on LineName, Timestamp
| project LineName, Timestamp, StoppedEvents, TotalDowntimeSec, DailyBags
| order by Timestamp desc
| take 30
```
