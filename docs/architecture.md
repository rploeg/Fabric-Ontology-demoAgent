# Architecture Overview

System design documentation for contributors and maintainers.

> **Version**: 0.2.0+ uses the [Unofficial Fabric Ontology SDK](https://github.com/falloutxAY/Unofficial-Fabric-Ontology-SDK) for ontology operations.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interface                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         CLI (cli.py)                                  │  │
│  │  python -m demo_automation setup | validate | cleanup | config | ... │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Orchestration Layer                                 │
│  ┌────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ GlobalConfig   │  │ DemoOrchestrator│  │ SetupStateManager           │  │
│  │ (~/.fabric-    │  │ (11-step        │  │ (.setup-state.yaml)         │  │
│  │  demo/config)  │  │  workflow)      │  │ Resume + Audit trail        │  │
│  └────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Business Logic Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────────────┐  │
│  │ Validator       │  │ BindingParser   │  │ SDKBindingBridge           │  │
│  │ (demo structure)│  │ (YAML + MD)     │  │ (Static + Timeseries +     │  │
│  │                 │  │                 │  │  Relationships via SDK)    │  │
│  └─────────────────┘  └─────────────────┘  └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Platform Clients                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────────────┐  │
│  │ FabricClient    │  │ LakehouseClient │  │ EventhouseClient           │  │
│  │ (Base + Auth +  │  │ (Create +       │  │ (Create + KQL Database +   │  │
│  │  Ontology APIs) │  │  Table loading) │  │  Data ingestion)           │  │
│  └─────────────────┘  └─────────────────┘  └────────────────────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      OneLakeDataClient                               │   │
│  │                (File upload via Azure SDK)                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           External Services                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────────────┐  │
│  │ Azure AD        │  │ Fabric REST API │  │ OneLake Storage            │  │
│  │ (Authentication)│  │ (Resources,     │  │ (File operations)          │  │
│  │                 │  │  Ontology)      │  │                            │  │
│  └─────────────────┘  └─────────────────┘  └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Module Structure

```
Demo-automation/
├── src/demo_automation/
│   ├── __init__.py
│   ├── cli.py                 # CLI entry point, argument parsing
│   ├── orchestrator.py        # 11-step workflow execution
│   ├── state_manager.py       # Setup state persistence
│   ├── validator.py           # Demo package validation
│   ├── sdk_adapter.py         # SDK client/builder factories (v0.2.0+)
│   │
│   ├── core/
│   │   ├── config.py          # Demo-specific configuration
│   │   ├── global_config.py   # Global user configuration
│   │   └── errors.py          # Custom exception hierarchy
│   │
│   ├── platform/
│   │   ├── fabric_client.py   # Base Fabric API client + Ontology
│   │   ├── lakehouse_client.py    # Lakehouse operations
│   │   ├── eventhouse_client.py   # Eventhouse/KQL operations
│   │   └── onelake_client.py      # OneLake file operations
│   │
│   ├── binding/
│   │   ├── sdk_binding_bridge.py  # SDK-based binding builder (recommended)
│   │   ├── binding_builder.py     # Legacy binding builder (deprecated)
│   │   ├── binding_parser.py      # Parse binding instructions
│   │   └── yaml_parser.py         # Parse bindings.yaml
│   │
│   └── ontology/
│       ├── ttl_converter.py       # Parse TTL files
│       └── sdk_converter.py       # TTL to SDK builder conversion (v0.2.0+)
│
├── tests/
│   ├── conftest.py            # Pytest fixtures
│   ├── test_config.py
│   ├── test_validator.py
│   ├── test_relationship_bindings.py
│   ├── test_sdk_adapter.py        # SDK adapter tests
│   ├── test_sdk_binding_bridge.py # SDK binding bridge tests
│   └── test_sdk_converter.py      # SDK converter tests
│
└── pyproject.toml             # Package configuration
```

---

## Key Components

### CLI (`cli.py`)

Entry point for all commands. Uses `argparse` for argument parsing and `rich` for terminal output.

**Responsibilities**:
- Parse command-line arguments
- Load configuration (global + demo-specific)
- Dispatch to appropriate handlers
- Format output for terminal

### Orchestrator (`orchestrator.py`)

Coordinates the 11-step setup workflow.

**Responsibilities**:
- Execute steps in sequence
- Handle resource existence checks
- Manage state persistence
- Provide progress reporting

**Steps**:
1. validate
2. create_lakehouse
3. upload_files
4. load_tables
5. create_eventhouse
6. ingest_data
7. create_ontology
8. bind_static
9. bind_timeseries
10. bind_relationships
11. verify

### State Manager (`state_manager.py`)

Persists setup state to `.setup-state.yaml` for resume and audit.

**States**:
- `NOT_STARTED`
- `IN_PROGRESS`
- `COMPLETED`
- `FAILED`
- `CLEANED_UP`

### FabricClient (`platform/fabric_client.py`)

Base client for Fabric REST APIs.

**Features**:
- Multiple auth methods (Interactive, Service Principal, Default)
- Token bucket rate limiting
- Automatic retries with exponential backoff
- Long-running operation (LRO) polling

**Rate Limiting**:
```python
RateLimitConfig(
    enabled=True,
    requests_per_minute=30,
    burst=10
)
```

### SDK Binding Bridge (`binding/sdk_binding_bridge.py`) *(v0.2.0+)*

Constructs binding payloads using the Fabric Ontology SDK builders.

**Binding Types**:
- Static (Lakehouse tables)
- Timeseries (Eventhouse tables)
- Relationship contextualizations

> **Note**: The legacy `OntologyBindingBuilder` in `binding_builder.py` is deprecated. Use `SDKBindingBridge` for new code.

---

## Data Flow

### Setup Workflow

```
Demo Package → Validator → Orchestrator
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
    Lakehouse            Eventhouse           Ontology
    - Create             - Create             - Create
    - Upload CSV         - Create KQL DB      - Parse TTL
    - Load tables        - Ingest data        - Create entities
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                         Bindings
                    - Static properties
                    - Timeseries properties
                    - Relationships
                              │
                              ▼
                        Verification
                    - Check resources
                    - Validate bindings
```

### Configuration Resolution

```
CLI Arguments
     │
     ▼ (override)
Environment Variables (FABRIC_WORKSPACE_ID, etc.)
     │
     ▼ (override)
Global Config (~/.fabric-demo/config.yaml)
     │
     ▼ (override)
Demo Config (demo.yaml)
     │
     ▼ (fallback)
Built-in Defaults
```

---

## Error Handling

### Exception Hierarchy

```
DemoAutomationError (base)
├── ConfigurationError
│   └── MissingConfigError
├── ValidationError
│   └── SchemaValidationError
├── FabricAPIError
│   ├── AuthenticationError
│   ├── RateLimitError
│   ├── ResourceNotFoundError
│   └── ResourceExistsError
├── BindingError
└── CancellationRequestedError
```

### Retry Strategy

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, RateLimitError)),
)
def _make_request(self, ...):
    ...
