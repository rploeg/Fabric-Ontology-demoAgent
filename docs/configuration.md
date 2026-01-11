# Configuration Guide

Complete guide to configuring the demo automation CLI tool.

> 💡 **Recommended**: Use `python -m demo_automation` instead of `fabric-demo` to avoid PATH configuration issues.

---

## Configuration Precedence

The tool uses multiple configuration sources in this order (highest priority first):

1. **CLI arguments**: `--workspace-id abc123`
2. **Environment variables**: `FABRIC_WORKSPACE_ID`
3. **Global config file**: `~/.fabric-demo/config.yaml`
4. **Demo-specific config**: `demo.yaml` in demo folder
5. **Built-in defaults**

---

## Global Configuration File

Location:
- **Windows**: `%USERPROFILE%\.fabric-demo\config.yaml`
- **macOS/Linux**: `~/.fabric-demo/config.yaml`

### Creating the Config File

```bash
# Interactive wizard (recommended)
python -m demo_automation config init

# Or create manually
mkdir -p ~/.fabric-demo
touch ~/.fabric-demo/config.yaml
```

### Full Configuration Template

```yaml
# Fabric Demo Automation - Global Configuration
# =============================================

defaults:
  # Your default Fabric workspace ID (GUID)
  workspace_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  
  # Azure AD tenant ID (optional, for multi-tenant scenarios)
  tenant_id: 
  
  # Authentication method: interactive, service_principal, or default
  # - interactive: Opens browser for login (recommended for demos)
  # - service_principal: Uses AZURE_CLIENT_ID and AZURE_CLIENT_SECRET env vars
  # - default: Uses DefaultAzureCredential chain
  auth_method: interactive

options:
  # Skip creation if resources already exist (default: true)
  skip_existing: true
  
  # Preview mode - don't make changes (default: false)
  dry_run: false
  
  # Show verbose output (default: false)
  verbose: false
  
  # Require --confirm or interactive confirmation for cleanup (default: true)
  confirm_cleanup: true

# API rate limiting settings
# Adjust these if you have higher Fabric SKU quotas or experience throttling
rate_limiting:
  # Enable/disable rate limiting (default: true)
  enabled: true
  
  # Maximum requests per minute (default: 30)
  # Fabric API typically allows 30-60 requests/minute depending on SKU
  requests_per_minute: 30
  
  # Burst allowance for short request spikes (default: 10)
  burst: 10
```

### View Current Configuration

```bash
python -m demo_automation config show
```

Output:

```
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Setting         ┃ Value                                ┃ Source  ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Workspace ID    │ bf5fab96-5f75-44a9-a8e2-850ad6ea59ce │ env     │
│ Tenant ID       │ not set                              │ not set │
│ Auth Method     │ interactive                          │ config  │
│ Skip Existing   │ True                                 │ config  │
│ Confirm Cleanup │ True                                 │ config  │
├─────────────────┼──────────────────────────────────────┼─────────┤
│ Rate Limiting   │                                      │         │
│   Enabled       │ True                                 │ config  │
│   Requests/min  │ 30                                   │ config  │
│   Burst         │ 10                                   │ config  │
└─────────────────┴──────────────────────────────────────┴─────────┘
```

---

## Environment Variables

Set these in your shell or a `.env` file:

| Variable | Description | Example |
|----------|-------------|---------|
| `FABRIC_WORKSPACE_ID` | Fabric workspace GUID | `bf5fab96-5f75-...` |
| `AZURE_TENANT_ID` | Azure AD tenant ID | `72f988bf-86f1-...` |
| `AZURE_CLIENT_ID` | Service principal app ID | (for automation) |
| `AZURE_CLIENT_SECRET` | Service principal secret | (for automation) |

### Using a .env File

Create a `.env` file in your project root:

```bash
# .env
FABRIC_WORKSPACE_ID=bf5fab96-5f75-44a9-a8e2-850ad6ea59ce
AZURE_TENANT_ID=72f988bf-86f1-41af-91ab-2d7cd011db47
```

The tool automatically loads `.env` files from the current directory.

> ⚠️ **Security**: Never commit `.env` files with real credentials. Use `.env.example` as a template.

---

## Demo-Specific Configuration

Each demo folder can have a `demo.yaml` file:

```yaml
# demo.yaml
demo:
  name: MedicalManufacturing
  description: "Medical device manufacturing ontology demo"

fabric:
  # Override workspace for this specific demo
  workspace_id: ${FABRIC_WORKSPACE_ID}

options:
  skip_existing: true
  dry_run: false
```

### Variable Substitution

Use `${VAR_NAME}` to reference environment variables:

```yaml
fabric:
  workspace_id: ${FABRIC_WORKSPACE_ID}
  tenant_id: ${AZURE_TENANT_ID}
```

---

## Authentication Methods

The tool supports multiple authentication methods via the [Unofficial Fabric Ontology SDK](https://github.com/falloutxAY/Unofficial-Fabric-Ontology-SDK). Set via `config init` or in `~/.fabric-demo/config.yaml`:

| Method | Use Case | SDK Factory Method |
|--------|----------|-------------------|
| `interactive` | Demos, development | `FabricClient.from_interactive()` |
| `azure_cli` | Local dev with `az login` | `FabricClient.from_azure_cli()` |
| `service_principal` | CI/CD automation | `FabricClient.from_service_principal()` |
| `device_code` | Headless environments | `FabricClient.from_device_code()` |

### Interactive Browser (Default)

Opens browser for Azure AD login. Best for demos and local development.

```yaml
defaults:
  auth_method: interactive
```

### Azure CLI (Recommended for Local Dev)

Uses credentials from `az login`. Requires Azure CLI to be installed and logged in.

```yaml
defaults:
  auth_method: azure_cli
```

```bash
# Login first
az login
```

### Service Principal (Recommended for CI/CD)

Uses service principal credentials from environment variables.

```yaml
defaults:
  auth_method: service_principal
```

Required environment variables:
```bash
export AZURE_TENANT_ID=your-tenant-id
export AZURE_CLIENT_ID=your-app-id  
export AZURE_CLIENT_SECRET=your-secret
```

### Device Code (Headless Environments)

Displays a code to enter at https://microsoft.com/devicelogin. Useful for remote servers without browser access.

```yaml
defaults:
  auth_method: device_code
```

---

## Rate Limiting

The Fabric API has rate limits. The tool includes a token bucket rate limiter.

### Default Settings

- **30 requests/minute** - Conservative for all Fabric SKUs
- **Burst of 10** - Allows short spikes

### Adjusting for Higher SKUs

If you have a Fabric F64 or higher SKU, you may have higher quotas:

```yaml
rate_limiting:
  enabled: true
  requests_per_minute: 60
  burst: 20
```

### Disabling Rate Limiting

Not recommended, but possible:

```yaml
rate_limiting:
  enabled: false
```

---

## Common Configuration Scenarios

**Personal Demo**: Use `interactive` auth, 30 req/min, confirm cleanup  
**CI/CD**: Use `service_principal` auth, 60 req/min, auto-confirm  
**Shared**: Use `interactive` auth, always confirm cleanup

---

## Troubleshooting

**"Workspace ID not configured"** → Run `python -m demo_automation config init`  
**"Auth method not recognized"** → Valid: `interactive`, `service_principal`, `default`  
**Config not loading** → Check path with `python -m demo_automation config path`

---

## See Also

- [CLI Reference](cli-reference.md) - All commands
- [Troubleshooting](troubleshooting.md) - Common issues
