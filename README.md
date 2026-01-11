# Fabric Ontology Demo Agent

Create and deploy Microsoft Fabric Ontology demos with automated tooling and AI agent specifications.

**[📚 Full Documentation →](docs/index.md)** | [CLI Reference](docs/cli-reference.md) | [Troubleshooting](docs/troubleshooting.md)

## Disclaimer

⚠️ This is a personal project to learn about AI development and is not an official Microsoft product. It is not supported, endorsed, or maintained by Microsoft Corporation. Use at your own risk. See `LICENSE`.

## Prerequisites

- Python 3.10+
- Microsoft Fabric workspace with Ontology preview enabled
- Azure authentication (interactive or service principal)

## Project Structure

```
├── .agentic/              # AI agent specs for generating demos
│   ├── agent-instructions.md       # 7-phase workflow guide
│   ├── schemas/
│   │   ├── validation-rules.yaml   # Validation rules (source of truth)
│   │   ├── bindings-schema.yaml    # Bindings file schema
│   │   └── metadata-schema.yaml    # Metadata file schema
│   └── templates/                  # Output templates
├── Demo-automation/       # CLI tool (uses Unofficial Fabric Ontology SDK v0.3.0)
├── docs/                  # Documentation
├── AutoManufacturing-SupplyChain/  # Example demo
└── FreshMart/             # Example demo
```

## Quick Start

### 1. Clone and Open

```bash
git clone https://github.com/falloutxAY/Fabric-Ontology-demoAgent.git
cd Fabric-Ontology-demoAgent
```

### 2. Generate New Demos with AI

Use [.agentic](.agentic) specifications with any AI agent to create custom demos:

```
Using #file:.agentic, create a demo for "Car manufacturing, add supply chain"
```

See [agent-workflow.md](docs/agent-workflow.md) for the generation process.

### 3. Deploy to Fabric

```bash
# Install CLI tool
cd Demo-automation && pip install -e .

# Configure workspace (one-time)
python -m demo_automation config init

# Validate and deploy
python -m demo_automation validate ../AutoManufacturing-SupplyChain
python -m demo_automation setup ../AutoManufacturing-SupplyChain

# Cleanup when done
python -m demo_automation cleanup ../AutoManufacturing-SupplyChain
```

**[🚀 Full Setup Guide →](docs/index.md)** | **[Authentication Options →](docs/configuration.md#authentication-methods)**

## License

MIT — see `LICENSE`.
