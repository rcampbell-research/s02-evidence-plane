"""Deterministic Stage 12E-3 research-release assembly.

This module constructs three schema-governed release records from explicit,
already-acquired inputs and persists their validated bytes to one bounded
release directory.  It performs no acquisition, repository discovery, Git
operation, network access, scientific execution, or release-tag mutation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from types import MappingProxyType
from typing import Any, Final, NoReturn, TypeAlias

from jsonschema.exceptions import SchemaError, ValidationError

from frontier_agent_containment.integrity import (
    IntegrityError,
    canonical_sha256,
    canonicalize_json,
    forensic_sha256_bytes,
)
from frontier_agent_containment.manifest_validation import (
    validate_artifact_manifest,
    validate_reproducibility_manifest,
)
from frontier_agent_containment.release_acquisition import (
    AcquisitionErrorCode,
    GOVERNING_DOCUMENT_REGISTRY_V0_1,
    GitProvenance,
    GoverningDocumentAcquisition,
    RuntimeDependencyClosure,
    RuntimeEnvironmentFacts,
    validate_release_build_consistency,
)
from frontier_agent_containment.release_validation import (
    validate_release_artifact_version_gates,
)
from frontier_agent_containment.schema_validation import (
    ExternalSchemaReferenceError,
    SchemaStore,
    SchemaStoreError,
    UnknownSchemaReferenceError,
    validate_instance,
)
from frontier_agent_containment.semantic_validation import (
    get_artifact_family_contract_spec,
    get_artifact_family_spec,
)


JsonObject: TypeAlias = Mapping[str, Any]
PathInput: TypeAlias = str | os.PathLike[str]

_RELEASE_PROFILE_SCHEMA_ID: Final = (
    "urn:frontier-agent-containment:schema:release-profile:0.1.0"
)
_RELEASE_BUILD_SCHEMA_ID: Final = (
    "urn:frontier-agent-containment:schema:release-build-record:0.1.0"
)
_MANIFEST_VERSION: Final = "0.1.0"
_REPRODUCIBILITY_VERSION: Final = "0.1.0"
_BUILD_VERSION: Final = "0.1.0"
_CONTROLLED_RUNTIME: Final = "CONTROLLED_RUNTIME"
_DEVELOPMENT_TOOLING: Final = "DEVELOPMENT_TOOLING"
_PHASE_CONTEXTS: Final = frozenset(
    {
        "DEVELOPMENT",
        "INSTRUMENT_VALIDATION",
        "PILOT",
        "CONFIRMATORY",
        "NOT_APPLICABLE",
    }
)
_LIFECYCLE_STATES: Final = frozenset(
    {"DRAFT", "VALIDATED", "FROZEN", "RETIRED"}
)
_MACHINE_IDENTIFIER: Final = re.compile(
    r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$"
)
_RELEASE_TOKEN: Final = re.compile(
    r"^(?:development|instrument-validation|pilot|confirmatory)"
    r"-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$"
)
_GENERATED_FILENAMES: Final = (
    "artifact-manifest.json",
    "reproducibility-manifest.json",
    "release-build.json",
)
_SCHEMA_FAILURES: Final = (
    SchemaError,
    ValidationError,
    SchemaStoreError,
    ExternalSchemaReferenceError,
    UnknownSchemaReferenceError,
)


class ReleaseAssemblyErrorCode(str, Enum):
    """Closed Stage 12E-3 assembly failure categories."""

    ASSEMBLY_INPUT_INVALID = "ASSEMBLY_INPUT_INVALID"
    ASSEMBLY_INPUT_MISSING = "ASSEMBLY_INPUT_MISSING"
    ASSEMBLY_ENVIRONMENT_NOT_ASSEMBLABLE = (
        "ASSEMBLY_ENVIRONMENT_NOT_ASSEMBLABLE"
    )
    ASSEMBLY_DEPENDENCY_PROVENANCE_INCOMPLETE = (
        "ASSEMBLY_DEPENDENCY_PROVENANCE_INCOMPLETE"
    )
    ASSEMBLY_VALIDATION_FAILED = "ASSEMBLY_VALIDATION_FAILED"
    ASSEMBLY_DESTINATION_EXISTS = "ASSEMBLY_DESTINATION_EXISTS"
    ASSEMBLY_WRITE_FAILED = "ASSEMBLY_WRITE_FAILED"


class ReleaseAssemblyError(ValueError):
    """One deterministic assembly failure with optional validator findings."""

    def __init__(
        self,
        code: ReleaseAssemblyErrorCode,
        message: str,
        *,
        findings: Sequence[Any] = (),
    ) -> None:
        self.code = code
        self.findings = tuple(findings)
        super().__init__(f"{code.value}: {message}")


@dataclass(frozen=True, slots=True)
class ArtifactAssemblyMetadata:
    """Caller-declared non-derived metadata for one selected artifact."""

    lifecycle_state: str
    phase_context: str


@dataclass(frozen=True, slots=True)
class RejectedInputAssemblyMetadata:
    """Caller-declared metadata for one selected rejected input."""

    rejection_class: str
    description: str
    phase_context: str


@dataclass(frozen=True, slots=True)
class RepetitionIdentity:
    """One exact Reproducibility Manifest repetition record."""

    repetition_id: str
    seed_status: str
    scheduled_run_id: str | None = None
    run_id: str | None = None
    seed_value: int | str | None = None


@dataclass(frozen=True, slots=True)
class PhaseProjection:
    """Complete caller-supplied phase projection for one release."""

    scenario_subset: tuple[str, ...]
    control_subset: tuple[str, ...]
    instrument_configuration_id: str
    instrument_acceptance_reference: str
    capability_evaluation_reference: str
    analysis_configuration_id: str
    campaign_id: str
    scheduled_run_ids: tuple[str, ...]
    run_ids: tuple[str, ...]
    repetition_identities: tuple[RepetitionIdentity, ...]


@dataclass(frozen=True, slots=True)
class BuiltResearchRelease:
    """Immutable views and authoritative bytes for one validated release."""

    release_id: str
    release_id_token: str
    artifact_manifest: Mapping[str, Any]
    reproducibility_manifest: Mapping[str, Any]
    release_build_record: Mapping[str, Any]
    artifact_manifest_bytes: bytes
    reproducibility_manifest_bytes: bytes
    release_build_bytes: bytes


def build_research_release(
    *,
    release_profile: Mapping[str, Any],
    artifact_documents_by_locator: Mapping[str, Mapping[str, Any]],
    artifact_metadata_by_locator: Mapping[str, ArtifactAssemblyMetadata],
    rejected_bytes_by_locator: Mapping[str, bytes],
    rejected_input_metadata_by_locator: Mapping[
        str, RejectedInputAssemblyMetadata
    ],
    schema_store: SchemaStore,
    git_provenance: GitProvenance,
    governing_documents: GoverningDocumentAcquisition,
    runtime_dependency_closure: RuntimeDependencyClosure,
    runtime_environment_facts: RuntimeEnvironmentFacts,
    environment_artifact: Mapping[str, Any],
    phase_projection: PhaseProjection,
    provider_records: Sequence[Mapping[str, Any]],
    reproducibility_limitations: Sequence[str],
    build_mode: str | None = None,
) -> BuiltResearchRelease:
    """Purely construct and validate one deterministic research release."""

    _validate_schema_object(
        release_profile,
        _RELEASE_PROFILE_SCHEMA_ID,
        schema_store,
        "Release Profile",
    )
    release_id = release_profile["release_id"]
    release_id_token = release_id.removeprefix("release:")
    release_phase = release_profile["release_phase"]
    _validate_source_provenance(
        release_profile, git_provenance, release_id_token
    )
    _validate_explicit_input_types(
        artifact_metadata_by_locator,
        rejected_input_metadata_by_locator,
        phase_projection,
    )
    environment_reference = release_profile["environment_reference"]
    if environment_reference == "NOT_APPLICABLE":
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_ENVIRONMENT_NOT_ASSEMBLABLE,
            "Release Profile environment_reference is NOT_APPLICABLE",
        )

    limitations = _normalized_limitations(reproducibility_limitations)
    selected_build_mode = _resolve_build_mode(release_phase, build_mode)
    projection = _phase_projection_record(phase_projection)
    providers = _normalized_providers(provider_records)
    governing_records = _governing_document_records(governing_documents)
    _validate_dependency_acquisition(runtime_dependency_closure)
    if runtime_environment_facts.environment_reference != environment_reference:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "RuntimeEnvironmentFacts environment_reference does not equal Release Profile",
        )
    environment = _copy_json_object(environment_artifact, "environment_artifact")
    if environment.get("environment_id") != environment_reference:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "Environment artifact identity does not equal environment_reference",
        )

    selected_documents: dict[str, dict[str, Any]] = {}
    artifact_entries: list[dict[str, Any]] = []
    active_artifacts: dict[str, list[dict[str, Any]]] = {}
    for index, selection in enumerate(release_profile["active_artifacts"]):
        locator = selection["locator"]
        document = artifact_documents_by_locator.get(locator)
        if document is None:
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_MISSING,
                f"selected artifact document is missing at locator {locator!r}",
            )
        metadata = artifact_metadata_by_locator.get(locator)
        if metadata is None:
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_MISSING,
                f"selected artifact metadata is missing at locator {locator!r}",
            )
        _validate_artifact_metadata(metadata, locator)
        copied = _copy_json_object(document, f"artifact_documents_by_locator[{locator!r}]")
        family = selection["artifact_family"]
        artifact_id = selection["artifact_id"]
        try:
            family_spec = get_artifact_family_spec(family)
            artifact_version = copied[family_spec.version_field]
            contract = get_artifact_family_contract_spec(
                family, artifact_version
            )
        except (KeyError, TypeError) as error:
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
                f"selected artifact at index {index} has no exact family/version contract: {error}",
            )
        if (
            contract.identity_field is None
            or copied.get(contract.identity_field) != artifact_id
        ):
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
                f"selected {family} identity {artifact_id!r} does not equal the exact artifact identity",
            )
        selected_documents[locator] = copied
        active_artifacts.setdefault(family, []).append(copied)
        artifact_entries.append(
            {
                "artifact_family": family,
                "artifact_id": artifact_id,
                "artifact_version": contract.artifact_version,
                "locator": locator,
                "schema_id": contract.schema_id,
                "schema_version": _schema_version(contract.schema_id),
                "lifecycle_state": metadata.lifecycle_state,
                "phase_context": metadata.phase_context,
                "content_digest": _canonical_digest(
                    copied, f"selected artifact at locator {locator!r}"
                ),
            }
        )

    _validate_selected_environment(
        active_artifacts, environment_reference, environment
    )
    artifact_entries.sort(
        key=lambda entry: (
            entry["artifact_family"],
            entry["artifact_id"],
            entry["locator"],
        )
    )

    selected_rejected_bytes: dict[str, bytes] = {}
    rejected_entries: list[dict[str, Any]] = []
    for selection in release_profile["rejected_inputs"]:
        locator = selection["locator"]
        if locator not in rejected_bytes_by_locator:
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_MISSING,
                f"selected rejected bytes are missing at locator {locator!r}",
            )
        metadata = rejected_input_metadata_by_locator.get(locator)
        if metadata is None:
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_MISSING,
                f"selected rejected-input metadata is missing at locator {locator!r}",
            )
        _validate_rejected_metadata(metadata, locator)
        raw = rejected_bytes_by_locator[locator]
        try:
            digest = forensic_sha256_bytes(raw)
        except TypeError as error:
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
                f"selected rejected input at {locator!r} is not exact bytes: {error}",
            )
        selected_rejected_bytes[locator] = raw
        rejected_entries.append(
            {
                "rejected_input_id": selection["rejected_input_id"],
                "locator": locator,
                "rejection_class": metadata.rejection_class,
                "description": metadata.description,
                "digest_scope": "FORENSIC_RAW_BYTES",
                "forensic_byte_digest": digest,
                "phase_context": metadata.phase_context,
            }
        )
    rejected_entries.sort(
        key=lambda entry: (entry["rejected_input_id"], entry["locator"])
    )

    artifact_manifest = {
        "manifest_version": _MANIFEST_VERSION,
        "scope": {"scope_type": "RELEASE"},
        "canonicalization_id": "RFC8785-JCS",
        "digest_algorithm": "SHA-256",
        "artifacts": artifact_entries,
        "rejected_inputs": rejected_entries,
    }
    artifact_findings = validate_artifact_manifest(
        artifact_manifest,
        artifact_documents_by_locator=selected_documents,
        rejected_bytes_by_locator=selected_rejected_bytes,
        schema_store=schema_store,
    )
    _raise_validation_findings("Artifact Manifest", artifact_findings)

    release_findings = validate_release_artifact_version_gates(
        release_profile,
        artifact_manifest=artifact_manifest,
        artifact_documents_by_locator=selected_documents,
        rejected_bytes_by_locator=selected_rejected_bytes,
        schema_store=schema_store,
    )
    _raise_validation_findings("release artifact version gates", release_findings)

    _validate_distribution_provenance(
        runtime_dependency_closure, release_phase, limitations
    )
    build_identity = f"build:{release_id_token}"
    release_build_record = _build_release_record(
        release_id,
        build_identity,
        selected_build_mode,
        runtime_dependency_closure,
        runtime_environment_facts,
    )
    _validate_schema_object(
        release_build_record,
        _RELEASE_BUILD_SCHEMA_ID,
        schema_store,
        "Release Build Record",
    )
    consistency_findings = validate_release_build_consistency(
        release_build_record, runtime_environment_facts
    )
    _raise_validation_findings(
        "Release Build Record consistency", consistency_findings
    )

    schema_records = _schema_records(artifact_entries, schema_store)
    dependencies = _reproducibility_dependencies(runtime_dependency_closure)
    environment_record = {
        "python_version": runtime_environment_facts.python_version,
        "os_runtime_identity": runtime_environment_facts.os_runtime_identity,
        "architecture": runtime_environment_facts.architecture,
        "environment_reference": environment_reference,
        "build_identity": build_identity,
        "environment_content_digest": _canonical_digest(
            environment, "Environment artifact"
        ),
        "build_content_digest": _canonical_digest(
            release_build_record, "Release Build Record"
        ),
    }
    reproducibility_manifest = {
        "reproducibility_version": _REPRODUCIBILITY_VERSION,
        "release_phase": release_phase,
        "repository_object_format": git_provenance.repository_object_format,
        "repository_commit_sha": git_provenance.repository_commit_sha,
        "repository_tree_sha": git_provenance.repository_tree_sha,
        "release_tag_identity": git_provenance.release_tag_identity,
        "release_tag_object_sha": git_provenance.release_tag_object_sha,
        "release_tag_target_commit_sha": (
            git_provenance.release_tag_target_commit_sha
        ),
        "artifact_manifest_locator": (
            f"releases/{release_id_token}/artifact-manifest.json"
        ),
        "artifact_manifest_digest": _canonical_digest(
            artifact_manifest, "Artifact Manifest"
        ),
        "governing_documents": governing_records,
        "schema_set": schema_records,
        "environment": environment_record,
        "dependencies": dependencies,
        **projection,
        "model_provider_identities": providers,
        "reproducibility_limitations": limitations,
    }
    repository_provenance = {
        "repository_object_format": git_provenance.repository_object_format,
        "repository_commit_sha": git_provenance.repository_commit_sha,
        "repository_tree_sha": git_provenance.repository_tree_sha,
        "release_tag_identity": git_provenance.release_tag_identity,
        "release_tag_object_sha": git_provenance.release_tag_object_sha,
        "release_tag_target_commit_sha": (
            git_provenance.release_tag_target_commit_sha
        ),
    }
    repro_findings = validate_reproducibility_manifest(
        reproducibility_manifest,
        artifact_manifest=artifact_manifest,
        artifact_documents_by_locator=selected_documents,
        schema_store=schema_store,
        active_artifacts=active_artifacts,
        governing_document_bytes_by_id=(
            governing_documents.governing_document_bytes_by_id
        ),
        governing_document_provenance_by_id=(
            governing_documents.governing_document_provenance_by_id
        ),
        repository_provenance=repository_provenance,
        resolved_dependencies=runtime_dependency_closure.resolved_dependencies,
        trusted_environment=environment_record,
        artifact_manifest_external_locator=(
            f"releases/{release_id_token}/artifact-manifest.json"
        ),
        rejected_bytes_by_locator=selected_rejected_bytes,
    )
    _raise_validation_findings("Reproducibility Manifest", repro_findings)

    try:
        artifact_manifest_bytes = _serialize_json(artifact_manifest)
        reproducibility_manifest_bytes = _serialize_json(
            reproducibility_manifest
        )
        release_build_bytes = _serialize_json(release_build_record)
    except (TypeError, ValueError) as error:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            f"generated JSON is not deterministically serializable: {error}",
        )
    return BuiltResearchRelease(
        release_id=release_id,
        release_id_token=release_id_token,
        artifact_manifest=_freeze_json(artifact_manifest),
        reproducibility_manifest=_freeze_json(reproducibility_manifest),
        release_build_record=_freeze_json(release_build_record),
        artifact_manifest_bytes=artifact_manifest_bytes,
        reproducibility_manifest_bytes=reproducibility_manifest_bytes,
        release_build_bytes=release_build_bytes,
    )


def write_research_release(
    built_release: BuiltResearchRelease,
    *,
    output_root: PathInput,
) -> Path:
    """Persist one validated built release through a sibling atomic rename."""

    _validate_built_release_for_write(built_release)
    releases_root = Path(output_root) / "releases"
    destination = releases_root / built_release.release_id_token
    if os.path.lexists(destination):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_DESTINATION_EXISTS,
            f"release destination already exists: {destination}",
        )

    temporary: Path | None = None
    try:
        releases_root.mkdir(parents=True, exist_ok=True)
        if os.path.lexists(destination):
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_DESTINATION_EXISTS,
                f"release destination already exists: {destination}",
            )
        temporary = Path(
            tempfile.mkdtemp(
                prefix=f".{built_release.release_id_token}.tmp-",
                dir=releases_root,
            )
        )
        payloads = {
            "artifact-manifest.json": built_release.artifact_manifest_bytes,
            "reproducibility-manifest.json": (
                built_release.reproducibility_manifest_bytes
            ),
            "release-build.json": built_release.release_build_bytes,
        }
        for filename in _GENERATED_FILENAMES:
            with (temporary / filename).open("xb") as stream:
                stream.write(payloads[filename])
                stream.flush()
        actual = tuple(sorted(item.name for item in temporary.iterdir()))
        if actual != tuple(sorted(_GENERATED_FILENAMES)) or not all(
            (temporary / filename).is_file()
            for filename in _GENERATED_FILENAMES
        ):
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_WRITE_FAILED,
                "temporary release directory violates the three-file whitelist",
            )
        if os.path.lexists(destination):
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_DESTINATION_EXISTS,
                f"release destination already exists: {destination}",
            )
        temporary.rename(destination)
        temporary = None
        return destination
    except ReleaseAssemblyError:
        raise
    except OSError as error:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_WRITE_FAILED,
            f"release persistence failed: {error}",
        )
    finally:
        if temporary is not None:
            shutil.rmtree(temporary, ignore_errors=True)


def _validate_built_release_for_write(value: Any) -> None:
    if not isinstance(value, BuiltResearchRelease):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "built_release must be a BuiltResearchRelease",
        )
    if (
        _RELEASE_TOKEN.fullmatch(value.release_id_token) is None
        or value.release_id != f"release:{value.release_id_token}"
    ):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "built release identity cannot name a bounded release destination",
        )
    if any(
        type(payload) is not bytes
        for payload in (
            value.artifact_manifest_bytes,
            value.reproducibility_manifest_bytes,
            value.release_build_bytes,
        )
    ):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "built release payloads must be exact bytes",
        )


def _validate_schema_object(
    value: Mapping[str, Any],
    schema_id: str,
    schema_store: SchemaStore,
    label: str,
) -> None:
    schema = schema_store.get(schema_id)
    if schema is None:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_VALIDATION_FAILED,
            f"required local {label} schema {schema_id!r} is absent",
        )
    try:
        validate_instance(value, schema, schema_store=schema_store)
    except _SCHEMA_FAILURES as error:
        raise ReleaseAssemblyError(
            ReleaseAssemblyErrorCode.ASSEMBLY_VALIDATION_FAILED,
            f"{label} validation failed: {_schema_error_message(error)}",
            findings=(_schema_error_message(error),),
        )


def _validate_source_provenance(
    profile: Mapping[str, Any],
    provenance: GitProvenance,
    release_id_token: str,
) -> None:
    expected_tag = f"research-release-{release_id_token}"
    if profile["source_release_tag_identity"] != expected_tag:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "Release Profile source tag does not match release phase/version",
        )
    if provenance.release_tag_identity != expected_tag:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "Git provenance source tag does not match Release Profile",
        )
    if provenance.release_tag_target_commit_sha != provenance.repository_commit_sha:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "Git provenance source tag target does not match repository commit",
        )


def _validate_explicit_input_types(
    artifact_metadata: Mapping[str, ArtifactAssemblyMetadata],
    rejected_metadata: Mapping[str, RejectedInputAssemblyMetadata],
    phase_projection: PhaseProjection,
) -> None:
    if not isinstance(phase_projection, PhaseProjection):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "phase_projection must be a PhaseProjection",
        )
    if any(
        not isinstance(value, ArtifactAssemblyMetadata)
        for value in artifact_metadata.values()
    ):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "artifact metadata values must be ArtifactAssemblyMetadata records",
        )
    if any(
        not isinstance(value, RejectedInputAssemblyMetadata)
        for value in rejected_metadata.values()
    ):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "rejected-input metadata values must be RejectedInputAssemblyMetadata records",
        )


def _validate_artifact_metadata(
    metadata: ArtifactAssemblyMetadata, locator: str
) -> None:
    if metadata.lifecycle_state not in _LIFECYCLE_STATES:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            f"invalid lifecycle_state for selected locator {locator!r}",
        )
    if metadata.phase_context not in _PHASE_CONTEXTS:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            f"invalid phase_context for selected locator {locator!r}",
        )


def _validate_rejected_metadata(
    metadata: RejectedInputAssemblyMetadata, locator: str
) -> None:
    if (
        not isinstance(metadata.rejection_class, str)
        or len(metadata.rejection_class) > 128
        or _MACHINE_IDENTIFIER.fullmatch(metadata.rejection_class) is None
    ):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            f"invalid rejection_class for selected locator {locator!r}",
        )
    if (
        not isinstance(metadata.description, str)
        or not 1 <= len(metadata.description) <= 2000
    ):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            f"invalid description for selected locator {locator!r}",
        )
    if metadata.phase_context not in _PHASE_CONTEXTS:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            f"invalid phase_context for selected rejected locator {locator!r}",
        )


def _validate_selected_environment(
    active_artifacts: Mapping[str, Sequence[Mapping[str, Any]]],
    environment_reference: str,
    environment: Mapping[str, Any],
) -> None:
    selected = tuple(
        document
        for document in active_artifacts.get("environment", ())
        if document.get("environment_id") == environment_reference
    )
    if len(selected) != 1:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_MISSING,
            "active_artifacts must select the concrete Environment exactly once",
        )
    if selected[0] != environment:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "selected Environment document differs from environment_artifact",
        )


def _normalized_limitations(values: Sequence[str]) -> list[str]:
    copied = list(values)
    if any(not isinstance(value, str) for value in copied):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "reproducibility limitations must be strings",
        )
    if len(copied) != len(set(copied)):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "reproducibility limitations contain a duplicate",
        )
    return sorted(copied, key=lambda value: value.encode("utf-8"))


def _validate_dependency_acquisition(
    closure: RuntimeDependencyClosure,
) -> None:
    disallowed = tuple(
        finding
        for finding in closure.findings
        if finding.code
        is not AcquisitionErrorCode.ACQUISITION_DISTRIBUTION_PROVENANCE_UNAVAILABLE
    )
    if disallowed:
        raise ReleaseAssemblyError(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "runtime dependency closure contains acquisition findings",
            findings=disallowed,
        )


def _validate_distribution_provenance(
    closure: RuntimeDependencyClosure,
    release_phase: str,
    limitations: Sequence[str],
) -> None:
    missing = tuple(
        dependency.name
        for dependency in closure.dependencies
        if dependency.distribution_provenance is None
    )
    if not missing:
        return
    if release_phase in {"PILOT", "CONFIRMATORY"} or not limitations:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_DEPENDENCY_PROVENANCE_INCOMPLETE,
            "original distribution provenance is missing for: "
            + ", ".join(missing),
        )


def _resolve_build_mode(release_phase: str, build_mode: str | None) -> str:
    if release_phase in {"PILOT", "CONFIRMATORY"}:
        if build_mode not in {None, _CONTROLLED_RUNTIME}:
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
                f"{release_phase} requires CONTROLLED_RUNTIME",
            )
        return _CONTROLLED_RUNTIME
    if build_mode is None:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_MISSING,
            f"{release_phase} requires an explicit build_mode",
        )
    if build_mode not in {_DEVELOPMENT_TOOLING, _CONTROLLED_RUNTIME}:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            f"invalid build_mode {build_mode!r}",
        )
    return build_mode


def _build_release_record(
    release_id: str,
    build_identity: str,
    build_mode: str,
    closure: RuntimeDependencyClosure,
    facts: RuntimeEnvironmentFacts,
) -> dict[str, Any]:
    dependencies: list[dict[str, str]] = []
    for dependency in closure.dependencies:
        record = {"name": dependency.name, "version": dependency.version}
        if dependency.distribution_provenance is not None:
            record["distribution_filename"] = (
                dependency.distribution_provenance.distribution_filename
            )
            record["distribution_digest"] = (
                dependency.distribution_provenance.distribution_digest
            )
        dependencies.append(record)
    return {
        "build_id": build_identity,
        "build_version": _BUILD_VERSION,
        "release_id": release_id,
        "python_implementation": facts.python_implementation,
        "python_version": facts.python_version,
        "python_build_string": facts.python_build_string,
        "os_system": facts.os_system,
        "os_release_identity": facts.os_release_identity,
        "kernel_release": facts.kernel_release,
        "libc_identity": facts.libc_identity,
        "architecture": facts.architecture,
        "os_runtime_identity": facts.os_runtime_identity,
        "locale_identity": facts.locale_identity,
        "timezone_identity": facts.timezone_identity,
        "environment_reference": facts.environment_reference,
        "environment_mode": build_mode,
        "system_site_packages_enabled": facts.system_site_packages_enabled,
        "user_site_packages_enabled": facts.user_site_packages_enabled,
        "dependency_scope": closure.dependency_scope,
        "dependencies": dependencies,
    }


def _governing_document_records(
    acquisition: GoverningDocumentAcquisition,
) -> list[dict[str, str]]:
    if len(acquisition.documents) != len(GOVERNING_DOCUMENT_REGISTRY_V0_1):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            "governing document acquisition does not contain exactly nine records",
        )
    records: list[dict[str, str]] = []
    for expected, acquired in zip(
        GOVERNING_DOCUMENT_REGISTRY_V0_1,
        acquisition.documents,
        strict=True,
    ):
        provenance = acquired.provenance
        if (
            provenance.document_id != expected.document_id
            or provenance.document_version != expected.document_version
            or provenance.frozen_tag_identity != expected.frozen_tag_identity
            or forensic_sha256_bytes(acquired.exact_bytes)
            != provenance.exact_byte_content_digest
        ):
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
                f"governing document acquisition is incoherent for {expected.document_id!r}",
            )
        records.append(
            {
                "document_id": provenance.document_id,
                "document_version": provenance.document_version,
                "frozen_tag_identity": provenance.frozen_tag_identity,
                "content_digest": provenance.exact_byte_content_digest,
            }
        )
    return records


def _schema_records(
    artifact_entries: Sequence[Mapping[str, Any]],
    schema_store: SchemaStore,
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for schema_id in sorted({entry["schema_id"] for entry in artifact_entries}):
        schema = schema_store.get(schema_id)
        if schema is None:
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_MISSING,
                f"selected artifact schema is absent from SchemaStore: {schema_id!r}",
            )
        copied_schema = _copy_json_object(schema, f"schema_store[{schema_id!r}]")
        records.append(
            {
                "schema_id": schema_id,
                "schema_version": _schema_version(schema_id),
                "content_digest": _canonical_digest(
                    copied_schema, f"schema {schema_id!r}"
                ),
            }
        )
    return records


def _reproducibility_dependencies(
    closure: RuntimeDependencyClosure,
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for dependency in closure.dependencies:
        record = {"name": dependency.name, "version": dependency.version}
        if dependency.distribution_provenance is not None:
            record["distribution_digest"] = (
                dependency.distribution_provenance.distribution_digest
            )
        records.append(record)
    return records


def _phase_projection_record(projection: PhaseProjection) -> dict[str, Any]:
    scalar_arrays = {
        "scenario_subset": projection.scenario_subset,
        "control_subset": projection.control_subset,
        "scheduled_run_ids": projection.scheduled_run_ids,
        "run_ids": projection.run_ids,
    }
    normalized: dict[str, Any] = {}
    for field, values in scalar_arrays.items():
        copied = list(values)
        if any(not isinstance(value, str) for value in copied):
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
                f"{field} must contain only strings",
            )
        if len(copied) != len(set(copied)):
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
                f"{field} contains a duplicate",
            )
        normalized[field] = sorted(copied)
    repetitions: list[dict[str, Any]] = []
    for item in projection.repetition_identities:
        if not isinstance(item, RepetitionIdentity):
            _raise(
                ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
                "repetition_identities must contain RepetitionIdentity records",
            )
        record: dict[str, Any] = {
            "repetition_id": item.repetition_id,
            "seed_status": item.seed_status,
        }
        if item.scheduled_run_id is not None:
            record["scheduled_run_id"] = item.scheduled_run_id
        if item.run_id is not None:
            record["run_id"] = item.run_id
        if item.seed_value is not None:
            record["seed_value"] = item.seed_value
        repetitions.append(record)
    repetitions.sort(
        key=lambda record: (
            record["repetition_id"],
            record.get("scheduled_run_id", ""),
            record.get("run_id", ""),
            canonicalize_json(record),
        )
    )
    normalized.update(
        {
            "instrument_configuration_id": (
                projection.instrument_configuration_id
            ),
            "instrument_acceptance_reference": (
                projection.instrument_acceptance_reference
            ),
            "capability_evaluation_reference": (
                projection.capability_evaluation_reference
            ),
            "analysis_configuration_id": projection.analysis_configuration_id,
            "campaign_id": projection.campaign_id,
            "repetition_identities": repetitions,
        }
    )
    return normalized


def _normalized_providers(
    provider_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    records = [
        _copy_json_object(record, f"provider_records[{index}]")
        for index, record in enumerate(provider_records)
    ]
    try:
        records.sort(
            key=lambda record: (
                record["agent_condition_id"],
                record["model_identifier"],
                canonicalize_json(record),
            )
        )
    except (KeyError, TypeError, IntegrityError) as error:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            f"provider records cannot be deterministically ordered: {error}",
        )
    return records


def _copy_json_object(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    copied = _copy_json(value)
    if not isinstance(copied, dict):
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            f"{label} must be a JSON object",
        )
    return copied


def _copy_json(value: Any) -> Any:
    if value is None or type(value) in {bool, int, float, str}:
        return value
    if isinstance(value, Mapping):
        copied: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                _raise(
                    ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
                    "JSON object member names must be exact strings",
                )
            copied[key] = _copy_json(item)
        return copied
    if isinstance(value, (list, tuple)):
        return [_copy_json(item) for item in value]
    _raise(
        ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
        f"value of type {type(value).__name__} is outside the JSON domain",
    )


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _canonical_digest(value: Any, label: str) -> str:
    try:
        return canonical_sha256(value)
    except (IntegrityError, TypeError) as error:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            f"{label} cannot receive a canonical content digest: {error}",
        )


def _serialize_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _schema_version(schema_id: str) -> str:
    version = schema_id.rsplit(":", 1)[-1]
    if not version or version == schema_id:
        _raise(
            ReleaseAssemblyErrorCode.ASSEMBLY_INPUT_INVALID,
            f"schema ID has no exact version component: {schema_id!r}",
        )
    return version


def _schema_error_message(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return error.message
    return str(error)


def _raise_validation_findings(
    label: str, findings: Sequence[Any]
) -> None:
    if findings:
        raise ReleaseAssemblyError(
            ReleaseAssemblyErrorCode.ASSEMBLY_VALIDATION_FAILED,
            f"{label} has {len(findings)} finding(s)",
            findings=findings,
        )


def _raise(code: ReleaseAssemblyErrorCode, message: str) -> NoReturn:
    raise ReleaseAssemblyError(code, message)


__all__ = [
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
