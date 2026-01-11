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

The agent generates: ontology-structure.md → TTL file → CSV data → bindings.yaml → demo-questions.md → README.md

Once generation is complete:

```bash
# Validate the generated package
python -m demo_automation validate ./demo-water-treatment

# Deploy to Fabric
python -m demo_automation setup ./demo-water-treatment
```

---

## The 7 Phases

1. **Discovery** - Gather requirements (domain, entities, relationships, use cases)
2. **Design** - Create ontology-structure.md + diagram
3. **Ontology TTL** - Generate RDF/Turtle file with entities, properties, relationships
4. **Data** - Create CSV files (Dim/Fact tables, timeseries)
5. **Bindings** - Generate bindings.yaml + markdown guides
6. **Queries** - Create demo-questions.md with 5+ sample GQL queries
7. **Final** - Generate README.md + metadata

---

## Output Structure

`{DemoName}/README.md` • `.demo-metadata.yaml` • `demo-questions.md` • `ontology-structure.md` • `Bindings/` (yaml + guides) • `Data/Lakehouse/` (CSVs) • `Data/Eventhouse/` (telemetry) • `Ontology/` (TTL + diagram)

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
| `.agentic/schemas/validation-rules.yaml` | Validation rules (single source of truth) |
| `.agentic/schemas/bindings-schema.yaml` | Bindings file schema |
| `.agentic/schemas/metadata-schema.yaml` | Metadata file schema |
| `.agentic/templates/` | Output templates |

---

## See Also

- [Quick Start](index.md) - Deploy existing demos
- [CLI Reference](cli-reference.md) - Automation commands
- [Troubleshooting](troubleshooting.md) - Common issues
