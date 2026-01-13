# Fabric Ontology Demo Generation - Agent Workflow

> **Spec Version**: 3.5  
> **Last Updated**: January 2026  
> **Purpose**: Phase-by-phase workflow for generating error-free Fabric Ontology demos

---

## Validation Rules Reference

⚠️ **CRITICAL - READ BEFORE GENERATING ANY NAMES**: All validation rules are defined in the **Unofficial Fabric Ontology SDK** at:

**📄 Canonical Source**: [https://github.com/falloutxAY/Unofficial-Fabric-Ontology-SDK/blob/main/porting/contracts/validation-rules.yaml](https://github.com/falloutxAY/Unofficial-Fabric-Ontology-SDK/blob/main/porting/contracts/validation-rules.yaml)

This file is the **single source of truth** for:
- **Reserved Words** (317 GQL reserved words - MUST check before naming ANY entity, property, or relationship)
- Entity/relationship type name patterns and length limits (1-26 characters)
- Property name patterns and length limits (1-52 characters)
- Ontology name patterns and length limits (1-52 characters, NO hyphens)
- Data type constraints (NO Decimal - use Double)
- Binding validation rules

⛔ **BEFORE NAMING ANY ENTITY OR PROPERTY**, you MUST verify the name is NOT in the `reservedWords` list in the SDK validation rules file. Common violations include:
- `Order` (reserved - use `SalesOrder`, `PurchaseOrder`, `TradeOrder`)
- `Match`, `Return`, `Filter`, `Where`, `Node`, `Edge`, `Path`
- `Count`, `Sum`, `Avg`, `Min`, `Max`
- See full list in the validation-rules.yaml file

**Official Microsoft Documentation**:
- [Entity Type Creation](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-entity-types) - naming rules, key constraints
- [Data Binding](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data) - property uniqueness, binding order
- [GQL Reserved Words](https://learn.microsoft.com/en-us/fabric/graph/gql-reference-reserved-terms) - complete reserved words list
- [Relationship Types](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-relationship-types) - source/target constraints

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
demo-{DemoName}/
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

**Agent instructions** Do each phase one at a time so that we do not hit token limits

---
## Phase 1: Discovery

⛔ **BEFORE PROPOSING ANY ENTITY NAMES**: Read the `reservedWords` list in [`validation-rules.yaml`](https://github.com/falloutxAY/Unofficial-Fabric-Ontology-SDK/blob/main/porting/contracts/validation-rules.yaml)

**Output**: Brief summary confirming:
- Company/industry context
- 6-8 proposed entity types with descriptions
  - ⛔ **Verify each name is NOT a reserved word** (e.g., use `TradeOrder` not `Order`)
- Key relationships (aim for 8-12)
- Which entities will have timeseries data
- 2-3 multi-hop traversal scenarios

**Common Reserved Word Violations to Avoid:**
- ❌ `Order` → ✅ `SalesOrder`, `TradeOrder`, `PurchaseOrder`, `StockOrder`
- ❌ `Match` → ✅ `TradeMatch`, `OrderMatch`
- ❌ `Record` → ✅ `TradeRecord`, `DataRecord`

**Action**: Ask "Does this scope look correct? Ready for Phase 2: Design?"

**Agent instructions** Do not procceed till user say yes

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

> ⛔ **MANDATORY**: Read [`Unofficial-Fabric-Ontology-SDK/porting/contracts/validation-rules.yaml`](../../../Unofficial-Fabric-Ontology-SDK/porting/contracts/validation-rules.yaml) BEFORE naming entities/properties

- [ ] ⛔ **NO RESERVED WORDS**: Check EVERY entity and property name against `reservedWords` in validation-rules.yaml
- [ ] All entity keys are string or int type ([keyDataTypes](https://learn.microsoft.com/en-us/fabric/iq/ontology/resources-glossary))
- [ ] Property names are unique across ALL entities ([globalPropertyUniqueness](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data))
- [ ] Entity/relationship type names ≤26 characters, property names ≤52 characters
- [ ] Names: alphanumeric with hyphens/underscores, start with letter
- [ ] No reserved GQL words in property names ([reservedWords](https://learn.microsoft.com/en-us/fabric/graph/gql-reference-reserved-terms))
- [ ] Relationships have distinct source and target entities ([sourceTargetDistinct](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-relationship-types))

**Action**: Ask "Design complete. Ready for Phase 3: Ontology TTL?"

---

## Phase 3: Ontology TTL

**Output**: `{scenario}.ttl` file saved to `{DemoName}/Ontology/{scenario}.ttl` with:
- Namespace declarations
- Entity class definitions
- Entity key definitions (rdfs:comment noting "Key: {PropertyName}")
- Datatype properties with xsd types
- Object properties for relationships

### ⚠️ CRITICAL: Key Property Format for Parser

The TTL converter parses `rdfs:comment` to extract key property names. Use this **exact format**:

```turtle
:Product a owl:Class ;
    rdfs:label "Product" ;
    rdfs:comment "Key: ProductId (string)" .  # Parser extracts "ProductId"

:ProductId a owl:DatatypeProperty ;
    rdfs:domain :Product ;
    rdfs:range xsd:string .
```

The parser uses regex `Key:\s*(\w+)` to extract the key property name.

### Type Mapping

| Ontology Type | XSD Type | Graph Type |
|---------------|----------|------------|
| string | xsd:string | STRING |
| int | xsd:integer | INTEGER (64-bit signed) |
| double | xsd:double | DOUBLE (64-bit floating point) |
| boolean | xsd:boolean | BOOLEAN (true/false) |
| datetime | xsd:dateTime | ZONED DATETIME |

> ⚠️ **CRITICAL TYPE CONSTRAINTS**:
> - **Never use xsd:decimal** - Fabric Graph does NOT support Decimal type (returns NULL)
> - **Key properties MUST be string or int ONLY** (not datetime, boolean, or double)
> - Use **double** instead of decimal for all monetary/precision values

**Action**: Ask "TTL complete. Ready for Phase 4: Data Generation?"

---

## ⛔ CRITICAL: Property and Entity Naming Constraints

> **CANONICAL SOURCE**: [`Unofficial-Fabric-Ontology-SDK/porting/contracts/validation-rules.yaml`](../../../Unofficial-Fabric-Ontology-SDK/porting/contracts/validation-rules.yaml)
> 
> **READ THIS FILE BEFORE NAMING ANYTHING** - It contains 280+ reserved words that CANNOT be used.

### Entity Type Names
- **Length**: 1–26 characters
- **Pattern**: `^[a-zA-Z][a-zA-Z0-9_-]{0,25}$`
- Must start with a letter
- Can contain letters, numbers, hyphens and underscores
- ⛔ **MUST NOT be a reserved word** (case-insensitive)

### Property Names
- **Length**: 1–52 characters  
- **Pattern**: `^[a-zA-Z][a-zA-Z0-9_-]{0,51}$`
- **MUST be unique across ALL entity types in the ontology** (ERROR, not warning)
- Must start with a letter
- Can contain letters, numbers, hyphens and underscores
- Recommendation: Use entity prefix for uniqueness (e.g., `Product_Name`, `Batch_Status`)
- ⛔ **MUST NOT be a reserved word** (case-insensitive)

### ⛔ RESERVED WORDS - NEVER USE AS ENTITY OR PROPERTY NAMES

> **Full list (317 words)**: See `reservedWords` section in [`validation-rules.yaml`](../../../Unofficial-Fabric-Ontology-SDK/porting/contracts/validation-rules.yaml)

**COMMONLY VIOLATED RESERVED WORDS:**
```
❌ Order      → ✅ Use: SalesOrder, PurchaseOrder, TradeOrder, StockOrder
❌ Match      → ✅ Use: TradeMatch, OrderMatch
❌ Return     → ✅ Use: ProductReturn, OrderReturn
❌ Node       → ✅ Use: NetworkNode, GraphNode
❌ Edge       → ✅ Use: NetworkEdge, Connection
❌ Path       → ✅ Use: RoutePath, NetworkPath
❌ Record     → ✅ Use: DataRecord, TradeRecord
❌ Key        → ✅ Use: AccessKey, PrimaryKey
❌ Label      → ✅ Use: ItemLabel, ProductLabel
❌ Value      → ✅ Use: AssetValue, TradeValue
❌ Type       → ✅ Use: AssetType, OrderType
❌ Count      → ✅ Use: ItemCount, TradeCount
❌ Sum        → ✅ Use: TotalSum, OrderSum
❌ Min/Max    → ✅ Use: MinValue, MaxValue, MinPrice, MaxPrice
```

**GQL KEYWORDS (all reserved):**
```
MATCH, RETURN, FILTER, WHERE, LET, ORDER, LIMIT, OFFSET,
DISTINCT, GROUP, BY, ASC, DESC, AND, OR, NOT, TRUE, FALSE,
NULL, IS, IN, STARTS, ENDS, CONTAINS, WITH, AS, NODE, EDGE,
PATH, TRAIL, UNION, ALL, count, sum, avg, min, max, coalesce,
size, labels, nodes, edges, upper, lower, trim, char_length
```

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
- **CRITICAL**: Data MUST be in COLUMNAR format (each row = one timestamped observation)
- **Format**: Each row represents one entity at one timestamp with metric values as columns

#### Timeseries Columnar Format Example:
```csv
Timestamp,AssemblyId,Temperature,Torque,CycleTime
2024-01-15T08:00:00Z,ASM-001,72.5,45.2,120.5
2024-01-15T08:01:00Z,ASM-001,73.1,44.8,119.8
```

### Data Validation Checklist

- [ ] All key values are unique within table
- [ ] Key values contain no NULLs
- [ ] Key columns are string or int type ONLY
- [ ] Foreign keys reference valid parent records
- [ ] No decimal type columns (use double/float for precision values)
- [ ] Timestamps in ISO 8601 format (e.g., 2024-01-15T10:30:00Z)
- [ ] Boolean values as true/false (lowercase, not 1/0)
- [ ] No NULL in key columns
- [ ] All property values match declared data types

**Action**: Ask "All data generated. Ready for Phase 5: Bindings?" after all CSVs.

---

## Phase 5: Binding Instructions (3 responses)

### Response 1: bindings.yaml (REQUIRED) — save to `{DemoName}/Bindings/bindings.yaml`

Generate machine-readable bindings file first. This is the **SOURCE OF TRUTH** for automation.

See: [schemas/bindings-schema.yaml](schemas/bindings-schema.yaml) for full schema.

**Pathing**: All file references inside `bindings.yaml` must use `Data/Lakehouse/` for Lakehouse tables and `Data/Eventhouse/` for Eventhouse tables.

#### ⚠️ CRITICAL: Required YAML Structure (Parser-Compatible)

The `fabric-demo` CLI parser expects this **exact nested structure**:

```yaml
_schema_version: "1.0"

metadata:
  name: "{DemoName}"
  version: "1.0"
  description: "{description}"

lakehouse:
  name: "{DemoName}_Lakehouse"
  entities:
    - entity: EntityName           # Entity type name (matches ontology)
      sourceTable: DimEntityName   # Table name
      keyColumn: EntityId          # Primary key column
      file: Data/Lakehouse/DimEntityName.csv
      properties:
        - property: PropertyName   # Ontology property name
          column: ColumnName       # Source column name
          type: string             # string|int|double|boolean|datetime
          
  relationships:
    - relationship: RELATIONSHIP_NAME
      sourceEntity: SourceEntity
      targetEntity: TargetEntity
      sourceTable: FactOrChildTable
      sourceKeyColumn: SourceEntityId   # FK to source entity
      targetKeyColumn: TargetEntityId   # Key/FK to target entity

eventhouse:
  name: "{DemoName}_Telemetry"
  database: "{DemoName}DB"
  entities:
    - entity: EntityWithTimeseries
      sourceTable: EntityTelemetry
      keyColumn: EntityId
      timestampColumn: Timestamp
      file: Data/Eventhouse/EntityTelemetry.csv
      rowCount: 50
      properties:
        - property: MetricName
          column: MetricColumn
          type: double
```

> ⚠️ **Parser Requirement**: The root keys MUST be `_schema_version`, `lakehouse`, and `eventhouse` (not a flat `entities:` list). The parser looks for `lakehouse.entities` and `eventhouse.entities` specifically.

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

#### ⚠️ CRITICAL: BOTH sourceKeyColumn AND targetKeyColumn MUST Match Entity Key Names

The Fabric API **requires** that **both** `sourceKeyColumn` and `targetKeyColumn` have the **exact same names** as their respective entity's key properties. From the documentation:

> "The source column selections must match the entity type keys."

This applies to **BOTH** columns - the API validates this for both source and target entities.

**❌ WRONG - Column names differ from entity keys:**
```yaml
# Shipment entity has key: ShipmentId
# Facility entity has key: FacilityId
# But table uses different column names - THIS WILL FAIL!
- relationship: ORIGINATED_FROM
  sourceEntity: Shipment
  targetEntity: Facility
  sourceTable: FactShipment
  sourceKeyColumn: ShipmentId         # ✅ Matches Shipment's key
  targetKeyColumn: OriginFacilityId   # ❌ ERROR! Must be "FacilityId"
```
API Error: `targetKeyRefBindings targetPropertyId 'OriginFacilityId' must be present in the target EntityType's EntityIdParts`

**✅ CORRECT - Use edge tables with matching column names:**
```yaml
# Create separate edge table with columns named exactly as entity keys
- relationship: ORIGINATED_FROM
  sourceEntity: Shipment
  targetEntity: Facility
  sourceTable: EdgeShipmentOrigin    # Edge table with proper column names
  sourceKeyColumn: ShipmentId        # ✅ Matches Shipment's key property name
  targetKeyColumn: FacilityId        # ✅ Matches Facility's key property name
```

**Rule**: If your source table has FK columns with different names (e.g., `OriginFacilityId`, `DestFacilityId`, `SourceShipmentId`), you MUST create a separate edge table where the columns are renamed to match the entity keys exactly.

**Common Patterns:**
| Relationship Pattern | sourceTable | sourceKeyColumn | targetKeyColumn |
|---------------------|-------------|-----------------|-----------------|
| Parent OWNS Child | Child table | ParentId (FK) | ChildId (PK) |
| Entity1 USES Entity2 | Fact table | Entity1Id | Entity2Id |
| Many-to-Many | Junction/Edge table | Entity1Id | Entity2Id |
| Multiple refs to same entity | **Separate Edge tables** | SourceId | **TargetEntityKey** (exact name!) |

**Validation**: 
1. The sourceTable must contain both `sourceKeyColumn` and `targetKeyColumn` as columns
2. **`targetKeyColumn` must be named exactly the same as the target entity's key property**

### Response 2: lakehouse-binding.md (human-readable) — save to `{DemoName}/Bindings/lakehouse-binding.md`

Include:
- Prerequisites (disable OneLake security!)
- Step-by-step for each entity
- Relationship binding steps
- Troubleshooting section

#### ⚠️ CRITICAL: Lakehouse Binding Limitations

Document these limitations clearly:

1. **OneLake Security**: Lakehouses with OneLake security enabled CANNOT be used as data sources
2. **One Static Binding Per Entity**: Each entity type supports only ONE static data binding (cannot combine static data from multiple sources)
3. **Multiple Timeseries Supported**: Entity types DO support bindings from multiple time series sources (eventhouse + lakehouse)
4. **Schema Requirement**: Lakehouse schemas (Public Preview) must be DISABLED - the automation sets sourceSchema to null

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
- [ ] No OPTIONAL MATCH (not supported in Fabric Graph)
- [ ] Aggregations in RETURN with GROUP BY
- [ ] Max 8 hops in variable-length patterns
- [ ] Query results must be < 64MB (truncated otherwise)
- [ ] Query timeout is 20 minutes max

### GQL Features NOT YET Supported

Do NOT use these in demo queries:
- OPTIONAL MATCH
- UNION DISTINCT (only UNION ALL works)
- Unbounded graph pattern quantifiers (use {1,8} max)
- Path value constructor
- Scalar subqueries
- Undirected edge patterns

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

See: [schemas/metadata-schema.yaml](schemas/metadata-schema.yaml) for full schema.

#### Required Structure:

```yaml
metadata:
  name: "{DemoName}"
  version: "1.0"
  created: "YYYY-MM-DD"
  author: Fabric Ontology Demo Agent
  specVersion: "3.3"

demo:
  company: "{CompanyName}"
  industry: "{Industry}"
  domain: "{Domain}"
  description: "{description}"
  useCases:
    - "Use case 1"
    - "Use case 2"

ontology:
  file: Ontology/{demo-slug}.ttl           # Use forward slashes
  namespace: http://example.com/ontology#
  entities:
    - name: EntityName
      key: EntityId
      keyType: string                       # string or int
      hasTimeseries: false

data:
  lakehouse:
    folder: Data/Lakehouse                  # Use forward slashes
    tables:
      - name: DimEntity
        file: DimEntity.csv
        rowCount: 20
  eventhouse:
    folder: Data/Eventhouse
    tables:
      - name: EntityTelemetry
        file: EntityTelemetry.csv
        rowCount: 50

bindings:
  file: Bindings/bindings.yaml              # Use forward slashes
```

> ⚠️ **Path Format**: Use **forward slashes** (`/`) in all file paths within YAML files. The Python `pathlib.Path` handles cross-platform conversion automatically.

> ⚠️ **Critical**: This file enables the fabric-demo automation tool to validate compatibility.

---

## Generation Complete!

Final message should include:

1. **Summary** of all generated files (including .demo-metadata.yaml)
2. **Next steps** for user:
   - Follow Quickstart in README.md

---

## Phase 8: Final Validation (MANDATORY)

> ⚠️ **This phase is REQUIRED before declaring demo complete.** Run validation to catch errors before setup.

### Step 1: Run the Validate Command

Execute the validation command on the generated demo:

```bash
cd Demo-automation/src
python -m demo_automation validate ../../{DemoName}
```

Or if installed:
```bash
fabric-demo validate {DemoName}
```

### Step 2: Review Validation Output

The validator checks ALL Fabric Ontology constraints:

| Check | What It Validates |
|-------|------------------|
| **Structure** | Required directories, expected files |
| **Naming** | Entity/property names 1-26 chars, valid pattern, no GQL reserved words |
| **Types** | No xsd:decimal in TTL, keys are string/int only |
| **Property Uniqueness** | Property names unique across ALL entities |
| **TTL Key Format** | `rdfs:comment "Key: PropertyName (type)"` present |
| **CSV Data** | No NULL keys, unique key values, valid timestamps |
| **Bindings** | sourceTable exists, columns present in CSV |
| **targetKeyColumn Match** | Column name matches target entity's key exactly |
| **Static Binding Count** | Only 1 static binding per entity (across ALL sources) |

### Step 3: Fix All Errors

If validation reports **ERRORS**, you MUST fix them before proceeding:

| Error Type | Action Required |
|------------|----------------|
| `targetKeyColumn 'X' does not match target entity's key 'Y'` | Create edge table with column renamed to 'Y' |
| `Entity 'X' has N static bindings - only 1 allowed` | Remove duplicate bindings or change to TimeSeries |
| `Property 'X' uses reserved GQL word` | Rename property with entity prefix |
| `Property 'X' is not unique - also exists in Entity Y` | Rename with entity prefix (e.g., `Entity_Property`) |
| `Invalid data type: decimal` | Change to `double` in TTL and data |
| `Key column has NULL values` | Fix data to ensure all keys have values |

### Step 4: Re-validate

After fixing errors, run validation again:

```bash
python -m demo_automation validate ../../{DemoName}
```

**Repeat Steps 2-4 until validation passes with 0 errors.**

### Step 5: Confirm Success

✅ **Demo is ready when:**
- Validation shows `0 errors`
- Warnings are reviewed and acceptable
- All critical constraints are satisfied

**Action**: Report validation results to user. If errors exist, list them and offer to fix. If clean, confirm: "Demo validated successfully! Ready for `fabric-demo setup`."


---

## ⚠️ CRITICAL: Parser Compatibility Checklist

Before finishing, verify ALL of the following for `fabric-demo setup` to work:

### bindings.yaml
- [ ] Root keys are `_schema_version`, `lakehouse`, `eventhouse` (NOT flat `entities:`)
- [ ] `_schema_version: "1.0"` is present at root level
- [ ] Entities under `lakehouse.entities[]` use `sourceTable`, `keyColumn`, `properties[]`
- [ ] Relationships under `lakehouse.relationships[]` use `relationship`, `sourceEntity`, `targetEntity`, `sourceTable`, `sourceKeyColumn`, `targetKeyColumn`
- [ ] **`sourceKeyColumn` name MUST exactly match the SOURCE entity's key property name**
- [ ] **`targetKeyColumn` name MUST exactly match the TARGET entity's key property name**
- [ ] If a table has multiple FK columns to the same entity (e.g., OriginFacilityId, DestFacilityId), create **separate Edge tables** with the columns renamed to match entity keys
- [ ] Eventhouse entities under `eventhouse.entities[]` include `timestampColumn`
- [ ] All paths use **forward slashes** (`Data/Lakehouse/`, not `Data\Lakehouse\`)

### TTL Ontology
- [ ] Each entity class has `rdfs:comment "Key: {PropertyName} (type)"` 
- [ ] Key property name in comment matches an actual DatatypeProperty
- [ ] No `xsd:decimal` types (use `xsd:double` instead)
- [ ] Key properties use `xsd:string` or `xsd:integer` ONLY

### Entity & Property Naming
- [ ] Entity names are 1-26 characters
- [ ] Property names are 1-26 characters
- [ ] Names start and end with alphanumeric characters
- [ ] Property names are UNIQUE across ALL entities in the ontology
- [ ] No GQL reserved words used as names

### Folder Structure
- [ ] Case matches exactly: `Bindings/`, `Data/`, `Ontology/` (parser is case-insensitive but consistency matters)
- [ ] `Data/Lakehouse/` contains Dim*.csv and Fact*.csv files
- [ ] `Data/Eventhouse/` contains *Telemetry.csv files
- [ ] `Ontology/` contains {demo-slug}.ttl file

### CSV Files
- [ ] All CSVs have headers in first row
- [ ] Key columns contain unique values (no duplicates)
- [ ] Key columns are string or int type only
- [ ] Foreign keys reference valid parent records
- [ ] No NULL values in key columns
- [ ] Timestamps in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
- [ ] Booleans as lowercase `true`/`false`
- [ ] No decimal columns (use double/float)

### .demo-metadata.yaml
- [ ] `ontology.file` path uses forward slashes
- [ ] `data.lakehouse.folder` path uses forward slashes
- [ ] All entity names match TTL class names exactly
- [ ] All entity keys specify `keyType: string` or `keyType: int`

### Graph Query Constraints
- [ ] Demo questions use max 8 hops in MATCH patterns
- [ ] No OPTIONAL MATCH in GQL queries
- [ ] Use bounded quantifiers `{1,N}` not unbounded `*`
- [ ] Results designed to stay under 64MB


# REFERENCES

When asked to validate limitations for update, read through all the below.

references:
  documentation:
    - { title: "IQ Overview", url: "https://learn.microsoft.com/en-us/fabric/iq/overview" }
    - { title: "Data Binding", url: "https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-bind-data" }
    - { title: "Graph Limitations", url: "https://learn.microsoft.com/en-us/fabric/graph/limitations" }
    - { title: "GQL Guide", url: "https://learn.microsoft.com/en-us/fabric/graph/gql-language-guide" }
    - { title: "Entity Types", url: "https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-entity-types" }
    - { title: "Troubleshooting", url: "https://learn.microsoft.com/en-us/fabric/iq/ontology/resources-troubleshooting" }
  
  knownIssues:
    - { title: "IQ Known Issues", url: "https://support.fabric.microsoft.com/known-issues/?product=IQ" }

---

# COMPREHENSIVE CONSTRAINTS SUMMARY

This section consolidates ALL constraints from Microsoft Fabric Ontology and Graph documentation.

## 1. Graph Data Type Constraints

| Supported Type | Description | Notes |
|----------------|-------------|-------|
| Boolean | `true` / `false` | Lowercase only |
| Double | 64-bit floating point | Use instead of Decimal |
| Integer | 64-bit signed integers | Range: -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807 |
| String | Unicode character strings | |
| Zoned DateTime | Timestamps with timezone | ISO 8601 format |

**❌ NOT SUPPORTED:**
- `Decimal` type - returns NULL in Graph queries
- Complex types (arrays, objects as properties)

## 2. Entity Type Constraints

| Constraint | Value |
|------------|-------|
| Name length | 1–26 characters |
| Name pattern | `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,24}[a-zA-Z0-9]$` |
| Key types | string OR int ONLY |
| Properties | Must be unique across ALL entities |

## 3. Data Binding Constraints

| Constraint | Details |
|------------|---------|
| OneLake Security | Must be DISABLED on Lakehouse |
| Static bindings per entity | Maximum ONE per entity type |
| Timeseries bindings | Multiple allowed from eventhouse + lakehouse |
| Lakehouse schemas | Must be DISABLED (automation sets sourceSchema=null) |

## 4. Relationship Binding Constraints

| Field | Constraint |
|-------|------------|
| `sourceKeyColumn` | **MUST have EXACT SAME NAME as source entity's key property** |
| `targetKeyColumn` | **MUST have EXACT SAME NAME as target entity's key property** |

> From MS Documentation: "The source column selections must match the entity type keys."

**Common Errors:**
- `targetKeyRefBindings targetPropertyId 'X' must be present in the target EntityType's EntityIdParts`
  - **Cause**: targetKeyColumn name doesn't match target entity's key
  - **Fix**: Rename column or create edge table with correct column name
- `sourceKeyRefBindings` error (similar for source)
  - **Cause**: sourceKeyColumn name doesn't match source entity's key
  - **Fix**: Rename column or create edge table with correct column name

## 5. GQL Query Constraints

| Constraint | Limit |
|------------|-------|
| Maximum hops | 8 in variable-length patterns |
| Result size | 64 MB (truncated if larger) |
| Query timeout | 20 minutes |
| Graph instances | 10 per workspace |
| Graph size | 500 million nodes+edges (performance degrades) |

**Not Supported:**
- OPTIONAL MATCH
- UNION DISTINCT (only UNION ALL)
- Unbounded quantifiers (use `{1,8}` max)
- Undirected edge patterns

## 6. Timeseries Data Constraints

| Requirement | Details |
|-------------|---------|
| Format | Columnar (row = one timestamped observation) |
| Required columns | Timestamp, EntityKey, metric values |
| Timestamp format | ISO 8601 (YYYY-MM-DDTHH:MM:SSZ) |
| Static binding first | Must have static binding before timeseries |
| Key contextualization | Static key must match column in timeseries data |
