# Fabric Ontology Demo Agent

An expert agent configuration for creating Microsoft Fabric Ontology demo scenarios with realistic sample data, bindings, and guidance. The core configuration lives in [.agentic](.agentic), describing entities, relationships, bindings, validation checks, and deliverables.

## 📖 Documentation

**[📚 Read the Full Documentation →](docs/index.md)**

| Guide | Description |
|-------|-------------|
| [Quick Start](docs/index.md) | Get a demo running in 5 minutes |
| [CLI Reference](docs/cli-reference.md) | All commands explained |
| [Configuration](docs/configuration.md) | Setup options |
| [Troubleshooting](docs/troubleshooting.md) | Common issues |
| [Agent Workflow](docs/agent-workflow.md) | Generate new demos with AI |

## What's inside
- **[.agentic](.agentic)** — Agent specifications, schemas, and templates for generating ontology demos
  - Agent instructions and constraints
  - Bindings and metadata schemas
  - Entity/relationship templates
  - Data generation guidance
- **[Demo-automation](Demo-automation)** — CLI tool for automated Fabric setup and deployment
  - Automated 11-step setup workflow
  - State-based resume capability
  - Safe cleanup with audit trail
  - See [Demo-automation/README.md](Demo-automation/README.md) for details
- **[docs](docs)** — Consolidated documentation
- **demo-*** — generated demo folders (e.g., `demo-water_treatment_plant/`, `MedicalManufacturing/`)

## Output folder structure
Each generated demo follows a consistent structure:

```
demo-{scenario_name}/
├── ontology/
│   ├── {scenario_name}.ttl          # RDF/Turtle ontology definition with classes, relationships, and properties
│   ├── ontology.mmd                 # Mermaid ER diagram (fenced markdown block) for visualization
│   ├── ontology-structure.md        # Human-readable entity/relationship summary with binding notes
│   └── ontology-diagram-slide.html  # Interactive HTML presentation slide with embedded Mermaid diagram
├── data/
│   ├── data-dictionary.md           # CSV schema definitions for static, edge, and timeseries tables
│   ├── lakehouse/*.csv              # Static and edge data files (dimension and fact tables)
│   └── eventhouse/*.csv             # Timeseries data files with timestamp columns
├── bindings/
│   ├── lakehouse-binding-instructions.md    # Step-by-step guide for static data bindings (OneLake/Lakehouse)
│   └── eventhouse-binding-instructions.md   # Step-by-step guide for timeseries bindings (Eventhouse)
├── queries/
│   └── demo-questions.md            # 5+ sample questions with GQL traversals and expected insights
└── README.md                        # Demo overview, setup steps, constraints, and usage guidance
```

### File purposes
- **TTL file**: Formal ontology in Turtle format defining entity types, relationships, and data properties aligned to Fabric Ontology constraints (string/int keys, no Decimal types, property uniqueness).
- **Mermaid diagram**: Visual ER representation of the ontology for quick comprehension; can be rendered in VS Code with Mermaid extensions.
- **Ontology structure**: Plain markdown summary of entities, relationships, and binding mappings for reference.
- **HTML slide**: Interactive presentation slide with gradient styling, key metrics cards, embedded Mermaid diagram, and color-coded legend. Print-ready and suitable for stakeholder demos.
- **Data dictionary**: Detailed schemas for creating CSV files (≥50 rows each) with column names, types, foreign keys, and constraints.
- **Binding instructions**: Step-by-step workflows for configuring static (lakehouse) and timeseries (eventhouse) bindings in the Fabric Ontology preview UI.
- **Demo questions**: Example analytical queries demonstrating how the ontology enables traversals across heterogeneous data sources.
- **Demo README**: Quick-start guide with setup, bindings summary, constraints, and try-it instructions.

## Getting started

### Option 1: Automated Setup (Recommended)

Use the Demo-automation CLI tool for fully automated deployment:

1. **Clone this repo**:
   ```bash
   git clone https://github.com/falloutxAY/Fabric-Ontology-demoAgent.git
   cd Fabric-Ontology-demoAgent
   ```

2. **Install the automation tool**:
   ```bash
   cd Demo-automation
   pip install -e .
   ```

3. **Setup a demo** (e.g., CreditFraud):
   ```bash
   # Validate the demo package
   fabric-demo validate ../CreditFraud
   
   # Run automated setup (11 steps)
   fabric-demo setup ../CreditFraud --workspace-id <your-workspace-id>
   
   # Check status
   fabric-demo status ../CreditFraud
   ```

4. **Cleanup when done**:
   ```bash
   fabric-demo cleanup ../CreditFraud --confirm
   ```

See [Demo-automation/README.md](Demo-automation/README.md) for full documentation.

### Option 2: Generate New Demo with AI Agent

Use the `.agentic` folder specifications to prompt an AI agent:

1. **Clone this repo** (if not already done):
   ```bash
   git clone https://github.com/falloutxAY/Fabric-Ontology-demoAgent.git
   cd Fabric-Ontology-demoAgent
   ```

2. **Prompt an AI agent** with the `.agentic` folder context:
   ```
   Using #file:.agentic, create a demo for [your scenario, e.g., "water treatment plant"]
   ```
   
   The agent will follow a 7-phase incremental workflow:
   - **Discovery** → **Design** → **Ontology** → **Data** → **Bindings** → **Queries** → **README**
   - Each phase generates specific deliverables to avoid token limits

3. **Deploy using automation**:
   ```bash
   fabric-demo setup ./demo-<scenario-name> --workspace-id <your-workspace-id>
   ```

### Option 3: Manual Setup

For manual control or custom scenarios:

1. Generate demo assets using the `.agentic` specifications
2. Read `demo-{scenario_name}/README.md` for setup instructions
3. Upload TTL to Fabric Ontology using [rdf-fabric-ontology-converter](https://github.com/falloutxAY/rdf-fabric-ontology-converter)
4. Manually bind and map data based on bindings folder instructions
5. Use the HTML slide (`ontology-diagram-slide.html`) for stakeholder presentations
6. Use queries folder with Data Agent for interactive demos

**Note**: Generated demo folders (`demo-*/`) are excluded from version control by default via `.gitignore`. This keeps the repository focused on the agent spec and documentation. To track a specific demo, use `git add -f demo-<scenario-name>/`.

## Key features

### Demo Automation Tool
- **11-step automated setup**: Creates Lakehouse, Eventhouse, uploads data, loads tables, creates ontology, and configures all bindings
- **Resume capability**: State-based recovery from failures via `.setup-state.yaml`
- **Safe cleanup**: Only removes resources that were created by setup (tracked by ID)
- **Individual step execution**: Run specific steps independently for debugging or iteration
- **Validation**: Ensures demo packages meet all Fabric Ontology constraints

### AI Agent Specifications
- **7-phase workflow**: Incremental demo generation avoiding token limits
- **Constraint enforcement**: Aligns to all known Fabric Ontology limitations
- **Template-driven**: Consistent output structure across all generated demos
- **Schema validation**: Bindings and metadata follow documented schemas

## Troubleshooting

### Demo Automation Issues
- **"fabric-demo not recognized"**: See [Demo-automation/README.md](Demo-automation/README.md#troubleshooting-fabric-demo-not-recognized) for PATH setup
- **Resume after failure**: Use `fabric-demo setup <path> --resume` to continue from last successful step
- **Clear state and restart**: Use `fabric-demo setup <path> --clear-state` to start fresh
- **Cleanup safely**: Use `fabric-demo cleanup <path> --confirm` to remove only created resources

### AI Agent Generation
As this is based on an agent, the output is non-deterministic. Happy prompting!

## License
MIT — see `LICENSE`.
