"""Identity-3 exact Instrument Acceptance 0.2.0 reference regressions."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from frontier_agent_containment.schema_validation import load_schema_store
from frontier_agent_containment.semantic_validation import (
    SemanticErrorCode,
    validate_artifact_set,
)
from tests.semantic.test_stage10_confirmatory_gating import gating_artifact_set


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_ID = "acceptance:example-001"
REFERENCE_PATH = "/instrument_acceptance_reference"
REFERENCE_MESSAGE = (
    "instrument_acceptance reference 'acceptance:missing' does not resolve "
    "exactly once in the active artifact set"
)
_ABSENT = object()


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(sorted((ROOT / "schemas").glob("*.schema.json")))


def _validate(
    artifacts: dict[str, list[dict[str, Any]]], schema_store: dict[str, Any]
) -> tuple[Any, ...]:
    return validate_artifact_set(artifacts, schema_store=schema_store)


def _prospective_set(
    *,
    phase: str = "CONFIRMATORY",
    reference: str | object = REFERENCE_ID,
) -> dict[str, list[dict[str, Any]]]:
    artifacts = gating_artifact_set(phase)
    acceptance = artifacts["instrument_acceptance"][0]
    acceptance["acceptance_version"] = "0.2.0"
    acceptance["instrument_acceptance_id"] = REFERENCE_ID
    campaign = artifacts["campaign"][0]
    if reference is _ABSENT:
        campaign.pop("instrument_acceptance_reference", None)
    else:
        assert isinstance(reference, str)
        campaign["instrument_acceptance_reference"] = reference
    return artifacts


def _historical_acceptance(phase: str = "CONFIRMATORY") -> dict[str, Any]:
    return copy.deepcopy(gating_artifact_set(phase)["instrument_acceptance"][0])


def _add_second_prospective(
    artifacts: dict[str, list[dict[str, Any]]],
    *,
    identity: str = "acceptance:example-002",
) -> dict[str, Any]:
    second = copy.deepcopy(artifacts["instrument_acceptance"][0])
    second["instrument_acceptance_id"] = identity
    artifacts["instrument_acceptance"].append(second)
    return second


def _reference_findings(findings: tuple[Any, ...]) -> list[Any]:
    return [
        finding
        for finding in findings
        if finding.artifact_family == "campaign"
        and finding.field_path == REFERENCE_PATH
    ]


def _assert_single_reference_finding(
    findings: tuple[Any, ...],
    code: SemanticErrorCode,
) -> Any:
    reference_findings = _reference_findings(findings)
    assert len(reference_findings) == 1, findings
    assert reference_findings[0].code == code
    return reference_findings[0]


def test_valid_historical_campaign_is_unchanged(
    schema_store: dict[str, Any],
) -> None:
    assert _validate(gating_artifact_set(), schema_store) == ()


def test_historical_zero_compatible_candidates_is_unchanged(
    schema_store: dict[str, Any],
) -> None:
    artifacts = gating_artifact_set()
    artifacts["instrument_acceptance"] = []
    finding = _assert_single_reference_finding(
        _validate(artifacts, schema_store),
        SemanticErrorCode.ACCEPTANCE_INVALID,
    )
    assert finding.message.endswith("found 0")


def test_historical_multiple_compatible_candidates_is_unchanged(
    schema_store: dict[str, Any],
) -> None:
    artifacts = gating_artifact_set()
    artifacts["instrument_acceptance"].append(
        copy.deepcopy(artifacts["instrument_acceptance"][0])
    )
    finding = _assert_single_reference_finding(
        _validate(artifacts, schema_store),
        SemanticErrorCode.ACCEPTANCE_INVALID,
    )
    assert finding.message.endswith("found 2")


def test_historical_reference_remains_opaque(
    schema_store: dict[str, Any],
) -> None:
    artifacts = gating_artifact_set()
    artifacts["campaign"][0]["instrument_acceptance_reference"] = (
        "acceptance:opaque-reference"
    )
    assert _validate(artifacts, schema_store) == ()


def test_exact_valid_prospective_reference_resolves(
    schema_store: dict[str, Any],
) -> None:
    findings = _validate(_prospective_set(), schema_store)
    assert findings == ()
    assert not any(
        finding.code
        in {
            SemanticErrorCode.PROVENANCE_UNRESOLVED,
            SemanticErrorCode.REFERENCE_INVALID,
        }
        for finding in findings
    )


def test_multiple_compatible_prospective_acceptances_resolve_exact_target(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set()
    _add_second_prospective(artifacts)
    assert _validate(artifacts, schema_store) == ()


def test_nonexistent_prospective_reference_is_invalid(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set(reference="acceptance:missing")
    findings = _validate(artifacts, schema_store)
    finding = _assert_single_reference_finding(
        findings,
        SemanticErrorCode.REFERENCE_INVALID,
    )
    assert finding.message == REFERENCE_MESSAGE
    assert finding.referenced_artifact_family == "instrument_acceptance"
    assert finding.referenced_artifact_id == "acceptance:missing"
    assert not any(
        item.code == SemanticErrorCode.PROVENANCE_UNRESOLVED for item in findings
    )


def test_duplicated_referenced_identity_fails_without_selection(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set()
    _add_second_prospective(artifacts, identity=REFERENCE_ID)
    findings = _validate(artifacts, schema_store)
    _assert_single_reference_finding(findings, SemanticErrorCode.REFERENCE_INVALID)
    duplicates = [
        finding
        for finding in findings
        if finding.code == SemanticErrorCode.DUPLICATE_IDENTITY
        and finding.artifact_family == "instrument_acceptance"
    ]
    assert len(duplicates) == 1
    assert duplicates[0].field_path == "/instrument_acceptance_id"
    assert not any(
        finding.code == SemanticErrorCode.ACCEPTANCE_INVALID
        and finding.artifact_family == "campaign"
        for finding in findings
    )


def _make_target_incompatible(
    artifacts: dict[str, list[dict[str, Any]]],
    field: str,
) -> None:
    acceptance = artifacts["instrument_acceptance"][0]
    if field == "campaign_id":
        acceptance[field] = "campaign:other"
        return
    if field == "instrument_configuration_id":
        other = copy.deepcopy(artifacts["instrument_configuration"][0])
        other[field] = "instrument:other"
        artifacts["instrument_configuration"].append(other)
        acceptance[field] = "instrument:other"
        return
    if field == "environment_id":
        other_environment = copy.deepcopy(artifacts["environment"][0])
        other_environment[field] = "env:other"
        artifacts["environment"].append(other_environment)
        artifacts["instrument_configuration"][0][field] = "env:other"
        acceptance[field] = "env:other"
        return
    raise AssertionError(field)


@pytest.mark.parametrize(
    "field",
    ["campaign_id", "instrument_configuration_id", "environment_id"],
)
def test_exact_target_incompatibility_preserves_resolved_identity(
    field: str,
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set()
    _make_target_incompatible(artifacts, field)
    findings = _validate(artifacts, schema_store)
    finding = _assert_single_reference_finding(
        findings,
        SemanticErrorCode.ACCEPTANCE_INVALID,
    )
    assert finding.referenced_artifact_id == REFERENCE_ID
    assert not any(
        item.code == SemanticErrorCode.REFERENCE_INVALID
        and item.artifact_family == "campaign"
        and item.field_path == REFERENCE_PATH
        for item in findings
    )


@pytest.mark.parametrize("eligibility", ["state", "phase"])
def test_exact_target_ineligibility_remains_acceptance_invalid(
    eligibility: str,
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set()
    acceptance = artifacts["instrument_acceptance"][0]
    if eligibility == "state":
        acceptance["acceptance_state"] = "REJECTED"
        acceptance.pop("accepted_for_phase")
        acceptance["unresolved_conditions"] = ["Synthetic rejection."]
    else:
        acceptance["acceptance_state"] = "ACCEPTED_FOR_PILOT"
        acceptance["accepted_for_phase"] = "PILOT"
    findings = _validate(artifacts, schema_store)
    finding = _assert_single_reference_finding(
        findings,
        SemanticErrorCode.ACCEPTANCE_INVALID,
    )
    assert finding.referenced_artifact_id == REFERENCE_ID
    assert not any(
        item.code == SemanticErrorCode.REFERENCE_INVALID
        and item.artifact_family == "campaign"
        and item.field_path == REFERENCE_PATH
        for item in findings
    )


def test_resolved_target_scientific_defect_does_not_unresolve_identity(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set()
    artifacts["instrument_acceptance"][0]["component_versions"][0][
        "component_version"
    ] = "0.2.0"
    findings = _validate(artifacts, schema_store)
    assert any(
        finding.code == SemanticErrorCode.VERSION_INVALID
        and finding.artifact_family == "instrument_acceptance"
        for finding in findings
    )
    assert _reference_findings(findings) == []


def test_mixed_graph_exact_prospective_target_governs(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set()
    artifacts["instrument_acceptance"].append(_historical_acceptance())
    assert _validate(artifacts, schema_store) == ()


def test_mixed_graph_linked_prospective_without_target_has_no_fallback(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set(reference="acceptance:missing")
    artifacts["instrument_acceptance"].append(_historical_acceptance())
    findings = _validate(artifacts, schema_store)
    _assert_single_reference_finding(findings, SemanticErrorCode.REFERENCE_INVALID)
    assert not any(
        finding.code == SemanticErrorCode.ACCEPTANCE_INVALID
        and finding.artifact_family == "campaign"
        for finding in findings
    )


def test_mixed_graph_opaque_reference_still_selects_prospective_mode(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set(reference="acceptance:opaque-reference")
    artifacts["instrument_acceptance"].append(_historical_acceptance())
    _assert_single_reference_finding(
        _validate(artifacts, schema_store),
        SemanticErrorCode.REFERENCE_INVALID,
    )


def test_unrelated_prospective_acceptance_preserves_historical_mode(
    schema_store: dict[str, Any],
) -> None:
    artifacts = gating_artifact_set()
    unrelated = copy.deepcopy(artifacts["instrument_acceptance"][0])
    unrelated["acceptance_version"] = "0.2.0"
    unrelated["instrument_acceptance_id"] = "acceptance:unrelated"
    unrelated["campaign_id"] = "campaign:other"
    artifacts["instrument_acceptance"].append(unrelated)
    assert _validate(artifacts, schema_store) == ()


def test_cross_campaign_exact_target_does_not_fall_back(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set()
    artifacts["instrument_acceptance"][0]["campaign_id"] = "campaign:other"
    artifacts["instrument_acceptance"].append(_historical_acceptance())
    finding = _assert_single_reference_finding(
        _validate(artifacts, schema_store),
        SemanticErrorCode.ACCEPTANCE_INVALID,
    )
    assert finding.referenced_artifact_id == REFERENCE_ID


def test_pilot_optional_reference_absence_adds_no_identity3_finding(
    schema_store: dict[str, Any],
) -> None:
    assert _validate(
        _prospective_set(phase="PILOT", reference=_ABSENT),
        schema_store,
    ) == ()


def test_pilot_present_valid_reference_resolves(
    schema_store: dict[str, Any],
) -> None:
    assert _validate(_prospective_set(phase="PILOT"), schema_store) == ()


def test_pilot_present_invalid_reference_fails_exactly(
    schema_store: dict[str, Any],
) -> None:
    findings = _validate(
        _prospective_set(phase="PILOT", reference="acceptance:missing"),
        schema_store,
    )
    _assert_single_reference_finding(findings, SemanticErrorCode.REFERENCE_INVALID)


def test_malformed_campaign_reference_fails_structurally(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set(reference="not-an-acceptance")
    findings = _validate(artifacts, schema_store)
    assert any(
        finding.code == SemanticErrorCode.SCHEMA_INVALID
        and finding.artifact_family == "campaign"
        and finding.field_path == REFERENCE_PATH
        for finding in findings
    )


def test_malformed_acceptance_identity_fails_structurally(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set()
    artifacts["instrument_acceptance"][0]["instrument_acceptance_id"] = "invalid"
    findings = _validate(artifacts, schema_store)
    assert any(
        finding.code == SemanticErrorCode.SCHEMA_INVALID
        and finding.artifact_family == "instrument_acceptance"
        and finding.field_path == "/instrument_acceptance_id"
        for finding in findings
    )


@pytest.mark.parametrize("eligibility", ["state", "phase"])
def test_linked_prospective_mode_selection_ignores_eligibility(
    eligibility: str,
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set(reference="acceptance:missing")
    acceptance = artifacts["instrument_acceptance"][0]
    if eligibility == "state":
        acceptance["acceptance_state"] = "REJECTED"
        acceptance.pop("accepted_for_phase")
        acceptance["unresolved_conditions"] = ["Synthetic rejection."]
    else:
        acceptance["acceptance_state"] = "ACCEPTED_FOR_PILOT"
        acceptance["accepted_for_phase"] = "PILOT"
    findings = _validate(artifacts, schema_store)
    _assert_single_reference_finding(findings, SemanticErrorCode.REFERENCE_INVALID)
    assert not any(
        finding.code == SemanticErrorCode.ACCEPTANCE_INVALID
        and finding.artifact_family == "campaign"
        for finding in findings
    )


def _determinism_case(kind: str) -> dict[str, list[dict[str, Any]]]:
    if kind == "success":
        return _prospective_set()
    if kind == "no_match":
        return _prospective_set(reference="acceptance:missing")
    if kind == "mixed":
        artifacts = _prospective_set(reference="acceptance:missing")
        artifacts["instrument_acceptance"].append(_historical_acceptance())
        return artifacts
    if kind == "duplicate":
        artifacts = _prospective_set()
        _add_second_prospective(artifacts, identity=REFERENCE_ID)
        return artifacts
    raise AssertionError(kind)


@pytest.mark.parametrize("kind", ["success", "no_match", "mixed", "duplicate"])
def test_identity3_findings_are_deterministic(
    kind: str,
    schema_store: dict[str, Any],
) -> None:
    artifacts = _determinism_case(kind)
    first = _validate(artifacts, schema_store)
    for _ in range(4):
        assert _validate(artifacts, schema_store) == first


@pytest.mark.parametrize("kind", ["success", "no_match", "duplicate"])
def test_candidate_order_does_not_change_resolution(
    kind: str,
    schema_store: dict[str, Any],
) -> None:
    artifacts = _determinism_case(kind)
    if kind != "duplicate":
        _add_second_prospective(artifacts)
        artifacts["instrument_acceptance"].append(_historical_acceptance())
    expected = _validate(artifacts, schema_store)
    permuted = copy.deepcopy(artifacts)
    permuted["instrument_acceptance"].reverse()
    assert _validate(permuted, schema_store) == expected


def test_identity3_validation_does_not_mutate_inputs(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_set(reference="acceptance:missing")
    _add_second_prospective(artifacts)
    artifacts["instrument_acceptance"].append(_historical_acceptance())
    original = copy.deepcopy(artifacts)
    _validate(artifacts, schema_store)
    assert artifacts == original
