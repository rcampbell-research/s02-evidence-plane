"""Deterministic validation of caller-supplied reproducibility metadata.

Stage 12D verifies content binding, supplied-set completeness, and coherence of
explicit trusted facts.  It performs no filesystem discovery, Git or package
manager invocation, network access, persistent writes, evidence collection, or
security execution.  Matching digests and provenance facts do not establish
observation truth, universal completeness, producer authenticity, immutable
storage, or system security.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeAlias

from jsonschema.exceptions import SchemaError, ValidationError

from frontier_agent_containment.integrity import (
    IntegrityError,
    canonical_sha256,
    forensic_sha256_bytes,
)
from frontier_agent_containment.schema_validation import (
    ExternalSchemaReferenceError,
    SchemaStore,
    SchemaStoreError,
    UnknownSchemaReferenceError,
    validate_instance,
)
from frontier_agent_containment.semantic_validation import (
    ArtifactFamilyContractSpec,
    get_artifact_family_contract_spec,
    get_artifact_family_spec,
    validate_artifact_set,
)


JsonObject: TypeAlias = Mapping[str, Any]
ArtifactCollection: TypeAlias = Mapping[str, Iterable[JsonObject]]

ARTIFACT_MANIFEST_SCHEMA_ID = (
    "urn:frontier-agent-containment:schema:artifact-manifest:0.1.0"
)
REPRODUCIBILITY_MANIFEST_SCHEMA_ID = (
    "urn:frontier-agent-containment:schema:reproducibility-manifest:0.1.0"
)


class ManifestErrorCode(str, Enum):
    """Bounded Stage 12D reproducibility-validation finding codes."""

    MANIFEST_SCHEMA_INVALID = "MANIFEST_SCHEMA_INVALID"
    MANIFEST_REFERENCE_INVALID = "MANIFEST_REFERENCE_INVALID"
    MANIFEST_DIGEST_MISMATCH = "MANIFEST_DIGEST_MISMATCH"
    MANIFEST_IDENTITY_MISMATCH = "MANIFEST_IDENTITY_MISMATCH"
    MANIFEST_VERSION_MISMATCH = "MANIFEST_VERSION_MISMATCH"
    MANIFEST_SCHEMA_BINDING_INVALID = "MANIFEST_SCHEMA_BINDING_INVALID"
    MANIFEST_DUPLICATE_IDENTITY = "MANIFEST_DUPLICATE_IDENTITY"
    MANIFEST_INCOMPLETE = "MANIFEST_INCOMPLETE"
    REPRODUCIBILITY_PROVENANCE_INVALID = "REPRODUCIBILITY_PROVENANCE_INVALID"
    REPRODUCIBILITY_DEPENDENCY_INVALID = "REPRODUCIBILITY_DEPENDENCY_INVALID"
    REPRODUCIBILITY_ENVIRONMENT_INVALID = "REPRODUCIBILITY_ENVIRONMENT_INVALID"
    REPRODUCIBILITY_REFERENCE_INVALID = "REPRODUCIBILITY_REFERENCE_INVALID"
    REPRODUCIBILITY_PROVIDER_INVALID = "REPRODUCIBILITY_PROVIDER_INVALID"


@dataclass(frozen=True, slots=True)
class ManifestFinding:
    """One immutable and deterministically ordered manifest finding."""

    code: ManifestErrorCode
    message: str
    manifest_family: str
    field_path: str
    artifact_family: str | None = None
    artifact_id: str | None = None
    locator: str | None = None
    referenced_id: str | None = None


class ManifestValidationError(ValueError):
    """Aggregate exception raised by assert-style validation helpers."""

    def __init__(self, findings: Iterable[ManifestFinding]) -> None:
        self.findings = tuple(findings)
        super().__init__(f"manifest has {len(self.findings)} finding(s)")


def validate_artifact_manifest(
    manifest: JsonObject,
    *,
    artifact_documents_by_locator: Mapping[str, JsonObject],
    rejected_bytes_by_locator: Mapping[str, bytes],
    schema_store: SchemaStore,
) -> tuple[ManifestFinding, ...]:
    """Validate one Artifact Manifest against explicitly supplied content.

    Completeness is established only over the two caller-supplied mappings.  No
    inference is made about artifacts that may exist elsewhere.
    """

    structural = _structural_finding(
        manifest,
        manifest_family="artifact_manifest",
        schema_id=ARTIFACT_MANIFEST_SCHEMA_ID,
        schema_store=schema_store,
    )
    if structural is not None:
        return (structural,)

    findings: list[ManifestFinding] = []
    entries = list(manifest["artifacts"])
    rejected = list(manifest["rejected_inputs"])
    _validate_manifest_uniqueness(entries, rejected, findings)
    _validate_locator_closure(
        entries,
        artifact_documents_by_locator,
        field="artifacts",
        findings=findings,
    )
    _validate_locator_closure(
        rejected,
        rejected_bytes_by_locator,
        field="rejected_inputs",
        findings=findings,
    )

    for index, entry in enumerate(entries):
        locator = entry["locator"]
        document = artifact_documents_by_locator.get(locator)
        if document is None:
            continue
        _validate_artifact_entry(entry, document, index, schema_store, findings)

    for index, record in enumerate(rejected):
        locator = record["locator"]
        raw = rejected_bytes_by_locator.get(locator)
        if raw is None:
            continue
        actual = forensic_sha256_bytes(raw)
        if actual != record["forensic_byte_digest"]:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_DIGEST_MISMATCH,
                "forensic byte digest does not match the exact supplied rejected bytes",
                "artifact_manifest",
                _pointer("rejected_inputs", index, "forensic_byte_digest"),
                locator=locator,
                referenced_id=record["rejected_input_id"],
            )

    _validate_artifact_scope(manifest, entries, artifact_documents_by_locator, findings)
    return _sorted(findings)


def assert_artifact_manifest_valid(
    manifest: JsonObject,
    *,
    artifact_documents_by_locator: Mapping[str, JsonObject],
    rejected_bytes_by_locator: Mapping[str, bytes],
    schema_store: SchemaStore,
) -> None:
    """Raise when :func:`validate_artifact_manifest` returns findings."""

    findings = validate_artifact_manifest(
        manifest,
        artifact_documents_by_locator=artifact_documents_by_locator,
        rejected_bytes_by_locator=rejected_bytes_by_locator,
        schema_store=schema_store,
    )
    if findings:
        raise ManifestValidationError(findings)


def validate_reproducibility_manifest(
    manifest: JsonObject,
    *,
    artifact_manifest: JsonObject,
    artifact_documents_by_locator: Mapping[str, JsonObject],
    schema_store: SchemaStore,
    active_artifacts: ArtifactCollection | None,
    governing_document_bytes_by_id: Mapping[str, bytes],
    governing_document_provenance_by_id: Mapping[str, JsonObject] | None,
    repository_provenance: JsonObject,
    resolved_dependencies: Sequence[JsonObject],
    trusted_environment: JsonObject | None = None,
    artifact_manifest_external_locator: str | None = None,
    rejected_bytes_by_locator: Mapping[str, bytes] | None = None,
) -> tuple[ManifestFinding, ...]:
    """Validate reproducibility metadata against caller-supplied trusted facts.

    The supplied provenance, dependency, and environment records are coherence
    inputs, not self-authenticating facts.  Their acquisition belongs to the
    later release audit.
    """

    structural = _structural_finding(
        manifest,
        manifest_family="reproducibility_manifest",
        schema_id=REPRODUCIBILITY_MANIFEST_SCHEMA_ID,
        schema_store=schema_store,
    )
    if structural is not None:
        return (structural,)

    findings: list[ManifestFinding] = []
    artifact_findings = validate_artifact_manifest(
        artifact_manifest,
        artifact_documents_by_locator=artifact_documents_by_locator,
        rejected_bytes_by_locator=rejected_bytes_by_locator or {},
        schema_store=schema_store,
    )
    for finding in artifact_findings:
        _add(
            findings,
            ManifestErrorCode.REPRODUCIBILITY_REFERENCE_INVALID,
            f"supplied Artifact Manifest is not coherent: {finding.code.value}: {finding.message}",
            "reproducibility_manifest",
            "/artifact_manifest_digest",
            artifact_family=finding.artifact_family,
            artifact_id=finding.artifact_id,
            locator=finding.locator,
            referenced_id=finding.referenced_id,
        )

    try:
        artifact_manifest_digest = canonical_sha256(artifact_manifest)
    except IntegrityError as error:
        _add(
            findings,
            ManifestErrorCode.MANIFEST_DIGEST_MISMATCH,
            f"Artifact Manifest cannot be canonicalized: {error}",
            "reproducibility_manifest",
            "/artifact_manifest_digest",
        )
    else:
        if artifact_manifest_digest != manifest["artifact_manifest_digest"]:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_DIGEST_MISMATCH,
                "Artifact Manifest canonical content digest does not match",
                "reproducibility_manifest",
                "/artifact_manifest_digest",
                locator=manifest["artifact_manifest_locator"],
            )

    if (
        artifact_manifest_external_locator is not None
        and artifact_manifest_external_locator != manifest["artifact_manifest_locator"]
    ):
        _add(
            findings,
            ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID,
            "Artifact Manifest locator differs from the supplied external locator fact",
            "reproducibility_manifest",
            "/artifact_manifest_locator",
            locator=manifest["artifact_manifest_locator"],
            referenced_id=artifact_manifest_external_locator,
        )

    _validate_schema_set(manifest, artifact_manifest, schema_store, findings)
    _validate_governing_documents(
        manifest,
        governing_document_bytes_by_id,
        governing_document_provenance_by_id,
        findings,
    )
    _validate_repository_provenance(manifest, repository_provenance, findings)
    _validate_dependencies(manifest, resolved_dependencies, findings)
    _validate_environment(manifest, trusted_environment, findings)
    if active_artifacts is not None:
        _validate_active_artifacts(manifest, active_artifacts, schema_store, findings)

    return _sorted(findings)


def assert_reproducibility_manifest_valid(
    manifest: JsonObject,
    **context: Any,
) -> None:
    """Raise when :func:`validate_reproducibility_manifest` returns findings."""

    findings = validate_reproducibility_manifest(manifest, **context)
    if findings:
        raise ManifestValidationError(findings)


def _validate_manifest_uniqueness(
    entries: list[JsonObject],
    rejected: list[JsonObject],
    findings: list[ManifestFinding],
) -> None:
    identities = Counter(
        (entry["artifact_family"], entry["artifact_id"]) for entry in entries
    )
    for family, artifact_id in sorted(
        key for key, count in identities.items() if count > 1
    ):
        _add(
            findings,
            ManifestErrorCode.MANIFEST_DUPLICATE_IDENTITY,
            "artifact semantic identity occurs more than once in the manifest",
            "artifact_manifest",
            "/artifacts",
            artifact_family=family,
            artifact_id=artifact_id,
        )

    locators = Counter(
        [entry["locator"] for entry in entries]
        + [record["locator"] for record in rejected]
    )
    for locator in sorted(value for value, count in locators.items() if count > 1):
        _add(
            findings,
            ManifestErrorCode.MANIFEST_DUPLICATE_IDENTITY,
            "locator occurs more than once across canonical and rejected records",
            "artifact_manifest",
            "/",
            locator=locator,
        )

    rejected_ids = Counter(record["rejected_input_id"] for record in rejected)
    for rejected_id in sorted(
        value for value, count in rejected_ids.items() if count > 1
    ):
        _add(
            findings,
            ManifestErrorCode.MANIFEST_DUPLICATE_IDENTITY,
            "rejected-input identity occurs more than once",
            "artifact_manifest",
            "/rejected_inputs",
            referenced_id=rejected_id,
        )


def _validate_locator_closure(
    records: list[JsonObject],
    supplied: Mapping[str, Any],
    *,
    field: str,
    findings: list[ManifestFinding],
) -> None:
    listed = Counter(record["locator"] for record in records)
    for index, record in enumerate(records):
        locator = record["locator"]
        if locator not in supplied:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_INCOMPLETE,
                "manifest locator has no corresponding caller-supplied content",
                "artifact_manifest",
                _pointer(field, index, "locator"),
                locator=locator,
            )
    for locator in sorted(set(supplied) - set(listed)):
        _add(
            findings,
            ManifestErrorCode.MANIFEST_INCOMPLETE,
            "caller-supplied content is not represented in the manifest",
            "artifact_manifest",
            _pointer(field),
            locator=locator,
        )


def _validate_artifact_entry(
    entry: JsonObject,
    document: JsonObject,
    index: int,
    schema_store: SchemaStore,
    findings: list[ManifestFinding],
) -> None:
    family = entry["artifact_family"]
    artifact_id = entry["artifact_id"]
    locator = entry["locator"]
    base = _pointer("artifacts", index)
    try:
        family_spec = get_artifact_family_spec(family)
    except KeyError:
        _add(
            findings,
            ManifestErrorCode.MANIFEST_REFERENCE_INVALID,
            f"unsupported artifact family {family!r}",
            "artifact_manifest",
            f"{base}/artifact_family",
            artifact_family=family,
            artifact_id=artifact_id,
            locator=locator,
        )
        return
    try:
        spec = _artifact_contract_spec(family, document)
    except KeyError:
        actual_version = document.get(family_spec.version_field)
        _add(
            findings,
            ManifestErrorCode.MANIFEST_REFERENCE_INVALID,
            "artifact document does not declare a supported exact contract version",
            "artifact_manifest",
            f"{base}/artifact_version",
            artifact_family=family,
            artifact_id=artifact_id,
            locator=locator,
            referenced_id=str(actual_version),
        )
        return

    if spec.identity_field is None:
        _add(
            findings,
            ManifestErrorCode.MANIFEST_REFERENCE_INVALID,
            "artifact family has no intrinsic primary ID bindable by this manifest contract",
            "artifact_manifest",
            f"{base}/artifact_id",
            artifact_family=family,
            artifact_id=artifact_id,
            locator=locator,
        )
    else:
        actual_id = document.get(spec.identity_field)
        if actual_id != artifact_id:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_IDENTITY_MISMATCH,
                f"manifest artifact_id does not equal document field {spec.identity_field!r}",
                "artifact_manifest",
                f"{base}/artifact_id",
                artifact_family=family,
                artifact_id=artifact_id,
                locator=locator,
                referenced_id=str(actual_id),
            )

    actual_version = document.get(spec.version_field)
    if actual_version != entry["artifact_version"]:
        _add(
            findings,
            ManifestErrorCode.MANIFEST_VERSION_MISMATCH,
            f"manifest artifact_version does not equal document field {spec.version_field!r}",
            "artifact_manifest",
            f"{base}/artifact_version",
            artifact_family=family,
            artifact_id=artifact_id,
            locator=locator,
            referenced_id=str(actual_version),
        )

    if entry["schema_id"] != spec.schema_id:
        _add(
            findings,
            ManifestErrorCode.MANIFEST_SCHEMA_BINDING_INVALID,
            "manifest schema_id does not match the authoritative artifact-family binding",
            "artifact_manifest",
            f"{base}/schema_id",
            artifact_family=family,
            artifact_id=artifact_id,
            locator=locator,
            referenced_id=spec.schema_id,
        )

    schema = schema_store.get(entry["schema_id"])
    if schema is None:
        _add(
            findings,
            ManifestErrorCode.MANIFEST_REFERENCE_INVALID,
            "bound schema_id is absent from the supplied local schema store",
            "artifact_manifest",
            f"{base}/schema_id",
            artifact_family=family,
            artifact_id=artifact_id,
            locator=locator,
            referenced_id=entry["schema_id"],
        )
    else:
        actual_schema_id = schema.get("$id")
        if actual_schema_id != entry["schema_id"]:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_SCHEMA_BINDING_INVALID,
                "schema-store document $id does not equal the manifest schema_id",
                "artifact_manifest",
                f"{base}/schema_id",
                artifact_family=family,
                artifact_id=artifact_id,
                locator=locator,
                referenced_id=str(actual_schema_id),
            )
        expected_schema_version = _schema_version(entry["schema_id"])
        if entry["schema_version"] != expected_schema_version:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_VERSION_MISMATCH,
                "manifest schema_version does not match the bound executable schema identity",
                "artifact_manifest",
                f"{base}/schema_version",
                artifact_family=family,
                artifact_id=artifact_id,
                locator=locator,
                referenced_id=expected_schema_version,
            )
        try:
            validate_instance(document, schema, schema_store=schema_store)
        except (
            ValidationError,
            SchemaError,
            SchemaStoreError,
            ExternalSchemaReferenceError,
            UnknownSchemaReferenceError,
        ) as error:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_SCHEMA_BINDING_INVALID,
                f"artifact does not validate against its exact bound schema: {error}",
                "artifact_manifest",
                base,
                artifact_family=family,
                artifact_id=artifact_id,
                locator=locator,
                referenced_id=entry["schema_id"],
            )

    try:
        actual_digest = canonical_sha256(document)
    except IntegrityError as error:
        _add(
            findings,
            ManifestErrorCode.MANIFEST_DIGEST_MISMATCH,
            f"artifact cannot receive a canonical content digest: {error}",
            "artifact_manifest",
            f"{base}/content_digest",
            artifact_family=family,
            artifact_id=artifact_id,
            locator=locator,
        )
    else:
        if actual_digest != entry["content_digest"]:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_DIGEST_MISMATCH,
                "canonical artifact content digest does not match",
                "artifact_manifest",
                f"{base}/content_digest",
                artifact_family=family,
                artifact_id=artifact_id,
                locator=locator,
            )


def _validate_artifact_scope(
    manifest: JsonObject,
    entries: list[JsonObject],
    documents: Mapping[str, JsonObject],
    findings: list[ManifestFinding],
) -> None:
    scope = manifest["scope"]
    scope_type = scope["scope_type"]
    family_documents = [
        (entry, documents.get(entry["locator"])) for entry in entries
    ]
    if scope_type == "RUN":
        for entry, document in family_documents:
            if entry["artifact_family"] != "run_manifest" or document is None:
                continue
            for field in ("experiment_id", "run_id"):
                if document.get(field) != scope[field]:
                    _add(
                        findings,
                        ManifestErrorCode.MANIFEST_IDENTITY_MISMATCH,
                        f"RUN scope {field} does not match the supplied Run Manifest",
                        "artifact_manifest",
                        f"/scope/{field}",
                        artifact_family="run_manifest",
                        artifact_id=entry["artifact_id"],
                        locator=entry["locator"],
                    )
    elif scope_type == "CAMPAIGN":
        for entry, document in family_documents:
            if entry["artifact_family"] != "campaign" or document is None:
                continue
            for field in ("experiment_id", "campaign_id"):
                if document.get(field) != scope[field]:
                    _add(
                        findings,
                        ManifestErrorCode.MANIFEST_IDENTITY_MISMATCH,
                        f"CAMPAIGN scope {field} does not match the supplied Campaign",
                        "artifact_manifest",
                        f"/scope/{field}",
                        artifact_family="campaign",
                        artifact_id=entry["artifact_id"],
                        locator=entry["locator"],
                    )


def _validate_schema_set(
    manifest: JsonObject,
    artifact_manifest: JsonObject,
    schema_store: SchemaStore,
    findings: list[ManifestFinding],
) -> None:
    entries = list(manifest["schema_set"])
    counts = Counter(entry["schema_id"] for entry in entries)
    for schema_id in sorted(value for value, count in counts.items() if count > 1):
        _add(
            findings,
            ManifestErrorCode.MANIFEST_DUPLICATE_IDENTITY,
            "schema identity occurs more than once in schema_set",
            "reproducibility_manifest",
            "/schema_set",
            referenced_id=schema_id,
        )
    for index, entry in enumerate(entries):
        schema_id = entry["schema_id"]
        schema = schema_store.get(schema_id)
        base = _pointer("schema_set", index)
        if schema is None:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_REFERENCE_INVALID,
                "schema_set identity is absent from the supplied local schema store",
                "reproducibility_manifest",
                f"{base}/schema_id",
                referenced_id=schema_id,
            )
            continue
        if schema.get("$id") != schema_id:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_SCHEMA_BINDING_INVALID,
                "schema-store document $id does not equal schema_set schema_id",
                "reproducibility_manifest",
                f"{base}/schema_id",
                referenced_id=schema_id,
            )
        expected_version = _schema_version(schema_id)
        if entry["schema_version"] != expected_version:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_VERSION_MISMATCH,
                "schema_set version does not match the executable schema identity",
                "reproducibility_manifest",
                f"{base}/schema_version",
                referenced_id=schema_id,
            )
        try:
            actual_digest = canonical_sha256(schema)
        except IntegrityError as error:
            _add(
                findings,
                ManifestErrorCode.MANIFEST_DIGEST_MISMATCH,
                f"schema cannot receive a canonical content digest: {error}",
                "reproducibility_manifest",
                f"{base}/content_digest",
                referenced_id=schema_id,
            )
        else:
            if actual_digest != entry["content_digest"]:
                _add(
                    findings,
                    ManifestErrorCode.MANIFEST_DIGEST_MISMATCH,
                    "schema canonical content digest does not match",
                    "reproducibility_manifest",
                    f"{base}/content_digest",
                    referenced_id=schema_id,
                )

    listed = set(counts)
    required = {entry["schema_id"] for entry in artifact_manifest["artifacts"]}
    for schema_id in sorted(required - listed):
        _add(
            findings,
            ManifestErrorCode.MANIFEST_INCOMPLETE,
            "schema referenced by the Artifact Manifest is absent from schema_set",
            "reproducibility_manifest",
            "/schema_set",
            referenced_id=schema_id,
        )


def _validate_governing_documents(
    manifest: JsonObject,
    supplied_bytes: Mapping[str, bytes],
    provenance: Mapping[str, JsonObject] | None,
    findings: list[ManifestFinding],
) -> None:
    records = list(manifest["governing_documents"])
    counts = Counter(record["document_id"] for record in records)
    for document_id in sorted(value for value, count in counts.items() if count > 1):
        _add(
            findings,
            ManifestErrorCode.MANIFEST_DUPLICATE_IDENTITY,
            "governing document identity occurs more than once",
            "reproducibility_manifest",
            "/governing_documents",
            referenced_id=document_id,
        )
    for index, record in enumerate(records):
        document_id = record["document_id"]
        raw = supplied_bytes.get(document_id)
        base = _pointer("governing_documents", index)
        if raw is None:
            _add(
                findings,
                ManifestErrorCode.REPRODUCIBILITY_REFERENCE_INVALID,
                "governing document_id has no caller-supplied exact bytes",
                "reproducibility_manifest",
                f"{base}/document_id",
                referenced_id=document_id,
            )
            continue
        actual = forensic_sha256_bytes(raw)
        if actual != record["content_digest"]:
            _add(
                findings,
                ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID,
                "exact-byte document content digest does not match supplied bytes",
                "reproducibility_manifest",
                f"{base}/content_digest",
                referenced_id=document_id,
            )
        if provenance is not None:
            trusted = provenance.get(document_id)
            if trusted is None:
                _add(
                    findings,
                    ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID,
                    "trusted governing-document provenance is absent",
                    "reproducibility_manifest",
                    f"{base}/document_id",
                    referenced_id=document_id,
                )
            else:
                for field in ("document_version", "frozen_tag_identity"):
                    if trusted.get(field) != record[field]:
                        _add(
                            findings,
                            ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID,
                            f"governing-document {field} differs from supplied trusted metadata",
                            "reproducibility_manifest",
                            f"{base}/{field}",
                            referenced_id=document_id,
                        )
    for document_id in sorted(set(supplied_bytes) - set(counts)):
        _add(
            findings,
            ManifestErrorCode.MANIFEST_INCOMPLETE,
            "caller-supplied governing document is absent from the manifest",
            "reproducibility_manifest",
            "/governing_documents",
            referenced_id=document_id,
        )
    if provenance is not None:
        for document_id in sorted(set(provenance) - set(counts)):
            _add(
                findings,
                ManifestErrorCode.MANIFEST_INCOMPLETE,
                "caller-supplied governing-document provenance is absent from the manifest",
                "reproducibility_manifest",
                "/governing_documents",
                referenced_id=document_id,
            )


def _validate_repository_provenance(
    manifest: JsonObject,
    provenance: JsonObject,
    findings: list[ManifestFinding],
) -> None:
    fields = (
        "repository_object_format",
        "repository_commit_sha",
        "repository_tree_sha",
        "release_tag_identity",
        "release_tag_object_sha",
        "release_tag_target_commit_sha",
    )
    for field in fields:
        if provenance.get(field) != manifest[field]:
            _add(
                findings,
                ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID,
                f"{field} differs from the supplied trusted repository fact",
                "reproducibility_manifest",
                f"/{field}",
                referenced_id=str(provenance.get(field)),
            )
    if manifest["release_tag_target_commit_sha"] != manifest["repository_commit_sha"]:
        _add(
            findings,
            ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID,
            "release tag target commit does not equal repository_commit_sha",
            "reproducibility_manifest",
            "/release_tag_target_commit_sha",
            referenced_id=manifest["repository_commit_sha"],
        )
    expected_length = 40 if manifest["repository_object_format"] == "SHA-1" else 64
    for field in (
        "repository_commit_sha",
        "repository_tree_sha",
        "release_tag_object_sha",
        "release_tag_target_commit_sha",
    ):
        if len(manifest[field]) != expected_length:
            _add(
                findings,
                ManifestErrorCode.REPRODUCIBILITY_PROVENANCE_INVALID,
                f"{field} length conflicts with repository_object_format",
                "reproducibility_manifest",
                f"/{field}",
            )


def _validate_dependencies(
    manifest: JsonObject,
    resolved: Sequence[JsonObject],
    findings: list[ManifestFinding],
) -> None:
    declared = list(manifest["dependencies"])
    declared_counts = Counter(entry["name"] for entry in declared)
    resolved_counts = Counter(entry.get("name") for entry in resolved)
    for name in sorted(value for value, count in declared_counts.items() if count > 1):
        _add(
            findings,
            ManifestErrorCode.MANIFEST_DUPLICATE_IDENTITY,
            "dependency name occurs more than once in the manifest",
            "reproducibility_manifest",
            "/dependencies",
            referenced_id=name,
        )
    for name in sorted(
        str(value) for value, count in resolved_counts.items() if count > 1
    ):
        _add(
            findings,
            ManifestErrorCode.REPRODUCIBILITY_DEPENDENCY_INVALID,
            "dependency name occurs more than once in resolved_dependencies",
            "reproducibility_manifest",
            "/dependencies",
            referenced_id=name,
        )
    declared_by_name = {entry["name"]: entry for entry in declared}
    resolved_by_name = {
        entry["name"]: entry for entry in resolved if isinstance(entry.get("name"), str)
    }
    for name in sorted(set(declared_by_name) - set(resolved_by_name)):
        _add(
            findings,
            ManifestErrorCode.REPRODUCIBILITY_DEPENDENCY_INVALID,
            "manifest dependency is absent from authoritative resolved_dependencies",
            "reproducibility_manifest",
            "/dependencies",
            referenced_id=name,
        )
    for name in sorted(set(resolved_by_name) - set(declared_by_name)):
        _add(
            findings,
            ManifestErrorCode.MANIFEST_INCOMPLETE,
            "authoritative resolved dependency is absent from the manifest",
            "reproducibility_manifest",
            "/dependencies",
            referenced_id=name,
        )
    for name in sorted(set(declared_by_name) & set(resolved_by_name)):
        declared_entry = declared_by_name[name]
        resolved_entry = resolved_by_name[name]
        if declared_entry["version"] != resolved_entry.get("version"):
            _add(
                findings,
                ManifestErrorCode.REPRODUCIBILITY_DEPENDENCY_INVALID,
                "dependency exact version differs from authoritative resolved version",
                "reproducibility_manifest",
                "/dependencies",
                referenced_id=name,
            )
        if "distribution_digest" in declared_entry:
            trusted_digest = resolved_entry.get("distribution_digest")
            if trusted_digest is None:
                message = "manifest distribution digest lacks a corresponding trusted digest"
            elif declared_entry["distribution_digest"] != trusted_digest:
                message = "dependency distribution digest differs from the trusted digest"
            else:
                message = None
            if message is not None:
                _add(
                    findings,
                    ManifestErrorCode.REPRODUCIBILITY_DEPENDENCY_INVALID,
                    message,
                    "reproducibility_manifest",
                    "/dependencies",
                    referenced_id=name,
                )


def _validate_environment(
    manifest: JsonObject,
    trusted_environment: JsonObject | None,
    findings: list[ManifestFinding],
) -> None:
    if trusted_environment is not None and dict(manifest["environment"]) != dict(
        trusted_environment
    ):
        _add(
            findings,
            ManifestErrorCode.REPRODUCIBILITY_ENVIRONMENT_INVALID,
            "environment record differs from the caller-supplied trusted environment",
            "reproducibility_manifest",
            "/environment",
            referenced_id=str(trusted_environment.get("environment_reference")),
        )


def _validate_active_artifacts(
    manifest: JsonObject,
    active: ArtifactCollection,
    schema_store: SchemaStore,
    findings: list[ManifestFinding],
) -> None:
    for semantic in validate_artifact_set(active, schema_store=schema_store):
        _add(
            findings,
            ManifestErrorCode.REPRODUCIBILITY_REFERENCE_INVALID,
            f"active artifact graph is invalid: {semantic.code.value}: {semantic.message}",
            "reproducibility_manifest",
            semantic.field_path,
            artifact_family=semantic.artifact_family,
            artifact_id=semantic.artifact_id,
            referenced_id=semantic.referenced_artifact_id,
        )
    for field, family in (
        ("scenario_subset", "scenario"),
        ("control_subset", "control_condition"),
    ):
        for index, identity in enumerate(manifest[field]):
            if _resolve_active(active, family, identity) is None:
                _active_missing(findings, family, identity, _pointer(field, index))
    instrument_id = manifest["instrument_configuration_id"]
    if _resolve_active(active, "instrument_configuration", instrument_id) is None:
        _active_missing(
            findings,
            "instrument_configuration",
            instrument_id,
            "/instrument_configuration_id",
        )

    campaign_id = manifest["campaign_id"]
    campaign = None
    if campaign_id != "NOT_APPLICABLE":
        campaign = _resolve_active(active, "campaign", campaign_id)
        if campaign is None:
            _active_missing(findings, "campaign", campaign_id, "/campaign_id")
        else:
            _validate_campaign_context(manifest, campaign, findings)
    _validate_acceptance_context(manifest, active, campaign, schema_store, findings)
    _validate_confirmatory_context(manifest, active, campaign, findings)
    _validate_repetitions(manifest, active, findings)
    _validate_providers(manifest, active, findings)


def _validate_campaign_context(
    manifest: JsonObject,
    campaign: JsonObject,
    findings: list[ManifestFinding],
) -> None:
    if campaign.get("phase") != manifest["release_phase"]:
        _reference_conflict(findings, "/release_phase", "release phase differs from Campaign")
    if campaign.get("instrument_configuration_id") != manifest["instrument_configuration_id"]:
        _reference_conflict(
            findings,
            "/instrument_configuration_id",
            "instrument configuration differs from Campaign",
        )
    for index, identity in enumerate(manifest["scenario_subset"]):
        if identity not in campaign.get("scenario_ids", []):
            _reference_conflict(
                findings,
                _pointer("scenario_subset", index),
                "release scenario is not a member of the Campaign scenario set",
                identity,
            )
    for index, identity in enumerate(manifest["control_subset"]):
        if identity not in campaign.get("control_condition_ids", []):
            _reference_conflict(
                findings,
                _pointer("control_subset", index),
                "release control condition is not a member of the Campaign control set",
                identity,
            )
    if manifest["release_phase"] == "CONFIRMATORY":
        for field in ("capability_evaluation_reference", "analysis_configuration_id"):
            if campaign.get(field) != manifest[field]:
                _reference_conflict(
                    findings,
                    f"/{field}",
                    f"{field} differs from Campaign",
                )


def _validate_acceptance_context(
    manifest: JsonObject,
    active: ArtifactCollection,
    campaign: JsonObject | None,
    schema_store: SchemaStore,
    findings: list[ManifestFinding],
) -> None:
    phase = manifest["release_phase"]
    if phase not in {"PILOT", "CONFIRMATORY"} or "instrument_acceptance" not in active:
        return
    expected_state = (
        "ACCEPTED_FOR_PILOT" if phase == "PILOT" else "ACCEPTED_FOR_CONFIRMATORY"
    )
    acceptances = list(active["instrument_acceptance"])
    prospective = [
        item
        for item in acceptances
        if _is_structurally_valid_prospective_acceptance(item, schema_store)
    ]
    reference = manifest["instrument_acceptance_reference"]
    claims_prospective_id = any(
        item.get("instrument_acceptance_id") == reference for item in prospective
    )
    linked_prospective = any(
        item.get("instrument_configuration_id")
        == manifest["instrument_configuration_id"]
        and item.get("environment_id")
        == manifest["environment"]["environment_reference"]
        and item.get("campaign_id") == manifest["campaign_id"]
        for item in prospective
    )
    if claims_prospective_id or linked_prospective:
        targets = [
            item
            for item in prospective
            if item.get("instrument_acceptance_id") == reference
        ]
        if len(targets) != 1:
            _active_missing(
                findings,
                "instrument_acceptance",
                reference,
                "/instrument_acceptance_reference",
            )
        else:
            target = targets[0]
            compatible = (
                target.get("instrument_configuration_id")
                == manifest["instrument_configuration_id"]
                and target.get("environment_id")
                == manifest["environment"]["environment_reference"]
                and target.get("campaign_id") == manifest["campaign_id"]
                and target.get("acceptance_state") == expected_state
                and target.get("accepted_for_phase") == phase
            )
            if not compatible:
                _reference_conflict(
                    findings,
                    "/instrument_acceptance_reference",
                    "referenced instrument acceptance is incompatible with release context",
                    reference,
                )
    else:
        historical = [
            item
            for item in acceptances
            if _artifact_contract_version(item, "instrument_acceptance") == "0.1.0"
        ]
        compatible = [
            item
            for item in historical
            if item.get("instrument_configuration_id")
            == manifest["instrument_configuration_id"]
            and item.get("environment_id")
            == manifest["environment"]["environment_reference"]
            and item.get("campaign_id") == manifest["campaign_id"]
            and item.get("acceptance_state") == expected_state
            and item.get("accepted_for_phase") == phase
        ]
        if len(compatible) != 1:
            _reference_conflict(
                findings,
                "/instrument_acceptance_reference",
                f"release requires exactly one compatible acceptance; found {len(compatible)}",
            )
    if campaign is not None and campaign.get("instrument_acceptance_reference") not in {
        None,
        reference,
    }:
        _reference_conflict(
            findings,
            "/instrument_acceptance_reference",
            "opaque acceptance reference differs from Campaign",
        )


def _validate_confirmatory_context(
    manifest: JsonObject,
    active: ArtifactCollection,
    campaign: JsonObject | None,
    findings: list[ManifestFinding],
) -> None:
    if manifest["release_phase"] != "CONFIRMATORY":
        return
    capability_id = manifest["capability_evaluation_reference"]
    capability = _resolve_active(active, "capability_evaluation", capability_id)
    if capability is None:
        _active_missing(
            findings,
            "capability_evaluation",
            capability_id,
            "/capability_evaluation_reference",
        )
    else:
        if capability.get("evaluation_state") != "FROZEN_FOR_CONFIRMATORY_USE":
            _reference_conflict(
                findings,
                "/capability_evaluation_reference",
                "Capability Evaluation is not frozen for confirmatory use",
                capability_id,
            )
        if capability.get("containment_outcomes_used") is not False:
            _reference_conflict(
                findings,
                "/capability_evaluation_reference",
                "Capability Evaluation uses containment outcomes",
                capability_id,
            )
    analysis_id = manifest["analysis_configuration_id"]
    analysis = _resolve_active(active, "analysis_manifest", analysis_id)
    if analysis is None:
        _active_missing(
            findings,
            "analysis_manifest",
            analysis_id,
            "/analysis_configuration_id",
        )
    else:
        expected = {
            "analysis_state": "FROZEN_FOR_CONFIRMATORY",
            "primary_endpoint": "RUN_LEVEL_ANY_UNAUTHORIZED_EXECUTED",
            "primary_estimand": "RISK_DIFFERENCE",
            "primary_effect_direction": "M3_MINUS_M1",
        }
        for field, value in expected.items():
            if analysis.get(field) != value:
                _reference_conflict(
                    findings,
                    "/analysis_configuration_id",
                    f"Analysis Manifest {field} is not the frozen H1 configuration",
                    analysis_id,
                )
    if campaign is not None:
        if campaign.get("capability_evaluation_reference") != capability_id:
            _reference_conflict(
                findings,
                "/capability_evaluation_reference",
                "Capability Evaluation is inconsistent with Campaign",
                capability_id,
            )
        if campaign.get("analysis_configuration_id") != analysis_id:
            _reference_conflict(
                findings,
                "/analysis_configuration_id",
                "Analysis Manifest is inconsistent with Campaign",
                analysis_id,
            )


def _validate_repetitions(
    manifest: JsonObject,
    active: ArtifactCollection,
    findings: list[ManifestFinding],
) -> None:
    for field, family in (("scheduled_run_ids", "scheduled_run"), ("run_ids", "run_manifest")):
        for index, identity in enumerate(manifest[field]):
            if family in active and _resolve_active(active, family, identity) is None:
                _active_missing(findings, family, identity, _pointer(field, index))
    for index, repetition in enumerate(manifest["repetition_identities"]):
        for field, family in (("scheduled_run_id", "scheduled_run"), ("run_id", "run_manifest")):
            identity = repetition.get(field)
            if identity is None or family not in active:
                continue
            target = _resolve_active(active, family, identity)
            if target is None:
                _active_missing(
                    findings,
                    family,
                    identity,
                    _pointer("repetition_identities", index, field),
                )
                continue
            expected_seed = {
                key: repetition[key]
                for key in ("repetition_id", "seed_status", "seed_value")
                if key in repetition
            }
            if target.get("seed_repetition_identity") != expected_seed:
                _reference_conflict(
                    findings,
                    _pointer("repetition_identities", index),
                    "repetition seed identity differs from the referenced run artifact",
                    identity,
                )


def _validate_providers(
    manifest: JsonObject,
    active: ArtifactCollection,
    findings: list[ManifestFinding],
) -> None:
    for index, provider in enumerate(manifest["model_provider_identities"]):
        agent_id = provider["agent_condition_id"]
        agent = _resolve_active(active, "agent_model_condition", agent_id)
        base = _pointer("model_provider_identities", index)
        if agent is None:
            _active_missing(
                findings,
                "agent_model_condition",
                agent_id,
                f"{base}/agent_condition_id",
            )
            continue
        if provider["model_identifier"] != agent.get("model_identifier"):
            _provider_conflict(
                findings,
                f"{base}/model_identifier",
                "model identifier differs from Agent/Model Condition",
                agent_id,
            )
        runtime = provider["provider_runtime_identity"]
        agent_runtime = agent.get("provider_runtime_identity", {})
        if (
            runtime["identity_status"] == "REPORTED"
            and runtime.get("runtime_identifier") != agent_runtime.get("runtime_id")
        ):
            _provider_conflict(
                findings,
                f"{base}/provider_runtime_identity/runtime_identifier",
                "provider runtime identifier differs from Agent/Model Condition",
                agent_id,
            )
        model_version = agent.get("model_version")
        if provider["version_status"] == "REPORTED":
            if provider.get("model_version") != model_version:
                _provider_conflict(
                    findings,
                    f"{base}/model_version",
                    "reported model version differs from Agent/Model Condition",
                    agent_id,
                )
        elif model_version not in {None, "UNAVAILABLE"}:
            _provider_conflict(
                findings,
                f"{base}/version_status",
                "unavailable/not-reported status conflicts with a concrete model version",
                agent_id,
            )


def _resolve_active(active: ArtifactCollection, family: str, identity: str) -> JsonObject | None:
    if family not in active:
        return None
    matches = []
    for item in active[family]:
        try:
            spec = _artifact_contract_spec(family, item)
        except KeyError:
            continue
        if spec.identity_field is not None and item.get(spec.identity_field) == identity:
            matches.append(item)
    return matches[0] if len(matches) == 1 else None


def _artifact_contract_spec(
    family: str,
    document: JsonObject,
) -> ArtifactFamilyContractSpec:
    version_field = get_artifact_family_spec(family).version_field
    artifact_version = document.get(version_field)
    if not isinstance(artifact_version, str):
        raise KeyError((family, artifact_version))
    return get_artifact_family_contract_spec(family, artifact_version)


def _artifact_contract_version(document: JsonObject, family: str) -> str | None:
    try:
        return _artifact_contract_spec(family, document).artifact_version
    except KeyError:
        return None


def _is_structurally_valid_prospective_acceptance(
    document: JsonObject,
    schema_store: SchemaStore,
) -> bool:
    try:
        spec = _artifact_contract_spec("instrument_acceptance", document)
    except KeyError:
        return False
    if spec.artifact_version != "0.2.0":
        return False
    schema = schema_store.get(spec.schema_id)
    if schema is None or schema.get("$id") != spec.schema_id:
        return False
    try:
        validate_instance(document, schema, schema_store=schema_store)
    except (
        ValidationError,
        SchemaError,
        SchemaStoreError,
        ExternalSchemaReferenceError,
        UnknownSchemaReferenceError,
    ):
        return False
    return True


def _structural_finding(
    manifest: JsonObject,
    *,
    manifest_family: str,
    schema_id: str,
    schema_store: SchemaStore,
) -> ManifestFinding | None:
    schema = schema_store.get(schema_id)
    if schema is None:
        return ManifestFinding(
            ManifestErrorCode.MANIFEST_SCHEMA_INVALID,
            f"required local manifest schema {schema_id!r} is absent",
            manifest_family,
            "/",
            referenced_id=schema_id,
        )
    try:
        validate_instance(manifest, schema, schema_store=schema_store)
    except ValidationError as error:
        return ManifestFinding(
            ManifestErrorCode.MANIFEST_SCHEMA_INVALID,
            f"Draft 2020-12 validation failed: {error.message}",
            manifest_family,
            _error_pointer(error),
        )
    except (
        SchemaError,
        SchemaStoreError,
        ExternalSchemaReferenceError,
        UnknownSchemaReferenceError,
    ) as error:
        return ManifestFinding(
            ManifestErrorCode.MANIFEST_SCHEMA_INVALID,
            f"local schema validation failed: {error}",
            manifest_family,
            "/",
        )
    return None


def _schema_version(schema_id: str) -> str:
    return schema_id.rsplit(":", 1)[-1]


def _active_missing(
    findings: list[ManifestFinding],
    family: str,
    identity: str,
    field_path: str,
) -> None:
    _add(
        findings,
        ManifestErrorCode.REPRODUCIBILITY_REFERENCE_INVALID,
        f"{family} identity does not resolve exactly once in active_artifacts",
        "reproducibility_manifest",
        field_path,
        artifact_family=family,
        artifact_id=identity,
        referenced_id=identity,
    )


def _reference_conflict(
    findings: list[ManifestFinding],
    field_path: str,
    message: str,
    referenced_id: str | None = None,
) -> None:
    _add(
        findings,
        ManifestErrorCode.REPRODUCIBILITY_REFERENCE_INVALID,
        message,
        "reproducibility_manifest",
        field_path,
        referenced_id=referenced_id,
    )


def _provider_conflict(
    findings: list[ManifestFinding],
    field_path: str,
    message: str,
    referenced_id: str,
) -> None:
    _add(
        findings,
        ManifestErrorCode.REPRODUCIBILITY_PROVIDER_INVALID,
        message,
        "reproducibility_manifest",
        field_path,
        artifact_family="agent_model_condition",
        artifact_id=referenced_id,
        referenced_id=referenced_id,
    )


def _add(
    findings: list[ManifestFinding],
    code: ManifestErrorCode,
    message: str,
    manifest_family: str,
    field_path: str,
    *,
    artifact_family: str | None = None,
    artifact_id: str | None = None,
    locator: str | None = None,
    referenced_id: str | None = None,
) -> None:
    findings.append(
        ManifestFinding(
            code=code,
            message=message,
            manifest_family=manifest_family,
            field_path=field_path,
            artifact_family=artifact_family,
            artifact_id=artifact_id,
            locator=locator,
            referenced_id=referenced_id,
        )
    )


def _sorted(findings: list[ManifestFinding]) -> tuple[ManifestFinding, ...]:
    return tuple(
        sorted(
            findings,
            key=lambda item: (
                item.manifest_family,
                item.field_path,
                item.code.value,
                item.artifact_family or "",
                item.artifact_id or "",
                item.locator or "",
                item.referenced_id or "",
                item.message,
            ),
        )
    )


def _pointer(*parts: str | int) -> str:
    if not parts:
        return "/"
    return "/" + "/".join(
        str(part).replace("~", "~0").replace("/", "~1") for part in parts
    )


def _error_pointer(error: ValidationError) -> str:
    return _pointer(*error.absolute_path)
