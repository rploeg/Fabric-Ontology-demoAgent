# Credit Fraud Detection - Fabric Ontology Demo

> **Company**: FinanceGuard Bank  
> **Domain**: Financial Services - Credit Card Fraud Detection  
> **Version**: 1.0  
> **Created**: January 2026

---

## 🎯 Demo Overview

This demo showcases Microsoft Fabric's Ontology capabilities for **credit card fraud detection and prevention**. It demonstrates how graph-based queries can uncover fraud patterns that are difficult or impossible to detect with traditional SQL approaches.

### Key Use Cases

- **Fraud Ring Detection**: Identify connected fraud patterns across customers and merchants
- **Device Compromise Analysis**: Trace the blast radius of compromised devices
- **Impossible Travel Detection**: Flag geographically impossible transaction sequences
- **Real-Time Velocity Monitoring**: Correlate transaction velocity with fraud alerts
- **Compliance Reporting**: Geographic risk exposure for AML/KYC requirements

---

## 📊 Ontology Summary

### Entities (7)

| Entity | Key | Records | Description |
|--------|-----|---------|-------------|
| Customer | CustomerId | 25 | Bank customers with credit accounts |
| CreditCard | CardId | 35 | Credit cards with velocity metrics (timeseries) |
| Transaction | TransactionId | 80 | Individual credit card transactions |
| Merchant | MerchantId | 20 | Merchants with risk tier classification |
| FraudAlert | AlertId | 25 | ML-generated fraud alerts |
| Device | DeviceId | 30 | Devices with login metrics (timeseries) |
| GeoLocation | LocationId | 15 | Geographic locations with risk zones |

### Relationships (10)

| Relationship | Source → Target | Description |
|--------------|-----------------|-------------|
| OWNS | Customer → CreditCard | Customer owns credit cards |
| HAS_TRANSACTION | CreditCard → Transaction | Card used for transactions |
| OCCURRED_AT | Transaction → Merchant | Transaction location |
| TRIGGERED | Transaction → FraudAlert | Transaction triggered alert |
| USED_DEVICE | Transaction → Device | Device used for transaction |
| LOCATED_IN_TXN | Transaction → GeoLocation | Transaction geography |
| REGISTERED_DEVICE | Customer → Device | Customer's registered devices |
| LOCATED_IN_MERCHANT | Merchant → GeoLocation | Merchant location |
| FLAGGED_CARD | FraudAlert → CreditCard | Alert flagged this card |
| HAS_ALERT | Customer → FraudAlert | Customer's fraud alerts |

### Timeseries Properties

| Entity | Properties | Source |
|--------|------------|--------|
| CreditCard | TxnVelocity, DailySpend, DeclineRate | CardTelemetry (Eventhouse) |
| Device | LoginAttempts, FailedLogins, SessionDuration | DeviceTelemetry (Eventhouse) |

---

## 📁 Folder Structure

```
CreditFraud/
├── README.md                      # This file
├── .demo-metadata.yaml            # Automation metadata
├── credit-fraud.ttl               # Ontology definition (TTL format)
├── bindings.yaml                  # Machine-readable binding config
├── ontology-structure.md          # Entity/relationship documentation
├── ontology-diagram-slide.html    # Interactive presentation slide
├── lakehouse-binding.md           # Lakehouse binding instructions
├── eventhouse-binding.md          # Eventhouse binding instructions
├── demo-questions.md              # 5 demo scenarios with GQL queries
└── data/
    ├── DimCustomer.csv            # Customer dimension (25 rows)
    ├── DimCreditCard.csv          # Credit card dimension (35 rows)
    ├── DimMerchant.csv            # Merchant dimension (20 rows)
    ├── DimDevice.csv              # Device dimension (30 rows)
    ├── DimGeoLocation.csv         # Location dimension (15 rows)
    ├── FactTransaction.csv        # Transaction fact (80 rows)
    ├── FactFraudAlert.csv         # Fraud alert fact (25 rows)
    ├── FactCustomerDevice.csv     # Customer-Device edge (43 rows)
    ├── CardTelemetry.csv          # Card timeseries (70 rows)
    └── DeviceTelemetry.csv        # Device timeseries (64 rows)
```

---

## ✅ Prerequisites Checklist

Before starting the demo setup:

- [ ] Microsoft Fabric workspace with capacity
- [ ] Lakehouse created in workspace
- [ ] Eventhouse (KQL Database) created in workspace
- [ ] Ontology feature enabled in workspace
- [ ] **OneLake folder-level security DISABLED** (critical!)

