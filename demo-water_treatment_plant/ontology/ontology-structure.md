# Water Treatment Plant Ontology Structure

## Entity Types
- Plant
  - Key: PlantId (string)
  - Properties: PlantName (string), Region (string)
- Unit
  - Key: UnitId (string)
  - Properties: UnitType (string), Status (string), PlantId (string)
- SensorEvent
  - Key: SensorEventId (string)
  - Properties: FlowRateLps (double), PressureBar (double), Timestamp (datetime), UnitId (string)
- WaterQualitySample
  - Key: SampleId (string)
  - Properties: TurbidityNTU (double), pH (double), ConductivityuScm (double), SampleTimestamp (datetime), PlantId (string)

## Relationships
- Plant operates Unit (one-to-many)
  - Source table: DimUnit
  - Mapping: sourceKeyColumn=PlantId, targetKeyColumn=UnitId
- Unit hasReading SensorEvent (one-to-many)
  - Source table: UnitTelemetry
  - Mapping: sourceKeyColumn=UnitId, targetKeyColumn=SensorEventId
- Plant sampledAt WaterQualitySample (one-to-many)
  - Source table: FactWaterQuality
  - Mapping: sourceKeyColumn=PlantId, targetKeyColumn=SampleId

## Binding Notes
- Static first (OneLake), then Time-series (Eventhouse or OneLake) for telemetry
- Keys must be string/int; avoid Decimal types (use Double)
- Only managed tables; OneLake security must be disabled for static bindings
- Timeseries requires a timestamp column; key must match static source key
