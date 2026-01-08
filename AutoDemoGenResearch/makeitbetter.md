# Fabric Ontology Demo Agent - Architecture Review & Improvement Plan

> **Review Date**: January 2026  
> **Reviewer**: Senior Architect  
> **Scope**: Demo-automation CLI, .agentic agent specifications, documentation  
> **Target Users**: Sellers, Product Managers, Demo Engineers

---

## Executive Summary

The project is well-structured for its purpose—a demo/showcase tool for Microsoft Fabric Ontology. The codebase demonstrates good patterns (retry logic, state management, rate limiting) but has opportunities for improvement in:

1. **Security**: Credentials handling needs hardening
2. **Configuration UX**: Scattered config sources create friction
3. **Documentation**: Good but fragmented; needs consolidation
4. **Error Recovery**: Manual cleanup scenario exposed a gap

This plan prioritizes quick wins that improve daily usability for non-developers.

---

## Current State Analysis

### ✅ Strengths

| Area | What's Good |
|------|-------------|
| **State Management** | Excellent resume capability via `.setup-state.yaml`; cleanup now preserves audit trail |
| **Error Handling** | Comprehensive custom exception hierarchy with contextual details |
| **API Integration** | Proper retry logic, token bucket rate limiting, LRO polling |
| **CLI Structure** | Well-organized subcommands with rich terminal output |
| **Modularity** | Clean separation: platform/, binding/, core/, ontology/ |

### ⚠️ Areas of Concern

| Area | Issue | Risk |
|------|-------|------|
| **Security** | `.env` file in repo root contains actual workspace ID | Medium - credential leak |
| **Security** | No guidance on secrets management for CI/CD | Medium |
| **Config UX** | Config split across: `.env`, `demo.yaml`, CLI args, env vars | High friction |
| **Recovery** | Manual cleanup required when state file lost | User frustration |
| **Documentation** | README duplicated concepts; agent-instructions.md is separate | Onboarding friction |
| **Testing** | Only 3 test files; no integration tests | Regression risk |

### 🔍 Design Observations

1. **Orchestrator is 2600+ lines** - Doing too much; harder to maintain
2. **fabric_client.py is 800+ lines** - Contains both base client and ontology-specific logic
3. **CLI parser is 1000+ lines** - Could be simplified with config file
4. **No validation of bindings.yaml against schema** - Schema exists but not enforced

---

## Phased Improvement Plan

### Phase 1: Security & Configuration (Priority: HIGH)

**Goal**: Eliminate credential leaks, simplify configuration

#### 1.1 Secure Credentials Handling

| Task | Description | Effort |
|------|-------------|--------|
| Add `.env.example` | Template file without real values; remove workspace ID from `.env` | 30 min |
| Update `.gitignore` | Ensure `.env` is ignored (verify current state) | 15 min |
| Document auth options | Clear guide for interactive vs service principal vs managed identity | 1 hr |
| Add credential validation | Check token acquisition before starting setup | 1 hr |

#### 1.2 Unified Configuration File

**Current**: User must manage `.env` + `demo.yaml` + CLI args  
**Proposed**: Single `fabric-demo.config.yaml` in user's home directory for global settings

```yaml
# ~/.fabric-demo/config.yaml (or %USERPROFILE%\.fabric-demo\config.yaml)
defaults:
  workspace_id: ${FABRIC_WORKSPACE_ID}  # Still supports env vars
  tenant_id: ${AZURE_TENANT_ID}
  auth_method: interactive  # interactive | service_principal | default

options:
  skip_existing: true
  dry_run: false
  verbose: false
```

| Task | Description | Effort |
|------|-------------|--------|
| Design config hierarchy | CLI args > env vars > config file > defaults | 1 hr |
| Implement config loader | Load from `~/.fabric-demo/config.yaml` if exists | 2 hr |
| Add `fabric-demo config` command | Interactive config setup wizard | 2 hr |
| Update docs | Document config file location and precedence | 1 hr |

#### 1.3 Deliverables
- [ ] `.env.example` template file
- [ ] Config file loader with precedence rules
- [ ] `fabric-demo config init` command
- [ ] Updated security documentation

---

### Phase 2: CLI Usability (Priority: HIGH)

**Goal**: Reduce friction for first-time users

#### 2.1 Simplify Common Workflows

