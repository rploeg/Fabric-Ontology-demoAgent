# CLI Reference

Complete reference for the demo automation CLI.

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

### `config init`

Interactive wizard to create or update global configuration.

```bash
python -m demo_automation config init
```

Creates `~/.fabric-demo/config.yaml` with your default workspace ID and preferences.

### `config show`

Display current configuration with source indicators.

```bash
python -m demo_automation config show
```

Output shows where each value comes from (env, config file, or default).

### `config path`

Show the path to the global configuration file.

```bash
python -m demo_automation config path
# Output: ~/.fabric-demo/config.yaml
```

---

## Demo Commands

### `validate <path>`

Validate a demo package structure and contents.

```bash
python -m demo_automation validate ./MedicalManufacturing
```

Checks:
- Required folders exist (Ontology/, Data/, Bindings/)
- TTL file is valid
- CSV files are present
- bindings.yaml matches expected schema

### `setup <path>`

Run the complete 11-step setup workflow.

```bash
python -m demo_automation setup ./MedicalManufacturing [--workspace-id <guid>] [--dry-run] [--resume] [--clear-state]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--workspace-id` | Fabric workspace ID (overrides config) |
| `--tenant-id` | Azure AD tenant ID |
| `--dry-run` | Preview actions without executing |
| `--resume` | Continue from last successful step |
| `--clear-state` | Delete state file and start fresh |

### `status <path>`

Check the setup progress of a demo.

```bash
python -m demo_automation status ./MedicalManufacturing
```

Shows which steps have completed, failed, or are pending.

### `list`

List ontology-related resources in your workspace.

```bash
# List all resources
python -m demo_automation list

# Specify workspace
python -m demo_automation list --workspace-id <guid>
```

### `cleanup <path>`

Remove resources created by the setup command.

```bash
python -m demo_automation cleanup ./MedicalManufacturing [--confirm|-y] [--force-by-name] [--dry-run]
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

### `run-step <path> --step <n>`

Execute a single step from the workflow.

```bash
# Run by step number
python -m demo_automation run-step ./MedicalManufacturing --step 2

# Run by step name
python -m demo_automation run-step ./MedicalManufacturing --step create_lakehouse

# Force re-run of completed step
python -m demo_automation run-step ./MedicalManufacturing --step 8 --force
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

### `init <path>`

Create a `demo.yaml` template in a folder.

```bash
python -m demo_automation init ./MyNewDemo
```

### `docs`

Open documentation in your browser.

```bash
python -m demo_automation docs
```

### `recover <path>`

Rebuild the state file from existing Fabric resources.

```bash
# Recover state for a demo
python -m demo_automation recover ./MedicalManufacturing

# Specify workspace
python -m demo_automation recover ./MedicalManufacturing --workspace-id <guid>

# Overwrite existing state file
python -m demo_automation recover ./MedicalManufacturing --force
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
