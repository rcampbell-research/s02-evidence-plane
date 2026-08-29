"""Pure Stage 12E release-selected artifact version-gate validation.

This module validates only the caller-supplied Release Profile selection and
its exact, already-governed Artifact Manifest bindings.  It performs no file
discovery, acquisition, release assembly, subprocess execution, network access,
or persistent writes.  A release-version finding is an eligibility result, not
a scientific-validity, security, authenticity, or corruption claim.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final, TypeAlias

from jsonschema.exceptions import SchemaError, ValidationError

from frontier_agent_containment.manifest_validation import validate_artifact_manifest
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
)


JsonObject: TypeAlias = Mapping[str, Any]

_RELEASE_PROFILE_SCHEMA_ID: Final = (
    "urn:frontier-agent-containment:schema:release-profile:0.1.0"
)
_AFFECTED_FAMILIES: Final = frozenset(
    {
        "instrument_acceptance",
        "derived_action_outcome",
        "derived_run_outcome",
    }
)
_REQUIRED_AFFECTED_VERSION: Final = "0.2.0"


class ReleaseValidationErrorCode(str, Enum):
    """Bounded Stage 12E release artifact version-gate finding codes."""

    RELEASE_PROFILE_SCHEMA_INVALID = "RELEASE_PROFILE_SCHEMA_INVALID"
    RELEASE_ARTIFACT_MANIFEST_INVALID = "RELEASE_ARTIFACT_MANIFEST_INVALID"
    RELEASE_ARTIFACT_DUPLICATE_SELECTION = (
        "RELEASE_ARTIFACT_DUPLICATE_SELECTION"
    )
    RELEASE_ARTIFACT_UNRESOLVED = "RELEASE_ARTIFACT_UNRESOLVED"
    RELEASE_ARTIFACT_EXPECTED_VERSION_MISMATCH = (
        "RELEASE_ARTIFACT_EXPECTED_VERSION_MISMATCH"
    )
    RELEASE_ARTIFACT_VERSION_INELIGIBLE = (
        "RELEASE_ARTIFACT_VERSION_INELIGIBLE"
    )


@dataclass(frozen=True, slots=True)
class ReleaseValidationFinding:
    """One immutable, deterministically ordered release-validation finding."""

    code: ReleaseValidationErrorCode
    message: str
    field_path: str
    artifact_family: str | None = None
    artifact_id: str | None = None
    locator: str | None = None


class ReleaseValidationError(ValueError):
    """Aggregate exception raised by the release assert-style helper."""

    def __init__(self, findings: Iterable[ReleaseValidationFinding]) -> None:
        self.findings = tuple(findings)
        super().__init__(
            "release artifact version validation has "
            f"{len(self.findings)} finding(s)"
        )


def validate_release_artifact_version_gates(
    release_profile: Mapping[str, Any],
    *,
    artifact_manifest: Mapping[str, Any],
    artifact_documents_by_locator: Mapping[str, Mapping[str, Any]],
    rejected_bytes_by_locator: Mapping[str, bytes],
    schema_store: SchemaStore,
) -> tuple[ReleaseValidationFinding, ...]:
    """Validate exact selected-artifact versions for one Release Profile.

    The Release Profile is structurally validated first.  A nonempty selection
    is resolved only through a complete Artifact Manifest that passes the
    public Stage 12D validator.  Release policy is then applied to each exact
    resolved contract without inferring versions from unresolved declarations.
    """

    structural = _release_profile_structural_finding(release_profile, schema_store)
    if structural is not None:
        return (structural,)

    active_entries = list(release_profile["active_artifacts"])
    if not active_entries:
        return ()

    manifest_findings = validate_artifact_manifest(
        artifact_manifest,
        artifact_documents_by_locator=artifact_documents_by_locator,
        rejected_bytes_by_locator=rejected_bytes_by_locator,
        schema_store=schema_store,
    )
    if manifest_findings:
        return tuple(
            ReleaseValidationFinding(
                code=ReleaseValidationErrorCode.RELEASE_ARTIFACT_MANIFEST_INVALID,
                message=(
                    "supplied Artifact Manifest is not coherent: "
                    f"{finding.code.value}: {finding.message}"
                ),
                field_path="/active_artifacts",
                artifact_family=finding.artifact_family,
                artifact_id=finding.artifact_id,
                locator=finding.locator,
            )
            for finding in manifest_findings
        )

    findings: list[ReleaseValidationFinding] = []
    _validate_duplicate_selections(active_entries, findings)

    manifest_entries = tuple(artifact_manifest["artifacts"])
    for index, selection in enumerate(active_entries):
        matches = tuple(
            entry
            for entry in manifest_entries
            if entry["locator"] == selection["locator"]
            and entry["artifact_family"] == selection["artifact_family"]
            and entry["artifact_id"] == selection["artifact_id"]
        )
        if len(matches) != 1:
            findings.append(_unresolved_finding(selection, index))
            continue

        entry = matches[0]
        try:
            contract_spec = get_artifact_family_contract_spec(
                entry["artifact_family"], entry["artifact_version"]
            )
        except KeyError:
            findings.append(_unresolved_finding(selection, index))
            continue
        _validate_resolved_selection(selection, contract_spec, index, findings)

    return tuple(findings)


def assert_release_artifact_version_gates_valid(
    release_profile: Mapping[str, Any],
    *,
    artifact_manifest: Mapping[str, Any],
    artifact_documents_by_locator: Mapping[str, Mapping[str, Any]],
    rejected_bytes_by_locator: Mapping[str, bytes],
    schema_store: SchemaStore,
) -> None:
    """Raise when release artifact version-gate validation returns findings."""

    findings = validate_release_artifact_version_gates(
        release_profile,
        artifact_manifest=artifact_manifest,
        artifact_documents_by_locator=artifact_documents_by_locator,
        rejected_bytes_by_locator=rejected_bytes_by_locator,
        schema_store=schema_store,
    )
    if findings:
        raise ReleaseValidationError(findings)


def _release_profile_structural_finding(
    release_profile: JsonObject,
    schema_store: SchemaStore,
) -> ReleaseValidationFinding | None:
    schema = schema_store.get(_RELEASE_PROFILE_SCHEMA_ID)
    if schema is None:
        return ReleaseValidationFinding(
            code=ReleaseValidationErrorCode.RELEASE_PROFILE_SCHEMA_INVALID,
            message=(
                "required local Release Profile schema "
                f"{_RELEASE_PROFILE_SCHEMA_ID!r} is absent"
            ),
            field_path="/",
        )
    try:
        validate_instance(release_profile, schema, schema_store=schema_store)
    except ValidationError as error:
        return ReleaseValidationFinding(
            code=ReleaseValidationErrorCode.RELEASE_PROFILE_SCHEMA_INVALID,
            message=f"Draft 2020-12 validation failed: {error.message}",
            field_path=_error_pointer(error),
        )
    except (
        SchemaError,
        SchemaStoreError,
        ExternalSchemaReferenceError,
        UnknownSchemaReferenceError,
    ) as error:
        return ReleaseValidationFinding(
            code=ReleaseValidationErrorCode.RELEASE_PROFILE_SCHEMA_INVALID,
            message=f"local Release Profile schema validation failed: {error}",
            field_path="/",
        )
    return None


def _validate_duplicate_selections(
    active_entries: list[JsonObject],
    findings: list[ReleaseValidationFinding],
) -> None:
    identities = Counter(
        (entry["artifact_family"], entry["artifact_id"]) for entry in active_entries
    )
    for family, artifact_id in sorted(
        identity for identity, count in identities.items() if count > 1
    ):
        findings.append(
            ReleaseValidationFinding(
                code=(
                    ReleaseValidationErrorCode.RELEASE_ARTIFACT_DUPLICATE_SELECTION
                ),
                message=(
                    f"selected {family} artifact identity {artifact_id!r} occurs "
                    "more than once in active_artifacts"
                ),
                field_path="/active_artifacts",
                artifact_family=family,
                artifact_id=artifact_id,
            )
        )


def _unresolved_finding(selection: JsonObject, index: int) -> ReleaseValidationFinding:
    family = selection["artifact_family"]
    artifact_id = selection["artifact_id"]
    locator = selection["locator"]
    return ReleaseValidationFinding(
        code=ReleaseValidationErrorCode.RELEASE_ARTIFACT_UNRESOLVED,
        message=(
            f"selected {family} artifact {artifact_id!r} at locator {locator!r} "
            "does not resolve exactly once through the valid Artifact Manifest"
        ),
        field_path=_pointer("active_artifacts", index),
        artifact_family=family,
        artifact_id=artifact_id,
        locator=locator,
    )


def _validate_resolved_selection(
    selection: JsonObject,
    contract_spec: ArtifactFamilyContractSpec,
    index: int,
    findings: list[ReleaseValidationFinding],
) -> None:
    family = selection["artifact_family"]
    artifact_id = selection["artifact_id"]
    locator = selection["locator"]
    base = _pointer("active_artifacts", index)
    expected_version = selection.get("expected_artifact_version")
    actual_version = contract_spec.artifact_version

    if expected_version is not None and expected_version != actual_version:
        findings.append(
            ReleaseValidationFinding(
                code=(
                    ReleaseValidationErrorCode.
                    RELEASE_ARTIFACT_EXPECTED_VERSION_MISMATCH
                ),
                message=(
                    f"expected_artifact_version {expected_version!r} does not equal "
                    f"resolved artifact contract version {actual_version!r}"
                ),
                field_path=f"{base}/expected_artifact_version",
                artifact_family=family,
                artifact_id=artifact_id,
                locator=locator,
            )
        )

    if family in _AFFECTED_FAMILIES and actual_version != _REQUIRED_AFFECTED_VERSION:
        findings.append(
            ReleaseValidationFinding(
                code=(
                    ReleaseValidationErrorCode.RELEASE_ARTIFACT_VERSION_INELIGIBLE
                ),
                message=(
                    f"selected {family} artifact uses contract version "
                    f"{actual_version}; research release eligibility requires version "
                    f"{_REQUIRED_AFFECTED_VERSION} for this family"
                ),
                field_path=base,
                artifact_family=family,
                artifact_id=artifact_id,
                locator=locator,
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


__all__ = [
    "ReleaseValidationError",
    "ReleaseValidationErrorCode",
    "ReleaseValidationFinding",
    "assert_release_artifact_version_gates_valid",
    "validate_release_artifact_version_gates",
]
