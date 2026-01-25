"""
Canonical correlation ID helpers.

OMEGA SDK enforces the canonical format: t:<TenantId>|c:<UUIDv7>

This ensures all operations are traceable to a tenant and can be correlated
across distributed systems with time-ordered UUIDs.
"""

import re
from uuid import UUID
from uuid7 import uuid7


# Canonical format: t:<tenant>|c:<uuidv7>
CORRELATION_ID_PATTERN = re.compile(r"^t:([^|]+)\|c:([0-9a-fA-F-]{36})$")


class CorrelationError(ValueError):
    """Raised when correlation ID validation fails."""
    pass


def make_correlation_id(tenant_id: str) -> str:
    """
    Create a canonical correlation ID.

    Args:
        tenant_id: Tenant identifier (must not contain '|')

    Returns:
        Canonical correlation ID: t:<tenant>|c:<uuidv7>

    Raises:
        CorrelationError: If tenant_id contains '|'

    Example:
        >>> cid = make_correlation_id("acme")
        >>> print(cid)
        t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789
    """
    if "|" in tenant_id:
        raise CorrelationError(f"Tenant ID cannot contain '|': {tenant_id}")
    if not tenant_id.strip():
        raise CorrelationError("Tenant ID cannot be empty")

    correlation_uuid = uuid7()
    return f"t:{tenant_id}|c:{correlation_uuid}"


def validate_correlation_id(correlation_id: str) -> tuple[str, UUID]:
    """
    Validate and parse a correlation ID.

    Args:
        correlation_id: Correlation ID to validate

    Returns:
        Tuple of (tenant_id, uuid)

    Raises:
        CorrelationError: If correlation ID is invalid

    Example:
        >>> tenant, uuid = validate_correlation_id("t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789")
        >>> print(tenant)
        acme
    """
    match = CORRELATION_ID_PATTERN.match(correlation_id)
    if not match:
        raise CorrelationError(
            f"Invalid correlation ID format. Expected 't:<tenant>|c:<uuidv7>', got: {correlation_id}"
        )

    tenant_id, uuid_str = match.groups()

    try:
        correlation_uuid = UUID(uuid_str)
    except ValueError as e:
        raise CorrelationError(f"Invalid UUID in correlation ID: {uuid_str}") from e

    return tenant_id, correlation_uuid


def normalize_correlation_id(correlation_id: str) -> str:
    """
    Normalize and validate a correlation ID.

    Args:
        correlation_id: Correlation ID to normalize

    Returns:
        Normalized correlation ID (lowercase UUID)

    Raises:
        CorrelationError: If correlation ID is invalid
    """
    tenant_id, correlation_uuid = validate_correlation_id(correlation_id)
    return f"t:{tenant_id}|c:{correlation_uuid}"
