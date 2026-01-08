# FreshMart Supermarket - Demo Questions

> **Version**: 1.0  
> **Last Updated**: January 2026  
> **Purpose**: Graph-powered business questions showcasing ontology capabilities

---

## Question Overview

| # | Theme | Hops | Business Focus |
|---|-------|------|----------------|
| 1 | Supply Chain Traceability | 3 | Food recall impact assessment |
| 2 | Impact Assessment | 4 | Supplier quality chain analysis |
| 3 | Operational Correlation | 2 + TS | Temperature anomaly detection |
| 4 | Compliance/Regulatory | 2 | Inspection audit trail |
| 5 | End-to-End Genealogy | 4 | Complete product journey |

---

## Question 1: Food Recall Traceability

### Business Question

> "A supplier has issued a recall for seafood products. Which stores received affected batches and what is their current status?"

### Why It Matters

When a food safety issue is identified at the supplier level, supermarkets must rapidly identify all affected locations to:
- Remove products from shelves immediately
- Notify customers who may have purchased affected items
- Coordinate with health authorities for reporting
- Minimize liability and brand damage

**Without graph**: Requires joining 4+ tables, writing complex SQL, and manual correlation
**With graph**: Single query traverses the supply chain in milliseconds

### Graph Traversal

```
Supplier ←[SUPPLIED_BY]← Product ←[CONTAINS]← ProductBatch →[RECEIVED_AT]→ Store
   │                         │                    │                         │
 SUP006                   PRD016-18            BAT016-18,               STR003,
(Ocean Harvest)          (Seafood)              BAT038                 STR006...
```

### GQL Query

```gql
MATCH (sup:Supplier)<-[:SUPPLIED_BY]-(p:Product)<-[:CONTAINS]-(b:ProductBatch)-[:RECEIVED_AT]->(s:Store)
WHERE sup.SupplierId = 'SUP006'
RETURN sup.SupplierName, p.ProductName, b.BatchId, b.BatchStatus, b.ExpiryDate, s.StoreName, s.City
ORDER BY b.BatchStatus, s.StoreName
```

### Expected Results

| SupplierName | ProductName | BatchId | BatchStatus | ExpiryDate | StoreName | City |
|--------------|-------------|---------|-------------|------------|-----------|------|
| Ocean Harvest Seafood | Atlantic Salmon Fillet | BAT038 | Recalled | 2025-11-25 | FreshMart Redmond | Redmond |
| Ocean Harvest Seafood | Atlantic Salmon Fillet | BAT016 | Active | 2025-12-10 | FreshMart Everett | Everett |
| Ocean Harvest Seafood | Shrimp 1lb Bag | BAT017 | Active | 2025-12-10 | FreshMart Everett | Everett |
| Ocean Harvest Seafood | Tilapia Fillets 1lb | BAT018 | Active | 2025-12-11 | FreshMart Everett | Everett |
| Ocean Harvest Seafood | Tilapia Fillets 1lb | BAT045 | Active | 2025-12-11 | FreshMart Olympia | Olympia |

### Why Ontology is Better

| Approach | Complexity | Time | Maintenance |
|----------|------------|------|-------------|
| **Traditional SQL** | 4 JOINs across tables, complex WHERE clauses | Minutes to write, seconds to run | Breaks when schema changes |
| **Graph Ontology** | Single MATCH pattern following relationships | Seconds to write, milliseconds to run | Schema-agnostic traversal |

**Key Advantage**: The ontology query reads like the business question - "Find supplier's products' batches' stores" - making it accessible to non-technical stakeholders.

---

## Question 2: Supplier Quality Chain Analysis

### Business Question

> "Which suppliers have products with failed quality inspections, and what is their overall quality rating compared to inspection outcomes?"

### Why It Matters

Procurement and quality teams need to:
- Identify suppliers with recurring quality issues
- Correlate supplier ratings with actual inspection outcomes
- Make data-driven decisions about supplier contracts
- Prioritize supplier audits based on risk

