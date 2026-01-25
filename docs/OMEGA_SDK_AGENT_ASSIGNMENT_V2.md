# OMEGA SDK - Agent Team Assignment v2.0
## Doctrine-Compliant Architecture

**Team Size**: 10 specialized agents
**Timeline**: 3 weeks to v1.0.0
**Architecture**: Federation-first, thin HTTP client

---

## Team Structure

```
SDK Architect (Lead)
├── Core Team (4 agents)
│   ├── Models Developer
│   ├── Client Developer
│   ├── Conversation Developer
│   └── Utilities Developer
├── Governance Team (2 agents)
│   ├── KEON Developer
│   └── Config/Exceptions Developer
├── Quality Team (2 agents)
│   ├── Test Engineer
│   └── Type Safety Specialist
└── Documentation Team (2 agents)
    ├── Example Creator
    └── Technical Writer
```

---

## Agent 1: SDK Architect (LEAD)

**Role**: Project coordinator & architecture guardian

**Responsibilities**:
1. Create project structure at `D:/Repos/forgepilot/omega-sdk/`
2. Initialize `pyproject.toml` (copy from `D:\Repos\OMEGA\omega-sdk\pyproject.toml` as template)
3. Setup package structure at `omega_sdk/`
4. Create `omega_sdk/__init__.py` with public API exports
5. Review all PRs for Doctrine compliance
6. Ensure federation-first architecture maintained
7. Make final decisions on Genesis Protocol exposure

**Deliverables**:
- [ ] Project structure created
- [ ] `pyproject.toml` configured with dependencies
- [ ] `omega_sdk/__init__.py` with clean exports
- [ ] `.gitignore` for Python
- [ ] `README.md` skeleton
- [ ] `LICENSE` (MIT)

**Key Exports** (`__init__.py`):
```python
from .client import OmegaClient
from .conversation import Conversation
from .keon import KEONConfig, KEONHelper
from .models import (
    WorkflowState,
    ConversationStatus,
    ConversationResult,
    BrandCampaignInputs,
    JobApplicationInputs
)
from .exceptions import (
    OmegaError,
    AuthenticationError,
    WorkflowTimeoutError,
    WorkflowFailedError,
    KEONConsentRequired
)

__version__ = "1.0.0"
__all__ = [
    "OmegaClient",
    "Conversation",
    "KEONConfig",
    "KEONHelper",
    "WorkflowState",
    "ConversationStatus",
    "ConversationResult",
    "BrandCampaignInputs",
    "JobApplicationInputs",
    "OmegaError",
    "AuthenticationError",
    "WorkflowTimeoutError",
    "WorkflowFailedError",
    "KEONConsentRequired"
]
```

**Dependencies**: None (starts Day 1)

---

## Agent 2: Models Developer

**Role**: Create all Pydantic models for type safety

**Source Files**:
- `forgepilot-api/app/models/`
- `forgepilot-api/tests/contracts/test_federation_contracts.py`

**Tasks**:
1. Create `omega_sdk/models.py`
2. Define `WorkflowState` enum
3. Define `ConversationStatus` model
4. Define `ConversationResult` model
5. Define input models (`BrandCampaignInputs`, `JobApplicationInputs`)
6. Add convenience properties (e.g., `result.brand_name`)
7. Add validators where needed

**Code Template**:
```python
from enum import Enum
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class WorkflowState(str, Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationStatus(BaseModel):
    """Current status from federation_core."""
    conversation_id: str
    state: WorkflowState
    current_phase: Optional[str] = None
    completion_percentage: int = Field(0, ge=0, le=100)
    phases_completed: list[str] = Field(default_factory=list)
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
        """Extract brand_name from artifacts."""
        return self.artifacts.get("brand_name")

    @property
    def available_domains(self) -> Optional[list[str]]:
        """Extract available_domains from artifacts."""
        return self.artifacts.get("available_domains")

    @property
    def brand_guidelines(self) -> Optional[dict[str, Any]]:
        """Extract brand_guidelines from artifacts."""
        return self.artifacts.get("brand_guidelines")


class BrandCampaignInputs(BaseModel):
    """Inputs for brand campaign workflow."""
    business_idea: str = Field(..., min_length=10)
    target_audience: str = Field(..., min_length=5)
    brand_values: list[str] = Field(..., min_items=1)
    budget_range: Optional[str] = None


class JobApplicationInputs(BaseModel):
    """Inputs for job application workflow."""
    resume_text: str = Field(..., min_length=100)
    job_description: str = Field(..., min_length=50)
    cover_letter_tone: Literal["professional", "casual", "creative"] = "professional"
```

