# Credit Fraud Detection - Lakehouse Binding Instructions

> **Version**: 1.0  
> **Last Updated**: January 2026  
> **Ontology**: CreditFraud  
> **Company**: FinanceGuard Bank

---

## Prerequisites

### ⚠️ CRITICAL: Disable OneLake Security

Before binding, you **MUST** disable OneLake folder-level security:

1. Go to **Lakehouse Settings** → **OneLake**
2. Set **"OneLake folder level security"** to **OFF**
3. Wait 5 minutes for propagation

> **Why?** Graph queries cannot access data with folder-level security enabled.

### Required Resources

- [ ] Fabric Workspace with Lakehouse capacity
- [ ] Ontology created and published
- [ ] CSV files uploaded to Lakehouse Files section
- [ ] OneLake security disabled (see above)

---

## Step 1: Upload CSV Files to Lakehouse

1. Open your Lakehouse in Fabric
2. Navigate to **Files** section
3. Create folder: `CreditFraud/data/`
4. Upload all CSV files from the `data/` folder:
   - DimCustomer.csv
   - DimCreditCard.csv
   - DimMerchant.csv
   - DimDevice.csv
   - DimGeoLocation.csv
   - FactTransaction.csv
   - FactFraudAlert.csv
   - FactCustomerDevice.csv

---

## Step 2: Create Delta Tables

For each CSV file, create a Delta table:

### Option A: Using Notebook (Recommended)

```python
# Run this for each table
from pyspark.sql import SparkSession

tables = [
    "DimCustomer", "DimCreditCard", "DimMerchant", "DimDevice", 
    "DimGeoLocation", "FactTransaction", "FactFraudAlert", "FactCustomerDevice"
]

for table in tables:
    df = spark.read.option("header", "true").option("inferSchema", "true").csv(f"Files/CreditFraud/data/{table}.csv")
    df.write.mode("overwrite").format("delta").saveAsTable(table)
    print(f"Created table: {table}")
```

### Option B: Using UI

1. Right-click on CSV file → **Load to Table**
2. Name table exactly as shown below
3. Repeat for each file

---

## Step 3: Entity Bindings

### 3.1 Customer Entity

| Property | Column | Type |
|----------|--------|------|
| **CustomerId** (Key) | CustomerId | string |
| FullName | FullName | string |
| Email | Email | string |
| PhoneNumber | PhoneNumber | string |
| RiskScore | RiskScore | double |
| AccountStatus | AccountStatus | string |
| CreatedDate | CreatedDate | datetime |

**Binding Steps:**
1. In Ontology Designer, select **Customer** entity
2. Click **Bind to Data Source**
3. Select Lakehouse: `CreditFraudLakehouse`
4. Select Table: `DimCustomer`
5. Map Key: `CustomerId` → `CustomerId`
6. Map each property to its corresponding column
7. Click **Save Binding**

---

### 3.2 CreditCard Entity

| Property | Column | Type |
|----------|--------|------|
| **CardId** (Key) | CardId | string |
| CardNumber | CardNumber | string |
| CardType | CardType | string |
| CreditLimit | CreditLimit | double |
| IssuedDate | IssuedDate | datetime |
| ExpiryDate | ExpiryDate | datetime |
| IsActive | IsActive | boolean |

> ⚠️ **Timeseries Note**: Properties `TxnVelocity`, `DailySpend`, and `DeclineRate` are bound separately via Eventhouse. See [eventhouse-binding.md](eventhouse-binding.md).

**Binding Steps:**
1. Select **CreditCard** entity
2. Click **Bind to Data Source**
3. Select Lakehouse: `CreditFraudLakehouse`
4. Select Table: `DimCreditCard`
5. Map Key: `CardId` → `CardId`
6. Map each property (excluding timeseries)
7. Click **Save Binding**

---

### 3.3 Transaction Entity

| Property | Column | Type |
|----------|--------|------|
| **TransactionId** (Key) | TransactionId | string |
| Amount | Amount | double |
| TransactionType | TransactionType | string |
| TransactionDate | TransactionDate | datetime |
| IsOnline | IsOnline | boolean |
| RiskFlag | RiskFlag | string |

**Binding Steps:**
1. Select **Transaction** entity
2. Click **Bind to Data Source**
3. Select Lakehouse: `CreditFraudLakehouse`
4. Select Table: `FactTransaction`
5. Map Key: `TransactionId` → `TransactionId`
6. Map each property
7. Click **Save Binding**

