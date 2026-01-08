# Eventhouse Binding Guide - Automotive Manufacturing & Supply Chain

This guide walks through binding Eventhouse (KQL) tables for timeseries data to ontology entities.

---

## Overview

Two entities have timeseries properties bound to Eventhouse:

| Entity | Timeseries Properties | Table |
|--------|----------------------|-------|
| Assembly | Temperature, Torque, CycleTime | AssemblyTelemetry |
| Facility | EnergyConsumption, Humidity, ProductionRate | FacilityTelemetry |

---

## Prerequisites

1. ✅ Eventhouse created in Fabric workspace
2. ✅ KQL database created (AutoManufacturingDB)
3. ✅ Entity static bindings completed in Lakehouse first
4. ✅ CSV files ready for ingestion

---

## Assembly Timeseries Binding

### Configuration Summary

| Setting | Value |
|---------|-------|
| Entity | Assembly |
| KQL Table | AssemblyTelemetry |
| Key Column | AssemblyId |
| Timestamp Column | Timestamp |
| Source File | Data/Eventhouse/AssemblyTelemetry.csv |

### Timeseries Property Mappings

| Ontology Property | KQL Column | Type | Unit |
|-------------------|------------|------|------|
| Temperature | Temperature | double | °C |
| Torque | Torque | double | Nm |
| CycleTime | CycleTime | double | seconds |

### Step-by-Step Instructions

1. **Create KQL Table**
   ```kql
   .create table AssemblyTelemetry (
       Timestamp: datetime,
       AssemblyId: string,
       Temperature: real,
       Torque: real,
       CycleTime: real
   )
   ```

2. **Ingest CSV Data**
   ```kql
   .ingest into table AssemblyTelemetry (
       h'<blob-url-or-local-path>/AssemblyTelemetry.csv'
   ) with (
       format = 'csv',
       ignoreFirstRecord = true
   )
   ```
   
   Or use the Fabric UI:
   - Navigate to KQL database
   - Select "Get data" → "Local file"
   - Upload AssemblyTelemetry.csv
   - Map columns appropriately

3. **Bind to Ontology**
   - Go to Ontology → Data Binding
   - Select entity "Assembly"
   - Add timeseries binding
   - Choose Eventhouse as source
   - Select database: AutoManufacturingDB
   - Select table: AssemblyTelemetry
   - Map key: AssemblyId → AssemblyId
   - Map timestamp: Timestamp
   - Map properties:
     - Temperature → Temperature
     - Torque → Torque
     - CycleTime → CycleTime
   - Save binding

---

## Facility Timeseries Binding

### Configuration Summary

| Setting | Value |
|---------|-------|
| Entity | Facility |
| KQL Table | FacilityTelemetry |
| Key Column | FacilityId |
| Timestamp Column | Timestamp |
| Source File | Data/Eventhouse/FacilityTelemetry.csv |

### Timeseries Property Mappings

| Ontology Property | KQL Column | Type | Unit |
|-------------------|------------|------|------|
| EnergyConsumption | EnergyConsumption | double | kWh |
| Humidity | Humidity | double | % |
| ProductionRate | ProductionRate | double | units/hour |

### Step-by-Step Instructions

1. **Create KQL Table**
   ```kql
   .create table FacilityTelemetry (
       Timestamp: datetime,
       FacilityId: string,
       EnergyConsumption: real,
       Humidity: real,
       ProductionRate: real
   )
   ```

2. **Ingest CSV Data**
   ```kql
   .ingest into table FacilityTelemetry (
       h'<blob-url-or-local-path>/FacilityTelemetry.csv'
   ) with (
       format = 'csv',
       ignoreFirstRecord = true
   )
   ```

3. **Bind to Ontology**
   - Go to Ontology → Data Binding
   - Select entity "Facility"
   - Add timeseries binding
   - Choose Eventhouse as source
   - Select database: AutoManufacturingDB
   - Select table: FacilityTelemetry
   - Map key: FacilityId → FacilityId
   - Map timestamp: Timestamp
   - Map properties:
     - EnergyConsumption → EnergyConsumption
     - Humidity → Humidity
     - ProductionRate → ProductionRate
   - Save binding

---

## Verification Queries

After binding, verify data with these KQL queries:

### Check Assembly Telemetry
```kql
AssemblyTelemetry
| summarize count() by AssemblyId
| order by AssemblyId
```

### Check Facility Telemetry
```kql
FacilityTelemetry
| summarize count() by FacilityId
| order by FacilityId
```

### Check Time Range
```kql
AssemblyTelemetry
| summarize MinTime = min(Timestamp), MaxTime = max(Timestamp)

FacilityTelemetry
| summarize MinTime = min(Timestamp), MaxTime = max(Timestamp)
```

---

## Sample Timeseries Queries

Once bound, you can query timeseries through the Graph:

### Assembly Temperature Over Time
```gql
MATCH (a:Assembly {AssemblyId: 'ASM-001'})
RETURN a.AssemblyId, a.Temperature, a.Timestamp
ORDER BY a.Timestamp
```

### Facility Production Rate Trend
```gql
MATCH (f:Facility {FacilityId: 'FAC-001'})
RETURN f.Facility_Name, f.ProductionRate, f.Timestamp
ORDER BY f.Timestamp DESC
LIMIT 10
```

---

## Troubleshooting

### Common Issues

1. **"Timeseries data not appearing"**
   - Verify KQL table has data: `TableName | count`
   - Check key column values match entity keys exactly
   - Ensure timestamp column is datetime type

2. **"Key mismatch"**
   - AssemblyId/FacilityId in Eventhouse must match Lakehouse exactly
   - Check for case sensitivity issues

3. **"Timestamp parsing errors"**
   - Ensure ISO 8601 format: `YYYY-MM-DDTHH:MM:SS`
   - Verify timezone consistency

4. **"Real vs Double type"**
   - KQL uses 'real' for floating point (equivalent to double)
   - Both work interchangeably

---

## Data Freshness

For real-time scenarios, consider:
- Streaming ingestion from IoT Hub
- Event Grid triggers for near-real-time updates
- Batch ingestion for historical backfill

---

## Next Steps

After completing Eventhouse bindings:
1. Test GQL queries in Graph Explorer
2. Review demo-questions.md for sample queries
3. Run full validation: `python -m demo_automation validate ./AutoManufacturing-SupplyChain`
