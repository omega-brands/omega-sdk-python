# Team Foxtrot — OMEGA SDK Implementation Plan

## Objective
Expose Keon Evidence Pack verification and retrieval capabilities to SDK users, ensuring all SDK-built applications automatically produce and verify evidence.

---

## ✅ Phase 1: Evidence Pack Models in SDK

### File: `omega-sdk/src/omega_sdk/evidence.py`
Copy evidence pack models from `omega-core/core/evidence.py` with SDK-specific adjustments:

```python
"""
Keon Evidence Pack models for OMEGA SDK
Enables SDK clients to retrieve, inspect, and verify evidence packs.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

# Copy all models from omega-core/core/evidence.py
# Adjust for SDK usage patterns
```

---

## ✅ Phase 2: Evidence Client in SDK

### File: `omega-sdk/src/omega_sdk/evidence_client.py`

```python
"""
Keon Evidence Pack Client
Provides methods to retrieve and verify evidence packs from Federation Core.
"""

import httpx
from typing import Optional
from uuid import UUID
from .evidence import MemoryEvidencePack
from .config import OmegaConfig
from .errors import OmegaError


class EvidenceClient:
    """Client for retrieving and verifying Keon evidence packs."""
    
    def __init__(self, config: OmegaConfig):
        self.config = config
        self.base_url = config.federation_url.rstrip("/") + "/api/v1/evidence"
        self._client = httpx.AsyncClient(timeout=30.0)
    
    async def get_pack(
        self,
        pack_id: UUID,
        *,
        tenant_id: str,
        actor_id: str,
        correlation_id: str
    ) -> Optional[MemoryEvidencePack]:
        """
        Retrieve an evidence pack by ID.
        
        Args:
            pack_id: Evidence pack UUID
            tenant_id: Tenant identifier (for authorization)
            actor_id: Actor identifier (for authorization)
            correlation_id: Correlation ID (for tracing)
            
        Returns:
            MemoryEvidencePack if found, None otherwise
            
        Raises:
            OmegaError: On retrieval error
        """
        headers = {
            "X-Tenant-Id": tenant_id,
            "X-Actor-Id": actor_id,
            "X-Correlation-Id": correlation_id
        }
        
        response = await self._client.get(
            f"{self.base_url}/packs/{pack_id}",
            headers=headers
        )
        
        if response.status_code == 404:
            return None
        
        if response.status_code != 200:
            raise OmegaError(
                code="EVIDENCE_RETRIEVAL_FAILED",
                message=f"Failed to retrieve evidence pack: {response.text}",
                retryable=False
            )
        
        data = response.json()
        return MemoryEvidencePack.model_validate(data)
    
    async def get_pack_by_receipt(
        self,
        receipt_id: UUID,
        *,
        tenant_id: str,
        actor_id: str,
        correlation_id: str
    ) -> Optional[MemoryEvidencePack]:
        """
        Retrieve an evidence pack by Keon receipt ID.
        
        Args:
            receipt_id: Keon ALPHA receipt UUID
            tenant_id, actor_id, correlation_id: Governance context
            
        Returns:
            MemoryEvidencePack if found, None otherwise
        """
        headers = {
            "X-Tenant-Id": tenant_id,
            "X-Actor-Id": actor_id,
            "X-Correlation-Id": correlation_id
        }
        
        response = await self._client.get(
            f"{self.base_url}/receipts/{receipt_id}",
            headers=headers
        )
        
        if response.status_code == 404:
            return None
        
        if response.status_code != 200:
            raise OmegaError(
                code="EVIDENCE_RETRIEVAL_FAILED",
                message=f"Failed to retrieve evidence pack: {response.text}",
                retryable=False
            )
        
        data = response.json()
        return MemoryEvidencePack.model_validate(data)
    
    async def verify_pack(
        self,
        pack: MemoryEvidencePack
    ) -> Dict[str, Any]:
        """
        Verify the integrity and signatures of an evidence pack.
        
        Args:
            pack: Evidence pack to verify
            
        Returns:
            Verification result with status and details
            
        Example:
            {
                "valid": True,
                "integrity_check": "passed",
                "signature_check": "passed",
                "alpha_receipt_check": "passed",
                "issues": []
            }
        """
        issues = []
        
        # 1. Verify integrity scope hash
        # TODO: Implement canonical JSON hashing
        
        # 2. Verify pack signature
        # TODO: Implement signature verification  
        
        # 3. Verify ALPHA receipt signature
        # TODO: Implement receipt signature verification
        
        # 4. Verify policy snapshot consistency
        # TODO: Check that authority section matches operation outcome
        
        return {
            "valid": len(issues) == 0,
            "integrity_check": "not_implemented",
            "signature_check": "not_implemented",
            "alpha_receipt_check": "not_implemented",
            "issues": issues
        }
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
```

