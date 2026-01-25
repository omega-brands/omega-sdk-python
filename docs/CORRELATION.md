# Correlation Discipline

OMEGA SDK enforces strict correlation discipline to ensure traceability across distributed systems.

## Canonical Format

Every request requires a correlation ID in the canonical format:

```
t:<TenantId>|c:<UUIDv7>
```

Where:
- `t:` is the tenant prefix
- `<TenantId>` is the tenant identifier (must not contain `|`)
- `c:` is the correlation prefix
- `<UUIDv7>` is a time-ordered UUID (RFC 9562)

### Examples

```python
t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789
t:my-org|c:0194f0b0-5678-9abc-def0-123456789abc
```

## Auto-Generation

The SDK automatically generates correlation IDs when not provided:

```python
from omega_sdk import OmegaClient

client = OmegaClient.from_env()

# Correlation ID auto-generated from tenant_id
tools = await client.tools.list()
```

## Explicit Correlation IDs

For distributed tracing or when you need to track operations across services:

```python
from omega_sdk import OmegaClient
from omega_sdk.utils import make_correlation_id

client = OmegaClient.from_env()

# Create correlation ID once
correlation_id = make_correlation_id("acme")

# Use same correlation ID across multiple operations
tools = await client.tools.list(correlation_id=correlation_id)
result = await client.tools.invoke(
    "csv_processor",
    input={"file": "data.csv"},
    correlation_id=correlation_id
)
```

## Validation

The SDK validates correlation IDs on every request:

```python
from omega_sdk.utils import validate_correlation_id, CorrelationError

try:
    tenant, uuid = validate_correlation_id("t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789")
    print(f"Tenant: {tenant}")
    print(f"UUID: {uuid}")
except CorrelationError as e:
    print(f"Invalid correlation ID: {e}")
```

## Error Tracking

All errors include the correlation ID:

```python
from omega_sdk import OmegaClient
from omega_sdk.errors import OmegaError

client = OmegaClient.from_env()

try:
    result = await client.tools.invoke("nonexistent", input={})
except OmegaError as e:
    print(f"Error: {e.message}")
    print(f"Correlation ID: {e.correlation_id}")
    print(f"Request ID: {e.request_id}")
```

## Benefits

1. **Distributed Tracing**: Track operations across Federation Core, Titans, Agents, and Services
2. **Time-Ordered**: UUIDv7 provides chronological ordering
3. **Tenant Isolation**: Correlation IDs are scoped to tenants
4. **Debuggability**: Every error includes correlation + request IDs for support

## Best Practices

### ✅ DO

- Let the SDK auto-generate correlation IDs for single operations
- Create explicit correlation IDs for multi-step workflows
- Include correlation IDs in your application logs
- Pass correlation IDs to external services when integrating

### ❌ DON'T

- Don't create correlation IDs with invalid formats
- Don't reuse correlation IDs across tenants
- Don't use arbitrary UUIDs (use UUIDv7 for time ordering)
- Don't include sensitive data in tenant IDs

## Integration with Keon

Correlation IDs are part of the Keon governance model. They appear in:

- Decision receipts
- Audit events
- Evidence packs
- Compliance reports

This ensures full traceability from application request → Federation Core → Agent → Tool → Evidence.
