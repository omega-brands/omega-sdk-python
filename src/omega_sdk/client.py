"""
OMEGA SDK Client - Main entrypoint for developers.

Provides a clean, ergonomic interface to the Federation Core API.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from omega_sdk.config import OmegaConfig
from omega_sdk.federation import FederationCoreGateway
from omega_sdk.models import (
    Agent,
    AgentListResponse,
    Tool,
    ToolListResponse,
    ToolInvokeRequest,
    ToolInvokeContext,
    ToolInvokeOptions,
    ToolInvokeResult,
    Task,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskContext,
    TaskRouting,
    TaskGovernance,
    HealthStatus,
    StatusResponse,
)
from omega_sdk.evidence import (
    MemoryEvidencePack,
    EvidencePackListResponse,
    EvidenceVerificationResult,
)
from omega_sdk.workflows import WorkflowsNamespace
from omega_sdk.utils.correlation import make_correlation_id


class ToolsNamespace:
    """Tools API namespace."""

    def __init__(self, gateway: FederationCoreGateway, config: OmegaConfig):
        self._gateway = gateway
        self._config = config

    async def list(
        self,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        capability: Optional[str] = None,
        agent_id: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> ToolListResponse:
        """
        List available tools.

        Args:
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)
            capability: Filter by capability
            agent_id: Filter by agent ID
            tag: Filter by tag
            limit: Page limit (default 50, max 200)
            cursor: Pagination cursor

        Returns:
            Tool list response

        Example:
            >>> tools = await client.tools.list(capability="data")
            >>> for tool in tools.items:
            ...     print(f"{tool.tool_id}: {tool.description}")
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        params: dict[str, Any] = {"limit": limit}
        if capability:
            params["capability"] = capability
        if agent_id:
            params["agent_id"] = agent_id
        if tag:
            params["tag"] = tag
        if cursor:
            params["cursor"] = cursor

        data = await self._gateway.get(
            "/tools",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            params=params,
        )

        return ToolListResponse.model_validate(data)

    async def get(
        self,
        tool_id: str,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Tool:
        """
        Get tool details.

        Args:
            tool_id: Tool identifier
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)

        Returns:
            Tool details

        Example:
            >>> tool = await client.tools.get("csv_processor")
            >>> print(tool.input_schema)
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        data = await self._gateway.get(
            f"/tools/{tool_id}",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )

        return Tool.model_validate(data)

    async def invoke(
        self,
        tool_id: str,
        input: dict[str, Any],
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        decision_receipt_id: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        stream: bool = False,
        tags: Optional[list[str]] = None,
    ) -> ToolInvokeResult:
        """
        Invoke a tool.

        Args:
            tool_id: Tool identifier
            input: Tool input parameters
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)
            decision_receipt_id: Decision receipt ID (if required by policy)
            timeout_ms: Request timeout in milliseconds
            stream: Enable streaming response
            tags: Policy tags (e.g., ["silentapply", "prod"])

        Returns:
            Tool invocation result

        Example:
            >>> result = await client.tools.invoke(
            ...     "csv_processor",
            ...     input={"file": "data.csv"}
            ... )
            >>> print(result.result)
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        request = ToolInvokeRequest(
            input=input,
            options=ToolInvokeOptions(
                timeout_ms=timeout_ms,
                stream=stream,
            ),
            context=ToolInvokeContext(
                tenant_id=tenant_id,
                actor_id=actor_id,
                correlation_id=correlation_id,
                decision_receipt_id=decision_receipt_id,
                tags=tags,
            ),
        )

        data = await self._gateway.post(
            f"/tools/{tool_id}:invoke",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            json=request.model_dump(exclude_none=True),
            idempotency_key=str(uuid4()),
            decision_receipt_id=decision_receipt_id,
        )

        return ToolInvokeResult.model_validate(data)


