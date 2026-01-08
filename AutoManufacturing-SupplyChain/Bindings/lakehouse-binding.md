# Lakehouse Binding Guide - Automotive Manufacturing & Supply Chain

This guide walks through binding Lakehouse tables to the ontology entities for the NextGen Motors demo.

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

### 1. Vehicle Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | Vehicle |
| Source Table | DimVehicle |
| Key Column | VehicleId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| VehicleId | VehicleId | string |
| Vehicle_VIN | Vehicle_VIN | string |
| Vehicle_Model | Vehicle_Model | string |
| Vehicle_Year | Vehicle_Year | int |
| Vehicle_Status | Vehicle_Status | string |
| Vehicle_CompletionDate | Vehicle_CompletionDate | datetime |

**Steps:**
1. Navigate to Ontology → Data Binding
2. Select entity "Vehicle"
3. Choose Lakehouse as data source
4. Select table "DimVehicle"
5. Map key: VehicleId → VehicleId
6. Map each property as shown above
7. Click "Save Binding"

---

### 2. Assembly Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | Assembly |
| Source Table | DimAssembly |
| Key Column | AssemblyId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| AssemblyId | AssemblyId | string |
| Assembly_Type | Assembly_Type | string |
| Assembly_SerialNum | Assembly_SerialNum | string |
| Assembly_Status | Assembly_Status | string |
| Assembly_StartDate | Assembly_StartDate | datetime |

> ⚠️ **Note**: Timeseries properties (Temperature, Torque, CycleTime) are bound separately via Eventhouse. See eventhouse-binding.md.

---

### 3. Component Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | Component |
| Source Table | DimComponent |
| Key Column | ComponentId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| ComponentId | ComponentId | string |
| Component_Name | Component_Name | string |
| Component_PartNumber | Component_PartNumber | string |
| Component_Category | Component_Category | string |
| Component_UnitCost | Component_UnitCost | double |
| Component_LeadTimeDays | Component_LeadTimeDays | int |

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

### 5. Facility Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | Facility |
| Source Table | DimFacility |
| Key Column | FacilityId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| FacilityId | FacilityId | string |
| Facility_Name | Facility_Name | string |
| Facility_Type | Facility_Type | string |
| Facility_Location | Facility_Location | string |
| Facility_Capacity | Facility_Capacity | int |

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

### 7. QualityEvent Entity

| Configuration | Value |
|---------------|-------|
| Entity Type | QualityEvent |
| Source Table | FactQualityEvent |
| Key Column | EventId |

**Property Mappings:**

| Ontology Property | Table Column | Type |
|-------------------|--------------|------|
| EventId | EventId | string |
| Event_Type | Event_Type | string |
| Event_Severity | Event_Severity | string |
| Event_Description | Event_Description | string |
| Event_Timestamp | Event_Timestamp | datetime |
| Event_Resolution | Event_Resolution | string |

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

### ASSEMBLED_INTO (Assembly → Vehicle)

| Configuration | Value |
|---------------|-------|
| Relationship | ASSEMBLED_INTO |
| Source Entity | Assembly |
| Target Entity | Vehicle |
| Source Table | DimAssembly |
| Source Key Column | AssemblyId |
| Target Key Column | VehicleId |

---

### USES_COMPONENT (Assembly → Component)

| Configuration | Value |
|---------------|-------|
| Relationship | USES_COMPONENT |
| Source Entity | Assembly |
| Target Entity | Component |
| Source Table | EdgeAssemblyComponent |
| Source Key Column | AssemblyId |
| Target Key Column | ComponentId |

---

### SUPPLIED_BY (Component → Supplier)

| Configuration | Value |
|---------------|-------|
| Relationship | SUPPLIED_BY |
| Source Entity | Component |
| Target Entity | Supplier |
| Source Table | DimComponent |
| Source Key Column | ComponentId |
| Target Key Column | SupplierId |

---

### PRODUCED_AT (Vehicle → Facility)

| Configuration | Value |
|---------------|-------|
| Relationship | PRODUCED_AT |
| Source Entity | Vehicle |
| Target Entity | Facility |
| Source Table | DimVehicle |
| Source Key Column | VehicleId |
| Target Key Column | FacilityId |

---

### ORDERED_FOR (ProductionOrder → Vehicle)

| Configuration | Value |
|---------------|-------|
| Relationship | ORDERED_FOR |
| Source Entity | ProductionOrder |
| Target Entity | Vehicle |
| Source Table | DimProductionOrder |
| Source Key Column | OrderId |
| Target Key Column | VehicleId |

---

### AFFECTS (QualityEvent → Assembly)

| Configuration | Value |
|---------------|-------|
| Relationship | AFFECTS |
| Source Entity | QualityEvent |
| Target Entity | Assembly |
| Source Table | FactQualityEvent |
| Source Key Column | EventId |
| Target Key Column | AssemblyId |

---

### ORIGINATED_FROM (Shipment → Facility)

| Configuration | Value |
|---------------|-------|
| Relationship | ORIGINATED_FROM |
| Source Entity | Shipment |
| Target Entity | Facility |
| Source Table | FactShipment |
| Source Key Column | ShipmentId |
| Target Key Column | OriginFacilityId |

---

### DELIVERED_TO (Shipment → Facility)

| Configuration | Value |
|---------------|-------|
| Relationship | DELIVERED_TO |
| Source Entity | Shipment |
| Target Entity | Facility |
| Source Table | FactShipment |
| Source Key Column | ShipmentId |
| Target Key Column | DestFacilityId |

---

### CONTAINS (Shipment → Component)

| Configuration | Value |
|---------------|-------|
| Relationship | CONTAINS |
| Source Entity | Shipment |
| Target Entity | Component |
| Source Table | EdgeShipmentComponent |
| Source Key Column | ShipmentId |
| Target Key Column | ComponentId |

---

### OPERATES_FROM (Supplier → Facility)

| Configuration | Value |
|---------------|-------|
| Relationship | OPERATES_FROM |
| Source Entity | Supplier |
| Target Entity | Facility |
| Source Table | DimSupplier |
| Source Key Column | SupplierId |
| Target Key Column | FacilityId |

---

## Troubleshooting

### Common Issues

1. **"Entity key not found"**
   - Verify key column name matches exactly (case-sensitive)
   - Check for trailing spaces in CSV headers

2. **"Foreign key reference not found"**
   - Ensure all FK values exist in parent table
   - Check for typos in ID values

3. **"Binding validation failed"**
   - Confirm OneLake security is disabled
   - Verify table was created from CSV (not just file upload)

4. **"Property type mismatch"**
   - datetime must be ISO 8601 format
   - boolean must be true/false (not 1/0)
   - double must not have decimal type in source

---

## Next Steps

After completing Lakehouse bindings:
1. Proceed to [Eventhouse Binding](eventhouse-binding.md) for timeseries data
2. Test queries in demo-questions.md
3. Run validation: `python -m demo_automation validate ./AutoManufacturing-SupplyChain`