### Graph Traversal

```
QualityInspection →[INSPECTED]→ ProductBatch →[CONTAINS]→ Product →[SUPPLIED_BY]→ Supplier
        │                            │                       │                      │
    QI017,QI031                  BAT017,BAT031           PRD017,PRD013           SUP006,SUP005
   (Result=Fail)                 (Failed batches)       (Shrimp, Beef)       (Ocean, Valley)
```

### GQL Query

```gql
MATCH (qi:QualityInspection)-[:INSPECTED]->(b:ProductBatch)-[:CONTAINS]->(p:Product)-[:SUPPLIED_BY]->(sup:Supplier)
WHERE qi.Result = 'Fail'
RETURN sup.SupplierName, sup.Rating, p.ProductName, b.BatchId, qi.InspectionId, qi.InspectionDate, qi.Score, qi.Notes
ORDER BY sup.Rating DESC
```

### Expected Results

| SupplierName | Rating | ProductName | BatchId | InspectionId | InspectionDate | Score | Notes |
|--------------|--------|-------------|---------|--------------|----------------|-------|-------|
| Valley Meats Inc | 4.6 | Ground Beef 1lb | BAT031 | QI031 | 2025-12-02 | 38 | Ground beef temperature too high |
| Valley Meats Inc | 4.6 | Ground Beef 1lb | BAT037 | QI037 | 2025-11-21 | 30 | Ground beef contamination suspected |
| Ocean Harvest Seafood | 4.3 | Shrimp 1lb Bag | BAT017 | QI017 | 2025-12-06 | 45 | Shrimp showing early spoilage signs |
| Ocean Harvest Seafood | 4.3 | Atlantic Salmon Fillet | BAT038 | QI038 | 2025-11-23 | 20 | Salmon recall due to supplier issue |
| Green Valley Organics | 4.9 | Fresh Spinach 10oz | BAT036 | QI036 | 2025-11-26 | 25 | Spinach showing bacterial growth |

### Why Ontology is Better

| Metric | SQL Approach | Ontology Approach |
|--------|--------------|-------------------|
| **Query complexity** | 4 table JOINs with aggregations | Single path traversal |
| **Business readability** | Requires SQL expertise | Natural language pattern |
| **Extensibility** | New tables = new JOINs | New entities = same pattern |
| **Performance** | Full table scans likely | Index-optimized traversal |

**Key Insight**: High supplier ratings (4.6, 4.9) don't always correlate with zero failures - the graph reveals that even top-rated suppliers can have quality incidents, enabling proactive risk management.

---

## Question 3: Temperature Anomaly Detection (Operational Correlation)

### Business Question

> "Which product batches show temperature anomalies in storage, and have any of these batches failed quality inspections?"

### Why It Matters

Food safety compliance requires continuous cold chain monitoring. By correlating:
- Real-time storage telemetry (temperature, humidity)
- Quality inspection outcomes
- Product characteristics (perishability)

Operations teams can:
- Identify batches at risk before spoilage
- Predict quality issues from sensor data
- Reduce waste through proactive intervention

### Graph Traversal

```
ProductBatch →[INSPECTED]← QualityInspection
     │
 [Timeseries: StorageTemperature, Humidity]
     │
 Temperature > 5°C = Risk
```

### GQL Query

```gql
MATCH (b:ProductBatch)
WHERE b.StorageTemperature > 5.0
OPTIONAL MATCH (qi:QualityInspection)-[:INSPECTED]->(b)
RETURN b.BatchId, b.LotNumber, b.StorageTemperature, b.Humidity, b.DaysToExpiry,
       qi.InspectionId, qi.Result, qi.Score
ORDER BY b.StorageTemperature DESC
```

### Expected Results

