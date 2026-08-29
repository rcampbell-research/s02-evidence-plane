from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, fields
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

import frontier_agent_containment.release_assembly as release_assembly
from frontier_agent_containment.integrity import (
    canonical_sha256,
    forensic_sha256_bytes,
)
from frontier_agent_containment.manifest_validation import (
    validate_artifact_manifest,
    validate_reproducibility_manifest,
)
from frontier_agent_containment.release_acquisition import (
    AcquiredGoverningDocument,
    DistributionArtifactProvenance,
    GitProvenance,
    GoverningDocumentAcquisition,
    GoverningDocumentProvenance,
    GOVERNING_DOCUMENT_REGISTRY_V0_1,
    ResolvedDependency,
    RuntimeDependencyClosure,
    RuntimeEnvironmentFacts,
    validate_release_build_consistency,
)
from frontier_agent_containment.release_assembly import (
    ArtifactAssemblyMetadata,
    BuiltResearchRelease,
    PhaseProjection,
    RejectedInputAssemblyMetadata,
    ReleaseAssemblyError,
    ReleaseAssemblyErrorCode,
    RepetitionIdentity,
    build_research_release,
    write_research_release,
)
from frontier_agent_containment.release_validation import (
    validate_release_artifact_version_gates,
)
from frontier_agent_containment.schema_validation import load_schema_store
from frontier_agent_containment.semantic_validation import (
    get_artifact_family_contract_spec,
    get_artifact_family_spec,
)
from tests.semantic.test_stage10_confirmatory_gating import gating_artifact_set


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
ZERO_DIGEST = "sha256:" + "0" * 64


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(sorted(SCHEMAS.glob("*.json")))


def environment() -> dict[str, Any]:
    return {
        "environment_id": "env:synthetic-lab",
        "environment_version": "0.1.0",
        "build_id": "build:synthetic-lab-001",
        "display_name": "Synthetic laboratory",
        "description": "Fictional environment entirely inside S0.",
        "trust_zones": [
            {"zone_id": "Z1", "description": "Workspace.", "agent_accessible": True},
            {"zone_id": "Z3", "description": "Protected.", "agent_accessible": False},
            {"zone_id": "Z6", "description": "Sink.", "agent_accessible": False},
        ],
        "synthetic_assets": [],
        "network_relationships": [
            {
                "source_zone": "Z1",
                "destination_zone": "Z6",
                "relationship": "SERVICE_ACCESS",
                "authorized": True,
            }
        ],
        "s0_configuration_id": "cond:s0-baseline",
        "reset_baseline_id": "cond:reset-baseline",
        "expected_observers": [
            {
                "observer_id": "resource_observer",
                "observed_property": "resource_access",
                "trust_zone": "Z3",
            }
        ],
        "controlled_endpoints": [
            {
                "endpoint_id": "synthetic_sink",
                "zone_id": "Z6",
                "purpose": "Controlled synthetic receipt.",
            }
        ],
        "forbidden_external_relationships": [
            "UNRESTRICTED_INTERNET",
            "REAL_CREDENTIAL_SOURCE",
            "PRODUCTION_SYSTEM",
            "HOST_ADMINISTRATION",
            "THIRD_PARTY_TARGET",
        ],
    }


def instrument() -> dict[str, Any]:
    return {
        "instrument_configuration_id": "instrument:baseline",
        "configuration_version": "0.1.0",
        "display_name": "Synthetic instrument",
        "description": "Exact declarative instrument configuration.",
        "environment_id": "env:synthetic-lab",
        "component_manifest": [
            {
                "component_id": "orchestrator",
                "component_role": "experiment_orchestrator",
                "component_version": "0.1.0",
                "dependency_component_ids": [],
            },
            {
                "component_id": "resource_observer",
                "component_role": "resource_service_observer",
                "component_version": "0.1.0",
                "dependency_component_ids": ["orchestrator"],
            },
            {
                "component_id": "evidence_collector",
                "component_role": "evidence_collector",
                "component_version": "0.1.0",
                "dependency_component_ids": ["resource_observer"],
            },
        ],
        "observer_configuration": [
            {
                "observer_id": "synthetic_resource_observer",
                "observed_property": "Synthetic resource effects.",
                "authoritative_role": "RESOURCE_SERVICE_OBSERVER",
                "component_id": "resource_observer",
            }
        ],
        "evidence_pipeline_configuration": {
            "collector_component_id": "evidence_collector",
            "normalized_evidence_destination_id": "normalized_store",
            "ordering_mechanism_id": "sequence_order",
            "evidence_format_schema_id": (
                "urn:frontier-agent-containment:schema:evidence-event:0.1.0"
            ),
            "evidence_format_version": "0.1.0",
        },
        "orchestration_configuration": {
            "orchestration_component_id": "orchestrator",
            "run_initialization_responsibility": "Initialize frozen run state.",
            "termination_responsibility": "Record termination.",
            "action_budget_enforcement_responsibility": "Enforce declared budget.",
        },
        "reset_configuration": {
            "reset_configuration_id": "synthetic_reset",
            "reset_baseline_reference": "baseline_snapshot",
            "reset_component_id": "orchestrator",
            "description": "Restore the synthetic baseline.",
        },
        "s0_configuration_reference": {
            "configuration_id": "cond:s0-baseline",
            "configuration_version": "0.1.0",
            "description": "Separate S0 configuration.",
        },
        "schema_contract_set": [
            {
                "schema_id": "urn:frontier-agent-containment:schema:evidence-event:0.1.0",
                "schema_version": "0.1.0",
            }
        ],
        "configuration_state": "FROZEN",
    }


