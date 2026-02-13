# Lakehouse Binding Guide - Tea Bag Manufacturing (ISA-95)

This guide walks through binding Lakehouse tables to the ontology entities for the Golden Leaf Tea Co. demo.

---

## Prerequisites

Before starting, ensure:

1. ✅ **OneLake Security is DISABLED** on your Lakehouse
   - Go to Lakehouse settings → OneLake → Disable security
2. ✅ **Lakehouse schemas are DISABLED**
3. ✅ CSV files are uploaded to `Files/` folder in Lakehouse
4. ✅ Tables are created from CSV files
5. ✅ Ontology TTL file is uploaded to Graph

---

## Entity Bindings

### 1. ProductBatch Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | ProductBatch |
| Source Table | DimProductBatch |
| Key Column | BatchId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| BatchId | BatchId | string |
| Batch_Product | Batch_Product | string |
| Batch_BlendCode | Batch_BlendCode | string |
| Batch_Quantity | Batch_Quantity | int |
| Batch_Status | Batch_Status | string |
| Batch_CompletionDate | Batch_CompletionDate | datetime |

**Steps:**
1. Navigate to Ontology → Data Binding
2. Select entity "ProductBatch"
3. Choose Lakehouse as data source
4. Select table "DimProductBatch"
5. Map key: BatchId → BatchId
6. Map each property as shown above
7. Click "Save Binding"

---

### 2. ProcessSegment Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | ProcessSegment |
| Source Table | DimProcessSegment |
| Key Column | SegmentId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| SegmentId | SegmentId | string |
| Segment_Type | Segment_Type | string |
| Segment_Code | Segment_Code | string |
| Segment_Status | Segment_Status | string |
| Segment_StartDate | Segment_StartDate | datetime |

> ⚠️ **Note**: Timeseries properties (Temperature, MoistureContent, CycleTime) are bound separately via Eventhouse. See eventhouse-binding.md.

---

### 3. Material Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | Material |
| Source Table | DimMaterial |
| Key Column | MaterialId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| MaterialId | MaterialId | string |
| Material_Name | Material_Name | string |
| Material_PartNumber | Material_PartNumber | string |
| Material_Class | Material_Class | string |
| Material_UnitCost | Material_UnitCost | double |
| Material_LeadTimeDays | Material_LeadTimeDays | int |

---

### 4. Supplier Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | Supplier |
| Source Table | DimSupplier |
| Key Column | SupplierId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| SupplierId | SupplierId | string |
| Supplier_Name | Supplier_Name | string |
| Supplier_Tier | Supplier_Tier | int |
| Supplier_Country | Supplier_Country | string |
| Supplier_Rating | Supplier_Rating | double |
| Supplier_Certified | Supplier_Certified | boolean |

---

### 5. Equipment Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | Equipment |
| Source Table | DimEquipment |
| Key Column | EquipmentId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| EquipmentId | EquipmentId | string |
| Equipment_Name | Equipment_Name | string |
| Equipment_Level | Equipment_Level | string |
| Equipment_Type | Equipment_Type | string |
| Equipment_Location | Equipment_Location | string |
| Equipment_Capacity | Equipment_Capacity | int |

> ⚠️ **Note**: Timeseries properties (EnergyConsumption, Humidity, ProductionRate) are bound separately via Eventhouse. See eventhouse-binding.md.

---

### 6. ProductionOrder Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | ProductionOrder |
| Source Table | DimProductionOrder |
| Key Column | OrderId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| OrderId | OrderId | string |
| Order_Number | Order_Number | string |
| Order_Quantity | Order_Quantity | int |
| Order_Priority | Order_Priority | string |
| Order_DueDate | Order_DueDate | datetime |
| Order_Status | Order_Status | string |

---

### 7. QualityTest Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | QualityTest |
| Source Table | FactQualityTest |
| Key Column | TestId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| TestId | TestId | string |
| Test_Type | Test_Type | string |
| Test_Result | Test_Result | string |
| Test_Description | Test_Description | string |
| Test_Timestamp | Test_Timestamp | datetime |
| Test_Resolution | Test_Resolution | string |

---

### 8. Shipment Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | Shipment |
| Source Table | FactShipment |
| Key Column | ShipmentId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| ShipmentId | ShipmentId | string |
| Shipment_TrackingNum | Shipment_TrackingNum | string |
| Shipment_Status | Shipment_Status | string |
| Shipment_DepartureDate | Shipment_DepartureDate | datetime |
| Shipment_ArrivalDate | Shipment_ArrivalDate | datetime |
| Shipment_Carrier | Shipment_Carrier | string |

---

## Relationship Bindings

### 1. PRODUCED_IN (ProcessSegment → ProductBatch)

| Configuration | Value |
|---------------|-------|
| Relationship | PRODUCED_IN |
| Source Entity | ProcessSegment |
| Target Entity | ProductBatch |
| Source Table | DimProcessSegment |
| Source Key Column | SegmentId |
| Target Key Column | BatchId |

