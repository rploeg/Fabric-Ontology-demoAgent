# Troubleshooting Guide

Solutions to common issues with the `fabric-demo` tool.

---

## Installation Issues

### "fabric-demo: The term 'fabric-demo' is not recognized"

The Python Scripts folder is not in your PATH.

**Option 1: Add to PATH (Recommended)**

```powershell
# Find install location (shown during pip install)
# Usually: C:\Users\<username>\AppData\Roaming\Python\Python3xx\Scripts

# Add to PATH for current session
$env:PATH += ";$env:APPDATA\Python\Python314\Scripts"

# Add permanently (restart terminal after)
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";$env:APPDATA\Python\Python314\Scripts", "User")
```

**Option 2: Run as Python Module**

```bash
cd Demo-automation
python -m demo_automation.cli --help
python -m demo_automation.cli setup ../MedicalManufacturing
```

**Option 3: Use Full Path**

```powershell
& "$env:APPDATA\Python\Python314\Scripts\fabric-demo.exe" --help
```

### "No module named 'demo_automation'"

Install the package in development mode:

```bash
cd Demo-automation
pip install -e .
```

---

## Authentication Issues

### "Failed to acquire token"

**Cause**: Azure authentication failed.

**Solutions**:

1. **Interactive auth**: Ensure your browser opens and you complete login
2. **Service principal**: Verify environment variables are set:
   ```bash
   echo $AZURE_TENANT_ID
   echo $AZURE_CLIENT_ID
   echo $AZURE_CLIENT_SECRET
   ```
3. **Network**: Check you can reach `https://login.microsoftonline.com`

### "AADSTS50076: Multi-factor authentication required"

Your organization requires MFA. Use interactive authentication:

```yaml
# ~/.fabric-demo/config.yaml
defaults:
  auth_method: interactive
```

### "AADSTS700016: Application not found"

The service principal client ID is incorrect. Verify `AZURE_CLIENT_ID`.

---

## Setup Issues

### "Workspace not found" or "403 Forbidden"

**Causes**:
- Workspace ID is incorrect
- You don't have access to the workspace
- The workspace doesn't have Ontology preview enabled

**Solutions**:

1. Verify workspace ID from Fabric portal URL:
   ```
   https://app.fabric.microsoft.com/groups/YOUR-WORKSPACE-ID/...
   ```

2. Check your access permissions in Fabric

3. Ensure Ontology preview is enabled for your tenant

### "Resource already exists"

By default, the tool skips existing resources. If you want to fail instead:

```yaml
# demo.yaml
options:
  skip_existing: false
```

Or delete existing resources first:

```bash
fabric-demo cleanup ./MedicalManufacturing --confirm
```

### "Rate limit exceeded" / 429 Error

The Fabric API is throttling requests.

**Solutions**:

1. Wait and retry - the tool has automatic retry logic

2. Reduce rate limit settings:
   ```yaml
   rate_limiting:
     requests_per_minute: 20
     burst: 5
   ```

3. Wait a few minutes for your quota to reset

### Setup Fails Mid-Way

Use resume to continue from where you left off:

```bash
fabric-demo setup ./MedicalManufacturing --resume
```

If you want to start fresh:

```bash
fabric-demo setup ./MedicalManufacturing --clear-state
```

---

## Binding Issues

### "An error occurred while loading the columns"

When viewing relationship bindings in Fabric UI.

**Cause**: Lakehouse was created with "Lakehouse schemas (Public Preview)" enabled.

**Solutions**:

1. Delete the Lakehouse and recreate without schemas enabled
2. Or use a different workspace with schemas disabled

### "Property not found" in binding step

**Causes**:
- Property name in bindings.yaml doesn't match TTL
- Column name doesn't exist in CSV/table

**Solutions**:

1. Verify property names in `Ontology/*.ttl` match `bindings.yaml`
2. Check column names in `Data/Lakehouse/*.csv` files
3. Re-run validation: `fabric-demo validate ./MedicalManufacturing`

### "Entity key column not found"

**Cause**: The `keyColumn` in bindings.yaml doesn't match the actual table column.

**Solution**: Check `bindings.yaml` and ensure `keyColumn` matches CSV header exactly (case-sensitive).

