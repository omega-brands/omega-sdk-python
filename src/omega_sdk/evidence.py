"""
Evidence models for OMEGA SDK.
Mirroring Team Echo's canonical evidence structure (read-only).
"""

from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvidencePackStatus(str, Enum):
    """Canonical status vocabulary for evidence packs."""

    UNSIGNED = "unsigned"
    SIGNED = "signed"
    INVALID = "invalid"
    TAMPERED = "tampered"
    BLOB_MISSING = "blob_missing"


class EvidenceType(IntEnum):
    Observed = 0
    Derived = 1
    Asserted = 2
    Attested = 3


class OperationOutcome(IntEnum):
    Completed = 0
    Denied = 1
    Expired = 2
    Pending = 3
    Aborted = 4


class ExpiryBehavior(IntEnum):
    Abort = 0
    CompleteAndFlag = 1
    MarkInvalid = 2


class BaseEvidenceModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        frozen=True,  # Read-only
    )


class ExternalReference(BaseEvidenceModel):
    ref_type: str = Field(..., alias="RefType")
    ref_id: str = Field(..., alias="RefId")
    ref_hash: str = Field(..., alias="RefHash")


class IntegrityScope(BaseEvidenceModel):
    signed_payload_hash: str = Field(..., alias="SignedPayloadHash")
    hash_algorithm: str = Field(..., alias="HashAlgorithm")
    included_sections: List[str] = Field(..., alias="IncludedSections")
    external_references: List[ExternalReference] = Field(..., alias="ExternalReferences")
    signature_exclusions: List[str] = Field(..., alias="SignatureExclusions")


class IdentitySection(BaseEvidenceModel):
    evidence_type: EvidenceType = Field(..., alias="EvidenceType")
    tenant_id: str = Field(..., alias="TenantId")
    actor_id: str = Field(..., alias="ActorId")
    correlation_id: str = Field(..., alias="CorrelationId")
    session_id: Optional[str] = Field(None, alias="SessionId")


class OperationSection(BaseEvidenceModel):
    evidence_type: EvidenceType = Field(..., alias="EvidenceType")
    op_type: str = Field(..., alias="OpType")
    op_id: str = Field(..., alias="OpId")
    requested_at: datetime = Field(..., alias="RequestedAt")
    completed_at: Optional[datetime] = Field(None, alias="CompletedAt")
    outcome: OperationOutcome = Field(..., alias="Outcome")
    outcome_reason: str = Field(..., alias="OutcomeReason")
    target_shard_key: str = Field(..., alias="TargetShardKey")
    request_payload_hash: str = Field(..., alias="RequestPayloadHash")


class Obligation(BaseEvidenceModel):
    obligation_type: str = Field(..., alias="ObligationType")
    parameters: Dict[str, str] = Field(..., alias="Parameters")


class AlphaReceipt(BaseEvidenceModel):
    receipt_id: str = Field(..., alias="ReceiptId")
    policy_ref: str = Field(..., alias="PolicyRef")
    policy_snapshot: Dict[str, Any] = Field(..., alias="PolicySnapshot")
    certified: bool = Field(..., alias="Certified")
    reason_code: str = Field(..., alias="ReasonCode")
    obligations: List[Obligation] = Field(..., alias="Obligations")
    audit_flags: int = Field(..., alias="AuditFlags")
    issued_at: datetime = Field(..., alias="IssuedAt")
    valid_from: datetime = Field(..., alias="ValidFrom")
    valid_until: datetime = Field(..., alias="ValidUntil")
    expiry_behavior: ExpiryBehavior = Field(..., alias="ExpiryBehavior")
    signature: str = Field(..., alias="Signature")
    hash: str = Field(..., alias="Hash")


class AuthoritySection(BaseEvidenceModel):
    evidence_type: EvidenceType = Field(..., alias="EvidenceType")
    alpha_receipt: AlphaReceipt = Field(..., alias="AlphaReceipt")
    # Escalation chain omitted for brevity if not strictly required by Echo's current SDK needs, 
    # but we'll include it if mirroring exactly.
    # For Phase 4 retrieval, we'll keep it simple but accurate.


class StateSection(BaseEvidenceModel):
    evidence_type: EvidenceType = Field(..., alias="EvidenceType")
    before_state: Dict[str, Any] = Field(..., alias="BeforeState")
    after_state: Optional[Dict[str, Any]] = Field(None, alias="AfterState")
    delta_hash: str = Field(..., alias="DeltaHash")
    state_snapshot_version: str = Field(..., alias="StateSnapshotVersion")