def profile(*, rejected: bool = False) -> dict[str, Any]:
    result = {
        "profile_version": "0.1.0",
        "release_id": "release:development-v0.1",
        "release_phase": "DEVELOPMENT",
        "source_release_tag_identity": "research-release-development-v0.1",
        "active_artifacts": [
            {
                "artifact_family": "instrument_configuration",
                "artifact_id": "instrument:baseline",
                "locator": "scientific/instrument.json",
                "expected_artifact_version": "0.1.0",
            },
            {
                "artifact_family": "environment",
                "artifact_id": "env:synthetic-lab",
                "locator": "scientific/environment.json",
            },
        ],
        "rejected_inputs": [],
        "environment_reference": "env:synthetic-lab",
        "governing_profile_version": "release-integrity-profile-v0.1",
        "enabled_dependency_extras": [],
    }
    if rejected:
        result["rejected_inputs"] = [
            {
                "rejected_input_id": "rejected:duplicate-key",
                "locator": "rejected/duplicate-key.raw",
            }
        ]
    return result


def git_provenance() -> GitProvenance:
    return GitProvenance(
        repository_object_format="SHA-1",
        repository_commit_sha="1" * 40,
        repository_tree_sha="2" * 40,
        release_tag_identity="research-release-development-v0.1",
        release_tag_object_sha="3" * 40,
        release_tag_target_commit_sha="1" * 40,
        repository_clean=True,
    )


def governing_documents() -> GoverningDocumentAcquisition:
    documents = []
    for index, registry in enumerate(GOVERNING_DOCUMENT_REGISTRY_V0_1):
        exact_bytes = f"frozen {registry.document_id}\n".encode()
        documents.append(
            AcquiredGoverningDocument(
                exact_bytes=exact_bytes,
                provenance=GoverningDocumentProvenance(
                    document_id=registry.document_id,
                    document_version=registry.document_version,
                    frozen_tag_identity=registry.frozen_tag_identity,
                    frozen_tag_object_sha=f"{index + 4:x}" * 40,
                    frozen_tag_target_commit_sha="1" * 40,
                    exact_byte_content_digest=forensic_sha256_bytes(exact_bytes),
                ),
            )
        )
    return GoverningDocumentAcquisition(tuple(documents))


def dependency_closure(*, provenance: bool = True) -> RuntimeDependencyClosure:
    distribution = None
    if provenance:
        distribution = DistributionArtifactProvenance(
            distribution_filename="rfc8785-0.1.4-py3-none-any.whl",
            distribution_digest=forensic_sha256_bytes(b"wheel"),
            source="test fixture",
        )
    return RuntimeDependencyClosure(
        dependencies=(
            ResolvedDependency(
                name="rfc8785",
                version="0.1.4",
                requires_dist=(),
                provides_extra=(),
                distribution_provenance=distribution,
            ),
        ),
        findings=(),
    )


def runtime_facts(
    *, mode: str = "DEVELOPMENT_TOOLING"
) -> RuntimeEnvironmentFacts:
    return RuntimeEnvironmentFacts(
        python_executable="/not/released/python",
        venv_root="/not/released/venv",
        python_implementation="CPython",
        python_version="3.12.3",
        python_build_string="main Aug 1 2026",
        os_system="Linux",
        os_release_identity="Ubuntu_24.04",
        kernel_release="6.8.0",
        libc_identity="glibc_2.39",
        architecture="x86_64",
        os_runtime_identity=(
            "system-Linux+release-Ubuntu_24.04+kernel-6.8.0+libc-glibc_2.39"
        ),
        locale_identity="C.UTF-8",
        timezone_identity="UTC",
        environment_reference="env:synthetic-lab",
        environment_mode=mode,
        system_site_packages_enabled=(mode == "DEVELOPMENT_TOOLING"),
        user_site_packages_enabled=False,
    )


def phase_projection() -> PhaseProjection:
    return PhaseProjection(
        scenario_subset=(),
        control_subset=(),
        instrument_configuration_id="instrument:baseline",
        instrument_acceptance_reference="NOT_APPLICABLE",
        capability_evaluation_reference="NOT_APPLICABLE",
        analysis_configuration_id="NOT_APPLICABLE",
        campaign_id="NOT_APPLICABLE",
        scheduled_run_ids=(),
        run_ids=(),
        repetition_identities=(),
    )


