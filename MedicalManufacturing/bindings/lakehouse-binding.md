# Lakehouse Binding Instructions

This guide explains how to bind static data from OneLake Lakehouse tables to the BD Medical Manufacturing ontology.

## Prerequisites

- [ ] Fabric workspace with Ontology preview enabled
- [ ] Lakehouse created with **OneLake security DISABLED**
- [ ] CSV files uploaded and converted to managed Delta tables
- [ ] User has read access to the Lakehouse

---

## Step 1: Upload CSV Files to Lakehouse

1. Navigate to your Fabric workspace
2. Open your Lakehouse
3. Click **Get data** → **Upload files**
4. Upload all CSV files from `data/lakehouse/` folder:
   - DimProduct.csv
   - DimFacility.csv
   - DimSupplier.csv
   - DimComponent.csv
   - DimProductionBatch.csv
   - DimRegulatorySubmission.csv
   - FactQualityEvent.csv
   - FactCustomerComplaint.csv
   - FactBatchComponent.csv
   - FactFacilitySupplier.csv

5. For each file, right-click → **Load to Tables** → **New table**
6. Verify tables appear under **Tables** (not Files)

---

## Step 2: Create Ontology Item

1. In workspace, click **+ New item** → **Ontology (preview)**
2. Name: `BD-Medical-Manufacturing-Ontology`
3. Click **Create**

---

## Step 3: Import TTL File (Optional)

If using the TTL file to pre-create entity types:
1. Open the ontology
2. Click **Import** → Select `bd-medical-manufacturing.ttl`
3. Review imported entity types and relationships

---

## Step 4: Bind Static Data to Entity Types

### 4.1 Product Entity

| Setting | Value |
|---------|-------|
| Entity Type | Product |
| Source | Lakehouse |
| Table | DimProduct |
| Key Column | ProductId |

**Property Mappings:**

| Property | Column | Type |
|----------|--------|------|
| ProductId | ProductId | string |
| ProductName | ProductName | string |
| ProductLine | ProductLine | string |
| Segment | Segment | string |
| SKU | SKU | string |
| UnitOfMeasure | UnitOfMeasure | string |
| RegulatoryClass | RegulatoryClass | string |
| IsActive | IsActive | boolean |

---

### 4.2 Facility Entity

| Setting | Value |
|---------|-------|
| Entity Type | Facility |
| Source | Lakehouse |
| Table | DimFacility |
| Key Column | FacilityId |

**Property Mappings:**

| Property | Column | Type |
|----------|--------|------|
| FacilityId | FacilityId | string |
| FacilityName | FacilityName | string |
| Country | Country | string |
| Region | Region | string |
| FacilityType | FacilityType | string |
| Capacity | Capacity | int |
| CertificationStatus | CertificationStatus | string |

> ⚠️ **Note:** Timeseries properties (DailyOutput, EquipmentUptime) are bound separately via Eventhouse.

---

### 4.3 Supplier Entity

| Setting | Value |
|---------|-------|
| Entity Type | Supplier |
| Source | Lakehouse |
| Table | DimSupplier |
| Key Column | SupplierId |

**Property Mappings:**

| Property | Column | Type |
|----------|--------|------|
| SupplierId | SupplierId | string |
| SupplierName | SupplierName | string |
| Country | Country | string |
| SupplierType | SupplierType | string |
| RiskTier | RiskTier | string |
| ContractStatus | ContractStatus | string |

---

### 4.4 Component Entity

| Setting | Value |
|---------|-------|
| Entity Type | Component |
| Source | Lakehouse |
| Table | DimComponent |
| Key Column | ComponentId |

**Property Mappings:**

| Property | Column | Type |
|----------|--------|------|
| ComponentId | ComponentId | string |
| ComponentName | ComponentName | string |
| ComponentType | ComponentType | string |
| Material | Material | string |
| CriticalityLevel | CriticalityLevel | string |
| SupplierId | SupplierId | string |

---

### 4.5 ProductionBatch Entity

| Setting | Value |
|---------|-------|
| Entity Type | ProductionBatch |
| Source | Lakehouse |
| Table | DimProductionBatch |
| Key Column | BatchId |

**Property Mappings:**

| Property | Column | Type |
|----------|--------|------|
| BatchId | BatchId | string |
| ProductId | ProductId | string |
| FacilityId | FacilityId | string |
| BatchDate | BatchDate | datetime |
| ExpirationDate | ExpirationDate | datetime |
| Quantity | Quantity | int |
| BatchStatus | BatchStatus | string |

> ⚠️ **Note:** Timeseries properties (YieldRate, DefectCount, CycleTimeMin) are bound separately via Eventhouse.

---

### 4.6 QualityEvent Entity

| Setting | Value |
|---------|-------|
| Entity Type | QualityEvent |
| Source | Lakehouse |
| Table | FactQualityEvent |
| Key Column | EventId |

**Property Mappings:**

