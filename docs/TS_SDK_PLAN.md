# TypeScript SDK Plan

## Status: Not Yet Implemented

This document outlines the plan for a TypeScript/JavaScript SDK that mirrors the Python SDK's architecture and contract discipline.

## Core Principles

### 1. Contract Consumption (No Drift)

The TS SDK **MUST**:
- Consume contracts from the same authority as Python SDK (Team Gemini output)
- Use generated TypeScript types from Federation Core OpenAPI spec
- Never redefine governance logic locally

### 2. Keon Alignment

The TS SDK **MUST**:
- Use the same canonical correlation ID format: `t:<tenant>|c:<uuidv7>`
- Support receipt threading for governed operations
- Provide the same structured error model

### 3. DX Parity

The TS SDK **SHOULD**:
- Match Python SDK's ergonomics where possible
- Support both Node.js and browser environments
- Provide async/await and Promise-based APIs

## Architecture

### Package Structure

```
omega-sdk-ts/
├── src/
│   ├── client.ts              # OmegaClient (main entry)
│   ├── federation.ts          # FederationCoreGateway
│   ├── config.ts              # OmegaConfig
│   ├── errors.ts              # Typed errors
│   ├── models.ts              # Generated types from OpenAPI
│   ├── utils/
│   │   ├── correlation.ts     # Correlation ID helpers
│   │   ├── retry.ts           # Retry policy
│   │   └── validation.ts      # Hard validation
│   └── index.ts               # Public API
├── tests/
│   ├── correlation.test.ts
│   ├── errors.test.ts
│   ├── client.test.ts
│   └── chaos/
│       └── integration.test.ts
├── examples/
│   ├── list-tools.ts
│   ├── invoke-tool.ts
│   └── spawn-task.ts
├── package.json
├── tsconfig.json
└── README.md
```

## API Surface (Target)

### Client Initialization

```typescript
import { OmegaClient } from '@omega/sdk';

// From environment
const client = OmegaClient.fromEnv();

// Explicit config
const client = new OmegaClient({
  federationUrl: 'http://localhost:9405',
  tenantId: 'acme',
  actorId: 'clint',
  apiKey: process.env.OMEGA_API_KEY,
});
```

### Tools API

```typescript
// List tools
const tools = await client.tools.list();

// Get tool
const tool = await client.tools.get('csv_processor');

// Invoke tool
const result = await client.tools.invoke('csv_processor', {
  input: { file: 'data.csv' },
  tags: ['prod'],
});
```

### Agents API

```typescript
// List agents
const agents = await client.agents.list({ kind: 'titan' });

// Get agent
const agent = await client.agents.get('gpt_titan');
```

### Tasks API

```typescript
// Create task
const task = await client.tasks.create({
  taskType: 'workflow.run',
  input: { workflow: 'brand_campaign' },
  routing: {
    strategy: 'capability',
    capability: 'branding',
  },
});

// Get task status
const status = await client.tasks.get(task.taskId);
```

### Correlation IDs

```typescript
import { makeCorrelationId } from '@omega/sdk/utils';

// Auto-generated
const tools = await client.tools.list();

// Explicit
const correlationId = makeCorrelationId('acme');
const tools = await client.tools.list({ correlationId });
```

### Error Handling

```typescript
import { OmegaError, NotFoundError, ValidationError } from '@omega/sdk';

try {
  const result = await client.tools.invoke('nonexistent', { input: {} });
} catch (error) {
  if (error instanceof NotFoundError) {
    console.log(`Tool not found: ${error.message}`);
    console.log(`Correlation: ${error.correlationId}`);
  } else if (error instanceof ValidationError) {
    console.log(`Validation failed: ${error.message}`);
    console.log(error.details.fieldErrors);
  } else if (error instanceof OmegaError) {
    console.log(`Error: ${error.code} - ${error.message}`);
  }
}
```

## Implementation Strategy

### Phase 1: Core Client (4 weeks)

**Deliverables:**
- `OmegaClient` class
- `FederationCoreGateway` (HTTP client)
- Correlation ID helpers (matching Python canonical format)
- Structured error model
- Basic retry logic