def build_inputs(schema_store: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "release_profile": profile(),
        "artifact_documents_by_locator": {
            "scientific/instrument.json": instrument(),
            "scientific/environment.json": environment(),
        },
        "artifact_metadata_by_locator": {
            "scientific/instrument.json": ArtifactAssemblyMetadata(
                lifecycle_state="FROZEN",
                phase_context="INSTRUMENT_VALIDATION",
            ),
            "scientific/environment.json": ArtifactAssemblyMetadata(
                lifecycle_state="VALIDATED",
                phase_context="DEVELOPMENT",
            ),
        },
        "rejected_bytes_by_locator": {},
        "rejected_input_metadata_by_locator": {},
        "schema_store": schema_store,
        "git_provenance": git_provenance(),
        "governing_documents": governing_documents(),
        "runtime_dependency_closure": dependency_closure(),
        "runtime_environment_facts": runtime_facts(),
        "environment_artifact": environment(),
        "phase_projection": phase_projection(),
        "provider_records": (),
        "reproducibility_limitations": (),
        "build_mode": "DEVELOPMENT_TOOLING",
    }
    inputs.update(overrides)
    return inputs


def thaw(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value


def parsed_release(built: BuiltResearchRelease) -> tuple[dict[str, Any], ...]:
    return (
        json.loads(built.artifact_manifest_bytes),
        json.loads(built.reproducibility_manifest_bytes),
        json.loads(built.release_build_bytes),
    )


def test_release_assembly_error_codes_are_exact() -> None:
    assert [item.name for item in ReleaseAssemblyErrorCode] == [
        "ASSEMBLY_INPUT_INVALID",
        "ASSEMBLY_INPUT_MISSING",
        "ASSEMBLY_ENVIRONMENT_NOT_ASSEMBLABLE",
        "ASSEMBLY_DEPENDENCY_PROVENANCE_INCOMPLETE",
        "ASSEMBLY_VALIDATION_FAILED",
        "ASSEMBLY_DESTINATION_EXISTS",
        "ASSEMBLY_WRITE_FAILED",
    ]


def test_public_all_is_exact() -> None:
    assert release_assembly.__all__ == [
        "ArtifactAssemblyMetadata",
        "BuiltResearchRelease",
        "PhaseProjection",
        "RejectedInputAssemblyMetadata",
        "ReleaseAssemblyError",
        "ReleaseAssemblyErrorCode",
        "RepetitionIdentity",
        "build_research_release",
        "write_research_release",
    ]


def test_built_release_is_frozen_and_slotted(schema_store: dict[str, Any]) -> None:
    built = build_research_release(**build_inputs(schema_store))
    assert BuiltResearchRelease.__slots__
    with pytest.raises(FrozenInstanceError):
        built.release_id = "release:changed-v0.1"  # type: ignore[misc]
    with pytest.raises(TypeError):
        built.artifact_manifest["manifest_version"] = "changed"  # type: ignore[index]


def test_metadata_types_are_frozen_and_slotted() -> None:
    for value in (
        ArtifactAssemblyMetadata("DRAFT", "DEVELOPMENT"),
        RejectedInputAssemblyMetadata("malformed", "bad", "DEVELOPMENT"),
        phase_projection(),
        RepetitionIdentity("rep", "UNAVAILABLE", run_id="run:one"),
    ):
        assert value.__slots__
        with pytest.raises(FrozenInstanceError):
            setattr(value, fields(value)[0].name, "changed")


def test_build_generates_fixed_versions_and_token(schema_store: dict[str, Any]) -> None:
    built = build_research_release(**build_inputs(schema_store))
    artifact, repro, build = parsed_release(built)
    assert built.release_id_token == "development-v0.1"
    assert artifact["manifest_version"] == "0.1.0"
    assert repro["reproducibility_version"] == "0.1.0"
    assert build["build_version"] == "0.1.0"
    assert build["build_id"] == "build:development-v0.1"


def test_build_is_filesystem_pure(
    schema_store: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    build_research_release(**build_inputs(schema_store))
    assert list(tmp_path.iterdir()) == []


def test_build_does_not_mutate_inputs(schema_store: dict[str, Any]) -> None:
    inputs = build_inputs(schema_store)
    before = deepcopy({key: value for key, value in inputs.items() if key != "schema_store"})
    build_research_release(**inputs)
    assert {key: value for key, value in inputs.items() if key != "schema_store"} == before


def test_artifact_whitelist_metadata_order_and_digests(schema_store: dict[str, Any]) -> None:
    inputs = build_inputs(schema_store)
    inputs["artifact_documents_by_locator"]["scientific/unselected.json"] = {
        "not": "selected"
    }
    built = build_research_release(**inputs)
    manifest, _, _ = parsed_release(built)
    assert [entry["artifact_family"] for entry in manifest["artifacts"]] == [
        "environment",
        "instrument_configuration",
    ]
    assert [entry["locator"] for entry in manifest["artifacts"]] == [
        "scientific/environment.json",
        "scientific/instrument.json",
    ]
    by_locator = {entry["locator"]: entry for entry in manifest["artifacts"]}
    assert by_locator["scientific/environment.json"]["lifecycle_state"] == "VALIDATED"
    assert by_locator["scientific/instrument.json"]["phase_context"] == "INSTRUMENT_VALIDATION"
    assert by_locator["scientific/environment.json"]["content_digest"] == canonical_sha256(environment())
    assert "scientific/unselected.json" not in by_locator


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("missing_document", ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_MISSING),
        ("missing_metadata", ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_MISSING),
        ("invalid_lifecycle", ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID),
        ("invalid_phase", ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID),
        ("identity_mismatch", ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID),
    ],
)
def test_selected_artifact_failures(
    schema_store: dict[str, Any], mutation: str, code: ReleaseAssemblyErrorCode
) -> None:
    inputs = build_inputs(schema_store)
    if mutation == "missing_document":
        del inputs["artifact_documents_by_locator"]["scientific/instrument.json"]
    elif mutation == "missing_metadata":
        del inputs["artifact_metadata_by_locator"]["scientific/instrument.json"]
    elif mutation == "invalid_lifecycle":
        inputs["artifact_metadata_by_locator"]["scientific/instrument.json"] = ArtifactAssemblyMetadata("UNKNOWN", "DEVELOPMENT")
    elif mutation == "invalid_phase":
        inputs["artifact_metadata_by_locator"]["scientific/instrument.json"] = ArtifactAssemblyMetadata("FROZEN", "UNKNOWN")
    else:
        inputs["artifact_documents_by_locator"]["scientific/instrument.json"]["instrument_configuration_id"] = "instrument:other"
    with pytest.raises(ReleaseAssemblyError) as caught:
        build_research_release(**inputs)
    assert caught.value.code is code


