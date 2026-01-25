# OMEGA SDK Quick Reference

One-page cheat sheet for common operations.

## Installation

```bash
pip install omega-sdk
```

## Client Setup

```python
from omega_sdk import OmegaClient

# From environment
client = OmegaClient.from_env()

# Explicit config
client = OmegaClient(
    federation_url="http://localhost:9405",
    tenant_id="acme",
    actor_id="clint",
)
```

## Tools

```python
# List tools
tools = await client.tools.list()
tools = await client.tools.list(capability="data", limit=10)

# Get tool
tool = await client.tools.get("csv_processor")

# Invoke tool
result = await client.tools.invoke(
    "csv_processor",
    input={"file": "data.csv"},
    tags=["prod"],
)
```

## Agents

```python
# List agents
agents = await client.agents.list()
agents = await client.agents.list(kind="titan")

# Get agent
agent = await client.agents.get("gpt_titan")
```

## Tasks

```python
from omega_sdk.models import TaskRouting, TaskGovernance

# Create task
task = await client.tasks.create(
    task_type="workflow.run",
    input={"workflow": "brand_campaign"},
    routing=TaskRouting(strategy="capability", capability="branding"),
)

# Get task status
status = await client.tasks.get(task.task_id)
```

## Correlation IDs

```python
from omega_sdk.utils import make_correlation_id

# Auto-generated (recommended)
tools = await client.tools.list()

# Explicit
cid = make_correlation_id("acme")
tools = await client.tools.list(correlation_id=cid)
```

## Governance

```python
# Receipt threading
result = await client.tools.invoke(
    "csv_processor",
    input={"file": "sensitive.csv"},
    decision_receipt_id="kr_01H...",  # From Keon
    tags=["prod", "pii"],
)

# Access audit metadata
print(result.audit.keon_receipt_id)
print(result.audit.evidence_pack_id)
```

## Error Handling

```python
from omega_sdk.errors import (
    OmegaError,
    NotFoundError,
    ValidationError,
    RateLimitError,
)

try:
    result = await client.tools.invoke("tool_id", input={})
except NotFoundError as e:
    print(f"Not found: {e.message}")
    print(f"Correlation: {e.correlation_id}")
except ValidationError as e:
    print(f"Validation: {e.details['field_errors']}")
except RateLimitError as e:
    print(f"Rate limited: {e.details['retry_after_ms']}ms")
except OmegaError as e:
    print(f"Error: {e.code} - {e.message}")
```

## Context Manager

```python
async with OmegaClient.from_env() as client:
    tools = await client.tools.list()
    # Client auto-closed
```

## Configuration

```python
from omega_sdk import OmegaConfig

config = OmegaConfig(
    federation_url="http://localhost:9405",
    api_key="your-key",
    tenant_id="acme",
    actor_id="clint",
    timeout_ms=120000,  # 2 minutes
    max_retries=3,
)

client = OmegaClient(config=config)
```

## Environment Variables

```bash
OMEGA_FEDERATION_URL=http://localhost:9405
OMEGA_API_KEY=your-api-key
OMEGA_TENANT_ID=acme
OMEGA_ACTOR_ID=clint
OMEGA_TIMEOUT_MS=120000
OMEGA_MAX_RETRIES=3
```

## Common Patterns

### Paginated List

```python
cursor = None
while True:
    tools = await client.tools.list(limit=50, cursor=cursor)
    for tool in tools.items:
        print(tool.tool_id)

    if not tools.page.next_cursor:
        break
    cursor = tools.page.next_cursor
```

### Task Polling

```python
from omega_sdk.models import TaskStatus

task = await client.tasks.create(...)

while True:
    status = await client.tasks.get(task.task_id)
    print(f"Status: {status.status}")

    if status.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        break

    await asyncio.sleep(5)
```

### Distributed Tracing

```python
from omega_sdk.utils import make_correlation_id

# Create once, use across operations
cid = make_correlation_id("acme")

# Step 1
tools = await client.tools.list(correlation_id=cid)

# Step 2
result = await client.tools.invoke(
    "csv_processor",
    input={"file": "data.csv"},
    correlation_id=cid,
)

# Step 3
task = await client.tasks.create(
    task_type="workflow.run",
    input={"data": result.result},
    # correlation_id passed through task context automatically
)
```

## Testing

```python
import pytest
from omega_sdk import OmegaClient

@pytest.fixture
async def client():
    async with OmegaClient.from_env() as c:
        yield c

@pytest.mark.asyncio
async def test_list_tools(client):
    tools = await client.tools.list()
    assert len(tools.items) > 0
```

## Troubleshooting

### Connection Refused

```python
# Check Federation Core is running
health = await client.health()
print(health.status)
```

### Authentication Failed

```python
# Verify API key
config = OmegaConfig.from_env()
print(config.api_key)
```

### Correlation ID Invalid

```python
from omega_sdk.utils import validate_correlation_id

try:
    validate_correlation_id("invalid")
except CorrelationError as e:
    print(e)
```

### Rate Limiting

```python
from omega_sdk.errors import RateLimitError

try:
    result = await client.tools.invoke(...)
except RateLimitError as e:
    retry_after = e.details.get("retry_after_ms", 5000)
    await asyncio.sleep(retry_after / 1000)
    # Retry automatically handled by SDK
```
