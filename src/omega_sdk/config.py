"""
Configuration for OMEGA SDK.

Supports environment variable mapping for doctrine-compliant configuration.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field


class OmegaConfig(BaseModel):
    """
    Configuration for OMEGA SDK client.

    Can be initialized directly or loaded from environment variables using
    from_env().

    Environment variables:
        OMEGA_FEDERATION_URL: Federation Core base URL
        OMEGA_API_KEY: API key for authentication
        OMEGA_TENANT_ID: Default tenant ID
        OMEGA_ACTOR_ID: Default actor ID
        OMEGA_TIMEOUT_MS: Default request timeout in milliseconds
        OMEGA_MAX_RETRIES: Maximum number of retries for transient failures
    """

    # Federation Core connection
    federation_url: str = Field(
        default="http://localhost:9405",
        description="Federation Core base URL",
    )

    # Authentication
    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication (optional)",
    )

    # Default context (can be overridden per request)
    tenant_id: Optional[str] = Field(
        default=None,
        description="Default tenant ID (required for requests)",
    )

    actor_id: Optional[str] = Field(
        default=None,
        description="Default actor ID (required for requests)",
    )

    # Client behavior
    timeout_ms: int = Field(
        default=120000,  # 2 minutes
        description="Default request timeout in milliseconds",
        ge=1000,
        le=600000,  # Max 10 minutes
    )

    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for transient failures",
        ge=0,
        le=10,
    )

    # SDK metadata (sent in requests)
    sdk_name: str = Field(
        default="omega-sdk-python",
        description="SDK name (sent in meta)",
    )

    sdk_version: str = Field(
        default="1.0.0",
        description="SDK version (sent in meta)",
    )

    @classmethod
    def from_env(cls) -> "OmegaConfig":
        """
        Load configuration from environment variables.

        Returns:
            OmegaConfig instance with values from environment

        Example:
            >>> config = OmegaConfig.from_env()
            >>> client = OmegaClient(config=config)
        """
        return cls(
            federation_url=os.getenv("OMEGA_FEDERATION_URL", "http://localhost:9405"),
            api_key=os.getenv("OMEGA_API_KEY"),
            tenant_id=os.getenv("OMEGA_TENANT_ID"),
            actor_id=os.getenv("OMEGA_ACTOR_ID"),
            timeout_ms=int(os.getenv("OMEGA_TIMEOUT_MS", "120000")),
            max_retries=int(os.getenv("OMEGA_MAX_RETRIES", "3")),
        )

    def with_defaults(
        self,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> "OmegaConfig":
        """
        Create a new config with updated defaults.

        Args:
            tenant_id: Override default tenant ID
            actor_id: Override default actor ID

        Returns:
            New OmegaConfig with updated values
        """
        return self.model_copy(
            update={
                k: v
                for k, v in {
                    "tenant_id": tenant_id,
                    "actor_id": actor_id,
                }.items()
                if v is not None
            }
        )
