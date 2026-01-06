# Fabric Demo Automation Tool

Automates the setup of Fabric Ontology demos by creating all required resources in Microsoft Fabric.

## Features

- **Auto-discovery**: Reads folder structure, no manual mapping needed
- **Idempotent**: Safe to re-run, skips completed work
- **Resumable**: Continues from last successful step after failures
- **Simple**: One unified client, minimal configuration

## Installation

```bash
# From the fabric-demo directory
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Prerequisites

### Authentication

The tool uses `DefaultAzureCredential` from Azure Identity, which supports multiple authentication methods:

1. **Azure CLI** (local development): Run `az login` first
2. **Managed Identity** (Azure VMs/containers)
3. **Service Principal** (CI/CD): Set environment variables:
   - `AZURE_TENANT_ID`
   - `AZURE_CLIENT_ID`
   - `AZURE_CLIENT_SECRET`

### Required Permissions

- **Fabric Workspace**: Contributor role on target workspace
- **OneLake**: Storage Blob Data Contributor on workspace OneLake
- **Ontology**: Ontology.ReadWrite.All (or workspace Contributor)

## Usage

### Validate Demo Package

Check the demo package structure without making any API calls:

```bash
fabric-demo validate MedicalManufacturing/
```

Output:
```
✅ Demo package valid: MedicalManufacturing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Path: /path/to/MedicalManufacturing
   Lakehouse CSVs: 9
     • DimComponent.csv
     • DimFacility.csv
     ...
   Eventhouse CSVs: 2
     • BatchTelemetry.csv
     • FacilityTelemetry.csv
   TTL file: bd-medical-manufacturing.ttl
   Lakehouse bindings: 9
     • Product → DimProduct
     ...
   Eventhouse bindings: 2
     • BatchTelemetry → BatchTelemetry
     ...
```

### Setup Demo

Create all resources in Fabric:

```bash
fabric-demo setup MedicalManufacturing/ --workspace <workspace-id>
```

Output:
```
📦 Setting up: MedicalManufacturing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ⏳ create_lakehouse... ✅
  ⏳ upload_DimProduct... ✅
  ⏳ upload_DimFacility... ✅
  ...
  ⏳ create_ontology... ✅
  ⏳ bind_ontology... ✅
  ⏳ refresh_graph... ✅

══════════════════════════════════════════════════
✅ Setup complete!
══════════════════════════════════════════════════

Resources created:
  lakehouse_id: lh-abc123
  eventhouse_id: eh-def456
  ontology_id: ont-ghi789
```

### Force Restart

To start fresh, ignoring previous state:

```bash
fabric-demo setup MedicalManufacturing/ --workspace <workspace-id> --force
```

### Check Status

View the current setup status:

```bash
fabric-demo status MedicalManufacturing/
```

### Cleanup Resources

Remove all resources created by setup:

```bash
fabric-demo cleanup MedicalManufacturing/ --workspace <workspace-id>

# Skip confirmation prompt
fabric-demo cleanup MedicalManufacturing/ --workspace <workspace-id> --yes
```

## Demo Package Structure

The tool expects the following folder structure:

```
MedicalManufacturing/
├── data/
│   ├── lakehouse/          # Static dimensional data
│   │   ├── DimProduct.csv
│   │   ├── DimFacility.csv
│   │   └── Fact*.csv
│   └── eventhouse/         # Timeseries data
│       ├── BatchTelemetry.csv
│       └── FacilityTelemetry.csv
├── ontology/
│   └── bd-medical-manufacturing.ttl
├── bindings/
│   ├── lakehouse-binding.md
│   └── eventhouse-binding.md
└── queries/
    └── demo-questions.md
```

## Binding Markdown Format

The binding files define how ontology entities map to data tables:

```markdown
# Lakehouse Bindings

## Entity: Product (ID: 1000000000001)
**Table:** DimProduct

| Property | Column | Key |
|----------|--------|-----|
| productId | ProductId | Yes |
| name | ProductName | No |
| category | Category | No |

## Entity: Facility (ID: 1000000000002)
**Table:** DimFacility

| Property | Column | Key |
|----------|--------|-----|
| facilityId | FacilityId | Yes |
| name | FacilityName | No |
| location | Location | No |
```

## State Management

The tool creates a `.state.json` file in the demo folder to track progress:

```json
{
  "run_id": "setup-20260105-143022",
  "workspace_id": "12345678-...",
  "status": "in_progress",
  "completed": [
    "create_lakehouse",
    "upload_DimProduct",
    "load_DimProduct"
  ],
  "resources": {
    "lakehouse_id": "lh-abc123",
    "eventhouse_id": null,
    "ontology_id": null
  }
}
```

This enables resuming from the last successful step after failures.

## Error Handling

The tool includes automatic retry logic for transient errors:

- **429 (Rate Limited)**: Waits per `Retry-After` header
- **5xx (Server Errors)**: Exponential backoff with up to 3 retries
- **4xx (Client Errors)**: Fails immediately (except 429)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/

# Lint
ruff src/
```

## License

MIT