class ComputationInfo(BaseEvidenceModel):
    algorithm_id: str = Field(..., alias="AlgorithmId")
    algorithm_version: str = Field(..., alias="AlgorithmVersion")
    input_fingerprint_hash: str = Field(..., alias="InputFingerprintHash")


class ResourceConsumption(BaseEvidenceModel):
    tokens_consumed: int = Field(..., alias="TokensConsumed")
    compute_units: float = Field(..., alias="ComputeUnits")
    budget_ref: str = Field(..., alias="BudgetRef")


class ExpiryEnforcement(BaseEvidenceModel):
    checked_at: List[datetime] = Field(..., alias="CheckedAt")
    expiry_violation: bool = Field(..., alias="ExpiryViolation")
    expiry_behavior_applied: Optional[ExpiryBehavior] = Field(None, alias="ExpiryBehaviorApplied")


class ExecutionSection(BaseEvidenceModel):
    evidence_type: EvidenceType = Field(..., alias="EvidenceType")
    runtime_receipt_id: str = Field(..., alias="RuntimeReceiptId")
    execution_trace_ref: Optional[str] = Field(None, alias="ExecutionTraceRef")
    resource_consumption: ResourceConsumption = Field(..., alias="ResourceConsumption")
    expiry_enforcement: ExpiryEnforcement = Field(..., alias="ExpiryEnforcement")


class ComplianceSection(BaseEvidenceModel):
    evidence_type: EvidenceType = Field(..., alias="EvidenceType")
    retention_policy: str = Field(..., alias="RetentionPolicy")
    retention_expiry: datetime = Field(..., alias="RetentionExpiry")
    jurisdiction_tags: List[str] = Field(..., alias="JurisdictionTags")
    data_classification: int = Field(..., alias="DataClassification")
    redaction_applied: bool = Field(..., alias="RedactionApplied")


class VerificationSection(BaseEvidenceModel):
    signed_payload_hash: str = Field(..., alias="SignedPayloadHash")
    hash_algorithm: str = Field(..., alias="HashAlgorithm")
    signing_authority: str = Field(..., alias="SigningAuthority")
    pack_signature: str = Field(..., alias="PackSignature")
    verification_instructions: str = Field(..., alias="VerificationInstructions")


class MemoryEvidencePack(BaseEvidenceModel):
    """Full evidence pack in memory."""

    pack_id: str = Field(..., alias="PackId")
    pack_version: str = Field(..., alias="PackVersion")
    canon_version: str = Field(..., alias="CanonVersion")
    sealed_at: datetime = Field(..., alias="SealedAt")
    status: EvidencePackStatus = Field(EvidencePackStatus.SIGNED, alias="Status")
    integrity_scope: IntegrityScope = Field(..., alias="IntegrityScope")
    identity: IdentitySection = Field(..., alias="Identity")
    operation: OperationSection = Field(..., alias="Operation")
    authority: AuthoritySection = Field(..., alias="Authority")
    state: StateSection = Field(..., alias="State")
    execution: ExecutionSection = Field(..., alias="Execution")
    compliance: ComplianceSection = Field(..., alias="Compliance")
    verification: VerificationSection = Field(..., alias="Verification")


class EvidencePackMetadata(BaseEvidenceModel):
    """Summary metadata for an evidence pack."""

    pack_id: str = Field(..., alias="PackId")
    tenant_id: str = Field(..., alias="TenantId")
    correlation_id: str = Field(..., alias="CorrelationId")
    name: str = Field(..., alias="Name")
    created_at_utc: datetime = Field(..., alias="CreatedAtUtc")
    artifact_count: int = Field(..., alias="ArtifactCount")
    status: EvidencePackStatus = Field(..., alias="Status")


class EvidencePackListResponse(BaseModel):
    """Response data for listing evidence packs."""

    items: List[EvidencePackMetadata] = Field(..., description="List of evidence packs")
    # page metadata omitted if not present in Federation Core response for this endpoint


class EvidenceVerificationResult(BaseModel):
    """Factual result of an evidence verification request."""

    is_valid: bool = Field(..., alias="IsValid")
    verdict: str = Field(..., alias="Verdict")
    pack_hash: str = Field(..., alias="PackHash")
    timestamp: datetime = Field(..., alias="Timestamp")
    details: str = Field(..., alias="Details")
