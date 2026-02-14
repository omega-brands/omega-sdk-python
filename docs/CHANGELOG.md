# Changelog

## [v1.0.1] - 2026-02-14
### Added
- `workflows.register(...)` for first-class workflow artifact registration.
- `workflows.resume_run(..., decision, input=...)` contract parity with TS/C# SDKs.
- Workflow registration DTO exports in package root.

### Changed
- Workflow FC error parsing now supports structured `detail.message` payloads.
- Workflow tests expanded for resume input and registration idempotency.

## [v1.0.0] - 2026-01-28
### Added
- Initial public release of Omega SDK.
- Core governance modules.
- Evidence client implementation.
