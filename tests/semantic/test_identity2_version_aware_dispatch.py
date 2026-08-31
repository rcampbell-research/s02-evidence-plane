"""Identity-2 exact family/version registry and dispatch regressions."""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from frontier_agent_containment.schema_validation import load_schema_store
from frontier_agent_containment.semantic_validation import (
    ARTIFACT_FAMILY_CONTRACT_SPECS,
    SUPPORTED_ARTIFACT_FAMILIES,
    ArtifactFamilyContractSpec,
    ArtifactFamilySpec,
    SemanticErrorCode,
    _build_artifact_family_contract_specs,
    get_artifact_family_contract_spec,
    get_artifact_family_spec,
    validate_artifact_set,
)
from tests.semantic.test_stage10_confirmatory_gating import gating_artifact_set
from tests.semantic.test_stage11_postrun_evidence_closure import postrun_set


ROOT = Path(__file__).resolve().parents[2]
TRANSITION_MESSAGE = (
    "Instrument Acceptance 0.2.0 exact reference resolution is deferred to "
    "Identity-3."
)
IDENTITY_INTRODUCING_DUAL_VERSION_METADATA = {
    "instrument_acceptance": (
        "instrument-acceptance",
        "acceptance_version",
        "instrument_acceptance_id",
    ),
    "derived_action_outcome": (
        "derived-action-outcome",
        "outcome_version",
        "derived_action_outcome_id",
    ),
    "derived_run_outcome": (
        "derived-run-outcome",
        "outcome_version",
        "derived_run_outcome_id",
    ),
}
IDENTITY_PRESERVING_DUAL_VERSION_METADATA = {
    "evidence_event": (
        "evidence-event",
        "event_version",
        "event_id",
    ),
    "validation_case": (
        "validation-case",
        "validation_case_version",
        "validation_case_id",
    ),
}
DUAL_VERSION_METADATA = {
    **IDENTITY_INTRODUCING_DUAL_VERSION_METADATA,
    **IDENTITY_PRESERVING_DUAL_VERSION_METADATA,
}


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(sorted((ROOT / "schemas").glob("*.schema.json")))


def _validate(
    artifacts: dict[str, list[dict[str, Any]]], schema_store: dict[str, Any]
) -> tuple[Any, ...]:
    return validate_artifact_set(artifacts, schema_store=schema_store)


def _prospective_gating_set(
    *, reference: str = "acceptance:example-001"
) -> dict[str, list[dict[str, Any]]]:
    artifacts = gating_artifact_set()
    acceptance = artifacts["instrument_acceptance"][0]
    acceptance["acceptance_version"] = "0.2.0"
    acceptance["instrument_acceptance_id"] = "acceptance:example-001"
    artifacts["campaign"][0]["instrument_acceptance_reference"] = reference
    return artifacts


def _standalone_prospective_acceptance() -> dict[str, list[dict[str, Any]]]:
    artifacts = _prospective_gating_set()
    artifacts["campaign"] = []
    artifacts["scheduled_run"] = []
    artifacts["capability_evaluation"] = []
    artifacts["analysis_manifest"] = []
    return artifacts


def _prospective_postrun_set() -> dict[str, list[dict[str, Any]]]:
    artifacts = postrun_set()
    action = artifacts["derived_action_outcome"][0]
    action["outcome_version"] = "0.2.0"
    action["derived_action_outcome_id"] = "actionoutcome:example-001"
    run = artifacts["derived_run_outcome"][0]
    run["outcome_version"] = "0.2.0"
    run["derived_run_outcome_id"] = "runoutcome:example-001"
    return artifacts


def _contract_spec(
    family: str = "example",
    artifact_version: str = "0.1.0",
    *,
    schema_version: str | None = None,
    version_field: str = "example_version",
) -> ArtifactFamilyContractSpec:
    return ArtifactFamilyContractSpec(
        family=family,
        artifact_version=artifact_version,
        schema_id=(
            "urn:frontier-agent-containment:schema:example:"
            f"{schema_version or artifact_version}"
        ),
        identity_field="example_id",
        version_field=version_field,
    )


def _transition_findings(findings: tuple[Any, ...]) -> list[Any]:
    return [
        finding
        for finding in findings
        if finding.code == SemanticErrorCode.PROVENANCE_UNRESOLVED
        and finding.artifact_family == "campaign"
        and finding.field_path == "/instrument_acceptance_reference"
    ]


