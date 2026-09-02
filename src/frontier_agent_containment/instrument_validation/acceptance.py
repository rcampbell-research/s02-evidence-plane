"""Pure IV-G5 validation-case evaluation and acceptance production.

The functions consume already-governed immutable material.  They neither
observe runtime state nor execute Pilot or Confirmatory work.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Final, Mapping, Sequence

from .models import validate_iv_validation_case_inventory


REPETITIONS_BY_PHASE: Final[Mapping[str, int]] = MappingProxyType(
    {"V0": 2, "V1": 3, "V2": 3, "V3": 3, "V4": 5, "V5": 2}
)
CASES_BY_PHASE: Final[Mapping[str, int]] = MappingProxyType(
    {"V0": 10, "V1": 58, "V2": 22, "V3": 35, "V4": 4, "V5": 7}
)
ACCEPTANCE_RULE_ID: Final = "iv_g5_instrument_acceptance_v0_1"
ACCEPTANCE_RULE_VERSION: Final = "0.1.0"
ACCEPTANCE_VERSION: Final = "0.2.0"
_TYPED_ID = re.compile(r"^[a-z][a-z0-9]*:[a-z0-9][a-z0-9._-]*$")
_SHA256_ID = re.compile(r"^sha256:[0-9a-f]{64}$")


class ValidationResultState(str, Enum):
    VALIDATION_PASS = "VALIDATION_PASS"
    VALIDATION_FAIL = "VALIDATION_FAIL"
    VALIDATION_INCONCLUSIVE = "VALIDATION_INCONCLUSIVE"
    VALIDATION_NOT_APPLICABLE = "VALIDATION_NOT_APPLICABLE"


class ApplicabilityClass(str, Enum):
    MANDATORY_GLOBAL = "MANDATORY_GLOBAL"
    MANDATORY_CONDITIONAL = "MANDATORY_CONDITIONAL"
    OPTIONAL_DIAGNOSTIC = "OPTIONAL_DIAGNOSTIC"


class AcceptanceState(str, Enum):
    ACCEPTED_FOR_PILOT = "ACCEPTED_FOR_PILOT"
    ACCEPTED_FOR_CONFIRMATORY = "ACCEPTED_FOR_CONFIRMATORY"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class RepetitionEvaluationInput:
    validation_case_id: str
    validation_case_version: str
    validation_phase: str
    repetition_id: str
    governing_binding_valid: bool
    authority_usable: bool
    expected_material: tuple[tuple[str, Any], ...]
    observed_material: tuple[tuple[str, Any], ...]
    material_references: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RepetitionResult:
    validation_case_id: str
    validation_case_version: str
    validation_phase: str
    repetition_id: str
    result_state: ValidationResultState
    material_references: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ValidationCaseResult:
    validation_case_id: str
    validation_case_version: str
    validation_phase: str
    applicability_class: ApplicabilityClass
    result_state: ValidationResultState
    evidence_event_ids: tuple[str, ...]
    result_description: str
    not_applicable_reason: str | None = None

    def __post_init__(self) -> None:
        if self.validation_case_version != "0.2.0":
            raise ValueError("validation case version must be 0.2.0")
        if self.validation_phase not in REPETITIONS_BY_PHASE:
            raise ValueError("unknown validation phase")
        if self.result_state is ValidationResultState.VALIDATION_NOT_APPLICABLE:
            if self.applicability_class is ApplicabilityClass.MANDATORY_GLOBAL:
                raise ValueError("mandatory-global case cannot be not applicable")
            if not self.not_applicable_reason:
                raise ValueError("not-applicable result requires a reason")
        elif self.not_applicable_reason is not None:
            raise ValueError("applicable result cannot carry a not-applicable reason")

    def as_contract_mapping(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "validation_case_id": self.validation_case_id,
            "validation_case_version": self.validation_case_version,
            "validation_phase": self.validation_phase,
            "applicability_class": self.applicability_class.value,
            "result_state": self.result_state.value,
            "evidence_event_ids": list(self.evidence_event_ids),
            "result_description": self.result_description,
        }
        if self.not_applicable_reason is not None:
            result["not_applicable_reason"] = self.not_applicable_reason
        return result


@dataclass(frozen=True, slots=True)
class GovernedAcceptanceCase:
    """One exact case entry from the validated execution schedule."""

    validation_case_id: str
    validation_case_version: str
    validation_phase: str
    case_ordinal: int
    required_repetitions: int
    requirement_class: str
    predicate_true: bool
    validation_inventory_digest: str
    schedule_binding: str

    def __post_init__(self) -> None:
        if self.validation_case_version != "0.2.0":
            raise ValueError("governed acceptance case must use Validation Case 0.2.0")
        if self.validation_phase not in REPETITIONS_BY_PHASE:
            raise ValueError("unknown governed validation phase")
        if self.case_ordinal < 1:
            raise ValueError("governed case ordinal must be positive")
        if self.required_repetitions not in {0, REPETITIONS_BY_PHASE[self.validation_phase]}:
            raise ValueError("governed case repetition count is not frozen")
        if self.requirement_class not in {"MG", "MC", "OD"}:
            raise ValueError("requirement class must be MG, MC, or OD")
        if self.requirement_class == "MG" and not self.predicate_true:
            raise ValueError("mandatory-global acceptance case is always applicable")
        expected_repetitions = (
            0
            if self.requirement_class == "MC" and not self.predicate_true
            else REPETITIONS_BY_PHASE[self.validation_phase]
        )
        if self.required_repetitions != expected_repetitions:
            raise ValueError("governed case repetition count is not frozen")
        if not _SHA256_ID.fullmatch(self.validation_inventory_digest):
            raise ValueError("governed case requires the frozen inventory digest")
        if not self.schedule_binding:
            raise ValueError("governed case requires its exact schedule binding")


@dataclass(frozen=True, slots=True)
class AcceptanceCaseMaterial:
    validation_case_id: str
    validation_case_version: str
    validation_phase: str
    case_ordinal: int
    validation_inventory_digest: str
    schedule_binding: str
    result: ValidationCaseResult | None
    requirement_class: str
    predicate_true: bool
    stale: bool = False

    def __post_init__(self) -> None:
        if self.requirement_class not in {"MG", "MC", "OD"}:
            raise ValueError("requirement class must be MG, MC, or OD")
        if self.case_ordinal < 1:
            raise ValueError("acceptance case ordinal must be positive")
        if not _SHA256_ID.fullmatch(self.validation_inventory_digest):
            raise ValueError("acceptance case requires the governed inventory digest")
        if not self.schedule_binding:
            raise ValueError("acceptance case requires its governed schedule binding")


@dataclass(frozen=True, slots=True)
class AcceptanceProductionInput:
    instrument_acceptance_id: str
    instrument_configuration_id: str
    instrument_configuration_version: str
    environment_id: str
    campaign_id: str
    validation_set_id: str
    validation_set_version: str
    target_phase: str
    final_analysis_frozen: bool
    validation_inventory_digest: str
    schedule_binding: str
    governed_cases: tuple[GovernedAcceptanceCase, ...]
    cases: tuple[AcceptanceCaseMaterial, ...]
    component_versions: tuple[tuple[tuple[str, Any], ...], ...]
    authority_id: str
    governing_configuration_valid: bool

    def __post_init__(self) -> None:
        if not _SHA256_ID.fullmatch(self.validation_inventory_digest):
            raise ValueError("acceptance input requires the governed inventory digest")
        if not self.schedule_binding:
            raise ValueError("acceptance input requires the governed schedule binding")


def evaluate_repetition(value: RepetitionEvaluationInput) -> RepetitionResult:
    """Evaluate one repetition without manufacturing material or references."""

    if value.validation_case_version != "0.2.0" or value.validation_phase not in REPETITIONS_BY_PHASE:
        raise ValueError("invalid governed validation-case binding")
    if not value.governing_binding_valid or not value.authority_usable:
        result = ValidationResultState.VALIDATION_INCONCLUSIVE
    elif not value.material_references or not value.observed_material:
        result = ValidationResultState.VALIDATION_INCONCLUSIVE
    elif value.observed_material != value.expected_material:
        result = ValidationResultState.VALIDATION_FAIL
    else:
        result = ValidationResultState.VALIDATION_PASS
    return RepetitionResult(
        validation_case_id=value.validation_case_id,
        validation_case_version=value.validation_case_version,
        validation_phase=value.validation_phase,
        repetition_id=value.repetition_id,
        result_state=result,
        material_references=value.material_references,
    )


def aggregate_case_result(
    *,
    validation_case_id: str,
    validation_case_version: str,
    validation_phase: str,
    applicability_class: ApplicabilityClass,
    applicable: bool,
    not_applicable_reason: str | None,
    repetitions: Sequence[RepetitionResult],
    case_evidence_event_ids: Sequence[str] = (),
) -> ValidationCaseResult:
    """Apply the frozen repetition aggregation precedence for one case."""

    values = tuple(repetitions)
    if not applicable:
        if applicability_class is ApplicabilityClass.MANDATORY_GLOBAL or values or not not_applicable_reason:
            raise ValueError("invalid not-applicable case aggregation")
        return ValidationCaseResult(
            validation_case_id,
            validation_case_version,
            validation_phase,
            applicability_class,
            ValidationResultState.VALIDATION_NOT_APPLICABLE,
            tuple(case_evidence_event_ids),
            "The governed applicability predicate evaluated false.",
            not_applicable_reason,
        )
    ids = tuple(result.repetition_id for result in values)
    bindings_valid = all(
        result.validation_case_id == validation_case_id
        and result.validation_case_version == validation_case_version
        and result.validation_phase == validation_phase
        for result in values
    )
    required_ids = tuple(f"rep_{index:03d}" for index in range(1, REPETITIONS_BY_PHASE[validation_phase] + 1))
    structural_incomplete = (
        ids != required_ids
        or len(ids) != len(set(ids))
        or not bindings_valid
        or any(result.result_state is ValidationResultState.VALIDATION_NOT_APPLICABLE for result in values)
    )
    if any(result.result_state is ValidationResultState.VALIDATION_FAIL for result in values):
        state = ValidationResultState.VALIDATION_FAIL
        description = "At least one governed repetition conclusively failed."
    elif any(result.result_state is ValidationResultState.VALIDATION_INCONCLUSIVE for result in values) or structural_incomplete:
        state = ValidationResultState.VALIDATION_INCONCLUSIVE
        description = "Repetition material is inconclusive or structurally incomplete."
    else:
        state = ValidationResultState.VALIDATION_PASS
        description = "Every required governed repetition conclusively passed."
    references = tuple(dict.fromkeys(reference for result in values for reference in result.material_references))
    if case_evidence_event_ids:
        references = tuple(dict.fromkeys((*references, *case_evidence_event_ids)))
    return ValidationCaseResult(
        validation_case_id,
        validation_case_version,
        validation_phase,
        applicability_class,
        state,
        references,
        description,
    )


def acceptance_inventory_violations(value: AcceptanceProductionInput) -> tuple[str, ...]:
    """Return exact governed-inventory and result-binding violations."""

    errors: list[str] = []
    governed = value.governed_cases
    governed_ids = tuple(item.validation_case_id for item in governed)
    if len(governed) != 136:
        errors.append("governed acceptance inventory must contain exactly 136 cases")
    if validate_iv_validation_case_inventory(governed_ids):
        errors.append("governed acceptance identities are not the frozen IV inventory")
    phase_counts = {phase: 0 for phase in CASES_BY_PHASE}
    governed_keys: list[tuple[str, str, str, int]] = []
    for expected_ordinal, item in enumerate(governed, 1):
        key = (
            item.validation_case_id,
            item.validation_case_version,
            item.validation_phase,
            item.case_ordinal,
        )
        governed_keys.append(key)
        if item.case_ordinal != expected_ordinal:
            errors.append(f"governed case ordinal mismatch at {expected_ordinal}")
        if item.validation_phase in phase_counts:
            phase_counts[item.validation_phase] += 1
        identity_phase = item.validation_case_id.split("-", 2)[1].upper()
        if identity_phase != item.validation_phase:
            errors.append(f"wrong governed phase binding for {item.validation_case_id}")
        if item.required_repetitions not in {
            0,
            REPETITIONS_BY_PHASE.get(item.validation_phase, -1),
        }:
            errors.append(f"governed repetition count mismatch for {item.validation_case_id}")
        if item.validation_inventory_digest != value.validation_inventory_digest:
            errors.append(f"wrong governed inventory binding for {item.validation_case_id}")
        if item.schedule_binding != value.schedule_binding:
            errors.append(f"wrong governed schedule binding for {item.validation_case_id}")
    if len(governed_keys) != len(set(governed_keys)):
        errors.append("governed acceptance inventory contains a duplicate case binding")
    if phase_counts != dict(CASES_BY_PHASE):
        errors.append("governed acceptance phase counts differ from 10/58/22/35/4/7")

    supplied_keys = [
        (
            item.validation_case_id,
            item.validation_case_version,
            item.validation_phase,
            item.case_ordinal,
        )
        for item in value.cases
    ]
    if len(supplied_keys) != len(set(supplied_keys)):
        errors.append("acceptance material contains a duplicate case binding")
    if len(supplied_keys) != len(governed_keys) or set(supplied_keys) != set(governed_keys):
        errors.append("acceptance material does not exactly equal the governed case inventory")
        missing = sorted(set(governed_keys) - set(supplied_keys), key=lambda item: item[3])
        extra = sorted(set(supplied_keys) - set(governed_keys), key=lambda item: item[3])
        errors.extend(f"missing governed case result {item[0]}" for item in missing)
        errors.extend(f"unauthorized extra case result {item[0]}" for item in extra)
    elif supplied_keys != governed_keys:
        errors.append("acceptance material is not in governed case order")

    governed_by_key = {key: item for key, item in zip(governed_keys, governed)}
    for material, key in zip(value.cases, supplied_keys):
        expected = governed_by_key.get(key)
        if material.validation_inventory_digest != value.validation_inventory_digest:
            errors.append(f"wrong inventory binding for {material.validation_case_id}")
        if material.schedule_binding != value.schedule_binding:
            errors.append(f"wrong schedule binding for {material.validation_case_id}")
        if expected is None:
            continue
        if (
            material.requirement_class != expected.requirement_class
            or material.predicate_true is not expected.predicate_true
        ):
            errors.append(f"wrong acceptance requirement binding for {material.validation_case_id}")
        if material.result is not None and (
            material.result.validation_case_id != expected.validation_case_id
            or material.result.validation_case_version != expected.validation_case_version
            or material.result.validation_phase != expected.validation_phase
        ):
            errors.append(f"wrong result binding for {material.validation_case_id}")
        expected_applicability = {
            "MG": ApplicabilityClass.MANDATORY_GLOBAL,
            "MC": ApplicabilityClass.MANDATORY_CONDITIONAL,
            "OD": ApplicabilityClass.OPTIONAL_DIAGNOSTIC,
        }[expected.requirement_class]
        if material.result is not None and material.result.applicability_class is not expected_applicability:
            errors.append(f"wrong result applicability binding for {material.validation_case_id}")
    return tuple(errors)


def decide_acceptance(value: AcceptanceProductionInput) -> AcceptanceState:
    """Apply the frozen mandatory/conditional/diagnostic decision kernel."""

    mandatory_invalid = bool(acceptance_inventory_violations(value)) or not value.governing_configuration_valid
    for item in value.cases:
        if item.requirement_class == "OD":
            continue
        if item.result is None or item.stale:
            mandatory_invalid = True
            continue
        result = item.result.result_state
        if item.requirement_class == "MG":
            mandatory_invalid |= result is not ValidationResultState.VALIDATION_PASS
        elif item.predicate_true:
            mandatory_invalid |= result is not ValidationResultState.VALIDATION_PASS
        else:
            mandatory_invalid |= result is not ValidationResultState.VALIDATION_NOT_APPLICABLE
    if mandatory_invalid:
        return AcceptanceState.REJECTED
    if value.target_phase == "PILOT":
        return AcceptanceState.ACCEPTED_FOR_PILOT
    if value.target_phase == "CONFIRMATORY" and value.final_analysis_frozen:
        return AcceptanceState.ACCEPTED_FOR_CONFIRMATORY
    return AcceptanceState.REJECTED


def produce_instrument_acceptance(value: AcceptanceProductionInput) -> dict[str, Any]:
    """Construct one inert Instrument Acceptance 0.2.0 candidate."""

    if not _TYPED_ID.fullmatch(value.instrument_acceptance_id) or not value.instrument_acceptance_id.startswith("acceptance:"):
        raise ValueError("invalid opaque Instrument Acceptance ID")
    if value.target_phase not in {"PILOT", "CONFIRMATORY"}:
        raise ValueError("target phase must be PILOT or CONFIRMATORY")
    state = decide_acceptance(value)
    unresolved: list[str] = list(acceptance_inventory_violations(value))
    results: list[dict[str, Any]] = []
    for index, item in enumerate(value.cases):
        if item.result is None:
            unresolved.append(
                f"Missing validation-case result: {item.validation_case_id} "
                f"at governed position {item.case_ordinal}."
            )
        else:
            results.append(item.result.as_contract_mapping())
            if item.stale:
                unresolved.append(f"Stale validation-case result: {item.result.validation_case_id}.")
    if not value.governing_configuration_valid:
        unresolved.append("Governing acceptance configuration is invalid.")
    if state is AcceptanceState.REJECTED and not unresolved:
        unresolved.append("At least one mandatory acceptance condition did not pass.")
    candidate: dict[str, Any] = {
        "acceptance_version": ACCEPTANCE_VERSION,
        "instrument_acceptance_id": value.instrument_acceptance_id,
        "instrument_configuration_id": value.instrument_configuration_id,
        "instrument_configuration_version": value.instrument_configuration_version,
        "environment_id": value.environment_id,
        "campaign_id": value.campaign_id,
        "validation_set_id": value.validation_set_id,
        "validation_set_version": value.validation_set_version,
        "acceptance_state": state.value,
        "validation_results": results,
        "component_versions": [dict(component) for component in value.component_versions],
        "acceptance_basis": "Frozen IV-G5 mandatory/conditional case aggregation with optional diagnostics retained.",
        "acceptance_order": 1,
        "acceptance_authority": {
            "authority_id": value.authority_id,
            "authority_role": "INSTRUMENT_ACCEPTANCE_AUTHORITY",
        },
        "acceptance_decision_rule_id": ACCEPTANCE_RULE_ID,
        "acceptance_decision_rule_version": ACCEPTANCE_RULE_VERSION,
        "unresolved_conditions": unresolved,
    }
    if state is AcceptanceState.ACCEPTED_FOR_PILOT:
        candidate["accepted_for_phase"] = "PILOT"
    elif state is AcceptanceState.ACCEPTED_FOR_CONFIRMATORY:
        candidate["accepted_for_phase"] = "CONFIRMATORY"
    return copy.deepcopy(candidate)
