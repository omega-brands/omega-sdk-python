"""
Tests for OmegaClient.workflows namespace (PR 5).

These are contract tests that verify the SDK correctly:
1. Calls the FC endpoints
2. Threads tenant_id/actor_id/correlation_id
3. Returns typed DTOs
4. Handles gate/resume flows
"""

import os
import sys
import asyncio
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure omega-sdk is in path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


from omega_sdk import (
    OmegaClient,
    OmegaConfig,
    WorkflowRunStatus,
    GateStatus,
    GateInfo,
    WorkflowRunLogEntry,
    WorkflowRunResult,
)
from omega_sdk.workflows import WorkflowsNamespace


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Create a mock config."""
    return OmegaConfig(
        federation_url="http://localhost:9405",
        api_key="test-api-key",
        tenant_id="tenant_test",
        actor_id="user_test",
        timeout_ms=30000,
        max_retries=3,
    )


@pytest.fixture
def mock_fc_responses():
    """Standard FC response shapes."""
    return {
        "create_run": {
            "run": {
                "run_id": "run-123",
                "workflow_id": "test-workflow",
                "workflow_version": "1.0.0",
                "status": "pending",
                "step_index": 0,
                "tenant_id": "tenant_test",
                "actor_id": "user_test",
                "correlation_id": "corr-123",
                "input_payload": {"key": "value"},
                "receipt_chain": [],
                "evidence_pack_refs": [],
                "created_at": "2024-01-01T00:00:00Z",
            },
            "logs": [
                {
                    "log_id": "log-1",
                    "run_id": "run-123",
                    "event_type": "FC-RUN-001",
                    "event_category": "workflow",
                    "actor_id": "user_test",
                    "message": "Workflow run created",
                    "details": {},
                    "timestamp": "2024-01-01T00:00:00Z",
                }
            ],
            "gates": [],
        },
        "get_run_paused": {
            "run": {
                "run_id": "run-456",
                "workflow_id": "gated-workflow",
                "workflow_version": "1.0.0",
                "status": "paused",
                "step_index": 1,
                "current_step": "deploy_step",
                "tenant_id": "tenant_test",
                "actor_id": "user_test",
                "correlation_id": "corr-456",
                "input_payload": {},
                "receipt_chain": ["hash-1"],
                "evidence_pack_refs": ["evidence-1"],
            },
            "logs": [
                {
                    "log_id": "log-1",
                    "run_id": "run-456",
                    "event_type": "FC-RUN-001",
                    "event_category": "workflow",
                    "actor_id": "user_test",
                    "message": "Run created",
                    "details": {},
                    "timestamp": "2024-01-01T00:00:00Z",
                },
                {
                    "log_id": "log-2",
                    "run_id": "run-456",
                    "event_type": "FC-GATE-001",
                    "event_category": "gate",
                    "actor_id": "user_test",
                    "message": "Gate required",
                    "details": {},
                    "timestamp": "2024-01-01T00:01:00Z",
                },
            ],
            "gates": [
                {
                    "gate_id": "gate-789",
                    "run_id": "run-456",
                    "step_id": "deploy_step",
                    "gate_type": "human_approval",
                    "gate_name": "Deploy Approval",
                    "status": "pending",
                    "required_approvers": ["admin_1"],
                    "created_at": "2024-01-01T00:01:00Z",
                }
            ],
        },
        "resume_approved": {
            "run": {
                "run_id": "run-456",
                "workflow_id": "gated-workflow",
                "workflow_version": "1.0.0",
                "status": "running",
                "step_index": 1,
                "tenant_id": "tenant_test",
                "actor_id": "user_test",
                "correlation_id": "corr-456",
                "input_payload": {},
                "receipt_chain": ["hash-1"],
            },
            "logs": [
                {
                    "log_id": "log-3",
                    "run_id": "run-456",
                    "event_type": "FC-GATE-002",
                    "event_category": "gate",
                    "actor_id": "user_test",
                    "message": "Gate approved",
                    "details": {},
                    "timestamp": "2024-01-01T00:02:00Z",
                },
            ],
            "gates": [
                {
                    "gate_id": "gate-789",
                    "run_id": "run-456",
                    "step_id": "deploy_step",
                    "gate_type": "human_approval",
                    "gate_name": "Deploy Approval",
                    "status": "approved",
                    "required_approvers": ["admin_1"],
                    "approved_by": "user_test",
                    "created_at": "2024-01-01T00:01:00Z",
                    "resolved_at": "2024-01-01T00:02:00Z",
                }
            ],
        },
        "resume_denied": {
            "run": {
                "run_id": "run-456",
                "workflow_id": "gated-workflow",
                "workflow_version": "1.0.0",
                "status": "failed",
                "step_index": 1,
                "tenant_id": "tenant_test",
                "actor_id": "user_test",
                "correlation_id": "corr-456",
                "input_payload": {},
                "error_details": {"gate_rejected": True, "reason": "Denied via :resume endpoint"},
            },
            "logs": [],
            "gates": [
                {
                    "gate_id": "gate-789",
                    "run_id": "run-456",
                    "step_id": "deploy_step",
                    "gate_type": "human_approval",
                    "gate_name": "Deploy Approval",
                    "status": "rejected",
                    "required_approvers": ["admin_1"],
                    "rejection_reason": "Denied via :resume endpoint",
                    "created_at": "2024-01-01T00:01:00Z",
                    "resolved_at": "2024-01-01T00:02:00Z",
                }
            ],
        },
        "get_logs": [
            {
                "log_id": "log-1",
                "run_id": "run-123",
                "event_type": "FC-RUN-001",
                "event_category": "workflow",
                "actor_id": "user_test",
                "message": "Workflow run created",
                "details": {},
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "log_id": "log-2",
                "run_id": "run-123",
                "event_type": "FC-STEP-001",
                "event_category": "workflow",
                "step_id": "step-1",
                "actor_id": "user_test",
                "message": "Step started",
                "details": {},
                "timestamp": "2024-01-01T00:00:01Z",
            },
        ],
    }


# =============================================================================
# WorkflowRunResult DTO Tests
# =============================================================================


class TestWorkflowDTOs:
    """Test workflow DTOs."""

    def test_workflow_run_status_enum(self):
        """Test WorkflowRunStatus enum values."""
        assert WorkflowRunStatus.PENDING == "pending"
        assert WorkflowRunStatus.RUNNING == "running"
        assert WorkflowRunStatus.PAUSED == "paused"
        assert WorkflowRunStatus.COMPLETED == "completed"
        assert WorkflowRunStatus.FAILED == "failed"
        assert WorkflowRunStatus.CANCELLED == "cancelled"

    def test_gate_status_enum(self):
        """Test GateStatus enum values."""
        assert GateStatus.PENDING == "pending"
        assert GateStatus.APPROVED == "approved"
        assert GateStatus.REJECTED == "rejected"
        assert GateStatus.EXPIRED == "expired"
        assert GateStatus.BYPASSED == "bypassed"

    def test_workflow_run_result_creation(self):
        """Test WorkflowRunResult model creation."""
        result = WorkflowRunResult(
            run_id="run-123",
            workflow_id="test-workflow",
            status=WorkflowRunStatus.PENDING,
            tenant_id="tenant_test",
            actor_id="user_test",
            correlation_id="corr-123",
        )

        assert result.run_id == "run-123"
        assert result.workflow_id == "test-workflow"
        assert result.status == WorkflowRunStatus.PENDING
        assert result.tenant_id == "tenant_test"
        assert result.gates == []
        assert result.logs == []

    def test_gate_info_creation(self):
        """Test GateInfo model creation."""
        gate = GateInfo(
            gate_id="gate-123",
            run_id="run-456",
            step_id="deploy_step",
            gate_type="human_approval",
            gate_name="Deploy Approval",
            status=GateStatus.PENDING,
            required_approvers=["admin_1"],
        )

        assert gate.gate_id == "gate-123"
        assert gate.status == GateStatus.PENDING
        assert "admin_1" in gate.required_approvers


# =============================================================================
# WorkflowsNamespace Contract Tests
# =============================================================================


class TestWorkflowsNamespaceRunWorkflow:
    """Test run_workflow method."""

    @pytest.mark.asyncio
    async def test_run_workflow_returns_run_id_and_status(self, mock_config, mock_fc_responses):
        """T1: run_workflow() returns run_id + status."""
        # Create mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_fc_responses["create_run"]

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        # Create namespace with mocked client
        mock_gateway = MagicMock()
        mock_gateway._client = mock_http_client
        mock_gateway.config = mock_config

        namespace = WorkflowsNamespace(mock_gateway, mock_config)

        # Call run_workflow
        result = await namespace.run_workflow(
            workflow_id="test-workflow",
            inputs={"key": "value"},
        )

        # Assertions
        assert result.run_id == "run-123"
        assert result.status == WorkflowRunStatus.PENDING
        assert result.workflow_id == "test-workflow"

        # Verify HTTP call was made
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert "/api/fc/runs" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_run_workflow_threads_headers(self, mock_config, mock_fc_responses):
        """T2: run_workflow() threads tenant_id/actor_id/correlation_id in headers."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_fc_responses["create_run"]

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        mock_gateway = MagicMock()
        mock_gateway._client = mock_http_client
        mock_gateway.config = mock_config

        namespace = WorkflowsNamespace(mock_gateway, mock_config)

        await namespace.run_workflow(
            workflow_id="test-workflow",
            inputs={},
            tenant_id="custom_tenant",
            actor_id="custom_actor",
            correlation_id="custom_corr_001",
        )

        # Verify headers
        call_args = mock_http_client.post.call_args
        headers = call_args[1]["headers"]

        assert headers["X-Tenant-Id"] == "custom_tenant"
        assert headers["X-Actor-Id"] == "custom_actor"
        assert headers["X-Correlation-Id"] == "custom_corr_001"