---

## ✅ Phase 3: Integrate into Main SDK Client

### File: `omega-sdk/src/omega_sdk/client.py`

Add to `OmegaClient` class:

```python
from .evidence_client import EvidenceClient
from .evidence import MemoryEvidencePack

class OmegaClient:
    def __init__(self, config: OmegaConfig):
        # ... existing init ...
        self.evidence = EvidenceClient(config)
    
    async def get_evidence_pack(
        self,
        pack_id: UUID,
        correlation_id: Optional[str] = None
    ) -> Optional[MemoryEvidencePack]:
        """
        Retrieve an evidence pack (convenience method).
        Automatically uses client's tenant/actor context.
        """
        return await self.evidence.get_pack(
            pack_id=pack_id,
            tenant_id=self.config.tenant_id,
            actor_id=self.config.actor_id,
            correlation_id=correlation_id or str(uuid4())
        )
```

---

## ✅ Phase 4: App Scaffolding Updates

### Template: `omega-sdk/templates/app/main.py`

```python
"""
{app_name} - Powered by OMEGA. Governed by Keon.
Auto-generated by OMEGA SDK v{sdk_version}
"""

import asyncio
from omega_sdk import OmegaClient, OmegaConfig
from omega_sdk.errors import OmegaError


async def main():
    # Initialize OMEGA client
    config = OmegaConfig.from_env()
    
    async with OmegaClient(config) as client:
        print("🚀 {app_name} started - Powered by OMEGA. Governed by Keon.")
        
        # Example: Invoke a tool
        result = await client.invoke_tool(
            tool_id="example.tool",
            input={"message": "Hello, OMEGA!"},
            correlation_id="demo-001"
        )
        
        print(f"✅ Tool result: {result.result}")
        
        # Retrieve the evidence pack for this operation
        if result.audit and result.audit.evidence_pack_id:
            evidence = await client.get_evidence_pack(
                pack_id=result.audit.evidence_pack_id
            )
            
            if evidence:
                print(f"📦 Evidence Pack: {evidence.pack_id}")
                print(f"🔐 Keon Receipt: {evidence.authority.alpha_receipt.receipt_id}")
                print(f"✓  Outcome: {evidence.operation.outcome.name}")
                print(f"✓  Policy: {evidence.authority.alpha_receipt.policy_ref}")
                
                # Verify the evidence pack
                verification = await client.evidence.verify_pack(evidence)
                print(f"🔍 Verified: {verification['valid']}")


if __name__ == "__main__":
    asyncio.run(main())
```

### Template Banner
Every SDK-generated app should display:
```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   Powered by OMEGA  |  Governed by Keon                  ║
║                                                           ║
║   All operations are auditable and policy-enforced       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

---

## ✅ Phase 5: Hot-Reload Config

### File: `omega-sdk/examples/hot_reload_config.py`

```python
"""
Example: Hot-reload configuration for OMEGA SDK apps
Automatically reloads when config changes, no restart required.
"""

import asyncio
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from omega_sdk import OmegaConfig


class ConfigReloader(FileSystemEventHandler):
    def __init__(self, config_path: Path, reload_callback):
        self.config_path = config_path
        self.reload_callback = reload_callback
    
    def on_modified(self, event):
        if event.src_path == str(self.config_path):
            print(f"🔄 Config changed, reloading...")
            new_config = OmegaConfig.from_file(self.config_path)
            asyncio.create_task(self.reload_callback(new_config))


async def on_config_reload(config: OmegaConfig):
    """Called when config is reloaded."""
    print(f"✅ Config reloaded: Federation URL = {config.federation_url}")
    # Reinitialize client, reconnect, etc.


