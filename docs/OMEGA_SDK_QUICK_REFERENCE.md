# OMEGA SDK v2.0 - Quick Reference Card

**For Agent Team** - Keep this handy during build!

---

## 🎯 Core Principle

```
SDK is a THIN HTTP CLIENT to federation_core.
Federation_core handles ALL internal routing.
SDK does NOT orchestrate Titans, Genesis, or services directly.
```

---

## 📦 Package Structure (What You're Building)

```
omega-sdk/
├── omega_sdk/
│   ├── __init__.py         # Exports: OmegaClient, KEONConfig, models
│   ├── client.py           # OmegaClient (HTTP to federation_core)
│   ├── conversation.py     # Conversation tracking
│   ├── utilities.py        # ⭐ COPY from tests/helpers/
│   ├── keon.py             # KEON governance
│   ├── models.py           # Pydantic models
│   ├── config.py           # Configuration
│   └── exceptions.py       # Custom exceptions
├── tests/                  # >80% coverage
├── examples/               # Working examples
└── docs/                   # Full documentation
```

---

## ⭐ CRITICAL: Battle-Tested Utilities

**DO NOT WRITE FROM SCRATCH!**

**COPY from**: `forgepilot-api/tests/helpers/federation_helpers.py`

**What to copy**:
- ✅ `ConversationPoller` (adaptive polling with backoff)
- ✅ `PhaseTracker` (phase progression tracking)
- ✅ `ArtifactValidator` (output validation)
- ✅ `TitanParticipationTracker` (Titan tracking)

**Why**: These are proven in production tests. Don't reinvent!

---

## 🏗️ Core Classes to Build

### 1. OmegaClient (client.py)
```python
class OmegaClient:
    def __init__(federation_url, api_key, keon, timeout)
    async def create_conversation(workflow_type, inputs, user_consent_token, on_progress) -> Conversation
    async def get_conversation(conversation_id) -> ConversationStatus
    async def health_check() -> bool
```

**Purpose**: Thin HTTP wrapper around federation_core

### 2. Conversation (conversation.py)
```python
class Conversation:
    def __init__(conversation_id, client, on_progress)
    async def wait_for_completion(timeout) -> ConversationResult
    async def get_status() -> ConversationStatus
    async def get_artifacts() -> dict
```

**Purpose**: Track conversation progress with polling

### 3. Models (models.py)
```python
class WorkflowState(Enum): PENDING, RUNNING, COMPLETED, FAILED
class ConversationStatus(BaseModel): conversation_id, state, current_phase, completion_percentage, ...
class ConversationResult(BaseModel): conversation_id, status, artifacts
class BrandCampaignInputs(BaseModel): business_idea, target_audience, brand_values
class JobApplicationInputs(BaseModel): resume_text, job_description, cover_letter_tone
```

**Purpose**: Type-safe data models (Pydantic)

### 4. KEONConfig (keon.py)
```python
@dataclass
class KEONConfig:
    require_consent: bool = True
    audit_trail: bool = True
    data_privacy: Literal["strict", "standard", "minimal"] = "strict"
    transparency_level: Literal["full", "summary", "minimal"] = "full"

class KEONHelper:
    @staticmethod
    def validate_consent_token(token) -> bool
    @staticmethod
    def create_audit_entry(conversation_id, action, user_id) -> dict
```

**Purpose**: KEON governance helpers

---

## 📍 Federation Core Endpoints (What SDK Calls)

```
Base URL: http://localhost:9405

POST   /mcp/collaboration/conversational  # Create conversation
GET    /mcp/conversations/{id}            # Get conversation status
GET    /mcp/conversations/{id}/artifacts  # Get artifacts
GET    /mcp/health                        # Health check
```

**Note**: These are the ONLY endpoints SDK calls. Everything else is internal to federation_core.

---

## ✅ Definition of Done (Every PR)

- [ ] Code written
- [ ] Type hints added (all functions)
- [ ] Docstrings with examples
- [ ] Tests passing (if applicable)
- [ ] Mypy passing (zero errors)
- [ ] Reviewed by SDK Architect
- [ ] CHANGELOG updated
- [ ] Merged to main

---

## 🧪 Testing Requirements

**Coverage**: >80%

**Test files**:
- `tests/test_client.py` (10+ tests)
- `tests/test_conversation.py` (5+ tests)
- `tests/test_utilities.py` (8+ tests)
- `tests/test_keon.py` (5+ tests)
- `tests/test_models.py` (5+ tests)

**Integration tests**: Must test against live federation_core at `http://localhost:9405`

---

## 📘 Documentation Requirements

**Required docs**:
- `README.md` (compelling, 5-line quick start)
- `docs/quickstart.md` (5-minute guide)
- `docs/api-reference.md` (all public APIs)
- `docs/keon-governance.md` (KEON guide)
- `docs/examples.md` (usage examples)
- `CHANGELOG.md` (version history)

