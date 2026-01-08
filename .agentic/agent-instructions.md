# Fabric Ontology Demo Generation - Agent Workflow

> **Spec Version**: 3.3  
> **Last Updated**: January 2026  
> **Purpose**: Phase-by-phase workflow for generating error-free Fabric Ontology demos

---

## Pre-Flight Checklist

Before starting, confirm with user:

1. Target company/industry (for realistic data)
2. Primary use case (traceability, quality, risk, compliance, etc.)
3. Number of entities (recommend 6-8 for meaningful demo)
4. Timeseries requirements (which entities need operational metrics?)
5. Target audience (executives, technical, compliance?)

---

## MANDATORY Output Folder Layout

Every demo MUST be generated in this exact structure (case-sensitive paths):

```
{DemoName}/
├── README.md
├── .demo-metadata.yaml
├── demo-questions.md
├── ontology-structure.md
├── Bindings/
│   ├── bindings.yaml
│   ├── lakehouse-binding.md
│   └── eventhouse-binding.md
├── Data/
│   ├── Lakehouse/             # Dimension, fact, and edge CSVs
│   │   ├── Dim*.csv
│   │   ├── Fact*.csv
│   │   └── Edge*.csv (if any)
│   └── Eventhouse/            # Timeseries CSVs
│       └── <Timeseries>.csv
└── Ontology/
    ├── {demo-slug}.ttl
    └── ontology-diagram-slide.html
```

**Path rules**
- Use the `Bindings/` folder for ALL binding artifacts.
- Place Lakehouse CSVs in `Data/Lakehouse/` and Eventhouse CSVs in `Data/Eventhouse/`.
- TTL and slide files live in `Ontology/`.
- All relative paths referenced in docs and YAML must match these locations exactly.

---

## Phase 1: Discovery

**Output**: Brief summary confirming:
- Company/industry context
- 6-8 proposed entity types with descriptions
- Key relationships (aim for 8-12)
- Which entities will have timeseries data
- 2-3 multi-hop traversal scenarios

**Action**: Ask "Does this scope look correct? Ready for Phase 2: Design?"

---

## Phase 2: Design (2 responses)

### Response 1: ontology-structure.md (save to `{DemoName}/ontology-structure.md`)

Generate:
- Entity table with: Name, Key (MUST be string or int), Properties, Binding Source
- Relationship table with: Name, Source→Target, Source Table
- Mermaid ER diagram
- Multi-hop traversal examples

### Response 2: ontology-diagram-slide.html (save to `{DemoName}/Ontology/ontology-diagram-slide.html`)

Generate:
- Interactive HTML with Mermaid CDN
- Gradient styling, metric cards, legend
- Copy Mermaid diagram from ontology-structure.md

### Validation Checklist

- [ ] All entity keys are string or int type
- [ ] Property names are unique across ALL entities
- [ ] Property names ≤26 characters, alphanumeric with hyphens/underscores
- [ ] No reserved GQL words in property names
- [ ] Relationships have distinct source and target entities

**Action**: Ask "Design complete. Ready for Phase 3: Ontology TTL?"

---

## Phase 3: Ontology TTL

**Output**: `{scenario}.ttl` file saved to `{DemoName}/Ontology/{scenario}.ttl` with:
- Namespace declarations
- Entity class definitions
- Entity key definitions (rdfs:comment noting "Key: string" or "Key: int")
- Datatype properties with xsd types
- Object properties for relationships

### Type Mapping

| Ontology Type | XSD Type |
|---------------|----------|
| string | xsd:string |
| int | xsd:integer |
| double | xsd:double |
| boolean | xsd:boolean |
| datetime | xsd:dateTime |

> ⚠️ **Never use xsd:decimal** - it returns NULL in Graph queries

**Action**: Ask "TTL complete. Ready for Phase 4: Data Generation?"

---

## Phase 4: Data Generation 

### 1. Dimension Tables (Lakehouse → place in `Data/Lakehouse/`)
- DimProduct, DimFacility, DimSupplier, etc.
- 15-30 rows each
- Keys must be unique strings/integers

### 2. Fact Tables (Lakehouse → place in `Data/Lakehouse/`)
- FactQualityEvent, FactOrder, etc.
- 30-50 rows each
- Include foreign keys to dimensions

### 3. Edge Tables (Lakehouse → place in `Data/Lakehouse/`)
- FactBatchComponent (ProductionBatch-Component relationship)
- FactFacilitySupplier (Facility-Supplier relationship)
- Many-to-many junction tables

### 4. Timeseries Tables (Eventhouse → place in `Data/Eventhouse/`)
- BatchTelemetry, FacilityTelemetry, etc.
- 30-50 rows each
- MUST include: Timestamp, EntityKey, Metric columns

### Data Validation Checklist

- [ ] All key values are unique within table
- [ ] Foreign keys reference valid parent records
- [ ] No decimal type columns (use double/float)
- [ ] Timestamps in ISO 8601 format
- [ ] Boolean values as true/false (not 1/0)
- [ ] No NULL in key columns

**Action**: Ask "All data generated. Ready for Phase 5: Bindings?" after all CSVs.

---

## Phase 5: Binding Instructions (3 responses)

### Response 1: bindings.yaml (REQUIRED) — save to `{DemoName}/Bindings/bindings.yaml`