| Current | Proposed |
|---------|----------|
| `fabric-demo setup ./Demo --workspace-id abc123` | `fabric-demo setup ./Demo` (uses config file) |
| `fabric-demo cleanup ./Demo --confirm` | `fabric-demo cleanup ./Demo` (with interactive confirmation) |
| Manual: find resources, delete | `fabric-demo cleanup ./Demo --force-by-name` (fallback when state lost) |

| Task | Description | Effort |
|------|-------------|--------|
| Default workspace from config | Remove required `--workspace-id` if configured | 1 hr |
| Interactive cleanup confirmation | Default to interactive; `--yes` to skip | 30 min |
| Add `--force-by-name` cleanup | Fallback cleanup by resource name when state file missing | 2 hr |
| Add `fabric-demo list` command | List demos in workspace (by naming convention) | 2 hr |

#### 2.2 Better Error Messages

| Task | Description | Effort |
|------|-------------|--------|
| Add troubleshooting hints | Common errors should suggest fixes | 2 hr |
| Link to docs in errors | Include doc URLs in error output | 1 hr |
| Add `--debug` flag | Full stack trace only when requested | 30 min |

#### 2.3 Deliverables
- [ ] Config-file-based workspace resolution
- [ ] `--force-by-name` cleanup option
- [ ] `fabric-demo list` command
- [ ] Enhanced error messages with hints

---

### Phase 3: Documentation Consolidation (Priority: MEDIUM)

**Goal**: Single source of truth, easy onboarding

#### 3.1 Documentation Structure

**Current State**:
- `README.md` (root) - Project overview
- `Demo-automation/README.md` - CLI tool docs (detailed)
- `.agentic/agent-instructions.md` - Agent workflow
- `.agentic/schemas/*.yaml` - Schema definitions
- Scattered markdown in demo folders

**Proposed Structure**:

```
docs/
├── index.md                    # Quick start (links to others)
├── cli-reference.md            # Complete CLI documentation
├── configuration.md            # All config options explained
├── troubleshooting.md          # Common issues and fixes
├── agent-workflow.md           # How to use with AI agent
└── architecture.md             # For contributors
```

| Task | Description | Effort |
|------|-------------|--------|
| Create `docs/` folder | Centralized documentation | 30 min |
| Write quick-start guide | 5-minute setup to first demo | 1 hr |
| Consolidate CLI docs | Single authoritative reference | 2 hr |
| Create troubleshooting guide | Expanded from current README sections | 1 hr |
| Add architecture diagram | Visual system overview | 1 hr |

#### 3.2 Inline Help Improvements

| Task | Description | Effort |
|------|-------------|--------|
| Add examples to each command | `fabric-demo setup --help` shows real examples | 1 hr |
| Add `fabric-demo docs` command | Opens documentation in browser | 30 min |

#### 3.3 Deliverables
- [ ] Consolidated `docs/` folder
- [ ] Quick-start guide (<5 min to first demo)
- [ ] `fabric-demo docs` command

---

### Phase 4: Robustness & Recovery (Priority: MEDIUM)

**Goal**: Graceful handling of edge cases

#### 4.1 State Recovery

| Task | Description | Effort |
|------|-------------|--------|
| Add `fabric-demo recover` command | Rebuild state file from existing Fabric resources | 3 hr |
| State file backup | Auto-backup before modifications | 1 hr |
| State file versioning | Handle schema changes in state file | 1 hr |

#### 4.2 Idempotency Improvements

| Task | Description | Effort |
|------|-------------|--------|
| Verify resource state before steps | Check if already done, even without state file | 2 hr |
| Add checksums to uploads | Skip re-upload if file unchanged | 2 hr |

#### 4.3 Deliverables
- [ ] `fabric-demo recover` command
- [ ] Improved idempotency checks
- [ ] State file backup mechanism

---

### Phase 5: Code Quality (Priority: LOW)

**Goal**: Maintainability for future contributors

#### 5.1 Refactoring

| Task | Description | Effort |
|------|-------------|--------|
| Split orchestrator.py | Separate step executors into modules | 4 hr |
| Split fabric_client.py | Base client vs. ontology operations | 2 hr |
| Extract CLI argument parsing | Declarative config, less boilerplate | 2 hr |

#### 5.2 Testing