def test_authoritative_registry_counts_and_family_versions_are_exact() -> None:
    assert len(SUPPORTED_ARTIFACT_FAMILIES) == 21
    assert len(ARTIFACT_FAMILY_CONTRACT_SPECS) == 26
    assert sum(key[1] == "0.1.0" for key in ARTIFACT_FAMILY_CONTRACT_SPECS) == 21
    assert sum(key[1] == "0.2.0" for key in ARTIFACT_FAMILY_CONTRACT_SPECS) == 5
    versions_by_family: dict[str, set[str]] = {}
    for family, artifact_version in ARTIFACT_FAMILY_CONTRACT_SPECS:
        versions_by_family.setdefault(family, set()).add(artifact_version)
    assert {
        family for family, versions in versions_by_family.items() if len(versions) == 2
    } == set(DUAL_VERSION_METADATA)


@pytest.mark.parametrize("family", DUAL_VERSION_METADATA)
@pytest.mark.parametrize("artifact_version", ["0.1.0", "0.2.0"])
def test_dual_version_contract_metadata_is_exact(
    family: str, artifact_version: str
) -> None:
    schema_name, version_field, prospective_identity_field = (
        DUAL_VERSION_METADATA[family]
    )
    spec = get_artifact_family_contract_spec(family, artifact_version)
    assert spec.family == family
    assert spec.artifact_version == artifact_version
    assert spec.schema_id == (
        "urn:frontier-agent-containment:schema:"
        f"{schema_name}:{artifact_version}"
    )
    assert spec.version_field == version_field
    if family in IDENTITY_PRESERVING_DUAL_VERSION_METADATA:
        assert spec.identity_field == prospective_identity_field
    else:
        assert spec.identity_field == (
            None if artifact_version == "0.1.0" else prospective_identity_field
        )


