# OMEGA SDK (Python)

**Production-ready Python client for OMEGA Federation Core.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Features

- ✅ **Federation Core API Client** - Clean, typed interface to all Federation Core endpoints
- ✅ **Governance-First** - Correlation discipline + optional receipt threading built-in
- ✅ **Structured Errors** - KeonResult-style envelope with typed exceptions
- ✅ **Bounded Retries** - Exponential backoff for transient failures
- ✅ **Battle-Tested** - >80% test coverage + chaos harness
- ✅ **Doctrine-Compliant** - Contracts from Keon SDK, no drift

## Installation

```bash
pip install omega-sdk
```

## Quick Start

### 1. List Tools

```python
from omega_sdk import OmegaClient

client = OmegaClient.from_env()

# List available tools
tools = await client.tools.list()
for tool in tools.items:
    print(f"{tool.tool_id}: {tool.description}")
```

### 2. Invoke a Tool

```python
from omega_sdk import OmegaClient

client = OmegaClient(
    federation_url="http://localhost:9405",
    tenant_id="acme",
    actor_id="clint",
)

# Invoke a tool
result = await client.tools.invoke(
    "csv_processor",
    input={"file": "data.csv", "normalize": True}
)

print(f"Processed {result.result['normalized_rows']} rows")
print(f"Audit event: {result.audit.event_id}")
```

### 3. Spawn a Task

```python
from omega_sdk import OmegaClient
from omega_sdk.models import TaskRouting

client = OmegaClient.from_env()

# Create an asynchronous task
task = await client.tasks.create(
    task_type="workflow.run",
    input={"workflow": "brand_campaign"},
    routing=TaskRouting(
        strategy="capability",
        capability="branding"
    )
)

print(f"Task created: {task.task_id}")

# Poll for completion
while True:
    status = await client.tasks.get(task.task_id)
    print(f"Status: {status.status} - Progress: {status.state.progress}")

    if status.status in ["completed", "failed"]:
        break

    await asyncio.sleep(5)

if status.result:
    print(f"Result: {status.result}")
```

## Configuration

### Environment Variables

```bash
export OMEGA_FEDERATION_URL="http://localhost:9405"
export OMEGA_API_KEY="your-api-key"
export OMEGA_TENANT_ID="acme"
export OMEGA_ACTOR_ID="clint"
export OMEGA_TIMEOUT_MS="120000"
export OMEGA_MAX_RETRIES="3"
```

### Programmatic Configuration

```python
from omega_sdk import OmegaClient, OmegaConfig

config = OmegaConfig(
    federation_url="http://localhost:9405",
    api_key="your-api-key",
    tenant_id="acme",
    actor_id="clint",
    timeout_ms=120000,
    max_retries=3,
)

client = OmegaClient(config=config)
```

## Correlation Discipline

**Every request requires a canonical correlation ID:**

```python
from omega_sdk.utils import make_correlation_id

# Auto-generated (recommended)
tools = await client.tools.list()  # Correlation ID auto-generated

# Explicit (for distributed tracing)
correlation_id = make_correlation_id("acme")
tools = await client.tools.list(correlation_id=correlation_id)
```

**Canonical format:** `t:<tenant>|c:<uuidv7>`

## Governance Hooks (Receipt Threading)

For "execute-like" operations that require governance proof:

```python
result = await client.tools.invoke(
    "csv_processor",
    input={"file": "sensitive_data.csv"},
    decision_receipt_id="kr_01H...",  # From Keon decision
    tags=["prod", "pii"]
)

# Audit metadata includes receipt linkage
print(result.audit.keon_receipt_id)
print(result.audit.evidence_pack_id)
```

## Error Handling

All errors are structured and correlation-aware:

```python
from omega_sdk.errors import (
    OmegaError,
    ValidationError,
    NotFoundError,
    RateLimitError,
)

try:
    result = await client.tools.invoke("nonexistent_tool", input={})
except NotFoundError as e:
    print(f"Tool not found: {e.message}")
    print(f"Correlation: {e.correlation_id}")
    print(f"Request ID: {e.request_id}")
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    print(f"Field errors: {e.details['field_errors']}")
except RateLimitError as e:
    print(f"Rate limited, retry after: {e.details['retry_after_ms']}ms")
    if e.retryable:
        # SDK will auto-retry with exponential backoff
        pass
except OmegaError as e:
    print(f"OMEGA error: {e.code} - {e.message}")
```

## Async Context Manager

```python
async with OmegaClient.from_env() as client:
    tools = await client.tools.list()
    # Client automatically closed on exit
```

## API Reference

### OmegaClient

- `tools.list()` - List available tools
- `tools.get(tool_id)` - Get tool details
- `tools.invoke(tool_id, input)` - Invoke a tool synchronously
- `agents.list()` - List registered agents
- `agents.get(agent_id)` - Get agent details
- `tasks.create(task_type, input)` - Create an asynchronous task
- `tasks.get(task_id)` - Get task status
- `health()` - Health check
- `status()` - Rich status (dependencies, build info)

## Development

### Install Dev Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
pytest --cov=omega_sdk --cov-report=html
```

### Linting & Formatting

```bash
black src tests
ruff src tests
mypy src
```

## Architecture

```
Developer App
     ↓
OMEGA SDK (thin HTTP client)
     ↓
Federation Core :9405/api/v1
     ↓
[Internal Routing]
     ↓
Titans, Agents, Tools, Services
```

**SDK Responsibility:**
- HTTP communication
- Correlation discipline
- Structured errors
- Retry logic
- Optional governance hooks

**NOT SDK Responsibility:**
- Routing decisions
- Titan orchestration
- Service discovery
- Genesis Protocol

## License

MIT

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## Support

- **Issues:** [GitHub Issues](https://github.com/omega-systems/omega-sdk-python/issues)
- **Docs:** [docs.omega.dev/sdk/python](https://docs.omega.dev/sdk/python)
