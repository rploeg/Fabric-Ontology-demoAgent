# CLI Reference

Complete reference for all `fabric-demo` commands.

---

## Global Options

These options work with any command:

| Option | Description |
|--------|-------------|
| `--help`, `-h` | Show help for command |
| `--debug` | Show full stack traces on error |
| `--version` | Show version information |

---

## Configuration Commands

### `fabric-demo config init`

Interactive wizard to create or update global configuration.

```bash
fabric-demo config init
```

Creates `~/.fabric-demo/config.yaml` with your default workspace ID and preferences.

### `fabric-demo config show`

Display current configuration with source indicators.

```bash
fabric-demo config show
```

Output shows where each value comes from (env, config file, or default).

### `fabric-demo config path`

Show the path to the global configuration file.

```bash
fabric-demo config path
# Output: ~/.fabric-demo/config.yaml
```

---

## Demo Commands

### `fabric-demo validate <path>`

Validate a demo package structure and contents.

```bash
fabric-demo validate ./MedicalManufacturing
```

Checks:
- Required folders exist (Ontology/, Data/, Bindings/)
- TTL file is valid
- CSV files are present
- bindings.yaml matches expected schema

### `fabric-demo setup <path>`

Run the complete 11-step setup workflow.

```bash
# Basic usage (uses config file for workspace ID)
fabric-demo setup ./MedicalManufacturing

# Specify workspace ID explicitly
fabric-demo setup ./MedicalManufacturing --workspace-id <guid>

# Preview without making changes
fabric-demo setup ./MedicalManufacturing --dry-run

# Resume from a failed run
fabric-demo setup ./MedicalManufacturing --resume

# Clear state and start fresh
fabric-demo setup ./MedicalManufacturing --clear-state
```

**Options:**

| Option | Description |
|--------|-------------|
| `--workspace-id` | Fabric workspace ID (overrides config) |
| `--tenant-id` | Azure AD tenant ID |
| `--dry-run` | Preview actions without executing |
| `--resume` | Continue from last successful step |
| `--clear-state` | Delete state file and start fresh |

### `fabric-demo status <path>`

Check the setup progress of a demo.

```bash
fabric-demo status ./MedicalManufacturing
```

Shows which steps have completed, failed, or are pending.

### `fabric-demo list`

List ontology-related resources in your workspace.

```bash
# List all resources
fabric-demo list

# Specify workspace
fabric-demo list --workspace-id <guid>
```

### `fabric-demo cleanup <path>`

Remove resources created by the setup command.

```bash
# Interactive confirmation (default)
fabric-demo cleanup ./MedicalManufacturing

# Skip confirmation
fabric-demo cleanup ./MedicalManufacturing --confirm

# Skip confirmation with -y shorthand
fabric-demo cleanup ./MedicalManufacturing -y

# Cleanup by name (when state file is missing)
fabric-demo cleanup ./MedicalManufacturing --force-by-name
```

**Options:**

| Option | Description |
|--------|-------------|
| `--confirm`, `-y` | Skip interactive confirmation |
| `--force-by-name` | Delete by resource name (fallback when state file lost) |
| `--dry-run` | Preview what would be deleted |

**Safety Features:**
- Only deletes resources tracked in `.setup-state.yaml` by ID
- Pre-existing resources with matching names are NOT deleted
- State file preserved with `cleaned_up` status for audit trail

---

## Advanced Commands

### `fabric-demo run-step <path> --step <n>`

Execute a single step from the workflow.

```bash
# Run by step number
fabric-demo run-step ./MedicalManufacturing --step 2

# Run by step name
fabric-demo run-step ./MedicalManufacturing --step create_lakehouse

# Force re-run of completed step
fabric-demo run-step ./MedicalManufacturing --step 8 --force
```

**Available Steps:**

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

### `fabric-demo init <path>`

Create a `demo.yaml` template in a folder.

```bash
fabric-demo init ./MyNewDemo
```

### `fabric-demo docs`

Open documentation in your browser.

```bash
fabric-demo docs
```

### `fabric-demo recover <path>`

Rebuild the state file from existing Fabric resources.

```bash
# Recover state for a demo
fabric-demo recover ./MedicalManufacturing

# Specify workspace
fabric-demo recover ./MedicalManufacturing --workspace-id <guid>

# Overwrite existing state file
fabric-demo recover ./MedicalManufacturing --force
```

**Options:**

| Option | Description |
|--------|-------------|
| `--workspace-id`, `-w` | Fabric workspace ID |
| `--force`, `-f` | Overwrite existing state file |

**Use when:**
- State file (.setup-state.yaml) is lost or corrupted
- You manually deleted the state file but resources still exist
- You need to enable cleanup for resources created outside the tool

The command searches for resources matching the demo naming convention (prefixed with demo name) and recreates the state file.

---

## Examples

### Complete Workflow

```bash
# One-time setup
fabric-demo config init

# Deploy a demo
fabric-demo validate ./MedicalManufacturing
fabric-demo setup ./MedicalManufacturing

# Check progress
fabric-demo status ./MedicalManufacturing

# Cleanup when done
fabric-demo cleanup ./MedicalManufacturing
```

### Recovery from Failure

```bash
# If setup fails mid-way
fabric-demo setup ./MedicalManufacturing --resume

# If you need to start fresh
fabric-demo setup ./MedicalManufacturing --clear-state

# If state file is corrupted/deleted but resources exist
fabric-demo recover ./MedicalManufacturing

# If state file is lost, cleanup by resource name
fabric-demo cleanup ./MedicalManufacturing --force-by-name
```

### Debugging

```bash
# See exactly what would happen
fabric-demo setup ./MedicalManufacturing --dry-run

# Run a specific step
fabric-demo run-step ./MedicalManufacturing --step bind_static

# Force re-run a step
fabric-demo run-step ./MedicalManufacturing --step 8 --force

# Show full error details
fabric-demo setup ./MedicalManufacturing --debug
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Validation error |
| 3 | Authentication error |
| 4 | Resource not found |
| 5 | User cancelled |

---

## See Also

- [Configuration Guide](configuration.md) - All configuration options
- [Troubleshooting](troubleshooting.md) - Common issues and fixes
