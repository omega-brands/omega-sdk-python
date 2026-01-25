"""
Federation Core Gateway - HTTP client for Federation Core API.

This module provides the low-level HTTP interface to Federation Core,
handling:
- Request/response envelope serialization
- Correlation ID injection
- Error mapping
- Retry logic
- Structured logging
"""

from typing import Any, Optional
import httpx

from omega_sdk.config import OmegaConfig
from omega_sdk.models import Envelope
from omega_sdk.errors import error_from_response, OmegaError
from omega_sdk.utils.retry import create_retry_decorator
from omega_sdk.utils.correlation import validate_correlation_id


class FederationCoreGateway:
    """
    HTTP client for Federation Core API.

    Handles all HTTP communication with Federation Core, including:
    - Header injection (tenant, actor, correlation, auth)
    - Response envelope unwrapping
    - Error mapping
    - Retry logic for transient failures
    """

    def __init__(self, config: OmegaConfig):
        """
        Initialize the gateway.

        Args:
            config: SDK configuration
        """
        self.config = config
        self.base_url = config.federation_url.rstrip("/") + "/api/v1"

        # Create HTTP client with timeout
        timeout = httpx.Timeout(config.timeout_ms / 1000.0)
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
        )

        # Create retry decorator
        self._retry = create_retry_decorator(max_attempts=config.max_retries)

    async def __aenter__(self) -> "FederationCoreGateway":
        """Async context manager entry."""
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self._client.__aexit__(*args)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    def _build_headers(
        self,
        tenant_id: str,
        actor_id: str,
        correlation_id: str,
        idempotency_key: Optional[str] = None,
        decision_receipt_id: Optional[str] = None,
    ) -> dict[str, str]:
        """
        Build request headers.

        Args:
            tenant_id: Tenant identifier
            actor_id: Actor identifier
            correlation_id: Correlation ID (canonical format)
            idempotency_key: Idempotency key (optional)
            decision_receipt_id: Decision receipt ID (optional)

        Returns:
            Request headers

        Raises:
            CorrelationError: If correlation ID is invalid
        """
        # Validate correlation ID
        validate_correlation_id(correlation_id)

        headers = {
            "X-Tenant-Id": tenant_id,
            "X-Actor-Id": actor_id,
            "X-Correlation-Id": correlation_id,
            "Content-Type": "application/json",
        }

        # Add optional headers
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        if decision_receipt_id:
            headers["X-Decision-Receipt-Id"] = decision_receipt_id

        return headers

    def _unwrap_envelope(self, response: httpx.Response) -> Any:
        """
        Unwrap response envelope and handle errors.

        Args:
            response: HTTP response

        Returns:
            Response data

        Raises:
            OmegaError: If the response indicates an error
        """
        # Parse JSON
        try:
            body = response.json()
        except Exception as e:
            raise OmegaError(
                code="INVALID_RESPONSE",
                message=f"Failed to parse JSON response: {e}",
                retryable=False,
            )

        # Validate envelope structure
        if not isinstance(body, dict):
            raise OmegaError(
                code="INVALID_RESPONSE",
                message="Response is not a JSON object",
                retryable=False,
            )

        # Extract meta
        meta = body.get("meta", {})
        correlation_id = meta.get("correlation_id")
        request_id = meta.get("request_id")

        # Check for success
        if response.status_code >= 400:
            error_data = body.get("error", {})
            if not error_data:
                # Construct error from status code
                error_data = {
                    "code": "HTTP_ERROR",
                    "message": f"HTTP {response.status_code} error",
                    "retryable": response.status_code >= 500,
                }

            raise error_from_response(
                status_code=response.status_code,
                error_data=error_data,
                correlation_id=correlation_id,
                request_id=request_id,
            )

        # Parse envelope
        try:
            envelope = Envelope.model_validate(body)
        except Exception as e:
            raise OmegaError(
                code="INVALID_ENVELOPE",
                message=f"Failed to parse response envelope: {e}",
                retryable=False,
            )

        # Check envelope ok flag
        if not envelope.ok:
            if envelope.error:
                raise error_from_response(
                    status_code=response.status_code,
                    error_data=envelope.error.model_dump(),
                    correlation_id=envelope.meta.correlation_id,
                    request_id=envelope.meta.request_id,
                )
            else:
                raise OmegaError(
                    code="ENVELOPE_ERROR",
                    message="Response envelope indicates failure but no error details provided",
                    retryable=False,
                    correlation_id=envelope.meta.correlation_id,
                    request_id=envelope.meta.request_id,
                )

        return envelope.data

    async def get(
        self,
        path: str,
        tenant_id: str,
        actor_id: str,
        correlation_id: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Send GET request to Federation Core.

        Args:
            path: API path (relative to /api/v1)
            tenant_id: Tenant identifier
            actor_id: Actor identifier
            correlation_id: Correlation ID
            params: Query parameters

        Returns:
            Response data

        Raises:
            OmegaError: On error
        """

        @self._retry
        async def _request() -> Any:
            url = f"{self.base_url}{path}"
            headers = self._build_headers(tenant_id, actor_id, correlation_id)

            response = await self._client.get(url, headers=headers, params=params or {})
            return self._unwrap_envelope(response)

        return await _request()

    async def post(
        self,
        path: str,
        tenant_id: str,
        actor_id: str,
        correlation_id: str,
        json: dict[str, Any],
        idempotency_key: Optional[str] = None,
        decision_receipt_id: Optional[str] = None,
    ) -> Any:
        """
        Send POST request to Federation Core.

        Args:
            path: API path (relative to /api/v1)
            tenant_id: Tenant identifier
            actor_id: Actor identifier
            correlation_id: Correlation ID
            json: Request body
            idempotency_key: Idempotency key (optional)
            decision_receipt_id: Decision receipt ID (optional)

        Returns:
            Response data

        Raises:
            OmegaError: On error
        """

        @self._retry
        async def _request() -> Any:
            url = f"{self.base_url}{path}"
            headers = self._build_headers(
                tenant_id,
                actor_id,
                correlation_id,
                idempotency_key=idempotency_key,
                decision_receipt_id=decision_receipt_id,
            )

            response = await self._client.post(url, headers=headers, json=json)
            return self._unwrap_envelope(response)

        return await _request()