### Required Permissions

- Workspace Admin or Member role
- Lakehouse read/write access
- Eventhouse admin access
- Ontology create/edit permissions

---

## 🚀 Quick Start Guide

### Option A: Manual Setup

1. **Create Ontology**
   - Import `credit-fraud.ttl` into Ontology Designer
   - Publish the ontology

2. **Setup Lakehouse**
   - Upload CSV files from `data/` folder
   - Create Delta tables (see `lakehouse-binding.md`)
   - Disable OneLake security

3. **Setup Eventhouse**
   - Create KQL tables (see `eventhouse-binding.md`)
   - Ingest timeseries CSVs
   - Create ingestion mappings

4. **Bind Data Sources**
   - Follow `lakehouse-binding.md` for entities
   - Follow `eventhouse-binding.md` for timeseries
   - Publish ontology

5. **Run Demo**
   - Open Graph Explorer
   - Execute queries from `demo-questions.md`

### Option B: Automated Setup

```bash
# Using fabric-demo automation tool
fabric-demo setup CreditFraud/
```

---

## 🎬 Demo Scenarios

### Scenario 1: Executive Briefing (10 minutes)

**Audience**: C-suite, Board members

**Script**:
1. Open `ontology-diagram-slide.html` in browser
2. Explain the 7 entities and their relationships
3. Run **Question 1** (Fraud Ring Detection) in Graph Explorer
4. Show how 5-hop traversal finds connected fraudsters
5. Compare to SQL approach (show complexity)

**Key Message**: "Graph queries find patterns that SQL cannot efficiently detect"

### Scenario 2: Technical Deep-Dive (20 minutes)

**Audience**: Data engineers, Architects

**Script**:
1. Walk through `credit-fraud.ttl` ontology definition
2. Explain binding configuration in `bindings.yaml`
3. Run **Question 2** (Device Compromise) - show 4-hop impact analysis
4. Run **Question 3** (Operational Correlation) - demonstrate timeseries integration
5. Show KQL tables in Eventhouse and explain ingestion

**Key Message**: "Ontology unifies Lakehouse and Eventhouse data in one query interface"

### Scenario 3: Compliance Demo (15 minutes)

**Audience**: Risk officers, Compliance teams

**Script**:
1. Explain geographic risk zones in data model
2. Run **Question 4** (Regulatory Compliance) - show exposure report
3. Demonstrate filtering by risk zone and aggregation
4. Run **Question 5** (End-to-End Genealogy) - show forensic trace
5. Discuss audit trail capabilities

**Key Message**: "Ontology enables instant compliance reporting across all data sources"

---

## ⚠️ Known Limitations

1. **No xsd:decimal**: Ontology queries return NULL for decimal types. Use double instead.
2. **OneLake Security**: Must be disabled for Graph queries to access data.
3. **Unbounded Quantifiers**: GQL doesn't support `*` for path lengths. Use bounded `{1,4}`.
4. **No OPTIONAL MATCH**: Not currently supported in Fabric GQL.
5. **Case Sensitivity**: Table and column names are case-sensitive in bindings.

---

## 🔧 Troubleshooting

### "No data returned from query"

1. Verify OneLake security is disabled
2. Check ontology is published (not draft)
3. Confirm Delta tables exist with data
4. Verify binding key columns match exactly

### "Timeseries properties show NULL"

1. Check Eventhouse binding configuration
2. Verify timestamp column is datetime type
3. Confirm KQL table has data for the entity key
4. Re-publish ontology after binding changes

### "Relationship returns empty"

1. Verify foreign key values exist in both tables
2. Check source/target key column mappings
3. Ensure no NULL values in key columns
4. Verify relationship direction matches data

---

## 📚 Additional Resources

- [Microsoft Fabric Ontology Documentation](https://learn.microsoft.com/fabric/ontology)
- [GQL Query Language Reference](https://learn.microsoft.com/fabric/ontology/gql)
- [Eventhouse KQL Reference](https://learn.microsoft.com/fabric/real-time-analytics)

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | January 2026 | Initial release |

---

## 👥 Contributors

- Generated by Fabric Ontology Demo Agent
- Based on FinanceGuard Bank fraud detection requirements

---

## 📄 License

This demo is provided for educational and demonstration purposes. Sample data is synthetic and does not represent real customers or transactions.