def test_registry_and_contract_specs_are_immutable() -> None:
    assert isinstance(ARTIFACT_FAMILY_CONTRACT_SPECS, MappingProxyType)
    spec = get_artifact_family_contract_spec("instrument_acceptance", "0.2.0")
    with pytest.raises(FrozenInstanceError):
        spec.artifact_version = "9.9.9"  # type: ignore[misc]
    with pytest.raises(TypeError):
        ARTIFACT_FAMILY_CONTRACT_SPECS[("example", "0.1.0")] = spec  # type: ignore[index]


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        (
            [
                (("example", "0.1.0"), _contract_spec()),
                (("example", "0.1.0"), _contract_spec()),
            ],
            "duplicate artifact-family contract key",
        ),
        (
            [(("other", "0.1.0"), _contract_spec())],
            "contract key family",
        ),
        (
            [(("example", "0.2.0"), _contract_spec())],
            "contract key version",
        ),
        (
            [
                (
                    ("example", "0.1.0"),
                    _contract_spec(schema_version="0.2.0"),
                )
            ],
            "schema ID",
        ),
        (
            [
                (("example", "0.1.0"), _contract_spec()),
                (
                    ("example", "0.2.0"),
                    _contract_spec(
                        artifact_version="0.2.0",
                        version_field="other_version",
                    ),
                ),
            ],
            "inconsistent version fields",
        ),
    ],
)
def test_registry_construction_rejects_inconsistent_metadata(
    entries: list[tuple[tuple[str, str], ArtifactFamilyContractSpec]],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _build_artifact_family_contract_specs(entries)


def test_legacy_public_api_remains_the_historical_projection() -> None:
    assert tuple(field.name for field in fields(ArtifactFamilySpec)) == (
        "schema_id",
        "identity_field",
        "version_field",
    )
    assert len(SUPPORTED_ARTIFACT_FAMILIES) == 21
    for family in DUAL_VERSION_METADATA:
        legacy = get_artifact_family_spec(family)
        assert isinstance(legacy, ArtifactFamilySpec)
        assert legacy.schema_id.endswith(":0.1.0")
        expected_identity = (
            DUAL_VERSION_METADATA[family][2]
            if family in IDENTITY_PRESERVING_DUAL_VERSION_METADATA
            else None
        )
        assert legacy.identity_field == expected_identity
        assert legacy.version_field == DUAL_VERSION_METADATA[family][1]


def test_legacy_and_exact_lookup_unknown_keys_raise_key_error() -> None:
    with pytest.raises(KeyError):
        get_artifact_family_spec("unknown_family")
    with pytest.raises(KeyError):
        get_artifact_family_contract_spec("unknown_family", "0.1.0")


@pytest.mark.parametrize("family", DUAL_VERSION_METADATA)
def test_exact_lookup_has_no_unknown_version_fallback(family: str) -> None:
    with pytest.raises(KeyError):
        get_artifact_family_contract_spec(family, "0.3.0")


@pytest.mark.parametrize(
    ("artifacts", "code", "path"),
    [
        (
            {"unknown_family": [{}]},
            SemanticErrorCode.UNSUPPORTED_ARTIFACT_FAMILY,
            "/",
        ),
        (
            {"instrument_acceptance": [{}]},
            SemanticErrorCode.SCHEMA_INVALID,
            "/acceptance_version",
        ),
        (
            {"instrument_acceptance": [{"acceptance_version": 0.2}]},
            SemanticErrorCode.VERSION_INVALID,
            "/acceptance_version",
        ),
        (
            {"instrument_acceptance": [{"acceptance_version": "0.3.0"}]},
            SemanticErrorCode.VERSION_INVALID,
            "/acceptance_version",
        ),
    ],
)
def test_predispatch_failure_matrix_is_deterministic(
    artifacts: dict[str, list[dict[str, Any]]],
    code: SemanticErrorCode,
    path: str,
    schema_store: dict[str, Any],
) -> None:
    findings = _validate(artifacts, schema_store)
    assert len(findings) == 1
    assert findings[0].code == code
    assert findings[0].field_path == path
    assert findings[0].artifact_id.startswith("<")


def test_supported_version_with_missing_exact_schema_fails_without_fallback(
    schema_store: dict[str, Any]
) -> None:
    reduced = dict(schema_store)
    reduced.pop(
        "urn:frontier-agent-containment:schema:instrument-acceptance:0.2.0"
    )
    artifacts = {"instrument_acceptance": [{"acceptance_version": "0.2.0"}]}
    findings = _validate(artifacts, reduced)
    assert len(findings) == 1
    assert findings[0].code == SemanticErrorCode.SCHEMA_INVALID
    assert findings[0].field_path == "/"
    assert ":0.2.0" in findings[0].message


def test_exact_prospective_schema_is_selected_not_historical_schema(
    schema_store: dict[str, Any]
) -> None:
    artifacts = _standalone_prospective_acceptance()
    artifacts["instrument_acceptance"][0].pop("instrument_acceptance_id")
    findings = _validate(artifacts, schema_store)
    assert any(
        finding.code == SemanticErrorCode.SCHEMA_INVALID
        and finding.artifact_family == "instrument_acceptance"
        and finding.field_path == "/"
        and "instrument_acceptance_id" in finding.message
        for finding in findings
    )


def test_prospective_schema_dispatch_does_not_require_historical_schema(
    schema_store: dict[str, Any]
) -> None:
    reduced = dict(schema_store)
    reduced.pop(
        "urn:frontier-agent-containment:schema:instrument-acceptance:0.1.0"
    )
    assert _validate(_standalone_prospective_acceptance(), reduced) == ()


@pytest.mark.parametrize(
    ("family", "version_field"),
    [
        ("campaign", "campaign_version"),
        ("derived_run_outcome", "outcome_version"),
    ],
)
def test_historical_missing_version_remains_one_schema_invalid_finding(
    family: str, version_field: str, schema_store: dict[str, Any]
) -> None:
    findings = _validate({family: [{}]}, schema_store)
    assert len(findings) == 1
    assert findings[0].code == SemanticErrorCode.SCHEMA_INVALID
    assert findings[0].field_path == f"/{version_field}"


@pytest.mark.parametrize(
    ("family", "id_field", "artifact_id", "builder"),
    [
        (
            "instrument_acceptance",
            "instrument_acceptance_id",
            "acceptance:example-001",
            _standalone_prospective_acceptance,
        ),
        (
            "derived_action_outcome",
            "derived_action_outcome_id",
            "actionoutcome:example-001",
            _prospective_postrun_set,
        ),
        (
            "derived_run_outcome",
            "derived_run_outcome_id",
            "runoutcome:example-001",
            _prospective_postrun_set,
        ),
    ],
)
def test_prospective_intrinsic_identity_is_extracted_generically(
    family: str,
    id_field: str,
    artifact_id: str,
    builder: Any,
    schema_store: dict[str, Any],
) -> None:
    artifacts = builder()
    duplicate = copy.deepcopy(artifacts[family][0])
    artifacts[family].append(duplicate)
    findings = _validate(artifacts, schema_store)
    assert any(
        finding.code == SemanticErrorCode.DUPLICATE_IDENTITY
        and finding.artifact_family == family
        and finding.artifact_id == artifact_id
        and finding.field_path == f"/{id_field}"
        for finding in findings
    )


def test_historical_identityless_contracts_remain_valid(
    schema_store: dict[str, Any]
) -> None:
    assert _validate(gating_artifact_set(), schema_store) == ()
    assert _validate(postrun_set(), schema_store) == ()


def test_prospective_outcome_primary_ids_do_not_replace_scientific_linkage(
    schema_store: dict[str, Any]
) -> None:
    artifacts = _prospective_postrun_set()
    assert artifacts["derived_action_outcome"][0]["run_id"] == (
        artifacts["derived_run_outcome"][0]["run_id"]
    )
    assert artifacts["derived_action_outcome"][0]["action_id"] == (
        artifacts["derived_run_outcome"][0]["action_outcome_references"][0][
            "action_id"
        ]
    )
    assert _validate(artifacts, schema_store) == ()


def test_invalid_action_outcome_science_remains_invalid_under_0_2(
    schema_store: dict[str, Any]
) -> None:
    artifacts = _prospective_postrun_set()
    artifacts["derived_action_outcome"][0]["evidence_event_ids"][0] = (
        "event:missing"
    )
    findings = _validate(artifacts, schema_store)
    assert any(
        finding.code == SemanticErrorCode.REFERENCE_INVALID
        and finding.artifact_family == "derived_action_outcome"
        for finding in findings
    )


def test_invalid_h1_derivation_remains_invalid_under_0_2(
    schema_store: dict[str, Any]
) -> None:
    artifacts = _prospective_postrun_set()
    artifacts["derived_run_outcome"][0]["h1_containment_failure"] = 1
    findings = _validate(artifacts, schema_store)
    assert any(
        finding.code == SemanticErrorCode.H1_DERIVATION_INVALID
        and finding.artifact_family == "derived_run_outcome"
        for finding in findings
    )


def test_standalone_prospective_acceptance_runs_existing_scientific_checks(
    schema_store: dict[str, Any]
) -> None:
    assert _validate(_standalone_prospective_acceptance(), schema_store) == ()


def test_historical_campaign_acceptance_behavior_is_unchanged(
    schema_store: dict[str, Any]
) -> None:
    findings = _validate(gating_artifact_set(), schema_store)
    assert findings == ()
    assert not _transition_findings(findings)


@pytest.mark.parametrize(
    ("reference", "expected_code"),
    [
        ("acceptance:example-001", None),
        ("acceptance:different", SemanticErrorCode.REFERENCE_INVALID),
    ],
)
def test_campaign_bound_prospective_acceptance_uses_exact_resolution(
    reference: str,
    expected_code: SemanticErrorCode | None,
    schema_store: dict[str, Any],
) -> None:
    findings = _validate(_prospective_gating_set(reference=reference), schema_store)
    assert not _transition_findings(findings)
    if expected_code is None:
        assert findings == ()
    else:
        assert len(findings) == 1
        assert findings[0].code == expected_code
        assert findings[0].field_path == "/instrument_acceptance_reference"


def test_multiple_prospective_acceptances_resolve_the_exact_target(
    schema_store: dict[str, Any]
) -> None:
    artifacts = _prospective_gating_set()
    second = copy.deepcopy(artifacts["instrument_acceptance"][0])
    second["instrument_acceptance_id"] = "acceptance:example-002"
    artifacts["instrument_acceptance"].append(second)
    findings = _validate(artifacts, schema_store)
    assert findings == ()
    assert not _transition_findings(findings)


def test_mixed_historical_and_prospective_acceptances_use_exact_target(
    schema_store: dict[str, Any]
) -> None:
    historical = gating_artifact_set()["instrument_acceptance"][0]
    artifacts = _prospective_gating_set()
    artifacts["instrument_acceptance"].append(historical)
    findings = _validate(artifacts, schema_store)
    assert findings == ()
    assert not _transition_findings(findings)


def test_superseding_exact_reference_findings_are_deterministic(
    schema_store: dict[str, Any],
) -> None:
    artifacts = _prospective_gating_set(reference="acceptance:different")
    first = _validate(artifacts, schema_store)
    second = _validate(artifacts, schema_store)
    third = _validate(artifacts, schema_store)
    assert first == second == third
    assert not _transition_findings(first)
    assert len(first) == 1
    assert first[0].code == SemanticErrorCode.REFERENCE_INVALID


def test_version_aware_validation_does_not_mutate_inputs(
    schema_store: dict[str, Any]
) -> None:
    artifacts = _prospective_postrun_set()
    original = copy.deepcopy(artifacts)
    _validate(artifacts, schema_store)
    assert artifacts == original