**Steps:**
1. Navigate to Ontology → Relationships
2. Select "PRODUCED_IN"
3. Source: DimProcessSegment, key: SegmentId
4. Target key: BatchId (column in DimProcessSegment)
5. Save

---

### 2. USES_MATERIAL (ProcessSegment → Material) — Many-to-Many

| Configuration | Value |
|---------------|-------|
| Relationship | USES_MATERIAL |
| Source Entity | ProcessSegment |
| Target Entity | Material |
| Source Table | EdgeSegmentMaterial |
| Source Key Column | SegmentId |
| Target Key Column | MaterialId |

> ⚠️ This is a **many-to-many** relationship using a dedicated edge table.

---

### 3. SUPPLIED_BY (Material → Supplier)

| Configuration | Value |
|---------------|-------|
| Relationship | SUPPLIED_BY |
| Source Entity | Material |
| Target Entity | Supplier |
| Source Table | DimMaterial |
| Source Key Column | MaterialId |
| Target Key Column | SupplierId |

---

### 4. MANUFACTURED_AT (ProductBatch → Equipment)

| Configuration | Value |
|---------------|-------|
| Relationship | MANUFACTURED_AT |
| Source Entity | ProductBatch |
| Target Entity | Equipment |
| Source Table | DimProductBatch |
| Source Key Column | BatchId |
| Target Key Column | EquipmentId |

---

### 5. ORDERED_FOR (ProductionOrder → ProductBatch)

| Configuration | Value |
|---------------|-------|
| Relationship | ORDERED_FOR |
| Source Entity | ProductionOrder |
| Target Entity | ProductBatch |
| Source Table | DimProductionOrder |
| Source Key Column | OrderId |
| Target Key Column | BatchId |

---

### 6. TESTED_IN (QualityTest → ProcessSegment)

| Configuration | Value |
|---------------|-------|
| Relationship | TESTED_IN |
| Source Entity | QualityTest |
| Target Entity | ProcessSegment |
| Source Table | FactQualityTest |
| Source Key Column | TestId |
| Target Key Column | SegmentId |

---

### 7. ORIGINATED_FROM (Shipment → Equipment) — Edge Table

| Configuration | Value |
|---------------|-------|
| Relationship | ORIGINATED_FROM |
| Source Entity | Shipment |
| Target Entity | Equipment |
| Source Table | EdgeShipmentOrigin |
| Source Key Column | ShipmentId |
| Target Key Column | EquipmentId |

---

### 8. DELIVERED_TO (Shipment → Equipment) — Edge Table

| Configuration | Value |
|---------------|-------|
| Relationship | DELIVERED_TO |
| Source Entity | Shipment |
| Target Entity | Equipment |
| Source Table | EdgeShipmentDestination |
| Source Key Column | ShipmentId |
| Target Key Column | EquipmentId |

---

### 9. SHIPS_MATERIAL (Shipment → Material) — Many-to-Many

| Configuration | Value |
|---------------|-------|
| Relationship | SHIPS_MATERIAL |
| Source Entity | Shipment |
| Target Entity | Material |
| Source Table | EdgeShipmentMaterial |
| Source Key Column | ShipmentId |
| Target Key Column | MaterialId |

---

### 10. OPERATES_FROM (Supplier → Equipment)

| Configuration | Value |
|---------------|-------|
| Relationship | OPERATES_FROM |
| Source Entity | Supplier |
| Target Entity | Equipment |
| Source Table | DimSupplier |
| Source Key Column | SupplierId |
| Target Key Column | EquipmentId |

---

## Data Loading Summary

| Table | File | Rows | Type |
|-------|------|------|------|
| DimProductBatch | Data/Lakehouse/DimProductBatch.csv | 20 | Dimension |
| DimProcessSegment | Data/Lakehouse/DimProcessSegment.csv | 30 | Dimension |
| DimMaterial | Data/Lakehouse/DimMaterial.csv | 25 | Dimension |
| DimSupplier | Data/Lakehouse/DimSupplier.csv | 10 | Dimension |
| DimEquipment | Data/Lakehouse/DimEquipment.csv | 15 | Dimension |
| DimProductionOrder | Data/Lakehouse/DimProductionOrder.csv | 20 | Dimension |
| FactQualityTest | Data/Lakehouse/FactQualityTest.csv | 30 | Fact |
| FactShipment | Data/Lakehouse/FactShipment.csv | 25 | Fact |
| EdgeSegmentMaterial | Data/Lakehouse/EdgeSegmentMaterial.csv | ~95 | Edge |
| EdgeShipmentMaterial | Data/Lakehouse/EdgeShipmentMaterial.csv | ~57 | Edge |
| EdgeShipmentOrigin | Data/Lakehouse/EdgeShipmentOrigin.csv | 25 | Edge |
| EdgeShipmentDestination | Data/Lakehouse/EdgeShipmentDestination.csv | 25 | Edge |