Generate machine-readable bindings file first. This is the **SOURCE OF TRUTH** for automation.

See: [schemas/bindings-schema.yaml](schemas/bindings-schema.yaml)

**Pathing**: All file references inside `bindings.yaml` must use `Data/Lakehouse/` for Lakehouse tables and `Data/Eventhouse/` for Eventhouse tables.

#### ⚠️ CRITICAL: Relationship Binding Rules (from MS Fabric Ontology Tutorial)

Based on the official Microsoft Fabric Ontology tutorial, relationship bindings work as follows:

**For a relationship `Source Entity → Target Entity`:**

1. **sourceTable**: The fact/bridge table that contains foreign keys to BOTH entities
2. **sourceKeyColumn**: The column in sourceTable that links to the SOURCE entity's key
3. **targetKeyColumn**: The column in sourceTable that links to the TARGET entity's key

**Example: Customer OWNS CreditCard**
```yaml
- relationship: OWNS
  sourceEntity: Customer
  targetEntity: CreditCard
  sourceTable: DimCreditCard      # Table containing relationship data
  sourceKeyColumn: CustomerId     # FK that identifies which Customer
  targetKeyColumn: CardId         # Key that identifies which CreditCard
```

**Common Patterns:**

| Relationship Pattern | sourceTable | sourceKeyColumn | targetKeyColumn |
|---------------------|-------------|-----------------|-----------------|
| Parent OWNS Child | Child table | ParentId (FK) | ChildId (PK) |
| Entity1 USES Entity2 | Fact table | Entity1Id | Entity2Id |
| Many-to-Many | Junction/Edge table | Entity1Id | Entity2Id |

**Validation**: The sourceTable must contain both `sourceKeyColumn` and `targetKeyColumn` as columns.

### Response 2: lakehouse-binding.md (human-readable) — save to `{DemoName}/Bindings/lakehouse-binding.md`

Include:
- Prerequisites (disable OneLake security!)
- Step-by-step for each entity
- Relationship binding steps
- Troubleshooting section

> ⚠️ **Timeseries Callout**: For EVERY entity with timeseries, add:
> "Note: Timeseries properties ({list}) are bound separately via Eventhouse."

### Response 3: eventhouse-binding.md (human-readable) — save to `{DemoName}/Bindings/eventhouse-binding.md`

For EACH entity with timeseries properties:

1. Configuration Summary Table
2. Timeseries Property Mappings Table
3. Step-by-step binding instructions
4. KQL ingestion command

**Action**: Ask "Bindings documented. Ready for Phase 6: Demo Questions?"

---

## Phase 6: Demo Questions

**Output**: `demo-questions.md` saved to `{DemoName}/demo-questions.md` with 5 questions covering:

| # | Theme | Minimum Hops |
|---|-------|--------------|
| 1 | Supply Chain Traceability | 3 |
| 2 | Impact Assessment | 4 |
| 3 | Operational Correlation | 2 + timeseries |
| 4 | Compliance/Regulatory | 2 |
| 5 | End-to-End Genealogy | 4 |

Each question must include:
- Business question in quotes
- Why it matters (business context)
- Graph traversal diagram
- GQL query (syntactically correct)
- Expected results table
- "Why Ontology is Better" comparison

### GQL Validation Checklist

- [ ] Use MATCH, not SELECT
- [ ] Use FILTER or WHERE clause, not HAVING
- [ ] Use bounded quantifiers {1,4} not unbounded *
- [ ] No OPTIONAL MATCH (not supported)
- [ ] Aggregations in RETURN with GROUP BY

Add comprehensive Data Agent Instructions at the end.

**Action**: Ask "Questions complete. Ready for Phase 7: README?"

---

## Phase 7: Final Documentation

### Output 1: README.md — save to `{DemoName}/README.md`

Include:
- Demo overview (company, domain, use case)
- Entity/relationship summary
- Folder structure
- Prerequisites checklist
- Quick start guide
- Known limitations
- Demo scenarios (3 scripted walkthroughs)

### Output 2: .demo-metadata.yaml (REQUIRED) — save to `{DemoName}/.demo-metadata.yaml`

See: [schemas/metadata-schema.yaml](schemas/metadata-schema.yaml)

> ⚠️ **Critical**: This file enables the fabric-demo automation tool to validate compatibility.

---

## Generation Complete!

Final message should include:

1. **Summary** of all generated files (including .demo-metadata.yaml)
2. **Next steps** for user:
   - Manual setup: Follow README.md
   - Automated setup: Run `fabric-demo setup {DemoName}/`
3. **Common pitfalls** to avoid
4. **Links** to documentation


# REFERENCES

When ask to validate limitations for update, read through all the below.
references:
  documentation:
    - { title: "IQ Overview", url: "https://learn.microsoft.com/en-us/fabric/iq/overview" }
    - { title: "Data Binding", url: "https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data" }
    - { title: "Graph Limitations", url: "https://learn.microsoft.com/en-us/fabric/graph/limitations" }
    - { title: "GQL Guide", url: "https://learn.microsoft.com/en-us/fabric/graph/gql-language-guide" }
  
  knownIssues:
    - { title: "IQ Known Issues", url: "https://support.fabric.microsoft.com/known-issues/?product=IQ" }