| BatchId | LotNumber | StorageTemp | Humidity | DaysToExpiry | InspectionId | Result | Score |
|---------|-----------|-------------|----------|--------------|--------------|--------|-------|
| BAT031 | LOT-2025-12-031 | 10.2 | 78.5 | 2 | QI031 | Fail | 38 |
| BAT038 | LOT-2025-11-038 | 8.5 | 78.2 | 0 | QI038 | Fail | 20 |
| BAT017 | LOT-2025-12-017 | 8.2 | 78.8 | 3 | QI017 | Fail | 45 |
| BAT003 | LOT-2025-12-003 | 5.5 | 78.4 | 0 | QI003 | Conditional | 78 |

### Why Ontology is Better

| Capability | Traditional BI | Graph + Timeseries |
|------------|----------------|-------------------|
| **Data correlation** | Separate dashboards, manual analysis | Unified query across static + streaming |
| **Root cause analysis** | Export data, analyze offline | Real-time traversal to related entities |
| **Predictive alerts** | Rule-based on single metrics | Pattern-based across relationships |

**Key Insight**: All batches with temperatures >8°C resulted in **Failed** inspections, while 5-6°C showed **Conditional** results. This correlation enables predictive quality management.

---

## Question 4: Inspection Compliance Audit Trail

### Business Question

> "For regulatory audit purposes, show all quality inspections performed by each inspector, including which batches they checked and the inspection outcomes."

### Why It Matters

Food safety regulations (FDA, local health departments) require:
- Complete audit trails of all inspections
- Traceability of inspector → inspection → product
- Evidence that qualified personnel performed checks
- Historical records for compliance reviews

### Graph Traversal

```
Employee ←[PERFORMED_BY]← QualityInspection →[INSPECTED]→ ProductBatch
    │                            │                              │
  EMP002                    QI001-003,QI036                 BAT001-003,BAT036
(Michael Chen,              (Inspections)                   (Produce batches)
 QA Inspector)
```

### GQL Query

```gql
MATCH (e:Employee)<-[:PERFORMED_BY]-(qi:QualityInspection)-[:INSPECTED]->(b:ProductBatch)
WHERE e.Role = 'QA Inspector'
RETURN e.EmployeeId, e.FirstName, e.LastName, e.Role,
       qi.InspectionId, qi.InspectionDate, qi.Result, qi.Score,
       b.BatchId, b.LotNumber
ORDER BY e.LastName, qi.InspectionDate DESC
LIMIT 20
```

### Expected Results

| EmployeeId | FirstName | LastName | Role | InspectionId | InspectionDate | Result | Score | BatchId | LotNumber |
|------------|-----------|----------|------|--------------|----------------|--------|-------|---------|-----------|
| EMP002 | Michael | Chen | QA Inspector | QI039 | 2025-12-01 | Pass | 93 | BAT039 | LOT-2025-12-039 |
| EMP002 | Michael | Chen | QA Inspector | QI036 | 2025-11-26 | Fail | 25 | BAT036 | LOT-2025-11-036 |
| EMP002 | Michael | Chen | QA Inspector | QI003 | 2025-12-01 | Conditional | 78 | BAT003 | LOT-2025-12-003 |
| EMP002 | Michael | Chen | QA Inspector | QI002 | 2025-12-02 | Pass | 92 | BAT002 | LOT-2025-12-002 |
| EMP002 | Michael | Chen | QA Inspector | QI001 | 2025-12-01 | Pass | 95 | BAT001 | LOT-2025-12-001 |
| EMP004 | David | Kim | QA Inspector | QI037 | 2025-11-21 | Fail | 30 | BAT037 | LOT-2025-11-037 |
| EMP004 | David | Kim | QA Inspector | QI006 | 2025-12-04 | Pass | 90 | BAT006 | LOT-2025-12-006 |

### Why Ontology is Better

| Audit Requirement | SQL Report | Ontology Query |
|-------------------|------------|----------------|
| **Inspector workload** | GROUP BY with JOINs | Aggregate in RETURN |
| **Failure patterns** | Subqueries per inspector | FILTER on traversal |
| **Complete trail** | Multiple reports | Single query, all context |
| **Ad-hoc questions** | New report development | Modify MATCH pattern |

