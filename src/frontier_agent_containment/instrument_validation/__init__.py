"""Static Instrument Validation runtime-contract validation.

IV-G1 exposes representation and reference-closure checks only.  It does not
provide a runtime executor or instantiate any instrument component.
"""

from .models import (
    EVIDENCE_INGRESS_SCHEMA_ID,
    RUNTIME_PLAN_SCHEMA_ID,
    S0_ACCEPTANCE_SCHEMA_ID,
    IVContractErrorCode,
    IVContractFinding,
    IVContractValidationError,
    IVReferenceCatalog,
    IVSourceRegistration,
    assert_valid_evidence_ingress_envelope,
    assert_valid_runtime_plan,
    assert_valid_s0_runtime_acceptance,
    is_iv_validation_case_id,
    load_and_validate_evidence_ingress_envelope,
    load_and_validate_runtime_plan,
    load_and_validate_s0_runtime_acceptance,
    validate_evidence_ingress_envelope,
    validate_iv_validation_case_inventory,
    validate_runtime_plan,
    validate_s0_acceptance_aggregation,
    validate_s0_runtime_acceptance,
)

__all__ = [
    "EVIDENCE_INGRESS_SCHEMA_ID",
    "RUNTIME_PLAN_SCHEMA_ID",
    "S0_ACCEPTANCE_SCHEMA_ID",
    "IVContractErrorCode",
    "IVContractFinding",
    "IVContractValidationError",
    "IVReferenceCatalog",
    "IVSourceRegistration",
    "assert_valid_evidence_ingress_envelope",
    "assert_valid_runtime_plan",
    "assert_valid_s0_runtime_acceptance",
    "is_iv_validation_case_id",
    "load_and_validate_evidence_ingress_envelope",
    "load_and_validate_runtime_plan",
    "load_and_validate_s0_runtime_acceptance",
    "validate_evidence_ingress_envelope",
    "validate_iv_validation_case_inventory",
    "validate_runtime_plan",
    "validate_s0_acceptance_aggregation",
    "validate_s0_runtime_acceptance",
]
