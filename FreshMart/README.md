# FreshMart Supermarket - Fabric Ontology Demo

> **Version**: 1.0  
> **Domain**: Retail / Grocery Supply Chain  
> **Created**: January 2026  
> **Status**: Ready for deployment

---

## 🛒 Demo Overview

**FreshMart Supermarkets** is a fictional regional grocery chain operating 12 stores across Washington State. This demo showcases how Microsoft Fabric's Ontology and Graph capabilities enable:

- **Supply Chain Traceability**: Track products from supplier through store shelves
- **Food Safety Compliance**: Monitor quality inspections and cold chain integrity
- **Operational Intelligence**: Correlate store traffic with sales performance
- **Regulatory Audit Trails**: Complete inspection history by inspector and batch

### Target Audience

| Audience | Focus Areas |
|----------|-------------|
| **Operations Managers** | Inventory optimization, store performance |
| **Supply Chain Analysts** | Supplier quality, batch traceability |
| **Compliance Officers** | Inspection audits, recall management |
| **IT/Data Teams** | Ontology implementation, data binding |

---

## 📊 Entity & Relationship Summary

### Entities (8)

| Entity | Description | Key | Timeseries |
|--------|-------------|-----|------------|
| Store | Physical supermarket locations | StoreId | ✅ FootTraffic, SalesVelocity, AvgTransactionValue |
| Product | SKUs sold across stores | ProductId | ❌ |
| Supplier | Vendor partners | SupplierId | ❌ |
| ProductBatch | Shipment lots with expiry tracking | BatchId | ✅ StorageTemperature, Humidity, DaysToExpiry |
| Category | Product classification | CategoryId | ❌ |
| Employee | Store staff including QA inspectors | EmployeeId | ❌ |
| PurchaseOrder | Orders placed to suppliers | OrderId | ❌ |
| QualityInspection | Food safety checks on batches | InspectionId | ❌ |

### Relationships (10)

```
Store ──STOCKS──> Product ──BELONGS_TO──> Category
  │                  │
  │                  └──SUPPLIED_BY──> Supplier
  │                                       ▲
  └──EMPLOYS──> Employee                  │
                   ▲                      │
                   │              PurchaseOrder
                   │                  │    │
         PERFORMED_BY             ORDERED_BY  FULFILLED_BY
                   │                  │    │
                   │                  ▼    │
        QualityInspection ◄──── ProductBatch
                   │                  │
               INSPECTED          CONTAINS ──> Product
                                      │
                              RECEIVED_AT ──> Store
```

---

## 📁 Folder Structure

```
FreshMart\
├── README.md                          # This file
├── .demo-metadata.yaml                # Automation metadata
├── demo-questions.md                  # 5 demo scenarios with GQL queries
├── ontology-structure.md              # Entity/relationship design
│
├── Bindings\
│   ├── bindings.yaml                  # Machine-readable binding config
│   ├── lakehouse-binding.md           # Lakehouse binding instructions
│   └── eventhouse-binding.md          # Eventhouse timeseries binding
│
├── Data\
│   ├── Lakehouse\                     # Dimension and fact tables
│   │   ├── DimStore.csv              (12 stores)
│   │   ├── DimProduct.csv            (28 products)
│   │   ├── DimSupplier.csv           (10 suppliers)
│   │   ├── DimProductBatch.csv       (45 batches)
│   │   ├── DimCategory.csv           (8 categories)
│   │   ├── DimEmployee.csv           (24 employees)
│   │   ├── FactPurchaseOrder.csv     (35 orders)
│   │   ├── FactQualityInspection.csv (40 inspections)
│   │   └── FactStoreInventory.csv    (70 inventory records)
│   │
│   └── Eventhouse\                    # Timeseries data
│       ├── StoreTelemetry.csv        (54 readings)
│       └── BatchTelemetry.csv        (63 readings)
│
└── Ontology\
    ├── freshmart.ttl                  # OWL/RDF ontology definition
    └── ontology-diagram-slide.html    # Interactive visualization
```

---

## ✅ Prerequisites Checklist

Before setting up this demo, ensure you have:

- [ ] **Microsoft Fabric workspace** with capacity enabled
- [ ] **Fabric trial or paid capacity** (P1 or higher recommended)
- [ ] **Permissions** to create Lakehouse, Eventhouse, and Ontology items
- [ ] **OneLake security disabled** on Lakehouse (required for binding)

### Fabric Items to Create

| Item | Name | Purpose |
|------|------|---------|
| Lakehouse | FreshMartLakehouse | Store dimension and fact tables |
| Eventhouse | FreshMartEventhouse | Store timeseries telemetry |
| Ontology | FreshMartOntology | Define and bind graph model |

---

## 🚀 Quick Start Guide

### Option 1: Manual Setup

1. **Create Lakehouse**
   ```powershell
   # Fabric Portal → New → Lakehouse → "FreshMartLakehouse"
   ```

