# Agent Workflow Guide

How to use AI agents to generate new Fabric Ontology demos.

---

## Overview

The `.agentic/` folder contains specifications that guide AI agents through a structured 7-phase workflow to generate complete, deployment-ready demo packages.

---

## Quick Start

### 1. Prompt an AI Agent

Open your preferred AI assistant (GitHub Copilot, ChatGPT, Claude, etc.) and provide the `.agentic` context:

```
Using #file:.agentic, create a demo for "water treatment plant monitoring"
```

Or be more specific:

```
Using #file:.agentic/agent-instructions.md, generate a Fabric Ontology demo 
for a pharmaceutical manufacturing company. 

Focus on:
- Batch traceability from raw materials to finished products
- Quality control events and deviations
- Equipment maintenance correlation with batch quality
- 6-8 entities with timeseries data for temperature and pressure monitoring
```

### 2. Follow the 7 Phases

The agent will guide you through each phase, asking for confirmation before proceeding:

| Phase | Output | Agent Prompt |
|-------|--------|--------------|
| 1. Discovery | Scope confirmation | "Does this scope look correct?" |
| 2. Design | ontology-structure.md, HTML slide | "Ready for Phase 3: Ontology TTL?" |
| 3. Ontology | TTL file | "Ready for Phase 4: Data Generation?" |
| 4. Data | CSV files | "Ready for Phase 5: Bindings?" |
| 5. Bindings | bindings.yaml, markdown guides | "Ready for Phase 6: Demo Questions?" |
| 6. Queries | demo-questions.md | "Ready for Phase 7: README?" |
| 7. Final | README.md, metadata | Generation complete! |

### 3. Deploy the Demo

Once generation is complete:

```bash
# Validate the generated package
python -m demo_automation validate ./demo-water-treatment

# Deploy to Fabric
python -m demo_automation setup ./demo-water-treatment
```

---

## The 7-Phase Workflow

### Phase 1: Discovery

The agent gathers requirements:

- **Industry/Company context**: What domain is this demo for?
- **Entity types**: What things are we modeling? (6-8 recommended)
- **Relationships**: How do entities connect? (8-12 recommended)
- **Timeseries needs**: Which entities have operational metrics?
- **Use cases**: What questions should the demo answer?

**Your input**: Describe your scenario and answer clarifying questions.

### Phase 2: Design

The agent creates the ontology design:

1. **ontology-structure.md**: Tables of entities, properties, relationships
2. **ontology-diagram-slide.html**: Interactive visualization

**Validation checklist**:
- ✅ All entity keys are string or int type
- ✅ Property names are unique across all entities
- ✅ Property names ≤26 characters
- ✅ No reserved GQL words in property names

### Phase 3: Ontology TTL

The agent generates the RDF/Turtle ontology file:

- Namespace declarations
- Entity class definitions
- Datatype properties with XSD types
- Object properties for relationships

**Critical**: Never use `xsd:decimal` - use `xsd:double` instead.

### Phase 4: Data Generation

The agent creates CSV files:

| Type | Location | Purpose |
|------|----------|---------|
| Dimension tables | `Data/Lakehouse/Dim*.csv` | Master data (15-30 rows) |
| Fact tables | `Data/Lakehouse/Fact*.csv` | Transactional data (30-50 rows) |
| Edge tables | `Data/Lakehouse/Edge*.csv` | Many-to-many relationships |
| Timeseries | `Data/Eventhouse/*.csv` | Metrics with timestamps |

### Phase 5: Bindings

The agent creates binding configurations:

1. **bindings.yaml**: Machine-readable, source of truth for automation
2. **lakehouse-binding.md**: Human-readable static binding instructions
3. **eventhouse-binding.md**: Human-readable timeseries instructions

### Phase 6: Demo Questions

The agent generates 5+ sample questions:

