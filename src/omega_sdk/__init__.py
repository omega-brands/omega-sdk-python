"""
OMEGA SDK - Python client for Federation Core.

This SDK provides a clean, typed, governance-aware interface to the OMEGA
Federation Core API. It handles correlation discipline, structured errors,
retry logic, and optional receipt threading for governed operations.

Example:
    >>> from omega_sdk import OmegaClient
    >>> client = OmegaClient.from_env()
    >>> tools = await client.tools.list()
    >>> result = await client.tools.invoke("csv_processor", input={"file": "data.csv"})
"""

__version__ = "1.0.0"

from omega_sdk.client import OmegaClient
from omega_sdk.config import OmegaConfig
from omega_sdk.errors import (
    OmegaError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    UpstreamError,
    InternalError,
)
from omega_sdk.models import (
    Envelope,
    Meta,
    Error,
    Agent,
    Tool,
    Task,
    TaskStatus,
)
from omega_sdk.workflows import (
    WorkflowRunStatus,
    GateStatus,
    GateInfo,
    WorkflowRunLogEntry,
    WorkflowRunOptions,
    WorkflowRunResult,
    ResumeRunResult,
    WorkflowRegisterRequest,
    WorkflowRegisterResult,
)

__all__ = [
    # Core client
    "OmegaClient",
    "OmegaConfig",
    # Errors
    "OmegaError",
    "AuthenticationError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
    "UpstreamError",
    "InternalError",
    # Models
    "Envelope",
    "Meta",
    "Error",
    "Agent",
    "Tool",
    "Task",
    "TaskStatus",
    # Workflow models
    "WorkflowRunStatus",
    "GateStatus",
    "GateInfo",
    "WorkflowRunLogEntry",
    "WorkflowRunOptions",
    "WorkflowRunResult",
    "ResumeRunResult",
    "WorkflowRegisterRequest",
    "WorkflowRegisterResult",
]
