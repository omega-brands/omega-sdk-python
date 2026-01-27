# KEON + OMEGA SDK Integration Seams

> **STATUS:** SCAFFOLDING ONLY — Ready for Keon evidence wiring
> **MERGE AUTHORITY:** ❌ NONE until Gemini clears Campaign II

---

## Purpose

This document identifies all integration points between the OMEGA SDK and Keon Core.
These are **structural shells** that will be wired to verified truth once Keon Control
evidence browser exists.

**This document prepares the world for Keon. It does NOT:**
- Define trust semantics
- Implement evidence validation
- Create governance logic
- Interpret evidence

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OMEGA SDK                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  OmegaClient                                                            ││
│  │    ├── tools.list() / get() / invoke()                                  ││
│  │    ├── agents.list() / get()                                            ││
│  │    ├── tasks.create() / get()                                           ││
│  │    └── health() / status()                                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  KEON INTEGRATION SEAMS                                                 ││
│  │    [1] Correlation ID → Keon canonical format                           ││
│  │    [2] Receipt Threading → decision_receipt_id header                   ││
│  │    [3] Audit Metadata → keon_receipt_id, evidence_pack_id               ││
│  │    [4] Trust Display → (STUB) trust level, evidence links               ││
│  │    [5] Evidence Browser → (STUB) Keon Control connection                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  FederationCoreGateway (HTTP Layer)                                     ││
│  │    Headers: X-Correlation-Id, X-Tenant-Id, X-Actor-Id                   ││
│  │             X-Keon-Receipt-Id (when governance enabled)                 ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │   Federation Core      │
                        │   :9405/api/v1/*       │
                        └────────────────────────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │   KEON CORE (STUB)     │
                        │   Evidence Browser     │
                        │   Trust Verification   │
                        └────────────────────────┘
```

---

## Seam 1: Correlation ID Discipline

**Location:** `src/omega_sdk/utils/correlation.py`
**Status:** ✅ IMPLEMENTED — Follows Keon canonical format

### Current Behavior
- Generates correlation IDs in format: `t:<tenant>|c:<uuidv7>`
- Validates format on every request
- Injects into `X-Correlation-Id` header

### Keon Wiring Points
```python
# correlation.py already implements Keon-compatible format
CANONICAL_PATTERN = r"^t:([a-z0-9_-]+)\|c:([a-f0-9-]{36})$"

def make_correlation_id(tenant_id: str) -> str:
    """Generate canonical correlation ID for Keon."""
    uid = uuid7().hex[:36]  # UUIDv7 for time-ordering
    return f"t:{tenant_id}|c:{uid}"
```

### When Keon Lands
- No code changes required
- Keon will recognize these correlation IDs natively
- Evidence browser will link correlation IDs to audit trail

---

## Seam 2: Receipt Threading

**Location:** `src/omega_sdk/models.py` (ToolInvokeContext, TaskGovernance)
**Status:** ✅ IMPLEMENTED — Structural shell ready

### Current Behavior
- `decision_receipt_id` field on `ToolInvokeContext`
- `require_receipt` flag on `TaskGovernance`
- Header `X-Keon-Receipt-Id` sent when receipt ID provided

### Model Definitions
```python
# models.py
class ToolInvokeContext(BaseModel):
    decision_receipt_id: Optional[str] = Field(
        None, description="Decision receipt ID (if required by policy)"
    )

class TaskGovernance(BaseModel):
    require_receipt: Optional[bool] = Field(None, description="Require decision receipt")
    decision_receipt_id: Optional[str] = Field(None, description="Pre-decided receipt ID")
    policy_tags: List[str] = Field(default_factory=list, description="Policy tags")
```

### Usage Example
```python
# When calling a tool with governance
result = await client.tools.invoke(
    "sensitive_operation",
    input={"data": "..."},
    context=ToolInvokeContext(
        decision_receipt_id="t:acme|r:01234567-89ab-cdef-0123-456789abcdef"
    )
)
```

### When Keon Lands
- Set `require_receipts: true` in config
- Keon will validate receipt IDs before allowing operations
- Invalid receipts will return `ForbiddenError`

---

## Seam 3: Audit Metadata

**Location:** `src/omega_sdk/models.py` (ToolInvokeAudit, TaskAudit)
**Status:** ✅ IMPLEMENTED — Ready to receive Keon metadata

### Current Behavior
- `keon_receipt_id` returned in audit metadata when present
- `evidence_pack_id` returned when evidence is generated
- Metadata flows through to caller unchanged

### Model Definitions
```python
# models.py
class ToolInvokeAudit(BaseModel):
    event_id: str
    timestamp: str
    keon_receipt_id: Optional[str] = Field(None, description="Keon receipt ID (if governed)")
    evidence_pack_id: Optional[str] = Field(None, description="Evidence pack ID (if applicable)")

class TaskAudit(BaseModel):
    event_id: str
    started_at: str
    completed_at: Optional[str] = None
    keon_receipt_id: Optional[str] = Field(None, description="Keon receipt ID (if governed)")
    evidence_pack_id: Optional[str] = Field(None, description="Evidence pack ID (if applicable)")
```

### Usage Example
```python
# After invoking a tool
result = await client.tools.invoke("csv_processor", input={...})

if result.audit:
    print(f"Event ID: {result.audit.event_id}")
    if result.audit.keon_receipt_id:
        print(f"Keon Receipt: {result.audit.keon_receipt_id}")
        # SEAM: When Keon lands, this links to evidence browser
    if result.audit.evidence_pack_id:
        print(f"Evidence: {result.audit.evidence_pack_id}")
```

### When Keon Lands
- Federation Core will populate these fields automatically
- SDK consumers can link directly to evidence browser
- No SDK code changes required

---

## Seam 4: Trust Display (STUB)

**Location:** Not yet implemented
**Status:** 🟡 STUB — Shell prepared, waiting for Keon Control

### Planned Behavior
- Display trust level in CLI output
- Show evidence links in responses
- Embed governance state in results

### Config Stub
```yaml
# keon_omega.yaml
keon:
  trust_display:
    show_trust_level: false      # STUB: Set true when TrustOps lands
    show_evidence_links: false
    show_governance_state: false
```

### Expected Output Format (When Wired)
```
$ omega invoke csv_processor --file data.csv
✓ Tool invocation successful
  Result: { ... }

  Trust: VERIFIED ████████████ 100%
  Evidence: https://keon.control/evidence/t:acme|e:01234567...
  Governance: compliant (receipt: t:acme|r:01234567...)
```

### Integration Contract
When Keon Control lands:
1. SDK will fetch trust status via `KEON_EVIDENCE_BROWSER_URL`
2. Trust levels: `NONE`, `LOW`, `MEDIUM`, `HIGH`, `VERIFIED`
3. Evidence links follow format: `{KEON_BASE}/evidence/{evidence_pack_id}`
4. Governance state is immutable once receipt is issued

---

## Seam 5: Evidence Browser Connection (STUB)

**Location:** Not yet implemented
**Status:** 🟡 STUB — Waiting for Keon Control evidence browser

### Planned Behavior
- Connect to Keon Control evidence browser
- Fetch trust status before operations
- Generate dashboard links automatically

### Config Stub
```yaml
# keon_omega.yaml
keon:
  evidence_browser:
    enabled: false  # STUB: Set true when Keon Control lands
    url: "${KEON_EVIDENCE_BROWSER_URL:-}"
```

### Expected API Contract
```
GET /api/v1/evidence/{evidence_pack_id}
Response:
{
  "trust_level": "VERIFIED",
  "created_at": "2025-01-25T12:00:00Z",
  "correlation_id": "t:acme|c:...",
  "receipt_chain": [...],
  "artifacts": [...]
}
```

### Integration Contract
When Keon Control lands:
1. Evidence browser will expose REST API at `/api/v1/evidence/*`
2. SDK will call this API to fetch trust status
3. Response includes full audit trail and evidence artifacts
4. Links are generated automatically from evidence_pack_id

---

## Assumptions

These assumptions are documented so they can be validated when Keon lands:

| # | Assumption | Validation |
|---|------------|------------|
| 1 | Keon Evidence Browser exposes REST API at `/api/v1/evidence/*` | Check Keon Control API spec |
| 2 | Trust levels are: NONE, LOW, MEDIUM, HIGH, VERIFIED | Verify against Keon Core enums |
| 3 | Receipt IDs follow format: `t:<tenant>\|r:<uuidv7>` | Validate against Keon SDK |
| 4 | Evidence pack IDs follow format: `t:<tenant>\|e:<uuidv7>` | Validate against Keon SDK |
| 5 | Governance state is immutable once a receipt is issued | Confirm Keon Core behavior |

If any assumption is wrong, update this document and corresponding config files.

---

## Wiring Checklist

When Keon Control evidence browser is ready:

- [ ] Update `examples/config/keon_omega.yaml` with real Keon URLs
- [ ] Set `evidence_browser.enabled: true`
- [ ] Set `governance.require_receipts: true` for production
- [ ] Set `trust_display` flags to true
- [ ] Validate assumptions against actual Keon API
- [ ] Update examples to demonstrate trust display
- [ ] Run integration tests against Keon Control

---

## Dependencies

This scaffolding depends on:

| Dependency | Owner | Status |
|------------|-------|--------|
| Keon Core evidence browser | Gemini (Campaign II) | ⏳ Pending |
| Key lifecycle UX | Gemini (Campaign II) | ⏳ Pending |
| TrustOps documentation | Gemini (Campaign II) | ⏳ Pending |

Merges are blocked until these dependencies are cleared.

---

## File Index

| File | Purpose |
|------|---------|
| `examples/hello_world.py` | Minimal OMEGA app with Keon seams marked |
| `examples/config/keon_omega.yaml` | Full Keon integration config stub |
| `examples/config/.env.keon.example` | Environment variable template |
| `src/omega_sdk/utils/correlation.py` | Keon-compatible correlation IDs |
| `src/omega_sdk/models.py` | Audit metadata models (keon_receipt_id, evidence_pack_id) |
| `docs/KEON_INTEGRATION_SEAMS.md` | This document |

---

*Last updated: 2025-01-25*
*Orchestrator: Claude (Product Proof & Integration)*
*Status: SCAFFOLDING ONLY — NO MERGE AUTHORITY*
