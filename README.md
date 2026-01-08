# Fabric Ontology Demo Agent

Create and deploy Microsoft Fabric Ontology demos with automated tooling and AI agent specifications.

**[📚 Full Documentation →](docs/index.md)** | [CLI Reference](docs/cli-reference.md) | [Troubleshooting](docs/troubleshooting.md)

## Disclaimer
⚠️ Disclaimer: This is a personal project to learn about AI development and is not an official Microsoft product. It is not supported, endorsed, or maintained by Microsoft Corporation. Use at your own risk. see `LICENSE`.

## Project Structure

- **[.agentic](.agentic)** — AI agent specs for generating demos
- **[Demo-automation](Demo-automation)** — CLI tool ([docs](Demo-automation/README.md))
- **[docs](docs)** — Documentation
- **demo-*** — Generated demos (e.g., `AutoManufacturing-SupplyChain/`)


## Quick Start

1. git clone this repo and open folder in VS code.

2. Generating New Demos with github copilot

Use [.agentic](.agentic) specifications with any AI agent to create custom demos.

```
Using #file:.agentic, create a demo for "water treatment plant monitoring"
```

It will output to a folder. See [agent-workflow.md](docs/agent-workflow.md) for the process. 


3. Generate demo in Fabric Ontology

```bash
# Install dependencies
cd Demo-automation && pip install -e .

# Configure (one-time)
python -m demo_automation config init

# Validate the demo package
python -m demo_automation validate ../AutoManufacturing-SupplyChain

# Deploy generated demo to Fabric
python -m demo_automation setup ../AutoManufacturing-SupplyChain

# Cleanup
python -m demo_automation cleanup ../AutoManufacturing-SupplyChain
```

**[🚀 Full Setup Guide →](docs/index.md)** | **[Authentication Options →](docs/configuration.md#authentication-methods)**

## Manual Demo setup in Fabric Ontology

Generate demo assets using `.agentic` specifications, then follow the {demo}/README.md for setup instructions.

## License
MIT — see `LICENSE`.
