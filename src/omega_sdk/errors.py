"""
Typed errors for OMEGA SDK.

All errors are correlation-aware and structured according to the Federation
Core error model (KeonResult-style envelope discipline).
"""

from typing import Any, Optional


class OmegaError(Exception):
    """
    Base exception for all OMEGA SDK errors.

    Attributes:
        code: Error code (e.g., "VALIDATION_FAILED", "UPSTREAM_ERROR")
        message: Human-readable error message
        details: Additional error details
        retryable: Whether the error is retryable
        correlation_id: Correlation ID from the request (if available)
        request_id: Federation Core request ID (if available)
    """

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
        retryable: bool = False,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable
        self.correlation_id = correlation_id
        self.request_id = request_id

    def __repr__(self) -> str:
        parts = [f"code={self.code!r}", f"message={self.message!r}"]
        if self.correlation_id:
            parts.append(f"correlation_id={self.correlation_id!r}")
        if self.request_id:
            parts.append(f"request_id={self.request_id!r}")
        return f"{self.__class__.__name__}({', '.join(parts)})"


class AuthenticationError(OmegaError):
    """Raised when authentication fails (401)."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(
            code="UNAUTHENTICATED",
            message=message,
            details=details,
            retryable=False,
            correlation_id=correlation_id,
            request_id=request_id,
        )


class ForbiddenError(OmegaError):
    """Raised when access is forbidden (403)."""

    def __init__(
        self,
        message: str = "Access forbidden",
        details: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            details=details,
            retryable=False,
            correlation_id=correlation_id,
            request_id=request_id,
        )


class ValidationError(OmegaError):
    """Raised when request validation fails (400)."""

    def __init__(
        self,
        message: str,
        field_errors: Optional[list[dict[str, str]]] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        details = {"field_errors": field_errors} if field_errors else {}
        super().__init__(
            code="VALIDATION_FAILED",
            message=message,
            details=details,
            retryable=False,
            correlation_id=correlation_id,
            request_id=request_id,
        )


class NotFoundError(OmegaError):
    """Raised when a resource is not found (404)."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            code="NOT_FOUND",
            message=message,
            details=details,
            retryable=False,
            correlation_id=correlation_id,
            request_id=request_id,
        )


class ConflictError(OmegaError):
    """Raised when a request conflicts with existing state (409)."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(
            code="CONFLICT",
            message=message,
            details=details,
            retryable=False,
            correlation_id=correlation_id,
            request_id=request_id,
        )


class RateLimitError(OmegaError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after_ms: Optional[int] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        details = {}
        if retry_after_ms:
            details["retry_after_ms"] = retry_after_ms

        super().__init__(
            code="RATE_LIMITED",
            message=message,
            details=details,
            retryable=True,
            correlation_id=correlation_id,
            request_id=request_id,
        )


class UpstreamError(OmegaError):
    """Raised when an upstream service fails (502, 503, 504)."""

    def __init__(
        self,
        message: str,
        upstream_service: Optional[str] = None,
        upstream_status: Optional[int] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        details = {}
        if upstream_service:
            details["upstream_service"] = upstream_service
        if upstream_status:
            details["upstream_status"] = upstream_status

        super().__init__(
            code="UPSTREAM_ERROR",
            message=message,
            details=details,
            retryable=True,
            correlation_id=correlation_id,
            request_id=request_id,
        )


class TimeoutError(OmegaError):
    """Raised when a request times out (408, 504)."""

    def __init__(
        self,
        message: str = "Request timeout",
        timeout_ms: Optional[int] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        details = {}
        if timeout_ms:
            details["timeout_ms"] = timeout_ms

        super().__init__(
            code="TIMEOUT",
            message=message,
            details=details,
            retryable=True,
            correlation_id=correlation_id,
            request_id=request_id,
        )


class InternalError(OmegaError):
    """Raised when an internal server error occurs (500)."""

    def __init__(
        self,
        message: str = "Internal server error",
        details: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(
            code="INTERNAL_ERROR",
            message=message,
            details=details,
            retryable=False,
            correlation_id=correlation_id,
            request_id=request_id,
        )


# HTTP status code to error class mapping
ERROR_MAP: dict[int, type[OmegaError]] = {
    400: ValidationError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    408: TimeoutError,
    409: ConflictError,
    429: RateLimitError,
    500: InternalError,
    502: UpstreamError,
    503: UpstreamError,
    504: TimeoutError,
}


def error_from_response(
    status_code: int,
    error_data: dict[str, Any],
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> OmegaError:
    """
    Create an appropriate error instance from an HTTP response.

    Args:
        status_code: HTTP status code
        error_data: Error data from response envelope
        correlation_id: Correlation ID from response meta
        request_id: Request ID from response meta

    Returns:
        Appropriate OmegaError subclass instance
    """
    error_class = ERROR_MAP.get(status_code, OmegaError)
    code = error_data.get("code", "UNKNOWN_ERROR")
    message = error_data.get("message", f"HTTP {status_code} error")
    details = error_data.get("details", {})
    retryable = error_data.get("retryable", False)

    # Special handling for specific error types
    if error_class == ValidationError:
        return ValidationError(
            message=message,
            field_errors=details.get("field_errors"),
            correlation_id=correlation_id,
            request_id=request_id,
        )
    elif error_class == AuthenticationError:
        return AuthenticationError(
            message=message,
            details=details,
            correlation_id=correlation_id,
            request_id=request_id,
        )
    elif error_class == ForbiddenError:
        return ForbiddenError(
            message=message,
            details=details,
            correlation_id=correlation_id,
            request_id=request_id,
        )
    elif error_class == NotFoundError:
        return NotFoundError(
            message=message,
            resource_type=details.get("resource_type"),
            resource_id=details.get("resource_id"),
            correlation_id=correlation_id,
            request_id=request_id,
        )
    elif error_class == ConflictError:
        return ConflictError(
            message=message,
            details=details,
            correlation_id=correlation_id,
            request_id=request_id,
        )
    elif error_class == RateLimitError:
        return RateLimitError(
            message=message,
            retry_after_ms=details.get("retry_after_ms"),
            correlation_id=correlation_id,
            request_id=request_id,
        )
    elif error_class == UpstreamError:
        return UpstreamError(
            message=message,
            upstream_service=details.get("upstream_service"),
            upstream_status=details.get("upstream_status"),
            correlation_id=correlation_id,
            request_id=request_id,
        )
    elif error_class == TimeoutError:
        return TimeoutError(
            message=message,
            timeout_ms=details.get("timeout_ms"),
            correlation_id=correlation_id,
            request_id=request_id,
        )
    elif error_class == InternalError:
        return InternalError(
            message=message,
            details=details,
            correlation_id=correlation_id,
            request_id=request_id,
        )
    else:
        # Fallback for OmegaError base class
        return OmegaError(
            code=code,
            message=message,
            details=details,
            retryable=retryable,
            correlation_id=correlation_id,
            request_id=request_id,
        )
