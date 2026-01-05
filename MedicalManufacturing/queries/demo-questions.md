# BD Medical Manufacturing - Demo Questions

Five compelling demo questions showcasing Microsoft Fabric Ontology's graph traversal and multi-hop query capabilities for medical device manufacturing traceability.

---

## Question 1: Supplier Traceability for Quality Events

### Business Question
**"Which suppliers provided components used in batches that had critical quality events?"**

### Why This Matters
When a critical quality issue is discovered, regulatory teams need to quickly identify the upstream supply chain to assess scope, notify suppliers, and determine if other batches are at risk.

### Graph Traversal
```
Supplier → supplies → Component → usesComponent ← ProductionBatch → hasQualityEvent → QualityEvent
```

### GQL Query
```gql
MATCH (s:Supplier)-[:supplies]->(c:Component)<-[:usesComponent]-(b:ProductionBatch)-[:hasQualityEvent]->(qe:QualityEvent)
WHERE qe.Severity = 'Critical'
RETURN s.SupplierName, s.RiskTier, c.ComponentName, b.BatchId, qe.EventType, qe.RootCause
```

### Expected Results
| SupplierName | RiskTier | ComponentName | BatchId | EventType | RootCause |
|--------------|----------|---------------|---------|-----------|-----------|
| West Pharmaceutical | Critical | Rubber Plunger Stopper | BATCH021 | NCR | Sterility Failure |
| LyondellBasell | High | PVC IV Tubing | BATCH011 | CAPA | Equipment Failure |
| Aptar Pharma | High | Luer Lock Connector | BATCH027 | NCR | Component Failure |

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

### Graph Traversal
```
CustomerComplaint → tracesToBatch → ProductionBatch → usesComponent → Component → supplies ← Supplier
                                   ↓
                    ProductionBatch → produces ← Facility
```

### GQL Query
```gql
MATCH (cc:CustomerComplaint)-[:tracesToBatch]->(b:ProductionBatch)-[:usesComponent]->(c:Component)<-[:supplies]-(s:Supplier),
      (b)<-[:produces]-(f:Facility)
WHERE cc.IsReportable = true
RETURN cc.ComplaintId, cc.ComplaintType, b.BatchId, f.FacilityName, f.Country, 
       collect(DISTINCT s.SupplierName) AS Suppliers, collect(DISTINCT c.ComponentName) AS Components
```

### Expected Results
| ComplaintId | ComplaintType | BatchId | FacilityName | Country | Suppliers | Components |
|-------------|---------------|---------|--------------|---------|-----------|------------|
| CC006 | Device Malfunction | BATCH011 | Sumter SC Plant | United States | [LyondellBasell, Tekni-Plex] | [PVC IV Tubing, Roller Clamp, Luer Lock] |
| CC007 | Device Malfunction | BATCH027 | Sumter SC Plant | United States | [LyondellBasell, Tekni-Plex, Aptar Pharma] | [PVC IV Tubing, Roller Clamp, Luer Lock] |
| CC014 | Device Malfunction | BATCH021 | Franklin Lakes HQ | United States | [West Pharmaceutical, LyondellBasell] | [Luer Lock, PVC IV Tubing] |

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
**"Which facilities have declining equipment uptime AND batches with quality events in the same period?"**

### Why This Matters
Correlating facility operational metrics with quality outcomes helps identify systemic issues before they escalate to product recalls.

### Graph Traversal
```
Facility (timeseries: EquipmentUptime) → produces → ProductionBatch → hasQualityEvent → QualityEvent
```

### GQL Query
```gql
MATCH (f:Facility)-[:produces]->(b:ProductionBatch)-[:hasQualityEvent]->(qe:QualityEvent)
WHERE qe.Severity IN ['Critical', 'Major'] AND qe.EventStatus <> 'Closed'
RETURN f.FacilityId, f.FacilityName, f.Country, 
       count(DISTINCT qe.EventId) AS OpenQualityEvents,
       collect(DISTINCT b.BatchId) AS AffectedBatches
ORDER BY OpenQualityEvents DESC
```

