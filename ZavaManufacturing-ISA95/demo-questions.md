# Demo Questions — Zava Smart Textile Manufacturing

These questions demonstrate the graph-powered querying capabilities of the
ZavaManufacturing-ISA95 ontology deployed to Microsoft Fabric.

---

## 1. Quality Root-Cause Analysis

> "Which coating segments had quality test failures, and what materials were used?"

**GQL Query:**
```gql
MATCH (t:QualityTest)-[:TESTED_IN]->(s:ProcessSegment)-[:USES_MATERIAL]->(m:Material)
WHERE t.Test_Result = 'Fail' AND s.Segment_Type = 'Coating'
RETURN t.TestId, t.Test_Type, t.Test_Description,
       s.SegmentId, s.Segment_Code,
       m.Material_Name, m.Material_PartNumber
```

**Expected Insight:** Identifies that TST-010 (low conductivity in Field Slim)
and TST-020 (tensile delamination in Systems Elite) trace back to specific
coating segments and the raw materials used.

---

## 2. Supplier Risk & Lead Time

> "Which tier-1 suppliers have the longest lead times, and what materials do
>  they provide?"

**GQL Query:**
```gql
MATCH (m:Material)-[:SUPPLIED_BY]->(sup:Supplier)
WHERE sup.Supplier_Tier = 1
RETURN sup.Supplier_Name, sup.Supplier_Country, sup.Supplier_Rating,
       m.Material_Name, m.Material_LeadTimeDays
ORDER BY m.Material_LeadTimeDays DESC
```

**Expected Insight:** FR4-Global Inc (Taiwan) has 25-day lead time for FR-4
substrate sheets — longest among tier-1 suppliers.

---

## 3. Production Batch Traceability

> "Trace all process segments, quality tests, and materials for batch BTC-007
>  (ZavaCore Systems Elite)."

**GQL Query:**
```gql
MATCH (s:ProcessSegment)-[:PRODUCED_IN]->(b:ProductBatch)
WHERE b.BatchId = 'BTC-007'
OPTIONAL MATCH (t:QualityTest)-[:TESTED_IN]->(s)
OPTIONAL MATCH (s)-[:USES_MATERIAL]->(m:Material)
RETURN b.Batch_Product, b.Batch_MeshSpec,
       s.SegmentId, s.Segment_Type, s.Segment_Status,
       t.TestId, t.Test_Type, t.Test_Result,
       m.Material_Name
```

**Expected Insight:** Full traceability from batch through 4 manufacturing
steps (Coating → Weaving → SensorEmbed → Packaging) with associated quality
tests and material consumption.

---

## 4. Equipment Utilisation & Shipment Analysis

> "Which sites receive the most inbound shipments and what materials arrive?"

**GQL Query:**
```gql
MATCH (sh:Shipment)-[:DELIVERED_TO]->(e:Equipment)
MATCH (sh)-[:SHIPS_MATERIAL]->(m:Material)
WHERE sh.Shipment_Status = 'Delivered'
RETURN e.Equipment_Name, e.Equipment_Location,
       COUNT(DISTINCT sh.ShipmentId) AS DeliveredShipments,
       COLLECT(DISTINCT m.Material_Name) AS MaterialsReceived
```

**Expected Insight:** Zava Redmond Innovation Center receives the most inbound
shipments (raw materials from global suppliers), while Zava Portland Production
receives packaging/components.

---

## 5. Order Fulfilment & Priority Analysis

> "Show all rush/high-priority orders and their batch completion status."

**GQL Query:**
```gql
MATCH (o:ProductionOrder)-[:ORDERED_FOR]->(b:ProductBatch)
WHERE o.Order_Priority IN ['Rush', 'High']
OPTIONAL MATCH (b)<-[:MANUFACTURED_AT]-(b2:ProductBatch)
RETURN o.Order_Number, o.Order_Priority, o.Order_Quantity, o.Order_DueDate,
       b.Batch_Product, b.Batch_Status, b.Batch_CompletionDate
ORDER BY o.Order_DueDate
```

**Expected Insight:** Identifies rush orders WO-2025-3015 (15,000 Field Standard)
and WO-2025-3020 (20,000 Field Standard) still in Planned status, plus
high-priority orders with completion tracking.
