# Lakehouse Binding Instructions (Water Treatment Plant)

Follow these steps in the Fabric Ontology (preview) UI to bind static data:

1. Open your ontology item and select the Plant entity type.
2. Bind static data:
   - Data source: OneLake → Lakehouse
   - Table: `DimPlant`
   - Binding type: Static
   - Property map:
     - PlantId → PlantId
     - PlantName → PlantName
     - Region → Region
   - Save; set Key: PlantId (string)

3. Bind Unit static data:
   - Entity: Unit
   - Data source: OneLake → Lakehouse
   - Table: `DimUnit`
   - Binding type: Static
   - Property map:
     - UnitId → UnitId
     - PlantId → PlantId
     - UnitType → UnitType
     - Status → Status
   - Save; set Key: UnitId (string)

4. Bind WaterQualitySample static data:
   - Entity: WaterQualitySample
   - Data source: OneLake → Lakehouse
   - Table: `FactWaterQuality`
   - Binding type: Static
   - Property map:
     - SampleId → SampleId
     - PlantId → PlantId
     - TurbidityNTU → TurbidityNTU
     - pH → pH
     - ConductivityuScm → ConductivityuScm
     - SampleTimestamp → SampleTimestamp
   - Save; set Key: SampleId (string)

## Relationship type bindings
- Plant operates Unit
  - Source table: `DimUnit`
  - Mapping:
    - Source entity (Plant) key source column: `PlantId`
    - Target entity (Unit) key source column: `UnitId`
- Unit hasReading SensorEvent
  - Bound with timeseries (see eventhouse instructions)
- Plant sampledAt WaterQualitySample
  - Source table: `FactWaterQuality`
  - Mapping:
    - Source entity (Plant) key source column: `PlantId`
    - Target entity (WaterQualitySample) key source column: `SampleId`

## Constraints & notes
- Static must be bound before timeseries.
- Keys must be string/int.
- Only managed tables are supported; disable OneLake security on lakehouse sources used for static bindings.
- Property names must be unique across the ontology.
- After binding, run a manual Graph refresh in the preview experience.
