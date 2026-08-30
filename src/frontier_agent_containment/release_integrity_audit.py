"""Deterministic audit of one persisted Stage 12E-3 research release.

The auditor composes the existing schema, manifest, release-version, build,
and reproducibility validators against explicit caller-supplied governed
inputs.  It performs no discovery, acquisition, repair, Git operation, or
persistent write.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
import stat
from typing import Any, Final, TypeAlias

from jsonschema.exceptions import SchemaError, ValidationError

from frontier_agent_containment.integrity import (
    IntegrityError,
    canonical_sha256,
    canonicalize_json,
)
from frontier_agent_containment.manifest_validation import (
    ManifestFinding,
    validate_artifact_manifest,
    validate_reproducibility_manifest,
)
from frontier_agent_containment.release_acquisition import (
    GOVERNING_DOCUMENT_REGISTRY_V0_1,
    GitProvenance,
    GoverningDocumentAcquisition,
    ReleaseAcquisitionFinding,
    RuntimeDependencyClosure,
    RuntimeEnvironmentFacts,
    validate_release_build_consistency,
)
from frontier_agent_containment.release_validation import (
    ReleaseValidationFinding,
    validate_release_artifact_version_gates,
)
from frontier_agent_containment.schema_validation import (
    ExternalSchemaReferenceError,
    SchemaStore,
    SchemaStoreError,
    UnknownSchemaReferenceError,
    validate_instance,
)


JsonObject: TypeAlias = Mapping[str, Any]
PathInput: TypeAlias = str | os.PathLike[str]

_RELEASE_PROFILE_SCHEMA_ID: Final = (
    "urn:frontier-agent-containment:schema:release-profile:0.1.0"
)
_ARTIFACT_MANIFEST_SCHEMA_ID: Final = (
    "urn:frontier-agent-containment:schema:artifact-manifest:0.1.0"
)
_REPRODUCIBILITY_MANIFEST_SCHEMA_ID: Final = (
    "urn:frontier-agent-containment:schema:reproducibility-manifest:0.1.0"
)
_RELEASE_BUILD_SCHEMA_ID: Final = (
    "urn:frontier-agent-containment:schema:release-build-record:0.1.0"
)
_FILE_ORDER: Final = (
    "artifact-manifest.json",
    "release-build.json",
    "reproducibility-manifest.json",
)
_REQUIRED_FILES: Final = frozenset(_FILE_ORDER)
_GENERATED_VERSIONS: Final = (
    ("artifact-manifest.json", "manifest_version"),
    ("release-build.json", "build_version"),
    ("reproducibility-manifest.json", "reproducibility_version"),
)
_PHASE_ARRAYS: Final = (
    "scenario_subset",
    "control_subset",
    "scheduled_run_ids",
    "run_ids",
)
_SCHEMA_FAILURES: Final = (
    SchemaError,
    SchemaStoreError,
    ExternalSchemaReferenceError,
    UnknownSchemaReferenceError,
)


class ReleaseIntegrityAuditErrorCode(str, Enum):
    """Closed Stage 12E-4 audit-layer finding taxonomy."""

    AUDIT_PACKAGE_LAYOUT_INVALID = "AUDIT_PACKAGE_LAYOUT_INVALID"
    AUDIT_PACKAGE_READ_FAILED = "AUDIT_PACKAGE_READ_FAILED"
    AUDIT_JSON_INVALID = "AUDIT_JSON_INVALID"
    AUDIT_PHYSICAL_SERIALIZATION_INVALID = (
        "AUDIT_PHYSICAL_SERIALIZATION_INVALID"
    )
    AUDIT_GENERATED_VERSION_INVALID = "AUDIT_GENERATED_VERSION_INVALID"
    AUDIT_DETERMINISTIC_ORDER_INVALID = "AUDIT_DETERMINISTIC_ORDER_INVALID"
    AUDIT_RELEASE_BINDING_INVALID = "AUDIT_RELEASE_BINDING_INVALID"
    AUDIT_DEPENDENCY_PROVENANCE_INCOMPLETE = (
        "AUDIT_DEPENDENCY_PROVENANCE_INCOMPLETE"
    )
    AUDIT_VALIDATION_FAILED = "AUDIT_VALIDATION_FAILED"


@dataclass(frozen=True, slots=True)
class ReleaseIntegrityAuditFinding:
    """One immutable Stage 12E-4 finding with optional source evidence."""

    code: ReleaseIntegrityAuditErrorCode
    message: str
    field_path: str
    source: str | None = None
    source_code: str | None = None
    source_field_path: str | None = None
    source_message: str | None = None


@dataclass(frozen=True, slots=True)
class ReleaseIntegrityAuditResult:
    """Immutable result of auditing one persisted release directory."""

    release_id: str | None
    release_id_token: str | None
    findings: tuple[ReleaseIntegrityAuditFinding, ...]
    reproducibility_manifest_digest: str | None
    integrity_tag_annotation: str | None

    @property
    def passed(self) -> bool:
        """Return true exactly when the audit produced no findings."""

        return len(self.findings) == 0


class ReleaseIntegrityAuditError(ValueError):
    """Assertion-layer error carrying the complete immutable audit result."""

    def __init__(self, result: ReleaseIntegrityAuditResult) -> None:
        self.result = result
        self.findings = result.findings
        super().__init__(
            f"research release integrity audit has {len(self.findings)} finding(s)"
        )


@dataclass(frozen=True, slots=True)
class _PackageInspection:
    root_usable: bool
    readable_files: tuple[str, ...]
    findings: tuple[ReleaseIntegrityAuditFinding, ...]


class _DuplicateJsonKeyError(ValueError):
    def __init__(self, key: str) -> None:
        super().__init__(f"duplicate JSON object member: {key!r}")


def audit_research_release_integrity(
    release_directory: PathInput,
    *,
    release_profile: Mapping[str, Any],
    artifact_documents_by_locator: Mapping[str, Mapping[str, Any]],
    rejected_bytes_by_locator: Mapping[str, bytes],
    schema_store: SchemaStore,
    git_provenance: GitProvenance,
    governing_documents: GoverningDocumentAcquisition,
    runtime_dependency_closure: RuntimeDependencyClosure,
    runtime_environment_facts: RuntimeEnvironmentFacts,
    environment_artifact: Mapping[str, Any],
) -> ReleaseIntegrityAuditResult:
    """Audit a caller-supplied persisted Stage 12E-3 release directory."""

    profile_findings: list[ReleaseIntegrityAuditFinding] = []
    package_findings: list[ReleaseIntegrityAuditFinding] = []
    file_findings: list[ReleaseIntegrityAuditFinding] = []
    version_findings: list[ReleaseIntegrityAuditFinding] = []
    order_findings: list[ReleaseIntegrityAuditFinding] = []
    binding_findings: list[ReleaseIntegrityAuditFinding] = []
    stage12d_findings: list[ReleaseIntegrityAuditFinding] = []
    identity_findings: list[ReleaseIntegrityAuditFinding] = []
    provenance_findings: list[ReleaseIntegrityAuditFinding] = []
    build_findings: list[ReleaseIntegrityAuditFinding] = []
    closure_findings: list[ReleaseIntegrityAuditFinding] = []
    reproducibility_findings: list[ReleaseIntegrityAuditFinding] = []

    profile_error = _schema_finding(
        release_profile,
        _RELEASE_PROFILE_SCHEMA_ID,
        schema_store,
        label="Release Profile",
        namespace="/release-profile",
    )
    profile_valid = profile_error is None
    if profile_error is not None:
        profile_findings.append(profile_error)

    release_id: str | None = None
    release_id_token: str | None = None
    release_phase: str | None = None
    if profile_valid:
        release_id = release_profile["release_id"]
        release_id_token = release_id.removeprefix("release:")
        release_phase = release_profile["release_phase"]

    try:
        directory = Path(release_directory)
    except (TypeError, ValueError) as error:
        inspection = _PackageInspection(
            root_usable=False,
            readable_files=(),
            findings=(
                _native_finding(
                    ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
                    f"release directory path is invalid: {_bounded(error)}",
                    "/",
                ),
            ),
        )
    else:
        inspection = _inspect_package(directory)
    package_findings.extend(inspection.findings)

    raw_by_name: dict[str, bytes] = {}
    parsed_by_name: dict[str, Any] = {}
    if inspection.root_usable:
        for name in _FILE_ORDER:
            if name not in inspection.readable_files:
                continue
            path = directory / name
            try:
                raw = _read_exact_bytes(path)
            except OSError as error:
                package_findings.append(
                    _native_finding(
                        ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_READ_FAILED,
                        f"required release file cannot be read: {_bounded(error)}",
                        f"/{name}",
                    )
                )
                continue
            raw_by_name[name] = raw
            try:
                parsed = _parse_strict_json(raw)
            except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKeyError, ValueError) as error:
                file_findings.append(
                    _native_finding(
                        ReleaseIntegrityAuditErrorCode.AUDIT_JSON_INVALID,
                        f"strict JSON parsing failed: {_bounded(error)}",
                        f"/{name}",
                    )
                )
                continue
            parsed_by_name[name] = parsed
            try:
                expected_bytes = _serialize_physical_json(parsed)
            except (TypeError, ValueError) as error:
                file_findings.append(
                    _native_finding(
                        ReleaseIntegrityAuditErrorCode.AUDIT_JSON_INVALID,
                        f"parsed JSON is outside the physical JSON domain: {_bounded(error)}",
                        f"/{name}",
                    )
                )
            else:
                if expected_bytes != raw:
                    file_findings.append(
                        _native_finding(
                            ReleaseIntegrityAuditErrorCode.
                            AUDIT_PHYSICAL_SERIALIZATION_INVALID,
                            "persisted bytes do not equal the frozen physical JSON serialization",
                            f"/{name}",
                        )
                    )

    parsed_artifact_manifest = parsed_by_name.get("artifact-manifest.json")
    parsed_release_build = parsed_by_name.get("release-build.json")
    parsed_reproducibility_manifest = parsed_by_name.get(
        "reproducibility-manifest.json"
    )
    artifact_manifest = _mapping(parsed_artifact_manifest)
    release_build = _mapping(parsed_release_build)
    reproducibility_manifest = _mapping(
        parsed_reproducibility_manifest
    )

    artifact_schema_error = _parsed_schema_finding(
        parsed_artifact_manifest,
        "artifact-manifest.json" in parsed_by_name,
        _ARTIFACT_MANIFEST_SCHEMA_ID,
        schema_store,
        label="Artifact Manifest",
        namespace="/artifact-manifest.json",
    )
    build_schema_error = _parsed_schema_finding(
        parsed_release_build,
        "release-build.json" in parsed_by_name,
        _RELEASE_BUILD_SCHEMA_ID,
        schema_store,
        label="Release Build Record",
        namespace="/release-build.json",
    )
    reproducibility_schema_error = _parsed_schema_finding(
        parsed_reproducibility_manifest,
        "reproducibility-manifest.json" in parsed_by_name,
        _REPRODUCIBILITY_MANIFEST_SCHEMA_ID,
        schema_store,
        label="Reproducibility Manifest",
        namespace="/reproducibility-manifest.json",
    )
    artifact_schema_valid = (
        artifact_manifest is not None and artifact_schema_error is None
    )
    build_schema_valid = release_build is not None and build_schema_error is None
    reproducibility_schema_valid = (
        reproducibility_manifest is not None
        and reproducibility_schema_error is None
    )

    parsed_mappings = {
        "artifact-manifest.json": artifact_manifest,
        "release-build.json": release_build,
        "reproducibility-manifest.json": reproducibility_manifest,
    }
    schema_validity = {
        "artifact-manifest.json": artifact_schema_valid,
        "release-build.json": build_schema_valid,
        "reproducibility-manifest.json": reproducibility_schema_valid,
    }
    for name, field in _GENERATED_VERSIONS:
        value = parsed_mappings[name]
        if schema_validity[name] and value is not None and value[field] != "0.1.0":
            version_findings.append(
                _native_finding(
                    ReleaseIntegrityAuditErrorCode.AUDIT_GENERATED_VERSION_INVALID,
                    f"generated {field} is {value[field]!r}; required value is '0.1.0'",
                    f"/{name}/{field}",
                )
            )

    if artifact_schema_valid and artifact_manifest is not None:
        _audit_artifact_order(artifact_manifest, order_findings)
    if build_schema_valid and release_build is not None:
        _audit_dependency_order(
            release_build["dependencies"],
            "/release-build.json/dependencies",
            order_findings,
        )
    if reproducibility_schema_valid and reproducibility_manifest is not None:
        _audit_reproducibility_order(reproducibility_manifest, order_findings)

    selected_documents: dict[str, Mapping[str, Any]] = {}
    selected_rejected: dict[str, bytes] = {}
    active_artifacts: dict[str, list[Mapping[str, Any]]] = {}
    if profile_valid:
        selected_documents, selected_rejected, active_artifacts = _selected_inputs(
            release_profile,
            artifact_documents_by_locator,
            rejected_bytes_by_locator,
        )

    if (
        profile_valid
        and artifact_schema_valid
        and build_schema_valid
        and reproducibility_schema_valid
        and artifact_manifest is not None
        and release_build is not None
        and reproducibility_manifest is not None
        and release_id is not None
        and release_id_token is not None
        and release_phase is not None
    ):
        _audit_release_bindings(
            release_profile,
            artifact_manifest,
            release_build,
            reproducibility_manifest,
            git_provenance,
            runtime_environment_facts,
            environment_artifact,
            artifact_documents_by_locator,
            binding_findings,
        )
    elif (
        profile_valid
        and artifact_schema_valid
        and artifact_manifest is not None
    ):
        _audit_artifact_whitelists(
            release_profile, artifact_manifest, binding_findings
        )

    if artifact_manifest is not None:
        if profile_valid:
            for finding in validate_artifact_manifest(
                artifact_manifest,
                artifact_documents_by_locator=selected_documents,
                rejected_bytes_by_locator=selected_rejected,
                schema_store=schema_store,
            ):
                stage12d_findings.append(
                    _wrap_source_finding(finding, "/artifact-manifest.json")
                )
        elif artifact_schema_error is not None:
            stage12d_findings.append(artifact_schema_error)
    elif artifact_schema_error is not None:
        stage12d_findings.append(artifact_schema_error)

    if profile_valid and artifact_manifest is not None:
        for finding in validate_release_artifact_version_gates(
            release_profile,
            artifact_manifest=artifact_manifest,
            artifact_documents_by_locator=selected_documents,
            rejected_bytes_by_locator=selected_rejected,
            schema_store=schema_store,
        ):
            identity_findings.append(
                _wrap_source_finding(finding, "/release-profile")
            )

    if (
        profile_valid
        and reproducibility_schema_valid
        and reproducibility_manifest is not None
        and release_phase is not None
        and isinstance(runtime_dependency_closure, RuntimeDependencyClosure)
    ):
        _audit_distribution_provenance(
            runtime_dependency_closure,
            release_phase,
            reproducibility_manifest["reproducibility_limitations"],
            provenance_findings,
        )

    if release_build is not None:
        if build_schema_error is not None:
            build_findings.append(build_schema_error)
        else:
            for finding in validate_release_build_consistency(
                release_build,
                runtime_environment_facts,
            ):
                build_findings.append(
                    _wrap_source_finding(finding, "/release-build.json")
                )
    elif build_schema_error is not None:
        build_findings.append(build_schema_error)

    if (
        profile_valid
        and artifact_schema_valid
        and build_schema_valid
        and reproducibility_schema_valid
        and artifact_manifest is not None
        and release_build is not None
        and reproducibility_manifest is not None
    ):
        _audit_projection_closure(
            artifact_manifest,
            release_build,
            reproducibility_manifest,
            governing_documents,
            runtime_dependency_closure,
            closure_findings,
        )

    can_validate_reproducibility = (
        profile_valid
        and artifact_schema_valid
        and build_schema_valid
        and artifact_manifest is not None
        and release_build is not None
        and reproducibility_manifest is not None
        and release_id_token is not None
        and isinstance(git_provenance, GitProvenance)
        and isinstance(governing_documents, GoverningDocumentAcquisition)
        and isinstance(runtime_dependency_closure, RuntimeDependencyClosure)
        and isinstance(runtime_environment_facts, RuntimeEnvironmentFacts)
        and isinstance(environment_artifact, Mapping)
    )
    if can_validate_reproducibility:
        trusted_environment, trusted_error = _trusted_environment(
            environment_artifact,
            release_build,
            runtime_environment_facts,
        )
        if trusted_error is not None:
            reproducibility_findings.append(trusted_error)
        elif trusted_environment is not None:
            for finding in validate_reproducibility_manifest(
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
                repository_provenance=_repository_projection(git_provenance),
                resolved_dependencies=(
                    runtime_dependency_closure.resolved_dependencies
                ),
                trusted_environment=trusted_environment,
                artifact_manifest_external_locator=(
                    f"releases/{release_id_token}/artifact-manifest.json"
                ),
                rejected_bytes_by_locator=selected_rejected,
            ):
                reproducibility_findings.append(
                    _wrap_source_finding(
                        finding,
                        "/reproducibility-manifest.json",
                    )
                )
    elif reproducibility_schema_error is not None:
        reproducibility_findings.append(reproducibility_schema_error)

    groups = (
        _sorted_native(profile_findings),
        _sorted_native(package_findings),
        tuple(file_findings),
        _sorted_native(version_findings),
        _sorted_native(order_findings),
        _sorted_native(binding_findings),
        tuple(stage12d_findings),
        tuple(identity_findings),
        _sorted_native(provenance_findings),
        tuple(build_findings),
        _sorted_native(closure_findings),
        tuple(reproducibility_findings),
    )
    findings = tuple(item for group in groups for item in group)
    if findings or reproducibility_manifest is None:
        return ReleaseIntegrityAuditResult(
            release_id=release_id,
            release_id_token=release_id_token,
            findings=findings,
            reproducibility_manifest_digest=None,
            integrity_tag_annotation=None,
        )

    try:
        digest = canonical_sha256(dict(reproducibility_manifest))
    except IntegrityError as error:
        digest_finding = _validation_failure(
            message=f"Reproducibility Manifest canonicalization failed: {_bounded(error)}",
            field_path="/reproducibility-manifest.json",
            source=type(error).__name__,
            source_code=type(error).__name__,
            source_field_path="/",
            source_message=_bounded(error),
        )
        return ReleaseIntegrityAuditResult(
            release_id=release_id,
            release_id_token=release_id_token,
            findings=(digest_finding,),
            reproducibility_manifest_digest=None,
            integrity_tag_annotation=None,
        )
    return ReleaseIntegrityAuditResult(
        release_id=release_id,
        release_id_token=release_id_token,
        findings=(),
        reproducibility_manifest_digest=digest,
        integrity_tag_annotation=(
            "reproducibility-manifest-sha256: " + digest
        ),
    )


def assert_research_release_integrity(
    release_directory: PathInput,
    *,
    release_profile: Mapping[str, Any],
    artifact_documents_by_locator: Mapping[str, Mapping[str, Any]],
    rejected_bytes_by_locator: Mapping[str, bytes],
    schema_store: SchemaStore,
    git_provenance: GitProvenance,
    governing_documents: GoverningDocumentAcquisition,
    runtime_dependency_closure: RuntimeDependencyClosure,
    runtime_environment_facts: RuntimeEnvironmentFacts,
    environment_artifact: Mapping[str, Any],
) -> ReleaseIntegrityAuditResult:
    """Return a passed audit result or raise with the complete failed result."""

    result = audit_research_release_integrity(
        release_directory,
        release_profile=release_profile,
        artifact_documents_by_locator=artifact_documents_by_locator,
        rejected_bytes_by_locator=rejected_bytes_by_locator,
        schema_store=schema_store,
        git_provenance=git_provenance,
        governing_documents=governing_documents,
        runtime_dependency_closure=runtime_dependency_closure,
        runtime_environment_facts=runtime_environment_facts,
        environment_artifact=environment_artifact,
    )
    if not result.passed:
        raise ReleaseIntegrityAuditError(result)
    return result


def _inspect_package(directory: Path) -> _PackageInspection:
    try:
        root_stat = os.lstat(directory)
    except OSError as error:
        return _PackageInspection(
            False,
            (),
            (
                _native_finding(
                    ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
                    f"release directory cannot be inspected: {_bounded(error)}",
                    "/",
                ),
            ),
        )
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        return _PackageInspection(
            False,
            (),
            (
                _native_finding(
                    ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
                    "release directory must be an ordinary non-symlink directory under lstat",
                    "/",
                ),
            ),
        )
    try:
        names = tuple(sorted(entry.name for entry in os.scandir(directory)))
    except OSError as error:
        return _PackageInspection(
            False,
            (),
            (
                _native_finding(
                    ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_READ_FAILED,
                    f"release directory children cannot be enumerated: {_bounded(error)}",
                    "/",
                ),
            ),
        )

    findings: list[ReleaseIntegrityAuditFinding] = []
    actual = set(names)
    for name in sorted(_REQUIRED_FILES - actual):
        findings.append(
            _native_finding(
                ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
                "required direct child is missing",
                f"/{name}",
            )
        )
    additional = tuple(sorted(actual - _REQUIRED_FILES))
    if additional:
        findings.append(
            _native_finding(
                ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
                "release directory has additional direct child(ren): "
                + ", ".join(additional),
                "/",
            )
        )

    readable: list[str] = []
    for name in _FILE_ORDER:
        if name not in actual:
            continue
        try:
            child_stat = os.lstat(directory / name)
        except OSError as error:
            findings.append(
                _native_finding(
                    ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
                    f"required child cannot be inspected: {_bounded(error)}",
                    f"/{name}",
                )
            )
            continue
        if stat.S_ISLNK(child_stat.st_mode) or not stat.S_ISREG(child_stat.st_mode):
            findings.append(
                _native_finding(
                    ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
                    "required child must be an ordinary non-symlink regular file under lstat",
                    f"/{name}",
                )
            )
            continue
        readable.append(name)
    return _PackageInspection(True, tuple(readable), tuple(findings))


def _read_exact_bytes(path: Path) -> bytes:
    with path.open("rb") as stream:
        return stream.read()


def _parse_strict_json(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="strict")
    return json.loads(
        text,
        object_pairs_hook=_object_without_duplicate_keys,
        parse_constant=_reject_json_constant,
    )


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(key)
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-JSON numeric constant: {value}")


def _serialize_physical_json(value: Any) -> bytes:
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


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _parsed_schema_finding(
    value: Any,
    was_parsed: bool,
    schema_id: str,
    schema_store: SchemaStore,
    *,
    label: str,
    namespace: str,
) -> ReleaseIntegrityAuditFinding | None:
    if not was_parsed:
        return None
    return _schema_finding(
        value,
        schema_id,
        schema_store,
        label=label,
        namespace=namespace,
    )


def _schema_finding(
    value: Any,
    schema_id: str,
    schema_store: SchemaStore,
    *,
    label: str,
    namespace: str,
) -> ReleaseIntegrityAuditFinding | None:
    try:
        schema = schema_store.get(schema_id)
    except (AttributeError, TypeError) as error:
        return _schema_exception_finding(label, namespace, error)
    if schema is None:
        return _validation_failure(
            message=f"required local {label} schema {schema_id!r} is absent",
            field_path=namespace,
            source="SchemaStore",
            source_code="REQUIRED_SCHEMA_MISSING",
            source_field_path="/",
            source_message=f"required schema {schema_id!r} is absent",
        )
    try:
        validate_instance(value, schema, schema_store=schema_store)
    except ValidationError as error:
        pointer = _pointer(*error.absolute_path)
        message = _bounded_message(error.message)
        return _validation_failure(
            message=(
                f"{label} Draft 2020-12 validation failed: {message}"
            ),
            field_path=_join_namespace(namespace, pointer),
            source=type(error).__name__,
            source_code=str(error.validator),
            source_field_path=pointer,
            source_message=message,
        )
    except _SCHEMA_FAILURES as error:
        return _schema_exception_finding(label, namespace, error)
    return None


def _schema_exception_finding(
    label: str,
    namespace: str,
    error: Exception,
) -> ReleaseIntegrityAuditFinding:
    message = _bounded(error)
    return _validation_failure(
        message=f"{label} local schema validation failed: {message}",
        field_path=namespace,
        source=type(error).__name__,
        source_code=type(error).__name__,
        source_field_path="/",
        source_message=message,
    )


def _selected_inputs(
    release_profile: Mapping[str, Any],
    artifact_documents_by_locator: Mapping[str, Mapping[str, Any]],
    rejected_bytes_by_locator: Mapping[str, bytes],
) -> tuple[
    dict[str, Mapping[str, Any]],
    dict[str, bytes],
    dict[str, list[Mapping[str, Any]]],
]:
    documents: dict[str, Mapping[str, Any]] = {}
    rejected: dict[str, bytes] = {}
    active: dict[str, list[Mapping[str, Any]]] = {}
    for selection in release_profile["active_artifacts"]:
        locator = selection["locator"]
        document = artifact_documents_by_locator.get(locator)
        if document is not None:
            documents[locator] = document
            active.setdefault(selection["artifact_family"], []).append(document)
    for selection in release_profile["rejected_inputs"]:
        locator = selection["locator"]
        if locator in rejected_bytes_by_locator:
            rejected[locator] = rejected_bytes_by_locator[locator]
    return documents, rejected, active


def _audit_artifact_order(
    manifest: Mapping[str, Any],
    findings: list[ReleaseIntegrityAuditFinding],
) -> None:
    _audit_sorted_array(
        manifest["artifacts"],
        lambda item: (
            item["artifact_family"],
            item["artifact_id"],
            item["locator"],
        ),
        "/artifact-manifest.json/artifacts",
        "Artifact Manifest artifacts are not in exact deterministic order",
        findings,
    )
    _audit_sorted_array(
        manifest["rejected_inputs"],
        lambda item: (item["rejected_input_id"], item["locator"]),
        "/artifact-manifest.json/rejected_inputs",
        "Artifact Manifest rejected_inputs are not in exact deterministic order",
        findings,
    )


def _audit_reproducibility_order(
    manifest: Mapping[str, Any],
    findings: list[ReleaseIntegrityAuditFinding],
) -> None:
    _audit_sorted_array(
        manifest["model_provider_identities"],
        lambda item: (
            item["agent_condition_id"],
            item["model_identifier"],
            canonicalize_json(dict(item)),
        ),
        "/reproducibility-manifest.json/model_provider_identities",
        "model_provider_identities are not in exact deterministic order",
        findings,
    )
    _audit_sorted_array(
        manifest["reproducibility_limitations"],
        lambda item: item.encode("utf-8"),
        "/reproducibility-manifest.json/reproducibility_limitations",
        "reproducibility_limitations are not in exact UTF-8 byte order",
        findings,
    )
    _audit_sorted_array(
        manifest["schema_set"],
        lambda item: item["schema_id"],
        "/reproducibility-manifest.json/schema_set",
        "schema_set is not in exact schema_id order",
        findings,
    )
    governing = tuple(item["document_id"] for item in manifest["governing_documents"])
    expected_governing = tuple(
        item.document_id for item in GOVERNING_DOCUMENT_REGISTRY_V0_1
    )
    if Counter(governing) == Counter(expected_governing) and governing != expected_governing:
        findings.append(
            _native_finding(
                ReleaseIntegrityAuditErrorCode.AUDIT_DETERMINISTIC_ORDER_INVALID,
                "governing_documents do not follow the frozen nine-entry registry order",
                "/reproducibility-manifest.json/governing_documents",
            )
        )
    _audit_dependency_order(
        manifest["dependencies"],
        "/reproducibility-manifest.json/dependencies",
        findings,
    )
    for field in _PHASE_ARRAYS:
        _audit_sorted_array(
            manifest[field],
            lambda item: item,
            f"/reproducibility-manifest.json/{field}",
            f"{field} is not in exact lexicographic string order",
            findings,
        )
    _audit_sorted_array(
        manifest["repetition_identities"],
        lambda item: (
            item["repetition_id"],
            item.get("scheduled_run_id", ""),
            item.get("run_id", ""),
            canonicalize_json(dict(item)),
        ),
        "/reproducibility-manifest.json/repetition_identities",
        "repetition_identities are not in exact deterministic order",
        findings,
    )


def _audit_dependency_order(
    values: Sequence[Mapping[str, Any]],
    field_path: str,
    findings: list[ReleaseIntegrityAuditFinding],
) -> None:
    _audit_sorted_array(
        values,
        lambda item: (item["name"], item["version"]),
        field_path,
        "dependencies are not ordered by exact (name, version) strings",
        findings,
    )


def _audit_sorted_array(
    values: Sequence[Any],
    key: Any,
    field_path: str,
    message: str,
    findings: list[ReleaseIntegrityAuditFinding],
) -> None:
    actual = tuple(values)
    try:
        expected = tuple(sorted(actual, key=key))
    except (KeyError, TypeError, IntegrityError):
        return
    if actual != expected:
        findings.append(
            _native_finding(
                ReleaseIntegrityAuditErrorCode.AUDIT_DETERMINISTIC_ORDER_INVALID,
                message,
                field_path,
            )
        )

def _audit_artifact_whitelists(
    release_profile: Mapping[str, Any],
    artifact_manifest: Mapping[str, Any],
    findings: list[ReleaseIntegrityAuditFinding],
) -> None:
    expected_artifacts = sorted(
        (
            item["artifact_family"],
            item["artifact_id"],
            item["locator"],
        )
        for item in release_profile["active_artifacts"]
    )
    actual_artifacts = sorted(
        (
            item["artifact_family"],
            item["artifact_id"],
            item["locator"],
        )
        for item in artifact_manifest["artifacts"]
    )
    if actual_artifacts != expected_artifacts:
        findings.append(
            _binding_finding(
                "Artifact Manifest artifacts do not equal the Release Profile active whitelist",
                "/artifact-manifest.json/artifacts",
            )
        )
    expected_rejected = sorted(
        (item["rejected_input_id"], item["locator"])
        for item in release_profile["rejected_inputs"]
    )
    actual_rejected = sorted(
        (item["rejected_input_id"], item["locator"])
        for item in artifact_manifest["rejected_inputs"]
    )
    if actual_rejected != expected_rejected:
        findings.append(
            _binding_finding(
                "Artifact Manifest rejected_inputs do not equal the Release Profile rejected whitelist",
                "/artifact-manifest.json/rejected_inputs",
            )
        )




def _audit_release_bindings(
    release_profile: Mapping[str, Any],
    artifact_manifest: Mapping[str, Any],
    release_build: Mapping[str, Any],
    reproducibility_manifest: Mapping[str, Any],
    git_provenance: GitProvenance,
    runtime_environment_facts: RuntimeEnvironmentFacts,
    environment_artifact: Mapping[str, Any],
    artifact_documents_by_locator: Mapping[str, Mapping[str, Any]],
    findings: list[ReleaseIntegrityAuditFinding],
) -> None:
    expected_artifacts = sorted(
        (
            item["artifact_family"],
            item["artifact_id"],
            item["locator"],
        )
        for item in release_profile["active_artifacts"]
    )
    actual_artifacts = sorted(
        (
            item["artifact_family"],
            item["artifact_id"],
            item["locator"],
        )
        for item in artifact_manifest["artifacts"]
    )
    if actual_artifacts != expected_artifacts:
        findings.append(
            _binding_finding(
                "Artifact Manifest artifacts do not equal the Release Profile active whitelist",
                "/artifact-manifest.json/artifacts",
            )
        )
    expected_rejected = sorted(
        (item["rejected_input_id"], item["locator"])
        for item in release_profile["rejected_inputs"]
    )
    actual_rejected = sorted(
        (item["rejected_input_id"], item["locator"])
        for item in artifact_manifest["rejected_inputs"]
    )
    if actual_rejected != expected_rejected:
        findings.append(
            _binding_finding(
                "Artifact Manifest rejected_inputs do not equal the Release Profile rejected whitelist",
                "/artifact-manifest.json/rejected_inputs",
            )
        )

    release_id = release_profile["release_id"]
    release_id_token = release_id.removeprefix("release:")
    expected_build_id = f"build:{release_id_token}"
    if release_build["build_id"] != expected_build_id:
        findings.append(
            _binding_finding(
                f"Release Build build_id must equal {expected_build_id!r}",
                "/release-build.json/build_id",
            )
        )
    if reproducibility_manifest["environment"]["build_identity"] != release_build["build_id"]:
        findings.append(
            _binding_finding(
                "Reproducibility environment.build_identity does not equal Release Build build_id",
                "/reproducibility-manifest.json/environment/build_identity",
            )
        )
    if release_build["release_id"] != release_id:
        findings.append(
            _binding_finding(
                "Release Build release_id does not equal Release Profile release_id",
                "/release-build.json/release_id",
            )
        )
    if reproducibility_manifest["release_phase"] != release_profile["release_phase"]:
        findings.append(
            _binding_finding(
                "Reproducibility release_phase does not equal Release Profile release_phase",
                "/reproducibility-manifest.json/release_phase",
            )
        )

    expected_tag = f"research-release-{release_id_token}"
    if release_profile["source_release_tag_identity"] != expected_tag:
        findings.append(
            _binding_finding(
                "Release Profile source tag does not match its release phase/version",
                "/release-profile/source_release_tag_identity",
            )
        )
    if git_provenance.release_tag_identity != release_profile["source_release_tag_identity"]:
        findings.append(
            _binding_finding(
                "Git provenance source tag does not equal Release Profile source tag",
                "/release-profile/source_release_tag_identity",
            )
        )
    if git_provenance.release_tag_target_commit_sha != git_provenance.repository_commit_sha:
        findings.append(
            _binding_finding(
                "Git provenance source tag target does not equal repository commit",
                "/reproducibility-manifest.json/release_tag_target_commit_sha",
            )
        )

    expected_environment = release_profile["environment_reference"]
    candidate_environment = reproducibility_manifest["environment"]
    environment_id = environment_artifact.get("environment_id")
    environment_values = (
        expected_environment,
        environment_id,
        release_build["environment_reference"],
        candidate_environment["environment_reference"],
    )
    if expected_environment == "NOT_APPLICABLE" or len(set(environment_values)) != 1:
        findings.append(
            _binding_finding(
                "Release Profile, Environment, Build, and Reproducibility environment identities are not exactly equal",
                "/reproducibility-manifest.json/environment/environment_reference",
            )
        )
    if runtime_environment_facts.environment_reference != expected_environment:
        findings.append(
            _binding_finding(
                "RuntimeEnvironmentFacts environment_reference does not equal Release Profile",
                "/release-profile/environment_reference",
            )
        )
    selected_environment_documents = tuple(
        artifact_documents_by_locator.get(item["locator"])
        for item in release_profile["active_artifacts"]
        if item["artifact_family"] == "environment"
        and item["artifact_id"] == expected_environment
    )
    if (
        len(selected_environment_documents) != 1
        or selected_environment_documents[0] != environment_artifact
    ):
        findings.append(
            _binding_finding(
                "selected scientific Environment does not equal environment_artifact",
                "/release-profile/environment_reference",
            )
        )


def _audit_distribution_provenance(
    closure: RuntimeDependencyClosure,
    release_phase: str,
    limitations: Sequence[str],
    findings: list[ReleaseIntegrityAuditFinding],
) -> None:
    missing = tuple(
        dependency.name
        for dependency in closure.dependencies
        if dependency.distribution_provenance is None
    )
    if missing and (
        release_phase in {"PILOT", "CONFIRMATORY"} or not limitations
    ):
        findings.append(
            _native_finding(
                ReleaseIntegrityAuditErrorCode.
                AUDIT_DEPENDENCY_PROVENANCE_INCOMPLETE,
                "original distribution provenance is missing for: "
                + ", ".join(missing),
                "/release-build.json/dependencies",
            )
        )


def _audit_projection_closure(
    artifact_manifest: Mapping[str, Any],
    release_build: Mapping[str, Any],
    reproducibility_manifest: Mapping[str, Any],
    governing_documents: GoverningDocumentAcquisition,
    closure: RuntimeDependencyClosure,
    findings: list[ReleaseIntegrityAuditFinding],
) -> None:
    required_schema_ids = {
        item["schema_id"] for item in artifact_manifest["artifacts"]
    }
    actual_schema_ids = {
        item["schema_id"] for item in reproducibility_manifest["schema_set"]
    }
    if actual_schema_ids != required_schema_ids:
        findings.append(
            _binding_finding(
                "schema_set does not contain exactly the schemas used by active Artifact Manifest entries",
                "/reproducibility-manifest.json/schema_set",
            )
        )

    expected_governing = tuple(
        item.document_id for item in GOVERNING_DOCUMENT_REGISTRY_V0_1
    )
    actual_governing = tuple(
        item["document_id"]
        for item in reproducibility_manifest["governing_documents"]
    )
    acquired_governing = tuple(
        item.provenance.document_id for item in governing_documents.documents
    )
    if Counter(actual_governing) != Counter(expected_governing):
        findings.append(
            _binding_finding(
                "governing_documents membership does not equal the frozen nine-entry registry",
                "/reproducibility-manifest.json/governing_documents",
            )
        )
    if acquired_governing != expected_governing:
        findings.append(
            _binding_finding(
                "supplied governing acquisition does not follow the frozen nine-entry registry",
                "/reproducibility-manifest.json/governing_documents",
            )
        )

    expected_build = _expected_build_dependencies(closure)
    expected_repro = tuple(dict(item) for item in closure.resolved_dependencies)
    if not _records_equal_ignoring_order(release_build["dependencies"], expected_build):
        findings.append(
            _binding_finding(
                "Release Build dependencies do not equal the supplied RuntimeDependencyClosure projection",
                "/release-build.json/dependencies",
            )
        )
    if not _records_equal_ignoring_order(
        reproducibility_manifest["dependencies"], expected_repro
    ):
        findings.append(
            _binding_finding(
                "Reproducibility dependencies do not equal the supplied RuntimeDependencyClosure projection",
                "/reproducibility-manifest.json/dependencies",
            )
        )


def _expected_build_dependencies(
    closure: RuntimeDependencyClosure,
) -> tuple[dict[str, str], ...]:
    records: list[dict[str, str]] = []
    for dependency in closure.dependencies:
        record = {"name": dependency.name, "version": dependency.version}
        if dependency.distribution_provenance is not None:
            record["distribution_filename"] = (
                dependency.distribution_provenance.distribution_filename
            )
            record["distribution_digest"] = (
                dependency.distribution_provenance.distribution_digest
            )
        records.append(record)
    return tuple(records)


def _records_equal_ignoring_order(
    first: Sequence[Mapping[str, Any]],
    second: Sequence[Mapping[str, Any]],
) -> bool:
    try:
        first_bytes = sorted(canonicalize_json(dict(item)) for item in first)
        second_bytes = sorted(canonicalize_json(dict(item)) for item in second)
    except (TypeError, IntegrityError):
        return False
    return first_bytes == second_bytes


def _trusted_environment(
    environment_artifact: Mapping[str, Any],
    release_build: Mapping[str, Any],
    facts: RuntimeEnvironmentFacts,
) -> tuple[dict[str, Any] | None, ReleaseIntegrityAuditFinding | None]:
    try:
        environment = _copy_json(environment_artifact)
        build = _copy_json(release_build)
        if not isinstance(environment, dict) or not isinstance(build, dict):
            raise TypeError("trusted Environment and Build inputs must be JSON objects")
        environment_reference = environment["environment_id"]
        build_identity = build["build_id"]
        environment_digest = canonical_sha256(environment)
        build_digest = canonical_sha256(build)
    except (KeyError, TypeError, IntegrityError) as error:
        message = _bounded(error)
        return None, _validation_failure(
            message=f"trusted_environment cannot be independently constructed: {message}",
            field_path="/reproducibility-manifest.json/environment",
            source=type(error).__name__,
            source_code=type(error).__name__,
            source_field_path="/environment",
            source_message=message,
        )
    return (
        {
            "python_version": facts.python_version,
            "os_runtime_identity": facts.os_runtime_identity,
            "architecture": facts.architecture,
            "environment_reference": environment_reference,
            "build_identity": build_identity,
            "environment_content_digest": environment_digest,
            "build_content_digest": build_digest,
        },
        None,
    )


def _repository_projection(provenance: GitProvenance) -> dict[str, str]:
    return {
        "repository_object_format": provenance.repository_object_format,
        "repository_commit_sha": provenance.repository_commit_sha,
        "repository_tree_sha": provenance.repository_tree_sha,
        "release_tag_identity": provenance.release_tag_identity,
        "release_tag_object_sha": provenance.release_tag_object_sha,
        "release_tag_target_commit_sha": (
            provenance.release_tag_target_commit_sha
        ),
    }


def _copy_json(value: Any) -> Any:
    if value is None or type(value) in {bool, int, float, str}:
        return value
    if isinstance(value, Mapping):
        copied: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("JSON object keys must be exact strings")
            copied[key] = _copy_json(item)
        return copied
    if isinstance(value, (list, tuple)):
        return [_copy_json(item) for item in value]
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")


def _wrap_source_finding(
    finding: ManifestFinding | ReleaseValidationFinding | ReleaseAcquisitionFinding,
    namespace: str,
) -> ReleaseIntegrityAuditFinding:
    source = type(finding).__name__
    source_code = finding.code.value
    source_path = finding.field_path
    source_message = finding.message
    return _validation_failure(
        message=f"{source} {source_code}: {source_message}",
        field_path=_join_namespace(namespace, source_path),
        source=source,
        source_code=source_code,
        source_field_path=source_path,
        source_message=source_message,
    )


def _validation_failure(
    *,
    message: str,
    field_path: str,
    source: str,
    source_code: str,
    source_field_path: str,
    source_message: str,
) -> ReleaseIntegrityAuditFinding:
    return ReleaseIntegrityAuditFinding(
        code=ReleaseIntegrityAuditErrorCode.AUDIT_VALIDATION_FAILED,
        message=message,
        field_path=field_path,
        source=source,
        source_code=source_code,
        source_field_path=source_field_path,
        source_message=source_message,
    )


def _binding_finding(message: str, field_path: str) -> ReleaseIntegrityAuditFinding:
    return _native_finding(
        ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID,
        message,
        field_path,
    )


def _native_finding(
    code: ReleaseIntegrityAuditErrorCode,
    message: str,
    field_path: str,
) -> ReleaseIntegrityAuditFinding:
    return ReleaseIntegrityAuditFinding(code=code, message=message, field_path=field_path)


def _sorted_native(
    findings: Sequence[ReleaseIntegrityAuditFinding],
) -> tuple[ReleaseIntegrityAuditFinding, ...]:
    return tuple(
        sorted(
            findings,
            key=lambda item: (item.field_path, item.code.value, item.message),
        )
    )


def _pointer(*parts: str | int) -> str:
    if not parts:
        return "/"
    return "/" + "/".join(
        str(part).replace("~", "~0").replace("/", "~1") for part in parts
    )


def _join_namespace(namespace: str, pointer: str) -> str:
    return namespace if pointer == "/" else namespace + pointer


def _bounded(error: Exception) -> str:
    return _bounded_message(str(error))


def _bounded_message(message: str) -> str:
    return message[:2000]


__all__ = [
    "ReleaseIntegrityAuditErrorCode",
    "ReleaseIntegrityAuditFinding",
    "ReleaseIntegrityAuditResult",
    "ReleaseIntegrityAuditError",
    "audit_research_release_integrity",
    "assert_research_release_integrity",
]