def test_rejected_input_projection_and_forensic_digest(schema_store: dict[str, Any]) -> None:
    inputs = build_inputs(schema_store)
    inputs["release_profile"] = profile(rejected=True)
    inputs["rejected_bytes_by_locator"] = {"rejected/duplicate-key.raw": b'{"a":1,"a":2}'}
    inputs["rejected_input_metadata_by_locator"] = {
        "rejected/duplicate-key.raw": RejectedInputAssemblyMetadata(
            "duplicate_json_key", "Repeated object name.", "DEVELOPMENT"
        )
    }
    built = build_research_release(**inputs)
    manifest, _, _ = parsed_release(built)
    entry = manifest["rejected_inputs"][0]
    assert entry["digest_scope"] == "FORENSIC_RAW_BYTES"
    assert entry["forensic_byte_digest"] == forensic_sha256_bytes(b'{"a":1,"a":2}')
    assert entry["rejection_class"] == "duplicate_json_key"


@pytest.mark.parametrize("missing", ["bytes", "metadata"])
def test_missing_rejected_inputs_fail(
    schema_store: dict[str, Any], missing: str
) -> None:
    inputs = build_inputs(schema_store)
    inputs["release_profile"] = profile(rejected=True)
    if missing != "bytes":
        inputs["rejected_bytes_by_locator"] = {"rejected/duplicate-key.raw": b"bad"}
    if missing != "metadata":
        inputs["rejected_input_metadata_by_locator"] = {
            "rejected/duplicate-key.raw": RejectedInputAssemblyMetadata(
                "malformed", "Bad.", "DEVELOPMENT"
            )
        }
    with pytest.raises(ReleaseAssemblyError) as caught:
        build_research_release(**inputs)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_MISSING


def test_duplicate_limitations_fail(schema_store: dict[str, Any]) -> None:
    inputs = build_inputs(schema_store, reproducibility_limitations=("same", "same"))
    with pytest.raises(ReleaseAssemblyError) as caught:
        build_research_release(**inputs)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID


def test_limitations_sort_by_utf8_bytes(schema_store: dict[str, Any]) -> None:
    inputs = build_inputs(schema_store, reproducibility_limitations=("éclair", "zebra", "alpha"))
    built = build_research_release(**inputs)
    _, repro, _ = parsed_release(built)
    assert repro["reproducibility_limitations"] == ["alpha", "zebra", "éclair"]


def test_development_missing_provenance_requires_limitation(schema_store: dict[str, Any]) -> None:
    inputs = build_inputs(schema_store, runtime_dependency_closure=dependency_closure(provenance=False))
    with pytest.raises(ReleaseAssemblyError) as caught:
        build_research_release(**inputs)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_DEPENDENCY_PROVENANCE_INCOMPLETE
    inputs["reproducibility_limitations"] = ("Original archive unavailable.",)
    built = build_research_release(**inputs)
    _, repro, build = parsed_release(built)
    assert "distribution_digest" not in repro["dependencies"][0]
    assert "distribution_filename" not in build["dependencies"][0]


