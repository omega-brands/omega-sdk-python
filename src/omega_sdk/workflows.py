"""
OMEGA SDK Workflows - First-class governance workflow operations.

This module provides the WorkflowsNamespace for interacting with
the Federation Core workflow execution API.

Supports:
- Starting workflow runs
- Getting run status and details
- Retrieving run logs
- Resuming paused runs (gate approval/denial)
- Polling for completion (optional)

Usage:
    >>> client = OmegaClient.from_env()
    >>> result = await client.workflows.run_workflow(
    ...     workflow_id="council-of-titans",
    ...     inputs={"topic": "brand strategy"}
    ... )
    >>> print(f"Run ID: {result.run_id}, Status: {result.status}")
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from omega_sdk.config import OmegaConfig
from omega_sdk.federation import FederationCoreGateway
from omega_sdk.utils.correlation import make_correlation_id


# =============================================================================
# Workflow DTOs
# =============================================================================


class WorkflowRunStatus(str, Enum):
    """Workflow run execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"  # Waiting for gate approval
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GateStatus(str, Enum):
    """Approval gate status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    BYPASSED = "bypassed"


class GateInfo(BaseModel):
    """Information about a workflow gate."""

    gate_id: str = Field(..., description="Unique gate identifier")
    run_id: str = Field(..., description="Parent workflow run")
    step_id: str = Field(..., description="Step that requires gate approval")
    gate_type: str = Field(..., description="Gate type: human_approval, policy_check, timeout")
    gate_name: str = Field(..., description="Human-readable gate name")
    description: Optional[str] = Field(None)
    status: GateStatus = Field(..., description="Current gate status")
    required_approvers: list[str] = Field(default_factory=list)
    approved_by: Optional[str] = Field(None)
    rejection_reason: Optional[str] = Field(None)
    created_at: Optional[datetime] = Field(None)
    resolved_at: Optional[datetime] = Field(None)
    expires_at: Optional[datetime] = Field(None)
    evidence_pack_hash: Optional[str] = Field(None)


class WorkflowRunLogEntry(BaseModel):
    """A log entry for workflow run execution."""

    log_id: str = Field(..., description="Unique log entry ID")
    run_id: str = Field(..., description="Parent workflow run")
    event_type: str = Field(..., description="FC event type code (e.g., FC-RUN-001)")
    event_category: str = Field(default="workflow", description="Event category")
    step_id: Optional[str] = Field(None)
    previous_status: Optional[str] = Field(None)
    new_status: Optional[str] = Field(None)
    actor_id: str = Field(..., description="Who triggered this event")
    message: str = Field(..., description="Human-readable event description")
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(..., description="Event timestamp")
    duration_ms: Optional[int] = Field(None)
    evidence_hash: Optional[str] = Field(None)


class WorkflowRunOptions(BaseModel):
    """Options for starting a workflow run."""

    timeout_ms: Optional[int] = Field(None, description="Request timeout in milliseconds")
    tags: Optional[list[str]] = Field(None, description="Policy tags")
    metadata: Optional[dict[str, Any]] = Field(None, description="Custom metadata")
    parent_run_id: Optional[str] = Field(None, description="Parent run ID for nested workflows")


class WorkflowRunResult(BaseModel):
    """Result of a workflow run operation."""

    run_id: str = Field(..., description="Unique run identifier")
    workflow_id: str = Field(..., description="Workflow definition ID")
    workflow_version: str = Field(default="1.0.0")
    status: WorkflowRunStatus = Field(..., description="Current run status")
    current_step: Optional[str] = Field(None, description="Current step ID")
    step_index: int = Field(default=0)

    # Identity
    tenant_id: str = Field(..., description="Owning tenant")
    actor_id: str = Field(..., description="Initiating actor")
    correlation_id: str = Field(..., description="Correlation ID")

    # Input/Output
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: Optional[dict[str, Any]] = Field(None)
    error_details: Optional[dict[str, Any]] = Field(None)

    # Receipt chain
    receipt_chain: list[str] = Field(default_factory=list)
    workflow_receipt_hash: Optional[str] = Field(None)
    evidence_pack_hash: Optional[str] = Field(None)
    evidence_pack_refs: list[str] = Field(default_factory=list)

    # Gate information (if paused)
    gate_info: Optional[GateInfo] = Field(
        None, description="Gate info if run is paused for approval"
    )
    gates: list[GateInfo] = Field(default_factory=list, description="All gates for this run")

    # Timestamps
    created_at: Optional[datetime] = Field(None)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

    # Logs (optional, if requested)
    logs: list[WorkflowRunLogEntry] = Field(default_factory=list)


class ResumeRunResult(BaseModel):
    """Result of resuming a paused workflow run."""

    run_id: str = Field(..., description="Run identifier")
    status: WorkflowRunStatus = Field(..., description="New run status")
    gate_id: str = Field(..., description="Gate that was resolved")
    gate_status: GateStatus = Field(..., description="Gate resolution status")
    message: str = Field(..., description="Result message")


class WorkflowRegisterRequest(BaseModel):
    """Request for workflow artifact registration."""
    workflow_yaml: str
    prompts_poml: str
    schemas: dict[str, Any] = Field(default_factory=dict)
    workflow_id: Optional[str] = None
    version: Optional[str] = None


class WorkflowRegisterResult(BaseModel):
    """Workflow registration response."""
    workflow_id: str
    version: str
    artifact_hashes: dict[str, Any]
    idempotent: bool = False


# =============================================================================
# WorkflowsNamespace
# =============================================================================


class WorkflowsNamespace:
    """
    Workflows API namespace.

    Provides methods for starting, monitoring, and controlling
    first-class governance workflow runs.
    """

    def __init__(self, gateway: FederationCoreGateway, config: OmegaConfig):
        self._gateway = gateway
        self._config = config
        # FC routes use /api/fc prefix, not /api/v1
        # We'll construct the full URL directly
        self._fc_base_url = config.federation_url.rstrip("/") + "/api/fc"

    async def _fc_post(
        self,
        path: str,
        tenant_id: str,
        actor_id: str,
        correlation_id: str,
        json: dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Send POST request to FC routes (not /api/v1)."""
        import httpx

        url = f"{self._fc_base_url}{path}"
        headers = {
            "X-Tenant-Id": tenant_id,
            "X-Actor-Id": actor_id,
            "X-Correlation-Id": correlation_id,
            "Content-Type": "application/json",
        }

        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        response = await self._gateway._client.post(url, headers=headers, json=json)

        if response.status_code >= 400:
            # Try to extract error details
            try:
                body = response.json()
                detail_raw = body.get("detail", f"HTTP {response.status_code}")
                if isinstance(detail_raw, dict):
                    detail = detail_raw.get("message", f"HTTP {response.status_code}")
                else:
                    detail = detail_raw
            except Exception:
                detail = f"HTTP {response.status_code}"

            from omega_sdk.errors import OmegaError
            raise OmegaError(
                code="FC_ERROR",
                message=str(detail),
                retryable=response.status_code >= 500,
            )

        return response.json()

    async def _fc_get(
        self,
        path: str,
        tenant_id: str,
        actor_id: str,
        correlation_id: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Send GET request to FC routes (not /api/v1)."""
        url = f"{self._fc_base_url}{path}"
        headers = {
            "X-Tenant-Id": tenant_id,
            "X-Actor-Id": actor_id,
            "X-Correlation-Id": correlation_id,
        }

        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        response = await self._gateway._client.get(
            url, headers=headers, params=params or {}
        )

        if response.status_code >= 400:
            try:
                body = response.json()
                detail_raw = body.get("detail", f"HTTP {response.status_code}")
                if isinstance(detail_raw, dict):
                    detail = detail_raw.get("message", f"HTTP {response.status_code}")
                else:
                    detail = detail_raw
            except Exception:
                detail = f"HTTP {response.status_code}"

            from omega_sdk.errors import OmegaError
            raise OmegaError(
                code="FC_ERROR",
                message=str(detail),
                retryable=response.status_code >= 500,
            )

        return response.json()

    async def run_workflow(
        self,
        workflow_id: str,
        inputs: Optional[dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        options: Optional[WorkflowRunOptions] = None,
    ) -> WorkflowRunResult:
        """
        Start a new workflow run.

        Args:
            workflow_id: Workflow definition ID
            inputs: Input payload for the workflow
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)
            options: Workflow run options

        Returns:
            WorkflowRunResult with run_id and status

        Example:
            >>> result = await client.workflows.run_workflow(
            ...     workflow_id="council-of-titans",
            ...     inputs={"topic": "brand strategy"}
            ... )
            >>> print(f"Run: {result.run_id}, Status: {result.status}")
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        # Build request body
        request_body: dict[str, Any] = {
            "workflow_id": workflow_id,
            "input_payload": inputs or {},
        }

        if options:
            if options.metadata:
                request_body["metadata"] = options.metadata
            if options.tags:
                request_body["tags"] = options.tags
            if options.parent_run_id:
                request_body["parent_run_id"] = options.parent_run_id

        # POST /api/fc/runs
        data = await self._fc_post(
            "/runs",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            json=request_body,
            idempotency_key=str(uuid4()),
        )

        # FC returns { run: {...}, logs: [...], gates: [...] }
        run_data = data.get("run", data)

        return WorkflowRunResult(
            run_id=run_data["run_id"],
            workflow_id=run_data["workflow_id"],
            workflow_version=run_data.get("workflow_version", "1.0.0"),
            status=WorkflowRunStatus(run_data["status"]),
            current_step=run_data.get("current_step"),
            step_index=run_data.get("step_index", 0),
            tenant_id=run_data["tenant_id"],
            actor_id=run_data["actor_id"],
            correlation_id=run_data.get("correlation_id", correlation_id),
            input_payload=run_data.get("input_payload", {}),
            output_payload=run_data.get("output_payload"),
            error_details=run_data.get("error_details"),
            receipt_chain=run_data.get("receipt_chain", []),
            workflow_receipt_hash=run_data.get("workflow_receipt_hash"),
            evidence_pack_hash=run_data.get("evidence_pack_hash"),
            evidence_pack_refs=run_data.get("evidence_pack_refs", []),
            created_at=run_data.get("created_at"),
            started_at=run_data.get("started_at"),
            completed_at=run_data.get("completed_at"),
            updated_at=run_data.get("updated_at"),
            logs=[
                WorkflowRunLogEntry.model_validate(log)
                for log in data.get("logs", [])
            ],
            gates=[
                GateInfo.model_validate(gate)
                for gate in data.get("gates", [])
            ],
        )

    async def get_run(
        self,
        run_id: str,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        include_logs: bool = False,
        include_gates: bool = False,
    ) -> WorkflowRunResult:
        """
        Get workflow run details.

        Args:
            run_id: Run identifier
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)
            include_logs: Include log entries
            include_gates: Include gate records

        Returns:
            WorkflowRunResult with full run details

        Example:
            >>> run = await client.workflows.get_run("run-123")
            >>> print(f"Status: {run.status}")
            >>> if run.status == WorkflowRunStatus.PAUSED:
            ...     print(f"Gate: {run.gates[0].gate_name}")
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        params: dict[str, Any] = {}
        if include_logs:
            params["include_logs"] = "true"
        if include_gates:
            params["include_gates"] = "true"

        data = await self._fc_get(
            f"/runs/{run_id}",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            params=params,
        )

        run_data = data.get("run", data)

        # Find pending gate if run is paused
        gate_info = None
        gates = [GateInfo.model_validate(g) for g in data.get("gates", [])]
        if run_data.get("status") == "paused":
            pending_gates = [g for g in gates if g.status == GateStatus.PENDING]
            if pending_gates:
                gate_info = pending_gates[0]

        return WorkflowRunResult(
            run_id=run_data["run_id"],
            workflow_id=run_data["workflow_id"],
            workflow_version=run_data.get("workflow_version", "1.0.0"),
            status=WorkflowRunStatus(run_data["status"]),
            current_step=run_data.get("current_step"),
            step_index=run_data.get("step_index", 0),
            tenant_id=run_data["tenant_id"],
            actor_id=run_data["actor_id"],
            correlation_id=run_data.get("correlation_id", correlation_id),
            input_payload=run_data.get("input_payload", {}),
            output_payload=run_data.get("output_payload"),
            error_details=run_data.get("error_details"),
            receipt_chain=run_data.get("receipt_chain", []),
            workflow_receipt_hash=run_data.get("workflow_receipt_hash"),
            evidence_pack_hash=run_data.get("evidence_pack_hash"),
            evidence_pack_refs=run_data.get("evidence_pack_refs", []),
            gate_info=gate_info,
            gates=gates,
            created_at=run_data.get("created_at"),
            started_at=run_data.get("started_at"),
            completed_at=run_data.get("completed_at"),
            updated_at=run_data.get("updated_at"),
            logs=[
                WorkflowRunLogEntry.model_validate(log)
                for log in data.get("logs", [])
            ],
        )

    async def get_run_logs(
        self,
        run_id: str,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkflowRunLogEntry]:
        """
        Get logs for a workflow run.

        Args:
            run_id: Run identifier
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)
            event_type: Filter by event type (e.g., "FC-RUN-001")
            limit: Maximum entries to return
            offset: Pagination offset

        Returns:
            List of log entries

        Example:
            >>> logs = await client.workflows.get_run_logs("run-123")
            >>> for log in logs:
            ...     print(f"[{log.event_type}] {log.message}")
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }
        if event_type:
            params["event_type"] = event_type

        data = await self._fc_get(
            f"/runs/{run_id}/logs",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            params=params,
        )

        # Response is a list of log entries
        if isinstance(data, list):
            return [WorkflowRunLogEntry.model_validate(log) for log in data]
        return []

    async def resume_run(
        self,
        run_id: str,
        gate_id: str,
        decision: str = "approve",
        input: Optional[dict[str, Any]] = None,
        decision_receipt_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> WorkflowRunResult:
        """
        Resume a paused workflow run after gate resolution.

        Args:
            run_id: Run identifier
            gate_id: Gate identifier to resolve
            decision: "approve" or "deny"
            input: Optional resume input payload
            decision_receipt_id: Optional Keon decision receipt ID
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (auto-generated if not provided)

        Returns:
            Updated WorkflowRunResult

        Raises:
            OmegaError: If run is not paused or gate is invalid

        Example:
            >>> run = await client.workflows.get_run("run-123")
            >>> if run.status == WorkflowRunStatus.PAUSED:
            ...     gate = run.gate_info
            ...     result = await client.workflows.resume_run(
            ...         run_id=run.run_id,
            ...         gate_id=gate.gate_id,
            ...         decision="approve"
            ...     )
            ...     print(f"Resumed: {result.status}")
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        if decision not in ("approve", "deny"):
            from omega_sdk.errors import ValidationError
            raise ValidationError("decision must be 'approve' or 'deny'")

        request_body: dict[str, Any] = {
            "run_id": run_id,
            "gate_id": gate_id,
            "decision": decision,
            "input": input or {},
        }
        if decision_receipt_id:
            request_body["decision_receipt_id"] = decision_receipt_id

        data = await self._fc_post(
            f"/runs/{run_id}:resume",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            json=request_body,
        )

        run_data = data.get("run", data)
        gates = [GateInfo.model_validate(g) for g in data.get("gates", [])]

        return WorkflowRunResult(
            run_id=run_data["run_id"],
            workflow_id=run_data["workflow_id"],
            workflow_version=run_data.get("workflow_version", "1.0.0"),
            status=WorkflowRunStatus(run_data["status"]),
            current_step=run_data.get("current_step"),
            step_index=run_data.get("step_index", 0),
            tenant_id=run_data["tenant_id"],
            actor_id=run_data["actor_id"],
            correlation_id=run_data.get("correlation_id", correlation_id),
            input_payload=run_data.get("input_payload", {}),
            output_payload=run_data.get("output_payload"),
            error_details=run_data.get("error_details"),
            receipt_chain=run_data.get("receipt_chain", []),
            workflow_receipt_hash=run_data.get("workflow_receipt_hash"),
            evidence_pack_hash=run_data.get("evidence_pack_hash"),
            evidence_pack_refs=run_data.get("evidence_pack_refs", []),
            gates=gates,
            created_at=run_data.get("created_at"),
            started_at=run_data.get("started_at"),
            completed_at=run_data.get("completed_at"),
            updated_at=run_data.get("updated_at"),
            logs=[
                WorkflowRunLogEntry.model_validate(log)
                for log in data.get("logs", [])
            ],
        )

    async def register(
        self,
        workflow_yaml: str,
        prompts_poml: str,
        schemas: Optional[dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        version: Optional[str] = None,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> WorkflowRegisterResult:
        """Register workflow artifacts with Federation Core."""
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        body = {
            "workflow_yaml": workflow_yaml,
            "prompts_poml": prompts_poml,
            "schemas": schemas or {},
        }
        if workflow_id:
            body["workflow_id"] = workflow_id
        if version:
            body["version"] = version

        data = await self._fc_post(
            "/workflows/register",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            json=body,
            idempotency_key=str(uuid4()),
        )
        return WorkflowRegisterResult.model_validate(data)

    async def wait_for_completion(
        self,
        run_id: str,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        poll_interval_ms: int = 2000,
        timeout_ms: int = 600_000,
    ) -> WorkflowRunResult:
        """
        Poll for workflow run completion.

        Waits until the run reaches a terminal state (completed, failed, cancelled)
        or a paused state (gate required).

        Args:
            run_id: Run identifier
            tenant_id: Tenant ID (defaults to config)
            actor_id: Actor ID (defaults to config)
            correlation_id: Correlation ID (stable across polls)
            poll_interval_ms: Polling interval in milliseconds (default 2000)
            timeout_ms: Maximum wait time in milliseconds (default 600000 = 10 min)

        Returns:
            Final WorkflowRunResult

        Raises:
            OmegaError: If timeout is exceeded

        Example:
            >>> result = await client.workflows.run_workflow("my-workflow", inputs={})
            >>> final = await client.workflows.wait_for_completion(result.run_id)
            >>> print(f"Final status: {final.status}")
        """
        tenant_id = tenant_id or self._config.tenant_id or ""
        actor_id = actor_id or self._config.actor_id or ""
        # Use stable correlation ID for all polls
        correlation_id = correlation_id or make_correlation_id(tenant_id)

        terminal_states = {
            WorkflowRunStatus.COMPLETED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLED,
            WorkflowRunStatus.PAUSED,  # Also stop on paused (gate required)
        }

        elapsed_ms = 0
        poll_interval_s = poll_interval_ms / 1000.0

        while elapsed_ms < timeout_ms:
            run = await self.get_run(
                run_id=run_id,
                tenant_id=tenant_id,
                actor_id=actor_id,
                correlation_id=correlation_id,
                include_gates=True,
            )

            if run.status in terminal_states:
                return run

            await asyncio.sleep(poll_interval_s)
            elapsed_ms += poll_interval_ms

        from omega_sdk.errors import OmegaError
        raise OmegaError(
            code="TIMEOUT",
            message=f"Workflow run {run_id} did not complete within {timeout_ms}ms",
            retryable=False,
        )
