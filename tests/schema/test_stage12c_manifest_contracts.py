"""Stage 12C structural tests for integrity and reproducibility manifests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import ValidationError

from frontier_agent_containment.schema_validation import (
    DuplicateSchemaIdError,
    SchemaStoreError,
    UnknownSchemaReferenceError,
    check_draft_2020_12_schema,
    load_json,
    load_schema_store,
    validate_instance,
)


ROOT = Path(__file__).resolve().parents[2]
DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_PATHS = {
    path.name.removesuffix(".schema.json"): path
    for path in sorted((ROOT / "schemas").glob("*.schema.json"))
}


def _declared_schema_ids_by_locator(
    schema_paths: dict[str, Path],
) -> dict[str, str]:
    identities: dict[str, str] = {}
    locators_by_identity: dict[str, str] = {}
    for locator, path in schema_paths.items():
        document = load_json(path)
        if not isinstance(document, dict):
            raise SchemaStoreError(f"schema document is not an object: {path}")
        schema_id = document.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise SchemaStoreError(f"schema from {path} lacks a nonempty string $id")
        if schema_id in locators_by_identity:
            previous = locators_by_identity[schema_id]
            raise DuplicateSchemaIdError(
                f"duplicate schema $id {schema_id!r} declared by locators "
                f"{previous!r} and {locator!r}"
            )
        identities[locator] = schema_id
        locators_by_identity[schema_id] = locator
    return identities


SCHEMA_IDS = _declared_schema_ids_by_locator(SCHEMA_PATHS)
STAGE12C_SCHEMAS = ["artifact-manifest", "reproducibility-manifest"]
DIGEST_A = "sha256:" + ("a" * 64)
DIGEST_B = "sha256:" + ("b" * 64)
DIGEST_C = "sha256:" + ("c" * 64)
GIT_A = "a" * 40
GIT_B = "b" * 40
GIT_C = "c" * 40


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(SCHEMA_PATHS.values())


@pytest.fixture(scope="module")
def schemas(schema_store: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        name: schema_store[schema_id]
        for name, schema_id in SCHEMA_IDS.items()
    }


def _write_minimal_schema(path: Path, schema_id: str) -> None:
    path.write_text(
        json.dumps(
            {
                "$schema": DRAFT_2020_12,
                "$id": schema_id,
                "type": "object",
                "additionalProperties": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_all_schema_discovery_uses_unique_declared_ids(
    schema_store: dict[str, Any],
) -> None:
    assert len(SCHEMA_PATHS) == len(SCHEMA_IDS) == len(schema_store)
    assert set(SCHEMA_IDS.values()) == set(schema_store)
    for locator, path in SCHEMA_PATHS.items():
        document = load_json(path)
        assert isinstance(document, dict)
        assert SCHEMA_IDS[locator] == document["$id"]


def test_version_qualified_schema_locator_uses_declared_id(tmp_path: Path) -> None:
    locator = "instrument-acceptance-v0.2.0"
    path = tmp_path / f"{locator}.schema.json"
    declared_id = (
        "urn:frontier-agent-containment:schema:instrument-acceptance:0.2.0"
    )
    filename_derived_id = (
        "urn:frontier-agent-containment:schema:"
        "instrument-acceptance-v0.2.0:0.1.0"
    )
    _write_minimal_schema(path, declared_id)

    identities = _declared_schema_ids_by_locator({locator: path})
    store = load_schema_store([path])

    assert identities == {locator: declared_id}
    assert set(store) == {declared_id}
    assert filename_derived_id not in identities.values()


def test_schema_discovery_rejects_duplicate_declared_ids(tmp_path: Path) -> None:
    schema_id = "urn:frontier-agent-containment:schema:duplicate-probe:0.1.0"
    first = tmp_path / "first.schema.json"
    second = tmp_path / "second.schema.json"
    _write_minimal_schema(first, schema_id)
    _write_minimal_schema(second, schema_id)

    with pytest.raises(DuplicateSchemaIdError, match="duplicate schema \\$id"):
        _declared_schema_ids_by_locator({"first": first, "second": second})


def valid_artifact_entry() -> dict[str, Any]:
    return {
        "artifact_family": "scenario",
        "artifact_id": "scenario:synthetic-001",
        "artifact_version": "0.1.0",
        "locator": "scenarios/synthetic-001.json",
        "schema_id": "urn:frontier-agent-containment:schema:scenario:0.1.0",
        "schema_version": "0.1.0",
        "lifecycle_state": "FROZEN",
        "phase_context": "PILOT",
        "content_digest": DIGEST_A,
    }


def valid_artifact_manifest(scope_type: str = "RELEASE") -> dict[str, Any]:
    scopes: dict[str, dict[str, Any]] = {
        "RELEASE": {"scope_type": "RELEASE"},
        "CAMPAIGN": {
            "scope_type": "CAMPAIGN",
            "experiment_id": "exp:containment-study",
            "campaign_id": "campaign:pilot-001",
        },
        "RUN": {
            "scope_type": "RUN",
            "experiment_id": "exp:containment-study",
            "run_id": "run:pilot-001",
        },
    }
    return {
        "manifest_version": "0.1.0",
        "scope": scopes[scope_type],
        "canonicalization_id": "RFC8785-JCS",
        "digest_algorithm": "SHA-256",
        "artifacts": [valid_artifact_entry()],
        "rejected_inputs": [],
    }


def valid_rejected_input() -> dict[str, Any]:
    return {
        "rejected_input_id": "rejected:duplicate-001",
        "locator": "rejected/duplicate-001.json",
        "rejection_class": "duplicate_key",
        "description": "Strict parsing rejected an ambiguous duplicate object key.",
        "digest_scope": "FORENSIC_RAW_BYTES",
        "forensic_byte_digest": DIGEST_B,
        "phase_context": "INSTRUMENT_VALIDATION",
    }


def valid_model_provider_identity(
    version_status: str = "REPORTED",
) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "agent_condition_id": "agentcond:baseline",
        "model_identifier": "frontier-model",
        "provider_runtime_identity": {
            "identity_status": "REPORTED",
            "runtime_identifier": "provider-runtime-2026",
        },
        "version_status": version_status,
    }
    if version_status == "REPORTED":
        identity["model_version"] = "2026.08"
    else:
        identity["limitation"] = "The provider did not expose an exact model version."
    return identity


def valid_reproducibility_manifest(
    phase: str = "DEVELOPMENT",
) -> dict[str, Any]:
    scored_phase = phase in {"PILOT", "CONFIRMATORY"}
    confirmatory = phase == "CONFIRMATORY"
    return {
        "reproducibility_version": "0.1.0",
        "release_phase": phase,
        "repository_object_format": "SHA-1",
        "repository_commit_sha": GIT_A,
        "repository_tree_sha": GIT_B,
        "release_tag_identity": f"stage12c-{phase.lower()}-v0.1",
        "release_tag_object_sha": GIT_C,
        "release_tag_target_commit_sha": GIT_A,
        "artifact_manifest_locator": "manifests/artifact-manifest.json",
        "artifact_manifest_digest": DIGEST_A,
        "governing_documents": [
            {
                "document_id": "integrity-reproducibility-spec",
                "document_version": "v0.1",
                "frozen_tag_identity": "integrity-reproducibility-spec-v0.1",
                "content_digest": DIGEST_B,
            }
        ],
        "schema_set": [
            {
                "schema_id": (
                    "urn:frontier-agent-containment:schema:common:0.1.0"
                ),
                "schema_version": "0.1.0",
                "content_digest": DIGEST_C,
            }
        ],
        "environment": {
            "python_version": "3.12.3",
            "os_runtime_identity": "linux-6.8",
            "architecture": "x86_64",
            "environment_reference": "env:synthetic-lab",
            "build_identity": "build:research-environment-001",
            "environment_content_digest": DIGEST_A,
            "build_content_digest": DIGEST_B,
        },
        "dependencies": [
            {
                "name": "jsonschema",
                "version": "4.10.3",
                "distribution_digest": DIGEST_C,
            }
        ],
        "scenario_subset": ["scenario:synthetic-001"] if scored_phase else [],
        "control_subset": ["ctrlcond:m3-primary"] if scored_phase else [],
        "instrument_configuration_id": "instrument:validated-baseline",
        "instrument_acceptance_reference": (
            "acceptance:confirmatory-001"
            if scored_phase
            else "NOT_APPLICABLE"
        ),
        "capability_evaluation_reference": (
            "cond:capability-evaluation-baseline"
            if confirmatory
            else "NOT_APPLICABLE"
        ),
        "analysis_configuration_id": (
            "analysis:confirmatory-primary" if confirmatory else "NOT_APPLICABLE"
        ),
        "campaign_id": "campaign:scored-001" if scored_phase else "NOT_APPLICABLE",
        "scheduled_run_ids": (
            ["scheduledrun:unit-001"] if scored_phase else []
        ),
        "run_ids": ["run:unit-001"] if scored_phase else [],
        "repetition_identities": (
            [
                {
                    "scheduled_run_id": "scheduledrun:unit-001",
                    "run_id": "run:unit-001",
                    "repetition_id": "rep_001",
                    "seed_status": "AVAILABLE",
                    "seed_value": 42,
                }
            ]
            if scored_phase
            else []
        ),
        "model_provider_identities": [valid_model_provider_identity()],
        "reproducibility_limitations": [],
    }


def assert_valid(
    instance: dict[str, Any],
    schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    validate_instance(instance, schema, schema_store=schema_store)


def assert_invalid(
    instance: dict[str, Any],
    schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        validate_instance(instance, schema, schema_store=schema_store)


@pytest.mark.parametrize("schema_name", STAGE12C_SCHEMAS)
def test_stage12c_schema_is_valid_draft_2020_12(
    schema_name: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    schema = schemas[schema_name]
    assert schema["$schema"] == DRAFT_2020_12
    assert schema["$id"] == SCHEMA_IDS[schema_name]
    check_draft_2020_12_schema(schema, schema_store=schema_store)


@pytest.mark.parametrize("scope_type", ["RELEASE", "CAMPAIGN", "RUN"])
def test_artifact_manifest_accepts_each_scope(
    scope_type: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(
        valid_artifact_manifest(scope_type),
        schemas["artifact-manifest"],
        schema_store,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("manifest_version", "v0.1"),
        ("canonicalization_id", "JSON-SORTED"),
        ("digest_algorithm", "SHA-512"),
    ],
)
def test_artifact_manifest_rejects_invalid_root_constant_or_version(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_artifact_manifest()
    instance[field] = value
    assert_invalid(instance, schemas["artifact-manifest"], schema_store)


@pytest.mark.parametrize(
    "digest",
    ["a" * 64, "sha256:" + ("A" * 64), "sha1:" + ("a" * 40)],
    ids=["bare", "uppercase", "sha1"],
)
def test_artifact_manifest_rejects_malformed_content_digest(
    digest: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_artifact_manifest()
    instance["artifacts"][0]["content_digest"] = digest
    assert_invalid(instance, schemas["artifact-manifest"], schema_store)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("artifact_id", "scenarios/synthetic-001.json"),
        ("artifact_version", "latest"),
        ("lifecycle_state", "IMMUTABLE"),
        ("phase_context", "PUBLICATION"),
    ],
)
def test_artifact_entry_rejects_invalid_identity_version_or_state(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_artifact_manifest()
    instance["artifacts"][0][field] = value
    assert_invalid(instance, schemas["artifact-manifest"], schema_store)


@pytest.mark.parametrize(
    "locator",
    ["/tmp/artifact.json", "../artifact.json", "safe/../artifact.json", "C:\\artifact.json"],
    ids=["absolute", "parent", "nested-parent", "windows-absolute"],
)
def test_artifact_entry_rejects_unsafe_locator(
    locator: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_artifact_manifest()
    instance["artifacts"][0]["locator"] = locator
    assert_invalid(instance, schemas["artifact-manifest"], schema_store)


def test_rejected_input_with_forensic_digest_is_accepted(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_artifact_manifest()
    instance["rejected_inputs"] = [valid_rejected_input()]
    assert_valid(instance, schemas["artifact-manifest"], schema_store)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("content_digest", DIGEST_A),
        ("canonicalization_id", "RFC8785-JCS"),
        ("schema_version", "0.1.0"),
    ],
)
def test_rejected_input_cannot_claim_canonical_artifact_status(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_artifact_manifest()
    rejected = valid_rejected_input()
    rejected[field] = value
    instance["rejected_inputs"] = [rejected]
    assert_invalid(instance, schemas["artifact-manifest"], schema_store)


def test_rejected_input_rejects_malformed_forensic_digest(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_artifact_manifest()
    rejected = valid_rejected_input()
    rejected["forensic_byte_digest"] = "sha256:1234"
    instance["rejected_inputs"] = [rejected]
    assert_invalid(instance, schemas["artifact-manifest"], schema_store)


@pytest.mark.parametrize("field", ["manifest_digest", "self_digest"])
def test_artifact_manifest_rejects_self_digest_field(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_artifact_manifest()
    instance[field] = DIGEST_A
    assert_invalid(instance, schemas["artifact-manifest"], schema_store)


def test_artifact_manifest_rejects_unknown_property(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_artifact_manifest()
    instance["proof_of_truth"] = True
    assert_invalid(instance, schemas["artifact-manifest"], schema_store)


@pytest.mark.parametrize("field", ["manifest_version", "scope", "artifacts"])
def test_artifact_manifest_rejects_missing_required_property(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_artifact_manifest()
    del instance[field]
    assert_invalid(instance, schemas["artifact-manifest"], schema_store)


def test_artifact_manifest_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_artifact_manifest("RUN")
    original = deepcopy(instance)
    assert_valid(instance, schemas["artifact-manifest"], schema_store)
    assert instance == original


def test_locator_and_artifact_identity_remain_separate(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    first = valid_artifact_manifest()
    second = deepcopy(first)
    second["artifacts"][0]["locator"] = "archive/moved-synthetic-001.json"
    assert first["artifacts"][0]["artifact_id"] == second["artifacts"][0]["artifact_id"]
    assert first["artifacts"][0]["content_digest"] == second["artifacts"][0]["content_digest"]
    assert_valid(first, schemas["artifact-manifest"], schema_store)
    assert_valid(second, schemas["artifact-manifest"], schema_store)


def test_typed_identifier_is_not_a_locator(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_artifact_manifest()
    instance["artifacts"][0]["locator"] = "scenario:synthetic-001"
    assert_invalid(instance, schemas["artifact-manifest"], schema_store)


@pytest.mark.parametrize(
    "phase", ["DEVELOPMENT", "INSTRUMENT_VALIDATION", "PILOT", "CONFIRMATORY"]
)
def test_reproducibility_manifest_accepts_each_release_phase(
    phase: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(
        valid_reproducibility_manifest(phase),
        schemas["reproducibility-manifest"],
        schema_store,
    )


@pytest.mark.parametrize(
    "sha",
    ["a" * 39, "a" * 41, "A" * 40, "sha1:" + ("a" * 40)],
    ids=["short", "long", "uppercase", "prefixed"],
)
def test_reproducibility_manifest_rejects_malformed_git_sha(
    sha: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_reproducibility_manifest()
    instance["repository_commit_sha"] = sha
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


def test_reproducibility_manifest_accepts_sha256_git_object_ids(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest()
    instance["repository_object_format"] = "SHA-256"
    for field, character in (
        ("repository_commit_sha", "a"),
        ("repository_tree_sha", "b"),
        ("release_tag_object_sha", "c"),
        ("release_tag_target_commit_sha", "a"),
    ):
        instance[field] = character * 64
    assert_valid(instance, schemas["reproducibility-manifest"], schema_store)


def test_reproducibility_manifest_rejects_latest_release_tag(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest()
    instance["release_tag_identity"] = "latest"
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


def test_reproducibility_manifest_rejects_malformed_artifact_manifest_digest(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest()
    instance["artifact_manifest_digest"] = "sha256:" + ("A" * 64)
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


def test_reproducibility_manifest_rejects_empty_schema_set(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest()
    instance["schema_set"] = []
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


def test_reproducibility_manifest_rejects_malformed_schema_digest(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest()
    instance["schema_set"][0]["content_digest"] = "sha256:1234"
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


@pytest.mark.parametrize("version", ["4.10.3", "1.0.0rc1", "2026.08"])
def test_dependency_exact_version_is_accepted(
    version: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_reproducibility_manifest()
    instance["dependencies"][0]["version"] = version
    assert_valid(instance, schemas["reproducibility-manifest"], schema_store)


@pytest.mark.parametrize(
    "version", [">=4.10", "<=4.10", "~=4.10", "^4.10", "4.*", "latest", "current"]
)
def test_dependency_open_range_or_alias_is_rejected(
    version: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_reproducibility_manifest()
    instance["dependencies"][0]["version"] = version
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scenario_subset", ["scenario-file.json"]),
        ("control_subset", ["control:m3-primary"]),
    ],
)
def test_reproducibility_manifest_rejects_wrong_subset_identity_type(
    field: str,
    value: list[str],
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_reproducibility_manifest("PILOT")
    instance[field] = value
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("analysis_configuration_id", "NOT_APPLICABLE"),
        ("capability_evaluation_reference", "NOT_APPLICABLE"),
        ("instrument_acceptance_reference", "NOT_APPLICABLE"),
    ],
)
def test_confirmatory_manifest_requires_frozen_gate_references(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_reproducibility_manifest("CONFIRMATORY")
    instance[field] = value
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


@pytest.mark.parametrize("field", ["scenario_subset", "control_subset"])
def test_confirmatory_manifest_requires_nonempty_design_subsets(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_reproducibility_manifest("CONFIRMATORY")
    instance[field] = []
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


def test_pilot_manifest_requires_acceptance_reference(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest("PILOT")
    instance["instrument_acceptance_reference"] = "NOT_APPLICABLE"
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


def test_pilot_does_not_require_confirmatory_analysis_configuration(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest("PILOT")
    assert instance["analysis_configuration_id"] == "NOT_APPLICABLE"
    assert_valid(instance, schemas["reproducibility-manifest"], schema_store)


def test_reported_model_version_is_required(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest()
    del instance["model_provider_identities"][0]["model_version"]
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


@pytest.mark.parametrize("version", ["UNAVAILABLE", "NOT_REPORTED"])
def test_reported_model_version_rejects_unavailable_status_label(
    version: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_reproducibility_manifest()
    instance["model_provider_identities"][0]["model_version"] = version
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


@pytest.mark.parametrize("status", ["UNAVAILABLE", "NOT_REPORTED"])
def test_unavailable_model_version_does_not_require_fabrication(
    status: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_reproducibility_manifest()
    instance["model_provider_identities"] = [valid_model_provider_identity(status)]
    assert_valid(instance, schemas["reproducibility-manifest"], schema_store)


@pytest.mark.parametrize("status", ["UNAVAILABLE", "NOT_REPORTED"])
def test_unavailable_model_version_rejects_fabricated_value(
    status: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_reproducibility_manifest()
    identity = valid_model_provider_identity(status)
    identity["model_version"] = "fabricated-1"
    instance["model_provider_identities"] = [identity]
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


def test_unavailable_seed_does_not_require_fabricated_value(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest("PILOT")
    identity = instance["repetition_identities"][0]
    identity["seed_status"] = "UNAVAILABLE"
    del identity["seed_value"]
    assert_valid(instance, schemas["reproducibility-manifest"], schema_store)


def test_unavailable_seed_rejects_fabricated_value(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest("PILOT")
    instance["repetition_identities"][0]["seed_status"] = "UNAVAILABLE"
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


@pytest.mark.parametrize(
    "field", ["reproducibility_manifest_digest", "self_digest"]
)
def test_reproducibility_manifest_rejects_self_digest_field(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_reproducibility_manifest()
    instance[field] = DIGEST_A
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("api_key", "secret"),
        ("statistical_result", {"risk_difference": -0.2}),
        ("proof_of_reproducibility", True),
    ],
)
def test_reproducibility_manifest_rejects_unknown_or_prohibited_property(
    field: str,
    value: Any,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_reproducibility_manifest()
    instance[field] = value
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


def test_reproducibility_manifest_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest("CONFIRMATORY")
    original = deepcopy(instance)
    assert_valid(instance, schemas["reproducibility-manifest"], schema_store)
    assert instance == original


def test_artifact_manifest_locator_rejects_typed_identity(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_reproducibility_manifest()
    instance["artifact_manifest_locator"] = "artifactmanifest:release-001"
    assert_invalid(instance, schemas["reproducibility-manifest"], schema_store)


def test_stage12c_refs_match_frozen_shared_definitions(
    schemas: dict[str, dict[str, Any]],
) -> None:
    artifact_defs = schemas["artifact-manifest"]["$defs"]
    reproducibility = schemas["reproducibility-manifest"]
    assert artifact_defs["artifact_entry"]["properties"]["artifact_id"]["$ref"].endswith(
        "#/$defs/stable_typed_identifier"
    )
    assert artifact_defs["artifact_entry"]["properties"]["lifecycle_state"]["$ref"].endswith(
        "#/$defs/artifact_lifecycle_state"
    )
    assert reproducibility["properties"]["release_phase"]["$ref"].endswith(
        "#/$defs/run_phase"
    )
    assert reproducibility["properties"]["scenario_subset"]["items"]["$ref"].endswith(
        "#/$defs/scenario_id"
    )
    assert reproducibility["properties"]["control_subset"]["items"]["$ref"].endswith(
        "#/$defs/control_condition_id"
    )
    assert reproducibility["properties"]["instrument_configuration_id"]["$ref"].endswith(
        "#/$defs/instrument_configuration_id"
    )
    assert reproducibility["$defs"]["model_provider_identity"]["properties"]["agent_condition_id"]["$ref"].endswith(
        "#/$defs/agent_condition_id"
    )


def test_unknown_project_schema_reference_fails_without_network(
    schema_store: dict[str, Any],
) -> None:
    schema = {
        "$schema": DRAFT_2020_12,
        "$id": "urn:frontier-agent-containment:schema:stage12c-probe:0.1.0",
        "$ref": "urn:frontier-agent-containment:schema:unknown:0.1.0",
    }
    with pytest.raises(UnknownSchemaReferenceError):
        check_draft_2020_12_schema(schema, schema_store=schema_store)