**Docstring format**:
```python
def create_conversation(
    self,
    workflow_type: str,
    inputs: dict[str, Any],
    user_consent_token: Optional[str] = None,
    on_progress: Optional[Callable] = None
) -> Conversation:
    """
    Start conversational workflow via federation_core.

    Args:
        workflow_type: Type of workflow (e.g., "brand_campaign")
        inputs: Workflow inputs (validated by federation_core)
        user_consent_token: KEON consent token (required if keon.require_consent)
        on_progress: Optional callback for progress updates

    Returns:
        Conversation object for tracking

    Raises:
        KEONConsentRequired: If consent required but not provided
        OmegaError: For other API errors

    Example:
        >>> client = OmegaClient()
        >>> conversation = await client.create_conversation(
        ...     workflow_type="brand_campaign",
        ...     inputs={"business_idea": "AI fitness app", ...}
        ... )
        >>> result = await conversation.wait_for_completion()
    """
```

---

## 🎨 Code Style

**Formatting**: Black (line length: 100)

**Linting**: Ruff

**Type checking**: mypy (strict mode)

**Python version**: >=3.12

**Async**: Use `async/await` throughout

**Imports**: Sort with `isort`

---

## 📅 Timeline Quick Reference

### Week 1 (Days 1-7): Core
- Project structure
- models.py, keon.py, config.py, exceptions.py
- utilities.py (COPY from tests)
- client.py, conversation.py

### Week 2 (Days 8-14): Quality
- Complete test suite
- Type safety (mypy)
- Examples

### Week 3 (Days 15-21): Polish & Ship
- Documentation
- Bug fixes
- **Release v1.0.0** 🚀

---

## 🚨 Common Pitfalls (Avoid These!)

### ❌ DON'T
- Don't rewrite utilities from scratch (copy from tests!)
- Don't add direct Titan orchestration to SDK
- Don't add Genesis Protocol APIs without approval
- Don't make assumptions about federation_core internals
- Don't skip type hints
- Don't skip docstrings
- Don't merge without SDK Architect review

### ✅ DO
- Copy battle-tested utilities from tests
- Keep SDK as thin HTTP client
- Let federation_core handle routing
- Add comprehensive type hints
- Write clear docstrings with examples
- Get code reviewed before merging
- Update CHANGELOG for every change

---

## 🔗 Key File Locations

### Source Code (Copy From)
- `forgepilot-api/tests/helpers/federation_helpers.py` ⭐ **CRITICAL**
- `forgepilot-api/app/clients/federation_client.py`
- `forgepilot-api/tests/integration/test_*.py`

### OMEGA Doctrine (Reference)
- `D:\Repos\OMEGA\omega-docs\doctrine\OMEGA_DOCTRINE_FINAL_v1.0.md`
- `D:\Repos\OMEGA\omega-docs\doctrine\federation_control_plane.md`
- `D:\Repos\OMEGA\omega-docs\doctrine\CONVERSATIONAL_PANTHEON_API.md`

### Directives (Your Instructions)
- `OMEGA_SDK_DIRECTIVE_V2.md` (complete spec)
- `OMEGA_SDK_AGENT_ASSIGNMENT_V2.md` (your role)
- `OMEGA_SDK_HANDOFF_V2.md` (executive summary)

---

## 💬 Daily Standup Format

**Post in shared channel daily**:

```
Agent: [Your Name]
✅ Completed: [What you finished yesterday]
🚧 Working on: [What you're doing today]
🚨 Blockers: [Any issues, or "None"]
```

---

## 🎯 Success Metrics (Ship Checklist)

### Code Quality
- [ ] >80% test coverage
- [ ] Zero mypy errors
- [ ] Full type hints
- [ ] Comprehensive docstrings

### Developer Experience
- [ ] 5-line quick start works
- [ ] Progress callbacks work
- [ ] Error messages are clear
- [ ] KEON compliance automatic

### Production Ready
- [ ] Retry with backoff implemented
- [ ] Exception handling complete
- [ ] Environment variable support
- [ ] Battle-tested utilities integrated

### Documentation
- [ ] README is compelling
- [ ] API reference complete
- [ ] Examples all work
- [ ] KEON guide written

---

## 🚀 When in Doubt

1. **Check directive**: `OMEGA_SDK_DIRECTIVE_V2.md`
2. **Check assignment**: `OMEGA_SDK_AGENT_ASSIGNMENT_V2.md`
3. **Copy from tests**: `forgepilot-api/tests/helpers/`
4. **Ask SDK Architect**: Don't guess, clarify!

---

## This is the fucking way! 🚀

**Keep it simple. Copy proven code. Ship quality.**

---

**Quick Links**:
- Directives: `D:\Repos\forgepilot\OMEGA_SDK_DIRECTIVE_V2.md`
- Battle-tested utilities: `forgepilot-api/tests/helpers/federation_helpers.py`
- OMEGA Doctrine: `D:\Repos\OMEGA\omega-docs\doctrine/`

**Remember**: SDK is a **thin HTTP client**. Federation_core does the heavy lifting!