**Deliverables**:
- [ ] `omega_sdk/models.py` (200-300 lines)
- [ ] All models documented
- [ ] Type hints complete
- [ ] Validators added
- [ ] Convenience properties

**Dependencies**: Agent 1 (project structure)
**Timeline**: Days 1-2

---

## Agent 3: Client Developer

**Role**: Build main `OmegaClient` (federation HTTP client)

**Source Files**:
- `forgepilot-api/app/clients/federation_client.py`
- `forgepilot-api/tests/integration/test_federation_integration.py`

**Tasks**:
1. Create `omega_sdk/client.py`
2. Implement `OmegaClient` class
3. Add `create_conversation()` method
4. Add `get_conversation()` method
5. Add `health_check()` method
6. Implement retry logic with exponential backoff
7. Add sync wrapper methods (optional, for non-async users)

**Key Implementation**:
```python
import httpx
from typing import Any, Optional, Callable
from .models import ConversationStatus
from .conversation import Conversation
from .keon import KEONConfig, KEONHelper
from .exceptions import OmegaError, AuthenticationError, KEONConsentRequired


class OmegaClient:
    """
    Main SDK client. Thin HTTP wrapper around federation_core.

    Federation_core is the single control plane. It handles:
    - Routing to Titans, agents, tools, services
    - Genesis Protocol (internal)
    - Multi-Titan orchestration
    - Service discovery

    SDK provides:
    - Clean typed interface
    - Conversation management
    - KEON compliance
    - Progress tracking
    """

    def __init__(
        self,
        federation_url: str = "http://localhost:9405",
        api_key: Optional[str] = None,
        keon: Optional[KEONConfig] = None,
        timeout: float = 120.0,
        max_retries: int = 3
    ):
        """
        Initialize OMEGA SDK client.

        Args:
            federation_url: Federation core URL (default: http://localhost:9405)
            api_key: Optional API key for authentication
            keon: KEON governance configuration
            timeout: HTTP request timeout in seconds
            max_retries: Max retry attempts for failed requests
        """
        self.federation_url = federation_url.rstrip("/")
        self.api_key = api_key
        self.keon = keon or KEONConfig()
        self.timeout = timeout
        self.max_retries = max_retries

        # HTTP client with retry transport
        transport = httpx.AsyncHTTPTransport(retries=max_retries)
        self._http_client = httpx.AsyncClient(
            timeout=timeout,
            transport=transport
        )

    async def create_conversation(
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
        """
        # KEON validation
        if self.keon.require_consent:
            if not user_consent_token:
                raise KEONConsentRequired("User consent required by KEON policy")
            if not KEONHelper.validate_consent_token(user_consent_token):
                raise KEONConsentRequired("Invalid consent token format")

        # Build request
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "workflow_type": workflow_type,
            "inputs": inputs
        }
        if user_consent_token:
            payload["user_consent_token"] = user_consent_token

        # POST to federation_core
        try:
            response = await self._http_client.post(
                f"{self.federation_url}/mcp/collaboration/conversational",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            raise OmegaError(f"Federation API error: {e}")

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
        """
        Get current status of a conversation.

        Args:
            conversation_id: Conversation ID from create_conversation

        Returns:
            Current conversation status
        """
        response = await self._http_client.get(
            f"{self.federation_url}/mcp/conversations/{conversation_id}"
        )
        response.raise_for_status()
        return ConversationStatus(**response.json())

    async def health_check(self) -> bool:
        """
        Check federation_core health.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self._http_client.get(
                f"{self.federation_url}/mcp/health"
            )
            data = response.json()
            return data["status"] == "healthy"
        except Exception:
            return False

    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
```

**Deliverables**:
- [ ] `omega_sdk/client.py` (300-400 lines)
- [ ] Full docstrings
- [ ] Error handling
- [ ] Retry logic
- [ ] KEON validation

