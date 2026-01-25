"""
Tests for structured error handling.

Ensures all errors are correlation-aware and properly mapped from HTTP responses.
"""

import pytest

from omega_sdk.errors import (
    OmegaError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    UpstreamError,
    InternalError,
    error_from_response,
)


def test_omega_error_basic():
    """Test basic OmegaError creation."""
    error = OmegaError(
        code="TEST_ERROR",
        message="Test error message",
        details={"foo": "bar"},
        retryable=True,
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
        request_id="fc_01H...",
    )

    assert error.code == "TEST_ERROR"
    assert error.message == "Test error message"
    assert error.details == {"foo": "bar"}
    assert error.retryable is True
    assert error.correlation_id == "t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789"
    assert error.request_id == "fc_01H..."


def test_authentication_error():
    """Test AuthenticationError."""
    error = AuthenticationError(
        message="Invalid token",
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
    )

    assert error.code == "UNAUTHENTICATED"
    assert error.message == "Invalid token"
    assert error.retryable is False


def test_validation_error():
    """Test ValidationError."""
    error = ValidationError(
        message="Missing required field",
        field_errors=[{"field": "tool_id", "reason": "required"}],
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
    )

    assert error.code == "VALIDATION_FAILED"
    assert error.message == "Missing required field"
    assert error.details["field_errors"] == [{"field": "tool_id", "reason": "required"}]
    assert error.retryable is False


def test_not_found_error():
    """Test NotFoundError."""
    error = NotFoundError(
        message="Tool not found",
        resource_type="tool",
        resource_id="csv_processor",
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
    )

    assert error.code == "NOT_FOUND"
    assert error.message == "Tool not found"
    assert error.details["resource_type"] == "tool"
    assert error.details["resource_id"] == "csv_processor"
    assert error.retryable is False


def test_rate_limit_error():
    """Test RateLimitError."""
    error = RateLimitError(
        message="Rate limit exceeded",
        retry_after_ms=5000,
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
    )

    assert error.code == "RATE_LIMITED"
    assert error.message == "Rate limit exceeded"
    assert error.details["retry_after_ms"] == 5000
    assert error.retryable is True


def test_upstream_error():
    """Test UpstreamError."""
    error = UpstreamError(
        message="Upstream service failed",
        upstream_service="keon_runtime",
        upstream_status=503,
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
    )

    assert error.code == "UPSTREAM_ERROR"
    assert error.message == "Upstream service failed"
    assert error.details["upstream_service"] == "keon_runtime"
    assert error.details["upstream_status"] == 503
    assert error.retryable is True


def test_internal_error():
    """Test InternalError."""
    error = InternalError(
        message="Internal server error",
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
    )

    assert error.code == "INTERNAL_ERROR"
    assert error.message == "Internal server error"
    assert error.retryable is False


def test_error_from_response_400():
    """Test creating error from 400 response."""
    error_data = {
        "code": "VALIDATION_FAILED",
        "message": "Missing required field: tool_id",
        "details": {"field_errors": [{"field": "tool_id", "reason": "required"}]},
        "retryable": False,
    }

    error = error_from_response(
        status_code=400,
        error_data=error_data,
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
        request_id="fc_01H...",
    )

    assert isinstance(error, ValidationError)
    assert error.code == "VALIDATION_FAILED"
    assert error.message == "Missing required field: tool_id"


def test_error_from_response_401():
    """Test creating error from 401 response."""
    error_data = {
        "code": "UNAUTHENTICATED",
        "message": "Invalid token",
        "retryable": False,
    }

    error = error_from_response(
        status_code=401,
        error_data=error_data,
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
    )

    assert isinstance(error, AuthenticationError)


def test_error_from_response_404():
    """Test creating error from 404 response."""
    error_data = {
        "code": "NOT_FOUND",
        "message": "Tool not found",
        "retryable": False,
    }

    error = error_from_response(
        status_code=404,
        error_data=error_data,
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
    )

    assert isinstance(error, NotFoundError)


def test_error_from_response_429():
    """Test creating error from 429 response."""
    error_data = {
        "code": "RATE_LIMITED",
        "message": "Rate limit exceeded",
        "details": {"retry_after_ms": 5000},
        "retryable": True,
    }

    error = error_from_response(
        status_code=429,
        error_data=error_data,
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
    )

    assert isinstance(error, RateLimitError)
    assert error.retryable is True


def test_error_from_response_500():
    """Test creating error from 500 response."""
    error_data = {
        "code": "INTERNAL_ERROR",
        "message": "Internal server error",
        "retryable": False,
    }

    error = error_from_response(
        status_code=500,
        error_data=error_data,
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
    )

    assert isinstance(error, InternalError)


def test_error_from_response_502():
    """Test creating error from 502 response."""
    error_data = {
        "code": "UPSTREAM_ERROR",
        "message": "Bad gateway",
        "details": {"upstream_service": "keon_runtime", "upstream_status": 503},
        "retryable": True,
    }

    error = error_from_response(
        status_code=502,
        error_data=error_data,
        correlation_id="t:acme|c:0194f0b0-1234-7890-abcd-ef0123456789",
    )

    assert isinstance(error, UpstreamError)
    assert error.retryable is True
