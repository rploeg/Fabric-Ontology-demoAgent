# Fabric Ontology Demo Agent

An expert agent configuration for creating Microsoft Fabric Ontology demo scenarios with realistic sample data, bindings, and guidance. The core configuration lives in `.agentic/fabric-ontology-demo.yaml`, describing entities, relationships, bindings, validation checks, and deliverables.

## What's inside
- **.agentic/fabric-ontology-demo.yaml** — the agent spec covering capabilities, defaults, constraints, templates, known issues, and a 7-phase incremental workflow to generate demo assets (ontology structure, TTL, CSVs, bindings, HTML slides, queries, and docs) while avoiding token/length limits.
- **Docs** — project guidelines for contribution, conduct, and security reporting.
- **demo-*** — generated demo folders (e.g., `demo-water_treatment_plant/`, `demo-potash_mining/`, `MedicalManufacturing/`)

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
1) Clone this repo:
   - `git clone git@github.com:falloutxAY/Fabric-Ontology-demoAgent.git`
   - or `git clone https://github.com/falloutxAY/Fabric-Ontology-demoAgent.git`
2) (Optional) Inspect/update the agent spec: `.agentic/fabric-ontology-demo.yaml`.
3) Use the spec for an agent to generate your demo assets. Example: "Create a demo for a water treatment plant"
   - The agent will follow a 7-phase incremental workflow: Discovery → Design → Ontology → Data → Bindings → Queries → README
   - Each phase generates specific deliverables to avoid hitting token limits
4) Read demo-{scenario_name}/README.md for setup instructions
5) Upload TTL to Fabric Ontology using https://github.com/falloutxAY/rdf-fabric-ontology-converter
6) Bind and map data based on data and bindings folders
7) Use the HTML slide (ontology-diagram-slide.html) for stakeholder presentations
8) Use queries folder with Data Agent for interactive demos

**Note**: Generated demo folders (`demo-*/`) are excluded from version control by default via `.gitignore`. This keeps the repository focused on the agent spec and documentation. To track a specific demo, use `git add -f demo-<scenario-name>/`.

## Troubleshooting
As this is based on an agent, the output is non-deterministic. Happy prompting

## License
MIT — see `LICENSE`.
