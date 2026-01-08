# Fabric Ontology Demo Generator

> **Get a working Fabric Ontology demo running in under 5 minutes**

This project provides everything you need to create and deploy Microsoft Fabric Ontology demos—automated tooling, AI agent specifications, and complete demo packages.

---

## ⚡ Quick Start (5 Minutes)

### Prerequisites

- Python 3.10+
- A Microsoft Fabric workspace with Ontology preview enabled
- Your workspace ID (GUID from Fabric portal URL)

### Step 1: Install the Tool

```bash
git clone https://github.com/falloutxAY/Fabric-Ontology-demoAgent.git
cd Fabric-Ontology-demoAgent/Demo-automation
pip install -e .
```

### Step 2: Configure Your Workspace

```bash
fabric-demo config init
```

This interactive wizard saves your workspace ID to `~/.fabric-demo/config.yaml` so you don't need to type it every time.

### Step 3: Deploy a Demo

```bash
# Validate the demo package
fabric-demo validate ../MedicalManufacturing

# Run the 11-step automated setup
fabric-demo setup ../MedicalManufacturing
```

The tool will:
1. Create a Lakehouse and Eventhouse
2. Upload and load all CSV data
3. Create the ontology with entities, properties, and relationships
4. Configure all data bindings automatically
5. Verify everything is working

### Step 4: Try It Out

1. Open your Fabric workspace in the browser
2. Find the newly created ontology
3. Run the sample queries from `demo-questions.md`

### Step 5: Cleanup When Done

```bash
fabric-demo cleanup ../MedicalManufacturing
```

---

## 📖 Documentation

| Guide | Description |
|-------|-------------|
| [CLI Reference](cli-reference.md) | Complete command documentation |
| [Configuration](configuration.md) | All configuration options explained |
| [Troubleshooting](troubleshooting.md) | Common issues and fixes |
| [Agent Workflow](agent-workflow.md) | Generate new demos with AI agents |
| [Architecture](architecture.md) | System design for contributors |

---

## 🛠️ Three Ways to Use This Project

### 1. Deploy Existing Demos (Fastest)

Use pre-built demo packages with the automation tool:

```bash
fabric-demo setup ./MedicalManufacturing --workspace-id <your-id>
```

### 2. Generate New Demos with AI (Flexible)

Use the `.agentic/` specifications to prompt any AI agent:

```
Using #file:.agentic, create a demo for "water treatment plant"
```

The agent follows a 7-phase workflow to generate all artifacts.

### 3. Manual Setup (Full Control)

For custom scenarios or learning:
1. Generate demo assets using `.agentic/` specifications
2. Upload TTL using [rdf-fabric-ontology-converter](https://github.com/falloutxAY/rdf-fabric-ontology-converter)
3. Follow binding instructions in `Bindings/` folder

---

## 📁 Project Structure

```
Fabric-Ontology-demoAgent/
├── .agentic/                  # AI agent specifications
│   ├── agent-instructions.md  # 7-phase generation workflow
│   ├── schemas/               # Bindings and metadata schemas
│   └── templates/             # Output templates
├── Demo-automation/           # CLI tool source code
│   ├── src/demo_automation/   # Python modules
│   └── README.md              # Detailed CLI documentation
├── docs/                      # This documentation folder
└── demo-*/                    # Generated demo packages (gitignored)
```

---

## 🔗 Useful Links

- [Microsoft Fabric Ontology Documentation](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/ontology-overview)
- [RDF to Fabric Ontology Converter](https://github.com/falloutxAY/rdf-fabric-ontology-converter)
- [Project GitHub Repository](https://github.com/falloutxAY/Fabric-Ontology-demoAgent)

---

## 📝 License

MIT — see [LICENSE](../LICENSE).
