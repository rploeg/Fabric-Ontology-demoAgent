# BD Medical Manufacturing Ontology Demo

A Microsoft Fabric Ontology demo showcasing medical device manufacturing traceability, quality management, and supply chain visibility for Becton Dickinson (BD).

## Overview

This demo models BD's medical device manufacturing operations across three business segments:
- **BD Medical** - Syringes, needles, insulin delivery, infusion therapy
- **BD Life Sciences** - Falcon tubes, specimen collection, diagnostics
- **BD Interventional** - IV catheters, vascular access devices

### Key Capabilities Demonstrated

| Capability | Description |
|------------|-------------|
| **Multi-hop Traceability** | Trace products from raw materials → components → batches → quality events → complaints |
| **Supply Chain Visibility** | Identify suppliers linked to quality issues across facilities |
| **Timeseries Correlation** | Connect operational metrics (yield, uptime) with quality outcomes |
| **Regulatory Compliance** | Complete product genealogy for FDA/MDR reporting |
| **Natural Language Queries** | Data Agent enables business users to explore without SQL |

---

## Ontology Model

### Entity Types (8)

| Entity | Key | Description |
|--------|-----|-------------|
| Product | ProductId | Medical devices (syringes, catheters, tubes) |
| ProductionBatch | BatchId | Manufacturing lots with traceability |
| Facility | FacilityId | Global manufacturing plants |
| Supplier | SupplierId | Raw material and component vendors |
| Component | ComponentId | Parts used in device assembly |
| QualityEvent | EventId | NCRs, CAPAs, deviations, inspections |
| RegulatorySubmission | SubmissionId | FDA 510(k), CE Mark filings |
| CustomerComplaint | ComplaintId | Post-market surveillance |

### Relationships (10)

```
Facility ──produces──► ProductionBatch ──manufactures──► Product
                              │                            │
                              ▼                            ▼
                       usesComponent              requiresApproval
                              │                            │
                              ▼                            ▼
Supplier ──supplies──► Component              RegulatorySubmission
                                                          ▲
ProductionBatch ──hasQualityEvent──► QualityEvent ──escalatesTo──┘
       ▲
       │
       └──tracesToBatch── CustomerComplaint ◄──receivedComplaint── Product

Facility ──sourcedFrom──► Supplier
```

### Timeseries Properties

| Entity | Properties | Source |
|--------|------------|--------|
| ProductionBatch | YieldRate, DefectCount, CycleTimeMin | Eventhouse |
| Facility | DailyOutput, EquipmentUptime | Eventhouse |

---

## Folder Structure

```
MedicalManufacturing/
├── README.md                          # This file
├── ontology/
│   ├── ontology-structure.md          # Entity/relationship documentation
│   └── bd-medical-manufacturing.ttl   # RDF/OWL ontology file
├── data/
│   ├── lakehouse/                     # Static data (10 CSV files)
│   │   ├── DimProduct.csv
│   │   ├── DimFacility.csv
│   │   ├── DimSupplier.csv
│   │   ├── DimComponent.csv
│   │   ├── DimProductionBatch.csv
│   │   ├── DimRegulatorySubmission.csv
│   │   ├── FactQualityEvent.csv
│   │   ├── FactCustomerComplaint.csv
│   │   ├── FactBatchComponent.csv
│   │   └── FactFacilitySupplier.csv
│   └── eventhouse/                    # Timeseries data (2 CSV files)
│       ├── BatchTelemetry.csv
│       └── FacilityTelemetry.csv
├── bindings/
│   ├── lakehouse-binding.md           # Static binding instructions
│   └── eventhouse-binding.md          # Timeseries binding instructions
└── queries/
    └── demo-questions.md              # 5 demo questions with GQL
```

---

## Quick Start

### Prerequisites

- [ ] Microsoft Fabric workspace with **Ontology preview** enabled
- [ ] **Graph preview** tenant setting enabled
- [ ] Lakehouse with **OneLake security DISABLED**
- [ ] Eventhouse (KQL Database)
- [ ] (Optional) XMLA endpoints for semantic model generation
- [ ] (Optional) Data Agent preview for NL queries

### Setup Steps

1. **Create Lakehouse**
   - Upload all CSV files from `data/lakehouse/`
   - Load each as managed Delta table

2. **Create Eventhouse**
   - Ingest `BatchTelemetry.csv` and `FacilityTelemetry.csv`
   - Verify timestamp columns are datetime type

3. **Create Ontology**
   - Import `bd-medical-manufacturing.ttl` OR create entity types manually
   - Follow `bindings/lakehouse-binding.md` for static bindings
   - Follow `bindings/eventhouse-binding.md` for timeseries bindings