### Expected Results
| FacilityId | FacilityName | Country | OpenQualityEvents | AffectedBatches |
|------------|--------------|---------|-------------------|-----------------|
| FAC005 | Sumter SC Plant | United States | 3 | [BATCH011, BATCH027] |
| FAC001 | Franklin Lakes HQ | United States | 2 | [BATCH021] |

### Timeseries Correlation
After identifying FAC005, view the **EquipmentUptime** timeseries:
- 2025-02-20: 94.2% → 2025-02-23: 93.8%
- 2025-04-05: 88.5% → 2025-04-07: 82.8% ⚠️

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
**"Which products in the Vascular Access line have pending regulatory submissions, and do any have associated customer complaints?"**

### Why This Matters
Regulatory Affairs needs to track submission status alongside post-market surveillance data to prioritize responses and identify products requiring immediate attention.

### Graph Traversal
```
Product → requiresApproval → RegulatorySubmission
Product → receivedComplaint → CustomerComplaint
```

### GQL Query
```gql
MATCH (p:Product)-[:requiresApproval]->(r:RegulatorySubmission)
WHERE p.ProductLine = 'Vascular Access' AND r.SubmissionStatus <> 'Approved'
OPTIONAL MATCH (p)-[:receivedComplaint]->(cc:CustomerComplaint)
RETURN p.ProductId, p.ProductName, r.Agency, r.SubmissionType, r.SubmissionStatus,
       count(cc) AS ComplaintCount,
       collect(cc.ComplaintType) AS ComplaintTypes
```

### Expected Results
| ProductId | ProductName | Agency | SubmissionType | SubmissionStatus | ComplaintCount | ComplaintTypes |
|-----------|-------------|--------|----------------|------------------|----------------|----------------|
| PROD001 | BD Insyte Autoguard | TGA | Medical Device | Under Review | 2 | [Device Malfunction, Use Error] |

### Why Ontology is Better
**Traditional Approach:** Regulatory and quality systems are typically separate; correlation requires manual data extraction.

**Ontology Advantage:**
- Unified view of regulatory + quality data
- Enables risk-based prioritization: "Products with open submissions AND complaints"
- Supports proactive regulatory strategy
- Data Agent can alert: "PROD001 has complaints while TGA submission is pending"

---

## Question 5: End-to-End Product Genealogy

### Business Question
**"Show me the complete genealogy for product PROD009 (BD Alaris Infusion Set): facilities, batches, components, suppliers, quality events, and complaints."**

### Why This Matters
For high-risk Class II/III devices, complete traceability from raw materials to post-market is required for FDA compliance and recall management.

### Graph Traversal (4-hop)
```
Product ← manufactures ← ProductionBatch → produces ← Facility
                       ↓
         ProductionBatch → usesComponent → Component → supplies ← Supplier
                       ↓
         ProductionBatch → hasQualityEvent → QualityEvent
                       ↓
         Product → receivedComplaint → CustomerComplaint → tracesToBatch → ProductionBatch
```

### GQL Query
```gql
MATCH (p:Product {ProductId: 'PROD009'})<-[:manufactures]-(b:ProductionBatch)<-[:produces]-(f:Facility)
OPTIONAL MATCH (b)-[:usesComponent]->(c:Component)<-[:supplies]-(s:Supplier)
OPTIONAL MATCH (b)-[:hasQualityEvent]->(qe:QualityEvent)
OPTIONAL MATCH (p)-[:receivedComplaint]->(cc:CustomerComplaint)
RETURN p.ProductName, f.FacilityName, b.BatchId, b.BatchStatus,
       collect(DISTINCT {component: c.ComponentName, supplier: s.SupplierName}) AS BillOfMaterials,
       collect(DISTINCT {event: qe.EventId, type: qe.EventType, severity: qe.Severity}) AS QualityEvents,
       collect(DISTINCT {complaint: cc.ComplaintId, type: cc.ComplaintType, reportable: cc.IsReportable}) AS Complaints
```

