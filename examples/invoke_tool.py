"""
Example: Invoke a tool synchronously.

This example demonstrates:
- Tool invocation
- Correlation ID management
- Audit metadata access
- Error handling
"""

import asyncio
from omega_sdk import OmegaClient
from omega_sdk.errors import OmegaError, NotFoundError, ValidationError


async def main():
    # Create client with explicit configuration
    client = OmegaClient(
        federation_url="http://localhost:9405",
        tenant_id="acme",
        actor_id="clint",
    )

    try:
        # Get tool details first
        print("Fetching tool schema...")
        tool = await client.tools.get("csv_processor")
        print(f"Tool: {tool.display_name}")
        print(f"Description: {tool.description}")
        print()

        # Invoke the tool
        print("Invoking tool...")
        result = await client.tools.invoke(
            "csv_processor",
            input={
                "file": "data.csv",
                "normalize": True,
                "output_format": "json",
            },
            tags=["example", "test"],
        )

        print(f"✓ Tool invocation successful!")
        print()
        print(f"Result:")
        print(f"  {result.result}")
        print()

        # Access audit metadata
        if result.audit:
            print(f"Audit:")
            print(f"  Event ID: {result.audit.event_id}")
            if result.audit.keon_receipt_id:
                print(f"  Keon Receipt: {result.audit.keon_receipt_id}")
            if result.audit.evidence_pack_id:
                print(f"  Evidence Pack: {result.audit.evidence_pack_id}")

        # Access usage metadata
        if result.usage:
            print()
            print(f"Usage:")
            for key, value in result.usage.items():
                print(f"  {key}: {value}")

    except NotFoundError as e:
        print(f"Tool not found: {e.message}")
        print(f"Correlation ID: {e.correlation_id}")

    except ValidationError as e:
        print(f"Validation error: {e.message}")
        if "field_errors" in e.details:
            print("Field errors:")
            for field_error in e.details["field_errors"]:
                print(f"  - {field_error['field']}: {field_error['reason']}")

    except OmegaError as e:
        print(f"Error: {e.code} - {e.message}")
        if e.retryable:
            print("(This error is retryable)")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
