# Fabric Ontology Demo Generator

> **Get a working Fabric Ontology demo running in under 5 minutes**

This project provides everything you need to create and deploy Microsoft Fabric Ontology demos—automated tooling, AI agent specifications, and complete demo packages.

---

## ⚡ Quick Start

**Prerequisites**: Python 3.10+, Microsoft Fabric workspace with Ontology enabled

```bash
# Install
git clone https://github.com/falloutxAY/Fabric-Ontology-demoAgent.git
cd Fabric-Ontology-demoAgent/Demo-automation
pip install -e .

# Configure workspace
python -m demo_automation config init

# Deploy demo
python -m demo_automation setup ../FreshMart

# Cleanup when done
python -m demo_automation cleanup ../FreshMart
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
python -m demo_automation setup ./MedicalManufacturing --workspace-id <your-id>
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

`.agentic/` - AI agent specs • `Demo-automation/` - CLI tool • `docs/` - Documentation • `demo-*/` - Generated demos

---

## 🔗 Useful Links

- [Microsoft Fabric Ontology Documentation](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/ontology-overview)
- [RDF to Fabric Ontology Converter](https://github.com/falloutxAY/rdf-fabric-ontology-converter)
- [Project GitHub Repository](https://github.com/falloutxAY/Fabric-Ontology-demoAgent)

---

## 📝 License

MIT — see [LICENSE](../LICENSE).