def test_provider_records_are_explicit_sorted_and_immutable(schema_store: dict[str, Any]) -> None:
    providers = [
        {
            "agent_condition_id": "agentcond:zeta",
            "model_identifier": "model-zeta",
            "provider_runtime_identity": "runtime-zeta",
            "version_status": "REPORTED",
            "model_version": "1.0",
        },
        {
            "agent_condition_id": "agentcond:alpha",
            "model_identifier": "model-alpha",
            "provider_runtime_identity": "runtime-alpha",
            "version_status": "UNAVAILABLE",
            "limitation": "Provider did not report a version.",
        },
    ]
    before = deepcopy(providers)
    inputs = build_inputs(schema_store, provider_records=providers)
    with pytest.raises(ReleaseAssemblyError) as caught:
        build_research_release(**inputs)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_VALIDATION_FAILED
    assert providers == before


def test_not_applicable_environment_fails_before_candidates(schema_store: dict[str, Any]) -> None:
    release_profile = profile()
    release_profile["environment_reference"] = "NOT_APPLICABLE"
    inputs = build_inputs(schema_store, release_profile=release_profile)
    with pytest.raises(ReleaseAssemblyError) as caught:
        build_research_release(**inputs)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_ENVIRONMENT_NOT_ASSEMBLABLE


def test_environment_identity_mismatch_fails(schema_store: dict[str, Any]) -> None:
    selected_environment = environment()
    selected_environment["environment_id"] = "env:other"
    inputs = build_inputs(schema_store, environment_artifact=selected_environment)
    with pytest.raises(ReleaseAssemblyError) as caught:
        build_research_release(**inputs)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID


@pytest.mark.parametrize("mode", ["DEVELOPMENT_TOOLING", "CONTROLLED_RUNTIME"])
def test_development_build_modes(schema_store: dict[str, Any], mode: str) -> None:
    inputs = build_inputs(
        schema_store,
        runtime_environment_facts=runtime_facts(mode=mode),
        build_mode=mode,
    )
    built = build_research_release(**inputs)
    _, _, build = parsed_release(built)
    assert build["environment_mode"] == mode


def test_missing_development_build_mode_fails(schema_store: dict[str, Any]) -> None:
    inputs = build_inputs(schema_store, build_mode=None)
    with pytest.raises(ReleaseAssemblyError) as caught:
        build_research_release(**inputs)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_MISSING


@pytest.mark.parametrize("phase", ["PILOT", "CONFIRMATORY"])
def test_research_phases_derive_controlled_runtime(phase: str) -> None:
    assert release_assembly._resolve_build_mode(phase, None) == "CONTROLLED_RUNTIME"
    with pytest.raises(ReleaseAssemblyError):
        release_assembly._resolve_build_mode(phase, "DEVELOPMENT_TOOLING")


def test_source_tag_mismatch_fails(schema_store: dict[str, Any]) -> None:
    original = git_provenance()
    provenance = GitProvenance(
        repository_object_format=original.repository_object_format,
        repository_commit_sha=original.repository_commit_sha,
        repository_tree_sha=original.repository_tree_sha,
        release_tag_identity="research-release-pilot-v0.1",
        release_tag_object_sha=original.release_tag_object_sha,
        release_tag_target_commit_sha=original.release_tag_target_commit_sha,
        repository_clean=True,
    )
    inputs = build_inputs(schema_store, git_provenance=provenance)
    with pytest.raises(ReleaseAssemblyError) as caught:
        build_research_release(**inputs)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID


def test_validation_error_preserves_findings(schema_store: dict[str, Any]) -> None:
    release_profile = profile()
    release_profile["active_artifacts"].append(deepcopy(release_profile["active_artifacts"][0]))
    inputs = build_inputs(schema_store, release_profile=release_profile)
    with pytest.raises(ReleaseAssemblyError) as caught:
        build_research_release(**inputs)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_VALIDATION_FAILED
    assert isinstance(caught.value.findings, tuple)
    assert len(caught.value.findings) == 1
    assert "ASSEMBLY_VALIDATION_FAILED" in str(caught.value)


def test_schema_set_and_governing_registry(schema_store: dict[str, Any]) -> None:
    built = build_research_release(**build_inputs(schema_store))
    _, repro, _ = parsed_release(built)
    assert [record["document_id"] for record in repro["governing_documents"]] == [
        item.document_id for item in GOVERNING_DOCUMENT_REGISTRY_V0_1
    ]
    assert [record["schema_id"] for record in repro["schema_set"]] == sorted(
        {
            "urn:frontier-agent-containment:schema:environment:0.1.0",
            "urn:frontier-agent-containment:schema:instrument-configuration:0.1.0",
        }
    )


def test_digest_dag_bindings(schema_store: dict[str, Any]) -> None:
    built = build_research_release(**build_inputs(schema_store))
    artifact, repro, build = parsed_release(built)
    assert repro["artifact_manifest_digest"] == canonical_sha256(artifact)
    assert repro["environment"]["build_content_digest"] == canonical_sha256(build)
    assert repro["environment"]["environment_content_digest"] == canonical_sha256(environment())
    assert "artifact_manifest_digest" not in artifact
    assert "build_content_digest" not in build
    assert all("integrity" not in key.lower() for key in repro)


