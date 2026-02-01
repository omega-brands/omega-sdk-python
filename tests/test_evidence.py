"""
Integration tests for OMEGA SDK Evidence Client.
"""

import pytest
from omega_sdk import OmegaClient, OmegaConfig
from omega_sdk.evidence import EvidencePackStatus
from tests.chaos.stub_server import ChaosStubServer, ChaosConfig


@pytest.fixture
async def chaos_server():
    """Start chaos stub server for tests."""
    config = ChaosConfig(
        error_rate=0.0,  # No errors for these tests
        slow_rate=0.0,
        malformed_rate=0.0,
    )
    server = ChaosStubServer(config)
    await server.start(host="127.0.0.1", port=9997)
    yield server


@pytest.fixture
def client():
    """Create SDK client pointing to chaos server."""
    config = OmegaConfig(
        federation_url="http://127.0.0.1:9997",
        tenant_id="test",
        actor_id="evidence_test",
    )
    return OmegaClient(config=config)


@pytest.mark.asyncio
async def test_list_evidence(chaos_server, client):
    """Test listing evidence packs."""
    response = await client.evidence.list()
    assert len(response.items) > 0
    assert response.items[0].status == EvidencePackStatus.SIGNED


@pytest.mark.asyncio
async def test_get_evidence_pack_happy_path(chaos_server, client):
    """Test retrieving a valid evidence pack."""
    pack = await client.evidence.get("valid_hash")
    assert pack.pack_id is not None
    assert pack.status == EvidencePackStatus.SIGNED
    assert pack.authority.alpha_receipt.policy_ref == "pol-001"


@pytest.mark.asyncio
async def test_get_evidence_pack_tampered(chaos_server, client):
    """Test retrieving a tampered evidence pack."""
    pack = await client.evidence.get("tampered")
    assert pack.status == EvidencePackStatus.TAMPERED


@pytest.mark.asyncio
async def test_get_evidence_pack_invalid(chaos_server, client):
    """Test retrieving an invalid evidence pack."""
    pack = await client.evidence.get("invalid")
    assert pack.status == EvidencePackStatus.INVALID


@pytest.mark.asyncio
async def test_get_evidence_pack_missing_blob(chaos_server, client):
    """Test retrieving an evidence pack with missing blobs."""
    pack = await client.evidence.get("missing")
    assert pack.status == EvidencePackStatus.BLOB_MISSING


@pytest.mark.asyncio
async def test_verify_evidence_valid(chaos_server, client):
    """Test verifying a valid evidence pack."""
    result = await client.evidence.verify("valid_hash")
    assert result.is_valid is True
    assert result.verdict == "PASS"


@pytest.mark.asyncio
async def test_verify_evidence_invalid(chaos_server, client):
    """Test verifying an invalid evidence pack."""
    result = await client.evidence.verify("tampered")
    assert result.is_valid is False
    assert result.verdict == "FAIL"


@pytest.mark.asyncio
async def test_fail_closed_on_retrieval_error(chaos_server, client):
    """Test that retrieval errors are surfaced (fail-closed)."""
    from omega_sdk.errors import NotFoundError
    
    with pytest.raises(NotFoundError):
        await client.evidence.get("nonexistent")
