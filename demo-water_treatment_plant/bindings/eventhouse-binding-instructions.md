# Eventhouse / Timeseries Binding Instructions (Water Treatment Plant)

Bind telemetry (timeseries) to the Unit entity type after static bindings are complete.

1. Open your ontology item and select the Unit entity type.
2. Add data to entity type:
   - Data source: Eventhouse (or Lakehouse if using timeseries tables there)
   - Table: `UnitTelemetry`
   - Binding type: Timeseries
   - Source data timestamp column: `Timestamp`
3. Under Bind your properties:
   - Static section:
     - Add static property mapping for the key: `UnitId` → UnitId (string)
   - Timeseries section:
     - FlowRateLps → FlowRateLps (double)
     - PressureBar → PressureBar (double)
4. Save the timeseries binding.

## Constraints & notes
- Static data must be complete prior to timeseries binding.
- The timeseries table must include a timestamp column and a key column (`UnitId`) that matches the static binding key.
- Avoid Decimal types; prefer Double.
- Eventhouse materialized views are not supported as binding sources.
- Managed tables only; ensure data access.
- If the preview looks sparse, verify keys and property maps.
