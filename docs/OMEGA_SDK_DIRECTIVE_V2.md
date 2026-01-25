# OMEGA SDK - Build Directive v2.0
## Aligned with OMEGA Doctrine

**Status**: Ready for agent team execution
**Architecture**: Federation-first, KEON-governed, Doctrine-compliant
**Timeline**: 3 weeks to v1.0.0

---

## Core Principle: Federation Core is the Control Plane

```
Developer App (ForgePilot, SilentApply, etc.)
           ↓
     OMEGA SDK (thin HTTP client)
           ↓
  Federation Core :9405/mcp/*
           ↓
  [Internal Routing - NOT SDK's concern]
           ↓
    Titans, Agents, Tools, Services
```

**The SDK's job**: Provide clean, typed, battle-tested interface to federation_core.

**NOT the SDK's job**: Routing, Titan orchestration, Genesis Protocol, service discovery.

---

## What Developers Get

### Simple Campaign Creation
```python
from omega_sdk import OmegaClient

client = OmegaClient(federation_url="http://localhost:9405")

# Start a conversational workflow
conversation = await client.create_conversation(
    workflow_type="brand_campaign",
    inputs={
        "business_idea": "AI fitness app",
        "target_audience": "Millennials",
        "brand_values": ["innovation", "health"]
    }
)

# Poll for completion with progress tracking
result = await conversation.wait_for_completion(
    on_progress=lambda status: print(f"{status.phase}: {status.progress}%")
)

# Access artifacts
print(f"Brand: {result.artifacts['brand_name']}")
print(f"Domains: {result.artifacts['available_domains']}")
```

### KEON Governance Built-in
```python
from omega_sdk import OmegaClient, KEONConfig

client = OmegaClient(
    federation_url="http://localhost:9405",
    keon=KEONConfig(
        require_consent=True,
        audit_trail=True,
        data_privacy="strict"
    )
)

# KEON compliance automatic for every request
conversation = await client.create_conversation(
    workflow_type="job_application",
    user_consent_token="user-consent-xyz",  # KEON validates
    inputs={...}
)
```

### Genesis Protocol (If Exposed)
```python
# DECISION NEEDED: Should devs create custom agents via Genesis?
# Option A: Genesis is internal-only (not in SDK)
# Option B: Genesis exposed for custom agent creation

# Option B implementation:
agent_spec = await client.genesis.create_agent(
    name="CustomBrandAnalyzer",
    capabilities=["brand_research", "market_analysis"],
    passport_metadata={...}
)

# Agent gets immutable passport, managed by federation_core
print(f"Agent passport: {agent_spec.passport_id}")
```

---

## SDK Architecture

### Package Structure
```
omega-sdk/
├── omega_sdk/
│   ├── __init__.py           # Public API: OmegaClient, KEONConfig
│   ├── client.py             # OmegaClient (main class)
│   ├── conversation.py       # Conversation management
│   ├── utilities.py          # Battle-tested helpers (from tests)
│   ├── keon.py               # KEON governance helpers
│   ├── genesis.py            # Genesis Protocol (if exposed)
│   ├── models.py             # Pydantic models
│   ├── config.py             # Configuration
│   └── exceptions.py         # Custom exceptions
├── tests/                    # >80% coverage
├── examples/                 # Working examples
└── docs/                     # Full documentation
```

### Core Components

#### 1. OmegaClient (Federation HTTP Client)