2. **Upload CSV Files**
   - Navigate to `Data\Lakehouse\` folder
   - Upload all CSV files to Lakehouse Files section
   - Right-click each file → Load to Tables

3. **Create Eventhouse**
   ```powershell
   # Fabric Portal → New → Eventhouse → "FreshMartEventhouse"
   ```
   - Create KQL Database
   - Run ingestion commands from `Bindings\eventhouse-binding.md`

4. **Create Ontology**
   ```powershell
   # Fabric Portal → New → Ontology → "FreshMartOntology"
   ```
   - Upload `Ontology/freshmart.ttl`
   - Follow binding steps in `Bindings/lakehouse-binding.md`

5. **Test Queries**
   - Open Graph Explorer in Ontology
   - Run queries from `demo-questions.md`

### Option 2: Automated Setup (CLI)

```powershell
# Navigate to Demo-automation folder
cd Demo-automation

# Install Demo generator
pip install -e .

# Navigate to demo folder
cd ..\FreshMart

# Run automated setup
python -m demo_automation setup .\

# Validate bindings
python -m demo_automation validate .\
```

---

## ⚠️ Known Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| No `xsd:decimal` support | Returns NULL in queries | Use `xsd:double` instead |
| OneLake security must be disabled | Required for binding | Disable in Lakehouse settings |
| OPTIONAL MATCH not supported | Can't do left outer joins | Use separate queries |
| Unbounded path quantifiers | `*` not allowed | Use bounded `{1,4}` |

---

## 🎬 Demo Scenarios

### Scenario 1: Food Recall Response (5 minutes)

**Setup**: Ocean Harvest Seafood (SUP006) has issued a recall for salmon products.

**Demo Flow**:
1. Show the recall notification scenario
2. Run traceability query (Question 1 from demo-questions.md)
3. Highlight how graph traverses Supplier → Product → Batch → Store
4. Show affected stores on map (Seattle area)
5. Discuss response time: SQL = hours, Graph = seconds

**Key Talking Points**:
- Real-time traceability saves time during food safety incidents
- Single query replaces 4-table JOIN operations
- Business stakeholders can read and understand the query

---

### Scenario 2: Quality-Supplier Correlation (5 minutes)

**Setup**: Procurement wants to review supplier performance based on inspection data.

**Demo Flow**:
1. Run supplier quality analysis (Question 2)
2. Show that high-rated suppliers (4.6+) still have failures
3. Correlate temperature telemetry with failed inspections (Question 3)
4. Demonstrate predictive pattern: temp >8°C = likely failure

**Key Talking Points**:
- Graph connects operational data with transactional data
- Timeseries integration enables IoT + business correlation
- Proactive quality management reduces waste

---

### Scenario 3: Compliance Audit (5 minutes)

**Setup**: FDA auditor requests inspection records for the past month.

**Demo Flow**:
1. Run audit trail query (Question 4)
2. Show complete inspector → inspection → batch chain
3. Demonstrate filtering by date range, result type
4. Export results for compliance documentation

**Key Talking Points**:
- Complete audit trail in single query
- No data silos - all context in one place
- Auditors can self-serve with natural language

---

## 📈 Data Highlights

### Interesting Data Points for Demo

| Scenario | Data Point | Location |
|----------|------------|----------|
| **Failed Inspections** | BAT017 (shrimp), BAT031 (beef), BAT036-38 (various) | FactQualityInspection |
| **Recalled Batch** | BAT038 - Atlantic Salmon from SUP006 | DimProductBatch |
| **Temperature Anomaly** | BAT017 shows 8.2°C peak (spoilage threshold) | BatchTelemetry |
| **High Traffic Store** | STR001 (Downtown Seattle) - 310 peak foot traffic | StoreTelemetry |
| **Top Supplier** | SUP009 (Green Valley Organics) - 4.9 rating | DimSupplier |

### Data Volume Summary

| Category | Tables | Total Rows |
|----------|--------|------------|
| Dimension Tables | 6 | 127 |
| Fact Tables | 3 | 145 |
| Edge/Junction Tables | 1 | 70 |
| Timeseries Tables | 2 | 117 |
| **Total** | **12** | **459** |

---

## 🔗 Related Resources

### Documentation
- [Microsoft Fabric IQ Overview](https://learn.microsoft.com/en-us/fabric/iq/overview)
- [Data Binding Guide](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data)
- [GQL Language Guide](https://learn.microsoft.com/en-us/fabric/graph/gql-language-guide)
- [Graph Limitations](https://learn.microsoft.com/en-us/fabric/graph/limitations)

### Support
- [Fabric Known Issues](https://support.fabric.microsoft.com/known-issues/?product=IQ)

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | January 2026 | Initial release |

---

## 🤝 Contributing

To extend this demo:

1. Add new entities to `Ontology/freshmart.ttl`
2. Create corresponding CSV files in `Data/Lakehouse/`
3. Update `Bindings/bindings.yaml` with new bindings
4. Add demo questions to `demo-questions.md`
5. Update this README

---

*Generated by Fabric Ontology Demo Agent v3.3*
