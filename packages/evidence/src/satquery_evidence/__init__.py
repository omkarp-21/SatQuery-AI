"""satquery_evidence - evidence items, standardized provenance, deterministic verifier.

Depends only on `satquery_core` (allowed by ADR-001). No confidence values here.
"""

__version__ = "0.1.0"

from .models import EvidenceItem, EvidenceStatus, EvidenceType, Provenance, new_evidence_id, scrub
from .semantic_verifier import (
    SemanticStatus,
    SemanticVerificationResult,
    verify_semantic,
)
from .verifier import Check, VerificationResult, VerificationStatus, verify

__all__ = [
    "EvidenceItem",
    "EvidenceType",
    "EvidenceStatus",
    "Provenance",
    "new_evidence_id",
    "scrub",
    "Check",
    "VerificationResult",
    "VerificationStatus",
    "verify",
    "SemanticStatus",
    "SemanticVerificationResult",
    "verify_semantic",
]
