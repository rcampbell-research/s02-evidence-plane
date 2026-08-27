"""Stage 12E-1 structural tests for release selection and build metadata."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import ValidationError

from frontier_agent_containment.schema_validation import (
    UnknownSchemaReferenceError,
    check_draft_2020_12_schema,
    load_schema_store,
    validate_instance,
)


ROOT = Path(__file__).resolve().parents[2]
DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
RELEASE_PROFILE_ID = (
    "urn:frontier-agent-containment:schema:release-profile:0.1.0"
)
RELEASE_BUILD_RECORD_ID = (
    "urn:frontier-agent-containment:schema:release-build-record:0.1.0"
)
COMMON_ID = "urn:frontier-agent-containment:schema:common:0.1.0"
ARTIFACT_MANIFEST_ID = (
    "urn:frontier-agent-containment:schema:artifact-manifest:0.1.0"
)
REPRODUCIBILITY_MANIFEST_ID = (
    "urn:frontier-agent-containment:schema:reproducibility-manifest:0.1.0"
)
DIGEST = "sha256:" + ("a" * 64)
OS_RUNTIME_IDENTITY = (
    "system-Linux+release-Ubuntu-24.04.3-LTS+"
    "kernel-6.17.0-35-generic+libc-glibc-2.39"
)
PHASE_TOKEN = {
    "DEVELOPMENT": "development",
    "INSTRUMENT_VALIDATION": "instrument-validation",
    "PILOT": "pilot",
    "CONFIRMATORY": "confirmatory",
}
SCHEMA_PATHS = tuple(sorted((ROOT / "schemas").glob("*.schema.json")))


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(SCHEMA_PATHS)


@pytest.fixture(scope="module")
def release_profile_schema(schema_store: dict[str, Any]) -> dict[str, Any]:
    return schema_store[RELEASE_PROFILE_ID]


@pytest.fixture(scope="module")
def release_build_schema(schema_store: dict[str, Any]) -> dict[str, Any]:
    return schema_store[RELEASE_BUILD_RECORD_ID]


def active_artifact() -> dict[str, Any]:
    return {
        "artifact_family": "environment",
        "artifact_id": "env:synthetic-lab",
        "locator": "artifacts/environment.synthetic.json",
        "expected_artifact_version": "0.1.0",
    }


def valid_release_profile(phase: str = "DEVELOPMENT") -> dict[str, Any]:
    token = PHASE_TOKEN[phase]
    scored = phase in {"PILOT", "CONFIRMATORY"}
    return {
        "profile_version": "0.1.0",
        "release_id": f"release:{token}-v0.1",
        "release_phase": phase,
        "source_release_tag_identity": f"research-release-{token}-v0.1",
        "active_artifacts": [active_artifact()] if scored else [],
        "rejected_inputs": [],
        "environment_reference": "env:synthetic-lab" if scored else "NOT_APPLICABLE",
        "governing_profile_version": "release-integrity-profile-v0.1",
        "enabled_dependency_extras": [],
    }


def valid_release_build(
    environment_mode: str = "DEVELOPMENT_TOOLING",
) -> dict[str, Any]:
    token = "pilot" if environment_mode == "CONTROLLED_RUNTIME" else "development"
    controlled = environment_mode == "CONTROLLED_RUNTIME"
    return {
        "build_id": f"build:{token}-v0.1",
        "build_version": "0.1.0",
        "release_id": f"release:{token}-v0.1",
        "python_implementation": "CPython",
        "python_version": "3.12.3",
        "python_build_string": (
            "3.12.3 (main, Apr 9 2024, 09:04:19) [GCC 13.2.0]"
        ),
        "os_system": "Linux",
        "os_release_identity": "Ubuntu-24.04.3-LTS",
        "kernel_release": "6.17.0-35-generic",
        "libc_identity": "glibc-2.39",
        "architecture": "x86_64",
        "os_runtime_identity": OS_RUNTIME_IDENTITY,
        "locale_identity": "C.UTF-8",
        "timezone_identity": "America/New_York",
        "environment_reference": "env:synthetic-lab",
        "environment_mode": environment_mode,
        "system_site_packages_enabled": False if controlled else True,
        "user_site_packages_enabled": False if controlled else True,
        "dependency_scope": "FULL_TRANSITIVE_RUNTIME",
        "dependencies": [
            {
                "name": "rfc8785",
                "version": "0.1.4",
                "distribution_filename": "rfc8785-0.1.4-py3-none-any.whl",
                "distribution_digest": DIGEST,
            }
        ],
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


@pytest.mark.parametrize(
    "schema_id",
    [RELEASE_PROFILE_ID, RELEASE_BUILD_RECORD_ID],
)
def test_stage12e1_schema_is_valid_draft_2020_12(
    schema_id: str,
    schema_store: dict[str, Any],
) -> None:
    schema = schema_store[schema_id]
    assert schema["$schema"] == DRAFT_2020_12
    assert schema["$id"] == schema_id
    check_draft_2020_12_schema(schema, schema_store=schema_store)


@pytest.mark.parametrize("phase", tuple(PHASE_TOKEN))
def test_release_profile_accepts_each_phase(
    phase: str,
    release_profile_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(valid_release_profile(phase), release_profile_schema, schema_store)


def test_release_profile_rejects_malformed_profile_version(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile()
    instance["profile_version"] = "v0.1"
    assert_invalid(instance, release_profile_schema, schema_store)


@pytest.mark.parametrize(
    "release_id",
    ["release:pilot-latest", "release:pilot-v01.1", "pilot-v0.1"],
)
def test_release_profile_rejects_malformed_release_id(
    release_id: str,
    release_profile_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_profile("PILOT")
    instance["release_id"] = release_id
    assert_invalid(instance, release_profile_schema, schema_store)


def test_release_profile_rejects_release_id_for_wrong_phase(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile("PILOT")
    instance["release_id"] = "release:confirmatory-v0.1"
    assert_invalid(instance, release_profile_schema, schema_store)


@pytest.mark.parametrize(
    "tag",
    ["implementation-stage12d-v0.1", "research-release-pilot-latest"],
)
def test_release_profile_rejects_malformed_source_release_tag(
    tag: str,
    release_profile_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_profile("PILOT")
    instance["source_release_tag_identity"] = tag
    assert_invalid(instance, release_profile_schema, schema_store)


def test_release_profile_rejects_source_tag_for_wrong_phase(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile("CONFIRMATORY")
    instance["source_release_tag_identity"] = "research-release-pilot-v0.1"
    assert_invalid(instance, release_profile_schema, schema_store)


def test_release_profile_version_substring_equality_is_semantic_boundary(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile("PILOT")
    instance["source_release_tag_identity"] = "research-release-pilot-v1.7"
    assert_valid(instance, release_profile_schema, schema_store)


@pytest.mark.parametrize(
    "locator",
    ["/tmp/environment.json", "artifacts/../environment.json"],
)
def test_release_profile_rejects_unsafe_active_artifact_locator(
    locator: str,
    release_profile_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_profile("PILOT")
    instance["active_artifacts"][0]["locator"] = locator
    assert_invalid(instance, release_profile_schema, schema_store)


def test_release_profile_rejects_malformed_artifact_id(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile("PILOT")
    instance["active_artifacts"][0]["artifact_id"] = "artifacts/environment.json"
    assert_invalid(instance, release_profile_schema, schema_store)


def test_release_profile_accepts_optional_expected_artifact_version(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    assert_valid(
        valid_release_profile("PILOT"), release_profile_schema, schema_store
    )


def test_release_profile_rejects_malformed_expected_artifact_version(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile("PILOT")
    instance["active_artifacts"][0]["expected_artifact_version"] = "latest"
    assert_invalid(instance, release_profile_schema, schema_store)


def test_release_profile_accepts_minimal_rejected_input_selection(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile()
    instance["rejected_inputs"] = [
        {
            "rejected_input_id": "rejected:duplicate-001",
            "locator": "rejected/duplicate-001.raw",
        }
    ]
    assert_valid(instance, release_profile_schema, schema_store)


def test_release_profile_rejected_selection_cannot_claim_digest(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile()
    instance["rejected_inputs"] = [
        {
            "rejected_input_id": "rejected:duplicate-001",
            "locator": "rejected/duplicate-001.raw",
            "forensic_byte_digest": DIGEST,
        }
    ]
    assert_invalid(instance, release_profile_schema, schema_store)


def test_release_profile_rejects_malformed_environment_reference(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile("PILOT")
    instance["environment_reference"] = "build:synthetic-lab"
    assert_invalid(instance, release_profile_schema, schema_store)


@pytest.mark.parametrize("phase", ["DEVELOPMENT", "INSTRUMENT_VALIDATION"])
def test_nonresearch_profile_may_select_no_environment(
    phase: str,
    release_profile_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_profile(phase)
    assert instance["environment_reference"] == "NOT_APPLICABLE"
    assert_valid(instance, release_profile_schema, schema_store)


@pytest.mark.parametrize("phase", ["PILOT", "CONFIRMATORY"])
def test_scored_profile_requires_environment_identity(
    phase: str,
    release_profile_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_profile(phase)
    instance["environment_reference"] = "NOT_APPLICABLE"
    assert_invalid(instance, release_profile_schema, schema_store)


@pytest.mark.parametrize("phase", ["PILOT", "CONFIRMATORY"])
def test_scored_profile_requires_nonempty_active_artifacts(
    phase: str,
    release_profile_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_profile(phase)
    instance["active_artifacts"] = []
    assert_invalid(instance, release_profile_schema, schema_store)


def test_release_profile_rejects_wrong_governing_profile_version(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile()
    instance["governing_profile_version"] = "release-integrity-profile-v0.2"
    assert_invalid(instance, release_profile_schema, schema_store)


def test_release_profile_accepts_explicit_empty_dependency_extras(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile()
    assert instance["enabled_dependency_extras"] == []
    assert_valid(instance, release_profile_schema, schema_store)


@pytest.mark.parametrize("extra", ["Test Extra", "unsafe/extra", "UPPERCASE"])
def test_release_profile_rejects_malformed_dependency_extra(
    extra: str,
    release_profile_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_profile()
    instance["enabled_dependency_extras"] = [extra]
    assert_invalid(instance, release_profile_schema, schema_store)


@pytest.mark.parametrize("field", ["profile_digest", "self_digest", "unknown"])
def test_release_profile_rejects_unknown_or_self_digest_field(
    field: str,
    release_profile_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_profile()
    instance[field] = DIGEST
    assert_invalid(instance, release_profile_schema, schema_store)


@pytest.mark.parametrize(
    "field", ["profile_version", "release_id", "active_artifacts"]
)
def test_release_profile_rejects_missing_required_field(
    field: str,
    release_profile_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_profile()
    del instance[field]
    assert_invalid(instance, release_profile_schema, schema_store)


def test_release_profile_validation_does_not_mutate_input(
    release_profile_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_profile("CONFIRMATORY")
    original = deepcopy(instance)
    assert_valid(instance, release_profile_schema, schema_store)
    assert instance == original


@pytest.mark.parametrize(
    "mode", ["DEVELOPMENT_TOOLING", "CONTROLLED_RUNTIME"]
)
def test_release_build_accepts_each_environment_mode(
    mode: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(valid_release_build(mode), release_build_schema, schema_store)


@pytest.mark.parametrize(
    "build_id", ["build:pilot-latest", "build:pilot-v01.1", "release:pilot-v0.1"]
)
def test_release_build_rejects_malformed_build_id(
    build_id: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build("CONTROLLED_RUNTIME")
    instance["build_id"] = build_id
    assert_invalid(instance, release_build_schema, schema_store)


def test_release_build_rejects_build_id_for_wrong_phase(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build("CONTROLLED_RUNTIME")
    instance["build_id"] = "build:confirmatory-v0.1"
    assert_invalid(instance, release_build_schema, schema_store)


def test_release_build_version_substring_equality_is_semantic_boundary(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build("CONTROLLED_RUNTIME")
    instance["build_id"] = "build:pilot-v2.4"
    assert_valid(instance, release_build_schema, schema_store)


def test_release_build_rejects_malformed_build_version(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    instance["build_version"] = "v0.1"
    assert_invalid(instance, release_build_schema, schema_store)


def test_release_build_rejects_malformed_release_id(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    instance["release_id"] = "release:development-latest"
    assert_invalid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize("version", [">=3.10", "3.12", "latest", "3.012.3"])
def test_release_build_rejects_nonexact_python_version(
    version: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance["python_version"] = version
    assert_invalid(instance, release_build_schema, schema_store)


def test_release_build_accepts_complete_python_build_string(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    assert_valid(valid_release_build(), release_build_schema, schema_store)


def test_release_build_rejects_control_character_in_python_build_string(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    instance["python_build_string"] = "CPython 3.12.3\nGCC 13.2.0"
    assert_invalid(instance, release_build_schema, schema_store)


def test_release_build_accepts_required_os_runtime_identity(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    assert instance["os_runtime_identity"] == OS_RUNTIME_IDENTITY
    assert_valid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize(
    "identity",
    [
        "system=Linux;release=Ubuntu-24.04.3-LTS",
        "system-Linux+release-Ubuntu 24.04+kernel-6.17+libc-glibc-2.39",
        "system-Linux+release-Ubuntu+extra+kernel-6.17+libc-glibc-2.39",
    ],
)
def test_release_build_rejects_invalid_os_runtime_identity(
    identity: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance["os_runtime_identity"] = identity
    assert_invalid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("os_system", "Lin+ux"),
        ("os_release_identity", "Ubuntu/24.04"),
        ("kernel_release", "6.17 generic"),
        ("libc_identity", "glibc=2.39"),
    ],
)
def test_release_build_rejects_unsafe_os_component(
    field: str,
    value: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance[field] = value
    assert_invalid(instance, release_build_schema, schema_store)


def test_release_build_aggregate_component_equality_is_semantic_boundary(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    instance["os_system"] = "FreeBSD"
    assert_valid(instance, release_build_schema, schema_store)


def test_release_build_rejects_malformed_architecture(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    instance["architecture"] = "x86 64"
    assert_invalid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize("locale", ["C.UTF-8", "en_US.UTF-8"])
def test_release_build_accepts_realistic_locale(
    locale: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance["locale_identity"] = locale
    assert_valid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize("timezone", ["UTC", "America/New_York"])
def test_release_build_accepts_realistic_timezone(
    timezone: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance["timezone_identity"] = timezone
    assert_valid(instance, release_build_schema, schema_store)


def test_release_build_rejects_control_character_in_timezone(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    instance["timezone_identity"] = "America/New_York\nUTC"
    assert_invalid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize(
    "field", ["system_site_packages_enabled", "user_site_packages_enabled"]
)
def test_controlled_runtime_rejects_enabled_site_packages(
    field: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build("CONTROLLED_RUNTIME")
    instance[field] = True
    assert_invalid(instance, release_build_schema, schema_store)


def test_development_tooling_allows_enabled_site_packages(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    assert_valid(valid_release_build(), release_build_schema, schema_store)


def test_release_build_requires_full_transitive_runtime_scope(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    instance["dependency_scope"] = "DIRECT_RUNTIME"
    assert_invalid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize("version", ["4.10.3", "1.0.0rc1", "2026.08"])
def test_release_build_accepts_exact_dependency_version(
    version: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance["dependencies"][0]["version"] = version
    assert_valid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize(
    "version", [">=4.10", "<=4.99", "~=4.10", "^4.10", "*", "latest"]
)
def test_release_build_rejects_dependency_range_or_alias(
    version: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance["dependencies"][0]["version"] = version
    assert_invalid(instance, release_build_schema, schema_store)


def test_release_build_accepts_valid_distribution_digest(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    assert_valid(valid_release_build(), release_build_schema, schema_store)


@pytest.mark.parametrize(
    "digest", ["a" * 64, "sha256:" + ("A" * 64), "sha1:" + ("a" * 40)]
)
def test_release_build_rejects_malformed_distribution_digest(
    digest: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance["dependencies"][0]["distribution_digest"] = digest
    assert_invalid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize(
    "filename",
    [
        "/tmp/rfc8785-0.1.4.whl",
        "../rfc8785-0.1.4.whl",
        "wheels/rfc8785-0.1.4.whl",
        "wheels\\rfc8785-0.1.4.whl",
    ],
)
def test_release_build_rejects_distribution_filename_path(
    filename: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance["dependencies"][0]["distribution_filename"] = filename
    assert_invalid(instance, release_build_schema, schema_store)


def test_release_build_allows_missing_optional_distribution_provenance(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    del instance["dependencies"][0]["distribution_filename"]
    del instance["dependencies"][0]["distribution_digest"]
    assert_valid(instance, release_build_schema, schema_store)


def test_release_build_rejects_empty_dependency_set(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    instance["dependencies"] = []
    assert_invalid(instance, release_build_schema, schema_store)


def test_release_build_rejects_exact_duplicate_dependency_records(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    instance["dependencies"].append(deepcopy(instance["dependencies"][0]))
    assert_invalid(instance, release_build_schema, schema_store)


def test_dependency_name_conflict_detection_is_semantic_boundary(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    second = deepcopy(instance["dependencies"][0])
    second["version"] = "0.1.5"
    instance["dependencies"].append(second)
    assert_valid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize("field", ["build_content_digest", "self_digest"])
def test_release_build_rejects_self_digest_field(
    field: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance[field] = DIGEST
    assert_invalid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize(
    "field",
    [
        "repository_commit_sha",
        "repository_tree_sha",
        "release_tag_object_sha",
    ],
)
def test_release_build_rejects_git_provenance_field(
    field: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance[field] = "a" * 40
    assert_invalid(instance, release_build_schema, schema_store)


@pytest.mark.parametrize(
    "field", ["h1_result", "verdict", "effect_count", "containment_result"]
)
def test_release_build_rejects_scientific_result_field(
    field: str,
    release_build_schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_release_build()
    instance[field] = "PASS"
    assert_invalid(instance, release_build_schema, schema_store)


def test_release_build_rejects_unknown_property(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build()
    instance["unknown"] = True
    assert_invalid(instance, release_build_schema, schema_store)


def test_release_build_accepts_optional_container_identity(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build("CONTROLLED_RUNTIME")
    instance["container_image_identity"] = "registry.invalid/research@sha256:abc"
    assert_valid(instance, release_build_schema, schema_store)


def test_release_build_validation_does_not_mutate_input(
    release_build_schema: dict[str, Any], schema_store: dict[str, Any]
) -> None:
    instance = valid_release_build("CONTROLLED_RUNTIME")
    original = deepcopy(instance)
    assert_valid(instance, release_build_schema, schema_store)
    assert instance == original


def test_stage12e1_refs_reuse_frozen_shared_definitions(
    release_profile_schema: dict[str, Any], release_build_schema: dict[str, Any]
) -> None:
    assert release_profile_schema["properties"]["release_phase"]["$ref"] == (
        f"{COMMON_ID}#/$defs/run_phase"
    )
    assert release_profile_schema["$defs"]["release_id"]["allOf"][0]["$ref"] == (
        f"{COMMON_ID}#/$defs/stable_typed_identifier"
    )
    assert release_build_schema["properties"]["release_id"]["$ref"] == (
        f"{RELEASE_PROFILE_ID}#/$defs/release_id"
    )
    assert release_build_schema["properties"]["environment_reference"]["$ref"] == (
        f"{COMMON_ID}#/$defs/environment_id"
    )
    dependency = release_build_schema["$defs"]["dependency_record"]["properties"]
    assert dependency["name"]["$ref"] == (
        f"{REPRODUCIBILITY_MANIFEST_ID}#/$defs/machine_identifier"
    )
    assert dependency["version"]["$ref"] == (
        f"{REPRODUCIBILITY_MANIFEST_ID}#/$defs/concrete_version"
    )
    assert dependency["distribution_digest"]["$ref"] == (
        f"{REPRODUCIBILITY_MANIFEST_ID}#/$defs/sha256_digest"
    )
    assert release_profile_schema["$defs"]["active_artifact_selection"][
        "properties"
    ]["locator"]["$ref"] == f"{ARTIFACT_MANIFEST_ID}#/$defs/relative_locator"


def test_os_runtime_identity_reuses_frozen_bounded_identity(
    release_build_schema: dict[str, Any],
) -> None:
    assert release_build_schema["$defs"]["os_runtime_identity"]["allOf"][0][
        "$ref"
    ] == f"{REPRODUCIBILITY_MANIFEST_ID}#/$defs/bounded_identity"


def test_all_stage12e1_refs_are_local_fragments_or_project_urns(
    release_profile_schema: dict[str, Any], release_build_schema: dict[str, Any]
) -> None:
    def refs(node: Any) -> list[str]:
        if isinstance(node, dict):
            found = [node["$ref"]] if "$ref" in node else []
            return found + [value for child in node.values() for value in refs(child)]
        if isinstance(node, list):
            return [value for child in node for value in refs(child)]
        return []

    for reference in refs(release_profile_schema) + refs(release_build_schema):
        assert reference.startswith("#") or reference.startswith(
            "urn:frontier-agent-containment:schema:"
        )


def test_local_schema_store_loads_both_stage12e1_contracts(
    schema_store: dict[str, Any],
) -> None:
    assert RELEASE_PROFILE_ID in schema_store
    assert RELEASE_BUILD_RECORD_ID in schema_store


def test_unknown_stage12e1_project_reference_fails_without_network(
    schema_store: dict[str, Any],
) -> None:
    probe = {
        "$schema": DRAFT_2020_12,
        "$id": "urn:frontier-agent-containment:schema:stage12e1-probe:0.1.0",
        "$ref": "urn:frontier-agent-containment:schema:unknown:0.1.0",
    }
    with pytest.raises(UnknownSchemaReferenceError):
        check_draft_2020_12_schema(probe, schema_store=schema_store)