```python
class OmegaClient:
    """
    Main SDK client. Thin HTTP wrapper around federation_core.

    Federation_core handles:
    - Routing to Titans, agents, tools, services
    - Genesis Protocol (internal tool creation)
    - Multi-Titan orchestration
    - Service discovery

    SDK handles:
    - HTTP communication
    - Conversation management
    - Progress polling
    - KEON compliance
    - Error handling
    - Retry logic
    """

    def __init__(
        self,
        federation_url: str = "http://localhost:9405",
        api_key: Optional[str] = None,
        keon: Optional[KEONConfig] = None,
        timeout: float = 120.0
    ):
        self.federation_url = federation_url
        self.keon = keon or KEONConfig()
        self._http_client = httpx.AsyncClient(timeout=timeout)

    async def create_conversation(
        self,
        workflow_type: str,
        inputs: dict[str, Any],
        user_consent_token: Optional[str] = None,
        on_progress: Optional[Callable] = None
    ) -> Conversation:
        """
        Start a conversational workflow via federation_core.

        Federation_core determines:
        - Which Titans to use
        - Whether to invoke Genesis Protocol
        - Phase routing and orchestration

        Returns Conversation object for tracking.
        """
        # KEON validation
        if self.keon.require_consent and not user_consent_token:
            raise KEONConsentRequired("User consent required")

        # POST to federation_core
        response = await self._http_client.post(
            f"{self.federation_url}/mcp/collaboration/conversational",
            json={
                "workflow_type": workflow_type,
                "inputs": inputs,
                "user_consent_token": user_consent_token
            }
        )

        data = response.json()
        conversation_id = data["conversation_id"]

        # Return Conversation for tracking
        return Conversation(
            conversation_id=conversation_id,
            client=self,
            on_progress=on_progress
        )

    async def get_conversation(
        self,
        conversation_id: str
    ) -> ConversationStatus:
        """Get current status of a conversation."""
        response = await self._http_client.get(
            f"{self.federation_url}/mcp/conversations/{conversation_id}"
        )
        return ConversationStatus(**response.json())

    async def health_check(self) -> bool:
        """Check federation_core health."""
        try:
            response = await self._http_client.get(
                f"{self.federation_url}/mcp/health"
            )
            return response.json()["status"] == "healthy"
        except Exception:
            return False
```

#### 2. Conversation (Progress Tracking)

```python
class Conversation:
    """
    Manages a single conversation with federation_core.

    Provides:
    - Progress polling (adaptive backoff)
    - Phase tracking
    - Artifact retrieval
    - Completion waiting
    """

    def __init__(
        self,
        conversation_id: str,
        client: OmegaClient,
        on_progress: Optional[Callable] = None
    ):
        self.conversation_id = conversation_id
        self.client = client
        self.on_progress = on_progress
        self._poller = ConversationPoller(client, conversation_id)

    async def wait_for_completion(
        self,
        timeout: float = 300.0
    ) -> ConversationResult:
        """
        Poll until conversation completes.

        Uses adaptive backoff:
        - Start: 1s intervals
        - After 30s: 2s intervals
        - After 60s: 5s intervals
        """
        status = await self._poller.poll_until_complete(
            timeout=timeout,
            on_progress=self.on_progress
        )

        # Fetch final artifacts
        artifacts = await self.get_artifacts()

        return ConversationResult(
            conversation_id=self.conversation_id,
            status=status,
            artifacts=artifacts
        )

    async def get_status(self) -> ConversationStatus:
        """Get current status without polling."""
        return await self.client.get_conversation(self.conversation_id)

    async def get_artifacts(self) -> dict[str, Any]:
        """Retrieve conversation artifacts."""
        response = await self.client._http_client.get(
            f"{self.client.federation_url}/mcp/conversations/{self.conversation_id}/artifacts"
        )
        return response.json()
```

#### 3. Utilities (Battle-Tested from Tests)

**CRITICAL**: Copy directly from `forgepilot-api/tests/helpers/federation_helpers.py`