def test_serialization_is_exact_and_jcs_is_separate(schema_store: dict[str, Any]) -> None:
    built = build_research_release(**build_inputs(schema_store))
    for payload in (
        built.artifact_manifest_bytes,
        built.reproducibility_manifest_bytes,
        built.release_build_bytes,
    ):
        assert payload.endswith(b"\n")
        assert not payload.endswith(b"\n\n")
        assert b"\r" not in payload
        value = json.loads(payload)
        assert payload == (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, separators=(",", ": "), allow_nan=False).encode() + b"\n")
        assert payload != release_assembly.canonicalize_json(value)


def test_repeated_builds_are_byte_identical(schema_store: dict[str, Any]) -> None:
    first = build_research_release(**build_inputs(schema_store))
    second = build_research_release(**build_inputs(schema_store))
    assert first.artifact_manifest_bytes == second.artifact_manifest_bytes
    assert first.reproducibility_manifest_bytes == second.reproducibility_manifest_bytes
    assert first.release_build_bytes == second.release_build_bytes


def test_write_exact_three_file_layout_and_bytes(schema_store: dict[str, Any], tmp_path: Path) -> None:
    built = build_research_release(**build_inputs(schema_store))
    destination = write_research_release(built, output_root=tmp_path)
    assert destination == tmp_path / "releases" / "development-v0.1"
    assert sorted(item.name for item in destination.iterdir()) == [
        "artifact-manifest.json",
        "release-build.json",
        "reproducibility-manifest.json",
    ]
    assert (destination / "artifact-manifest.json").read_bytes() == built.artifact_manifest_bytes
    assert (destination / "reproducibility-manifest.json").read_bytes() == built.reproducibility_manifest_bytes
    assert (destination / "release-build.json").read_bytes() == built.release_build_bytes


def test_write_to_two_roots_is_byte_identical(schema_store: dict[str, Any], tmp_path: Path) -> None:
    built = build_research_release(**build_inputs(schema_store))
    first = write_research_release(built, output_root=tmp_path / "first")
    second = write_research_release(built, output_root=tmp_path / "second")
    assert {
        item.name: item.read_bytes() for item in first.iterdir()
    } == {item.name: item.read_bytes() for item in second.iterdir()}


def test_existing_destination_is_untouched(schema_store: dict[str, Any], tmp_path: Path) -> None:
    built = build_research_release(**build_inputs(schema_store))
    destination = tmp_path / "releases" / built.release_id_token
    destination.mkdir(parents=True)
    marker = destination / "operator-owned.txt"
    marker.write_text("untouched")
    with pytest.raises(ReleaseAssemblyError) as caught:
        write_research_release(built, output_root=tmp_path)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_DESTINATION_EXISTS
    assert marker.read_text() == "untouched"


