"""Identity-4 version-aware identified-artifact manifest regressions."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import frontier_agent_containment.manifest_validation as manifest_module
from frontier_agent_containment.integrity import canonical_sha256
from frontier_agent_containment.manifest_validation import (
    ManifestErrorCode,
    validate_artifact_manifest,
    validate_reproducibility_manifest,
)
from frontier_agent_containment.schema_validation import load_json, load_schema_store
from frontier_agent_containment.semantic_validation import (
    get_artifact_family_contract_spec,
)
from tests.semantic.test_stage10_confirmatory_gating import gating_artifact_set
from tests.semantic.test_stage11_postrun_evidence_closure import postrun_set


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/reproducibility/stage12d"
RESOURCE_LOCATOR = "artifacts/artifact.resource.json"
REFERENCE_PATH = "/instrument_acceptance_reference"
ZERO_DIGEST = "sha256:" + "0" * 64
FAMILY_METADATA = {
    "instrument_acceptance": (
        "acceptance_version",
        "instrument_acceptance_id",
        "acceptance:example-001",
    ),
    "derived_action_outcome": (
        "outcome_version",
        "derived_action_outcome_id",
        "actionoutcome:example-001",
    ),
    "derived_run_outcome": (
        "outcome_version",
        "derived_run_outcome_id",
        "runoutcome:example-001",
    ),
}


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(sorted((ROOT / "schemas").glob("*.schema.json")))


def _prospective_documents() -> dict[str, dict[str, Any]]:
    gating = gating_artifact_set()
    acceptance = deepcopy(gating["instrument_acceptance"][0])
    acceptance["acceptance_version"] = "0.2.0"
    acceptance["instrument_acceptance_id"] = "acceptance:example-001"

    postrun = postrun_set()
    action = deepcopy(postrun["derived_action_outcome"][0])
    action["outcome_version"] = "0.2.0"
    action["derived_action_outcome_id"] = "actionoutcome:example-001"
    run = deepcopy(postrun["derived_run_outcome"][0])
    run["outcome_version"] = "0.2.0"
    run["derived_run_outcome_id"] = "runoutcome:example-001"
    return {
        "instrument_acceptance": acceptance,
        "derived_action_outcome": action,
        "derived_run_outcome": run,
    }


def _historical_documents() -> dict[str, dict[str, Any]]:
    gating = gating_artifact_set()
    postrun = postrun_set()
    return {
        "instrument_acceptance": deepcopy(gating["instrument_acceptance"][0]),
        "derived_action_outcome": deepcopy(postrun["derived_action_outcome"][0]),
        "derived_run_outcome": deepcopy(postrun["derived_run_outcome"][0]),
    }


def _artifact_manifest(
    family: str,
    document: dict[str, Any],
    *,
    artifact_id: str | None = None,
    contract_version: str | None = None,
) -> dict[str, Any]:
    version_field, _, default_id = FAMILY_METADATA[family]
    version = contract_version or document[version_field]
    spec = get_artifact_family_contract_spec(family, version)
    identity = (
        document[spec.identity_field]
        if artifact_id is None and spec.identity_field is not None
        else artifact_id or default_id
    )
    return {
        "manifest_version": "0.1.0",
        "scope": {"scope_type": "RELEASE"},
        "canonicalization_id": "RFC8785-JCS",
        "digest_algorithm": "SHA-256",
        "artifacts": [
            {
                "artifact_family": family,
                "artifact_id": identity,
                "artifact_version": version,
                "locator": f"artifacts/{family}.json",
                "schema_id": spec.schema_id,
                "schema_version": version,
                "lifecycle_state": "FROZEN",
                "phase_context": "CONFIRMATORY",
                "content_digest": canonical_sha256(document),
            }
        ],
        "rejected_inputs": [],
    }


def _validate_binding(
    manifest: dict[str, Any],
    document: dict[str, Any],
    schema_store: dict[str, Any],
) -> tuple[Any, ...]:
    locator = manifest["artifacts"][0]["locator"]
    return validate_artifact_manifest(
        manifest,
        artifact_documents_by_locator={locator: document},
        rejected_bytes_by_locator={},
        schema_store=schema_store,
    )


def _codes(findings: tuple[Any, ...] | list[Any]) -> set[ManifestErrorCode]:
    return {finding.code for finding in findings}


@pytest.mark.parametrize("family", FAMILY_METADATA)
def test_exact_prospective_manifest_binding_is_valid(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()[family]
    assert _validate_binding(
        _artifact_manifest(family, document),
        document,
        schema_store,
    ) == ()


def test_acceptance_wrong_manifest_identity_is_rejected(
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()["instrument_acceptance"]
    manifest = _artifact_manifest(
        "instrument_acceptance",
        document,
        artifact_id="acceptance:wrong",
    )
    findings = _validate_binding(manifest, document, schema_store)
    assert _codes(findings) == {ManifestErrorCode.MANIFEST_IDENTITY_MISMATCH}
    assert findings[0].field_path == "/artifacts/0/artifact_id"


@pytest.mark.parametrize(
    "substitute",
    ["run_id", "action_id", "encoded_linkage"],
)
def test_action_outcome_linkage_cannot_substitute_for_primary_identity(
    substitute: str,
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()["derived_action_outcome"]
    if substitute == "encoded_linkage":
        artifact_id = "actionoutcome:run-action-linkage"
    else:
        artifact_id = document[substitute]
    manifest = _artifact_manifest(
        "derived_action_outcome",
        document,
        artifact_id=artifact_id,
    )
    findings = _validate_binding(manifest, document, schema_store)
    assert ManifestErrorCode.MANIFEST_IDENTITY_MISMATCH in _codes(findings)


def test_run_outcome_run_id_cannot_substitute_for_primary_identity(
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()["derived_run_outcome"]
    manifest = _artifact_manifest(
        "derived_run_outcome",
        document,
        artifact_id=document["run_id"],
    )
    findings = _validate_binding(manifest, document, schema_store)
    assert ManifestErrorCode.MANIFEST_IDENTITY_MISMATCH in _codes(findings)


@pytest.mark.parametrize("family", FAMILY_METADATA)
def test_correct_identity_with_wrong_digest_is_rejected(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()[family]
    manifest = _artifact_manifest(family, document)
    manifest["artifacts"][0]["content_digest"] = ZERO_DIGEST
    findings = _validate_binding(manifest, document, schema_store)
    assert ManifestErrorCode.MANIFEST_DIGEST_MISMATCH in _codes(findings)
    assert any(
        finding.field_path == "/artifacts/0/content_digest" for finding in findings
    )


def test_changed_identity_changes_digest_and_requires_both_updates(
    schema_store: dict[str, Any],
) -> None:
    old_document = _prospective_documents()["instrument_acceptance"]
    old_manifest = _artifact_manifest("instrument_acceptance", old_document)
    old_digest = old_manifest["artifacts"][0]["content_digest"]

    new_document = deepcopy(old_document)
    new_document["instrument_acceptance_id"] = "acceptance:example-002"
    new_digest = canonical_sha256(new_document)
    assert new_digest != old_digest

    old_id_new_digest = _artifact_manifest(
        "instrument_acceptance",
        new_document,
        artifact_id=old_document["instrument_acceptance_id"],
    )
    assert _codes(_validate_binding(old_id_new_digest, new_document, schema_store)) == {
        ManifestErrorCode.MANIFEST_IDENTITY_MISMATCH
    }

    new_id_old_digest = _artifact_manifest("instrument_acceptance", new_document)
    new_id_old_digest["artifacts"][0]["content_digest"] = old_digest
    assert _codes(_validate_binding(new_id_old_digest, new_document, schema_store)) == {
        ManifestErrorCode.MANIFEST_DIGEST_MISMATCH
    }

    assert _validate_binding(
        _artifact_manifest("instrument_acceptance", new_document),
        new_document,
        schema_store,
    ) == ()


def test_cross_family_document_uses_existing_binding_failures(
    schema_store: dict[str, Any],
) -> None:
    action = _prospective_documents()["derived_action_outcome"]
    manifest = _artifact_manifest(
        "derived_run_outcome",
        action,
        artifact_id=action["derived_action_outcome_id"],
    )
    findings = _validate_binding(manifest, action, schema_store)
    assert ManifestErrorCode.MANIFEST_IDENTITY_MISMATCH in _codes(findings)
    assert ManifestErrorCode.MANIFEST_SCHEMA_BINDING_INVALID in _codes(findings)


def test_manifest_duplicate_identity_behavior_is_unchanged(
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()["instrument_acceptance"]
    manifest = _artifact_manifest("instrument_acceptance", document)
    duplicate = deepcopy(manifest["artifacts"][0])
    duplicate["locator"] = "artifacts/instrument_acceptance-copy.json"
    manifest["artifacts"].append(duplicate)
    findings = validate_artifact_manifest(
        manifest,
        artifact_documents_by_locator={
            manifest["artifacts"][0]["locator"]: document,
            duplicate["locator"]: deepcopy(document),
        },
        rejected_bytes_by_locator={},
        schema_store=schema_store,
    )
    duplicates = [
        finding
        for finding in findings
        if finding.code is ManifestErrorCode.MANIFEST_DUPLICATE_IDENTITY
        and finding.field_path == "/artifacts"
    ]
    assert len(duplicates) == 1


@pytest.mark.parametrize("family", FAMILY_METADATA)
def test_historical_affected_families_remain_identityless(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    document = _historical_documents()[family]
    manifest = _artifact_manifest(
        family,
        document,
        artifact_id=FAMILY_METADATA[family][2],
    )
    findings = _validate_binding(manifest, document, schema_store)
    matching = [
        finding
        for finding in findings
        if finding.code is ManifestErrorCode.MANIFEST_REFERENCE_INVALID
        and finding.field_path == "/artifacts/0/artifact_id"
    ]
    assert len(matching) == 1
    assert "no intrinsic primary ID" in matching[0].message


@pytest.mark.parametrize("family", FAMILY_METADATA)
def test_manifest_version_must_match_document_selected_contract(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()[family]
    manifest = _artifact_manifest(family, document)
    manifest["artifacts"][0]["artifact_version"] = "0.1.0"
    findings = _validate_binding(manifest, document, schema_store)
    matching = [
        finding
        for finding in findings
        if finding.code is ManifestErrorCode.MANIFEST_VERSION_MISMATCH
        and finding.field_path == "/artifacts/0/artifact_version"
    ]
    assert len(matching) == 1


def test_unsupported_document_version_has_no_fallback(
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()["instrument_acceptance"]
    manifest = _artifact_manifest("instrument_acceptance", document)
    document["acceptance_version"] = "0.3.0"
    manifest["artifacts"][0]["artifact_version"] = "0.3.0"
    manifest["artifacts"][0]["content_digest"] = canonical_sha256(document)
    findings = _validate_binding(manifest, document, schema_store)
    assert len(findings) == 1
    assert findings[0].code is ManifestErrorCode.MANIFEST_REFERENCE_INVALID
    assert findings[0].field_path == "/artifacts/0/artifact_version"


def test_wrong_exact_schema_binding_is_rejected(
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()["instrument_acceptance"]
    manifest = _artifact_manifest("instrument_acceptance", document)
    entry = manifest["artifacts"][0]
    entry["schema_id"] = (
        "urn:frontier-agent-containment:schema:instrument-acceptance:0.1.0"
    )
    entry["schema_version"] = "0.1.0"
    findings = _validate_binding(manifest, document, schema_store)
    assert ManifestErrorCode.MANIFEST_SCHEMA_BINDING_INVALID in _codes(findings)


def test_correct_locator_does_not_rescue_wrong_identity(
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()["instrument_acceptance"]
    manifest = _artifact_manifest(
        "instrument_acceptance",
        document,
        artifact_id="acceptance:wrong",
    )
    findings = _validate_binding(manifest, document, schema_store)
    assert ManifestErrorCode.MANIFEST_IDENTITY_MISMATCH in _codes(findings)


def test_missing_supplied_locator_remains_incomplete(
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()["instrument_acceptance"]
    manifest = _artifact_manifest("instrument_acceptance", document)
    findings = validate_artifact_manifest(
        manifest,
        artifact_documents_by_locator={},
        rejected_bytes_by_locator={},
        schema_store=schema_store,
    )
    assert _codes(findings) == {ManifestErrorCode.MANIFEST_INCOMPLETE}


@pytest.mark.parametrize("family", FAMILY_METADATA)
def test_active_resolution_uses_exact_prospective_primary_identity(family: str) -> None:
    document = _prospective_documents()[family]
    identity_field = FAMILY_METADATA[family][1]
    active = {family: [document]}
    assert manifest_module._resolve_active(active, family, document[identity_field]) is document


@pytest.mark.parametrize(
    ("family", "linkage_field"),
    [
        ("derived_action_outcome", "run_id"),
        ("derived_action_outcome", "action_id"),
        ("derived_run_outcome", "run_id"),
    ],
)
def test_active_resolution_never_uses_scientific_linkage(
    family: str,
    linkage_field: str,
) -> None:
    document = _prospective_documents()[family]
    assert manifest_module._resolve_active(
        {family: [document]},
        family,
        document[linkage_field],
    ) is None


@pytest.mark.parametrize("family", FAMILY_METADATA)
def test_duplicate_prospective_primary_identity_never_resolves(family: str) -> None:
    document = _prospective_documents()[family]
    duplicate = deepcopy(document)
    identity_field = FAMILY_METADATA[family][1]
    assert manifest_module._resolve_active(
        {family: [document, duplicate]},
        family,
        document[identity_field],
    ) is None


def test_active_unknown_or_wrong_family_identity_fails_closed() -> None:
    documents = _prospective_documents()
    acceptance = documents["instrument_acceptance"]
    identity = acceptance["instrument_acceptance_id"]
    assert manifest_module._resolve_active(
        {"instrument_acceptance": [acceptance]},
        "instrument_acceptance",
        "acceptance:missing",
    ) is None
    assert manifest_module._resolve_active(
        {"derived_run_outcome": [documents["derived_run_outcome"]]},
        "derived_run_outcome",
        identity,
    ) is None


def test_unlisted_supplied_artifact_does_not_become_active() -> None:
    documents = _prospective_documents()
    active = {"instrument_acceptance": [documents["instrument_acceptance"]]}
    assert manifest_module._resolve_active(
        active,
        "derived_run_outcome",
        documents["derived_run_outcome"]["derived_run_outcome_id"],
    ) is None


def _acceptance_manifest(
    acceptance: dict[str, Any],
    *,
    reference: str | None = None,
) -> dict[str, Any]:
    return {
        "release_phase": "CONFIRMATORY",
        "instrument_configuration_id": acceptance["instrument_configuration_id"],
        "environment": {"environment_reference": acceptance["environment_id"]},
        "campaign_id": acceptance["campaign_id"],
        "instrument_acceptance_reference": (
            reference or acceptance.get("instrument_acceptance_id", "acceptance:opaque")
        ),
    }


def _acceptance_context_findings(
    manifest: dict[str, Any],
    acceptances: list[dict[str, Any]],
    schema_store: dict[str, Any],
) -> tuple[Any, ...]:
    findings: list[Any] = []
    manifest_module._validate_acceptance_context(
        manifest,
        {"instrument_acceptance": acceptances},
        None,
        schema_store,
        findings,
    )
    return manifest_module._sorted(findings)


def test_repro_prospective_acceptance_exact_reference_resolves(
    schema_store: dict[str, Any],
) -> None:
    acceptance = _prospective_documents()["instrument_acceptance"]
    manifest = _acceptance_manifest(acceptance)
    assert _acceptance_context_findings(manifest, [acceptance], schema_store) == ()


def test_repro_prospective_acceptance_no_match_is_exactly_unresolved(
    schema_store: dict[str, Any],
) -> None:
    acceptance = _prospective_documents()["instrument_acceptance"]
    manifest = _acceptance_manifest(acceptance, reference="acceptance:missing")
    findings = _acceptance_context_findings(manifest, [acceptance], schema_store)
    assert len(findings) == 1
    assert findings[0].code is ManifestErrorCode.REPRODUCIBILITY_REFERENCE_INVALID
    assert findings[0].field_path == REFERENCE_PATH
    assert findings[0].message == (
        "instrument_acceptance identity does not resolve exactly once "
        "in active_artifacts"
    )


def test_repro_duplicate_prospective_acceptance_is_not_selected(
    schema_store: dict[str, Any],
) -> None:
    acceptance = _prospective_documents()["instrument_acceptance"]
    manifest = _acceptance_manifest(acceptance)
    findings = _acceptance_context_findings(
        manifest,
        [acceptance, deepcopy(acceptance)],
        schema_store,
    )
    assert len(findings) == 1
    assert findings[0].code is ManifestErrorCode.REPRODUCIBILITY_REFERENCE_INVALID


def test_repro_exact_target_incompatibility_remains_resolved(
    schema_store: dict[str, Any],
) -> None:
    acceptance = _prospective_documents()["instrument_acceptance"]
    manifest = _acceptance_manifest(acceptance)
    manifest["campaign_id"] = "campaign:other"
    findings = _acceptance_context_findings(manifest, [acceptance], schema_store)
    assert len(findings) == 1
    assert findings[0].message == (
        "referenced instrument acceptance is incompatible with release context"
    )


@pytest.mark.parametrize("eligibility", ["state", "phase"])
def test_repro_mode_selection_does_not_depend_on_eligibility(
    eligibility: str,
    schema_store: dict[str, Any],
) -> None:
    acceptance = _prospective_documents()["instrument_acceptance"]
    manifest = _acceptance_manifest(acceptance, reference="acceptance:missing")
    if eligibility == "state":
        acceptance["acceptance_state"] = "REJECTED"
        acceptance.pop("accepted_for_phase")
        acceptance["unresolved_conditions"] = ["Synthetic rejection."]
    else:
        acceptance["acceptance_state"] = "ACCEPTED_FOR_PILOT"
        acceptance["accepted_for_phase"] = "PILOT"
    findings = _acceptance_context_findings(manifest, [acceptance], schema_store)
    assert len(findings) == 1
    assert findings[0].message.endswith("does not resolve exactly once in active_artifacts")


@pytest.mark.parametrize("candidate_count", [0, 1, 2])
def test_repro_historical_unique_compatible_behavior_is_preserved(
    candidate_count: int,
    schema_store: dict[str, Any],
) -> None:
    historical = _historical_documents()["instrument_acceptance"]
    manifest = _acceptance_manifest(historical, reference="acceptance:opaque")
    candidates = [deepcopy(historical) for _ in range(candidate_count)]
    findings = _acceptance_context_findings(manifest, candidates, schema_store)
    if candidate_count == 1:
        assert findings == ()
    else:
        assert len(findings) == 1
        assert findings[0].message.endswith(f"found {candidate_count}")


def test_structurally_invalid_prospective_acceptance_cannot_claim_reference(
    schema_store: dict[str, Any],
) -> None:
    historical = _historical_documents()["instrument_acceptance"]
    invalid = _prospective_documents()["instrument_acceptance"]
    invalid.pop("acceptance_basis")
    manifest = _acceptance_manifest(
        historical,
        reference=invalid["instrument_acceptance_id"],
    )
    assert _acceptance_context_findings(
        manifest,
        [historical, invalid],
        schema_store,
    ) == ()


def test_linked_prospective_acceptance_prevents_historical_fallback(
    schema_store: dict[str, Any],
) -> None:
    historical = _historical_documents()["instrument_acceptance"]
    prospective = _prospective_documents()["instrument_acceptance"]
    manifest = _acceptance_manifest(prospective, reference="acceptance:missing")
    findings = _acceptance_context_findings(
        manifest,
        [historical, prospective],
        schema_store,
    )
    assert len(findings) == 1
    assert findings[0].code is ManifestErrorCode.REPRODUCIBILITY_REFERENCE_INVALID
    assert "found" not in findings[0].message


def _fixed_corpus() -> dict[str, Any]:
    return {
        "resource": load_json(FIXTURES / "artifact.resource.json"),
        "artifact_manifest": load_json(FIXTURES / "artifact-manifest.json"),
        "reproducibility_manifest": load_json(
            FIXTURES / "reproducibility-manifest.json"
        ),
        "governing_raw": (
            ROOT / "docs/integrity-reproducibility-clarification-v0.1.md"
        ).read_bytes(),
    }


def _reproducibility_context(
    corpus: dict[str, Any],
    schema_store: dict[str, Any],
    active: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    manifest = corpus["reproducibility_manifest"]
    repository_fields = (
        "repository_object_format",
        "repository_commit_sha",
        "repository_tree_sha",
        "release_tag_identity",
        "release_tag_object_sha",
        "release_tag_target_commit_sha",
    )
    return {
        "artifact_manifest": corpus["artifact_manifest"],
        "artifact_documents_by_locator": {RESOURCE_LOCATOR: corpus["resource"]},
        "schema_store": schema_store,
        "active_artifacts": active,
        "governing_document_bytes_by_id": {
            "integrity-reproducibility-clarification": corpus["governing_raw"]
        },
        "governing_document_provenance_by_id": {
            "integrity-reproducibility-clarification": {
                "document_version": "v0.1",
                "frozen_tag_identity": (
                    "integrity-reproducibility-clarification-v0.1"
                ),
            }
        },
        "repository_provenance": {
            field: manifest[field] for field in repository_fields
        },
        "resolved_dependencies": [deepcopy(manifest["dependencies"][0])],
        "trusted_environment": deepcopy(manifest["environment"]),
        "artifact_manifest_external_locator": manifest[
            "artifact_manifest_locator"
        ],
    }


def _confirmatory_repro_case() -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    active = gating_artifact_set()
    acceptance = active["instrument_acceptance"][0]
    acceptance["acceptance_version"] = "0.2.0"
    acceptance["instrument_acceptance_id"] = "acceptance:example-001"
    campaign = active["campaign"][0]
    campaign["instrument_acceptance_reference"] = acceptance[
        "instrument_acceptance_id"
    ]

    manifest = _fixed_corpus()["reproducibility_manifest"]
    manifest["release_phase"] = "CONFIRMATORY"
    manifest["scenario_subset"] = list(campaign["scenario_ids"])
    manifest["control_subset"] = list(campaign["control_condition_ids"])
    manifest["instrument_configuration_id"] = campaign[
        "instrument_configuration_id"
    ]
    manifest["instrument_acceptance_reference"] = acceptance[
        "instrument_acceptance_id"
    ]
    manifest["campaign_id"] = campaign["campaign_id"]
    manifest["capability_evaluation_reference"] = campaign[
        "capability_evaluation_reference"
    ]
    manifest["analysis_configuration_id"] = campaign["analysis_configuration_id"]
    manifest["scheduled_run_ids"] = [
        item["scheduled_run_id"] for item in active["scheduled_run"]
    ]
    manifest["environment"]["environment_reference"] = campaign["environment_id"]
    return manifest, active


def test_public_reproducibility_path_accepts_exact_prospective_reference(
    schema_store: dict[str, Any],
) -> None:
    corpus = _fixed_corpus()
    manifest, active = _confirmatory_repro_case()
    corpus["reproducibility_manifest"] = manifest
    context = _reproducibility_context(corpus, schema_store, active)
    findings = validate_reproducibility_manifest(manifest, **context)
    assert not any(finding.field_path == REFERENCE_PATH for finding in findings)


def test_duplicate_identity_is_wrapped_by_active_graph_validation(
    schema_store: dict[str, Any],
) -> None:
    corpus = _fixed_corpus()
    acceptance = _prospective_documents()["instrument_acceptance"]
    active = {"instrument_acceptance": [acceptance, deepcopy(acceptance)]}
    context = _reproducibility_context(corpus, schema_store, active)
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"],
        **context,
    )
    duplicate_findings = [
        finding
        for finding in findings
        if finding.code is ManifestErrorCode.REPRODUCIBILITY_REFERENCE_INVALID
        and "DUPLICATE_IDENTITY" in finding.message
        and finding.field_path == "/instrument_acceptance_id"
    ]
    assert len(duplicate_findings) == 1


def test_mixed_versions_add_no_release_policy_finding(
    schema_store: dict[str, Any],
) -> None:
    corpus = _fixed_corpus()
    historical = _historical_documents()["instrument_acceptance"]
    prospective = _prospective_documents()["instrument_acceptance"]
    active = {"instrument_acceptance": [historical, prospective]}
    context = _reproducibility_context(corpus, schema_store, active)
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"],
        **context,
    )
    assert not any(
        "MIXED_VERSION" in finding.message
        or "mixed-version" in finding.message.lower()
        for finding in findings
    )


@pytest.mark.parametrize("kind", ["success", "missing", "duplicate"])
def test_repro_acceptance_resolution_is_order_deterministic(
    kind: str,
    schema_store: dict[str, Any],
) -> None:
    acceptance = _prospective_documents()["instrument_acceptance"]
    other = deepcopy(acceptance)
    other["instrument_acceptance_id"] = "acceptance:example-002"
    reference = acceptance["instrument_acceptance_id"]
    candidates = [acceptance, other]
    if kind == "missing":
        reference = "acceptance:missing"
    elif kind == "duplicate":
        other["instrument_acceptance_id"] = reference
    manifest = _acceptance_manifest(acceptance, reference=reference)
    expected = _acceptance_context_findings(manifest, candidates, schema_store)
    for _ in range(4):
        assert _acceptance_context_findings(
            manifest,
            list(reversed(candidates)),
            schema_store,
        ) == expected


def test_artifact_manifest_validation_does_not_mutate_inputs(
    schema_store: dict[str, Any],
) -> None:
    document = _prospective_documents()["derived_action_outcome"]
    manifest = _artifact_manifest("derived_action_outcome", document)
    documents = {manifest["artifacts"][0]["locator"]: document}
    before_manifest = deepcopy(manifest)
    before_documents = deepcopy(documents)
    validate_artifact_manifest(
        manifest,
        artifact_documents_by_locator=documents,
        rejected_bytes_by_locator={},
        schema_store=schema_store,
    )
    assert manifest == before_manifest
    assert documents == before_documents


def test_reproducibility_validation_does_not_mutate_inputs(
    schema_store: dict[str, Any],
) -> None:
    corpus = _fixed_corpus()
    manifest, active = _confirmatory_repro_case()
    corpus["reproducibility_manifest"] = manifest
    context = _reproducibility_context(corpus, schema_store, active)
    before_manifest = deepcopy(manifest)
    before_context = deepcopy(context)
    validate_reproducibility_manifest(manifest, **context)
    assert manifest == before_manifest
    assert context == before_context
