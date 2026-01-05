# BD Medical Manufacturing - Demo Questions (v2)

Five compelling demo questions showcasing Microsoft Fabric Ontology's graph traversal and multi-hop query capabilities for medical device manufacturing traceability.

> **⚠️ Version 2 Updates (January 2026)**
> - All GQL queries validated against [Fabric Graph limitations](https://learn.microsoft.com/en-us/fabric/graph/limitations)
> - Removed unsupported `OPTIONAL MATCH` statements (not yet available in Fabric Graph)
> - Uses only bounded pattern quantifiers (max 8 hops)
> - Queries use supported aggregation functions: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `COLLECT_LIST`
> - Alternative query patterns provided where needed

---

## Question 1: Supplier Traceability for Quality Events

### Business Question
**"Which suppliers provided components used in batches that had critical quality events?"**

### Why This Matters
When a critical quality issue is discovered, regulatory teams need to quickly identify the upstream supply chain to assess scope, notify suppliers, and determine if other batches are at risk.

### Graph Traversal (3-hop)
```
Supplier → supplies → Component ← usesComponent ← ProductionBatch → hasQualityEvent → QualityEvent
```

### GQL Query
```gql
MATCH (s:Supplier)-[:supplies]->(c:Component)<-[:usesComponent]-(b:ProductionBatch)-[:hasQualityEvent]->(qe:QualityEvent)
WHERE qe.Severity = 'Critical'
RETURN s.SupplierName, s.RiskTier, c.ComponentName, b.BatchId, qe.EventType, qe.RootCause
ORDER BY s.RiskTier DESC
LIMIT 100
```

### Expected Results
| SupplierName | RiskTier | ComponentName | BatchId | EventType | RootCause |
|--------------|----------|---------------|---------|-----------|-----------|
| West Pharmaceutical | Critical | Rubber Plunger Stopper | BATCH021 | NCR | Sterility Failure |
| LyondellBasell | High | PVC IV Tubing | BATCH011 | CAPA | Equipment Failure |
| Aptar Pharma | High | Luer Lock Connector | BATCH027 | NCR | Component Failure |

### GQL Compliance Notes
- ✅ Uses standard `MATCH` with directed edges
- ✅ `WHERE` clause for filtering
- ✅ `ORDER BY` and `LIMIT` for result management
- ✅ No unsupported features

### Why Ontology is Better
**Traditional Approach:** Requires 4+ JOIN operations across siloed tables, complex SQL, and manual correlation.

**Ontology Advantage:**
- Single traversal query expresses the business intent directly
- Graph visualization shows the impact path immediately
- Easy to extend: "Show me ALL batches from this supplier" with one click
- Data Agent can answer this in natural language

---

## Question 2: Product Recall Impact Assessment

### Business Question
**"For a reportable customer complaint, trace back to the facility, supplier, and all other batches that may be affected."**

### Why This Matters
When a reportable adverse event (MDR) occurs, BD must rapidly assess the scope: Which facility produced it? Which supplier components were used? Are other batches from the same production run at risk?

### Graph Traversal (4-hop)
```
CustomerComplaint → tracesToBatch → ProductionBatch → usesComponent → Component ← supplies ← Supplier
                                   ↓
                    ProductionBatch ← produces ← Facility
```

### GQL Query
```gql
-- Query 2a: Complaints with Batch and Facility (2-hop)
MATCH (cc:CustomerComplaint)-[:tracesToBatch]->(b:ProductionBatch)<-[:produces]-(f:Facility)
WHERE cc.IsReportable = true
RETURN cc.ComplaintId, cc.ComplaintType, b.BatchId, b.BatchStatus, 
       f.FacilityName, f.Country
ORDER BY cc.ComplaintId
```

```gql
-- Query 2b: Batch Components and Suppliers (separate query to avoid complex joins)
MATCH (b:ProductionBatch)-[:usesComponent]->(c:Component)<-[:supplies]-(s:Supplier)
WHERE b.BatchId IN ['BATCH011', 'BATCH027', 'BATCH021']
RETURN b.BatchId, 
       COLLECT_LIST(DISTINCT c.ComponentName) AS Components,
       COLLECT_LIST(DISTINCT s.SupplierName) AS Suppliers
GROUP BY b.BatchId
```

### Expected Results - Query 2a
| ComplaintId | ComplaintType | BatchId | BatchStatus | FacilityName | Country |
|-------------|---------------|---------|-------------|--------------|---------|
| CC006 | Device Malfunction | BATCH011 | Released | Sumter SC Plant | United States |
| CC007 | Device Malfunction | BATCH027 | Quarantine | Sumter SC Plant | United States |
| CC014 | Device Malfunction | BATCH021 | Released | Franklin Lakes HQ | United States |

### Expected Results - Query 2b
| BatchId | Components | Suppliers |
|---------|------------|-----------|
| BATCH011 | [PVC IV Tubing, Roller Clamp, Luer Lock] | [LyondellBasell, Tekni-Plex, Aptar Pharma] |
| BATCH027 | [PVC IV Tubing, Roller Clamp, Luer Lock] | [LyondellBasell, Tekni-Plex, Aptar Pharma] |
| BATCH021 | [Luer Lock, PVC IV Tubing] | [West Pharmaceutical, LyondellBasell] |

### GQL Compliance Notes
- ✅ Split into two queries to avoid unsupported `OPTIONAL MATCH`
- ✅ Uses `COLLECT_LIST` (supported) instead of `collect`
- ✅ Uses `GROUP BY` for aggregation
- ✅ `IN` clause for filtering
- ⚠️ **Note:** Boolean property `IsReportable` works in queries but may not render in UI preview (known issue)

### Why Ontology is Better
**Traditional Approach:** Would require a data analyst to manually query 5+ tables, build temp tables, and create a report over hours/days.

**Ontology Advantage:**
- Full supply chain visibility in seconds
- Visual graph shows the "blast radius" of the issue
- Enables proactive identification of at-risk batches
- Supports FDA/MDR reporting requirements with traceable evidence

---

## Question 3: Facility Quality Performance with Timeseries

### Business Question
**"Which facilities have batches with open quality events, and what are the severity distributions?"**

### Why This Matters
Correlating facility operational metrics with quality outcomes helps identify systemic issues before they escalate to product recalls.

### Graph Traversal (2-hop)
```
Facility → produces → ProductionBatch → hasQualityEvent → QualityEvent
```

### GQL Query
```gql
MATCH (f:Facility)-[:produces]->(b:ProductionBatch)-[:hasQualityEvent]->(qe:QualityEvent)
WHERE qe.EventStatus <> 'Closed'
LET facilityName = f.FacilityName
LET country = f.Country
LET severity = qe.Severity
RETURN facilityName, country, severity,
       COUNT(DISTINCT qe.EventId) AS EventCount,
       COLLECT_LIST(DISTINCT b.BatchId) AS AffectedBatches
GROUP BY facilityName, country, severity
ORDER BY EventCount DESC
LIMIT 50
```

### Expected Results
| facilityName | country | severity | EventCount | AffectedBatches |
|--------------|---------|----------|------------|-----------------|
| Sumter SC Plant | United States | Critical | 2 | [BATCH011, BATCH027] |
| Franklin Lakes HQ | United States | Critical | 1 | [BATCH021] |
| Sumter SC Plant | United States | Major | 1 | [BATCH027] |

### Timeseries Correlation (View in Ontology Preview)
After identifying Sumter SC Plant (FAC005), view the **EquipmentUptime** timeseries tile:
- 2025-02-20: 94.2% → 2025-02-23: 93.8%
- 2025-04-05: 88.5% → 2025-04-07: 82.8% ⚠️ **Declining trend correlates with quality events**

> **💡 Demo Tip:** Show the timeseries tile in the Entity Instance view to demonstrate how operational metrics correlate with quality events without writing additional queries.

### GQL Compliance Notes
- ✅ Uses `LET` for computed variables (cleaner than inline expressions)
- ✅ `GROUP BY` with multiple columns
- ✅ `COUNT(DISTINCT ...)` for accurate event counting
- ✅ `COLLECT_LIST` for aggregating batch IDs
- ✅ `ORDER BY` and `LIMIT` for manageable results

### Why Ontology is Better
**Traditional Approach:** Requires joining operational data warehouse with quality management system, often in different platforms.

**Ontology Advantage:**
- Single pane of glass for operational + quality data
- Timeseries tiles show trends without writing queries
- Enables predictive quality: "Alert when uptime drops below 90%"
- Connects the "why" (equipment) to the "what" (quality event)

---

## Question 4: Regulatory Submission Status by Product Line

### Business Question
**"Which products in the Vascular Access line have pending regulatory submissions?"**

### Why This Matters
Regulatory Affairs needs to track submission status alongside post-market surveillance data to prioritize responses and identify products requiring immediate attention.

### Graph Traversal (2-hop)
```
Product → requiresApproval → RegulatorySubmission
```

### GQL Query - Pending Submissions
```gql
MATCH (p:Product)-[:requiresApproval]->(r:RegulatorySubmission)
WHERE p.ProductLine = 'Vascular Access' 
  AND r.SubmissionStatus <> 'Approved'
RETURN p.ProductId, p.ProductName, p.RiskClassification,
       r.SubmissionId, r.Agency, r.SubmissionType, r.SubmissionStatus
ORDER BY r.SubmissionStatus, p.ProductName
```

### GQL Query - Products with Complaints (Separate Query)
```gql
-- Run separately to identify products that also have complaints
MATCH (p:Product)-[:receivedComplaint]->(cc:CustomerComplaint)
WHERE p.ProductLine = 'Vascular Access'
RETURN p.ProductId, p.ProductName,
       COUNT(cc) AS ComplaintCount,
       COLLECT_LIST(cc.ComplaintType) AS ComplaintTypes
GROUP BY p.ProductId, p.ProductName
ORDER BY ComplaintCount DESC
```

### Expected Results - Pending Submissions
| ProductId | ProductName | RiskClassification | SubmissionId | Agency | SubmissionType | SubmissionStatus |
|-----------|-------------|-------------------|--------------|--------|----------------|------------------|
| PROD001 | BD Insyte Autoguard | Class II | SUB012 | TGA | Medical Device | Under Review |
| PROD003 | BD Nexiva Catheter | Class II | SUB018 | Health Canada | 510(k) | Pending |

### Expected Results - Products with Complaints
| ProductId | ProductName | ComplaintCount | ComplaintTypes |
|-----------|-------------|----------------|----------------|
| PROD001 | BD Insyte Autoguard | 2 | [Device Malfunction, Use Error] |
| PROD002 | BD Saf-T-Intima | 1 | [Packaging Issue] |

### GQL Compliance Notes
- ⚠️ **OPTIONAL MATCH not supported** - Split into two separate queries
- ✅ First query: Products with pending submissions
- ✅ Second query: Products with complaints
- ✅ Correlate results manually or in Data Agent response
- 💡 **Alternative:** Use the Graph visual explorer to see both relationships for a selected product

### Why Ontology is Better
**Traditional Approach:** Regulatory and quality systems are typically separate; correlation requires manual data extraction.

**Ontology Advantage:**
- Unified view of regulatory + quality data
- Enables risk-based prioritization: "Products with open submissions AND complaints"
- Supports proactive regulatory strategy
- Data Agent can correlate: "PROD001 has complaints while TGA submission is pending"

---

## Question 5: End-to-End Product Genealogy

### Business Question
**"Show me the complete genealogy for product PROD009 (BD Alaris Infusion Set): facilities, batches, components, and suppliers."**

### Why This Matters
For high-risk Class II/III devices, complete traceability from raw materials to post-market is required for FDA compliance and recall management.

### Graph Traversal (4-hop maximum)
```
Product ← manufactures ← ProductionBatch ← produces ← Facility
                       ↓
         ProductionBatch → usesComponent → Component ← supplies ← Supplier
```

### GQL Queries (Split for Compliance)

```gql
-- Query 5a: Product → Batches → Facility
MATCH (p:Product {ProductId: 'PROD009'})<-[:manufactures]-(b:ProductionBatch)<-[:produces]-(f:Facility)
RETURN p.ProductName, p.ProductLine, p.RiskClassification,
       b.BatchId, b.BatchStatus, b.ProductionDate, b.ExpirationDate,
       f.FacilityName, f.Country, f.FacilityType
ORDER BY b.ProductionDate DESC
```

```gql
-- Query 5b: Batch → Components → Suppliers
MATCH (b:ProductionBatch {BatchId: 'BATCH011'})-[:usesComponent]->(c:Component)<-[:supplies]-(s:Supplier)
RETURN b.BatchId,
       c.ComponentName, c.ComponentType, c.CriticalityLevel,
       s.SupplierName, s.RiskTier, s.CertificationStatus
ORDER BY c.CriticalityLevel DESC
```

```gql
-- Query 5c: Batch Quality Events
MATCH (b:ProductionBatch)-[:hasQualityEvent]->(qe:QualityEvent)
WHERE b.BatchId IN ['BATCH011', 'BATCH027']
RETURN b.BatchId, qe.EventId, qe.EventType, qe.Severity, qe.RootCause, qe.EventStatus
ORDER BY qe.Severity DESC
```

```gql
-- Query 5d: Product Complaints
MATCH (p:Product {ProductId: 'PROD009'})-[:receivedComplaint]->(cc:CustomerComplaint)
RETURN p.ProductName, cc.ComplaintId, cc.ComplaintType, cc.IsReportable, cc.Resolution
```

### Expected Results - Query 5a (Product Genealogy)
| ProductName | ProductLine | RiskClassification | BatchId | BatchStatus | FacilityName | Country |
|-------------|-------------|-------------------|---------|-------------|--------------|---------|
| BD Alaris Infusion Set | Infusion Systems | Class II | BATCH011 | Released | Sumter SC Plant | United States |
| BD Alaris Infusion Set | Infusion Systems | Class II | BATCH027 | Quarantine | Sumter SC Plant | United States |

### Expected Results - Query 5b (Bill of Materials for BATCH011)
| BatchId | ComponentName | ComponentType | CriticalityLevel | SupplierName | RiskTier | CertificationStatus |
|---------|---------------|---------------|------------------|--------------|----------|---------------------|
| BATCH011 | PVC IV Tubing | Raw Material | Critical | LyondellBasell | High | ISO 13485 Certified |
| BATCH011 | Roller Clamp | Subassembly | High | Tekni-Plex | Medium | ISO 13485 Certified |
| BATCH011 | Luer Lock Connector | Component | Critical | Aptar Pharma | High | ISO 13485 Certified |

### GQL Compliance Notes
- ⚠️ **OPTIONAL MATCH not supported** - Split into 4 focused queries
- ✅ Each query is under 4 hops (well within 8-hop limit)
- ✅ Use property filtering `{ProductId: 'PROD009'}` for efficient node lookup
- ✅ `IN` clause for batch-level queries
- 💡 **Demo Strategy:** Run queries sequentially, building the complete picture

### Visual Graph Alternative
> **💡 Pro Tip:** For demos, use the **Graph Visual Explorer** in the Ontology Preview:
> 1. Navigate to Product entity → PROD009
> 2. Expand relationships visually (1-hop at a time)
> 3. Graph automatically shows all connected entities
> 4. No query writing needed for exploration!

### Why Ontology is Better
**Traditional Approach:** This query would require joining 8+ tables across ERP, QMS, PLM, and post-market systems—often impossible without a data warehouse project.

**Ontology Advantage:**
- Complete product genealogy through visual exploration OR targeted queries
- Graph visualization shows the full network of relationships
- Enables "what-if" analysis: "If we recall BATCH027, what else is affected?"
- Supports UDI (Unique Device Identification) compliance
- Data Agent can answer: "Tell me everything about the Alaris Infusion Set"

---

## Summary: Ontology Value Proposition for BD

| Capability | Traditional BI | Fabric Ontology |
|------------|----------------|-----------------|
| Multi-hop queries | Complex SQL joins | Single graph traversal |
| Supply chain traceability | Hours of analysis | Seconds |
| Quality correlation | Manual cross-system | Automatic relationships |
| Regulatory compliance | Scattered reports | Unified lineage |
| Natural language queries | Not possible | Data Agent enabled |
| Visual exploration | Limited | Interactive graph |

### Key Demo Takeaways

1. **Faster Root Cause Analysis:** Trace quality events to suppliers in seconds, not hours
2. **Proactive Risk Management:** Correlate timeseries metrics with quality outcomes
3. **Regulatory Readiness:** Complete product genealogy for FDA/MDR compliance
4. **Unified Data View:** Connect ERP, QMS, and operational data without complex ETL
5. **Self-Service Insights:** Business users can explore data visually without SQL expertise

---

## GQL Best Practices for Fabric Ontology

### ✅ Supported Features (Use These)
| Feature | Example |
|---------|---------|
| `MATCH` with patterns | `MATCH (a:Entity)-[:rel]->(b:Entity)` |
| `WHERE` / `FILTER` | `WHERE a.prop = 'value'` |
| `LET` for variables | `LET fullName = a.firstName + ' ' + a.lastName` |
| `ORDER BY` | `ORDER BY a.prop DESC` |
| `LIMIT` / `OFFSET` | `LIMIT 100 OFFSET 50` |
| `GROUP BY` | `RETURN ... GROUP BY col1, col2` |
| Aggregates | `COUNT(*)`, `SUM()`, `AVG()`, `MIN()`, `MAX()` |
| `COLLECT_LIST` | `COLLECT_LIST(DISTINCT a.prop)` |
| `COALESCE` | `COALESCE(a.prop, 'default')` |
| String functions | `CONTAINS`, `STARTS WITH`, `ENDS WITH` |
| Bounded patterns | `-[:rel]->{1,4}` (max 8 hops) |
| `TRAIL` mode | `MATCH TRAIL (a)-[:rel]->{1,3}(b)` |
| `UNION ALL` | Combine result sets |

### ❌ Not Yet Supported (Avoid These)
| Feature | Workaround |
|---------|------------|
| `OPTIONAL MATCH` | Split into separate queries |
| Undirected edges | Use directed edges with both directions if needed |
| Unbounded patterns `*` | Use bounded like `{1,8}` |
| `UNION DISTINCT` | Use `UNION ALL` + post-processing |
| `ACYCLIC`/`SIMPLE` path modes | Use `TRAIL` for cycle-free |
| `CALL` procedures | Not available |
| Multiple labels per node | Design with single labels |

### ⚠️ Known Limitations
| Issue | Impact | Workaround |
|-------|--------|------------|
| Boolean rendering in UI | Booleans don't display in preview | Works in queries - just UI display issue |
| Query timeout | 20 minutes max | Add `LIMIT`, use more specific filters |
| Result size | 64 MB truncation | Paginate with `OFFSET`/`LIMIT` |
| Materialized views | Can't bind as data source | Use regular KQL tables |

---

## Appendix: Data Agent Instructions (v2)

When creating a Data Agent for this ontology, use these comprehensive instructions that account for Fabric Graph capabilities:

```
You are the BD Medical Manufacturing Ontology Assistant, an expert in medical device manufacturing traceability, quality management, and regulatory compliance. You help users explore and analyze data across BD's manufacturing operations using the Microsoft Fabric Ontology graph.

## IMPORTANT: GQL CAPABILITIES

### You CAN use these GQL features:
- MATCH statements with directed edge patterns
- WHERE/FILTER for conditions
- LET for computed variables
- ORDER BY, LIMIT, OFFSET for result control
- GROUP BY with aggregation functions
- COUNT, SUM, AVG, MIN, MAX aggregates
- COLLECT_LIST for collecting values into arrays
- COALESCE for null handling
- String functions: CONTAINS, STARTS WITH, ENDS WITH
- Bounded variable-length patterns like {1,4} (max 8 hops)
- TRAIL for cycle-free traversal
- UNION ALL for combining results

### You CANNOT use these (not yet supported):
- OPTIONAL MATCH - split into separate queries instead
- Undirected edge patterns - use directed edges
- Unbounded patterns like * - use bounded {1,8}
- UNION DISTINCT - use UNION ALL
- CALL procedure statements

### When queries require optional data:
Instead of OPTIONAL MATCH, run multiple focused queries and combine results in your response.

## DOMAIN EXPERTISE

### Company Context
- Becton, Dickinson and Company (BD) is a global medical technology company
- Three business segments: BD Medical, BD Life Sciences, BD Interventional
- Products include syringes, IV catheters, infusion sets, blood collection devices, and diagnostic instruments
- Heavily regulated industry: FDA (21 CFR Part 820), ISO 13485, EU MDR

### Key Terminology
- **Batch/Lot**: A specific production run with unique traceability (e.g., BATCH021)
- **NCR (Non-Conformance Report)**: Documentation of a quality deviation
- **CAPA (Corrective and Preventive Action)**: Formal process to address quality issues
- **MDR (Medical Device Report)**: Reportable adverse event to FDA
- **UDI (Unique Device Identification)**: FDA-mandated device tracking system
- **DHR (Device History Record)**: Complete manufacturing record for a batch

## ENTITY KNOWLEDGE

### Core Entities (8)
1. **Product**: Medical devices with ProductId (string key), ProductName, ProductLine, RiskClassification
2. **ProductionBatch**: Manufacturing lots with BatchId (string key), BatchStatus, ExpirationDate, YieldRate (timeseries)
3. **Facility**: Manufacturing plants with FacilityId (string key), FacilityName, Country, DailyOutput (timeseries)
4. **Supplier**: Component vendors with SupplierId (string key), SupplierName, RiskTier, CertificationStatus
5. **Component**: Parts/materials with ComponentId (string key), ComponentName, ComponentType, UnitCost
6. **QualityEvent**: NCRs, CAPAs, deviations with EventId (string key), EventType, Severity, RootCause
7. **RegulatorySubmission**: FDA/CE filings with SubmissionId (string key), Agency, SubmissionType, SubmissionStatus
8. **CustomerComplaint**: Post-market issues with ComplaintId (string key), ComplaintType, IsReportable, Resolution

> **Note:** All entity keys are STRING type (not integer, datetime, or other types).

### Key Relationships (10) - All Directed
- Facility -[:produces]-> ProductionBatch
- ProductionBatch -[:manufactures]-> Product
- Supplier -[:supplies]-> Component
- ProductionBatch -[:usesComponent]-> Component
- ProductionBatch -[:hasQualityEvent]-> QualityEvent
- Product -[:requiresApproval]-> RegulatorySubmission
- Product -[:receivedComplaint]-> CustomerComplaint
- CustomerComplaint -[:tracesToBatch]-> ProductionBatch
- Facility -[:sourcedFrom]-> Supplier
- QualityEvent -[:escalatesTo]-> RegulatorySubmission

## QUERY PATTERNS

### Multi-Hop Traversal (Max 8 hops supported)
When users ask about relationships spanning multiple entities:

**2-hop example:** "Which facilities produce batches with quality events?"
```gql
MATCH (f:Facility)-[:produces]->(b:ProductionBatch)-[:hasQualityEvent]->(qe:QualityEvent)
WHERE qe.Severity = 'Critical'
RETURN f.FacilityName, b.BatchId, qe.EventType
```

**3-hop example:** "Which suppliers are linked to quality events?"
```gql
MATCH (s:Supplier)-[:supplies]->(c:Component)<-[:usesComponent]-(b:ProductionBatch)-[:hasQualityEvent]->(qe:QualityEvent)
RETURN s.SupplierName, c.ComponentName, b.BatchId, qe.Severity
```

**4-hop with bounded pattern:**
```gql
MATCH (start:Product)-[:rel1|rel2]->{1,4}(end:Entity)
WHERE start.ProductId = 'PROD009'
RETURN DISTINCT end
LIMIT 100
```

### Aggregations with GROUP BY
```gql
MATCH (f:Facility)-[:produces]->(b:ProductionBatch)-[:hasQualityEvent]->(qe:QualityEvent)
LET facilityName = f.FacilityName
RETURN facilityName, 
       COUNT(DISTINCT qe.EventId) AS EventCount,
       COLLECT_LIST(DISTINCT qe.Severity) AS Severities
GROUP BY facilityName
ORDER BY EventCount DESC
```

### Filtering Patterns
Common filter patterns - all use WHERE (not HAVING):
- Severity: `WHERE qe.Severity IN ['Critical', 'Major']`
- Status: `WHERE b.BatchStatus = 'Quarantine'`
- Risk: `WHERE s.RiskTier = 'Critical'`
- Reportable: `WHERE cc.IsReportable = true`
- Date ranges: `WHERE b.ProductionDate >= '2025-01-01'`
- String matching: `WHERE p.ProductName CONTAINS 'Alaris'`

## RESPONSE GUIDELINES

### For Traceability Questions
When users ask "trace", "track", "find the source", or "what's affected":
1. Identify the starting entity and target entities
2. Build a MATCH pattern (keep under 8 hops)
3. Use WHERE for filtering
4. Return relevant properties
5. Highlight any risk indicators (Critical severity, Quarantine status, Reportable complaints)

### For Complex Genealogy Questions
When a single query would require OPTIONAL MATCH:
1. Explain you'll run multiple queries
2. Run each relationship direction separately
3. Combine and summarize the results
4. Use bullet points or tables for clarity

### For Quality Analysis
When users ask about "quality issues", "problems", "failures":
1. Query ProductionBatch → hasQualityEvent → QualityEvent
2. Include Severity, RootCause, EventStatus
3. Link to upstream Supplier/Component via usesComponent
4. Mention timeseries correlation if relevant

### For Regulatory Questions
When users ask about "FDA", "submissions", "compliance", "recalls":
1. Query Product → requiresApproval → RegulatorySubmission
2. Separately query Product → receivedComplaint → CustomerComplaint
3. Correlate products appearing in both result sets
4. Provide complete audit trail context

## TIMESERIES INTEGRATION

### Available Timeseries Properties
- **ProductionBatch**: YieldRate, DefectCount, CycleTimeMin
- **Facility**: DailyOutput, EquipmentUptime

### When to Reference Timeseries
- "Show me trends" → suggest viewing timeseries tiles in Entity Instance view
- "Is performance declining?" → reference timeseries property names
- "Correlate quality with operations" → explain graph + timeseries correlation
- Note: Timeseries is viewed in the Ontology Preview UI, not queried via GQL directly

### Timeseries Thresholds
- YieldRate < 95%: Potential quality concern
- DefectCount spike: Investigate root cause
- EquipmentUptime < 90%: Maintenance needed
- DailyOutput drop: Capacity constraint

## SAFETY AND COMPLIANCE

- Never fabricate data—only return what exists in the ontology
- For regulatory questions, emphasize the need for official QMS/regulatory system verification
- Highlight reportable events (IsReportable = true) as requiring immediate attention
- When discussing recalls, note that actual recall decisions require human judgment
- If a query might return too much data, always include LIMIT

## CONVERSATION STARTERS

Suggest these to users:
- "Which batches are currently in quarantine and why?"
- "Show me the supplier risk profile for our Vascular Access products"
- "Trace the components in BATCH021 back to their suppliers"
- "Which products have pending regulatory submissions?"
- "What facilities have had quality events this month?"
- "Show me the bill of materials for BATCH011"
```

---

## Demo Execution Tips

### Before the Demo
1. ✅ Verify Graph is refreshed with latest data (manual refresh if needed)
2. ✅ Have the Entity Instance view open for timeseries tiles
3. ✅ Pre-test each query in the GQL editor
4. ✅ Know which queries to use (avoid OPTIONAL MATCH live!)

### During the Demo
1. Start with **visual exploration** (Graph Explorer) for impact
2. Use **prepared queries** from this document
3. Show **timeseries correlation** in Entity Instance view
4. Demonstrate **Data Agent** for natural language queries
5. End with the **"Why Ontology is Better"** comparison

### Handling Questions
- "Can it do X?" → Check GQL capabilities list above
- "What about OPTIONAL MATCH?" → Explain split-query approach
- "How real-time is this?" → Manual refresh; explain scheduled refresh option
- "Scale concerns?" → 500M nodes/edges supported; 20-min query timeout

---

*Document Version: 2.0 | Updated: January 2026 | Validated against Fabric Graph limitations*
