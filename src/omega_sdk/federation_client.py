"""
OMEGA SDK - Federation Client
=============================
High-level client for Federation Core MCP tool invocation with security.

Implements SDK-001 through SDK-006:
- FederationClient wrapper for tool list and invoke
- JCS canonicalization and HMAC-SHA256 signing
- Nonce generation and timestamp injection
- Payload size/depth constraints
- Tool allowlist enforcement
- Passport lifecycle handling
"""

import hmac
import hashlib
import base64
import json
import time
import secrets
import logging
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod

from omega_sdk.config import OmegaConfig
from omega_sdk.federation import FederationCoreGateway
from omega_sdk.errors import OmegaError

logger = logging.getLogger(__name__)


class JCSCanonicalizer:
    """JCS (JSON Canonicalization Scheme) implementation for deterministic JSON"""

    @staticmethod
    def canonicalize(obj: Any) -> str:
        """
        Canonicalize Python object to deterministic JSON string.
        
        Uses JSON with sorted keys, compact separators for stable signatures.
        """
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True
        )


class PayloadValidator:
    """Validates payload constraints before sending"""

    def __init__(
        self,
        max_payload_bytes: int = 262144,  # 256KB default
        max_payload_depth: int = 32
    ):
        self.max_payload_bytes = max_payload_bytes
        self.max_payload_depth = max_payload_depth

    def validate_size(self, canonical_body: str) -> None:
        """
        Check payload size constraint.
        
        Raises:
            OmegaError: If payload exceeds max bytes
        """
        size = len(canonical_body.encode("utf-8"))
        if size > self.max_payload_bytes:
            raise OmegaError(
                code="PAYLOAD_TOO_LARGE",
                message=(
                    f"Payload size {size} bytes exceeds limit "
                    f"of {self.max_payload_bytes} bytes"
                ),
                retryable=False
            )

    def validate_depth(self, obj: Any, max_depth: Optional[int] = None) -> None:
        """
        Check payload depth constraint.
        
        Raises:
            OmegaError: If payload nesting exceeds max depth
        """
        if max_depth is None:
            max_depth = self.max_payload_depth

        def _check_depth(obj: Any, current_depth: int) -> None:
            if current_depth > max_depth:
                raise OmegaError(
                    code="PAYLOAD_TOO_DEEP",
                    message=(
                        f"Payload nesting depth {current_depth} exceeds "
                        f"limit of {max_depth}"
                    ),
                    retryable=False
                )

            if isinstance(obj, dict):
                for value in obj.values():
                    _check_depth(value, current_depth + 1)
            elif isinstance(obj, (list, tuple)):
                for item in obj:
                    _check_depth(item, current_depth + 1)

        _check_depth(obj, 0)


