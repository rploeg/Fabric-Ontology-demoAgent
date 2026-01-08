# FreshMart Supermarket - Eventhouse Binding Instructions

> **Version**: 1.0  
> **Last Updated**: January 2026  
> **Purpose**: Step-by-step instructions for binding timeseries data from Eventhouse to the FreshMart ontology

---

## Prerequisites

Before starting Eventhouse bindings:

1. ✅ **Complete all Lakehouse bindings** (see `lakehouse-binding.md`)
2. ✅ **Create an Eventhouse** named `FreshMartEventhouse`
3. ✅ **Create a KQL Database** within the Eventhouse
4. ✅ **Ingest timeseries CSV files** from `Data\Eventhouse\` folder

---

## Timeseries Configuration Summary

| Entity | Eventhouse Table | Key Column | Timestamp Column | Metrics |
|--------|------------------|------------|------------------|---------|
| Store | StoreTelemetry | StoreId | Timestamp | FootTraffic, SalesVelocity, AvgTransactionValue |
| ProductBatch | BatchTelemetry | BatchId | Timestamp | StorageTemperature, Humidity, DaysToExpiry |

---

## Part 1: Store Timeseries Binding

### 1.1 Configuration Summary

| Setting | Value |
|---------|-------|
| Entity | Store |
| Eventhouse Table | StoreTelemetry |
| Key Column | StoreId |
| Timestamp Column | Timestamp |

### 1.2 Timeseries Property Mappings

| Ontology Property | Table Column | Data Type | Description |
|-------------------|--------------|-----------|-------------|
| FootTraffic | FootTraffic | int | Hourly customer count |
| SalesVelocity | SalesVelocity | double | Units sold per hour |
| AvgTransactionValue | AvgTransactionValue | double | Average basket value ($) |

### 1.3 Step-by-Step Binding Instructions

1. **Navigate to Store Entity**
   - Open your Ontology in Fabric
   - Select the **Store** entity
   - Click **Bind Timeseries Data**

2. **Select Eventhouse Source**
   - Source Type: **Eventhouse**
   - Select: `FreshMartEventhouse`
   - Database: Select your KQL database
   - Table: **StoreTelemetry**

3. **Configure Key Mapping**
   - Entity Key: `StoreId`
   - Table Key Column: `StoreId`
   - Timestamp Column: `Timestamp`

4. **Map Timeseries Properties**

   | Property | Column | Type |
   |----------|--------|------|
   | FootTraffic | FootTraffic | int |
   | SalesVelocity | SalesVelocity | double |
   | AvgTransactionValue | AvgTransactionValue | double |

5. **Save** the binding

### 1.4 KQL Ingestion Command

Run this in your KQL database to create the table and ingest data:

```kql
// Create the StoreTelemetry table
.create table StoreTelemetry (
    Timestamp: datetime,
    StoreId: string,
    FootTraffic: int,
    SalesVelocity: real,
    AvgTransactionValue: real
)

// Ingest from CSV (adjust path as needed)
.ingest into table StoreTelemetry (
    h'https://your-storage-account.blob.core.windows.net/data/StoreTelemetry.csv'
) with (
    format = 'csv',
    ignoreFirstRecord = true
)
```

**Alternative: Direct paste ingestion**

```kql
.set-or-append StoreTelemetry <|
datatable(Timestamp:datetime, StoreId:string, FootTraffic:int, SalesVelocity:real, AvgTransactionValue:real)
[
    datetime(2025-12-07T08:00:00), "STR001", 45, 12.5, 42.30,
    datetime(2025-12-07T09:00:00), "STR001", 120, 35.2, 48.75,
    // ... add remaining rows
]
```

---

## Part 2: ProductBatch Timeseries Binding

### 2.1 Configuration Summary

| Setting | Value |
|---------|-------|
| Entity | ProductBatch |
| Eventhouse Table | BatchTelemetry |
| Key Column | BatchId |
| Timestamp Column | Timestamp |

### 2.2 Timeseries Property Mappings

| Ontology Property | Table Column | Data Type | Description |
|-------------------|--------------|-----------|-------------|
| StorageTemperature | StorageTemperature | double | Temperature in Celsius |
| Humidity | Humidity | double | Relative humidity % |
| DaysToExpiry | DaysToExpiry | int | Days remaining until expiry |

### 2.3 Step-by-Step Binding Instructions

1. **Navigate to ProductBatch Entity**
   - Open your Ontology in Fabric
   - Select the **ProductBatch** entity
   - Click **Bind Timeseries Data**

2. **Select Eventhouse Source**
   - Source Type: **Eventhouse**
   - Select: `FreshMartEventhouse`
   - Database: Select your KQL database
   - Table: **BatchTelemetry**

3. **Configure Key Mapping**
   - Entity Key: `BatchId`
   - Table Key Column: `BatchId`
   - Timestamp Column: `Timestamp`

4. **Map Timeseries Properties**

   | Property | Column | Type |
   |----------|--------|------|
   | StorageTemperature | StorageTemperature | double |
   | Humidity | Humidity | double |
   | DaysToExpiry | DaysToExpiry | int |

5. **Save** the binding

### 2.4 KQL Ingestion Command

Run this in your KQL database to create the table and ingest data:

```kql
// Create the BatchTelemetry table
.create table BatchTelemetry (
    Timestamp: datetime,
    BatchId: string,
    StorageTemperature: real,
    Humidity: real,
    DaysToExpiry: int
)