**Dependencies**: Agent 1 (structure), Agent 2 (models), Agent 5 (KEON)
**Timeline**: Days 3-5

---

## Agent 4: Conversation Developer

**Role**: Build Conversation tracking and polling

**Source Files**:
- `forgepilot-api/tests/helpers/federation_helpers.py::ConversationPoller`

**Tasks**:
1. Create `omega_sdk/conversation.py`
2. Implement `Conversation` class
3. Add `wait_for_completion()` with polling
4. Add `get_status()` method
5. Add `get_artifacts()` method
6. Integrate with `ConversationPoller` utility

**Key Implementation**:
```python
import asyncio
from typing import Any, Optional, Callable
from .models import ConversationStatus, ConversationResult
from .utilities import ConversationPoller
from .exceptions import WorkflowTimeoutError, WorkflowFailedError


class Conversation:
    """
    Manages a single conversation with federation_core.

    Provides:
    - Progress polling with adaptive backoff
    - Phase tracking
    - Artifact retrieval
    - Completion waiting
    """

    def __init__(
        self,
        conversation_id: str,
        client: "OmegaClient",
        on_progress: Optional[Callable] = None
    ):
        """
        Initialize conversation tracker.

        Args:
            conversation_id: Conversation ID from federation_core
            client: OmegaClient instance
            on_progress: Optional progress callback
        """
        self.conversation_id = conversation_id
        self.client = client
        self.on_progress = on_progress
        self._poller = ConversationPoller(client, conversation_id)

    async def wait_for_completion(
        self,
        timeout: float = 300.0
    ) -> ConversationResult:
        """
        Poll until conversation completes or times out.

        Uses adaptive backoff:
        - 0-30s: 1s intervals
        - 30-60s: 2s intervals
        - 60s+: 5s intervals

        Args:
            timeout: Max time to wait in seconds

        Returns:
            ConversationResult with final status and artifacts

        Raises:
            WorkflowTimeoutError: If timeout exceeded
            WorkflowFailedError: If workflow failed
        """
        try:
            status = await self._poller.poll_until_complete(
                timeout=timeout,
                on_progress=self.on_progress
            )
        except TimeoutError as e:
            raise WorkflowTimeoutError(str(e))

        # Fetch final artifacts
        artifacts = await self.get_artifacts()

        return ConversationResult(
            conversation_id=self.conversation_id,
            status=status,
            artifacts=artifacts
        )

    async def get_status(self) -> ConversationStatus:
        """
        Get current status without polling.

        Returns:
            Current conversation status
        """
        return await self.client.get_conversation(self.conversation_id)

    async def get_artifacts(self) -> dict[str, Any]:
        """
        Retrieve conversation artifacts.

        Returns:
            Dict of artifacts produced by workflow
        """
        response = await self.client._http_client.get(
            f"{self.client.federation_url}/mcp/conversations/{self.conversation_id}/artifacts"
        )
        response.raise_for_status()
        return response.json()
```

**Deliverables**:
- [ ] `omega_sdk/conversation.py` (150-200 lines)
- [ ] Full docstrings
- [ ] Progress tracking
- [ ] Artifact retrieval

**Dependencies**: Agent 2 (models), Agent 3 (client), Agent 6 (utilities)
**Timeline**: Days 5-6

---

## Agent 5: KEON Developer

**Role**: Build KEON governance helpers

**Tasks**:
1. Create `omega_sdk/keon.py`
2. Implement `KEONConfig` dataclass
3. Implement `KEONHelper` class
4. Add consent token validation
5. Add audit trail helpers
6. Document KEON compliance patterns

**Key Implementation**:
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal


@dataclass
class KEONConfig:
    """
    KEON governance configuration.

    KEON principles:
    - Privacy by design
    - User consent required
    - Audit trail mandatory
    - Transparency enforced
    """
    require_consent: bool = True
    audit_trail: bool = True
    data_privacy: Literal["strict", "standard", "minimal"] = "strict"
    transparency_level: Literal["full", "summary", "minimal"] = "full"