```python
class ConversationPoller:
    """
    Adaptive polling for conversation completion.

    COPIED from forgepilot-api/tests/helpers/federation_helpers.py
    PROVEN in integration tests.
    """

    def __init__(self, client: OmegaClient, conversation_id: str):
        self.client = client
        self.conversation_id = conversation_id

    async def poll_until_complete(
        self,
        timeout: float = 300.0,
        on_progress: Optional[Callable] = None
    ) -> ConversationStatus:
        """
        Poll with exponential backoff until complete or timeout.

        Backoff strategy:
        - 0-30s: 1s intervals
        - 30-60s: 2s intervals
        - 60s+: 5s intervals
        """
        start_time = time.time()
        last_phase = None

        while True:
            elapsed = time.time() - start_time

            if elapsed > timeout:
                raise TimeoutError(f"Conversation timeout after {timeout}s")

            # Get current status
            status = await self.client.get_conversation(self.conversation_id)

            # Progress callback
            if on_progress and status.current_phase != last_phase:
                on_progress(status)
                last_phase = status.current_phase

            # Check completion
            if status.state == WorkflowState.COMPLETED:
                return status
            elif status.state == WorkflowState.FAILED:
                raise WorkflowFailedError(f"Workflow failed: {status.error}")

            # Adaptive backoff
            if elapsed < 30:
                await asyncio.sleep(1.0)
            elif elapsed < 60:
                await asyncio.sleep(2.0)
            else:
                await asyncio.sleep(5.0)


class PhaseTracker:
    """
    Track phase progression through workflow.

    COPIED from forgepilot-api/tests/helpers/federation_helpers.py
    """

    def __init__(self):
        self.phases_seen = []
        self.phase_timestamps = {}

    def record_phase(self, phase: str):
        """Record a phase transition."""
        if phase not in self.phases_seen:
            self.phases_seen.append(phase)
            self.phase_timestamps[phase] = time.time()

    def assert_phases_in_order(self, expected_phases: list[str]):
        """Validate phases occurred in expected order."""
        assert self.phases_seen == expected_phases


class ArtifactValidator:
    """
    Validate workflow artifacts against expected schemas.

    COPIED from forgepilot-api/tests/helpers/federation_helpers.py
    """

    def __init__(self, expected_artifacts: list[str]):
        self.expected_artifacts = expected_artifacts

    def validate(self, artifacts: dict[str, Any]):
        """Validate all expected artifacts present."""
        missing = set(self.expected_artifacts) - set(artifacts.keys())
        if missing:
            raise ValidationError(f"Missing artifacts: {missing}")


class TitanParticipationTracker:
    """
    Track which Titans participated in a workflow.

    COPIED from forgepilot-api/tests/helpers/federation_helpers.py
    """

    def __init__(self, expected_titans: list[str]):
        self.expected_titans = expected_titans
        self.titans_seen = set()

    def record_titan(self, titan_name: str):
        """Record Titan participation."""
        self.titans_seen.add(titan_name)

    def assert_all_titans_participated(self):
        """Validate all expected Titans participated."""
        missing = set(self.expected_titans) - self.titans_seen
        assert not missing, f"Missing Titans: {missing}"
```

#### 4. KEON Governance

```python
@dataclass
class KEONConfig:
    """KEON governance configuration."""
    require_consent: bool = True
    audit_trail: bool = True
    data_privacy: Literal["strict", "standard", "minimal"] = "strict"
    transparency_level: Literal["full", "summary", "minimal"] = "full"


class KEONHelper:
    """Helper for KEON compliance."""

    @staticmethod
    def validate_consent_token(token: str) -> bool:
        """Validate user consent token format."""
        # Implement KEON token validation
        return bool(token and len(token) > 10)

    @staticmethod
    def create_audit_entry(
        conversation_id: str,
        action: str,
        user_id: str
    ) -> dict[str, Any]:
        """Create KEON audit trail entry."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "conversation_id": conversation_id,
            "action": action,
            "user_id": user_id
        }
```

#### 5. Models (Pydantic)

```python
class WorkflowState(str, Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationStatus(BaseModel):
    """Current conversation status from federation_core."""
    conversation_id: str
    state: WorkflowState
    current_phase: Optional[str] = None
    completion_percentage: int = 0
    phases_completed: list[str] = []
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConversationResult(BaseModel):
    """Final conversation result with artifacts."""
    conversation_id: str
    status: ConversationStatus
    artifacts: dict[str, Any]

    @property
    def brand_name(self) -> Optional[str]:
        """Convenience: Extract brand_name from artifacts."""
        return self.artifacts.get("brand_name")

    @property
    def available_domains(self) -> Optional[list[str]]:
        """Convenience: Extract available_domains from artifacts."""
        return self.artifacts.get("available_domains")


class BrandCampaignInputs(BaseModel):
    """Inputs for brand campaign workflow."""
    business_idea: str
    target_audience: str
    brand_values: list[str]
    budget_range: Optional[str] = None


class JobApplicationInputs(BaseModel):
    """Inputs for job application workflow."""
    resume_text: str
    job_description: str
    cover_letter_tone: Literal["professional", "casual", "creative"] = "professional"
```

