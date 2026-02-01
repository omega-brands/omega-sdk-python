"""
Chaos stub server for OMEGA SDK testing.

Emulates Federation Core with controlled failure scenarios:
- Random 5xx bursts
- 429 throttles
- Delayed responses
- Malformed payloads
"""

import asyncio
import random
from datetime import datetime
from typing import Any
from aiohttp import web
from uuid import uuid4


class ChaosConfig:
    """Configuration for chaos scenarios."""

    def __init__(
        self,
        error_rate: float = 0.1,  # 10% error rate
        slow_rate: float = 0.05,  # 5% slow responses
        malformed_rate: float = 0.02,  # 2% malformed responses
        min_delay_ms: int = 100,
        max_delay_ms: int = 2000,
    ):
        self.error_rate = error_rate
        self.slow_rate = slow_rate
        self.malformed_rate = malformed_rate
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms


class ChaosStubServer:
    """
    Stub Federation Core server with chaos engineering.

    Useful for testing SDK retry logic, error handling, and resilience.
    """

    def __init__(self, config: ChaosConfig = ChaosConfig()):
        self.config = config
        self.app = web.Application()
        self._setup_routes()
        self.request_count = 0
        self.error_count = 0

    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/api/v1/health", self._handle_health)
        self.app.router.add_get("/api/v1/status", self._handle_status)
        self.app.router.add_get("/api/v1/tools", self._handle_list_tools)
        self.app.router.add_get("/api/v1/tools/{tool_id}", self._handle_get_tool)
        self.app.router.add_post("/api/v1/tools/{tool_id}:invoke", self._handle_invoke_tool)
        self.app.router.add_get("/api/v1/agents", self._handle_list_agents)
        self.app.router.add_get("/api/v1/agents/{agent_id}", self._handle_get_agent)
        self.app.router.add_post("/api/v1/tasks", self._handle_create_task)
        self.app.router.add_get("/api/v1/tasks/{task_id}", self._handle_get_task)
        self.app.router.add_get("/api/v1/compliance/evidence-packs", self._handle_list_evidence)
        self.app.router.add_get("/api/v1/compliance/evidence-packs/{pack_hash}", self._handle_get_evidence)
        self.app.router.add_post("/api/v1/compliance/evidence-packs/{pack_hash}:verify", self._handle_verify_evidence)

    async def _inject_chaos(self):
        """Inject chaos behavior before handling request."""
        self.request_count += 1

        # Malformed response
        if random.random() < self.config.malformed_rate:
            return web.Response(
                text="not valid json",
                status=200,
                content_type="application/json",
            )

        # Random errors
        if random.random() < self.config.error_rate:
            self.error_count += 1
            error_status = random.choice([500, 502, 503, 504])
            return self._error_response(
                status=error_status,
                code="CHAOS_INJECTED",
                message=f"Chaos injection: HTTP {error_status}",
                retryable=True,
            )

        # Slow responses
        if random.random() < self.config.slow_rate:
            delay = random.randint(self.config.min_delay_ms, self.config.max_delay_ms) / 1000.0
            await asyncio.sleep(delay)

        return None

    def _envelope(
        self,
        data: Any,
        correlation_id: str,
        ok: bool = True,
        error: Any = None,
    ) -> dict[str, Any]:
        """Create response envelope."""
        return {
            "ok": ok,
            "data": data if ok else None,
            "error": error,
            "meta": {
                "correlation_id": correlation_id,
                "request_id": f"fc_{uuid4().hex[:16]}",
                "ts": datetime.utcnow().isoformat() + "Z",
                "sdk": {"name": "omega-sdk-python", "version": "1.0.0"},
            },
        }

    def _error_response(
        self,
        status: int,
        code: str,
        message: str,
        retryable: bool = False,
        correlation_id: str = "t:test|c:00000000-0000-0000-0000-000000000000",
    ) -> web.Response:
        """Create error response."""
        envelope = self._envelope(
            data=None,
            correlation_id=correlation_id,
            ok=False,
            error={
                "code": code,
                "message": message,
                "details": {},
                "retryable": retryable,
            },
        )
        return web.json_response(envelope, status=status)

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Handle GET /health."""
        # Health endpoint never has chaos (needs to be reliable)
        envelope = self._envelope(
            data={
                "status": "ok",
                "version": "1.0.0-chaos",
                "uptime_s": 12345,
            },
            correlation_id="t:test|c:00000000-0000-0000-0000-000000000000",
        )
        return web.json_response(envelope)

    async def _handle_status(self, request: web.Request) -> web.Response:
        """Handle GET /status."""
        chaos_result = await self._inject_chaos()
        if chaos_result:
            return chaos_result

        correlation_id = request.headers.get("X-Correlation-Id", "t:test|c:00000000-0000-0000-0000-000000000000")

        envelope = self._envelope(
            data={
                "status": "ok",
                "dependencies": {
                    "redis": "ok",
                    "mongo": "ok",
                    "keon_runtime": "ok",
                },
                "build": {
                    "git_sha": "abc123",
                    "built_at": "2026-01-24T00:00:00Z",
                },
            },
            correlation_id=correlation_id,
        )
        return web.json_response(envelope)

    async def _handle_list_tools(self, request: web.Request) -> web.Response:
        """Handle GET /tools."""
        chaos_result = await self._inject_chaos()
        if chaos_result:
            return chaos_result

        correlation_id = request.headers.get("X-Correlation-Id", "t:test|c:00000000-0000-0000-0000-000000000000")

        envelope = self._envelope(
            data={
                "items": [
                    {
                        "tool_id": "csv_processor",
                        "display_name": "CSV Processor",
                        "description": "Parse and normalize CSVs",
                        "agent_id": "genesis_forge",
                        "schema_version": "v1",
                        "input_schema": {},
                        "output_schema": {},
                        "tags": ["data", "csv"],
                        "status": "ready",
                    }
                ],
                "page": {"limit": 50, "next_cursor": None},
            },
            correlation_id=correlation_id,
        )
        return web.json_response(envelope)

    async def _handle_get_tool(self, request: web.Request) -> web.Response:
        """Handle GET /tools/{tool_id}."""
        chaos_result = await self._inject_chaos()
        if chaos_result:
            return chaos_result

        tool_id = request.match_info["tool_id"]
        correlation_id = request.headers.get("X-Correlation-Id", "t:test|c:00000000-0000-0000-0000-000000000000")

        if tool_id == "nonexistent":
            return self._error_response(
                status=404,
                code="NOT_FOUND",
                message=f"Tool not found: {tool_id}",
                correlation_id=correlation_id,
            )

        envelope = self._envelope(
            data={
                "tool_id": tool_id,
                "display_name": "CSV Processor",
                "description": "Parse and normalize CSVs",
                "agent_id": "genesis_forge",
                "schema_version": "v1",
                "input_schema": {},
                "output_schema": {},
                "tags": ["data", "csv"],
                "status": "ready",
            },
            correlation_id=correlation_id,
        )
        return web.json_response(envelope)

    async def _handle_invoke_tool(self, request: web.Request) -> web.Response:
        """Handle POST /tools/{tool_id}:invoke."""
        chaos_result = await self._inject_chaos()
        if chaos_result:
            return chaos_result

        tool_id = request.match_info["tool_id"]
        correlation_id = request.headers.get("X-Correlation-Id", "t:test|c:00000000-0000-0000-0000-000000000000")

        envelope = self._envelope(
            data={
                "tool_id": tool_id,
                "result": {"normalized_rows": 123},
                "usage": {"duration_ms": 842},
                "audit": {
                    "event_id": f"ae_{uuid4().hex[:16]}",
                    "keon_receipt_id": f"kr_{uuid4().hex[:16]}",
                    "evidence_pack_id": None,
                },
            },
            correlation_id=correlation_id,
        )
        return web.json_response(envelope)

    async def _handle_list_agents(self, request: web.Request) -> web.Response:
        """Handle GET /agents."""
        chaos_result = await self._inject_chaos()
        if chaos_result:
            return chaos_result

        correlation_id = request.headers.get("X-Correlation-Id", "t:test|c:00000000-0000-0000-0000-000000000000")

        envelope = self._envelope(
            data={
                "items": [
                    {
                        "agent_id": "gpt_titan",
                        "kind": "titan",
                        "display_name": "GPT Titan",
                        "status": "online",
                        "capabilities": ["routing", "planning"],
                        "endpoints": {"mcp": "http://localhost:8100"},
                        "metadata": {},
                    }
                ],
                "page": {"limit": 50, "next_cursor": None},
            },
            correlation_id=correlation_id,
        )
        return web.json_response(envelope)

    async def _handle_get_agent(self, request: web.Request) -> web.Response:
        """Handle GET /agents/{agent_id}."""
        chaos_result = await self._inject_chaos()
        if chaos_result:
            return chaos_result

        agent_id = request.match_info["agent_id"]
        correlation_id = request.headers.get("X-Correlation-Id", "t:test|c:00000000-0000-0000-0000-000000000000")

        envelope = self._envelope(
            data={
                "agent_id": agent_id,
                "kind": "titan",
                "display_name": "GPT Titan",
                "status": "online",
                "capabilities": ["routing", "planning"],
                "endpoints": {"mcp": "http://localhost:8100"},
                "tools": ["tool_a", "tool_b"],
                "metadata": {},
            },
            correlation_id=correlation_id,
        )
        return web.json_response(envelope)

    async def _handle_create_task(self, request: web.Request) -> web.Response:
        """Handle POST /tasks."""
        chaos_result = await self._inject_chaos()
        if chaos_result:
            return chaos_result

        correlation_id = request.headers.get("X-Correlation-Id", "t:test|c:00000000-0000-0000-0000-000000000000")

        envelope = self._envelope(
            data={
                "task_id": f"tk_{uuid4().hex[:16]}",
                "status": "queued",
                "created_at": datetime.utcnow().isoformat() + "Z",
            },
            correlation_id=correlation_id,
        )
        return web.json_response(envelope, status=202)

    async def _handle_get_task(self, request: web.Request) -> web.Response:
        """Handle GET /tasks/{task_id}."""
        chaos_result = await self._inject_chaos()
        if chaos_result:
            return chaos_result

        task_id = request.match_info["task_id"]
        correlation_id = request.headers.get("X-Correlation-Id", "t:test|c:00000000-0000-0000-0000-000000000000")

        envelope = self._envelope(
            data={
                "task_id": task_id,
                "status": "completed",
                "state": {"current_step": "done", "progress": 1.0},
                "result": {"output": "success"},
                "audit": {
                    "keon_receipt_id": f"kr_{uuid4().hex[:16]}",
                    "evidence_pack_id": None,
                },
            },
            correlation_id=correlation_id,
        )
        return web.json_response(envelope)

    async def _handle_list_evidence(self, request: web.Request) -> web.Response:
        """Handle GET /compliance/evidence-packs."""
        chaos_result = await self._inject_chaos()
        if chaos_result:
            return chaos_result

        correlation_id = request.headers.get("X-Correlation-Id", "t:test|c:00000000-0000-0000-0000-000000000000")

        envelope = self._envelope(
            data={
                "items": [
                    {
                        "PackId": str(uuid4()),
                        "TenantId": "test",
                        "CorrelationId": correlation_id,
                        "Name": "Evidence Pack 1",
                        "CreatedAtUtc": datetime.utcnow().isoformat() + "Z",
                        "ArtifactCount": 12,
                        "Status": "signed",
                    }
                ]
            },
            correlation_id=correlation_id,
        )
        return web.json_response(envelope)

    async def _handle_get_evidence(self, request: web.Request) -> web.Response:
        """Handle GET /compliance/evidence-packs/{pack_hash}."""
        chaos_result = await self._inject_chaos()
        if chaos_result:
            return chaos_result

        pack_hash = request.match_info["pack_hash"]
        correlation_id = request.headers.get("X-Correlation-Id", "t:test|c:00000000-0000-0000-0000-000000000000")

        if pack_hash == "nonexistent":
            return self._error_response(
                status=404,
                code="NOT_FOUND",
                message=f"Evidence pack not found: {pack_hash}",
                correlation_id=correlation_id,
            )

        if pack_hash == "tampered":
            status = "tampered"
        elif pack_hash == "invalid":
            status = "invalid"
        elif pack_hash == "missing":
            status = "blob_missing"
        else:
            status = "signed"

        envelope = self._envelope(
            data={
                "PackId": str(uuid4()),
                "PackVersion": "1.0.0",
                "CanonVersion": "1.0.0",
                "SealedAt": datetime.utcnow().isoformat() + "Z",
                "Status": status,
                "IntegrityScope": {
                    "SignedPayloadHash": "hash123",
                    "HashAlgorithm": "sha256",
                    "IncludedSections": ["Identity", "Operation"],
                    "ExternalReferences": [],
                    "SignatureExclusions": [],
                },
                "Identity": {
                    "EvidenceType": 0,
                    "TenantId": "test",
                    "ActorId": str(uuid4()),
                    "CorrelationId": correlation_id,
                },
                "Operation": {
                    "EvidenceType": 0,
                    "OpType": "tool.invoke",
                    "OpId": str(uuid4()),
                    "RequestedAt": datetime.utcnow().isoformat() + "Z",
                    "Outcome": 0,
                    "OutcomeReason": "Success",
                    "TargetShardKey": "test",
                    "RequestPayloadHash": "reqhash123",
                },
                "Authority": {
                    "EvidenceType": 0,
                    "AlphaReceipt": {
                        "ReceiptId": str(uuid4()),
                        "PolicyRef": "pol-001",
                        "PolicySnapshot": {},
                        "Certified": True,
                        "ReasonCode": "OK",
                        "Obligations": [],
                        "AuditFlags": 0,
                        "IssuedAt": datetime.utcnow().isoformat() + "Z",
                        "ValidFrom": datetime.utcnow().isoformat() + "Z",
                        "ValidUntil": datetime.utcnow().isoformat() + "Z",
                        "ExpiryBehavior": 0,
                        "Signature": "sig123",
                        "Hash": "hash123",
                    },
                },
                "State": {
                    "EvidenceType": 0,
                    "BeforeState": {},
                    "DeltaHash": "deltahash123",
                    "StateSnapshotVersion": "1.0.0",
                },
                "Execution": {
                    "EvidenceType": 0,
                    "RuntimeReceiptId": str(uuid4()),
                    "ResourceConsumption": {
                        "TokensConsumed": 100,
                        "ComputeUnits": 1.5,
                        "BudgetRef": "budget-001",
                    },
                    "ExpiryEnforcement": {
                        "CheckedAt": [datetime.utcnow().isoformat() + "Z"],
                        "ExpiryViolation": False,
                    },
                },
                "Compliance": {
                    "EvidenceType": 0,
                    "RetentionPolicy": "standard",
                    "RetentionExpiry": datetime.utcnow().isoformat() + "Z",
                    "JurisdictionTags": ["US"],
                    "DataClassification": 1,
                    "RedactionApplied": False,
                },
                "Verification": {
                    "SignedPayloadHash": "hash123",
                    "HashAlgorithm": "sha256",
                    "SigningAuthority": "Keon.TrustOps",
                    "PackSignature": "packsig123",
                    "VerificationInstructions": "Verify with Keon public key",
                },
            },
            correlation_id=correlation_id,
        )
        return web.json_response(envelope)

    async def _handle_verify_evidence(self, request: web.Request) -> web.Response:
        """Handle POST /compliance/evidence-packs/{pack_hash}:verify."""
        chaos_result = await self._inject_chaos()
        if chaos_result:
            return chaos_result

        pack_hash = request.match_info["pack_hash"]
        correlation_id = request.headers.get("X-Correlation-Id", "t:test|c:00000000-0000-0000-0000-000000000000")

        is_valid = pack_hash not in ["tampered", "invalid", "missing"]

        envelope = self._envelope(
            data={
                "IsValid": is_valid,
                "Verdict": "PASS" if is_valid else "FAIL",
                "PackHash": pack_hash,
                "Timestamp": datetime.utcnow().isoformat() + "Z",
                "Details": "Verification successful" if is_valid else f"Verification failed for {pack_hash}",
            },
            correlation_id=correlation_id,
        )
        return web.json_response(envelope)

    async def start(self, host: str = "127.0.0.1", port: int = 9999):
        """Start the chaos stub server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        print(f"Chaos stub server running on http://{host}:{port}")
        print(f"Error rate: {self.config.error_rate * 100}%")
        print(f"Slow rate: {self.config.slow_rate * 100}%")
        print(f"Malformed rate: {self.config.malformed_rate * 100}%")

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
        }


async def main():
    """Run chaos stub server standalone."""
    config = ChaosConfig(
        error_rate=0.2,  # 20% errors for testing
        slow_rate=0.1,  # 10% slow
        malformed_rate=0.05,  # 5% malformed
    )
    server = ChaosStubServer(config)
    await server.start()

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\nShutting down...")
        stats = server.get_stats()
        print(f"Final stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