class KEONHelper:
    """Helper utilities for KEON compliance."""

    @staticmethod
    def validate_consent_token(token: str) -> bool:
        """
        Validate user consent token format.

        Args:
            token: Consent token from user

        Returns:
            True if valid format
        """
        if not token:
            return False
        if len(token) < 10:
            return False
        # Add more validation as needed
        return True

    @staticmethod
    def create_audit_entry(
        conversation_id: str,
        action: str,
        user_id: str,
        metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create KEON audit trail entry.

        Args:
            conversation_id: Conversation ID
            action: Action being audited
            user_id: User performing action
            metadata: Optional additional metadata

        Returns:
            Audit entry dict
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "conversation_id": conversation_id,
            "action": action,
            "user_id": user_id,
            "metadata": metadata or {}
        }
```

**Deliverables**:
- [ ] `omega_sdk/keon.py` (100-150 lines)
- [ ] `KEONConfig` dataclass
- [ ] `KEONHelper` utilities
- [ ] Consent validation
- [ ] Audit helpers

**Dependencies**: Agent 1 (structure)
**Timeline**: Days 2-3

---

## Agent 6: Utilities Developer

**Role**: Port battle-tested helpers from integration tests

**CRITICAL**: **COPY** from `forgepilot-api/tests/helpers/federation_helpers.py`

**Source File**: `forgepilot-api/tests/helpers/federation_helpers.py`

**Tasks**:
1. Create `omega_sdk/utilities.py`
2. **COPY** `ConversationPoller` class
3. **COPY** `PhaseTracker` class
4. **COPY** `ArtifactValidator` class
5. **COPY** `TitanParticipationTracker` class
6. Adapt for SDK use (remove test-specific code)
7. Add comprehensive docstrings

**IMPORTANT**: These are proven patterns. **DO NOT rewrite from scratch.** Copy and adapt.

**Deliverables**:
- [ ] `omega_sdk/utilities.py` (400+ lines)
- [ ] `ConversationPoller` - adaptive polling
- [ ] `PhaseTracker` - phase progression
- [ ] `ArtifactValidator` - output validation
- [ ] `TitanParticipationTracker` - Titan tracking

**Dependencies**: Agent 1 (structure), Agent 2 (models)
**Timeline**: Days 3-4

---

## Agent 7: Config/Exceptions Developer

**Role**: Build configuration and exception handling

**Tasks**:
1. Create `omega_sdk/config.py`
2. Create `omega_sdk/exceptions.py`
3. Add environment variable support
4. Create `.env.example` file
5. Document exception hierarchy

**omega_sdk/config.py**:
```python
import os
from typing import Optional
from pydantic_settings import BaseSettings


class OmegaSDKConfig(BaseSettings):
    """SDK configuration from environment."""

    federation_url: str = "http://localhost:9405"
    api_key: Optional[str] = None
    timeout: float = 120.0
    max_retries: int = 3

    class Config:
        env_prefix = "OMEGA_"
        env_file = ".env"


def get_config() -> OmegaSDKConfig:
    """Get SDK configuration singleton."""
    return OmegaSDKConfig()
```

**omega_sdk/exceptions.py**:
```python
class OmegaError(Exception):
    """Base exception for OMEGA SDK."""
    pass


class AuthenticationError(OmegaError):
    """Authentication failed."""
    pass


class WorkflowTimeoutError(OmegaError):
    """Workflow exceeded timeout."""
    pass


class WorkflowFailedError(OmegaError):
    """Workflow execution failed."""
    pass


class KEONConsentRequired(OmegaError):
    """KEON governance requires user consent."""
    pass


class ValidationError(OmegaError):
    """Input validation failed."""
    pass
```

**Deliverables**:
- [ ] `omega_sdk/config.py` (50-100 lines)
- [ ] `omega_sdk/exceptions.py` (50-100 lines)
- [ ] `.env.example` file
- [ ] Environment variable docs

**Dependencies**: Agent 1 (structure)
**Timeline**: Days 2-3

---

## Agent 8: Test Engineer

**Role**: Write comprehensive SDK tests

**Source**: `forgepilot-api/tests/`

**Tasks**:
1. Create `tests/conftest.py` with fixtures
2. Create `tests/test_client.py`
3. Create `tests/test_conversation.py`
4. Create `tests/test_utilities.py`
5. Create `tests/test_keon.py`
6. Create `tests/test_models.py`
7. Achieve >80% code coverage

**Test Structure**:
```python
# tests/conftest.py
import pytest
from omega_sdk import OmegaClient