**Compliance Value**: Auditors can interactively explore the graph to answer follow-up questions without waiting for IT to build new reports.

---

## Question 5: End-to-End Product Genealogy

### Business Question

> "Trace the complete journey of a product from purchase order through supplier, to batch, to quality inspection - showing the full supply chain genealogy."

### Why It Matters

End-to-end traceability is essential for:
- Investigating food safety incidents
- Verifying chain of custody for premium/organic products
- Insurance claims requiring proof of handling
- Consumer transparency initiatives

### Graph Traversal

```
PurchaseOrder →[FULFILLED_BY]→ Supplier ←[SUPPLIED_BY]← Product ←[CONTAINS]← ProductBatch ←[INSPECTED]← QualityInspection
      │                           │                        │                      │                         │
    PO026,PO027                 SUP006                  PRD016-18            BAT016-18,BAT038           QI016-18,QI038
  (Orders to              (Ocean Harvest)             (Seafood)              (Batches)               (Inspections)
   Ocean Harvest)
```

### GQL Query

```gql
MATCH (po:PurchaseOrder)-[:FULFILLED_BY]->(sup:Supplier)<-[:SUPPLIED_BY]-(p:Product)<-[:CONTAINS]-(b:ProductBatch)<-[:INSPECTED]-(qi:QualityInspection)
WHERE sup.SupplierId = 'SUP006'
RETURN po.OrderId, po.OrderDate, po.TotalAmount, po.OrderStatus,
       sup.SupplierName, sup.Rating,
       p.ProductName, p.UnitPrice,
       b.BatchId, b.LotNumber, b.ExpiryDate, b.BatchStatus,
       qi.InspectionId, qi.Result, qi.Score
ORDER BY po.OrderDate DESC, qi.InspectionDate DESC
```

### Expected Results

| OrderId | OrderDate | TotalAmount | OrderStatus | SupplierName | Rating | ProductName | UnitPrice | BatchId | LotNumber | ExpiryDate | BatchStatus | InspectionId | Result | Score |
|---------|-----------|-------------|-------------|--------------|--------|-------------|-----------|---------|-----------|------------|-------------|--------------|--------|-------|
| PO027 | 2025-11-22 | 15750.50 | Delivered | Ocean Harvest Seafood | 4.3 | Atlantic Salmon Fillet | 12.99 | BAT038 | LOT-2025-11-038 | 2025-11-25 | Recalled | QI038 | Fail | 20 |
| PO027 | 2025-11-22 | 15750.50 | Delivered | Ocean Harvest Seafood | 4.3 | Atlantic Salmon Fillet | 12.99 | BAT016 | LOT-2025-12-016 | 2025-12-10 | Active | QI016 | Pass | 96 |
| PO026 | 2025-11-21 | 10500.25 | Delivered | Ocean Harvest Seafood | 4.3 | Shrimp 1lb Bag | 14.99 | BAT017 | LOT-2025-12-017 | 2025-12-10 | Active | QI017 | Fail | 45 |
| PO011 | 2025-12-03 | 16800.75 | Delivered | Ocean Harvest Seafood | 4.3 | Tilapia Fillets 1lb | 8.99 | BAT018 | LOT-2025-12-018 | 2025-12-11 | Active | QI018 | Pass | 92 |

### Why Ontology is Better

| Genealogy Aspect | Relational Approach | Graph Approach |
|------------------|---------------------|----------------|
| **Path discovery** | Pre-defined JOINs only | Flexible path patterns |
| **Depth of traversal** | Exponential complexity | Linear query growth |
| **New relationships** | Schema migration required | Add edge, query immediately |
| **Visual exploration** | Build custom UI | Native graph visualization |

**Business Value**: Complete product genealogy in a single query enables instant response to regulators, insurers, and consumers asking "where did this product come from?"

