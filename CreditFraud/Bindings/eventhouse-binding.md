# Credit Fraud Detection - Eventhouse Binding Instructions

> **Version**: 1.0  
> **Last Updated**: January 2026  
> **Ontology**: CreditFraud  
> **Company**: FinanceGuard Bank

---

## Overview

This guide covers binding **timeseries properties** to Eventhouse (KQL Database) for real-time fraud detection metrics.

### Entities with Timeseries Properties

| Entity | Timeseries Properties | Eventhouse Table |
|--------|----------------------|------------------|
| CreditCard | TxnVelocity, DailySpend, DeclineRate | CardTelemetry |
| Device | LoginAttempts, FailedLogins, SessionDuration | DeviceTelemetry |

---

## Prerequisites

- [ ] Eventhouse created in Fabric Workspace
- [ ] KQL Database created: `CreditFraudDB`
- [ ] Lakehouse bindings completed (see [lakehouse-binding.md](lakehouse-binding.md))
- [ ] CSV files ready for ingestion

---

## Part 1: CreditCard Timeseries Binding

### Configuration Summary

| Setting | Value |
|---------|-------|
| Entity | CreditCard |
| Eventhouse Table | CardTelemetry |
| Key Column | CardId |
| Timestamp Column | Timestamp |
| Database | CreditFraudDB |

### Timeseries Property Mappings

| Property | Column | Type | Description |
|----------|--------|------|-------------|
| TxnVelocity | TxnVelocity | double | Transactions per hour |
| DailySpend | DailySpend | double | Daily spending amount ($) |
| DeclineRate | DeclineRate | double | Transaction decline rate (%) |

### Step 1.1: Create KQL Table

In your Eventhouse KQL Database, run:

```kql
.create table CardTelemetry (
    Timestamp: datetime,
    CardId: string,
    TxnVelocity: real,
    DailySpend: real,
    DeclineRate: real
)
```

### Step 1.2: Create Ingestion Mapping

```kql
.create table CardTelemetry ingestion csv mapping 'CardTelemetryMapping'
'['
'   {"column": "Timestamp", "datatype": "datetime", "Properties": {"Ordinal": "0"}},'
'   {"column": "CardId", "datatype": "string", "Properties": {"Ordinal": "1"}},'
'   {"column": "TxnVelocity", "datatype": "real", "Properties": {"Ordinal": "2"}},'
'   {"column": "DailySpend", "datatype": "real", "Properties": {"Ordinal": "3"}},'
'   {"column": "DeclineRate", "datatype": "real", "Properties": {"Ordinal": "4"}}'
']'
```

### Step 1.3: Ingest Data

**Option A: One-time ingestion from CSV**

```kql
.ingest into table CardTelemetry (
    h'https://your-storage-account.blob.core.windows.net/data/CardTelemetry.csv'
) with (
    format = 'csv',
    ingestionMappingReference = 'CardTelemetryMapping',
    ignoreFirstRecord = true
)
```

**Option B: Upload via UI**
1. In Eventhouse, select `CardTelemetry` table
2. Click **Get Data** → **Local file**
3. Upload `CardTelemetry.csv`
4. Map columns and ingest

### Step 1.4: Verify Data

```kql
CardTelemetry
| take 10
```

### Step 1.5: Bind to Ontology

1. In Ontology Designer, select **CreditCard** entity
2. Click on **TxnVelocity** property
3. Click **Bind to Timeseries**
4. Configure:
   - **Source**: Eventhouse
   - **Database**: CreditFraudDB
   - **Table**: CardTelemetry
   - **Key Column**: CardId
   - **Timestamp Column**: Timestamp
   - **Value Column**: TxnVelocity
5. Click **Save Binding**
6. Repeat for **DailySpend** and **DeclineRate**

---

## Part 2: Device Timeseries Binding

### Configuration Summary

| Setting | Value |
|---------|-------|
| Entity | Device |
| Eventhouse Table | DeviceTelemetry |
| Key Column | DeviceId |
| Timestamp Column | Timestamp |
| Database | CreditFraudDB |

### Timeseries Property Mappings

| Property | Column | Type | Description |
|----------|--------|------|-------------|
| LoginAttempts | LoginAttempts | int | Total login attempts |
| FailedLogins | FailedLogins | int | Failed login attempts |
| SessionDuration | SessionDuration | double | Avg session duration (min) |

### Step 2.1: Create KQL Table

```kql
.create table DeviceTelemetry (
    Timestamp: datetime,
    DeviceId: string,
    LoginAttempts: int,
    FailedLogins: int,
    SessionDuration: real
)
```

### Step 2.2: Create Ingestion Mapping

