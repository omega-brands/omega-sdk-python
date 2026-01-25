"""
Example: Spawn an asynchronous task and poll for completion.

This example demonstrates:
- Task creation with routing
- Task polling
- Progress tracking
- Governance configuration
"""

import asyncio
from omega_sdk import OmegaClient
from omega_sdk.models import TaskRouting, TaskGovernance, TaskStatus
from omega_sdk.errors import OmegaError


async def main():
    # Create client from environment
    client = OmegaClient.from_env()

    try:
        # Create an asynchronous task
        print("Creating task...")
        task = await client.tasks.create(
            task_type="workflow.run",
            input={
                "workflow": "brand_campaign",
                "business_idea": "AI fitness app",
                "target_audience": "Millennials",
            },
            routing=TaskRouting(
                strategy="capability",
                capability="branding",
            ),
            governance=TaskGovernance(
                require_receipt=True,
                policy_tags=["prod", "customer_facing"],
            ),
        )

        print(f"✓ Task created: {task.task_id}")
        print(f"  Status: {task.status}")
        print()

        # Poll for completion
        print("Polling for completion...")
        max_polls = 60  # 5 minutes max
        poll_count = 0

        while poll_count < max_polls:
            # Get task status
            status = await client.tasks.get(task.task_id)
            poll_count += 1

            # Print progress
            if status.state and status.state.progress is not None:
                progress_pct = status.state.progress * 100
                print(f"  [{status.status}] {progress_pct:.1f}% - {status.state.current_step or 'processing'}")
            else:
                print(f"  [{status.status}]")

            # Check if done
            if status.status == TaskStatus.COMPLETED:
                print()
                print("✓ Task completed successfully!")
                print()
                print("Result:")
                print(f"  {status.result}")
                print()

                # Access audit metadata
                if status.audit:
                    print("Audit:")
                    if status.audit.keon_receipt_id:
                        print(f"  Keon Receipt: {status.audit.keon_receipt_id}")
                    if status.audit.evidence_pack_id:
                        print(f"  Evidence Pack: {status.audit.evidence_pack_id}")

                break

            elif status.status == TaskStatus.FAILED:
                print()
                print("✗ Task failed")
                if status.result:
                    print(f"Error: {status.result}")
                break

            elif status.status == TaskStatus.CANCELLED:
                print()
                print("Task was cancelled")
                break

            # Wait before next poll
            await asyncio.sleep(5)

        else:
            print()
            print("Timeout: Task did not complete within 5 minutes")

    except OmegaError as e:
        print(f"Error: {e.code} - {e.message}")
        if e.correlation_id:
            print(f"Correlation ID: {e.correlation_id}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
