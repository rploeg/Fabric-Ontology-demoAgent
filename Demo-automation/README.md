# Fabric Demo Automation

Automated setup tool for Microsoft Fabric Ontology demos. This CLI tool orchestrates the complete demo setup process with **11 sequential steps**, each independently executable with built-in resume capability.

## Setup Workflow

The tool executes the following steps in order:

| Step | Description | Validation |
|------|-------------|------------|
| 1. **Validate** | Verify demo folder structure matches `fabric-ontology-demo-v2.yaml` spec | ✓ Structure & files |
| 2. **Create Lakehouse** | Create Lakehouse in Fabric workspace | ✓ Resource exists |
| 3. **Upload Files** | Upload `data/lakehouse/*.csv` files to Lakehouse | ✓ Files uploaded |
| 4. **Load Tables** | Convert CSV files to managed Delta tables | ✓ Tables created |
| 5. **Create Eventhouse** | Create Eventhouse with KQL Database | ✓ Resource exists |
| 6. **Ingest Data** | Upload `data/eventhouse/*.csv` and ingest to KQL tables | ✓ Tables have data |
| 7. **Create Ontology** | Create ontology from TTL file with entities, properties, keys | ✓ Definition uploaded |
| 8. **Bind Static** | Bind lakehouse properties (static/NonTimeSeries) with keyColumn | ✓ Static bindings configured |
| 9. **Bind TimeSeries** | Bind eventhouse properties (timeseries) per bindings.yaml | ✓ Timeseries bindings configured |
| 10. **Bind Relationships** | Bind relationship contextualizations per bindings.yaml | ✓ Relationship bindings configured |
| 11. **Verify Setup** | Comprehensive verification of all resources and bindings in Fabric | ✓ All checks passed |

## Features

- **Auto-discovery**: Reads demo structure from folder conventions
- **Structured bindings**: Parses `bindings.yaml` (v3.2+) for machine-readable configuration
- **Validation**: Ensures demo packages match generator constraints and limitations
- **Hybrid configuration**: YAML config with environment variable support
- **Resume capability**: State persistence via `.setup-state.yaml` for failure recovery
- **Individual step execution**: Run any step independently via `run-step` command
- **Smart skipping**: Automatically skips resources/tables that already exist
- **Progress reporting**: Real-time progress with rich terminal output
- **Constraint adherence**: Respects all Fabric Graph/Ontology limitations

## Installation

```bash
# Navigate to the Demo-automation folder first
cd Demo-automation

# Install in development mode (creates 'fabric-demo' command)
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
fabric-demo --help
```

### Troubleshooting: "fabric-demo not recognized"

If you get the error `fabric-demo: The term 'fabric-demo' is not recognized`, the Python Scripts folder is not in your PATH.

**Option 1: Add Python Scripts to PATH (Recommended)**

```powershell
# Find where the script was installed (look for the WARNING during pip install)
# Usually: C:\Users\<username>\AppData\Roaming\Python\Python3xx\Scripts

# Add to PATH for current session
$env:PATH += ";$env:APPDATA\Python\Python314\Scripts"

# Or add permanently (run as admin or via System Properties > Environment Variables)
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";$env:APPDATA\Python\Python314\Scripts", "User")
```

**Option 2: Run with Full Path**

```powershell
# Windows (adjust Python version as needed)
& "$env:APPDATA\Python\Python314\Scripts\fabric-demo.exe" --help
& "$env:APPDATA\Python\Python314\Scripts\fabric-demo.exe" setup ./PillManufacturing
```

**Option 3: Run as Python Module**

```bash
# From the Demo-automation folder
python -m demo_automation.cli --help
python -m demo_automation.cli validate ../MedicalManufacturing
python -m demo_automation.cli setup ../PillManufacturing --workspace-id <id>
```

**Option 4: Use pip-installed location**

```bash
# Check where pip installs scripts
python -m site --user-base
# Append /Scripts (Windows) or /bin (Linux/Mac) to that path
```