---

## Data Agent Instructions

When users ask natural language questions about the FreshMart data, use the following guidance:

### Entity Recognition

| User Says | Map To Entity | Key Property |
|-----------|---------------|--------------|
| "store", "location", "branch" | Store | StoreId |
| "product", "item", "SKU" | Product | ProductId |
| "supplier", "vendor", "source" | Supplier | SupplierId |
| "batch", "lot", "shipment" | ProductBatch | BatchId |
| "category", "department", "type" | Category | CategoryId |
| "employee", "staff", "worker", "inspector" | Employee | EmployeeId |
| "order", "purchase order", "PO" | PurchaseOrder | OrderId |
| "inspection", "quality check", "QA" | QualityInspection | InspectionId |

### Relationship Recognition

| User Says | Map To Relationship |
|-----------|---------------------|
| "belongs to", "in category", "type of" | BELONGS_TO |
| "supplied by", "from supplier", "sourced from" | SUPPLIED_BY |
| "stocks", "carries", "sells", "has inventory" | STOCKS |
| "employs", "works at", "assigned to" | EMPLOYS |
| "contains", "is in batch", "batch of" | CONTAINS |
| "received at", "delivered to", "shipped to" | RECEIVED_AT |
| "ordered by", "placed by" | ORDERED_BY |
| "fulfilled by", "shipped by" | FULFILLED_BY |
| "inspected", "checked", "tested" | INSPECTED |
| "performed by", "done by", "conducted by" | PERFORMED_BY |

### Common Query Patterns

**Traceability Questions**:
```gql
MATCH (source)-[:REL1]->(middle)-[:REL2]->(target)
WHERE source.property = 'value'
RETURN ...
```

**Aggregation Questions**:
```gql
MATCH (e:Entity)-[:REL]->(related)
RETURN e.property, COUNT(related) as count
GROUP BY e.property
```

**Timeseries Questions**:
```gql
MATCH (e:Entity)
WHERE e.timeseriesProperty > threshold
RETURN e.key, e.timeseriesProperty
```

### Status Values Reference

| Entity | Status Field | Possible Values |
|--------|--------------|-----------------|
| ProductBatch | BatchStatus | Active, Expired, Recalled, Sold |
| PurchaseOrder | OrderStatus | Pending, Shipped, Delivered, Cancelled |
| QualityInspection | Result | Pass, Fail, Conditional |
| Employee | IsActive | true, false |
| Category | IsPerishable | true, false |

### Sample Natural Language → GQL Mappings

**User**: "Which stores have products from suppliers with low ratings?"
```gql
MATCH (s:Store)-[:STOCKS]->(p:Product)-[:SUPPLIED_BY]->(sup:Supplier)
WHERE sup.Rating < 4.5
RETURN DISTINCT s.StoreName, sup.SupplierName, sup.Rating
```

**User**: "Show me all failed inspections this month"
```gql
MATCH (qi:QualityInspection)
WHERE qi.Result = 'Fail' AND qi.InspectionDate >= datetime('2025-12-01')
RETURN qi.InspectionId, qi.InspectionDate, qi.Score, qi.Notes
```

**User**: "What products are expiring soon?"
```gql
MATCH (b:ProductBatch)-[:CONTAINS]->(p:Product)
WHERE b.DaysToExpiry <= 3 AND b.BatchStatus = 'Active'
RETURN p.ProductName, b.BatchId, b.ExpiryDate, b.DaysToExpiry
ORDER BY b.DaysToExpiry ASC
```

**User**: "Trace the supply chain for recalled products"
```gql
MATCH (b:ProductBatch)-[:CONTAINS]->(p:Product)-[:SUPPLIED_BY]->(sup:Supplier)
WHERE b.BatchStatus = 'Recalled'
MATCH (b)-[:RECEIVED_AT]->(s:Store)
RETURN sup.SupplierName, p.ProductName, b.BatchId, s.StoreName
```