#### 6. Genesis Protocol (DECISION NEEDED)

```python
# OPTION A: Genesis is internal-only (NOT in SDK)
# - genesis.py doesn't exist
# - Federation_core handles all tool/agent creation internally
# - Devs cannot create custom agents via SDK

# OPTION B: Genesis exposed for custom agents
class GenesisClient:
    """
    Genesis Protocol interface (if exposed to SDK).

    Allows developers to create custom agents with passports.
    """

    def __init__(self, federation_client: OmegaClient):
        self.client = federation_client

    async def create_agent(
        self,
        name: str,
        capabilities: list[str],
        description: str,
        passport_metadata: Optional[dict[str, Any]] = None
    ) -> AgentSpec:
        """
        Create custom agent via Genesis Protocol.

        Federation_core:
        - Assigns immutable Agent Passport
        - Registers agent in ecosystem
        - Returns agent specification
        """
        response = await self.client._http_client.post(
            f"{self.client.federation_url}/mcp/genesis/agents",
            json={
                "name": name,
                "capabilities": capabilities,
                "description": description,
                "passport_metadata": passport_metadata or {}
            }
        )
        return AgentSpec(**response.json())

    async def create_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        implementation: str
    ) -> ToolSpec:
        """
        Create custom tool via Genesis Protocol.

        Federation_core:
        - Validates tool specification
        - Deploys tool container
        - Returns tool specification
        """
        response = await self.client._http_client.post(
            f"{self.client.federation_url}/mcp/genesis/tools",
            json={
                "name": name,
                "description": description,
                "input_schema": input_schema,
                "implementation": implementation
            }
        )
        return ToolSpec(**response.json())
```

---

## Developer Experience Examples

### Example 1: Simple Brand Campaign (ForgePilot)

```python
from omega_sdk import OmegaClient

# Initialize client
client = OmegaClient(federation_url="http://localhost:9405")

# Create brand campaign
conversation = await client.create_conversation(
    workflow_type="brand_campaign",
    inputs={
        "business_idea": "Sustainable fashion marketplace",
        "target_audience": "Eco-conscious millennials",
        "brand_values": ["sustainability", "transparency", "quality"]
    }
)

# Wait for completion with progress
result = await conversation.wait_for_completion(
    on_progress=lambda s: print(f"[{s.completion_percentage}%] {s.current_phase}")
)

# Access artifacts
print(f"✅ Brand: {result.brand_name}")
print(f"✅ Domains: {result.available_domains}")
print(f"✅ Guidelines: {result.artifacts['brand_guidelines']}")
```

### Example 2: Job Application (SilentApply)

```python
from omega_sdk import OmegaClient, KEONConfig

# Initialize with KEON governance
client = OmegaClient(
    federation_url="http://localhost:9405",
    keon=KEONConfig(
        require_consent=True,
        audit_trail=True,
        data_privacy="strict"
    )
)

# Create job application workflow
conversation = await client.create_conversation(
    workflow_type="job_application",
    user_consent_token="user-consent-abc123",  # KEON compliance
    inputs={
        "resume_text": resume_content,
        "job_description": job_posting,
        "cover_letter_tone": "professional"
    }
)

# Poll for completion
result = await conversation.wait_for_completion()

# Access optimized resume & cover letter
print(f"Resume: {result.artifacts['optimized_resume']}")
print(f"Cover Letter: {result.artifacts['cover_letter']}")
```

### Example 3: Custom Agent Creation (If Genesis Exposed)

```python
from omega_sdk import OmegaClient

client = OmegaClient(federation_url="http://localhost:9405")

# Create custom agent via Genesis
agent = await client.genesis.create_agent(
    name="CustomMarketAnalyzer",
    capabilities=["market_research", "competitor_analysis"],
    description="Analyzes market trends for startups",
    passport_metadata={
        "creator": "myapp@example.com",
        "version": "1.0.0"
    }
)

print(f"✅ Agent created with passport: {agent.passport_id}")
print(f"✅ Capabilities: {agent.capabilities}")

# Agent is now available to federation_core for routing
```

---

