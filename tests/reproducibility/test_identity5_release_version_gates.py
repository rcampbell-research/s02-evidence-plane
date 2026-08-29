"""Identity-5 dedicated release artifact version-gate regressions."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

import frontier_agent_containment.release_validation as release_module
from frontier_agent_containment.manifest_validation import validate_artifact_manifest
from frontier_agent_containment.release_validation import (
    ReleaseValidationError,
    ReleaseValidationErrorCode,
    ReleaseValidationFinding,
    assert_release_artifact_version_gates_valid,
    validate_release_artifact_version_gates,
)
from frontier_agent_containment.schema_validation import load_json, load_schema_store
from frontier_agent_containment.semantic_validation import (
    get_artifact_family_contract_spec,
)
from tests.reproducibility.test_identity4_identified_artifact_manifest_binding import (
    _artifact_manifest,
    _historical_documents,
    _prospective_documents,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/reproducibility/stage12d"
RELEASE_PROFILE_SCHEMA_ID = (
    "urn:frontier-agent-containment:schema:release-profile:0.1.0"
)
PHASE_TOKEN = {
    "DEVELOPMENT": "development",
    "INSTRUMENT_VALIDATION": "instrument-validation",
    "PILOT": "pilot",
    "CONFIRMATORY": "confirmatory",
}
ZERO_DIGEST = "sha256:" + ("0" * 64)
EXPECTED_CODES = [
    "RELEASE_PROFILE_SCHEMA_INVALID",
    "RELEASE_ARTIFACT_MANIFEST_INVALID",
    "RELEASE_ARTIFACT_DUPLICATE_SELECTION",
    "RELEASE_ARTIFACT_UNRESOLVED",
    "RELEASE_ARTIFACT_EXPECTED_VERSION_MISMATCH",
    "RELEASE_ARTIFACT_VERSION_INELIGIBLE",
]


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(sorted((ROOT / "schemas").glob("*.schema.json")))


def _release_profile(
    phase: str = "PILOT",
    active_entries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    token = PHASE_TOKEN[phase]
    entries = [] if active_entries is None else deepcopy(active_entries)
    return {
        "profile_version": "0.1.0",
        "release_id": f"release:{token}-v0.1",
        "release_phase": phase,
        "source_release_tag_identity": f"research-release-{token}-v0.1",
        "active_artifacts": entries,
        "rejected_inputs": [],
        "environment_reference": (
            "env:synthetic-lab"
            if phase in {"PILOT", "CONFIRMATORY"}
            else "NOT_APPLICABLE"
        ),
        "governing_profile_version": "release-integrity-profile-v0.1",
        "enabled_dependency_extras": [],
    }


def _selection(
    entry: dict[str, Any],
    *,
    expected_version: str | None = None,
) -> dict[str, Any]:
    selection = {
        "artifact_family": entry["artifact_family"],
        "artifact_id": entry["artifact_id"],
        "locator": entry["locator"],
    }
    if expected_version is not None:
        selection["expected_artifact_version"] = expected_version
    return selection


def _prospective_bundle(
    family: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    document = _prospective_documents()[family]
    manifest = _artifact_manifest(family, document)
    locator = manifest["artifacts"][0]["locator"]
    return document, manifest, {locator: document}


def _combined_manifest(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    combined = deepcopy(manifests[0])
    combined["artifacts"] = [
        deepcopy(entry)
        for manifest in manifests
        for entry in manifest["artifacts"]
    ]
    return combined


def _validate(
    release_profile: dict[str, Any],
    artifact_manifest: dict[str, Any],
    documents: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
    *,
    rejected: dict[str, bytes] | None = None,
) -> tuple[ReleaseValidationFinding, ...]:
    return validate_release_artifact_version_gates(
        release_profile,
        artifact_manifest=artifact_manifest,
        artifact_documents_by_locator=documents,
        rejected_bytes_by_locator=rejected or {},
        schema_store=schema_store,
    )


def _codes(
    findings: tuple[ReleaseValidationFinding, ...],
) -> list[ReleaseValidationErrorCode]:
    return [finding.code for finding in findings]


def test_release_error_code_members_are_exact() -> None:
    assert [member.value for member in ReleaseValidationErrorCode] == EXPECTED_CODES


def test_release_finding_is_frozen_and_slotted() -> None:
    finding = ReleaseValidationFinding(
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_UNRESOLVED,
        "synthetic",
        "/active_artifacts/0",
    )
    assert not hasattr(finding, "__dict__")
    with pytest.raises(FrozenInstanceError):
        finding.message = "changed"  # type: ignore[misc]


def test_validation_result_is_a_tuple(schema_store: dict[str, Any]) -> None:
    result = _validate(_release_profile("DEVELOPMENT"), {}, {}, schema_store)
    assert result == ()
    assert isinstance(result, tuple)


def test_module_all_exports_exact_public_api() -> None:
    assert release_module.__all__ == [
        "ReleaseValidationError",
        "ReleaseValidationErrorCode",
        "ReleaseValidationFinding",
        "assert_release_artifact_version_gates_valid",
        "validate_release_artifact_version_gates",
    ]


def test_assert_api_returns_none_on_success(schema_store: dict[str, Any]) -> None:
    assert (
        assert_release_artifact_version_gates_valid(
            _release_profile("DEVELOPMENT"),
            artifact_manifest={},
            artifact_documents_by_locator={},
            rejected_bytes_by_locator={},
            schema_store=schema_store,
        )
        is None
    )


def test_assert_api_raises_with_immutable_findings_and_count(
    schema_store: dict[str, Any],
) -> None:
    profile = _release_profile("DEVELOPMENT")
    profile["release_id"] = "release:pilot-v0.1"
    with pytest.raises(ReleaseValidationError) as caught:
        assert_release_artifact_version_gates_valid(
            profile,
            artifact_manifest={},
            artifact_documents_by_locator={},
            rejected_bytes_by_locator={},
            schema_store=schema_store,
        )
    assert isinstance(caught.value.findings, tuple)
    assert len(caught.value.findings) == 1
    assert str(caught.value) == "release artifact version validation has 1 finding(s)"


def test_malformed_release_profile_returns_structural_finding(
    schema_store: dict[str, Any],
) -> None:
    document, manifest, documents = _prospective_bundle("instrument_acceptance")
    profile = _release_profile("PILOT", [_selection(manifest["artifacts"][0])])
    profile["active_artifacts"][0]["locator"] = "/absolute.json"
    findings = _validate(profile, manifest, documents, schema_store)
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_PROFILE_SCHEMA_INVALID
    ]
    assert findings[0].field_path == "/active_artifacts/0/locator"
    assert document == _prospective_documents()["instrument_acceptance"]


def test_missing_release_profile_schema_fails_at_root(
    schema_store: dict[str, Any],
) -> None:
    incomplete_store = dict(schema_store)
    del incomplete_store[RELEASE_PROFILE_SCHEMA_ID]
    findings = _validate(_release_profile("DEVELOPMENT"), {}, {}, incomplete_store)
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_PROFILE_SCHEMA_INVALID
    ]
    assert findings[0].field_path == "/"
    assert RELEASE_PROFILE_SCHEMA_ID in findings[0].message


def test_structural_failure_stops_manifest_processing(
    schema_store: dict[str, Any],
) -> None:
    profile = _release_profile("PILOT", [])
    findings = _validate(profile, {}, {}, schema_store)
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_PROFILE_SCHEMA_INVALID
    ]


def test_exact_duplicate_active_entry_is_structurally_invalid(
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    selected = _selection(manifest["artifacts"][0])
    profile = _release_profile("PILOT", [selected, deepcopy(selected)])
    findings = _validate(profile, manifest, documents, schema_store)
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_PROFILE_SCHEMA_INVALID
    ]
    assert findings[0].field_path == "/active_artifacts"


def test_empty_active_artifacts_returns_without_manifest_validation(
    schema_store: dict[str, Any],
) -> None:
    assert _validate(_release_profile("DEVELOPMENT"), {}, {}, schema_store) == ()


def test_valid_manifest_prerequisite_permits_selection_processing(
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    profile = _release_profile(
        "PILOT", [_selection(manifest["artifacts"][0], expected_version="0.2.0")]
    )
    assert _validate(profile, manifest, documents, schema_store) == ()


def test_invalid_manifest_is_wrapped_and_stops_selection_processing(
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    manifest["artifacts"][0]["content_digest"] = ZERO_DIGEST
    selected = _selection(manifest["artifacts"][0], expected_version="0.1.0")
    findings = _validate(
        _release_profile("PILOT", [selected]), manifest, documents, schema_store
    )
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_MANIFEST_INVALID
    ]
    assert findings[0].field_path == "/active_artifacts"
    assert "MANIFEST_DIGEST_MISMATCH" in findings[0].message
    assert "canonical artifact content digest does not match" in findings[0].message


def test_multiple_manifest_findings_preserve_stage12d_order(
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    manifest["artifacts"][0]["artifact_id"] = "acceptance:wrong"
    manifest["artifacts"][0]["content_digest"] = ZERO_DIGEST
    stage12d = validate_artifact_manifest(
        manifest,
        artifact_documents_by_locator=documents,
        rejected_bytes_by_locator={},
        schema_store=schema_store,
    )
    findings = _validate(
        _release_profile("PILOT", [_selection(manifest["artifacts"][0])]),
        manifest,
        documents,
        schema_store,
    )
    assert len(stage12d) == len(findings) == 2
    assert all(
        finding.code is ReleaseValidationErrorCode.RELEASE_ARTIFACT_MANIFEST_INVALID
        for finding in findings
    )
    assert [finding.message for finding in findings] == [
        f"supplied Artifact Manifest is not coherent: {source.code.value}: "
        f"{source.message}"
        for source in stage12d
    ]


def test_only_active_artifacts_select_release_version_gate_subjects(
    schema_store: dict[str, Any],
) -> None:
    acceptance, acceptance_manifest, acceptance_documents = _prospective_bundle(
        "instrument_acceptance"
    )
    action, action_manifest, action_documents = _prospective_bundle(
        "derived_action_outcome"
    )
    manifest = _combined_manifest([acceptance_manifest, action_manifest])
    documents = acceptance_documents | action_documents
    selected = _selection(acceptance_manifest["artifacts"][0])
    assert _validate(
        _release_profile("PILOT", [selected]), manifest, documents, schema_store
    ) == ()
    assert acceptance["acceptance_version"] == action["outcome_version"] == "0.2.0"


@pytest.mark.parametrize(
    "family",
    [
        "instrument_acceptance",
        "derived_action_outcome",
        "derived_run_outcome",
    ],
)
def test_each_affected_0_2_contract_passes(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle(family)
    selected = _selection(manifest["artifacts"][0], expected_version="0.2.0")
    assert _validate(
        _release_profile("PILOT", [selected]), manifest, documents, schema_store
    ) == ()


def test_multiple_distinct_same_family_0_2_artifacts_pass(
    schema_store: dict[str, Any],
) -> None:
    first = _prospective_documents()["derived_action_outcome"]
    second = deepcopy(first)
    second["derived_action_outcome_id"] = "actionoutcome:example-002"
    first_manifest = _artifact_manifest("derived_action_outcome", first)
    second_manifest = _artifact_manifest("derived_action_outcome", second)
    second_manifest["artifacts"][0]["locator"] = (
        "artifacts/derived_action_outcome-002.json"
    )
    manifest = _combined_manifest([first_manifest, second_manifest])
    documents = {
        first_manifest["artifacts"][0]["locator"]: first,
        second_manifest["artifacts"][0]["locator"]: second,
    }
    selected = [
        _selection(entry, expected_version="0.2.0")
        for entry in manifest["artifacts"]
    ]
    assert _validate(
        _release_profile("PILOT", selected), manifest, documents, schema_store
    ) == ()


def test_all_three_affected_0_2_families_pass(
    schema_store: dict[str, Any],
) -> None:
    bundles = [_prospective_bundle(family) for family in (
        "instrument_acceptance",
        "derived_action_outcome",
        "derived_run_outcome",
    )]
    manifests = [bundle[1] for bundle in bundles]
    manifest = _combined_manifest(manifests)
    documents = {
        locator: document
        for _, _, mapping in bundles
        for locator, document in mapping.items()
    }
    selected = [
        _selection(entry, expected_version="0.2.0")
        for entry in manifest["artifacts"]
    ]
    assert _validate(
        _release_profile("PILOT", selected), manifest, documents, schema_store
    ) == ()


@pytest.mark.parametrize("mismatch", ["locator", "family", "artifact_id"])
def test_selection_triple_mismatch_is_unresolved(
    mismatch: str,
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    selected = _selection(manifest["artifacts"][0])
    if mismatch == "locator":
        selected["locator"] = "artifacts/missing.json"
    elif mismatch == "family":
        selected["artifact_family"] = "derived_run_outcome"
    else:
        selected["artifact_id"] = "acceptance:wrong"
    findings = _validate(
        _release_profile("PILOT", [selected]), manifest, documents, schema_store
    )
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_UNRESOLVED
    ]
    assert findings[0].field_path == "/active_artifacts/0"
    assert findings[0].artifact_family == selected["artifact_family"]
    assert findings[0].artifact_id == selected["artifact_id"]
    assert findings[0].locator == selected["locator"]
    assert findings[0].message == (
        f"selected {selected['artifact_family']} artifact {selected['artifact_id']!r} "
        f"at locator {selected['locator']!r} does not resolve exactly once "
        "through the valid Artifact Manifest"
    )


def test_unresolved_selection_suppresses_version_checks(
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    selected = _selection(manifest["artifacts"][0], expected_version="0.1.0")
    selected["locator"] = "artifacts/missing.json"
    findings = _validate(
        _release_profile("PILOT", [selected]), manifest, documents, schema_store
    )
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_UNRESOLVED
    ]


@pytest.mark.parametrize("expected_version", [None, "0.2.0"])
def test_expected_version_absent_or_matching_passes(
    expected_version: str | None,
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    selected = _selection(
        manifest["artifacts"][0], expected_version=expected_version
    )
    assert _validate(
        _release_profile("PILOT", [selected]), manifest, documents, schema_store
    ) == ()


def test_eligible_actual_with_wrong_expected_version_is_only_mismatch(
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    selected = _selection(manifest["artifacts"][0], expected_version="0.1.0")
    findings = _validate(
        _release_profile("PILOT", [selected]), manifest, documents, schema_store
    )
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_EXPECTED_VERSION_MISMATCH
    ]
    assert findings[0].field_path == (
        "/active_artifacts/0/expected_artifact_version"
    )
    assert findings[0].message == (
        "expected_artifact_version '0.1.0' does not equal resolved artifact "
        "contract version '0.2.0'"
    )


def _defense_findings(
    *, expected_version: str | None = None, index: int = 0
) -> tuple[ReleaseValidationFinding, ...]:
    selection = {
        "artifact_family": "instrument_acceptance",
        "artifact_id": "acceptance:historical-defense",
        "locator": "artifacts/historical-defense.json",
    }
    if expected_version is not None:
        selection["expected_artifact_version"] = expected_version
    findings: list[ReleaseValidationFinding] = []
    release_module._validate_resolved_selection(
        selection,
        get_artifact_family_contract_spec("instrument_acceptance", "0.1.0"),
        index,
        findings,
    )
    return tuple(findings)


def test_resolved_affected_0_1_defense_gate_is_ineligible() -> None:
    findings = _defense_findings(index=3)
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_VERSION_INELIGIBLE
    ]
    assert findings[0].field_path == "/active_artifacts/3"
    assert findings[0].message == (
        "selected instrument_acceptance artifact uses contract version 0.1.0; "
        "research release eligibility requires version 0.2.0 for this family"
    )


def test_resolved_0_1_expected_mismatch_precedes_ineligibility() -> None:
    findings = _defense_findings(expected_version="0.2.0")
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_EXPECTED_VERSION_MISMATCH,
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_VERSION_INELIGIBLE,
    ]


def test_public_historical_0_1_path_stops_at_manifest_prerequisite(
    schema_store: dict[str, Any],
) -> None:
    document = _historical_documents()["instrument_acceptance"]
    manifest = _artifact_manifest("instrument_acceptance", document)
    locator = manifest["artifacts"][0]["locator"]
    selected = _selection(manifest["artifacts"][0], expected_version="0.1.0")
    findings = _validate(
        _release_profile("PILOT", [selected]),
        manifest,
        {locator: document},
        schema_store,
    )
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_MANIFEST_INVALID
    ]
    assert "MANIFEST_REFERENCE_INVALID" in findings[0].message
    assert (
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_VERSION_INELIGIBLE
        not in _codes(findings)
    )


def test_unaffected_0_1_selected_artifact_has_no_version_gate(
    schema_store: dict[str, Any],
) -> None:
    manifest = load_json(FIXTURES / "artifact-manifest.json")
    document = load_json(FIXTURES / "artifact.resource.json")
    assert isinstance(manifest, dict)
    assert isinstance(document, dict)
    entry = manifest["artifacts"][0]
    findings = _validate(
        _release_profile("PILOT", [_selection(entry, expected_version="0.1.0")]),
        manifest,
        {entry["locator"]: document},
        schema_store,
    )
    assert findings == ()


def test_semantic_duplicate_with_different_locator_is_reported_and_resolved(
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    first = _selection(manifest["artifacts"][0])
    second = deepcopy(first)
    second["locator"] = "artifacts/missing.json"
    findings = _validate(
        _release_profile("PILOT", [first, second]), manifest, documents, schema_store
    )
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_DUPLICATE_SELECTION,
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_UNRESOLVED,
    ]
    assert findings[0].field_path == "/active_artifacts"
    assert findings[0].message == (
        "selected instrument_acceptance artifact identity "
        "'acceptance:example-001' occurs more than once in active_artifacts"
    )
    assert findings[1].field_path == "/active_artifacts/1"


def test_semantic_duplicate_with_different_expected_version_reports_both(
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    first = _selection(manifest["artifacts"][0], expected_version="0.1.0")
    second = _selection(manifest["artifacts"][0], expected_version="0.2.0")
    findings = _validate(
        _release_profile("PILOT", [first, second]), manifest, documents, schema_store
    )
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_DUPLICATE_SELECTION,
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_EXPECTED_VERSION_MISMATCH,
    ]
    assert findings[1].field_path == (
        "/active_artifacts/0/expected_artifact_version"
    )


def test_unselected_historical_artifact_outside_manifest_mapping_is_ignored(
    schema_store: dict[str, Any],
) -> None:
    historical = _historical_documents()["instrument_acceptance"]
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    selected = _selection(manifest["artifacts"][0])
    assert historical["acceptance_version"] == "0.1.0"
    assert _validate(
        _release_profile("PILOT", [selected]), manifest, documents, schema_store
    ) == ()


def test_extra_supplied_historical_document_wraps_locator_closure_failure(
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    documents["artifacts/unselected-historical.json"] = _historical_documents()[
        "instrument_acceptance"
    ]
    selected = _selection(manifest["artifacts"][0])
    findings = _validate(
        _release_profile("PILOT", [selected]), manifest, documents, schema_store
    )
    assert _codes(findings) == [
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_MANIFEST_INVALID
    ]
    assert "MANIFEST_INCOMPLETE" in findings[0].message
    assert (
        ReleaseValidationErrorCode.RELEASE_ARTIFACT_VERSION_INELIGIBLE
        not in _codes(findings)
    )


def test_manifest_listed_unselected_historical_artifact_is_only_prerequisite_failure(
    schema_store: dict[str, Any],
) -> None:
    _, prospective_manifest, prospective_documents = _prospective_bundle(
        "instrument_acceptance"
    )
    historical = _historical_documents()["instrument_acceptance"]
    historical_manifest = _artifact_manifest(
        "instrument_acceptance",
        historical,
        artifact_id="acceptance:historical-unselected",
    )
    historical_manifest["artifacts"][0]["locator"] = (
        "artifacts/historical-unselected.json"
    )
    manifest = _combined_manifest([prospective_manifest, historical_manifest])
    documents = prospective_documents | {
        historical_manifest["artifacts"][0]["locator"]: historical
    }
    selected = _selection(prospective_manifest["artifacts"][0])
    findings = _validate(
        _release_profile("PILOT", [selected]), manifest, documents, schema_store
    )
    assert ReleaseValidationErrorCode.RELEASE_ARTIFACT_MANIFEST_INVALID in _codes(
        findings
    )
    assert all(
        finding.code
        is not ReleaseValidationErrorCode.RELEASE_ARTIFACT_VERSION_INELIGIBLE
        for finding in findings
    )


@pytest.mark.parametrize("phase", tuple(PHASE_TOKEN))
def test_affected_0_2_gate_is_identical_in_every_release_phase(
    phase: str,
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    selected = _selection(manifest["artifacts"][0], expected_version="0.2.0")
    assert _validate(
        _release_profile(phase, [selected]), manifest, documents, schema_store
    ) == ()


def test_duplicate_findings_are_sorted_by_family_and_identity(
    schema_store: dict[str, Any],
) -> None:
    bundles = {
        family: _prospective_bundle(family)
        for family in ("instrument_acceptance", "derived_run_outcome")
    }
    manifests = [bundle[1] for bundle in bundles.values()]
    manifest = _combined_manifest(manifests)
    documents = {
        locator: document
        for _, _, mapping in bundles.values()
        for locator, document in mapping.items()
    }
    active: list[dict[str, Any]] = []
    for family in ("instrument_acceptance", "derived_run_outcome"):
        entry = bundles[family][1]["artifacts"][0]
        active.extend(
            [_selection(entry), _selection(entry, expected_version="0.2.0")]
        )
    findings = _validate(
        _release_profile("PILOT", active), manifest, documents, schema_store
    )
    duplicates = [
        finding
        for finding in findings
        if finding.code
        is ReleaseValidationErrorCode.RELEASE_ARTIFACT_DUPLICATE_SELECTION
    ]
    assert [finding.artifact_family for finding in duplicates] == [
        "derived_run_outcome",
        "instrument_acceptance",
    ]
    assert findings[:2] == tuple(duplicates)


def test_per_entry_findings_follow_active_array_order(
    schema_store: dict[str, Any],
) -> None:
    acceptance = _prospective_bundle("instrument_acceptance")
    run = _prospective_bundle("derived_run_outcome")
    manifest = _combined_manifest([acceptance[1], run[1]])
    documents = acceptance[2] | run[2]
    first = _selection(
        acceptance[1]["artifacts"][0], expected_version="0.1.0"
    )
    second = _selection(run[1]["artifacts"][0])
    second["artifact_id"] = "runoutcome:missing"
    findings = _validate(
        _release_profile("PILOT", [first, second]), manifest, documents, schema_store
    )
    assert [finding.field_path for finding in findings] == [
        "/active_artifacts/0/expected_artifact_version",
        "/active_artifacts/1",
    ]


def test_reordering_entries_updates_indices_but_preserves_attribution(
    schema_store: dict[str, Any],
) -> None:
    acceptance = _prospective_bundle("instrument_acceptance")
    run = _prospective_bundle("derived_run_outcome")
    manifest = _combined_manifest([acceptance[1], run[1]])
    documents = acceptance[2] | run[2]
    entries = [
        _selection(acceptance[1]["artifacts"][0], expected_version="0.1.0"),
        _selection(run[1]["artifacts"][0], expected_version="0.1.0"),
    ]
    forward = _validate(
        _release_profile("PILOT", entries), manifest, documents, schema_store
    )
    reverse = _validate(
        _release_profile("PILOT", list(reversed(entries))),
        manifest,
        documents,
        schema_store,
    )
    assert [finding.artifact_family for finding in forward] == [
        "instrument_acceptance",
        "derived_run_outcome",
    ]
    assert [finding.artifact_family for finding in reverse] == [
        "derived_run_outcome",
        "instrument_acceptance",
    ]
    assert [finding.field_path for finding in forward] == [
        "/active_artifacts/0/expected_artifact_version",
        "/active_artifacts/1/expected_artifact_version",
    ]
    assert [finding.field_path for finding in reverse] == [
        "/active_artifacts/0/expected_artifact_version",
        "/active_artifacts/1/expected_artifact_version",
    ]


def test_repeated_validation_is_deterministic(schema_store: dict[str, Any]) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    selected = _selection(manifest["artifacts"][0], expected_version="0.1.0")
    profile = _release_profile("PILOT", [selected])
    first = _validate(profile, manifest, documents, schema_store)
    second = _validate(profile, manifest, documents, schema_store)
    assert first == second


def test_validation_does_not_mutate_any_caller_input(
    schema_store: dict[str, Any],
) -> None:
    _, manifest, documents = _prospective_bundle("instrument_acceptance")
    profile = _release_profile(
        "PILOT",
        [_selection(manifest["artifacts"][0], expected_version="0.1.0")],
    )
    rejected = {"rejected/synthetic.raw": b"synthetic"}
    originals = deepcopy((profile, manifest, documents, rejected, schema_store))
    _validate(
        profile,
        manifest,
        documents,
        schema_store,
        rejected=rejected,
    )
    assert (profile, manifest, documents, rejected, schema_store) == originals