class TestWorkflowsNamespaceGetRun:
    """Test get_run method."""

    @pytest.mark.asyncio
    async def test_get_run_paused_has_gate_info(self, mock_config, mock_fc_responses):
        """T3: If status is paused, gate_info is present."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_fc_responses["get_run_paused"]

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response

        mock_gateway = MagicMock()
        mock_gateway._client = mock_http_client
        mock_gateway.config = mock_config

        namespace = WorkflowsNamespace(mock_gateway, mock_config)

        result = await namespace.get_run("run-456", include_gates=True)

        # Assertions
        assert result.status == WorkflowRunStatus.PAUSED
        assert result.gate_info is not None
        assert result.gate_info.gate_id == "gate-789"
        assert result.gate_info.status == GateStatus.PENDING
        assert len(result.gates) == 1


class TestWorkflowsNamespaceResumeRun:
    """Test resume_run method."""

    @pytest.mark.asyncio
    async def test_resume_run_approved_transitions_to_running(self, mock_config, mock_fc_responses):
        """T4: resume_run() with decision='approve' transitions status correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_fc_responses["resume_approved"]

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        mock_gateway = MagicMock()
        mock_gateway._client = mock_http_client
        mock_gateway.config = mock_config

        namespace = WorkflowsNamespace(mock_gateway, mock_config)

        result = await namespace.resume_run(
            run_id="run-456",
            gate_id="gate-789",
            decision="approve",
            input={"answers": ["a1"]},
        )

        # Assertions
        assert result.status == WorkflowRunStatus.RUNNING
        assert len(result.gates) == 1
        assert result.gates[0].status == GateStatus.APPROVED
        assert result.gates[0].approved_by == "user_test"

    @pytest.mark.asyncio
    async def test_resume_run_denied_transitions_to_failed(self, mock_config, mock_fc_responses):
        """T5: resume_run() with decision='deny' transitions to failed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_fc_responses["resume_denied"]

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        mock_gateway = MagicMock()
        mock_gateway._client = mock_http_client
        mock_gateway.config = mock_config

        namespace = WorkflowsNamespace(mock_gateway, mock_config)

        result = await namespace.resume_run(
            run_id="run-456",
            gate_id="gate-789",
            decision="deny",
        )

        # Assertions
        assert result.status == WorkflowRunStatus.FAILED
        assert len(result.gates) == 1
        assert result.gates[0].status == GateStatus.REJECTED
        assert result.error_details is not None
        assert result.error_details.get("gate_rejected") is True

    @pytest.mark.asyncio
    async def test_resume_run_calls_correct_endpoint(self, mock_config, mock_fc_responses):
        """T6: resume_run() calls POST /api/fc/runs/{id}:resume."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_fc_responses["resume_approved"]

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        mock_gateway = MagicMock()
        mock_gateway._client = mock_http_client
        mock_gateway.config = mock_config

        namespace = WorkflowsNamespace(mock_gateway, mock_config)

        await namespace.resume_run(
            run_id="run-456",
            gate_id="gate-789",
            decision="approve",
            input={"answers": ["a1", "a2"]},
            decision_receipt_id="sha256:receipt123",
        )

        # Verify endpoint
        call_args = mock_http_client.post.call_args
        url = call_args[0][0]
        json_body = call_args[1]["json"]

        assert "/api/fc/runs/run-456:resume" in url
        assert json_body["run_id"] == "run-456"
        assert json_body["gate_id"] == "gate-789"
        assert json_body["decision"] == "approve"
        assert json_body["input"]["answers"] == ["a1", "a2"]
        assert json_body["decision_receipt_id"] == "sha256:receipt123"

    @pytest.mark.asyncio
    async def test_register_idempotent(self, mock_config):
        """T6b: register() parses idempotent registration response."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "workflow_id": "forgepilot.teaser.v1",
            "version": "1.0.0",
            "artifact_hashes": {
                "workflowYaml": "sha256:a",
                "promptsPoml": "sha256:b",
                "schemas": {"output.schema.json": "sha256:c"},
            },
            "idempotent": True,
        }

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        mock_gateway = MagicMock()
        mock_gateway._client = mock_http_client
        mock_gateway.config = mock_config

        namespace = WorkflowsNamespace(mock_gateway, mock_config)
        result = await namespace.register(
            workflow_yaml="id: forgepilot.teaser.v1\nversion: 1.0.0",
            prompts_poml="<Prompt id='p'>x</Prompt>",
        )
        assert result.workflow_id == "forgepilot.teaser.v1"
        assert result.idempotent is True


class TestWorkflowsNamespaceGetLogs:
    """Test get_run_logs method."""

    @pytest.mark.asyncio
    async def test_get_run_logs_returns_entries(self, mock_config, mock_fc_responses):
        """T7: get_run_logs() returns log entries."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_fc_responses["get_logs"]

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response

        mock_gateway = MagicMock()
        mock_gateway._client = mock_http_client
        mock_gateway.config = mock_config

        namespace = WorkflowsNamespace(mock_gateway, mock_config)

        logs = await namespace.get_run_logs("run-123")

        # Assertions
        assert len(logs) == 2
        assert logs[0].event_type == "FC-RUN-001"
        assert logs[1].event_type == "FC-STEP-001"
        assert logs[1].step_id == "step-1"