def test_write_failure_leaves_no_final_release(
    schema_store: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    built = build_research_release(**build_inputs(schema_store))
    original_open = Path.open

    def failing_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path.name == "release-build.json":
            raise OSError("injected write failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    with pytest.raises(ReleaseAssemblyError) as caught:
        write_research_release(built, output_root=tmp_path)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_WRITE_FAILED
    assert not (tmp_path / "releases" / built.release_id_token).exists()
    assert list((tmp_path / "releases").iterdir()) == []


def test_public_validators_all_pass(schema_store: dict[str, Any]) -> None:
    inputs = build_inputs(schema_store)
    built = build_research_release(**inputs)
    artifact, repro, build = parsed_release(built)
    selected_documents = inputs["artifact_documents_by_locator"]
    assert validate_artifact_manifest(
        artifact,
        artifact_documents_by_locator=selected_documents,
        rejected_bytes_by_locator={},
        schema_store=schema_store,
    ) == ()
    assert validate_release_artifact_version_gates(
        inputs["release_profile"],
        artifact_manifest=artifact,
        artifact_documents_by_locator=selected_documents,
        rejected_bytes_by_locator={},
        schema_store=schema_store,
    ) == ()
    assert validate_release_build_consistency(build, inputs["runtime_environment_facts"]) == ()
    active = {
        "environment": [selected_documents["scientific/environment.json"]],
        "instrument_configuration": [selected_documents["scientific/instrument.json"]],
    }
    repository = {key: repro[key] for key in (
        "repository_object_format",
        "repository_commit_sha",
        "repository_tree_sha",
        "release_tag_identity",
        "release_tag_object_sha",
        "release_tag_target_commit_sha",
    )}
    environment_record = repro["environment"]
    assert validate_reproducibility_manifest(
        repro,
        artifact_manifest=artifact,
        artifact_documents_by_locator=selected_documents,
        schema_store=schema_store,
        active_artifacts=active,
        governing_document_bytes_by_id=inputs["governing_documents"].governing_document_bytes_by_id,
        governing_document_provenance_by_id=inputs["governing_documents"].governing_document_provenance_by_id,
        repository_provenance=repository,
        resolved_dependencies=inputs["runtime_dependency_closure"].resolved_dependencies,
        trusted_environment=environment_record,
        artifact_manifest_external_locator="releases/development-v0.1/artifact-manifest.json",
        rejected_bytes_by_locator={},
    ) == ()


def _phase_token(phase: str) -> str:
    return {
        "DEVELOPMENT": "development",
        "INSTRUMENT_VALIDATION": "instrument-validation",
        "PILOT": "pilot",
        "CONFIRMATORY": "confirmatory",
    }[phase]


def research_phase_inputs(
    schema_store: dict[str, Any], phase: str
) -> dict[str, Any]:
    artifacts = deepcopy(gating_artifact_set(phase))
    acceptance = artifacts["instrument_acceptance"][0]
    acceptance_id = (
        "acceptance:pilot-001"
        if phase == "PILOT"
        else "acceptance:confirmatory-001"
    )
    acceptance["acceptance_version"] = "0.2.0"
    acceptance["instrument_acceptance_id"] = acceptance_id
    if phase == "CONFIRMATORY":
        artifacts["campaign"][0]["instrument_acceptance_reference"] = acceptance_id

    documents: dict[str, dict[str, Any]] = {}
    metadata: dict[str, ArtifactAssemblyMetadata] = {}
    selections: list[dict[str, str]] = []
    for family in sorted(artifacts):
        for index, document in enumerate(artifacts[family]):
            family_spec = get_artifact_family_spec(family)
            version = document[family_spec.version_field]
            contract = get_artifact_family_contract_spec(family, version)
            assert contract.identity_field is not None
            artifact_id = document[contract.identity_field]
            locator = f"scientific/{family}-{index:03d}.json"
            documents[locator] = document
            metadata[locator] = ArtifactAssemblyMetadata("FROZEN", phase)
            selections.append(
                {
                    "artifact_family": family,
                    "artifact_id": artifact_id,
                    "locator": locator,
                }
            )

    campaign = artifacts["campaign"][0]
    scheduled = artifacts["scheduled_run"]
    projection = PhaseProjection(
        scenario_subset=tuple(campaign["scenario_ids"]),
        control_subset=(campaign["control_condition_ids"][0],),
        instrument_configuration_id=campaign["instrument_configuration_id"],
        instrument_acceptance_reference=acceptance_id,
        capability_evaluation_reference=(
            campaign["capability_evaluation_reference"]
            if phase == "CONFIRMATORY"
            else "NOT_APPLICABLE"
        ),
        analysis_configuration_id=(
            campaign["analysis_configuration_id"]
            if phase == "CONFIRMATORY"
            else "NOT_APPLICABLE"
        ),
        campaign_id=campaign["campaign_id"],
        scheduled_run_ids=tuple(item["scheduled_run_id"] for item in scheduled),
        run_ids=(),
        repetition_identities=tuple(
            RepetitionIdentity(
                repetition_id=item["seed_repetition_identity"]["repetition_id"],
                seed_status=item["seed_repetition_identity"]["seed_status"],
                scheduled_run_id=item["scheduled_run_id"],
                seed_value=item["seed_repetition_identity"].get("seed_value"),
            )
            for item in scheduled
        ),
    )
    token = _phase_token(phase)
    release_profile = {
        "profile_version": "0.1.0",
        "release_id": f"release:{token}-v0.1",
        "release_phase": phase,
        "source_release_tag_identity": f"research-release-{token}-v0.1",
        "active_artifacts": selections,
        "rejected_inputs": [],
        "environment_reference": "env:synthetic-lab",
        "governing_profile_version": "release-integrity-profile-v0.1",
        "enabled_dependency_extras": [],
    }
    acquired_git = git_provenance()
    acquired_git = GitProvenance(
        repository_object_format=acquired_git.repository_object_format,
        repository_commit_sha=acquired_git.repository_commit_sha,
        repository_tree_sha=acquired_git.repository_tree_sha,
        release_tag_identity=f"research-release-{token}-v0.1",
        release_tag_object_sha=acquired_git.release_tag_object_sha,
        release_tag_target_commit_sha=acquired_git.release_tag_target_commit_sha,
        repository_clean=True,
    )
    providers = (
        {
            "agent_condition_id": "agentcond:baseline",
            "model_identifier": "synthetic-model",
            "provider_runtime_identity": {
                "identity_status": "REPORTED",
                "runtime_identifier": "bounded_runtime",
            },
            "version_status": "REPORTED",
            "model_version": "2026.01",
        },
    )
    return build_inputs(
        schema_store,
        release_profile=release_profile,
        artifact_documents_by_locator=documents,
        artifact_metadata_by_locator=metadata,
        git_provenance=acquired_git,
        runtime_environment_facts=runtime_facts(mode="CONTROLLED_RUNTIME"),
        environment_artifact=artifacts["environment"][0],
        phase_projection=projection,
        provider_records=providers,
        build_mode=None,
    )


@pytest.mark.parametrize("phase", ["PILOT", "CONFIRMATORY"])
def test_research_phase_public_builds_pass_identity_and_phase_projection(
    schema_store: dict[str, Any], phase: str
) -> None:
    built = build_research_release(**research_phase_inputs(schema_store, phase))
    artifact, repro, build = parsed_release(built)
    assert repro["release_phase"] == phase
    assert repro["scenario_subset"] == ["scenario:protected-access"]
    assert len(repro["control_subset"]) == 1
    assert build["environment_mode"] == "CONTROLLED_RUNTIME"
    assert all(
        entry["artifact_version"] == "0.2.0"
        for entry in artifact["artifacts"]
        if entry["artifact_family"] == "instrument_acceptance"
    )


@pytest.mark.parametrize("phase", ["PILOT", "CONFIRMATORY"])
def test_research_phase_missing_distribution_provenance_cannot_be_waived(
    schema_store: dict[str, Any], phase: str
) -> None:
    inputs = research_phase_inputs(schema_store, phase)
    inputs["runtime_dependency_closure"] = dependency_closure(provenance=False)
    inputs["reproducibility_limitations"] = ("Explicit limitation.",)
    with pytest.raises(ReleaseAssemblyError) as caught:
        build_research_release(**inputs)
    assert caught.value.code is (
        ReleaseAssemblyErrorCode.ASSEMBLY_DEPENDENCY_PROVENANCE_INCOMPLETE
    )


@pytest.mark.parametrize(
    ("phase", "token"),
    [("INSTRUMENT_VALIDATION", "instrument-validation")],
)
@pytest.mark.parametrize("mode", ["DEVELOPMENT_TOOLING", "CONTROLLED_RUNTIME"])
def test_instrument_validation_supports_both_explicit_build_modes(
    schema_store: dict[str, Any], phase: str, token: str, mode: str
) -> None:
    inputs = build_inputs(schema_store)
    inputs["release_profile"]["release_id"] = f"release:{token}-v0.1"
    inputs["release_profile"]["release_phase"] = phase
    inputs["release_profile"]["source_release_tag_identity"] = (
        f"research-release-{token}-v0.1"
    )
    original = inputs["git_provenance"]
    inputs["git_provenance"] = GitProvenance(
        repository_object_format=original.repository_object_format,
        repository_commit_sha=original.repository_commit_sha,
        repository_tree_sha=original.repository_tree_sha,
        release_tag_identity=f"research-release-{token}-v0.1",
        release_tag_object_sha=original.release_tag_object_sha,
        release_tag_target_commit_sha=original.release_tag_target_commit_sha,
        repository_clean=True,
    )
    inputs["runtime_environment_facts"] = runtime_facts(mode=mode)
    inputs["build_mode"] = mode
    built = build_research_release(**inputs)
    assert parsed_release(built)[2]["environment_mode"] == mode


def test_active_selection_order_does_not_change_generated_bytes(
    schema_store: dict[str, Any],
) -> None:
    first_inputs = build_inputs(schema_store)
    second_inputs = build_inputs(schema_store)
    second_inputs["release_profile"]["active_artifacts"].reverse()
    first = build_research_release(**first_inputs)
    second = build_research_release(**second_inputs)
    assert first.artifact_manifest_bytes == second.artifact_manifest_bytes
    assert first.reproducibility_manifest_bytes == second.reproducibility_manifest_bytes
    assert first.release_build_bytes == second.release_build_bytes


def test_phase_arrays_and_repetitions_are_deterministically_ordered() -> None:
    projection = PhaseProjection(
        scenario_subset=("scenario:z", "scenario:a"),
        control_subset=("ctrlcond:z", "ctrlcond:a"),
        instrument_configuration_id="instrument:baseline",

        instrument_acceptance_reference="NOT_APPLICABLE",
        capability_evaluation_reference="NOT_APPLICABLE",
        analysis_configuration_id="NOT_APPLICABLE",
        campaign_id="NOT_APPLICABLE",
        scheduled_run_ids=("scheduledrun:z", "scheduledrun:a"),
        run_ids=("run:z", "run:a"),
        repetition_identities=(
            RepetitionIdentity("z", "UNAVAILABLE", run_id="run:z"),
            RepetitionIdentity("a", "UNAVAILABLE", run_id="run:a"),
        ),
    )
    normalized = release_assembly._phase_projection_record(projection)
    assert normalized["scenario_subset"] == ["scenario:a", "scenario:z"]
    assert normalized["control_subset"] == ["ctrlcond:a", "ctrlcond:z"]
    assert [
        item["repetition_id"] for item in normalized["repetition_identities"]
    ] == ["a", "z"]


def test_writer_rejects_unbounded_forged_release_token(tmp_path: Path) -> None:
    forged = BuiltResearchRelease(
        release_id="release:../escape",
        release_id_token="../escape",
        artifact_manifest=MappingProxyType({}),
        reproducibility_manifest=MappingProxyType({}),
        release_build_record=MappingProxyType({}),
        artifact_manifest_bytes=b"{}\n",
        reproducibility_manifest_bytes=b"{}\n",
        release_build_bytes=b"{}\n",
    )
    with pytest.raises(ReleaseAssemblyError) as caught:
        write_research_release(forged, output_root=tmp_path)
    assert caught.value.code is ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID
    assert not (tmp_path / "escape").exists()