---

### 3.4 Merchant Entity

| Property | Column | Type |
|----------|--------|------|
| **MerchantId** (Key) | MerchantId | string |
| MerchantName | MerchantName | string |
| MerchantCategory | MerchantCategory | string |
| RiskTier | RiskTier | string |
| RegistrationDate | RegistrationDate | datetime |

**Binding Steps:**
1. Select **Merchant** entity
2. Click **Bind to Data Source**
3. Select Lakehouse: `CreditFraudLakehouse`
4. Select Table: `DimMerchant`
5. Map Key: `MerchantId` → `MerchantId`
6. Map each property
7. Click **Save Binding**

---

### 3.5 FraudAlert Entity

| Property | Column | Type |
|----------|--------|------|
| **AlertId** (Key) | AlertId | string |
| AlertType | AlertType | string |
| Severity | Severity | string |
| AlertDate | AlertDate | datetime |
| Resolution | Resolution | string |
| InvestigatorNotes | InvestigatorNotes | string |

**Binding Steps:**
1. Select **FraudAlert** entity
2. Click **Bind to Data Source**
3. Select Lakehouse: `CreditFraudLakehouse`
4. Select Table: `FactFraudAlert`
5. Map Key: `AlertId` → `AlertId`
6. Map each property
7. Click **Save Binding**

---

### 3.6 Device Entity

| Property | Column | Type |
|----------|--------|------|
| **DeviceId** (Key) | DeviceId | string |
| DeviceType | DeviceType | string |
| DeviceOS | DeviceOS | string |
| FirstSeen | FirstSeen | datetime |
| LastSeen | LastSeen | datetime |
| IsTrusted | IsTrusted | boolean |

> ⚠️ **Timeseries Note**: Properties `LoginAttempts`, `FailedLogins`, and `SessionDuration` are bound separately via Eventhouse. See [eventhouse-binding.md](eventhouse-binding.md).

**Binding Steps:**
1. Select **Device** entity
2. Click **Bind to Data Source**
3. Select Lakehouse: `CreditFraudLakehouse`
4. Select Table: `DimDevice`
5. Map Key: `DeviceId` → `DeviceId`
6. Map each property (excluding timeseries)
7. Click **Save Binding**

---

### 3.7 GeoLocation Entity

| Property | Column | Type |
|----------|--------|------|
| **LocationId** (Key) | LocationId | string |
| City | City | string |
| Country | Country | string |
| Region | Region | string |
| Latitude | Latitude | double |
| Longitude | Longitude | double |
| RiskZone | RiskZone | string |

**Binding Steps:**
1. Select **GeoLocation** entity
2. Click **Bind to Data Source**
3. Select Lakehouse: `CreditFraudLakehouse`
4. Select Table: `DimGeoLocation`
5. Map Key: `LocationId` → `LocationId`
6. Map each property
7. Click **Save Binding**

---

## Step 4: Relationship Bindings

### 4.1 OWNS (Customer → CreditCard)

| Source | Target | Table | Source Key | Target Key |
|--------|--------|-------|------------|------------|
| Customer | CreditCard | DimCreditCard | CustomerId | CardId |

**Binding Steps:**
1. Select **OWNS** relationship
2. Click **Bind to Data Source**
3. Select Table: `DimCreditCard`
4. Source Key Column: `CustomerId`
5. Target Key Column: `CardId`
6. Click **Save Binding**

---

### 4.2 REGISTERED_DEVICE (Customer → Device)

| Source | Target | Table | Source Key | Target Key |
|--------|--------|-------|------------|------------|
| Customer | Device | FactCustomerDevice | CustomerId | DeviceId |

**Binding Steps:**
1. Select **REGISTERED_DEVICE** relationship
2. Select Table: `FactCustomerDevice`
3. Source Key Column: `CustomerId`
4. Target Key Column: `DeviceId`
5. Click **Save Binding**

---

### 4.3 HAS_ALERT (Customer → FraudAlert)

| Source | Target | Table | Source Key | Target Key |
|--------|--------|-------|------------|------------|
| Customer | FraudAlert | FactFraudAlert | CustomerId | AlertId |

**Binding Steps:**
1. Select **HAS_ALERT** relationship
2. Select Table: `FactFraudAlert`
3. Source Key Column: `CustomerId`
4. Target Key Column: `AlertId`
5. Click **Save Binding**

