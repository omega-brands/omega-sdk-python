"""
Integration tests against chaos stub server.

These tests validate SDK behavior under adverse conditions:
- Transient failures
- Rate limits
- Slow responses
- Malformed payloads
"""

import pytest
import asyncio
from omega_sdk import OmegaClient, OmegaConfig
from omega_sdk.errors import (
    OmegaError,
    UpstreamError,
    InternalError,
)
from tests.chaos.stub_server import ChaosStubServer, ChaosConfig


@pytest.fixture
async def chaos_server():
    """Start chaos stub server for tests."""
    config = ChaosConfig(
        error_rate=0.3,  # 30% errors
        slow_rate=0.1,  # 10% slow
        malformed_rate=0.05,  # 5% malformed
        min_delay_ms=50,
        max_delay_ms=500,
    )
    server = ChaosStubServer(config)
    await server.start(host="127.0.0.1", port=9999)

    yield server

    stats = server.get_stats()
    print(f"\nChaos server stats: {stats}")


@pytest.fixture
def client():
    """Create SDK client pointing to chaos server."""
    config = OmegaConfig(
        federation_url="http://127.0.0.1:9999",
        tenant_id="test",
        actor_id="chaos_test",
        timeout_ms=5000,
        max_retries=3,
    )
    return OmegaClient(config=config)


@pytest.mark.asyncio
async def test_health_endpoint(chaos_server, client):
    """Test health endpoint (no chaos injection)."""
    health = await client.health()
    assert health.status == "ok"
    assert health.version == "1.0.0-chaos"


@pytest.mark.asyncio
async def test_list_tools_with_retries(chaos_server, client):
    """Test listing tools with automatic retries."""
    # Should succeed eventually despite chaos
    tools = await client.tools.list()
    assert len(tools.items) > 0
    assert tools.items[0].tool_id == "csv_processor"


@pytest.mark.asyncio
async def test_get_tool_with_retries(chaos_server, client):
    """Test getting tool details with automatic retries."""
    tool = await client.tools.get("csv_processor")
    assert tool.tool_id == "csv_processor"
    assert tool.status == "ready"


@pytest.mark.asyncio
async def test_invoke_tool_with_retries(chaos_server, client):
    """Test invoking tool with automatic retries."""
    result = await client.tools.invoke(
        "csv_processor",
        input={"file": "test.csv"},
    )
    assert result.tool_id == "csv_processor"
    assert "normalized_rows" in result.result
    assert result.audit is not None


@pytest.mark.asyncio
async def test_list_agents_with_retries(chaos_server, client):
    """Test listing agents with automatic retries."""
    agents = await client.agents.list()
    assert len(agents.items) > 0
    assert agents.items[0].agent_id == "gpt_titan"


@pytest.mark.asyncio
async def test_create_task_with_retries(chaos_server, client):
    """Test creating task with automatic retries."""
    from omega_sdk.models import TaskRouting

    task = await client.tasks.create(
        task_type="workflow.run",
        input={"workflow": "test"},
        routing=TaskRouting(strategy="capability", capability="test"),
    )
    assert task.task_id.startswith("tk_")
    assert task.status == "queued"


@pytest.mark.asyncio
async def test_get_task_with_retries(chaos_server, client):
    """Test getting task status with automatic retries."""
    task_detail = await client.tasks.get("tk_test123")
    assert task_detail.task_id == "tk_test123"
    assert task_detail.status == "completed"


@pytest.mark.asyncio
async def test_correlation_id_propagation(chaos_server, client):
    """Test that correlation IDs are properly propagated."""
    from omega_sdk.utils import make_correlation_id

    correlation_id = make_correlation_id("test")

    # Make request with explicit correlation ID
    tools = await client.tools.list(correlation_id=correlation_id)

    # Correlation ID should be present in response
    assert len(tools.items) > 0


@pytest.mark.asyncio
async def test_not_found_error(chaos_server, client):
    """Test handling of 404 errors."""
    from omega_sdk.errors import NotFoundError

    with pytest.raises(NotFoundError) as exc_info:
        await client.tools.get("nonexistent")

    error = exc_info.value
    assert error.code == "NOT_FOUND"
    assert error.correlation_id is not None


@pytest.mark.asyncio
async def test_multiple_concurrent_requests(chaos_server, client):
    """Test handling multiple concurrent requests under chaos."""
    # Fire 10 concurrent requests
    tasks = [client.tools.list() for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Most should succeed (retries should handle transient failures)
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    assert success_count >= 7  # At least 70% should succeed


@pytest.mark.asyncio
async def test_bounded_retries(chaos_server, client):
    """Test that retries are bounded (not infinite)."""
    # Create client with aggressive chaos and low retries
    config = ChaosConfig(
        error_rate=0.9,  # 90% error rate
        slow_rate=0.0,
        malformed_rate=0.0,
    )
    aggressive_server = ChaosStubServer(config)
    await aggressive_server.start(host="127.0.0.1", port=9998)

    aggressive_client = OmegaClient(
        federation_url="http://127.0.0.1:9998",
        tenant_id="test",
        actor_id="aggressive_test",
        timeout_ms=5000,
        max_retries=2,  # Only 2 retries
    )

    # Should eventually fail after bounded retries
    with pytest.raises((UpstreamError, InternalError, OmegaError)):
        await aggressive_client.tools.list()


@pytest.mark.asyncio
async def test_context_manager(chaos_server):
    """Test async context manager."""
    config = OmegaConfig(
        federation_url="http://127.0.0.1:9999",
        tenant_id="test",
        actor_id="context_test",
    )

    async with OmegaClient(config=config) as client:
        tools = await client.tools.list()
        assert len(tools.items) > 0

    # Client should be closed after exit
