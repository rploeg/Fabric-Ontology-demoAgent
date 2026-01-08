# Fabric Ontology Demo Agent

Create and deploy Microsoft Fabric Ontology demos with automated tooling and AI agent specifications.

**[📚 Full Documentation →](docs/index.md)** | [CLI Reference](docs/cli-reference.md) | [Troubleshooting](docs/troubleshooting.md)

## Disclaimer
⚠️ Disclaimer: This is a personal project to learn about AI development and is not an official Microsoft product. It is not supported, endorsed, or maintained by Microsoft Corporation. Use at your own risk. see `LICENSE`.

## Project Structure

- **[.agentic](.agentic)** — AI agent specs for generating demos
- **[Demo-automation](Demo-automation)** — CLI tool ([docs](Demo-automation/README.md))
- **[docs](docs)** — Documentation
- **demo-*** — Generated demos (e.g., `FreshMart/`, `MedicalManufacturing/`)

## Demo Structure

```
demo-{name}/
├── Ontology/          # .ttl, diagrams, structure docs
├── Data/              # Lakehouse/*.csv, Eventhouse/*.csv
├── Bindings/          # Setup instructions + bindings.yaml
└── demo-questions.md  # Sample GQL queries
```

See [agent-workflow.md](docs/agent-workflow.md) for details.

## Generating New Demos

Use [.agentic](.agentic) specifications with any AI agent to create custom demos. It will output to a folder. See [agent-workflow.md](docs/agent-workflow.md) for the 7-phase process. 

Proceed to generate demo in Fabric Ontology based on it

## Quick Start - Generate demo in Fabric Ontology

```bash
# Install
cd Demo-automation && pip install -e .

# Configure (one-time)
python -m demo_automation config init

# Deploy a demo
python -m demo_automation setup ../FreshMart

# Cleanup
python -m demo_automation cleanup ../FreshMart
```

**[🚀 Full Setup Guide →](docs/index.md)** | **[Authentication Options →](docs/configuration.md#authentication-methods)**

## Manual Setup

For custom scenarios, generate demo assets using `.agentic` specifications, then follow the demo's README for setup instructions.

**Note**: Generated demo folders (`demo-*/`) are excluded from version control via `.gitignore`.

## Key Features

- **11-step automated setup** with resume capability
- **Safe cleanup** (only removes tracked resources)
- **Individual step execution** for debugging
- **Validation** for Fabric Ontology constraints

## License
MIT — see `LICENSE`.