## Quick Start

```bash
# Initialize a demo configuration
fabric-demo init ./MedicalManufacturing

# Validate demo package
fabric-demo validate ./MedicalManufacturing

# Run full setup
fabric-demo setup ./MedicalManufacturing --workspace-id <your-workspace-id>

# Run with dry-run to preview actions
fabric-demo setup ./MedicalManufacturing --dry-run

# Resume from a failed step
fabric-demo setup ./MedicalManufacturing --resume

# Clear state and start fresh
fabric-demo setup ./MedicalManufacturing --clear-state

# Check status (shows 11-step progress)
fabric-demo status ./MedicalManufacturing

# Cleanup resources
fabric-demo cleanup ./MedicalManufacturing --confirm
```

## Running Individual Steps

Each step can be executed independently using the `run-step` command:

```bash
# Run a step by number (1-11)
fabric-demo run-step ./MedicalManufacturing --step 2  # Create Lakehouse
fabric-demo run-step ./MedicalManufacturing --step 8  # Bind static properties

# Run a step by name
fabric-demo run-step ./MedicalManufacturing --step create_lakehouse
fabric-demo run-step ./MedicalManufacturing --step bind_static
fabric-demo run-step ./MedicalManufacturing --step verify

# Force re-run of a completed step
fabric-demo run-step ./MedicalManufacturing --step 8 --force
```

**Available steps:**
| # | Name | Description |
|---|------|-------------|
| 1 | `validate` | Validate demo folder structure |
| 2 | `create_lakehouse` | Create Lakehouse resource |
| 3 | `upload_files` | Upload CSV files to Lakehouse |
| 4 | `load_tables` | Load CSV files into Delta tables |
| 5 | `create_eventhouse` | Create Eventhouse resource |
| 6 | `ingest_data` | Upload and ingest eventhouse data |
| 7 | `create_ontology` | Create ontology with entities |
| 8 | `bind_static` | Bind lakehouse properties (static) |
| 9 | `bind_timeseries` | Bind eventhouse properties (timeseries) |
| 10 | `bind_relationships` | Bind relationship contextualizations |
| 11 | `verify` | Verify all resources and bindings |

## Configuration

### Environment Variables

```bash
# Required
FABRIC_WORKSPACE_ID=<your-workspace-guid>

# Optional
AZURE_TENANT_ID=<your-tenant-id>
```

### Demo Configuration (demo.yaml)

```yaml
demo:
  name: MedicalManufacturing
  description: "Medical manufacturing ontology demonstration"

fabric:
  workspace_id: ${FABRIC_WORKSPACE_ID}

options:
  skip_existing: true
  dry_run: false
```

## Demo Package Structure

```
DemoName/
├── demo.yaml                    # Configuration (optional - auto-generated)
├── .demo-metadata.yaml          # Version info (auto-generated)
├── .setup-state.yaml            # Resume state (auto-generated, gitignored)
├── ontology/
│   ├── *.ttl                    # Ontology definition (RDF/Turtle)
│   └── ontology-structure.md    # Human-readable structure docs
├── data/
│   ├── lakehouse/*.csv          # Static data → Delta tables
│   └── eventhouse/*.csv         # Timeseries data → KQL tables
├── bindings/
│   ├── bindings.yaml            # Machine-readable bindings (v3.2+, preferred)
│   ├── lakehouse-binding.md     # Human-readable static binding instructions
│   └── eventhouse-binding.md    # Human-readable timeseries instructions
├── queries/
│   └── demo-questions.md        # Demo GQL queries
└── README.md
```

## Bindings Configuration (v3.2+)

The `bindings/bindings.yaml` file is the **source of truth** for automation:

```yaml
version: "1.0"
generatedBy: "fabric-ontology-demo-v3.2"

lakehouse:
  entities:
    - entity: Product
      sourceTable: DimProduct
      keyColumn: ProductId
      properties:
        - property: ProductId
          column: ProductId
          type: string
        - property: Product_Name
          column: Product_Name
          type: string

  relationships:
    - relationship: produces
      sourceEntity: Facility
      targetEntity: ProductionBatch
      sourceTable: DimProductionBatch
      sourceKeyColumn: FacilityId
      targetKeyColumn: BatchId

eventhouse:
  entities:
    - entity: ProductionBatch
      sourceTable: BatchTelemetry
      keyColumn: BatchId
      timestampColumn: Timestamp
      properties:
        - property: Batch_Temperature
          column: Temperature
          type: double
```

## Constraints Enforced

Based on `fabric-ontology-demo-v2.yaml` and known Fabric limitations:

| Constraint | Enforcement |
|------------|-------------|
| Property types | `string`, `int`, `double`, `boolean`, `datetime` only |
| Entity key types | `string` or `int` only (no datetime/boolean) |
| Property name length | Max 26 characters |
| Static before timeseries | Lakehouse bindings created before Eventhouse |
| OneLake only for static | Uses `LakehouseTable` source type |
| Managed tables only | No shortcuts, views, or external tables |
| **Lakehouse schemas disabled** | Lakehouses must NOT have "Lakehouse schemas (Public Preview)" enabled |
| **sourceSchema: null** | Relationship contextualizations use `null` for lakehouses without schemas |

## Resume & Error Handling

- **On success**: Each step marks completion in `.setup-state.yaml`
- **On failure**: Stops immediately and outputs error; state preserved for resume
- **Resume**: Use `--resume` flag to continue from last successful step
- **Fresh start**: Use `--clear-state` to remove state and start over

## Cleanup Command

The `cleanup` command safely removes only the resources that were created by the setup process:

```bash
# Preview what will be deleted (dry run)
fabric-demo cleanup ./MedicalManufacturing

# Actually delete resources
fabric-demo cleanup ./MedicalManufacturing --confirm
```

**Safety features:**
- **State-based deletion**: Only deletes resources tracked in `.setup-state.yaml` by their IDs
- **No accidental deletion**: Pre-existing resources with matching names are NOT deleted
- **Audit trail**: After cleanup, the state file is preserved with status `cleaned_up`
- **Idempotent**: Running cleanup again shows "No resources recorded" since IDs are cleared

**What gets deleted:**
1. Ontology (deleted first, as it depends on data sources)
2. Eventhouse (includes KQL database)
3. Lakehouse

**What is NOT deleted:**
- The demo folder and its files
- Resources not created by this tool
- The `.setup-state.yaml` file (updated to `cleaned_up` status)

### Troubleshooting: "An error occurred while loading the columns"

If you see this error when viewing relationship bindings in the Fabric UI:

1. **Check Lakehouse schemas**: Ensure the Lakehouse was created WITHOUT "Lakehouse schemas (Public Preview)" enabled
2. **Re-run bindings**: Use `fabric-demo run-step --step bind_relationships --force <demo-path>`
3. **Verify OneLake security**: Ensure OneLake folder-level security is disabled

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Demo Automation Orchestrator                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ StateManager │  │  Validator   │  │   BindingsParser       │ │
│  │ (.yaml)      │  │ (structure)  │  │ (YAML + MD fallback)   │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                        Step Executors                            │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ LakehouseClient │  │ EventhouseClient │  │ FabricClient   │ │
│  │   - Create      │  │   - Create       │  │   - Ontology   │ │
│  │   - Upload CSV  │  │   - KQL Tables   │  │   - Bindings   │ │
│  │   - Load Tables │  │   - Ingest Data  │  │   - Definition │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              OntologyBindingBuilder                       │  │
│  │   - Lakehouse (Static) bindings                          │  │
│  │   - Eventhouse (TimeSeries) bindings                     │  │
│  │   - Relationship contextualizations                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## License

MIT License
