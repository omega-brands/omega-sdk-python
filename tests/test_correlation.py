"""
Tests for correlation ID discipline.

These tests ensure the canonical correlation ID format is enforced everywhere.
"""

import pytest
from uuid import UUID

from omega_sdk.utils.correlation import (
    make_correlation_id,
    validate_correlation_id,
    normalize_correlation_id,
    CorrelationError,
)


def test_make_correlation_id():
    """Test creating a canonical correlation ID."""
    cid = make_correlation_id("acme")

    # Should match pattern: t:<tenant>|c:<uuidv7>
    assert cid.startswith("t:acme|c:")

    # Should be parseable
    tenant, uuid = validate_correlation_id(cid)
    assert tenant == "acme"
    assert isinstance(uuid, UUID)


def test_make_correlation_id_invalid_tenant():
    """Test that tenant IDs cannot contain pipes."""
    with pytest.raises(CorrelationError, match="cannot contain '\\|'"):
        make_correlation_id("acme|evil")


def test_make_correlation_id_empty_tenant():
    """Test that tenant IDs cannot be empty."""
    with pytest.raises(CorrelationError, match="cannot be empty"):
        make_correlation_id("")


def test_validate_correlation_id_valid():
    """Test validating a valid correlation ID."""
    cid = "t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789"
    tenant, uuid = validate_correlation_id(cid)

    assert tenant == "acme"
    assert isinstance(uuid, UUID)
    assert str(uuid) == "0194f0b0-1234-7890-abcd-ef0123456789"


def test_validate_correlation_id_invalid_format():
    """Test validating an invalid correlation ID format."""
    with pytest.raises(CorrelationError, match="Invalid correlation ID format"):
        validate_correlation_id("invalid")

    with pytest.raises(CorrelationError, match="Invalid correlation ID format"):
        validate_correlation_id("t:acme")

    with pytest.raises(CorrelationError, match="Invalid correlation ID format"):
        validate_correlation_id("c:0194f0b0-1234-7890-abcd-ef0123456789")


def test_validate_correlation_id_invalid_uuid():
    """Test validating a correlation ID with invalid UUID."""
    with pytest.raises(CorrelationError, match="Invalid UUID"):
        validate_correlation_id("t:acme|c:not-a-uuid")


def test_normalize_correlation_id():
    """Test normalizing a correlation ID."""
    cid = "t:acme|c:0194F0B0-1234-7890-ABCD-EF0123456789"
    normalized = normalize_correlation_id(cid)

    # UUID should be lowercase
    assert normalized == "t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789"


def test_correlation_id_roundtrip():
    """Test creating, validating, and normalizing a correlation ID."""
    cid = make_correlation_id("acme")
    tenant, uuid = validate_correlation_id(cid)
    normalized = normalize_correlation_id(cid)

    assert tenant == "acme"
    assert normalized == cid  # Should already be normalized