class AgentsNamespace:
    """Agents API namespace."""

    def __init__(self, gateway: FederationCoreGateway, config: OmegaConfig):
        self._gateway = gateway
        self._config = config

    async def list(
        self,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        kind: Optional[str] = None,
        capability: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> AgentListResponse:
        """
        List registered agents.

        Args:
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)
            kind: Filter by agent kind (titan, agent, tool)
            capability: Filter by capability
            limit: Page limit (default 50, max 200)
            cursor: Pagination cursor

        Returns:
            Agent list response

        Example:
            >>> agents = await client.agents.list(kind="titan")
            >>> for agent in agents.items:
            ...     print(f"{agent.agent_id}: {agent.status}")
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        params: dict[str, Any] = {"limit": limit}
        if kind:
            params["kind"] = kind
        if capability:
            params["capability"] = capability
        if cursor:
            params["cursor"] = cursor

        data = await self._gateway.get(
            "/agents",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            params=params,
        )

        return AgentListResponse.model_validate(data)

    async def get(
        self,
        agent_id: str,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Agent:
        """
        Get agent details.

        Args:
            agent_id: Agent identifier
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)

        Returns:
            Agent details

        Example:
            >>> agent = await client.agents.get("gpt_titan")
            >>> print(agent.capabilities)
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        data = await self._gateway.get(
            f"/agents/{agent_id}",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )

        return Agent.model_validate(data)


class TasksNamespace:
    """Tasks API namespace."""

    def __init__(self, gateway: FederationCoreGateway, config: OmegaConfig):
        self._gateway = gateway
        self._config = config

    async def create(
        self,
        task_type: str,
        input: dict[str, Any],
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        routing: Optional[TaskRouting] = None,
        governance: Optional[TaskGovernance] = None,
    ) -> TaskCreateResponse:
        """
        Create (spawn) an asynchronous task.

        Args:
            task_type: Task type (e.g., "workflow.run")
            input: Task input
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)
            routing: Routing configuration
            governance: Governance configuration

        Returns:
            Task creation response

        Example:
            >>> task = await client.tasks.create(
            ...     task_type="workflow.run",
            ...     input={"workflow": "brand_campaign"},
            ...     routing=TaskRouting(strategy="capability", capability="branding")
            ... )
            >>> print(f"Task created: {task.task_id}")
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        request = TaskCreateRequest(
            task_type=task_type,
            input=input,
            routing=routing,
            governance=governance,
            context=TaskContext(
                tenant_id=tenant_id,
                actor_id=actor_id,
                correlation_id=correlation_id,
            ),
        )

        data = await self._gateway.post(
            "/tasks",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            json=request.model_dump(exclude_none=True),
            idempotency_key=str(uuid4()),
        )

        return TaskCreateResponse.model_validate(data)

    async def get(
        self,
        task_id: str,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Task:
        """
        Get task status and result.

        Args:
            task_id: Task identifier
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)

        Returns:
            Task details

        Example:
            >>> task = await client.tasks.get("tk_01H...")
            >>> print(f"Status: {task.status}")
            >>> if task.result:
            ...     print(f"Result: {task.result}")
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        data = await self._gateway.get(
            f"/tasks/{task_id}",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )

        return Task.model_validate(data)