class TestWorkflowsNamespaceWaitForCompletion:
    """Test wait_for_completion method."""

    @pytest.mark.asyncio
    async def test_wait_for_completion_returns_on_terminal_state(self, mock_config):
        """T8: wait_for_completion() returns when run reaches terminal state."""
        # First call returns running, second returns completed
        responses = [
            {
                "run": {
                    "run_id": "run-123",
                    "workflow_id": "test-workflow",
                    "status": "running",
                    "tenant_id": "tenant_test",
                    "actor_id": "user_test",
                    "correlation_id": "corr-123",
                },
                "gates": [],
                "logs": [],
            },
            {
                "run": {
                    "run_id": "run-123",
                    "workflow_id": "test-workflow",
                    "status": "completed",
                    "tenant_id": "tenant_test",
                    "actor_id": "user_test",
                    "correlation_id": "corr-123",
                    "output_payload": {"result": "success"},
                },
                "gates": [],
                "logs": [],
            },
        ]

        call_count = [0]

        def side_effect(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return mock_resp

        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = side_effect

        mock_gateway = MagicMock()
        mock_gateway._client = mock_http_client
        mock_gateway.config = mock_config

        namespace = WorkflowsNamespace(mock_gateway, mock_config)

        result = await namespace.wait_for_completion(
            run_id="run-123",
            poll_interval_ms=10,  # Fast polling for test
            timeout_ms=5000,
        )

        assert result.status == WorkflowRunStatus.COMPLETED
        assert call_count[0] >= 2

    @pytest.mark.asyncio
    async def test_wait_for_completion_stops_on_paused(self, mock_config, mock_fc_responses):
        """T9: wait_for_completion() also stops on paused status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_fc_responses["get_run_paused"]

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response

        mock_gateway = MagicMock()
        mock_gateway._client = mock_http_client
        mock_gateway.config = mock_config

        namespace = WorkflowsNamespace(mock_gateway, mock_config)

        result = await namespace.wait_for_completion(
            run_id="run-456",
            poll_interval_ms=10,
            timeout_ms=5000,
        )

        assert result.status == WorkflowRunStatus.PAUSED
        assert result.gate_info is not None


# =============================================================================
# OmegaClient Integration Tests
# =============================================================================


class TestOmegaClientWorkflowsIntegration:
    """Test OmegaClient.workflows integration."""

    def test_client_has_workflows_namespace(self, mock_config):
        """T10: OmegaClient has workflows namespace."""
        with patch("omega_sdk.client.FederationCoreGateway"):
            client = OmegaClient(config=mock_config)
            assert hasattr(client, "workflows")
            assert isinstance(client.workflows, WorkflowsNamespace)

    def test_no_imports_from_omega_core(self):
        """T11: No imports from omega-core/workflows in SDK."""
        import omega_sdk.workflows as workflows_module
        import omega_sdk.client as client_module

        # Get all imported module names
        workflows_imports = set(workflows_module.__dict__.keys())
        client_imports = set(client_module.__dict__.keys())

        # Should NOT have any omega_core imports
        for module_name in workflows_imports:
            assert "omega_core" not in str(module_name).lower()

        for module_name in client_imports:
            assert "omega_core" not in str(module_name).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