**Tests:**
- Correlation validation tests
- Error mapping tests
- Basic integration tests

### Phase 2: Governance Hooks (2 weeks)

**Deliverables:**
- Receipt threading support
- Validation helpers
- Audit metadata models

**Tests:**
- Receipt enforcement tests
- Governance contract tests

### Phase 3: Chaos Testing (2 weeks)

**Deliverables:**
- Chaos stub server (Node.js version)
- Integration tests against chaos server
- Retry/backoff validation

**Tests:**
- Transient failure handling
- Bounded retry verification
- Concurrent request stress tests

### Phase 4: DX Polish (2 weeks)

**Deliverables:**
- Complete documentation
- Working examples (Node.js + browser)
- JSDoc comments
- Type definitions publishing

**Tests:**
- Example scripts verified
- Type checking validation

## Dependencies

### Core Dependencies

```json
{
  "dependencies": {
    "axios": "^1.6.0",
    "uuid": "^9.0.1",
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/uuid": "^9.0.0",
    "typescript": "^5.3.0",
    "vitest": "^1.0.0",
    "eslint": "^8.0.0",
    "prettier": "^3.0.0"
  }
}
```

## Type Generation

**Option A: OpenAPI Generator**

```bash
npx @openapitools/openapi-generator-cli generate \
  -i omega-core/services/federation_core/openapi/federation-core.v1.yaml \
  -g typescript-axios \
  -o src/generated
```

**Option B: Manual Sync**

Maintain manual TypeScript types that exactly mirror Python Pydantic models, with CI checks to detect drift.

**Recommendation:** Option A for v1, with manual overrides as needed.

## Browser Support

The SDK should work in:
- Node.js 18+
- Modern browsers (Chrome, Firefox, Safari, Edge)
- React/Vue/Angular applications
- Next.js (both client and server)

**Browser-specific considerations:**
- Use `fetch` API instead of Node.js HTTP
- Provide separate bundles for Node.js and browser
- Handle CORS appropriately
- Support WebSocket streaming (optional)

## Publishing

```json
{
  "name": "@omega/sdk",
  "version": "1.0.0",
  "main": "./dist/index.js",
  "module": "./dist/index.mjs",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.js",
      "types": "./dist/index.d.ts"
    },
    "./utils": {
      "import": "./dist/utils/index.mjs",
      "require": "./dist/utils/index.js",
      "types": "./dist/utils/index.d.ts"
    }
  }
}
```

## Testing Strategy

### Unit Tests (Vitest)

- Correlation ID validation
- Error mapping
- Config loading
- Retry logic

### Integration Tests

- Against local Federation Core
- Against chaos stub server
- Mock server scenarios

### E2E Tests (Optional)

- Real Federation Core instance
- Full workflow tests
- Performance benchmarks

## Documentation

### Required Docs

- `README.md` - Quick start + examples
- `docs/API.md` - Full API reference
- `docs/CORRELATION.md` - Correlation discipline
- `docs/ERRORS.md` - Error handling guide
- `docs/RECIPES.md` - Common patterns
- `docs/MIGRATION.md` - Python SDK → TS SDK

### JSDoc Coverage

Target: 100% public API coverage with examples.

## Success Criteria

- [ ] TypeScript types generated from Federation Core OpenAPI spec
- [ ] Canonical correlation ID format enforced (`t:<tenant>|c:<uuidv7>`)
- [ ] Structured error model matches Python SDK
- [ ] Retry logic bounded and configurable
- [ ] Works in Node.js and browser
- [ ] >80% test coverage
- [ ] Chaos harness validates resilience
- [ ] Published to npm as `@omega/sdk`
- [ ] Examples run cleanly
- [ ] Docs complete

## Team Assignment

**Primary:** Team Augment (DX focus)

**Support:**
- Team Claude: API surface design
- Team Gemini: Contract generation + validation
- Team Grok: Chaos testing

## Timeline

**Total:** 10 weeks from Python SDK v1.0.0 seal

**Milestones:**
- Week 4: Core client + basic tests
- Week 6: Governance hooks
- Week 8: Chaos testing complete
- Week 10: DX polish + v1.0.0 release