class EvidenceNamespace:
    """Evidence API namespace."""

    def __init__(self, gateway: FederationCoreGateway, config: OmegaConfig):
        self._gateway = gateway
        self._config = config

    async def list(
        self,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> EvidencePackListResponse:
        """
        List evidence packs.

        Args:
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)
            limit: Page limit (default 50, max 200)
            cursor: Pagination cursor

        Returns:
            Evidence pack list response
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        params: dict[str, Any] = {"limit": limit}
        if correlation_id:
            params["correlation_id"] = correlation_id
        if cursor:
            params["cursor"] = cursor

        data = await self._gateway.get(
            "/compliance/evidence-packs",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            params=params,
        )

        return EvidencePackListResponse.model_validate(data)

    async def get(
        self,
        pack_hash: str,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> MemoryEvidencePack:
        """
        Get evidence pack details.

        Args:
            pack_hash: Evidence pack hash (or ID)
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)

        Returns:
            Evidence pack details
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        data = await self._gateway.get(
            f"/compliance/evidence-packs/{pack_hash}",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )

        return MemoryEvidencePack.model_validate(data)

    async def verify(
        self,
        pack_hash: str,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> EvidenceVerificationResult:
        """
        Verify an evidence pack.

        Args:
            pack_hash: Evidence pack hash
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)

        Returns:
            Verification result
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        data = await self._gateway.post(
            f"/compliance/evidence-packs/{pack_hash}:verify",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            json={},
        )

        return EvidenceVerificationResult.model_validate(data)


class OmegaClient:
    """
    Main OMEGA SDK client.

    Provides a clean, typed interface to the Federation Core API with:
    - Automatic correlation ID management
    - Structured error handling
    - Retry logic for transient failures
    - Optional governance (receipt threading)

    Example:
        >>> from omega_sdk import OmegaClient
        >>> client = OmegaClient.from_env()
        >>> tools = await client.tools.list()
        >>> result = await client.tools.invoke("csv_processor", input={"file": "data.csv"})
    """

    def __init__(
        self,
        config: Optional[OmegaConfig] = None,
        federation_url: Optional[str] = None,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
    ):
        """
        Initialize OMEGA client.

        Args:
            config: SDK configuration (optional, defaults to from_env())
            federation_url: Federation Core URL (overrides config)
            api_key: API key (overrides config)
            tenant_id: Default tenant ID (overrides config)
            actor_id: Default actor ID (overrides config)

        Example:
            >>> client = OmegaClient(
            ...     federation_url="http://localhost:9405",
            ...     tenant_id="acme",
            ...     actor_id="clint"
            ... )
        """
        if config is None:
            config = OmegaConfig.from_env()

        # Override config fields if provided
        if federation_url:
            config = config.model_copy(update={"federation_url": federation_url})
        if api_key:
            config = config.model_copy(update={"api_key": api_key})
        if tenant_id:
            config = config.model_copy(update={"tenant_id": tenant_id})
        if actor_id:
            config = config.model_copy(update={"actor_id": actor_id})

        self.config = config
        self._gateway = FederationCoreGateway(config)

        # API namespaces
        self.tools = ToolsNamespace(self._gateway, config)
        self.agents = AgentsNamespace(self._gateway, config)
        self.tasks = TasksNamespace(self._gateway, config)
        self.evidence = EvidenceNamespace(self._gateway, config)
        self.workflows = WorkflowsNamespace(self._gateway, config)

    @classmethod
    def from_env(cls) -> "OmegaClient":
        """
        Create client from environment variables.

        Environment variables:
            OMEGA_FEDERATION_URL
            OMEGA_API_KEY
            OMEGA_TENANT_ID
            OMEGA_ACTOR_ID
            OMEGA_TIMEOUT_MS
            OMEGA_MAX_RETRIES

        Returns:
            Configured OmegaClient

        Example:
            >>> client = OmegaClient.from_env()
        """
        return cls(config=OmegaConfig.from_env())

    async def __aenter__(self) -> "OmegaClient":
        """Async context manager entry."""
        await self._gateway.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self._gateway.__aexit__(*args)

    async def close(self) -> None:
        """Close the client."""
        await self._gateway.close()

    async def health(self) -> HealthStatus:
        """
        Check Federation Core health.

        Returns:
            Health status

        Example:
            >>> health = await client.health()
            >>> print(f"Federation Core {health.version}: {health.status}")
        """
        data = await self._gateway._client.get(f"{self._gateway.base_url}/health")
        envelope = self._gateway._unwrap_envelope(data)
        return HealthStatus.model_validate(envelope)

    async def status(
        self,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> StatusResponse:
        """
        Get rich Federation Core status.

        Args:
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)

        Returns:
            Status response

        Example:
            >>> status = await client.status()
            >>> print(status.dependencies)
        """
        tenant_id = tenant_id or self.config.tenant_id or ""
        actor_id = actor_id or self.config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        data = await self._gateway.get(
            "/status",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )

        return StatusResponse.model_validate(data)