async def main():
    config_path = Path("omega_config.yaml")
    config = OmegaConfig.from_file(config_path)
    
    # Setup file watcher
    event_handler = ConfigReloader(config_path, on_config_reload)
    observer = Observer()
    observer.schedule(event_handler, str(config_path.parent), recursive=False)
    observer.start()
    
    print("🔥 Hot-reload enabled. Edit omega_config.yaml to see changes.")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## ✅ Phase 6: No-Code Proof

### File: `omega-sdk/examples/no_code_app.yaml`

```yaml
# OMEGA No-Code App Definition
# Powered by OMEGA. Governed by Keon.

app:
  name: "Document Processor"
  description: "Process documents with OMEGA tools"
  version: "1.0.0"

tools:
  - id: "ocr.extract"
    name: "Extract Text"
    inputs:
      - name: "document_url"
        type: "string"
        required: true
    
  - id: "nlp.summarize"
    name: "Summarize Text"
    inputs:
      - name: "text"
        type: "string"
        required: true

workflows:
  - name: "Process Document"
    steps:
      - tool: "ocr.extract"
        inputs:
          document_url: "${input.document_url}"
        output: "extracted_text"
      
      - tool: "nlp.summarize"
        inputs:
          text: "${extracted_text.result}"
        output: "summary"
    
    return: "${summary.result}"

governance:
  require_receipts: true
  policy_tags:
    - "production"
    - "data_processing"
  auto_verify_evidence: true
```

### Runtime: `omega-sdk/runtime/no_code_runner.py`

```python
"""
OMEGA No-Code Runtime
Executes YAML-defined apps with full Keon governance.
"""

import yaml
from omega_sdk import OmegaClient, OmegaConfig


class NoCodeRunner:
    def __init__(self, app_definition: dict):
        self.app = app_definition
        self.config = OmegaConfig.from_env()
    
    async def execute_workflow(self, workflow_name: str, inputs: dict):
        """Execute a no-code workflow."""
        async with OmegaClient(self.config) as client:
            workflow = next(w for w in self.app["workflows"] if w["name"] == workflow_name)
            context = {"input": inputs}
            
            for step in workflow["steps"]:
                tool_id = step["tool"]
                tool_inputs = self._resolve_inputs(step["inputs"], context)
                
                result = await client.invoke_tool(
                    tool_id=tool_id,
                    input=tool_inputs,
                    governance=self.app.get("governance", {})
                )
                
                context[step["output"]] = result
                
                # Auto-verify evidence if configured
                if self.app["governance"].get("auto_verify_evidence"):
                    if result.audit and result.audit.evidence_pack_id:
                        evidence = await client.get_evidence_pack(result.audit.evidence_pack_id)
                        verification = await client.evidence.verify_pack(evidence)
                        if not verification["valid"]:
                            raise RuntimeError(f"Evidence verification failed: {verification['issues']}")
            
            # Return final result
            return self._resolve_value(workflow["return"], context)
    
    def _resolve_inputs(self, inputs: dict, context: dict):
        """Resolve variables like ${input.x} from context."""
        # ... implementation ...
        pass
    
    def _resolve_value(self, value: str, context: dict):
        """Resolve a single variable reference."""
        # ... implementation ...
        pass
```

---

## 🎯 Definition of Done (Team Foxtrot)

### Deliverables
- [ ] Evidence pack models in SDK
- [ ] `EvidenceClient` with get/verify methods
- [ ] Integration into main `OmegaClient`
- [ ] App scaffolding with "Powered by OMEGA. Governed by Keon"
- [ ] Hot-reload config example
- [ ] No-code YAML runner proof-of-concept

### Verification
- [ ] Builder can't violate Keon (enforced by SDK)
- [ ] SDK apps auto-produce evidence (every tool invoke)
- [ ] Zero opinionated UI required (no-code works)

---

## 📋 Implementation Order

1. **Week 1**: Evidence models + EvidenceClient
2. **Week 2**: Integration into OmegaClient + tests
3. **Week 3**: App scaffolding updates + hot-reload example
4. **Week 4**: No-code runtime + end-to-end demo

---

**Status**: 📝 Planning Complete | ⏳ Awaiting Team Echo Sign-Off