| Theme | Hops |
|-------|------|
| Supply Chain Traceability | 3+ |
| Impact Assessment | 4+ |
| Operational Correlation | 2 + timeseries |
| Compliance/Regulatory | 2+ |
| End-to-End Genealogy | 4+ |

Each includes GQL queries, expected results, and business context.

### Phase 7: Final Documentation

The agent wraps up with:

- **README.md**: Setup guide, scenarios, limitations
- **.demo-metadata.yaml**: Version info for automation compatibility

---

## Output Structure

```
{DemoName}/
├── README.md                    # Demo overview and setup
├── .demo-metadata.yaml          # Automation metadata
├── demo-questions.md            # Sample GQL queries
├── ontology-structure.md        # Entity/relationship summary
├── Bindings/
│   ├── bindings.yaml            # Machine-readable bindings
│   ├── lakehouse-binding.md     # Static binding guide
│   └── eventhouse-binding.md    # Timeseries binding guide
├── Data/
│   ├── Lakehouse/
│   │   ├── Dim*.csv             # Dimension tables
│   │   ├── Fact*.csv            # Fact tables
│   │   └── Edge*.csv            # Edge/junction tables
│   └── Eventhouse/
│       └── *Telemetry.csv       # Timeseries data
└── Ontology/
    ├── {demo-slug}.ttl          # RDF ontology
    └── ontology-diagram-slide.html  # Visual diagram
```

---

## Tips for Better Results

### Be Specific About Your Domain

❌ "Create a manufacturing demo"

✅ "Create a demo for a semiconductor fabrication plant focusing on wafer traceability, clean room environmental monitoring, and equipment maintenance correlation"

### Specify Timeseries Requirements

❌ "Include some metrics"

✅ "Equipment entities need temperature, vibration, and power consumption metrics sampled every 30 seconds. Batches need pressure and humidity during processing."

### Request Specific Traversal Scenarios

❌ "Add some queries"

✅ "I need to demonstrate:
1. Tracing a defective chip back to its wafer lot and equipment used
2. Finding all batches processed on equipment X during a maintenance window
3. Correlating environmental readings with yield rates"

### Review Each Phase

The agent asks for confirmation between phases. Use this to:
- Catch naming issues early
- Adjust entity scope
- Ensure relationships make sense

---

## Fabric Ontology Constraints

The agent enforces these automatically, but be aware:

| Constraint | Limit |
|------------|-------|
| Property types | string, int, double, boolean, datetime only |
| Entity key types | string or int only |
| Property name length | Max 26 characters |
| Decimal type | ❌ Not supported (use double) |
| OneLake security | Must be disabled for bindings |
| Lakehouse schemas | Must be disabled |

---

## Troubleshooting

### Agent Produces Invalid Output

Remind the agent:
```
Please re-read #file:.agentic/agent-instructions.md and follow the constraints exactly.
```

### Missing Files

Check the agent created all required files:
```bash
python -m demo_automation validate ./demo-name
```

### Bindings Don't Match TTL

The `bindings.yaml` entity names must exactly match TTL class names:
```
TTL: :ProductionBatch a owl:Class
YAML: entity: ProductionBatch  ✅
YAML: entity: Production_Batch  ❌
```

### Non-Deterministic Output

AI agents are non-deterministic. If you get unexpected results:
1. Start fresh with a new conversation
2. Be more explicit in your requirements
3. Break complex scenarios into smaller pieces

---

## Reference Files

| File | Purpose |
|------|---------|
| `.agentic/agent-instructions.md` | Complete 7-phase workflow |
| `.agentic/schemas/bindings-schema.yaml` | Bindings file schema |
| `.agentic/schemas/metadata-schema.yaml` | Metadata file schema |
| `.agentic/templates/` | Output templates |

---

## See Also

- [Quick Start](index.md) - Deploy existing demos
- [CLI Reference](cli-reference.md) - Automation commands
- [Troubleshooting](troubleshooting.md) - Common issues