@pytest.fixture
def omega_client():
    """Test client fixture."""
    return OmegaClient(federation_url="http://localhost:9405")


@pytest.fixture
async def live_client():
    """Live client for integration tests."""
    client = OmegaClient(federation_url="http://localhost:9405")
    yield client
    await client.close()


# tests/test_client.py
@pytest.mark.asyncio
async def test_health_check(live_client):
    """Test federation_core health check."""
    is_healthy = await live_client.health_check()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_create_conversation(live_client):
    """Test conversation creation."""
    conversation = await live_client.create_conversation(
        workflow_type="brand_campaign",
        inputs={
            "business_idea": "Test idea",
            "target_audience": "Test audience",
            "brand_values": ["innovation"]
        }
    )
    assert conversation.conversation_id is not None
```

**Deliverables**:
- [ ] `tests/conftest.py`
- [ ] `tests/test_client.py` (10+ tests)
- [ ] `tests/test_conversation.py` (5+ tests)
- [ ] `tests/test_utilities.py` (8+ tests)
- [ ] `tests/test_keon.py` (5+ tests)
- [ ] `tests/test_models.py` (5+ tests)
- [ ] >80% coverage

**Dependencies**: All core developers (2-7)
**Timeline**: Days 8-11

---

## Agent 9: Type Safety Specialist

**Role**: Ensure complete type safety

**Tasks**:
1. Add type hints to ALL functions
2. Create `py.typed` marker file
3. Configure `mypy.ini`
4. Run mypy on codebase
5. Fix all type errors
6. Add type stubs where needed

**mypy.ini**:
```ini
[mypy]
python_version = 3.12
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
follow_imports = normal
strict_equality = True
```

**Deliverables**:
- [ ] `py.typed` marker file
- [ ] `mypy.ini` configured
- [ ] Zero mypy errors in strict mode
- [ ] All public functions fully typed

**Dependencies**: All core developers (2-7)
**Timeline**: Days 11-13

---

## Agent 10: Example Creator

**Role**: Create working usage examples

**Tasks**:
1. Create `examples/basic_campaign.py`
2. Create `examples/job_application.py`
3. Create `examples/progress_monitoring.py`
4. Create `examples/keon_compliance.py`
5. Create `examples/README.md`
6. Test all examples against live federation_core

**Example Template**:
```python
# examples/basic_campaign.py
"""
Basic brand campaign example.

Demonstrates:
- Creating OmegaClient
- Starting a brand campaign workflow
- Waiting for completion
- Accessing artifacts
"""
import asyncio
from omega_sdk import OmegaClient