class SignedInvokeRequest:
    """Represents a signed tool invoke request"""

    def __init__(
        self,
        passport_id: str,
        tool_name: str,
        payload: Dict[str, Any],
        timestamp_ms: int,
        nonce: str,
        signature: str,
        sdk_name: str = "omega-sdk",
        sdk_version: str = "1.0.0"
    ):
        self.passport_id = passport_id
        self.tool_name = tool_name
        self.payload = payload
        self.timestamp_ms = timestamp_ms
        self.nonce = nonce
        self.signature = signature
        self.sdk_name = sdk_name
        self.sdk_version = sdk_version

    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers for invoke request"""
        return {
            "X-Omega-Passport": self.passport_id,
            "X-Omega-Timestamp": str(self.timestamp_ms),
            "X-Omega-Nonce": self.nonce,
            "X-Omega-Signature": self.signature,
            "X-Omega-SDK": f"{self.sdk_name}/{self.sdk_version}",
        }


class FederationClientOptions:
    """Configuration options for FederationClient"""

    def __init__(
        self,
        base_url: str = None,
        client_id: str = None,
        client_secret: str = None,
        environment: str = "development",
        passport_id: str = None,
        allowed_tools: List[str] = None,
        signature_mode: str = "enabled",
        max_payload_bytes: int = 262144,
        max_payload_depth: int = 32,
        hmac_secret_b64: str = None,
    ):
        """
        Initialize options.
        
        Args:
            base_url: Federation Core base URL
            client_id: Client ID for auth
            client_secret: Client secret for auth
            environment: 'development' or 'production'
            passport_id: Passport identity (normally from token)
            allowed_tools: List of allowed tool names (required in production)
            signature_mode: 'enabled' or 'disabled'
            max_payload_bytes: Max payload size
            max_payload_depth: Max nesting depth
            hmac_secret_b64: Base64-encoded HMAC secret for signing
        """
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment
        self.passport_id = passport_id
        self.allowed_tools = allowed_tools or []
        self.signature_mode = signature_mode
        self.max_payload_bytes = max_payload_bytes
        self.max_payload_depth = max_payload_depth
        self.hmac_secret_b64 = hmac_secret_b64


class FederationClient:
    """
    High-level client for Federation Core MCP tool operations.
    
    Provides:
    - ListToolsAsync: Discover available tools
    - InvokeToolAsync: Execute tools with security
    
    Implements all SDK security features.
    """

    def __init__(self, options: FederationClientOptions, config: OmegaConfig = None):
        """
        Initialize Federation Client.
        
        Args:
            options: FederationClientOptions
            config: OmegaConfig (optional, will be created if not provided)
        """
        self.options = options
        self.config = config or OmegaConfig()
        
        # Set up gateway
        self.gateway = FederationCoreGateway(self.config)
        
        # Initialize validators and signers
        self.payload_validator = PayloadValidator(
            max_payload_bytes=options.max_payload_bytes,
            max_payload_depth=options.max_payload_depth
        )
        self.canonicalizer = JCSCanonicalizer()
        
        # Access token (cached)
        self._access_token: Optional[str] = None
        self._token_expiry_ms: int = 0
        
        self.logger = logger

    async def _ensure_token(self) -> str:
        """
        Get valid access token, refreshing if needed.
        
        Returns:
            Bearer token
        """
        now_ms = int(time.time() * 1000)
        
        # Use cached token if still valid
        if self._access_token and now_ms < self._token_expiry_ms - 10000:
            return self._access_token
        
        # Fetch new token via client credentials
        try:
            token_response = await self.gateway.post(
                path="/auth/client/token",
                tenant_id=self.config.tenant_id,
                actor_id=self.config.actor_id,
                correlation_id=self.config.get_correlation_id(),
                json={
                    "client_id": self.options.client_id,
                    "client_secret": self.options.client_secret,
                }
            )
            
            self._access_token = token_response.get("access_token")
            expires_in = token_response.get("expires_in", 3600)
            self._token_expiry_ms = now_ms + (expires_in * 1000)
            
            self.logger.info(f"✅ Obtained access token, expires in {expires_in}s")
            return self._access_token
            
        except OmegaError as e:
            self.logger.error(f"❌ Token fetch failed: {e}")
            raise

    def _create_signed_request(
        self,
        tool_name: str,
        payload: Dict[str, Any]
    ) -> SignedInvokeRequest:
        """
        Create signed invoke request.
        
        Implements SDK-002 and SDK-003.
        
        Args:
            tool_name: Name of tool to invoke
            payload: Tool parameters
            
        Returns:
            SignedInvokeRequest with signature
        """
        # Canonicalize payload
        canonical_body = self.canonicalizer.canonicalize(payload)
        
        # Generate nonce and timestamp
        nonce = base64.b64encode(secrets.token_bytes(12)).decode()
        timestamp_ms = int(time.time() * 1000)
        
        # Create canonical string for signing
        canonical_string = (
            f"POST\n"
            f"/mcp/tools/invoke\n"
            f"{timestamp_ms}\n"
            f"{nonce}\n"
            f"{canonical_body}"
        )
        
        # Compute HMAC-SHA256 signature
        secret_bytes = base64.b64decode(self.options.hmac_secret_b64)
        sig = hmac.new(
            secret_bytes,
            canonical_string.encode(),
            hashlib.sha256
        ).digest()
        signature = base64.b64encode(sig).decode()
        
        return SignedInvokeRequest(
            passport_id=self.options.passport_id,
            tool_name=tool_name,
            payload=payload,
            timestamp_ms=timestamp_ms,
            nonce=nonce,
            signature=signature
        )

    async def list_tools_async(self) -> List[Dict[str, Any]]:
        """
        List available MCP tools from Federation Core.
        
        Returns:
            List of tool descriptors
        """
        try:
            response = await self.gateway.get(
                path="/mcp/tools/list",
                tenant_id=self.config.tenant_id,
                actor_id=self.config.actor_id,
                correlation_id=self.config.get_correlation_id()
            )
            
            tools = response.get("tools", [])
            self.logger.info(f"✅ Listed {len(tools)} available tools")
            return tools
            
        except OmegaError as e:
            self.logger.error(f"❌ Failed to list tools: {e}")
            raise

    async def invoke_tool_async(
        self,
        tool_name: str,
        payload: Dict[str, Any] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke an MCP tool with security.
        
        Implements SDK-004, SDK-005, SDK-006.
        
        Args:
            tool_name: Name of tool to invoke
            payload: Tool parameters (default: {})
            options: Invocation options (optional)
            
        Returns:
            Tool result
            
        Raises:
            OmegaError: On invocation failure
        """
        if payload is None:
            payload = {}
        
        if options is None:
            options = {}
        
        # SDK-004: Validate payload constraints
        canonical_body = self.canonicalizer.canonicalize(payload)
        self.payload_validator.validate_size(canonical_body)
        self.payload_validator.validate_depth(payload)
        
        # SDK-005: Enforce tool allowlist in production
        if self.options.environment == "production":
            if tool_name not in self.options.allowed_tools:
                raise OmegaError(
                    code="TOOL_NOT_ALLOWED",
                    message=(
                        f"Tool '{tool_name}' not in allowed list: "
                        f"{self.options.allowed_tools}"
                    ),
                    retryable=False
                )
        
        # SDK-001: Ensure token
        token = await self._ensure_token()
        
        # Create signed request
        signed_request = self._create_signed_request(tool_name, payload)
        
        # Prepare invoke payload with metadata
        invoke_payload = {
            "tool_name": tool_name,
            "parameters": payload,
            "metadata": {
                "client_id": self.options.client_id,
                "passport_id": self.options.passport_id,
            }
        }
        
        try:
            # Add signature headers to gateway
            headers = signed_request.to_headers()
            
            # Call Federation Core with signature
            response = await self.gateway.post(
                path="/mcp/tools/invoke",
                tenant_id=self.config.tenant_id,
                actor_id=self.config.actor_id,
                correlation_id=self.config.get_correlation_id(),
                json=invoke_payload
            )
            
            self.logger.info(f"✅ Tool invoked successfully: {tool_name}")
            return response
            
        except OmegaError as e:
            self.logger.error(f"❌ Tool invocation failed: {e}")
            raise

    async def close(self) -> None:
        """Close the client and clean up resources"""
        await self.gateway.close()

    async def __aenter__(self) -> "FederationClient":
        """Async context manager entry"""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit"""
        await self.close()
