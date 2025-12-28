# Data Dictionary (Water Treatment Plant)

## Static tables (OneLake / Lakehouse)

### DimPlant.csv (≥50 rows)
- PlantId (string) — unique key
- PlantName (string)
- Region (string)

### DimUnit.csv (≥50 rows)
- UnitId (string) — unique key
- PlantId (string) — FK → DimPlant.PlantId
- UnitType (string)
- Status (string)

### FactWaterQuality.csv (≥50 rows)
- SampleId (string) — unique key
- PlantId (string) — FK → DimPlant.PlantId
- TurbidityNTU (double)
- pH (double)
- ConductivityuScm (double)
- SampleTimestamp (datetime)

## Timeseries table (Eventhouse or Lakehouse)

### UnitTelemetry.csv (≥50 rows, columnar timeseries)
- SensorEventId (string) — unique key (optional if using natural key)
- UnitId (string) — FK → DimUnit.UnitId
- Timestamp (datetime) — required
- FlowRateLps (double)
- PressureBar (double)

## Constraints
- Keys must be string/int
- No Decimal types; use Double
- Property names unique across ontology
- Managed tables only; OneLake security disabled for static bindings
- Timeseries requires timestamp and matching key column