```

---

## Authentication

### SDK Factory Methods (v0.3.0+)

The [Unofficial Fabric Ontology SDK](https://github.com/falloutxAY/Unofficial-Fabric-Ontology-SDK) provides factory methods for authentication:

| Factory Method | Config Value | Use Case |
|---------------|--------------|----------|
| `FabricClient.from_interactive()` | `interactive` | Demos, development |
| `FabricClient.from_service_principal()` | `service_principal` | CI/CD automation |
| `FabricClient.from_azure_cli()` | `azure_cli` | Local dev with `az login` |
| `FabricClient.from_device_code()` | `device_code` | Headless environments |

### Token Management

- Tokens cached with 60-second buffer before expiry
- Automatic refresh on API calls
- Thread-safe credential access

---

## API Interactions

### Fabric REST API

Base URL: `https://api.fabric.microsoft.com/v1`

**Endpoints Used**:
- `POST /workspaces/{id}/lakehouses` - Create lakehouse
- `POST /workspaces/{id}/eventhouses` - Create eventhouse
- `POST /workspaces/{id}/ontologies` - Create ontology
- `PATCH /workspaces/{id}/ontologies/{id}/definition` - Update definition
- `DELETE /workspaces/{id}/{itemType}/{id}` - Delete resources

### OneLake

Uses Azure SDK `DataLakeServiceClient` for file operations:
- Upload CSV files to lakehouse
- No direct REST API calls

---

## Testing Strategy

### Unit Tests
- Configuration loading/merging
- Validation logic
- Binding payload construction

### Integration Tests (Future)
- Mock Fabric API responses
- End-to-end workflow tests

### Running Tests

```bash
cd Demo-automation
pip install -e ".[dev]"
pytest
```

---

## Contributing

### Code Style

- Python 3.10+
- Type hints required
- Docstrings for public methods
- Use `logging` module, not `print`

### Adding a New Command

1. Add subparser in `cli.py`
2. Create handler function
3. Update help text
4. Add to CLI Reference doc

### Adding a New Step

1. Add step enum in `orchestrator.py`
2. Implement step method
3. Add to step mapping
4. Update state schema if needed

---

## See Also

- [CLI Reference](cli-reference.md) - Command documentation
- [Configuration](configuration.md) - Config options
- [Troubleshooting](troubleshooting.md) - Common issues