---

## Cleanup Issues

### "No resources to clean up"

**Causes**:
- Setup was never run
- State file is missing or corrupted
- Resources were already cleaned up

**Solutions**:

1. Check if state file exists:
   ```bash
   cat ./MedicalManufacturing/.setup-state.yaml
   ```

2. **Recover the state file** from Fabric resources (recommended):
   ```bash
   fabric-demo recover ./MedicalManufacturing
   fabric-demo cleanup ./MedicalManufacturing
   ```

3. Or use force-by-name cleanup (deletes by resource name):
   ```bash
   fabric-demo cleanup ./MedicalManufacturing --force-by-name --confirm
   ```

### "Cannot delete ontology - bindings exist"

Delete in correct order: Ontology → Eventhouse → Lakehouse

The tool handles this automatically, but if manual cleanup is needed:

1. In Fabric UI, delete bindings first
2. Then delete the ontology
3. Finally delete data sources

### State File Lost or Corrupted

If the state file (`.setup-state.yaml`) is lost, corrupted, or accidentally deleted:

**Option 1: Recover from Fabric (Recommended)**

```bash
# Rebuild state file from existing resources
fabric-demo recover ./MedicalManufacturing

# Then cleanup normally
fabric-demo cleanup ./MedicalManufacturing
```

**Option 2: Restore from backup**

The tool automatically creates a backup before each save:

```bash
# Check for backup
ls ./MedicalManufacturing/.setup-state.yaml.backup

# Manually copy if exists
cp .setup-state.yaml.backup .setup-state.yaml
```

**Option 3: Force cleanup by name**

```bash
fabric-demo cleanup ./MedicalManufacturing --force-by-name
```

### State File Lost After Cleanup

The state file is preserved with `cleaned_up` status after cleanup. If you deleted it manually:

```bash
# Use force-by-name to cleanup by resource name
fabric-demo cleanup ./MedicalManufacturing --force-by-name
```

---

## Validation Issues

### "Missing required folder: Ontology/"

The demo package structure is incomplete.

**Required structure**:
```
DemoName/
├── Ontology/
│   └── *.ttl
├── Data/
│   ├── Lakehouse/
│   └── Eventhouse/
└── Bindings/
    └── bindings.yaml
```

### "Invalid TTL syntax"

The ontology file has syntax errors.

**Solution**: Validate TTL syntax with an RDF validator or check for:
- Unclosed quotes
- Missing semicolons or periods
- Invalid prefixes

### "bindings.yaml schema validation failed"

The bindings file doesn't match the expected schema.

**Common issues**:
- Missing required fields (`keyColumn`, `timestampColumn`)
- Wrong property types
- Mismatched entity names between TTL and bindings

---

## Performance Issues

### Setup Takes Very Long

**Causes**:
- Large CSV files
- Rate limiting
- Network latency

**Solutions**:

1. Check rate limit settings - increase if your SKU allows:
   ```yaml
   rate_limiting:
     requests_per_minute: 60
   ```

2. For large files, consider splitting data

3. Run individual steps to identify bottleneck:
   ```bash
   fabric-demo run-step ./Demo --step 3  # Upload files
   fabric-demo run-step ./Demo --step 6  # Ingest data
   ```

### "Connection timeout"

**Cause**: Network issues or Fabric service unavailable.

**Solutions**:
1. Check your internet connection
2. Verify Fabric service status at [Azure Status](https://status.azure.com)
3. Retry after a few minutes

---

## Getting More Help

### Enable Debug Mode

Get full stack traces:

```bash
fabric-demo setup ./MedicalManufacturing --debug
```

### Check Setup Status

See which steps completed:

```bash
fabric-demo status ./MedicalManufacturing
```

### View State File

```bash
cat ./MedicalManufacturing/.setup-state.yaml
```

### Report a Bug

If you find a bug, please report it at:
https://github.com/falloutxAY/Fabric-Ontology-demoAgent/issues

Include:
- Command you ran
- Full error output (with `--debug`)
- Your Python version (`python --version`)
- Your OS

---

## See Also

- [CLI Reference](cli-reference.md) - All commands
- [Configuration](configuration.md) - Configuration options