| Task | Description | Effort |
|------|-------------|--------|
| Add unit tests for config loader | Cover precedence rules | 2 hr |
| Add integration test framework | Mock Fabric API responses | 4 hr |
| Add schema validation tests | Ensure bindings.yaml validates | 1 hr |

#### 5.3 Deliverables
- [ ] Refactored orchestrator (<500 lines each module)
- [ ] 80% test coverage on core modules
- [ ] CI/CD pipeline (optional)

---

## Phase 6: Optional Enhancements (Priority: NICE-TO-HAVE)

### 6.1 Developer Experience

| Feature | Description | Effort |
|---------|-------------|--------|
| VS Code extension | Snippets, validation, commands | 8+ hr |
| GitHub Actions workflow | Auto-validate demo packages on PR | 2 hr |
| Demo package linter | `fabric-demo lint ./Demo` | 3 hr |

### 6.2 Advanced Features

| Feature | Description | Effort |
|---------|-------------|--------|
| Multi-workspace support | Deploy same demo to multiple workspaces | 4 hr |
| Demo versioning | Track which version is deployed | 3 hr |
| Rollback capability | Restore previous state | 4 hr |
| Export/Import state | Share state between team members | 2 hr |

### 6.3 Observability

| Feature | Description | Effort |
|---------|-------------|--------|
| Structured logging | JSON logs for analysis | 2 hr |
| Timing metrics | Per-step duration tracking | 1 hr |
| Health check command | `fabric-demo health` - verify connectivity | 1 hr |

---

## Implementation Roadmap

```
Week 1-2: Phase 1 (Security & Configuration)
├── Day 1-2: Secure credentials (.env.example, docs)
├── Day 3-5: Config file loader implementation
├── Day 6-7: Testing and documentation
└── Milestone: No credentials in repo, config wizard works

Week 3-4: Phase 2 (CLI Usability)
├── Day 1-3: Default workspace from config, interactive cleanup
├── Day 4-6: --force-by-name cleanup, list command
├── Day 7: Error message improvements
└── Milestone: First-time user can setup demo in <10 min

Week 5-6: Phase 3 (Documentation)
├── Day 1-3: Create docs/ structure, write quick-start
├── Day 4-6: Consolidate CLI reference, troubleshooting
├── Day 7: Review and polish
└── Milestone: Single docs/ folder, all READMEs link to it

Week 7-8: Phase 4 (Robustness)
├── Day 1-4: recover command implementation
├── Day 5-7: Idempotency improvements
└── Milestone: Graceful recovery from any failure state

Future: Phase 5-6 as needed
```

---

## Quick Wins (Can Do Today)

1. **Create `.env.example`** - 15 minutes, high impact
2. **Add `.env` to `.gitignore`** verification - 5 minutes
3. **Add `--force-by-name` flag to cleanup** - We just manually did this, make it a feature
4. **Improve error message** when state file missing - Suggest `--force-by-name`

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Time to first demo (new user) | ~30 min | <10 min |
| Config files to manage | 3+ | 1 |
| Recovery from lost state | Manual script | Single command |
| Documentation locations | 4+ | 1 (docs/) |
| Test coverage | Unknown (low) | 80% core |

---

## Appendix: File-by-File Notes

### Demo-automation/src/demo_automation/

| File | Lines | Notes |
|------|-------|-------|
| `cli.py` | 1027 | Consider `typer` or `click` for cleaner CLI; extract command handlers |
| `orchestrator.py` | 2609 | **Refactor candidate** - split into step modules |
| `state_manager.py` | 454 | Well-designed; add backup capability |
| `validator.py` | ? | Add schema validation for bindings.yaml |

### Demo-automation/src/demo_automation/platform/

| File | Lines | Notes |
|------|-------|-------|
| `fabric_client.py` | 836 | Split: base client + ontology client |
| `lakehouse_client.py` | ? | Good |
| `eventhouse_client.py` | ? | Good |
| `onelake_client.py` | ? | Good |

### Demo-automation/src/demo_automation/core/

| File | Lines | Notes |
|------|-------|-------|
| `config.py` | 498 | Add global config file support |
| `errors.py` | 166 | Add troubleshooting hints to exceptions |

---

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Prioritize config UX over refactoring | Users blocked by config friction more than code quality | Jan 2026 |
| Keep `argparse` over `typer` | Fewer dependencies; argparse is sufficient | Jan 2026 |
| Single `docs/` folder | Reduce confusion from multiple README files | Jan 2026 |
