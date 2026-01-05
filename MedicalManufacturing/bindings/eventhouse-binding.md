# Eventhouse Binding Instructions

This guide explains how to bind timeseries data from Eventhouse (KQL Database) to the BD Medical Manufacturing ontology.

## Prerequisites

- [ ] Static bindings completed first (see `lakehouse-binding.md`)
- [ ] Eventhouse/KQL Database created in the same workspace
- [ ] Timeseries CSV files ingested into Eventhouse tables
- [ ] Tables include `timestamp` column

> ⚠️ **CRITICAL:** Static binding MUST exist before adding timeseries binding.

---

## Step 1: Create Eventhouse

1. In workspace, click **+ New item** → **Eventhouse**
2. Name: `BD-Manufacturing-Telemetry`
3. Click **Create**
4. A KQL Database is automatically created

---

## Step 2: Ingest Timeseries Data

### 2.1 BatchTelemetry Table

1. In Eventhouse, click **Get data** → **Local file**
2. Select `BatchTelemetry.csv`
3. Configure table:
   - Table name: `BatchTelemetry`
   - First row is header: **Yes**

4. Verify schema mapping:

| Column | Type |
|--------|------|
| BatchId | string |
| timestamp | datetime |
| YieldRate | real |
| DefectCount | int |
| CycleTimeMin | real |

5. Click **Finish**

---

### 2.2 FacilityTelemetry Table

1. Click **Get data** → **Local file**
2. Select `FacilityTelemetry.csv`
3. Configure table:
   - Table name: `FacilityTelemetry`
   - First row is header: **Yes**

4. Verify schema mapping:

| Column | Type |
|--------|------|
| FacilityId | string |
| timestamp | datetime |
| DailyOutput | int |
| EquipmentUptime | real |

5. Click **Finish**

---

## Step 3: Verify Data Ingestion

Run these KQL queries to verify data:

```kql
// Check BatchTelemetry
BatchTelemetry
| take 10

// Check record count
BatchTelemetry
| count

// Verify timestamp range
BatchTelemetry
| summarize min(timestamp), max(timestamp)
```

```kql
// Check FacilityTelemetry
FacilityTelemetry
| take 10

// Check record count
FacilityTelemetry
| count
```

---

## Step 4: Bind Timeseries to ProductionBatch Entity

1. Open the ontology: `BD-Medical-Manufacturing-Ontology`
2. Navigate to **ProductionBatch** entity type
3. Click **Add binding** → **Timeseries binding**

### Binding Configuration:

| Setting | Value |
|---------|-------|
| Source Type | Eventhouse |
| Database | BD-Manufacturing-Telemetry |
| Table | BatchTelemetry |
| Entity Key Column | BatchId |
| Timestamp Column | timestamp |

### Property Mappings:

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| YieldRate | YieldRate | double |
| DefectCount | DefectCount | int |
| CycleTimeMin | CycleTimeMin | double |

4. Click **Save**

---

## Step 5: Bind Timeseries to Facility Entity

1. Navigate to **Facility** entity type
2. Click **Add binding** → **Timeseries binding**

### Binding Configuration:

| Setting | Value |
|---------|-------|
| Source Type | Eventhouse |
| Database | BD-Manufacturing-Telemetry |
| Table | FacilityTelemetry |
| Entity Key Column | FacilityId |
| Timestamp Column | timestamp |

### Property Mappings:

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| DailyOutput | DailyOutput | int |
| EquipmentUptime | EquipmentUptime | double |

4. Click **Save**

---

## Step 6: Refresh Graph

1. Return to ontology overview
2. Click **Refresh Graph**
3. Wait for refresh to complete

---

## Step 7: Verify Timeseries in Preview

1. Click **Preview**
2. Select an entity instance (e.g., `BATCH021`)
3. Verify timeseries tile appears showing:
   - YieldRate trend over time
   - DefectCount trend over time

### Sample Verification Queries:

Navigate to a ProductionBatch and check:
- **BATCH021**: Should show declining YieldRate (98% → 82%)
- **BATCH027**: Should show declining YieldRate (91% → 85%)

Navigate to a Facility and check:
- **FAC005**: Should show declining EquipmentUptime correlating with quality issues

---

## Timeseries Demo Scenarios

### Scenario 1: Batch Quality Degradation
1. View **BATCH021** timeseries
2. Observe YieldRate dropping from 88.5% to 82.5%
3. DefectCount increasing from 115 to 168
4. Navigate to linked QualityEvent (QE008, QE009)

### Scenario 2: Facility Performance Correlation
1. View **FAC005** timeseries
2. Observe EquipmentUptime dropping from 94% to 82%
3. Navigate to batches produced → quality events
4. Demonstrate multi-hop root cause analysis

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Timeseries binding option not available | Complete static binding first |
| Timestamp not recognized | Ensure column is datetime type in Eventhouse |
| No data in timeseries tile | Verify BatchId/FacilityId values match static data |
| Materialized view error | Use base tables only (not materialized views) |
| Null timeseries values | Check for data type mismatch (use real/double, not decimal) |

---

## Data Type Reference

| Ontology Type | Eventhouse Type | Notes |
|---------------|-----------------|-------|
| double | real | Use for decimals (not decimal type) |
| int | int | Integer values |
| datetime | datetime | ISO 8601 format |
| string | string | Text values |

> ⚠️ **Important:** Do not use `decimal` type in Eventhouse - it returns null in Graph visualization.

---

## Next Steps

After completing timeseries bindings:
1. Test multi-hop queries in Graph view
2. Create Data Agent for natural language queries
3. Run demo questions from `queries/demo-questions.md`
