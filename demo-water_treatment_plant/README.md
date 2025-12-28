# Water Treatment Plant Demo

A simple ontology-driven demo for a water treatment plant, aligned to Fabric Ontology (preview) best practices.

## Contents
- `ontology/water_treatment_plant.ttl` — TTL stub of entities and relationships.
- `ontology/ontology.mmd` — Mermaid ER diagram (Markdown fenced block).
- `ontology/ontology-structure.md` — Entity & relationship summary, binding notes.
- `data/data-dictionary.md` — CSV schema definitions for static & timeseries tables.
- `bindings/*.md` — Binding instructions for lakehouse/static and eventhouse/timeseries.
- `queries/demo-questions.md` — Five questions with traversal & GQL sketches.

## Setup (data)
Create the following CSVs and load into OneLake/Eventhouse as managed tables:
- `DimPlant.csv`, `DimUnit.csv`, `FactWaterQuality.csv` (≥50 rows each)
- `UnitTelemetry.csv` (≥50 rows, columnar timeseries with `Timestamp`)

## Bindings (summary)
- Static bindings first:
  - Plant ↔ DimPlant (Key: PlantId)
  - Unit ↔ DimUnit (Key: UnitId)
  - WaterQualitySample ↔ FactWaterQuality (Key: SampleId)
- Timeseries binding:
  - Unit ↔ UnitTelemetry (Key: UnitId; `Timestamp` column)
- Relationships:
  - Plant operates Unit (DimUnit via PlantId→UnitId)
  - Unit hasReading SensorEvent (UnitTelemetry via UnitId→SensorEventId)
  - Plant sampledAt WaterQualitySample (FactWaterQuality via PlantId→SampleId)

## Constraints & known limitations
- Keys must be string/int.
- Avoid Decimal; use Double.
- One static binding per entity; timeseries requires a timestamp.
- Only managed tables; lakehouse with OneLake security enabled is unsupported for static bindings.
- Manual graph refresh required after updates.
- Add data agent instruction: “Support group by in GQL” for aggregation.

## Try it
- Use the binding instructions to configure your ontology in Fabric.
- Open the preview experience; verify entity instances and relationship graph.
- Try the queries in `queries/demo-questions.md` using the graph/query builder.
