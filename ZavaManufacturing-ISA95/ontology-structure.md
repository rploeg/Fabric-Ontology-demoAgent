# Ontology Structure — Zava Smart Textile Manufacturing

## Namespace
`http://example.com/zava-manufacturing-isa95#`

## Entity Classes (8)

### 1. ProductBatch
ISA-95 Material Lot. A production batch of finished smart mesh units.
- **Key**: `BatchId` (string)
- **Properties**: Batch_Product, Batch_MeshSpec, Batch_Quantity, Batch_Status, Batch_CompletionDate, Batch_EquipmentId

### 2. ProcessSegment
ISA-95 Process Segment. Discrete manufacturing steps: Coating, Weaving, SensorEmbed, Packaging.
- **Key**: `SegmentId` (string)
- **Properties**: Segment_Type, Segment_Code, Segment_Status, Segment_StartDate, Segment_BatchId
- **Timeseries**: Temperature, MoistureContent, CycleTime

### 3. Material
ISA-95 Material Definition. Raw materials, components, and packaging materials.
- **Key**: `MaterialId` (string)
- **Properties**: Material_Name, Material_PartNumber, Material_Class, Material_UnitCost, Material_LeadTimeDays, Material_SupplierId

### 4. Supplier
External material provider.
- **Key**: `SupplierId` (string)
- **Properties**: Supplier_Name, Supplier_Tier, Supplier_Country, Supplier_Rating, Supplier_Certified, Supplier_EquipmentId

### 5. Equipment
ISA-95 Equipment hierarchy (Site → Area → WorkCenter → WorkUnit).
- **Key**: `EquipmentId` (string)
- **Properties**: Equipment_Name, Equipment_Level, Equipment_Type, Equipment_Location, Equipment_Capacity
- **Timeseries (site-level)**: EnergyConsumption, Humidity, ProductionRate
- **Timeseries (machine-level)**: MachineState, ErrorCode, DurationSec, UnitCount, UnitCountDelta, FiberProducedGram, UnitsRejected, OEE, VOT, LoadingTime

### 6. ProductionOrder
ISA-95 Production Schedule. Work orders for production runs.
- **Key**: `OrderId` (string)
- **Properties**: Order_Number, Order_Quantity, Order_Priority, Order_DueDate, Order_Status, Order_BatchId

### 7. QualityTest
ISA-95 Quality Test Operations.
- **Key**: `TestId` (string)
- **Properties**: Test_Type, Test_Result, Test_Description, Test_Timestamp, Test_Resolution, Test_SegmentId

### 8. Shipment
Logistics movement — inbound raw materials and outbound finished goods.
- **Key**: `ShipmentId` (string)
- **Properties**: Shipment_TrackingNum, Shipment_Status, Shipment_DepartureDate, Shipment_ArrivalDate, Shipment_Carrier

## Relationships (10)

| # | Name | Source → Target | Cardinality | Binding Table |
|---|------|----------------|-------------|---------------|
| 1 | PRODUCED_IN | ProcessSegment → ProductBatch | M:1 | DimProcessSegment |
| 2 | USES_MATERIAL | ProcessSegment → Material | M:N | EdgeSegmentMaterial |
| 3 | SUPPLIED_BY | Material → Supplier | M:1 | DimMaterial |
| 4 | MANUFACTURED_AT | ProductBatch → Equipment | M:1 | DimProductBatch |
| 5 | ORDERED_FOR | ProductionOrder → ProductBatch | 1:1 | DimProductionOrder |
| 6 | TESTED_IN | QualityTest → ProcessSegment | M:1 | FactQualityTest |
| 7 | ORIGINATED_FROM | Shipment → Equipment | M:1 | EdgeShipmentOrigin |
| 8 | DELIVERED_TO | Shipment → Equipment | M:1 | EdgeShipmentDestination |
| 9 | SHIPS_MATERIAL | Shipment → Material | M:N | EdgeShipmentMaterial |
| 10 | OPERATES_FROM | Supplier → Equipment | M:1 | DimSupplier |

## Property Count

| Category | Count |
|----------|-------|
| Key properties | 8 |
| Scalar datatype properties | 44 |
| Timeseries datatype properties | 17 |
| **Total datatype properties** | **69** |
| Object properties (relationships) | 10 |

## Process Flow

```
Coating (COT) → Weaving (WEV) → SensorEmbed (SEN) → Packaging (PKG)
   ↓                ↓                 ↓                  ↓
 Apply           Weave fiber      Embed sensor       Cut, package,
 conductive      into mesh        modules via        label, ship
 coating to      pattern          pick-and-place     in ESD bags
 raw fibers
```