---

### 4.4 HAS_TRANSACTION (CreditCard → Transaction)

| Source | Target | Table | Source Key | Target Key |
|--------|--------|-------|------------|------------|
| CreditCard | Transaction | FactTransaction | CardId | TransactionId |

**Binding Steps:**
1. Select **HAS_TRANSACTION** relationship
2. Select Table: `FactTransaction`
3. Source Key Column: `CardId`
4. Target Key Column: `TransactionId`
5. Click **Save Binding**

---

### 4.5 OCCURRED_AT (Transaction → Merchant)

| Source | Target | Table | Source Key | Target Key |
|--------|--------|-------|------------|------------|
| Transaction | Merchant | FactTransaction | TransactionId | MerchantId |

**Binding Steps:**
1. Select **OCCURRED_AT** relationship
2. Select Table: `FactTransaction`
3. Source Key Column: `TransactionId`
4. Target Key Column: `MerchantId`
5. Click **Save Binding**

---

### 4.6 TRIGGERED (Transaction → FraudAlert)

| Source | Target | Table | Source Key | Target Key |
|--------|--------|-------|------------|------------|
| Transaction | FraudAlert | FactFraudAlert | TransactionId | AlertId |

**Binding Steps:**
1. Select **TRIGGERED** relationship
2. Select Table: `FactFraudAlert`
3. Source Key Column: `TransactionId`
4. Target Key Column: `AlertId`
5. Click **Save Binding**

---

### 4.7 USED_DEVICE (Transaction → Device)

| Source | Target | Table | Source Key | Target Key |
|--------|--------|-------|------------|------------|
| Transaction | Device | FactTransaction | TransactionId | DeviceId |

**Binding Steps:**
1. Select **USED_DEVICE** relationship
2. Select Table: `FactTransaction`
3. Source Key Column: `TransactionId`
4. Target Key Column: `DeviceId`
5. Click **Save Binding**

---

### 4.8 LOCATED_IN_TXN (Transaction → GeoLocation)

| Source | Target | Table | Source Key | Target Key |
|--------|--------|-------|------------|------------|
| Transaction | GeoLocation | FactTransaction | TransactionId | LocationId |

**Binding Steps:**
1. Select **LOCATED_IN_TXN** relationship
2. Select Table: `FactTransaction`
3. Source Key Column: `TransactionId`
4. Target Key Column: `LocationId`
5. Click **Save Binding**

---

### 4.9 LOCATED_IN_MERCHANT (Merchant → GeoLocation)

| Source | Target | Table | Source Key | Target Key |
|--------|--------|-------|------------|------------|
| Merchant | GeoLocation | DimMerchant | MerchantId | LocationId |

**Binding Steps:**
1. Select **LOCATED_IN_MERCHANT** relationship
2. Select Table: `DimMerchant`
3. Source Key Column: `MerchantId`
4. Target Key Column: `LocationId`
5. Click **Save Binding**

---

### 4.10 FLAGGED_CARD (FraudAlert → CreditCard)

| Source | Target | Table | Source Key | Target Key |
|--------|--------|-------|------------|------------|
| FraudAlert | CreditCard | FactFraudAlert | AlertId | CardId |

**Binding Steps:**
1. Select **FLAGGED_CARD** relationship
2. Select Table: `FactFraudAlert`
3. Source Key Column: `AlertId`
4. Target Key Column: `CardId`
5. Click **Save Binding**

---

## Step 5: Validation

After completing all bindings:

1. **Publish** the ontology
2. Navigate to **Graph Explorer**
3. Run test query:

```gql
MATCH (c:Customer)-[:OWNS]->(card:CreditCard)
WHERE c.CustomerId = 'CUST001'
RETURN c.FullName, card.CardNumber, card.CardType
```

**Expected Result**: Sarah Mitchell with 2 credit cards

---

## Troubleshooting

### Issue: "No data returned"
- Verify OneLake security is disabled
- Check table names match exactly (case-sensitive)
- Ensure Delta tables were created from CSVs

### Issue: "Binding failed"
- Verify column names match property names
- Check data types are compatible
- Ensure key columns have unique values

### Issue: "Relationship returns empty"
- Verify foreign key values exist in parent table
- Check join columns are mapped correctly

---

## Next Steps

1. Complete [Eventhouse Binding](eventhouse-binding.md) for timeseries properties
2. Run demo questions from [demo-questions.md](demo-questions.md)
