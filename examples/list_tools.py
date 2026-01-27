"""
Example: List all available tools in Federation Core.

This example demonstrates:
- Environment-based configuration
- Tool listing with pagination
- Error handling
"""

import asyncio

from omega_sdk import OmegaClient
from omega_sdk.errors import OmegaError


async def main():
    # Create client from environment variables
    # Requires: OMEGA_FEDERATION_URL, OMEGA_TENANT_ID, OMEGA_ACTOR_ID
    client = OmegaClient.from_env()

    try:
        # List all tools
        print("Fetching tools from Federation Core...")
        tools = await client.tools.list()

        print(f"\nFound {len(tools.items)} tools:\n")

        for tool in tools.items:
            print(f"  • {tool.tool_id}")
            print(f"    Name: {tool.display_name}")
            print(f"    Description: {tool.description}")
            print(f"    Agent: {tool.agent_id}")
            print(f"    Status: {tool.status}")
            print(f"    Tags: {', '.join(tool.tags or [])}")
            print()

        # Pagination example
        if tools.page.next_cursor:
            print("More results available. Use cursor for pagination:")
            print(f"  next_cursor = '{tools.page.next_cursor}'")

    except OmegaError as e:
        print(f"Error: {e.code} - {e.message}")
        if e.correlation_id:
            print(f"Correlation ID: {e.correlation_id}")
        if e.request_id:
            print(f"Request ID: {e.request_id}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