```kql
.create table DeviceTelemetry ingestion csv mapping 'DeviceTelemetryMapping'
'['
'   {"column": "Timestamp", "datatype": "datetime", "Properties": {"Ordinal": "0"}},'
'   {"column": "DeviceId", "datatype": "string", "Properties": {"Ordinal": "1"}},'
'   {"column": "LoginAttempts", "datatype": "int", "Properties": {"Ordinal": "2"}},'
'   {"column": "FailedLogins", "datatype": "int", "Properties": {"Ordinal": "3"}},'
'   {"column": "SessionDuration", "datatype": "real", "Properties": {"Ordinal": "4"}}'
']'
```

### Step 2.3: Ingest Data

**Option A: One-time ingestion from CSV**

```kql
.ingest into table DeviceTelemetry (
    h'https://your-storage-account.blob.core.windows.net/data/DeviceTelemetry.csv'
) with (
    format = 'csv',
    ingestionMappingReference = 'DeviceTelemetryMapping',
    ignoreFirstRecord = true
)
```

**Option B: Upload via UI**
1. In Eventhouse, select `DeviceTelemetry` table
2. Click **Get Data** → **Local file**
3. Upload `DeviceTelemetry.csv`
4. Map columns and ingest

### Step 2.4: Verify Data

```kql
DeviceTelemetry
| take 10
```

### Step 2.5: Bind to Ontology

1. In Ontology Designer, select **Device** entity
2. Click on **LoginAttempts** property
3. Click **Bind to Timeseries**
4. Configure:
   - **Source**: Eventhouse
   - **Database**: CreditFraudDB
   - **Table**: DeviceTelemetry
   - **Key Column**: DeviceId
   - **Timestamp Column**: Timestamp
   - **Value Column**: LoginAttempts
5. Click **Save Binding**
6. Repeat for **FailedLogins** and **SessionDuration**

---

## Part 3: Validation Queries

### Validate CreditCard Timeseries

Query cards with high decline rates (fraud indicators):

```kql
CardTelemetry
| where DeclineRate > 20
| order by DeclineRate desc
| project Timestamp, CardId, TxnVelocity, DailySpend, DeclineRate
```

**Expected**: Cards CARD004, CARD007, CARD008, CARD015, CARD024 with elevated metrics

### Validate Device Timeseries

Query devices with suspicious login patterns:

```kql
DeviceTelemetry
| where FailedLogins > 5
| order by FailedLogins desc
| project Timestamp, DeviceId, LoginAttempts, FailedLogins, SessionDuration
```

**Expected**: Devices DEV005, DEV024, DEV026 with high failed logins

### Cross-Reference Fraud Correlation

```kql
CardTelemetry
| where DeclineRate > 30
| join kind=inner (
    DeviceTelemetry
    | where FailedLogins > 10
) on $left.Timestamp == $right.Timestamp
| project Timestamp, CardId, DeclineRate, DeviceId, FailedLogins
```

---

## Part 4: GQL Queries with Timeseries

After binding, you can query timeseries in GQL:

### Query 1: Cards with Anomalous Velocity

```gql
MATCH (card:CreditCard)
WHERE card.TxnVelocity > 10
RETURN card.CardId, card.CardType, card.TxnVelocity, card.DeclineRate
ORDER BY card.TxnVelocity DESC
```

### Query 2: Devices with High Failed Logins

```gql
MATCH (d:Device)
WHERE d.FailedLogins > 5
RETURN d.DeviceId, d.DeviceType, d.IsTrusted, d.FailedLogins, d.LoginAttempts
```

### Query 3: Fraud Pattern - High Velocity + Untrusted Device

```gql
MATCH (c:Customer)-[:OWNS]->(card:CreditCard)-[:HAS_TRANSACTION]->(t:Transaction)-[:USED_DEVICE]->(d:Device)
WHERE card.DeclineRate > 20 AND d.IsTrusted = false
RETURN c.FullName, card.CardId, card.DeclineRate, d.DeviceId, d.FailedLogins
```

---

## Troubleshooting

### Issue: "Timeseries data not showing in GQL"
- Verify Eventhouse binding is saved and published
- Check that Key Column matches entity key exactly
- Ensure Timestamp column is datetime type

### Issue: "Ingestion failed"
- Verify CSV column order matches mapping ordinals
- Check for NULL values in key columns
- Ensure datetime format is ISO 8601

### Issue: "Type mismatch"
- KQL uses `real` for double/float
- KQL uses `int` for integers
- Ensure CSV values match expected types

---

## Summary

| Entity | Table | Properties Bound | Status |
|--------|-------|------------------|--------|
| CreditCard | CardTelemetry | TxnVelocity, DailySpend, DeclineRate | ⬜ Pending |
| Device | DeviceTelemetry | LoginAttempts, FailedLogins, SessionDuration | ⬜ Pending |

After completing all bindings, mark as ✅ Complete.

---

## Next Steps

1. Return to [lakehouse-binding.md](lakehouse-binding.md) if entity bindings incomplete
2. Run demo scenarios from [demo-questions.md](demo-questions.md)