async def main():
    # Initialize client
    client = OmegaClient(federation_url="http://localhost:9405")

    # Create brand campaign
    print("🚀 Starting brand campaign...")
    conversation = await client.create_conversation(
        workflow_type="brand_campaign",
        inputs={
            "business_idea": "Sustainable fashion marketplace",
            "target_audience": "Eco-conscious millennials",
            "brand_values": ["sustainability", "transparency", "quality"]
        }
    )

    print(f"✅ Conversation created: {conversation.conversation_id}")

    # Wait for completion with progress
    print("⏳ Waiting for completion...")
    result = await conversation.wait_for_completion(
        on_progress=lambda s: print(f"  [{s.completion_percentage}%] {s.current_phase}")
    )

    # Access artifacts
    print(f"\n✅ Brand Campaign Complete!")
    print(f"  Brand Name: {result.brand_name}")
    print(f"  Domains: {', '.join(result.available_domains or [])}")
    print(f"  Guidelines: {result.brand_guidelines}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

**Deliverables**:
- [ ] `examples/basic_campaign.py`
- [ ] `examples/job_application.py`
- [ ] `examples/progress_monitoring.py`
- [ ] `examples/keon_compliance.py`
- [ ] `examples/README.md`
- [ ] All examples tested

**Dependencies**: All core developers (2-7)
**Timeline**: Days 12-14

---

## Agent 11: Technical Writer

**Role**: Create complete documentation

**Tasks**:
1. Write compelling `README.md`
2. Create `docs/quickstart.md`
3. Create `docs/api-reference.md`
4. Create `docs/keon-governance.md`
5. Create `docs/examples.md`
6. Create `CHANGELOG.md`
7. Add docstrings where missing

**README.md Structure**:
```markdown
# OMEGA SDK

Build OMEGA-native applications with "Powered by OMEGA, Governed by KEON" pattern.

## Features

- 🚀 Federation-first architecture
- 🔒 KEON governance built-in
- ⚡ Async + sync interfaces
- 📊 Progress tracking
- 🔄 Auto-retry with backoff
- 📝 Full type safety

## Quick Start

[5-line example]

## Documentation

- [Quick Start Guide](docs/quickstart.md)
- [API Reference](docs/api-reference.md)
- [KEON Governance](docs/keon-governance.md)
- [Examples](docs/examples.md)
```

**Deliverables**:
- [ ] `README.md` (compelling)
- [ ] `docs/quickstart.md`
- [ ] `docs/api-reference.md`
- [ ] `docs/keon-governance.md`
- [ ] `docs/examples.md`
- [ ] `CHANGELOG.md`

**Dependencies**: All developers
**Timeline**: Days 15-18

---

## Build Timeline

### Week 1: Core Implementation (Days 1-7)

**Day 1-2**:
- Agent 1: Project structure, pyproject.toml
- Agent 2: models.py
- Agent 5: keon.py
- Agent 7: config.py, exceptions.py

**Day 3-4**:
- Agent 6: utilities.py (COPY from tests)
- Agent 3: client.py (start)

**Day 5-7**:
- Agent 3: client.py (finish)
- Agent 4: conversation.py

### Week 2: Quality & Examples (Days 8-14)

**Day 8-11**:
- Agent 8: Complete test suite

**Day 11-13**:
- Agent 9: Type safety (mypy)

**Day 12-14**:
- Agent 10: Examples

### Week 3: Polish & Ship (Days 15-21)

**Day 15-18**:
- Agent 11: Documentation

**Day 19-20**:
- All agents: Bug fixes, optimization

**Day 21**:
- Agent 1: Final review, release v1.0.0 🚀

---

## Communication Protocol

### Daily Async Standup
Each agent posts in shared channel:
1. ✅ Completed yesterday
2. 🚧 Working on today
3. 🚨 Blockers (if any)

### Code Review by SDK Architect
Every PR must have:
- ✅ Docstrings with examples
- ✅ Type hints complete
- ✅ Tests passing (if applicable)
- ✅ Updated CHANGELOG
- ✅ Mypy passing

### Definition of Done
- [ ] Code written
- [ ] Type hints added
- [ ] Docstrings complete
- [ ] Tests passing (>80% coverage)
- [ ] Mypy passing (zero errors)
- [ ] Reviewed by SDK Architect
- [ ] Merged to main

---

## Critical Success Factors

### ✅ Federation-First
- SDK is thin HTTP client to federation_core
- No direct Titan/Genesis APIs (unless user decides)
- All routing handled by federation_core

### ✅ Battle-Tested Patterns
- **COPY utilities from `forgepilot-api/tests/helpers/`**
- Don't reinvent - proven patterns work!

### ✅ Type Safety
- Full type hints
- Pydantic models
- Zero mypy errors

### ✅ KEON Governed
- Consent validation
- Audit trail support
- Privacy by design

### ✅ Developer Experience
- 5-line quick start
- Progress callbacks
- Rich error messages
- Clear documentation

---

## Hand-off Package

Each agent receives:
1. This assignment document
2. `OMEGA_SDK_DIRECTIVE_V2.md` (technical spec)
3. Access to source code:
   - `forgepilot-api/app/clients/federation_client.py`
   - `forgepilot-api/tests/helpers/federation_helpers.py` ⭐
   - `forgepilot-api/tests/integration/`
4. Their specific deliverables checklist
5. Timeline with dependencies

---

## This is the fucking way! 🚀

**Federation-first. Type-safe. Battle-tested. KEON-governed.**

Build once. Ship fast. Empower developers.

**Ready to execute!**
