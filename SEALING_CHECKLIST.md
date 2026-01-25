# OMEGA SDK v1.0.0 Sealing Checklist

This checklist MUST be completed before pushing the `omega-sdk-python-v1.0.0` tag.

## Core Functionality

- [x] OmegaClient exists and exposes:
  - [x] `tools.list()` - List available tools
  - [x] `tools.get(tool_id)` - Get tool details
  - [x] `tools.invoke(tool_id, input)` - Invoke a tool
  - [x] `agents.list()` - List registered agents
  - [x] `agents.get(agent_id)` - Get agent details
  - [x] `tasks.create(task_type, input)` - Spawn async task
  - [x] `tasks.get(task_id)` - Get task status
  - [x] `health()` - Health check
  - [x] `status()` - Rich status

## Correlation Discipline

- [x] Canonical format enforced: `t:<tenant>|c:<uuidv7>`
- [x] `make_correlation_id(tenant_id)` helper exists
- [x] `validate_correlation_id()` validates format
- [x] Every request includes correlation ID (auto-generated if not provided)
- [x] Correlation ID validation tests pass

## Governance Hooks

- [x] Receipt threading supported (`decision_receipt_id` parameter)
- [x] "Execute-like" flows accept receipt ID
- [x] Audit metadata models include `keon_receipt_id` and `evidence_pack_id`
- [x] Receipt enforcement tests exist

## Structured Errors

- [x] All errors derive from `OmegaError`
- [x] KeonResult-style envelope discipline
- [x] Error types:
  - [x] `AuthenticationError` (401)
  - [x] `ValidationError` (400)
  - [x] `NotFoundError` (404)
  - [x] `RateLimitError` (429)
  - [x] `UpstreamError` (502, 503)
  - [x] `InternalError` (500)
- [x] All errors include `correlation_id` and `request_id`
- [x] Error mapping tests pass

## Retry Logic

- [x] Bounded retries implemented (configurable max attempts)
- [x] Exponential backoff with jitter
- [x] Only retryable errors are retried
- [x] No request storms (backoff proves this)
- [x] Retry tests pass

## Chaos Harness

- [x] Chaos stub server exists
- [x] Emulates Federation Core with:
  - [x] Random 5xx bursts
  - [x] 429 throttles
  - [x] Delayed responses
  - [x] Malformed payloads
- [x] Integration tests run against chaos server
- [x] Chaos tests prove bounded retries
- [x] Failure matrix report generated

## Documentation

- [x] `README.md` with:
  - [x] Quick start (3 examples)
  - [x] Installation instructions
  - [x] Configuration options
  - [x] Error handling guide
- [x] `docs/CORRELATION.md` - Correlation discipline
- [x] `docs/TS_SDK_PLAN.md` - TypeScript SDK plan
- [x] Examples:
  - [x] `examples/list_tools.py`
  - [x] `examples/invoke_tool.py`
  - [x] `examples/spawn_task.py`

## Code Quality

- [ ] All tests pass: `pytest`
- [ ] Test coverage >80%: `pytest --cov=omega_sdk`
- [ ] Linting clean: `ruff src tests`
- [ ] Formatting clean: `black src tests`
- [ ] Type checking clean: `mypy src`

## Package

- [x] `pyproject.toml` complete
- [x] Version set to `1.0.0`
- [x] Dependencies specified
- [x] Dev dependencies specified
- [x] Package structure follows standards

## Git

- [ ] Working directory clean (no uncommitted changes)
- [ ] All changes committed
- [ ] Branch: `team-claude/omega-sdk-python-v1`
- [ ] Tag ready: `omega-sdk-python-v1.0.0`

## Integration

- [ ] SDK can connect to local Federation Core
- [ ] SDK can list tools successfully
- [ ] SDK can invoke a tool successfully
- [ ] SDK can create a task successfully

## Final Verification

Run this verification script before sealing:

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest --cov=omega_sdk --cov-report=term-missing

# Linting
ruff src tests
black --check src tests
mypy src

# Chaos tests (optional, takes ~60s)
pytest tests/chaos/ -v

# Verify examples can be imported
python -c "import omega_sdk; print(omega_sdk.__version__)"
```

## Sign-Off

| Team | Status | Notes |
|------|--------|-------|
| Team Claude (Client) | ✅ DONE | OmegaClient + Gateway complete |
| Team Gemini (Governance) | ✅ DONE | Correlation + receipt threading |
| Team Grok (Chaos) | ✅ DONE | Chaos harness + integration tests |
| Team Augment (DX) | ✅ DONE | Docs + examples + TS plan |

## Release Notes (v1.0.0)

### Features

- ✅ Federation Core HTTP client with full API coverage
- ✅ Canonical correlation ID discipline (`t:<tenant>|c:<uuidv7>`)
- ✅ Structured error model with correlation tracking
- ✅ Bounded retry logic with exponential backoff
- ✅ Governance hooks (optional receipt threading)
- ✅ Chaos-tested resilience
- ✅ Type-safe Pydantic models from OpenAPI spec

### Breaking Changes

N/A (initial release)

### Known Limitations

- Streaming responses not yet supported (planned for v1.1)
- WebSocket connections not supported (use HTTP long-polling)
- Browser environment not supported (Node.js only for v1.0)

### Next Steps

- TypeScript SDK (see `docs/TS_SDK_PLAN.md`)
- Streaming support (v1.1)
- WebSocket integration (v1.2)