4. **Refresh Graph**
   - Click "Refresh Graph" after completing all bindings
   - Verify entities and relationships in Graph view

5. **Run Demo Questions**
   - Use queries from `queries/demo-questions.md`
   - Create Data Agent for natural language exploration

---

## Demo Scenarios

### Scenario 1: Quality Event Root Cause (5 min)

**Story:** A critical sterility failure (QE008) was detected in batch BATCH021. Identify the supplier impact.

1. Open Graph view
2. Search for `BATCH021`
3. Navigate: ProductionBatch → usesComponent → Component → supplies → Supplier
4. Show timeseries: YieldRate dropped from 88.5% to 82.5%
5. **Insight:** West Pharmaceutical (Rubber Plunger Stopper) and LyondellBasell (PVC IV Tubing) supplied this batch

### Scenario 2: Reportable Complaint Traceability (5 min)

**Story:** Customer complaint CC007 is an MDR-reportable device malfunction. Trace the full impact.

1. Search for `CC007` in Graph
2. Navigate: CustomerComplaint → tracesToBatch → ProductionBatch
3. Show batch BATCH027 is in Quarantine status
4. Navigate to Facility (FAC005 - Sumter SC Plant)
5. Show EquipmentUptime timeseries declining
6. **Insight:** FAC005 has equipment issues correlating with quality problems

### Scenario 3: Multi-hop Supplier Risk (5 min)

**Story:** Executive asks "Which of our critical-tier suppliers have been linked to quality events?"

1. Run GQL query from demo-questions.md (Question 1)
2. Show results: West Pharmaceutical, LyondellBasell, Aptar Pharma
3. Visualize in Graph
4. **Insight:** 3 critical/high-risk suppliers linked to open quality events

---

## Sample Data Highlights

### Products (20)
- Covers all 3 BD segments
- Mix of Class I and Class II devices
- Real BD product names (Insyte, Nexiva, Falcon, Alaris, etc.)

### Facilities (15)
- Global coverage: Americas, EMEA, APAC
- Includes Franklin Lakes HQ, Singapore, Ireland, China
- Various facility types and certifications

### Batches with Issues (Demo Focus)
| BatchId | Issue | Status |
|---------|-------|--------|
| BATCH021 | Sterility Failure | Quarantine |
| BATCH027 | Component Failure | Quarantine |
| BATCH011 | Equipment Failure | Released (CAPA open) |

### Quality Events (20)
- Mix of NCR, CAPA, Deviation, Inspection
- Critical/Major events linked to demo batches
- Escalation to regulatory submissions

### Customer Complaints (20)
- 3 reportable (MDR) complaints for demo scenarios
- Traced to specific batches and products

---

## Known Limitations

| Issue | Workaround |
|-------|------------|
| Entity keys must be string or int | All keys use string type |
| Decimal type returns null in Graph | Use double for numeric values |
| Static binding required before timeseries | Follow binding order in instructions |
| Manual Graph refresh required | Refresh after data updates |
| OneLake security blocks binding | Disable for demo Lakehouse |

---

## References

### Microsoft Fabric Ontology Documentation
- [Ontology Overview](https://learn.microsoft.com/en-us/fabric/iq/ontology/overview)
- [Create Entity Types](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-entity-types)
- [Bind Data](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data)
- [Tutorial: Create Ontology](https://learn.microsoft.com/en-us/fabric/iq/ontology/tutorial-1-create-ontology)
- [Troubleshooting](https://learn.microsoft.com/en-us/fabric/iq/ontology/resources-troubleshooting)

### Tools
- [RDF to Fabric Ontology Converter](https://github.com/falloutxAY/rdf-fabric-ontology-converter)
- [Fabric Samples - IQ](https://github.com/microsoft/fabric-samples/tree/main/docs-samples/iq)

---

## About Becton Dickinson

BD (Becton, Dickinson and Company) is one of the largest global medical technology companies, advancing the world of health by improving medical discovery, diagnostics, and care delivery.

- **Founded:** 1897
- **Headquarters:** Franklin Lakes, New Jersey
- **Employees:** ~72,000
- **Revenue:** ~$21.8B (FY2025)
- **Business Segments:** BD Medical, BD Life Sciences, BD Interventional

This demo uses realistic product names and manufacturing scenarios inspired by BD's public information, designed to showcase Fabric Ontology capabilities for medical device traceability and quality management.

---

## Support

For questions about this demo, contact your Microsoft account team or visit the [Fabric Community](https://community.fabric.microsoft.com/).

---

*Generated: January 2026*