## Build Timeline: 3 Weeks

### Week 1: Core (Days 1-7)
**Agents**: SDK Architect, Core Client Developer, Models Developer, Utilities Developer

**Deliverables**:
- [ ] Project structure (`omega-sdk/`)
- [ ] `pyproject.toml` configured
- [ ] `models.py` - Pydantic models
- [ ] `client.py` - OmegaClient
- [ ] `conversation.py` - Conversation tracking
- [ ] `utilities.py` - Battle-tested helpers (COPIED from tests)
- [ ] `keon.py` - KEON governance
- [ ] `config.py` - Configuration
- [ ] `exceptions.py` - Custom exceptions

### Week 2: Quality (Days 8-14)
**Agents**: Test Engineer, Type Safety Specialist, Example Creator

**Deliverables**:
- [ ] Complete test suite (>80% coverage)
- [ ] `tests/test_client.py`
- [ ] `tests/test_conversation.py`
- [ ] `tests/test_utilities.py`
- [ ] `tests/test_keon.py`
- [ ] Zero mypy errors
- [ ] All functions type-hinted
- [ ] Working examples

### Week 3: Polish & Ship (Days 15-21)
**Agents**: Documentation Writer, SDK Architect (final review)

**Deliverables**:
- [ ] `README.md` (compelling)
- [ ] `docs/quickstart.md`
- [ ] `docs/api-reference.md`
- [ ] `docs/examples.md`
- [ ] `CHANGELOG.md`
- [ ] Bug fixes
- [ ] Performance optimization
- [ ] Release v1.0.0 🚀

---

## Critical Decisions Needed

### 1. Genesis Protocol Exposure
**Question**: Should SDK expose Genesis Protocol for custom agent/tool creation?

**Option A**: Internal-only (simpler SDK)
- Genesis stays internal to federation_core
- Devs cannot create custom agents via SDK
- Cleaner separation of concerns

**Option B**: Exposed (more powerful)
- SDK includes `genesis.py`
- Devs can create custom agents with passports
- More developer flexibility

**Recommendation**: Start with Option A, add Option B in v2.0 if needed.

### 2. Agent Passport Protocol
**Question**: Should SDK expose passport-related functionality?

**Option A**: Hidden (federation_core manages)
- Devs don't interact with passports
- Passports are internal implementation detail

**Option B**: Visible (devs see passport IDs)
- Agent specs include passport_id
- Transparency for advanced use cases

**Recommendation**: Option B - show passport_id but don't allow modification.

### 3. Workflow Types
**Question**: Should SDK have typed workflow inputs or accept generic dict?

**Option A**: Generic dict (flexible)
```python
inputs = {"business_idea": "...", "target_audience": "..."}
```

**Option B**: Typed inputs (safe)
```python
inputs = BrandCampaignInputs(
    business_idea="...",
    target_audience="..."
)
```

**Recommendation**: Support both - typed models for common workflows, dict for custom.

---

## Success Metrics

### Code Quality
- ✅ >80% test coverage
- ✅ Zero mypy errors
- ✅ Full type hints
- ✅ Comprehensive docstrings

### Developer Experience
- ✅ 5-line quick start
- ✅ Async + sync interfaces
- ✅ Progress callbacks
- ✅ Rich error messages
- ✅ KEON compliance automatic

### Production Ready
- ✅ Retry with exponential backoff
- ✅ Proper exception handling
- ✅ Environment variable support
- ✅ Battle-tested utilities (from integration tests)

### Documentation
- ✅ Compelling README
- ✅ Complete API reference
- ✅ Working examples
- ✅ KEON governance guide

---

## This is the fucking way! 🚀

**Federation-first. KEON-governed. Doctrine-compliant.**

SDK is a **thin, typed, battle-tested HTTP client** to federation_core.

Federation_core handles:
- ✅ Routing to Titans/agents/tools/services
- ✅ Genesis Protocol (internal tool creation)
- ✅ Multi-Titan orchestration
- ✅ Service discovery

SDK handles:
- ✅ Clean typed interface
- ✅ Conversation management
- ✅ Progress tracking
- ✅ KEON compliance
- ✅ Battle-tested utilities

**Ready to build!**