### Expected Results
| ProductName | FacilityName | BatchId | BatchStatus | BillOfMaterials | QualityEvents | Complaints |
|-------------|--------------|---------|-------------|-----------------|---------------|------------|
| BD Alaris Infusion Set | Sumter SC Plant | BATCH011 | Released | [{PVC IV Tubing, LyondellBasell}, {Roller Clamp, Tekni-Plex}, {Luer Lock, Aptar Pharma}] | [{QE004, CAPA, Critical}] | [{CC006, Device Malfunction, true}] |
| BD Alaris Infusion Set | Sumter SC Plant | BATCH027 | Quarantine | [{PVC IV Tubing, LyondellBasell}, {Roller Clamp, Tekni-Plex}, {Luer Lock, Aptar Pharma}] | [{QE011, NCR, Critical}, {QE012, CAPA, Major}] | [{CC007, Device Malfunction, true}] |

### Why Ontology is Better
**Traditional Approach:** This query would require joining 8+ tables across ERP, QMS, PLM, and post-market systems—often impossible without a data warehouse project.

**Ontology Advantage:**
- Complete product genealogy in one query
- Visual graph shows the full network of relationships
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
5. **Self-Service Insights:** Business users can explore data without SQL expertise

---

## Appendix: Data Agent Instructions

When creating a Data Agent for this ontology, use these comprehensive instructions:

```
You are the BD Medical Manufacturing Ontology Assistant, an expert in medical device manufacturing traceability, quality management, and regulatory compliance. You help users explore and analyze data across BD's manufacturing operations using the Microsoft Fabric Ontology graph.

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
1. **Product**: Medical devices with ProductId, ProductName, ProductLine, RiskClassification
2. **ProductionBatch**: Manufacturing lots with BatchId, BatchStatus, ExpirationDate, YieldRate (timeseries)
3. **Facility**: Manufacturing plants with FacilityId, FacilityName, Country, DailyOutput (timeseries)
4. **Supplier**: Component vendors with SupplierId, SupplierName, RiskTier, CertificationStatus
5. **Component**: Parts/materials with ComponentId, ComponentName, ComponentType, UnitCost
6. **QualityEvent**: NCRs, CAPAs, deviations with EventId, EventType, Severity, RootCause
7. **RegulatorySubmission**: FDA/CE filings with SubmissionId, Agency, SubmissionType, SubmissionStatus
8. **CustomerComplaint**: Post-market issues with ComplaintId, ComplaintType, IsReportable, Resolution

### Key Relationships (10)
- Product → produces ← Facility (which facilities make which products)
- ProductionBatch → manufactures → Product (which batches make which products)
- Supplier → supplies → Component (supply chain)
- ProductionBatch → usesComponent → Component (bill of materials)
- ProductionBatch → hasQualityEvent → QualityEvent (quality linkage)
- Product → requiresApproval → RegulatorySubmission (regulatory linkage)
- Product → receivedComplaint → CustomerComplaint (post-market linkage)
- CustomerComplaint → tracesToBatch → ProductionBatch (complaint traceability)
- Facility → sourcedFrom → Supplier (facility-supplier relationship)
- QualityEvent → escalatesTo → RegulatorySubmission (escalation path)

## QUERY PATTERNS

### Multi-Hop Traversal
When users ask about relationships spanning multiple entities, use MATCH patterns:
- 2-hop: "Which suppliers provide components for Product X?" → Supplier → supplies → Component ← usesComponent ← ProductionBatch → manufactures → Product
- 3-hop: "Which suppliers are linked to quality events?" → Supplier → supplies → Component ← usesComponent ← ProductionBatch → hasQualityEvent → QualityEvent
- 4-hop: "Complete genealogy for a product" → traverse all connected entities

### Aggregations
Support GROUP BY for summaries:
- Count quality events by facility
- Sum complaints by product line
- Average yield rate by supplier tier

### Filtering
Common filter patterns:
- Severity: WHERE qe.Severity IN ['Critical', 'Major']
- Status: WHERE b.BatchStatus = 'Quarantine'
- Risk: WHERE s.RiskTier = 'Critical'
- Reportable: WHERE cc.IsReportable = true
- Date ranges: WHERE b.ProductionDate >= '2025-01-01'

## RESPONSE GUIDELINES

### For Traceability Questions
When users ask "trace", "track", "find the source", or "what's affected":
1. Identify the starting entity
2. Determine the traversal path through relationships
3. Return the connected entities with key attributes
4. Highlight any risk indicators (Critical severity, Quarantine status, Reportable complaints)

### For Quality Analysis
When users ask about "quality issues", "problems", "failures":
1. Query QualityEvent entities
2. Include Severity, RootCause, EventStatus
3. Link to affected ProductionBatch and upstream Supplier/Component
4. Mention any correlated timeseries trends (YieldRate drops, DefectCount spikes)

### For Regulatory Questions
When users ask about "FDA", "submissions", "compliance", "recalls":
1. Query RegulatorySubmission for status
2. Cross-reference with CustomerComplaint (IsReportable = true)
3. Provide complete audit trail back to ProductionBatch and Facility

### For Supplier Risk
When users ask about "supplier risk", "vendor assessment", "supply chain":
1. Query Supplier.RiskTier and CertificationStatus
2. Link to Components they supply
3. Identify any quality events in batches using those components
4. Flag Critical tier suppliers with recent quality issues

## TIMESERIES INTEGRATION

### Available Timeseries Properties
- **ProductionBatch**: YieldRate, DefectCount, CycleTimeMin (batch-level metrics over time)
- **Facility**: DailyOutput, EquipmentUptime (facility operational metrics)

### When to Reference Timeseries
- "Show me trends" → reference timeseries data
- "Is performance declining?" → analyze timeseries patterns
- "Correlate quality with operations" → combine graph + timeseries
- "Predictive" or "early warning" → use timeseries thresholds

### Timeseries Insights
- YieldRate < 95%: Potential quality concern
- DefectCount spike: Investigate root cause
- EquipmentUptime < 90%: Maintenance needed
- DailyOutput drop: Capacity constraint

## EXAMPLE RESPONSES

### User: "Which suppliers are linked to critical quality events?"
Response Pattern:
1. Execute: MATCH (s:Supplier)-[:supplies]->(c:Component)<-[:usesComponent]-(b:ProductionBatch)-[:hasQualityEvent]->(qe:QualityEvent) WHERE qe.Severity = 'Critical'
2. Return: Supplier name, risk tier, affected component, batch, event details
3. Insight: "3 suppliers are linked to critical events. West Pharmaceutical (Critical tier) supplied the Rubber Plunger Stopper used in BATCH021 which had a sterility failure."

### User: "Tell me everything about the Alaris Infusion Set"
Response Pattern:
1. Start with Product entity (PROD009)
2. Traverse ALL relationships: facilities, batches, components, suppliers, quality events, complaints, regulatory submissions
3. Present as a comprehensive genealogy
4. Highlight any risks: "BATCH027 is in Quarantine with 2 open quality events and 1 reportable complaint"

### User: "Are there any facilities with declining performance?"
Response Pattern:
1. Reference Facility timeseries (EquipmentUptime, DailyOutput)
2. Correlate with QualityEvent data for those facilities
3. Insight: "FAC005 (Sumter SC Plant) shows EquipmentUptime declining from 94.2% to 82.8% over the past month. This facility also has 3 open quality events—recommend maintenance review."

## SAFETY AND COMPLIANCE

- Never fabricate data—only return what exists in the ontology
- For regulatory questions, emphasize the need for official QMS/regulatory system verification
- Highlight reportable events (IsReportable = true) as requiring immediate attention
- When discussing recalls, note that actual recall decisions require human judgment

## CONVERSATION STARTERS

Suggest these to users:
- "Which batches are currently in quarantine and why?"
- "Show me the supplier risk profile for our Vascular Access products"
- "Trace the components in BATCH021 back to their suppliers"
- "Which products have pending regulatory submissions with associated complaints?"
- "What's the quality trend for our Franklin Lakes facility this month?"
```