// Ingest from CSV (adjust path as needed)
.ingest into table BatchTelemetry (
    h'https://your-storage-account.blob.core.windows.net/data/BatchTelemetry.csv'
) with (
    format = 'csv',
    ignoreFirstRecord = true
)
```

---

## Validation Queries

### Test Store Timeseries

Run this GQL query to verify Store timeseries binding:

```gql
MATCH (s:Store)
WHERE s.StoreId = 'STR001'
RETURN s.StoreName, s.FootTraffic, s.SalesVelocity, s.AvgTransactionValue
```

**Expected Result**: Should return the most recent timeseries values for STR001.

### Test ProductBatch Timeseries

Run this GQL query to verify ProductBatch timeseries binding:

```gql
MATCH (b:ProductBatch)
WHERE b.BatchId = 'BAT017'
RETURN b.LotNumber, b.StorageTemperature, b.Humidity, b.DaysToExpiry
```

**Expected Result**: Should show elevated temperature readings for BAT017 (the spoiled shrimp batch).

### Correlate Timeseries with Quality Issues

```gql
MATCH (qi:QualityInspection)-[:INSPECTED]->(b:ProductBatch)
WHERE qi.Result = 'Fail'
RETURN qi.InspectionId, qi.Notes, b.BatchId, b.StorageTemperature, b.Humidity
```

**Expected Result**: Failed inspections should correlate with abnormal temperature/humidity readings.

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Timeseries data not appearing | Verify Eventhouse table has data: `StoreTelemetry | count` |
| Key mismatch errors | Ensure BatchId/StoreId values match exactly between Lakehouse and Eventhouse |
| Timestamp format errors | Use ISO 8601: `2025-12-07T08:00:00` |
| NULL values in timeseries | Check for missing rows in CSV, verify column types |

### KQL Diagnostic Queries

```kql
// Check StoreTelemetry data
StoreTelemetry
| summarize count() by StoreId
| order by count_ desc

// Check BatchTelemetry data
BatchTelemetry
| summarize count() by BatchId
| order by count_ desc

// Find temperature anomalies
BatchTelemetry
| where StorageTemperature > 5.0
| project Timestamp, BatchId, StorageTemperature
| order by StorageTemperature desc
```

---

## Demo Scenarios Using Timeseries

### Scenario 1: High-Traffic Store Analysis

Query stores with highest foot traffic to analyze sales correlation:

```gql
MATCH (s:Store)
RETURN s.StoreName, s.City, s.FootTraffic, s.SalesVelocity
ORDER BY s.FootTraffic DESC
LIMIT 5
```

### Scenario 2: Cold Chain Monitoring

Identify batches with temperature excursions:

```gql
MATCH (b:ProductBatch)-[:CONTAINS]->(p:Product)
WHERE b.StorageTemperature > 5.0
RETURN b.BatchId, p.ProductName, b.StorageTemperature, b.Humidity
```

### Scenario 3: Expiry Risk Analysis

Find batches nearing expiry with elevated storage conditions:

```gql
MATCH (b:ProductBatch)-[:RECEIVED_AT]->(s:Store)
WHERE b.DaysToExpiry <= 3 AND b.StorageTemperature > 4.0
RETURN s.StoreName, b.BatchId, b.DaysToExpiry, b.StorageTemperature
```

---

## Next Steps

After completing Eventhouse bindings:

1. ✅ All entity bindings complete (Lakehouse)
2. ✅ All timeseries bindings complete (Eventhouse)
3. ➡️ Run validation queries above
4. ➡️ Proceed to `demo-questions.md` for full demo scenarios
