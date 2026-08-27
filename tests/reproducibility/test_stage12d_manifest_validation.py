"""Stage 12D manifest semantic validation and fixed-corpus tests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
from typing import Any

import pytest

from frontier_agent_containment.integrity import (
    canonical_sha256,
    forensic_sha256_bytes,
)
from frontier_agent_containment.manifest_validation import (
    ManifestErrorCode,
    validate_artifact_manifest,
    validate_reproducibility_manifest,
)
from frontier_agent_containment.schema_validation import (
    DuplicateJsonKeyError,
    load_json,
    load_schema_store,
)
from frontier_agent_containment.semantic_validation import (
    ArtifactFamilySpec,
    SUPPORTED_ARTIFACT_FAMILIES,
    get_artifact_family_spec,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/reproducibility/stage12d"
CLARIFICATION = ROOT / "docs/integrity-reproducibility-clarification-v0.1.md"
SCHEMA_NAMES = (
    "common",
    "artifact-manifest",
    "reproducibility-manifest",
    "resource",
    "agent-model-condition",
)
RESOURCE_LOCATOR = "artifacts/artifact.resource.json"
REJECTED_LOCATOR = "rejected/rejected-duplicate-key.raw"
ZERO_DIGEST = "sha256:" + "0" * 64


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    paths = [ROOT / "schemas" / f"{name}.schema.json" for name in SCHEMA_NAMES]
    return load_schema_store(paths)


@pytest.fixture()
def corpus() -> dict[str, Any]:
    return {
        "resource": load_json(FIXTURES / "artifact.resource.json"),
        "artifact_manifest": load_json(FIXTURES / "artifact-manifest.json"),
        "reproducibility_manifest": load_json(
            FIXTURES / "reproducibility-manifest.json"
        ),
        "expected": load_json(FIXTURES / "expected.json"),
        "negative": load_json(FIXTURES / "negative-cases.json"),
        "rejected_raw": (FIXTURES / "rejected-duplicate-key.raw").read_bytes(),
        "governing_raw": CLARIFICATION.read_bytes(),
    }


def artifact_documents(corpus: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {RESOURCE_LOCATOR: corpus["resource"]}


def repository_facts(manifest: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "repository_object_format",
        "repository_commit_sha",
        "repository_tree_sha",
        "release_tag_identity",
        "release_tag_object_sha",
        "release_tag_target_commit_sha",
    )
    return {field: manifest[field] for field in fields}


def reproducibility_context(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> dict[str, Any]:
    manifest = corpus["reproducibility_manifest"]
    return {
        "artifact_manifest": corpus["artifact_manifest"],
        "artifact_documents_by_locator": artifact_documents(corpus),
        "schema_store": schema_store,
        "active_artifacts": None,
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
        "repository_provenance": repository_facts(manifest),
        "resolved_dependencies": [deepcopy(manifest["dependencies"][0])],
        "trusted_environment": deepcopy(manifest["environment"]),
        "artifact_manifest_external_locator": manifest[
            "artifact_manifest_locator"
        ],
    }


def artifact_codes(findings: tuple[Any, ...]) -> set[ManifestErrorCode]:
    return {finding.code for finding in findings}


def validate_artifact(
    manifest: dict[str, Any],
    documents: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
    rejected: dict[str, bytes] | None = None,
) -> tuple[Any, ...]:
    return validate_artifact_manifest(
        manifest,
        artifact_documents_by_locator=documents,
        rejected_bytes_by_locator=rejected or {},
        schema_store=schema_store,
    )


def test_public_family_metadata_covers_exact_supported_set() -> None:
    assert set(SUPPORTED_ARTIFACT_FAMILIES) == {
        family
        for family in SUPPORTED_ARTIFACT_FAMILIES
        if get_artifact_family_spec(family) is SUPPORTED_ARTIFACT_FAMILIES[family]
    }
    assert len(SUPPORTED_ARTIFACT_FAMILIES) == 21


@pytest.mark.parametrize(
    ("family", "identity_field", "version_field", "schema_suffix"),
    [
        ("resource", "resource_id", "resource_version", "resource:0.1.0"),
        ("campaign", "campaign_id", "campaign_version", "campaign:0.1.0"),
        (
            "evidence_event",
            "event_id",
            "event_version",
            "evidence-event:0.1.0",
        ),
    ],
)
def test_public_family_metadata_matches_existing_semantics(
    family: str,
    identity_field: str,
    version_field: str,
    schema_suffix: str,
) -> None:
    spec = get_artifact_family_spec(family)
    assert spec.identity_field == identity_field
    assert spec.version_field == version_field
    assert spec.schema_id.endswith(schema_suffix)


def test_public_family_mapping_and_specs_are_immutable() -> None:
    with pytest.raises(TypeError):
        SUPPORTED_ARTIFACT_FAMILIES["invented"] = ArtifactFamilySpec(  # type: ignore[index]
            "urn:frontier-agent-containment:schema:invented:0.1.0",
            "invented_id",
            "invented_version",
        )
    with pytest.raises(FrozenInstanceError):
        get_artifact_family_spec("resource").schema_id = "changed"  # type: ignore[misc]
    assert get_artifact_family_spec("resource").schema_id.endswith(
        "resource:0.1.0"
    )


def test_unknown_family_lookup_fails_explicitly() -> None:
    with pytest.raises(KeyError):
        get_artifact_family_spec("unknown_artifact_family")


def test_fixed_fixture_constants_have_not_drifted(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    expected = corpus["expected"]
    assert canonical_sha256(corpus["resource"]) == expected[
        "resource_canonical_digest"
    ]
    assert canonical_sha256(corpus["artifact_manifest"]) == expected[
        "artifact_manifest_canonical_digest"
    ]
    resource_schema = schema_store[
        "urn:frontier-agent-containment:schema:resource:0.1.0"
    ]
    assert canonical_sha256(resource_schema) == expected[
        "resource_schema_canonical_digest"
    ]
    common_schema = schema_store[
        "urn:frontier-agent-containment:schema:common:0.1.0"
    ]
    assert canonical_sha256(common_schema) == expected[
        "common_schema_canonical_digest"
    ]
    assert forensic_sha256_bytes(corpus["governing_raw"]) == expected[
        "clarification_exact_byte_document_digest"
    ]
    assert forensic_sha256_bytes(corpus["rejected_raw"]) == expected[
        "rejected_duplicate_key_forensic_digest"
    ]


def test_fixed_valid_artifact_manifest_has_zero_findings(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    findings = validate_artifact(
        corpus["artifact_manifest"], artifact_documents(corpus), schema_store
    )
    assert len(findings) == corpus["expected"]["expected_positive_finding_count"]


def test_structural_validation_precedes_artifact_semantics(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = deepcopy(corpus["artifact_manifest"])
    del manifest["canonicalization_id"]
    findings = validate_artifact(manifest, {}, schema_store)
    assert len(findings) == 1
    assert findings[0].code is ManifestErrorCode.MANIFEST_SCHEMA_INVALID


def test_artifact_content_digest_mismatch_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = deepcopy(corpus["artifact_manifest"])
    manifest["artifacts"][0]["content_digest"] = ZERO_DIGEST
    assert ManifestErrorCode.MANIFEST_DIGEST_MISMATCH in artifact_codes(
        validate_artifact(manifest, artifact_documents(corpus), schema_store)
    )


def test_missing_supplied_artifact_locator_is_incomplete(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    assert ManifestErrorCode.MANIFEST_INCOMPLETE in artifact_codes(
        validate_artifact(corpus["artifact_manifest"], {}, schema_store)
    )


def test_unlisted_supplied_artifact_is_incomplete(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    documents = artifact_documents(corpus)
    documents["artifacts/unlisted.json"] = deepcopy(corpus["resource"])
    assert ManifestErrorCode.MANIFEST_INCOMPLETE in artifact_codes(
        validate_artifact(corpus["artifact_manifest"], documents, schema_store)
    )


def test_duplicate_semantic_artifact_identity_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = deepcopy(corpus["artifact_manifest"])
    duplicate = deepcopy(manifest["artifacts"][0])
    duplicate["locator"] = "artifacts/duplicate.json"
    manifest["artifacts"].append(duplicate)
    documents = artifact_documents(corpus)
    documents[duplicate["locator"]] = deepcopy(corpus["resource"])
    assert ManifestErrorCode.MANIFEST_DUPLICATE_IDENTITY in artifact_codes(
        validate_artifact(manifest, documents, schema_store)
    )


def test_duplicate_locator_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = deepcopy(corpus["artifact_manifest"])
    duplicate = deepcopy(manifest["artifacts"][0])
    duplicate["artifact_id"] = "resource:different"
    manifest["artifacts"].append(duplicate)
    assert ManifestErrorCode.MANIFEST_DUPLICATE_IDENTITY in artifact_codes(
        validate_artifact(manifest, artifact_documents(corpus), schema_store)
    )


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        (
            "artifact_id",
            "resource:wrong",
            ManifestErrorCode.MANIFEST_IDENTITY_MISMATCH,
        ),
        (
            "artifact_version",
            "0.2.0",
            ManifestErrorCode.MANIFEST_VERSION_MISMATCH,
        ),
        (
            "schema_id",
            "urn:frontier-agent-containment:schema:agent-model-condition:0.1.0",
            ManifestErrorCode.MANIFEST_SCHEMA_BINDING_INVALID,
        ),
        (
            "schema_version",
            "0.2.0",
            ManifestErrorCode.MANIFEST_VERSION_MISMATCH,
        ),
    ],
)
def test_artifact_identity_version_and_schema_binding_mismatches(
    field: str,
    value: str,
    code: ManifestErrorCode,
    corpus: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    manifest = deepcopy(corpus["artifact_manifest"])
    manifest["artifacts"][0][field] = value
    assert code in artifact_codes(
        validate_artifact(manifest, artifact_documents(corpus), schema_store)
    )


def test_missing_bound_schema_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    reduced_store = dict(schema_store)
    del reduced_store["urn:frontier-agent-containment:schema:resource:0.1.0"]
    assert ManifestErrorCode.MANIFEST_REFERENCE_INVALID in artifact_codes(
        validate_artifact(
            corpus["artifact_manifest"], artifact_documents(corpus), reduced_store
        )
    )


def test_artifact_failing_bound_schema_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    documents = artifact_documents(corpus)
    documents[RESOURCE_LOCATOR] = deepcopy(corpus["resource"])
    documents[RESOURCE_LOCATOR]["protected"] = "yes"
    assert ManifestErrorCode.MANIFEST_SCHEMA_BINDING_INVALID in artifact_codes(
        validate_artifact(corpus["artifact_manifest"], documents, schema_store)
    )


def rejected_manifest(corpus: dict[str, Any], digest: str) -> dict[str, Any]:
    manifest = deepcopy(corpus["artifact_manifest"])
    manifest["rejected_inputs"] = [
        {
            "rejected_input_id": "rejected:duplicate-key",
            "locator": REJECTED_LOCATOR,
            "rejection_class": "duplicate_key",
            "description": "Strict parsing rejected duplicate object keys.",
            "digest_scope": "FORENSIC_RAW_BYTES",
            "forensic_byte_digest": digest,
            "phase_context": "DEVELOPMENT",
        }
    ]
    return manifest


def test_valid_rejected_input_forensic_digest_is_accepted(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = rejected_manifest(
        corpus, corpus["expected"]["rejected_duplicate_key_forensic_digest"]
    )
    findings = validate_artifact(
        manifest,
        artifact_documents(corpus),
        schema_store,
        {REJECTED_LOCATOR: corpus["rejected_raw"]},
    )
    assert findings == ()


def test_rejected_input_forensic_digest_mismatch_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = rejected_manifest(corpus, ZERO_DIGEST)
    assert ManifestErrorCode.MANIFEST_DIGEST_MISMATCH in artifact_codes(
        validate_artifact(
            manifest,
            artifact_documents(corpus),
            schema_store,
            {REJECTED_LOCATOR: corpus["rejected_raw"]},
        )
    )


def test_duplicate_key_raw_fixture_is_rejected_before_canonical_treatment(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    with pytest.raises(DuplicateJsonKeyError):
        load_json(FIXTURES / "rejected-duplicate-key.raw")
    manifest = rejected_manifest(
        corpus, corpus["expected"]["rejected_duplicate_key_forensic_digest"]
    )
    assert len(manifest["artifacts"]) == 1
    assert "content_digest" not in manifest["rejected_inputs"][0]
    assert validate_artifact(
        manifest,
        artifact_documents(corpus),
        schema_store,
        {REJECTED_LOCATOR: corpus["rejected_raw"]},
    ) == ()


def test_artifact_validation_does_not_mutate_inputs(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = rejected_manifest(
        corpus, corpus["expected"]["rejected_duplicate_key_forensic_digest"]
    )
    documents = artifact_documents(corpus)
    rejected = {REJECTED_LOCATOR: corpus["rejected_raw"]}
    before = deepcopy((manifest, documents, rejected, schema_store))
    validate_artifact(manifest, documents, schema_store, rejected)
    assert (manifest, documents, rejected, schema_store) == before


def test_fixed_valid_reproducibility_manifest_has_zero_findings(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"],
        **reproducibility_context(corpus, schema_store),
    )
    assert len(findings) == corpus["expected"]["expected_positive_finding_count"]


def test_structural_validation_precedes_reproducibility_semantics(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = deepcopy(corpus["reproducibility_manifest"])
    del manifest["repository_commit_sha"]
    context = reproducibility_context(corpus, schema_store)
    context["resolved_dependencies"] = []
    findings = validate_reproducibility_manifest(manifest, **context)
    assert len(findings) == 1
    assert findings[0].code is ManifestErrorCode.MANIFEST_SCHEMA_INVALID


def test_artifact_manifest_digest_mismatch_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = deepcopy(corpus["reproducibility_manifest"])
    manifest["artifact_manifest_digest"] = ZERO_DIGEST
    findings = validate_reproducibility_manifest(
        manifest, **reproducibility_context(corpus, schema_store)
    )
    assert ManifestErrorCode.MANIFEST_DIGEST_MISMATCH in artifact_codes(findings)


def test_external_artifact_manifest_locator_mismatch_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    context = reproducibility_context(corpus, schema_store)
    context["artifact_manifest_external_locator"] = "manifests/other.json"
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    )
    assert ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID in artifact_codes(
        findings
    )


def test_absent_external_artifact_manifest_locator_is_nonfatal_deferred(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    context = reproducibility_context(corpus, schema_store)
    context["artifact_manifest_external_locator"] = None
    assert validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    ) == ()


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("digest", ManifestErrorCode.MANIFEST_DIGEST_MISMATCH),
        ("version", ManifestErrorCode.MANIFEST_VERSION_MISMATCH),
    ],
)
def test_schema_set_digest_and_version_binding(
    mutation: str,
    code: ManifestErrorCode,
    corpus: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    manifest = deepcopy(corpus["reproducibility_manifest"])
    if mutation == "digest":
        manifest["schema_set"][0]["content_digest"] = ZERO_DIGEST
    else:
        manifest["schema_set"][0]["schema_version"] = "0.2.0"
    findings = validate_reproducibility_manifest(
        manifest, **reproducibility_context(corpus, schema_store)
    )
    assert code in artifact_codes(findings)


def test_missing_schema_set_schema_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    context = reproducibility_context(corpus, dict(schema_store))
    del context["schema_store"][
        "urn:frontier-agent-containment:schema:resource:0.1.0"
    ]
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    )
    assert ManifestErrorCode.MANIFEST_REFERENCE_INVALID in artifact_codes(findings)


def test_schema_set_must_cover_artifact_manifest_schema_references(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = deepcopy(corpus["reproducibility_manifest"])
    manifest["schema_set"] = [
        {
            "schema_id": "urn:frontier-agent-containment:schema:common:0.1.0",
            "schema_version": "0.1.0",
            "content_digest": corpus["expected"][
                "common_schema_canonical_digest"
            ],
        }
    ]
    findings = validate_reproducibility_manifest(
        manifest, **reproducibility_context(corpus, schema_store)
    )
    assert ManifestErrorCode.MANIFEST_INCOMPLETE in artifact_codes(findings)


def test_governing_document_exact_byte_digest_mismatch_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = deepcopy(corpus["reproducibility_manifest"])
    manifest["governing_documents"][0]["content_digest"] = ZERO_DIGEST
    findings = validate_reproducibility_manifest(
        manifest, **reproducibility_context(corpus, schema_store)
    )
    assert ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID in artifact_codes(
        findings
    )


def test_missing_governing_document_id_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    context = reproducibility_context(corpus, schema_store)
    context["governing_document_bytes_by_id"] = {}
    context["governing_document_provenance_by_id"] = None
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    )
    assert ManifestErrorCode.REPRODUCIBILITY_REFERENCE_INVALID in artifact_codes(
        findings
    )


@pytest.mark.parametrize("field", ["document_version", "frozen_tag_identity"])
def test_governing_document_trusted_metadata_mismatch_is_rejected(
    field: str,
    corpus: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    context = reproducibility_context(corpus, schema_store)
    context["governing_document_provenance_by_id"][
        "integrity-reproducibility-clarification"
    ][field] = "v9.9" if field == "document_version" else "different-tag-v0.1"
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    )
    assert ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID in artifact_codes(
        findings
    )


@pytest.mark.parametrize(
    "field",
    [
        "repository_commit_sha",
        "repository_tree_sha",
        "release_tag_identity",
        "release_tag_object_sha",
        "release_tag_target_commit_sha",
    ],
)
def test_repository_supplied_fact_mismatch_is_rejected(
    field: str,
    corpus: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    context = reproducibility_context(corpus, schema_store)
    context["repository_provenance"][field] = (
        "different-tag-v0.1" if field == "release_tag_identity" else "f" * 40
    )
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    )
    assert ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID in artifact_codes(
        findings
    )


def test_internal_release_tag_target_commit_must_match_commit(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = deepcopy(corpus["reproducibility_manifest"])
    manifest["release_tag_target_commit_sha"] = "f" * 40
    context = reproducibility_context(corpus, schema_store)
    context["repository_provenance"]["release_tag_target_commit_sha"] = "f" * 40
    findings = validate_reproducibility_manifest(manifest, **context)
    assert ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID in artifact_codes(
        findings
    )


def test_dependency_absent_from_authoritative_set_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    context = reproducibility_context(corpus, schema_store)
    context["resolved_dependencies"] = []
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    )
    assert ManifestErrorCode.REPRODUCIBILITY_DEPENDENCY_INVALID in artifact_codes(
        findings
    )


def test_resolved_dependency_absent_from_manifest_is_incomplete(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    context = reproducibility_context(corpus, schema_store)
    context["resolved_dependencies"].append({"name": "jsonschema", "version": "4.10.3"})
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    )
    assert ManifestErrorCode.MANIFEST_INCOMPLETE in artifact_codes(findings)


def test_dependency_exact_version_mismatch_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    context = reproducibility_context(corpus, schema_store)
    context["resolved_dependencies"][0]["version"] = "0.1.3"
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    )
    assert ManifestErrorCode.REPRODUCIBILITY_DEPENDENCY_INVALID in artifact_codes(
        findings
    )


@pytest.mark.parametrize("trusted_digest", [ZERO_DIGEST, None])
def test_dependency_distribution_digest_requires_matching_trusted_fact(
    trusted_digest: str | None,
    corpus: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    context = reproducibility_context(corpus, schema_store)
    if trusted_digest is None:
        del context["resolved_dependencies"][0]["distribution_digest"]
    else:
        context["resolved_dependencies"][0]["distribution_digest"] = trusted_digest
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    )
    assert ManifestErrorCode.REPRODUCIBILITY_DEPENDENCY_INVALID in artifact_codes(
        findings
    )


def test_optional_manifest_distribution_digest_may_be_omitted(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = deepcopy(corpus["reproducibility_manifest"])
    del manifest["dependencies"][0]["distribution_digest"]
    findings = validate_reproducibility_manifest(
        manifest, **reproducibility_context(corpus, schema_store)
    )
    assert findings == ()


def test_trusted_environment_mismatch_is_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    context = reproducibility_context(corpus, schema_store)
    context["trusted_environment"]["architecture"] = "aarch64"
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    )
    assert ManifestErrorCode.REPRODUCIBILITY_ENVIRONMENT_INVALID in artifact_codes(
        findings
    )


def test_invalid_active_artifact_graph_is_traceable(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    context = reproducibility_context(corpus, schema_store)
    context["active_artifacts"] = {"unknown_artifact_family": [{}]}
    findings = validate_reproducibility_manifest(
        corpus["reproducibility_manifest"], **context
    )
    matching = [
        finding
        for finding in findings
        if finding.code is ManifestErrorCode.REPRODUCIBILITY_REFERENCE_INVALID
        and "UNSUPPORTED_ARTIFACT_FAMILY" in finding.message
    ]
    assert matching


def valid_agent_model_condition() -> dict[str, Any]:
    return {
        "agent_condition_id": "agentcond:stage12d-agent",
        "condition_version": "0.1.0",
        "model_condition_id": "modelcond:stage12d-model",
        "capability_condition_id": "capcond:stage12d-capability",
        "display_name": "Stage 12D synthetic agent condition",
        "description": "Declarative identity fixture only; no model is executed.",
        "model_identifier": "synthetic-model",
        "model_version": "2026.01",
        "provider_runtime_identity": {
            "provider_id": "synthetic_provider",
            "runtime_id": "bounded_runtime",
            "runtime_version": "0.1.0",
            "version_availability": "AVAILABLE",
            "description": "Synthetic declared runtime identity.",
        },
        "inference_configuration": {
            "reasoning_mode": "bounded",
            "temperature": 0,
            "top_p": 1,
            "max_output_tokens": 64,
            "other_parameters": [],
        },
        "context_configuration": {
            "system_context": {
                "context_id": "synthetic_system",
                "context_version": "0.1.0",
            },
            "task_context": {
                "context_id": "synthetic_task",
                "context_version": "0.1.0",
            },
            "maximum_context_tokens": 1024,
            "history_carryover_permitted": False,
            "additional_context_artifacts": [],
        },
        "tool_repertoire": [],
        "planning_configuration": {
            "internal_step_budget": 1,
            "tool_selection_mode": "none",
            "memory_mode": "run_local",
        },
    }


def provider_manifest(corpus: dict[str, Any]) -> dict[str, Any]:
    manifest = deepcopy(corpus["reproducibility_manifest"])
    manifest["model_provider_identities"] = [
        {
            "agent_condition_id": "agentcond:stage12d-agent",
            "model_identifier": "synthetic-model",
            "provider_runtime_identity": {
                "identity_status": "REPORTED",
                "runtime_identifier": "bounded_runtime",
            },
            "version_status": "REPORTED",
            "model_version": "2026.01",
        }
    ]
    return manifest


def test_provider_model_identifier_and_version_mismatches_are_rejected(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    agent = valid_agent_model_condition()
    context = reproducibility_context(corpus, schema_store)
    context["active_artifacts"] = {"agent_model_condition": [agent]}
    for field, value in (("model_identifier", "wrong-model"), ("model_version", "2025.01")):
        manifest = provider_manifest(corpus)
        manifest["model_provider_identities"][0][field] = value
        findings = validate_reproducibility_manifest(manifest, **context)
        assert ManifestErrorCode.REPRODUCIBILITY_PROVIDER_INVALID in artifact_codes(
            findings
        )


@pytest.mark.parametrize("status", ["UNAVAILABLE", "NOT_REPORTED"])
def test_unavailable_provider_version_is_not_fabricated(
    status: str,
    corpus: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    agent = valid_agent_model_condition()
    agent["model_version"] = "UNAVAILABLE"
    manifest = provider_manifest(corpus)
    identity = manifest["model_provider_identities"][0]
    identity["version_status"] = status
    identity.pop("model_version")
    identity["limitation"] = "Provider-controlled version was unavailable."
    context = reproducibility_context(corpus, schema_store)
    context["active_artifacts"] = {"agent_model_condition": [agent]}
    findings = validate_reproducibility_manifest(manifest, **context)
    assert ManifestErrorCode.REPRODUCIBILITY_PROVIDER_INVALID not in artifact_codes(
        findings
    )
    assert "model_version" not in identity


def test_reproducibility_validation_does_not_mutate_any_input(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = corpus["reproducibility_manifest"]
    context = reproducibility_context(corpus, schema_store)
    before_manifest = deepcopy(manifest)
    before_context = deepcopy(context)
    validate_reproducibility_manifest(manifest, **context)
    assert manifest == before_manifest
    assert context == before_context


def _apply_negative_case(
    mutation: str,
    corpus: dict[str, Any],
    schema_store: dict[str, Any],
) -> tuple[Any, ...]:
    artifact_manifest = deepcopy(corpus["artifact_manifest"])
    repro = deepcopy(corpus["reproducibility_manifest"])
    documents = artifact_documents(corpus)
    rejected: dict[str, bytes] = {}
    context = reproducibility_context(corpus, schema_store)
    if mutation == "artifact_digest_mismatch":
        artifact_manifest["artifacts"][0]["content_digest"] = ZERO_DIGEST
    elif mutation == "artifact_id_mismatch":
        artifact_manifest["artifacts"][0]["artifact_id"] = "resource:wrong"
    elif mutation == "artifact_version_mismatch":
        artifact_manifest["artifacts"][0]["artifact_version"] = "0.2.0"
    elif mutation == "schema_id_mismatch":
        artifact_manifest["artifacts"][0]["schema_id"] = (
            "urn:frontier-agent-containment:schema:agent-model-condition:0.1.0"
        )
    elif mutation == "missing_artifact_locator":
        artifact_manifest["artifacts"][0]["locator"] = "artifacts/missing.json"
    elif mutation == "unlisted_supplied_artifact":
        documents["artifacts/unlisted.json"] = deepcopy(corpus["resource"])
    elif mutation == "duplicate_semantic_artifact_identity":
        duplicate = deepcopy(artifact_manifest["artifacts"][0])
        duplicate["locator"] = "artifacts/duplicate.json"
        artifact_manifest["artifacts"].append(duplicate)
        documents[duplicate["locator"]] = deepcopy(corpus["resource"])
    elif mutation == "forensic_digest_mismatch":
        artifact_manifest = rejected_manifest(corpus, ZERO_DIGEST)
        rejected[REJECTED_LOCATOR] = corpus["rejected_raw"]
    elif mutation == "artifact_manifest_digest_mismatch":
        repro["artifact_manifest_digest"] = ZERO_DIGEST
    elif mutation == "schema_digest_mismatch":
        repro["schema_set"][0]["content_digest"] = ZERO_DIGEST
    elif mutation == "missing_schema":
        reduced = dict(schema_store)
        del reduced["urn:frontier-agent-containment:schema:resource:0.1.0"]
        return validate_artifact(artifact_manifest, documents, reduced)
    elif mutation == "dependency_missing_from_manifest":
        context["resolved_dependencies"].append(
            {"name": "jsonschema", "version": "4.10.3"}
        )
    elif mutation == "dependency_missing_from_resolved_set":
        context["resolved_dependencies"] = []
    elif mutation == "dependency_version_mismatch":
        context["resolved_dependencies"][0]["version"] = "0.1.3"
    elif mutation == "repository_commit_mismatch":
        context["repository_provenance"]["repository_commit_sha"] = "f" * 40
    elif mutation == "governing_document_digest_mismatch":
        repro["governing_documents"][0]["content_digest"] = ZERO_DIGEST
    else:
        raise AssertionError(f"unknown declarative mutation: {mutation}")

    artifact_mutations = {
        "artifact_digest_mismatch",
        "artifact_id_mismatch",
        "artifact_version_mismatch",
        "schema_id_mismatch",
        "missing_artifact_locator",
        "unlisted_supplied_artifact",
        "duplicate_semantic_artifact_identity",
        "forensic_digest_mismatch",
    }
    if mutation in artifact_mutations:
        return validate_artifact(
            artifact_manifest, documents, schema_store, rejected
        )
    return validate_reproducibility_manifest(repro, **context)


def test_declarative_negative_corpus(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    cases = corpus["negative"]["cases"]
    assert len(cases) == 16
    assert len({case["case_id"] for case in cases}) == len(cases)
    for case in cases:
        findings = _apply_negative_case(case["mutation"], corpus, schema_store)
        assert ManifestErrorCode(case["expected_code"]) in artifact_codes(findings), (
            case,
            findings,
        )


def test_multi_defect_findings_are_deterministic(
    corpus: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    manifest = deepcopy(corpus["artifact_manifest"])
    entry = manifest["artifacts"][0]
    entry["artifact_id"] = "resource:wrong"
    entry["artifact_version"] = "0.2.0"
    entry["content_digest"] = ZERO_DIGEST
    runs = [
        validate_artifact(manifest, artifact_documents(corpus), schema_store)
        for _ in range(5)
    ]
    assert runs[0]
    assert all(result == runs[0] for result in runs[1:])
    assert [
        (
            finding.code,
            finding.message,
            finding.field_path,
            finding.artifact_id,
            finding.locator,
            finding.referenced_id,
        )
        for finding in runs[0]
    ] == [
        (
            finding.code,
            finding.message,
            finding.field_path,
            finding.artifact_id,
            finding.locator,
            finding.referenced_id,
        )
        for finding in runs[-1]
    ]


def test_manifest_validator_is_local_only_source() -> None:
    source = (
        ROOT / "src/frontier_agent_containment/manifest_validation.py"
    ).read_text(encoding="utf-8")
    prohibited = (
        "import subprocess",
        "from subprocess",
        "import requests",
        "urllib.request",
        "git ",
        "pip ",
        "os.walk",
        "Path(",
        ".open(",
        "write_text(",
        "write_bytes(",
    )
    assert all(token not in source for token in prohibited)
