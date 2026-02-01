#!/usr/bin/env python3
"""
OMEGA SDK: Hello World

The simplest possible OMEGA app demonstrating:
- SDK initialization
- Health check
- Clean shutdown

This is a shell ready for Keon evidence wiring.
"""

import asyncio
from omega_sdk import OmegaClient
from omega_sdk.errors import OmegaError


async def main():
    """Minimal OMEGA app lifecycle."""

    # Initialize client from environment
    # Required env vars: OMEGA_FEDERATION_URL, OMEGA_TENANT_ID, OMEGA_ACTOR_ID
    client = OmegaClient.from_env()

    try:
        # Health check - verifies Federation Core connectivity
        print("Connecting to OMEGA Federation Core...")
        health = await client.health()

        if health.healthy:
            print(f"Hello, OMEGA!")
            print(f"  Federation: {health.federation_version}")
            print(f"  Status: healthy")
            # --------------------------------------------------
            # KEON INTEGRATION SEAM
            # When Keon evidence browser is wired:
            #   - Display verification status here
            #   - Show governance state
            #   - Link to evidence dashboard
            # --------------------------------------------------
        else:
            print(f"Federation unhealthy: {health.message}")

    except OmegaError as e:
        print(f"Connection failed: {e.message}")
        print(f"  Code: {e.code}")
        print(f"  Correlation: {e.correlation_id}")

    finally:
        await client.close()
        print("Goodbye.")


if __name__ == "__main__":
    asyncio.run(main())