| Property | Column | Type |
|----------|--------|------|
| EventId | EventId | string |
| BatchId | BatchId | string |
| EventType | EventType | string |
| Severity | Severity | string |
| RootCause | RootCause | string |
| EventStatus | EventStatus | string |
| EventDate | EventDate | datetime |
| ResolutionDate | ResolutionDate | datetime |
| SubmissionId | SubmissionId | string |

---

### 4.7 RegulatorySubmission Entity

| Setting | Value |
|---------|-------|
| Entity Type | RegulatorySubmission |
| Source | Lakehouse |
| Table | DimRegulatorySubmission |
| Key Column | SubmissionId |

**Property Mappings:**

| Property | Column | Type |
|----------|--------|------|
| SubmissionId | SubmissionId | string |
| ProductId | ProductId | string |
| Agency | Agency | string |
| SubmissionType | SubmissionType | string |
| SubmissionStatus | SubmissionStatus | string |
| SubmissionDate | SubmissionDate | datetime |
| ApprovalDate | ApprovalDate | datetime |

---

### 4.8 CustomerComplaint Entity

| Setting | Value |
|---------|-------|
| Entity Type | CustomerComplaint |
| Source | Lakehouse |
| Table | FactCustomerComplaint |
| Key Column | ComplaintId |

**Property Mappings:**

| Property | Column | Type |
|----------|--------|------|
| ComplaintId | ComplaintId | string |
| ProductId | ProductId | string |
| BatchId | BatchId | string |
| ComplaintDate | ComplaintDate | datetime |
| ComplaintType | ComplaintType | string |
| Region | Region | string |
| IsReportable | IsReportable | boolean |
| ComplaintStatus | ComplaintStatus | string |

---

## Step 5: Bind Relationships

### 5.1 produces (Facility → ProductionBatch)

| Setting | Value |
|---------|-------|
| Relationship | produces |
| Source Table | DimProductionBatch |
| Source Entity Key Column | FacilityId |
| Target Entity Key Column | BatchId |

---

### 5.2 manufactures (ProductionBatch → Product)

| Setting | Value |
|---------|-------|
| Relationship | manufactures |
| Source Table | DimProductionBatch |
| Source Entity Key Column | BatchId |
| Target Entity Key Column | ProductId |

---

### 5.3 supplies (Supplier → Component)

| Setting | Value |
|---------|-------|
| Relationship | supplies |
| Source Table | DimComponent |
| Source Entity Key Column | SupplierId |
| Target Entity Key Column | ComponentId |

---

### 5.4 usesComponent (ProductionBatch → Component)

| Setting | Value |
|---------|-------|
| Relationship | usesComponent |
| Source Table | FactBatchComponent |
| Source Entity Key Column | BatchId |
| Target Entity Key Column | ComponentId |

---

### 5.5 hasQualityEvent (ProductionBatch → QualityEvent)

| Setting | Value |
|---------|-------|
| Relationship | hasQualityEvent |
| Source Table | FactQualityEvent |
| Source Entity Key Column | BatchId |
| Target Entity Key Column | EventId |

---

### 5.6 requiresApproval (Product → RegulatorySubmission)

| Setting | Value |
|---------|-------|
| Relationship | requiresApproval |
| Source Table | DimRegulatorySubmission |
| Source Entity Key Column | ProductId |
| Target Entity Key Column | SubmissionId |

---

### 5.7 receivedComplaint (Product → CustomerComplaint)

| Setting | Value |
|---------|-------|
| Relationship | receivedComplaint |
| Source Table | FactCustomerComplaint |
| Source Entity Key Column | ProductId |
| Target Entity Key Column | ComplaintId |

---

### 5.8 tracesToBatch (CustomerComplaint → ProductionBatch)

| Setting | Value |
|---------|-------|
| Relationship | tracesToBatch |
| Source Table | FactCustomerComplaint |
| Source Entity Key Column | ComplaintId |
| Target Entity Key Column | BatchId |

---

### 5.9 sourcedFrom (Facility → Supplier)

| Setting | Value |
|---------|-------|
| Relationship | sourcedFrom |
| Source Table | FactFacilitySupplier |
| Source Entity Key Column | FacilityId |
| Target Entity Key Column | SupplierId |

---

### 5.10 escalatesTo (QualityEvent → RegulatorySubmission)

| Setting | Value |
|---------|-------|
| Relationship | escalatesTo |
| Source Table | FactQualityEvent |
| Source Entity Key Column | EventId |
| Target Entity Key Column | SubmissionId |

---

## Step 6: Refresh Graph

1. After all bindings complete, click **Refresh Graph**
2. Wait for refresh to complete
3. Navigate to **Graph** view to verify relationships

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Table not visible | Ensure CSV loaded as managed table (not file) |
| 403 Forbidden | Check user has Lakehouse read permissions |
| Missing entities in graph | Verify key columns contain matching values |
| Null values for properties | Check column names match exactly (case-sensitive) |

---

## Next Steps

After completing static bindings, proceed to **eventhouse-binding.md** to add timeseries data for:
- ProductionBatch: YieldRate, DefectCount, CycleTimeMin
- Facility: DailyOutput, EquipmentUptime
