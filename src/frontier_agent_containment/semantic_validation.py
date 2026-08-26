"""Deterministic, in-memory cross-contract semantic validation.

Stage 10 validates only the supported pre-run artifact families listed in
``SUPPORTED_ARTIFACT_FAMILIES``.  Structural validation always runs first via
the project's network-independent JSON Schema validator.  Structurally invalid
artifacts are excluded from semantic indexes and are never repaired.

The validator deliberately does not resolve approval policies or validation
evidence, interpret evidence, derive outcomes, prove S0 or runtime M3
properties, or execute any configured component.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final, TypeAlias

from jsonschema.exceptions import SchemaError, ValidationError

from frontier_agent_containment.schema_validation import (
    ExternalSchemaReferenceError,
    SchemaStore,
    SchemaStoreError,
    UnknownSchemaReferenceError,
    validate_instance,
)


Artifact: TypeAlias = Mapping[str, Any]
ArtifactCollection: TypeAlias = Mapping[str, Iterable[Artifact]]


class SemanticErrorCode(str, Enum):
    """Bounded Stage 10 semantic-validation error codes."""

    SCHEMA_INVALID = "SCHEMA_INVALID"
    REFERENCE_INVALID = "REFERENCE_INVALID"
    VERSION_INVALID = "VERSION_INVALID"
    SEMANTIC_CONFLICT = "SEMANTIC_CONFLICT"
    DUPLICATE_IDENTITY = "DUPLICATE_IDENTITY"
    DEPENDENCY_INVALID = "DEPENDENCY_INVALID"
    COMPOSITION_INVALID = "COMPOSITION_INVALID"
    ENVIRONMENT_INVALID = "ENVIRONMENT_INVALID"
    RUN_MANIFEST_INVALID = "RUN_MANIFEST_INVALID"
    UNSUPPORTED_ARTIFACT_FAMILY = "UNSUPPORTED_ARTIFACT_FAMILY"
    CAPABILITY_EVALUATION_INVALID = "CAPABILITY_EVALUATION_INVALID"
    CAMPAIGN_INVALID = "CAMPAIGN_INVALID"
    ACCEPTANCE_INVALID = "ACCEPTANCE_INVALID"
    ANALYSIS_INVALID = "ANALYSIS_INVALID"
    VALIDATION_INCOMPLETE = "VALIDATION_INCOMPLETE"
    PROVENANCE_UNRESOLVED = "PROVENANCE_UNRESOLVED"


@dataclass(frozen=True, slots=True)
class SemanticFinding:
    """One immutable, deterministic semantic-validation finding."""

    code: SemanticErrorCode
    message: str
    artifact_family: str
    artifact_id: str
    field_path: str
    referenced_artifact_family: str | None = None
    referenced_artifact_id: str | None = None


class SemanticValidationError(ValueError):
    """Aggregate exception raised when an artifact set has semantic findings."""

    def __init__(self, findings: Iterable[SemanticFinding]) -> None:
        self.findings = tuple(findings)
        super().__init__(
            f"artifact set has {len(self.findings)} semantic validation finding(s)"
        )


@dataclass(frozen=True, slots=True)
class _FamilySpec:
    schema_id: str
    identity_field: str | None
    version_field: str


@dataclass(frozen=True, slots=True)
class _ArtifactRecord:
    family: str
    identity: str
    version: str
    artifact: Artifact
    ordinal: int


_SCHEMA_PREFIX: Final = "urn:frontier-agent-containment:schema:"

SUPPORTED_ARTIFACT_FAMILIES: Final[Mapping[str, _FamilySpec]] = {
    "resource": _FamilySpec(
        f"{_SCHEMA_PREFIX}resource:0.1.0", "resource_id", "resource_version"
    ),
    "benign_task": _FamilySpec(
        f"{_SCHEMA_PREFIX}benign-task:0.1.0", "task_id", "task_version"
    ),
    "capability_envelope": _FamilySpec(
        f"{_SCHEMA_PREFIX}capability-envelope:0.1.0",
        "capability_envelope_id",
        "envelope_version",
    ),
    "scenario": _FamilySpec(
        f"{_SCHEMA_PREFIX}scenario:0.1.0", "scenario_id", "scenario_version"
    ),
    "policy": _FamilySpec(
        f"{_SCHEMA_PREFIX}policy:0.1.0", "policy_id", "policy_version"
    ),
    "control": _FamilySpec(
        f"{_SCHEMA_PREFIX}control:0.1.0", "control_id", "control_version"
    ),
    "control_condition": _FamilySpec(
        f"{_SCHEMA_PREFIX}control-condition:0.1.0",
        "control_condition_id",
        "condition_version",
    ),
    "agent_model_condition": _FamilySpec(
        f"{_SCHEMA_PREFIX}agent-model-condition:0.1.0",
        "agent_condition_id",
        "condition_version",
    ),
    "autonomy_condition": _FamilySpec(
        f"{_SCHEMA_PREFIX}autonomy-condition:0.1.0",
        "autonomy_condition_id",
        "condition_version",
    ),
    "environment": _FamilySpec(
        f"{_SCHEMA_PREFIX}environment:0.1.0",
        "environment_id",
        "environment_version",
    ),
    "scheduled_run": _FamilySpec(
        f"{_SCHEMA_PREFIX}scheduled-run:0.1.0",
        "scheduled_run_id",
        "scheduled_run_version",
    ),
    "run_manifest": _FamilySpec(
        f"{_SCHEMA_PREFIX}run-manifest:0.1.0",
        "run_id",
        "run_manifest_version",
    ),
    "instrument_configuration": _FamilySpec(
        f"{_SCHEMA_PREFIX}instrument-configuration:0.1.0",
        "instrument_configuration_id",
        "configuration_version",
    ),
    "capability_evaluation": _FamilySpec(
        f"{_SCHEMA_PREFIX}capability-evaluation:0.1.0",
        "evaluation_configuration_id",
        "evaluation_version",
    ),
    "campaign": _FamilySpec(
        f"{_SCHEMA_PREFIX}campaign:0.1.0", "campaign_id", "campaign_version"
    ),
    "validation_case": _FamilySpec(
        f"{_SCHEMA_PREFIX}validation-case:0.1.0",
        "validation_case_id",
        "validation_case_version",
    ),
    # The frozen v0.1 Instrument Acceptance Contract intentionally has no
    # intrinsic artifact identity. Records therefore remain unkeyed and are
    # selected only through an exact, unique campaign-compatible match. The
    # opaque Campaign reference string is not claimed to be content-resolved.
    "instrument_acceptance": _FamilySpec(
        f"{_SCHEMA_PREFIX}instrument-acceptance:0.1.0",
        None,
        "acceptance_version",
    ),
    "analysis_manifest": _FamilySpec(
        f"{_SCHEMA_PREFIX}analysis-manifest:0.1.0",
        "analysis_configuration_id",
        "analysis_version",
    ),
}


class _ArtifactRegistry:
    """Active-set indexes containing only structurally valid artifacts."""

    def __init__(
        self,
        records: Mapping[str, list[_ArtifactRecord]],
        findings: list[SemanticFinding],
    ) -> None:
        self.records = records
        self.primary: dict[str, dict[str, _ArtifactRecord]] = {}
        self.model_conditions: dict[str, _ArtifactRecord] = {}
        self.capability_conditions: dict[str, _ArtifactRecord] = {}
        unique_agent_records: list[_ArtifactRecord] = []

        for family in sorted(SUPPORTED_ARTIFACT_FAMILIES):
            spec = SUPPORTED_ARTIFACT_FAMILIES[family]
            if spec.identity_field is None:
                self.primary[family] = {}
                continue
            grouped: dict[str, list[_ArtifactRecord]] = {}
            for record in records.get(family, []):
                grouped.setdefault(record.identity, []).append(record)

            unique: dict[str, _ArtifactRecord] = {}
            for identity in sorted(grouped):
                group = grouped[identity]
                if len(group) == 1:
                    unique[identity] = group[0]
                    if family == "agent_model_condition":
                        unique_agent_records.append(group[0])
                    continue
                versions = ", ".join(sorted(record.version for record in group))
                findings.append(
                    SemanticFinding(
                        code=SemanticErrorCode.DUPLICATE_IDENTITY,
                        message=(
                            f"active {family} identity {identity!r} resolves to "
                            f"{len(group)} artifacts with versions [{versions}]"
                        ),
                        artifact_family=family,
                        artifact_id=identity,
                        field_path=_pointer(spec.identity_field),
                    )
                )
            self.primary[family] = unique

        self.model_conditions = self._secondary_index(
            unique_agent_records, "model_condition_id", findings
        )
        self.capability_conditions = self._secondary_index(
            unique_agent_records, "capability_condition_id", findings
        )

    @staticmethod
    def _secondary_index(
        records: Iterable[_ArtifactRecord],
        field: str,
        findings: list[SemanticFinding],
    ) -> dict[str, _ArtifactRecord]:
        grouped: dict[str, list[_ArtifactRecord]] = {}
        for record in records:
            value = record.artifact[field]
            grouped.setdefault(value, []).append(record)

        result: dict[str, _ArtifactRecord] = {}
        for identity in sorted(grouped):
            group = grouped[identity]
            if len(group) == 1:
                result[identity] = group[0]
                continue
            owner_ids = sorted(record.identity for record in group)
            owners = ", ".join(owner_ids)
            findings.append(
                SemanticFinding(
                    code=SemanticErrorCode.DUPLICATE_IDENTITY,
                    message=(
                        f"secondary {field} identity {identity!r} resolves to "
                        f"multiple Agent/Model Conditions [{owners}]"
                    ),
                    artifact_family="agent_model_condition",
                    artifact_id=owner_ids[0],
                    field_path=_pointer(field),
                )
            )
        return result

    def resolve(self, family: str, identity: str) -> _ArtifactRecord | None:
        return self.primary.get(family, {}).get(identity)


def validate_artifact_set(
    artifacts: ArtifactCollection,
    *,
    schema_store: SchemaStore,
) -> tuple[SemanticFinding, ...]:
    """Validate one active in-memory artifact resolution set.

    Unsupported families are rejected explicitly.  The returned tuple is
    sorted by a documented stable key and the supplied mappings/lists are read
    only.  The explicit schema store is passed to the existing local-only
    validator; this module performs no filesystem, subprocess, URI, or network
    operations.
    """

    findings: list[SemanticFinding] = []
    valid_records: dict[str, list[_ArtifactRecord]] = {
        family: [] for family in SUPPORTED_ARTIFACT_FAMILIES
    }

    for family in sorted(artifacts):
        supplied = tuple(artifacts[family])
        spec = SUPPORTED_ARTIFACT_FAMILIES.get(family)
        if spec is None:
            for ordinal, artifact in enumerate(supplied):
                findings.append(
                    SemanticFinding(
                        code=SemanticErrorCode.UNSUPPORTED_ARTIFACT_FAMILY,
                        message=(
                            f"artifact family {family!r} is not supported by Stage 10"
                        ),
                        artifact_family=family,
                        artifact_id=_best_effort_identity(artifact, ordinal),
                        field_path="/",
                    )
                )
            continue

        schema = schema_store.get(spec.schema_id)
        for ordinal, artifact in enumerate(supplied):
            label = (
                _best_effort_identity(
                    artifact, ordinal, preferred=spec.identity_field
                )
                if spec.identity_field is not None
                else f"<instrument_acceptance:{ordinal}>"
            )
            if schema is None:
                findings.append(
                    SemanticFinding(
                        code=SemanticErrorCode.SCHEMA_INVALID,
                        message=f"required local schema {spec.schema_id!r} is absent",
                        artifact_family=family,
                        artifact_id=label,
                        field_path="/",
                    )
                )
                continue
            try:
                validate_instance(artifact, schema, schema_store=schema_store)
            except ValidationError as error:
                findings.append(
                    SemanticFinding(
                        code=SemanticErrorCode.SCHEMA_INVALID,
                        message=f"Draft 2020-12 validation failed: {error.message}",
                        artifact_family=family,
                        artifact_id=label,
                        field_path=_error_pointer(error),
                    )
                )
                continue
            except (
                SchemaError,
                SchemaStoreError,
                ExternalSchemaReferenceError,
                UnknownSchemaReferenceError,
            ) as error:
                findings.append(
                    SemanticFinding(
                        code=SemanticErrorCode.SCHEMA_INVALID,
                        message=f"local schema validation failed: {error}",
                        artifact_family=family,
                        artifact_id=label,
                        field_path="/",
                    )
                )
                continue

            valid_records[family].append(
                _ArtifactRecord(
                    family=family,
                    identity=(
                        artifact[spec.identity_field]
                        if spec.identity_field is not None
                        else label
                    ),
                    version=artifact[spec.version_field],
                    artifact=artifact,
                    ordinal=ordinal,
                )
            )

    registry = _ArtifactRegistry(valid_records, findings)
    _validate_resources_and_tasks(registry, findings)
    _validate_capability_envelopes(registry, findings)
    _validate_scenarios(registry, findings)
    _validate_policies(registry, findings)
    _validate_controls(registry, findings)
    _validate_control_conditions(registry, findings)
    _validate_environments(registry, findings)
    _validate_instrument_configurations(registry, findings)
    _validate_scheduled_runs(registry, findings)
    _validate_run_manifests(registry, findings)
    _validate_capability_evaluations(registry, findings)
    _validate_validation_cases(registry, findings)
    _validate_instrument_acceptances(registry, findings)
    _validate_analysis_manifests(registry, findings)
    _validate_campaigns(registry, findings)

    return tuple(sorted(findings, key=_finding_sort_key))


def assert_artifact_set_valid(
    artifacts: ArtifactCollection,
    *,
    schema_store: SchemaStore,
) -> None:
    """Raise one aggregate error when ``validate_artifact_set`` finds defects."""

    findings = validate_artifact_set(artifacts, schema_store=schema_store)
    if findings:
        raise SemanticValidationError(findings)


def _validate_resources_and_tasks(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "benign_task"):
        artifact = record.artifact
        authorized = set(artifact["authorized_resources"])
        prohibited = set(artifact["prohibited_resources"])

        for field in ("authorized_resources", "prohibited_resources"):
            for index, resource_id in enumerate(artifact[field]):
                _require_reference(
                    record,
                    registry,
                    "resource",
                    resource_id,
                    _pointer(field, index),
                    findings,
                )

        for resource_id in sorted(authorized & prohibited):
            _add_conflict(
                record,
                findings,
                _pointer("authorized_resources"),
                f"resource {resource_id!r} is both authorized and prohibited",
                "resource",
                resource_id,
            )

        for field in ("required_authority", "optional_authority"):
            for index, authority in enumerate(artifact[field]):
                resource_id = authority["resource_id"]
                _require_reference(
                    record,
                    registry,
                    "resource",
                    resource_id,
                    _pointer(field, index, "resource_id"),
                    findings,
                )
                if resource_id in prohibited:
                    _add_conflict(
                        record,
                        findings,
                        _pointer(field, index, "resource_id"),
                        f"{field} refers to prohibited resource {resource_id!r}",
                        "resource",
                        resource_id,
                    )
                if field == "required_authority" and resource_id not in authorized:
                    _add_conflict(
                        record,
                        findings,
                        _pointer(field, index, "resource_id"),
                        (
                            f"required authority resource {resource_id!r} is not in "
                            "authorized_resources"
                        ),
                        "resource",
                        resource_id,
                    )


def _validate_capability_envelopes(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "capability_envelope"):
        artifact = record.artifact
        _require_reference(
            record,
            registry,
            "agent_model_condition",
            artifact["subject_agent_condition_id"],
            _pointer("subject_agent_condition_id"),
            findings,
        )
        _require_reference(
            record,
            registry,
            "benign_task",
            artifact["task_id"],
            _pointer("task_id"),
            findings,
        )
        _require_reference(
            record,
            registry,
            "policy",
            artifact["policy_id"],
            _pointer("policy_id"),
            findings,
        )

        seen: set[tuple[str, str]] = set()
        for index, entry in enumerate(artifact["entries"]):
            resource_id = entry["resource_id"]
            _require_reference(
                record,
                registry,
                "resource",
                resource_id,
                _pointer("entries", index, "resource_id"),
                findings,
            )
            key = (resource_id, entry["action_class"])
            if key in seen:
                _add_conflict(
                    record,
                    findings,
                    _pointer("entries", index),
                    (
                        "duplicate normative capability entry for resource/action "
                        f"pair {key!r}"
                    ),
                    "resource",
                    resource_id,
                )
            seen.add(key)


def _validate_scenarios(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "scenario"):
        artifact = record.artifact
        task = _require_reference(
            record,
            registry,
            "benign_task",
            artifact["benign_task_id"],
            _pointer("benign_task_id"),
            findings,
        )
        envelope = _require_reference(
            record,
            registry,
            "capability_envelope",
            artifact["capability_envelope_id"],
            _pointer("capability_envelope_id"),
            findings,
        )

        for field in (
            "protected_resource_set",
            "authorized_resource_set",
            "unauthorized_resource_set",
        ):
            for index, resource_id in enumerate(artifact[field]):
                _require_reference(
                    record,
                    registry,
                    "resource",
                    resource_id,
                    _pointer(field, index),
                    findings,
                )
        for index, state in enumerate(artifact["starting_state"]):
            _require_reference(
                record,
                registry,
                "resource",
                state["resource_id"],
                _pointer("starting_state", index, "resource_id"),
                findings,
            )

        authorized = set(artifact["authorized_resource_set"])
        unauthorized = set(artifact["unauthorized_resource_set"])
        for resource_id in sorted(authorized & unauthorized):
            _add_conflict(
                record,
                findings,
                _pointer("authorized_resource_set"),
                (
                    f"resource {resource_id!r} is in both authorized and "
                    "unauthorized scenario sets"
                ),
                "resource",
                resource_id,
            )

        if envelope is not None and envelope.artifact["task_id"] != artifact["benign_task_id"]:
            _add_conflict(
                record,
                findings,
                _pointer("capability_envelope_id"),
                (
                    "scenario benign_task_id does not match the referenced "
                    "Capability Envelope task_id"
                ),
                "capability_envelope",
                envelope.identity,
            )

        if task is not None:
            task_authorized = set(task.artifact["authorized_resources"])
            for resource_id in sorted(task_authorized - authorized):
                _add_conflict(
                    record,
                    findings,
                    _pointer("authorized_resource_set"),
                    (
                        f"scenario authorized resources omit Benign Task resource "
                        f"{resource_id!r}"
                    ),
                    "resource",
                    resource_id,
                )
            for resource_id in sorted(task_authorized & unauthorized):
                _add_conflict(
                    record,
                    findings,
                    _pointer("unauthorized_resource_set"),
                    (
                        f"scenario marks Benign Task authorized resource "
                        f"{resource_id!r} unauthorized"
                    ),
                    "resource",
                    resource_id,
                )


def _validate_policies(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "policy"):
        for index, rule in enumerate(record.artifact["rules"]):
            _require_reference(
                record,
                registry,
                "resource",
                rule["resource_id"],
                _pointer("rules", index, "resource_id"),
                findings,
            )
            subject = rule.get("subject_agent_condition_id")
            if subject is not None:
                _require_reference(
                    record,
                    registry,
                    "agent_model_condition",
                    subject,
                    _pointer("rules", index, "subject_agent_condition_id"),
                    findings,
                )
            # approval_policy_id intentionally has no resolvable contract family.


def _validate_controls(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    graph: dict[str, list[str]] = {
        record.identity: [] for record in _records(registry, "control")
    }
    for record in _records(registry, "control"):
        for index, dependency_id in enumerate(record.artifact["dependencies"]):
            path = _pointer("dependencies", index)
            if dependency_id == record.identity:
                findings.append(
                    SemanticFinding(
                        code=SemanticErrorCode.DEPENDENCY_INVALID,
                        message="control may not depend on itself",
                        artifact_family=record.family,
                        artifact_id=record.identity,
                        field_path=path,
                        referenced_artifact_family="control",
                        referenced_artifact_id=dependency_id,
                    )
                )
                continue
            dependency = registry.resolve("control", dependency_id)
            if dependency is None:
                findings.append(
                    SemanticFinding(
                        code=SemanticErrorCode.DEPENDENCY_INVALID,
                        message=(
                            f"control dependency {dependency_id!r} does not resolve "
                            "exactly once"
                        ),
                        artifact_family=record.family,
                        artifact_id=record.identity,
                        field_path=path,
                        referenced_artifact_family="control",
                        referenced_artifact_id=dependency_id,
                    )
                )
                continue
            graph[record.identity].append(dependency_id)

    for component in _strongly_connected_components(graph):
        if len(component) < 2:
            continue
        owner = component[0]
        findings.append(
            SemanticFinding(
                code=SemanticErrorCode.DEPENDENCY_INVALID,
                message=(
                    "control dependency cycle contains: " + ", ".join(component)
                ),
                artifact_family="control",
                artifact_id=owner,
                field_path=_pointer("dependencies"),
            )
        )


def _validate_control_conditions(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "control_condition"):
        artifact = record.artifact
        constituents = artifact["constituents"]
        counts = Counter(item["control_id"] for item in constituents)
        for control_id in sorted(key for key, count in counts.items() if count > 1):
            findings.append(
                SemanticFinding(
                    code=SemanticErrorCode.COMPOSITION_INVALID,
                    message=f"constituent control_id {control_id!r} occurs more than once",
                    artifact_family=record.family,
                    artifact_id=record.identity,
                    field_path=_pointer("constituents"),
                    referenced_artifact_family="control",
                    referenced_artifact_id=control_id,
                )
            )

        resolved: dict[str, _ArtifactRecord] = {}
        all_resolved = True
        for index, constituent in enumerate(constituents):
            control_id = constituent["control_id"]
            control = _require_reference(
                record,
                registry,
                "control",
                control_id,
                _pointer("constituents", index, "control_id"),
                findings,
            )
            if control is None:
                all_resolved = False
                continue
            resolved.setdefault(control_id, control)
            if constituent["control_version"] != control.version:
                findings.append(
                    SemanticFinding(
                        code=SemanticErrorCode.VERSION_INVALID,
                        message=(
                            f"constituent version {constituent['control_version']!r} "
                            f"does not match Control version {control.version!r}"
                        ),
                        artifact_family=record.family,
                        artifact_id=record.identity,
                        field_path=_pointer("constituents", index, "control_version"),
                        referenced_artifact_family="control",
                        referenced_artifact_id=control_id,
                    )
                )
            if constituent["configuration_id"] != control.artifact["configuration_id"]:
                _add_conflict(
                    record,
                    findings,
                    _pointer("constituents", index, "configuration_id"),
                    (
                        f"constituent configuration {constituent['configuration_id']!r} "
                        "does not match the resolved Control configuration"
                    ),
                    "control",
                    control_id,
                )

        order = artifact.get("composition_order")
        if order is not None:
            order_counts = Counter(order)
            constituent_counts = Counter(item["control_id"] for item in constituents)
            if order_counts != constituent_counts:
                findings.append(
                    SemanticFinding(
                        code=SemanticErrorCode.COMPOSITION_INVALID,
                        message=(
                            "composition_order must contain every constituent "
                            "control_id exactly once and no other IDs"
                        ),
                        artifact_family=record.family,
                        artifact_id=record.identity,
                        field_path=_pointer("composition_order"),
                    )
                )

        if not all_resolved or len(resolved) != len(constituents):
            continue
        layers = {
            control.artifact["experimental_control_layer"]
            for control in resolved.values()
        }
        composition_type = artifact["composition_type"]
        if composition_type == "COMBINED_M3":
            for control_id in sorted(resolved):
                if resolved[control_id].artifact["experimental_control_layer"] != "M3":
                    findings.append(
                        SemanticFinding(
                            code=SemanticErrorCode.COMPOSITION_INVALID,
                            message=(
                                f"COMBINED_M3 constituent {control_id!r} is not "
                                "declared M3"
                            ),
                            artifact_family=record.family,
                            artifact_id=record.identity,
                            field_path=_pointer("constituents"),
                            referenced_artifact_family="control",
                            referenced_artifact_id=control_id,
                        )
                    )
        elif composition_type == "LAYER_CONDITION" and len(layers) != 1:
            findings.append(
                SemanticFinding(
                    code=SemanticErrorCode.COMPOSITION_INVALID,
                    message="LAYER_CONDITION constituents must share one control layer",
                    artifact_family=record.family,
                    artifact_id=record.identity,
                    field_path=_pointer("constituents"),
                )
            )
        elif composition_type == "DEFENSE_IN_DEPTH" and len(layers) < 2:
            findings.append(
                SemanticFinding(
                    code=SemanticErrorCode.COMPOSITION_INVALID,
                    message=(
                        "DEFENSE_IN_DEPTH requires constituents from at least two "
                        "experimental control layers"
                    ),
                    artifact_family=record.family,
                    artifact_id=record.identity,
                    field_path=_pointer("constituents"),
                )
            )


def _validate_environments(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "environment"):
        artifact = record.artifact
        zone_ids = [entry["zone_id"] for entry in artifact["trust_zones"]]
        zones = set(zone_ids)
        _report_local_duplicates(record, findings, "trust_zones", "zone_id", zone_ids)

        for index, resource_id in enumerate(artifact["synthetic_assets"]):
            resource = _require_reference(
                record,
                registry,
                "resource",
                resource_id,
                _pointer("synthetic_assets", index),
                findings,
            )
            if resource is not None and resource.artifact["trust_zone"] not in zones:
                findings.append(
                    SemanticFinding(
                        code=SemanticErrorCode.ENVIRONMENT_INVALID,
                        message=(
                            f"Resource trust zone {resource.artifact['trust_zone']!r} "
                            "is not declared by the Environment"
                        ),
                        artifact_family=record.family,
                        artifact_id=record.identity,
                        field_path=_pointer("synthetic_assets", index),
                        referenced_artifact_family="resource",
                        referenced_artifact_id=resource_id,
                    )
                )

        for index, relationship in enumerate(artifact["network_relationships"]):
            for field in ("source_zone", "destination_zone"):
                zone = relationship[field]
                if zone not in zones:
                    _add_environment_error(
                        record,
                        findings,
                        _pointer("network_relationships", index, field),
                        f"network {field} {zone!r} is not declared",
                    )

        endpoint_ids = [entry["endpoint_id"] for entry in artifact["controlled_endpoints"]]
        _report_local_duplicates(
            record, findings, "controlled_endpoints", "endpoint_id", endpoint_ids
        )
        for index, endpoint in enumerate(artifact["controlled_endpoints"]):
            if endpoint["zone_id"] not in zones:
                _add_environment_error(
                    record,
                    findings,
                    _pointer("controlled_endpoints", index, "zone_id"),
                    f"controlled endpoint zone {endpoint['zone_id']!r} is not declared",
                )

        observer_ids = [entry["observer_id"] for entry in artifact["expected_observers"]]
        _report_local_duplicates(
            record, findings, "expected_observers", "observer_id", observer_ids
        )
        for index, observer in enumerate(artifact["expected_observers"]):
            if observer["trust_zone"] not in zones:
                _add_environment_error(
                    record,
                    findings,
                    _pointer("expected_observers", index, "trust_zone"),
                    f"observer trust zone {observer['trust_zone']!r} is not declared",
                )


def _validate_instrument_configurations(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "instrument_configuration"):
        artifact = record.artifact
        _require_reference(
            record,
            registry,
            "environment",
            artifact["environment_id"],
            _pointer("environment_id"),
            findings,
        )

        component_ids = [entry["component_id"] for entry in artifact["component_manifest"]]
        components = set(component_ids)
        _report_local_duplicates(
            record, findings, "component_manifest", "component_id", component_ids
        )
        observer_ids = [entry["observer_id"] for entry in artifact["observer_configuration"]]
        _report_local_duplicates(
            record, findings, "observer_configuration", "observer_id", observer_ids
        )

        for index, component in enumerate(artifact["component_manifest"]):
            for dep_index, dependency in enumerate(
                component["dependency_component_ids"]
            ):
                if dependency not in components:
                    _add_component_reference_error(
                        record,
                        findings,
                        _pointer(
                            "component_manifest",
                            index,
                            "dependency_component_ids",
                            dep_index,
                        ),
                        dependency,
                    )

        for index, observer in enumerate(artifact["observer_configuration"]):
            component_id = observer["component_id"]
            if component_id not in components:
                _add_component_reference_error(
                    record,
                    findings,
                    _pointer("observer_configuration", index, "component_id"),
                    component_id,
                )

        component_references = (
            (
                artifact["reset_configuration"]["reset_component_id"],
                _pointer("reset_configuration", "reset_component_id"),
            ),
            (
                artifact["evidence_pipeline_configuration"]["collector_component_id"],
                _pointer(
                    "evidence_pipeline_configuration", "collector_component_id"
                ),
            ),
            (
                artifact["orchestration_configuration"]["orchestration_component_id"],
                _pointer(
                    "orchestration_configuration", "orchestration_component_id"
                ),
            ),
        )
        for component_id, path in component_references:
            if component_id not in components:
                _add_component_reference_error(record, findings, path, component_id)


def _validate_scheduled_runs(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "scheduled_run"):
        _validate_run_references(record, registry, findings)


def _validate_run_manifests(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    shared_fields = (
        "experiment_id",
        "campaign_id",
        "scheduled_run_id",
        "phase",
        "scenario_id",
        "task_id",
        "agent_condition_id",
        "model_condition_id",
        "capability_condition_id",
        "autonomy_condition_id",
        "control_condition_id",
        "capability_envelope_id",
        "policy_id",
        "environment_id",
        "instrument_configuration_id",
        "seed_repetition_identity",
        "action_budget",
    )
    for record in _records(registry, "run_manifest"):
        artifact = record.artifact
        scheduled = registry.resolve("scheduled_run", artifact["scheduled_run_id"])
        if scheduled is None:
            findings.append(
                SemanticFinding(
                    code=SemanticErrorCode.RUN_MANIFEST_INVALID,
                    message=(
                        f"scheduled_run_id {artifact['scheduled_run_id']!r} does not "
                        "resolve exactly once"
                    ),
                    artifact_family=record.family,
                    artifact_id=record.identity,
                    field_path=_pointer("scheduled_run_id"),
                    referenced_artifact_family="scheduled_run",
                    referenced_artifact_id=artifact["scheduled_run_id"],
                )
            )
        else:
            for field in shared_fields:
                if artifact[field] != scheduled.artifact[field]:
                    findings.append(
                        SemanticFinding(
                            code=SemanticErrorCode.RUN_MANIFEST_INVALID,
                            message=(
                                f"Run Manifest {field} does not exactly match the "
                                "referenced Scheduled Run"
                            ),
                            artifact_family=record.family,
                            artifact_id=record.identity,
                            field_path=_pointer(field),
                            referenced_artifact_family="scheduled_run",
                            referenced_artifact_id=scheduled.identity,
                        )
                    )
            if (
                artifact["configuration_frozen_before_start"]
                != scheduled.artifact["scheduled_configuration_frozen"]
            ):
                findings.append(
                    SemanticFinding(
                        code=SemanticErrorCode.RUN_MANIFEST_INVALID,
                        message=(
                            "Run Manifest and Scheduled Run frozen-before-start "
                            "declarations do not match"
                        ),
                        artifact_family=record.family,
                        artifact_id=record.identity,
                        field_path=_pointer("configuration_frozen_before_start"),
                        referenced_artifact_family="scheduled_run",
                        referenced_artifact_id=scheduled.identity,
                    )
                )

        _validate_run_references(record, registry, findings)


def _validate_run_references(
    record: _ArtifactRecord,
    registry: _ArtifactRegistry,
    findings: list[SemanticFinding],
) -> None:
    artifact = record.artifact
    scenario = _require_reference(
        record, registry, "scenario", artifact["scenario_id"], _pointer("scenario_id"), findings
    )
    task = _require_reference(
        record, registry, "benign_task", artifact["task_id"], _pointer("task_id"), findings
    )
    agent = _require_reference(
        record,
        registry,
        "agent_model_condition",
        artifact["agent_condition_id"],
        _pointer("agent_condition_id"),
        findings,
    )
    model = _require_secondary_agent_reference(
        record,
        registry,
        "model_condition_id",
        artifact["model_condition_id"],
        findings,
    )
    capability = _require_secondary_agent_reference(
        record,
        registry,
        "capability_condition_id",
        artifact["capability_condition_id"],
        findings,
    )
    _require_reference(
        record,
        registry,
        "autonomy_condition",
        artifact["autonomy_condition_id"],
        _pointer("autonomy_condition_id"),
        findings,
    )
    _require_reference(
        record,
        registry,
        "control_condition",
        artifact["control_condition_id"],
        _pointer("control_condition_id"),
        findings,
    )
    envelope = _require_reference(
        record,
        registry,
        "capability_envelope",
        artifact["capability_envelope_id"],
        _pointer("capability_envelope_id"),
        findings,
    )
    _require_reference(
        record, registry, "policy", artifact["policy_id"], _pointer("policy_id"), findings
    )
    _require_reference(
        record,
        registry,
        "environment",
        artifact["environment_id"],
        _pointer("environment_id"),
        findings,
    )
    instrument = _require_reference(
        record,
        registry,
        "instrument_configuration",
        artifact["instrument_configuration_id"],
        _pointer("instrument_configuration_id"),
        findings,
    )

    if agent is not None and model is not None and model.identity != agent.identity:
        _add_conflict(
            record,
            findings,
            _pointer("model_condition_id"),
            "model_condition_id resolves to a different Agent/Model Condition",
            "agent_model_condition",
            model.identity,
        )
    if agent is not None and capability is not None and capability.identity != agent.identity:
        _add_conflict(
            record,
            findings,
            _pointer("capability_condition_id"),
            "capability_condition_id resolves to a different Agent/Model Condition",
            "agent_model_condition",
            capability.identity,
        )

    if scenario is not None:
        if artifact["task_id"] != scenario.artifact["benign_task_id"]:
            _add_conflict(
                record,
                findings,
                _pointer("task_id"),
                "task_id does not match the referenced Scenario benign_task_id",
                "scenario",
                scenario.identity,
            )
        if artifact["capability_envelope_id"] != scenario.artifact["capability_envelope_id"]:
            _add_conflict(
                record,
                findings,
                _pointer("capability_envelope_id"),
                (
                    "capability_envelope_id does not match the referenced Scenario "
                    "capability_envelope_id"
                ),
                "scenario",
                scenario.identity,
            )
    if envelope is not None:
        for field, envelope_field in (
            ("task_id", "task_id"),
            ("agent_condition_id", "subject_agent_condition_id"),
            ("policy_id", "policy_id"),
        ):
            if artifact[field] != envelope.artifact[envelope_field]:
                _add_conflict(
                    record,
                    findings,
                    _pointer(field),
                    (
                        f"{field} does not match Capability Envelope "
                        f"{envelope_field}"
                    ),
                    "capability_envelope",
                    envelope.identity,
                )
    if instrument is not None and artifact["environment_id"] != instrument.artifact["environment_id"]:
        findings.append(
            SemanticFinding(
                code=SemanticErrorCode.ENVIRONMENT_INVALID,
                message=(
                    "run environment_id does not match Instrument Configuration "
                    "environment_id"
                ),
                artifact_family=record.family,
                artifact_id=record.identity,
                field_path=_pointer("environment_id"),
                referenced_artifact_family="instrument_configuration",
                referenced_artifact_id=instrument.identity,
            )
        )

    # ``task`` is resolved independently even though its consistency is checked
    # through Scenario and Capability Envelope identity comparisons above.
    del task


def _validate_capability_evaluations(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "capability_evaluation"):
        artifact = record.artifact
        evaluated = set(artifact["evaluated_capability_conditions"])
        for index, capability_id in enumerate(
            artifact["evaluated_capability_conditions"]
        ):
            _require_capability_condition(
                record,
                registry,
                capability_id,
                _pointer("evaluated_capability_conditions", index),
                findings,
            )

        task_ids = [
            task["capability_task_id"] for task in artifact["capability_tasks"]
        ]
        declared_tasks = set(task_ids)
        _report_local_duplicates(
            record,
            findings,
            "capability_tasks",
            "capability_task_id",
            task_ids,
        )

        score_pairs: Counter[tuple[str, str]] = Counter()
        for index, score in enumerate(artifact["observed_scores"]):
            capability_id = score["capability_condition_id"]
            task_id = score["capability_task_id"]
            if capability_id not in evaluated:
                _add_stage10_finding(
                    record,
                    findings,
                    SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
                    _pointer("observed_scores", index, "capability_condition_id"),
                    (
                        f"observed score capability condition {capability_id!r} "
                        "is not declared in evaluated_capability_conditions"
                    ),
                    "agent_model_condition",
                    capability_id,
                )
            if task_id not in declared_tasks:
                _add_stage10_finding(
                    record,
                    findings,
                    SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
                    _pointer("observed_scores", index, "capability_task_id"),
                    f"observed score task {task_id!r} is not declared",
                    "capability_task",
                    task_id,
                )
            score_pairs[(capability_id, task_id)] += 1

        for pair in sorted(key for key, count in score_pairs.items() if count > 1):
            _add_stage10_finding(
                record,
                findings,
                SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
                _pointer("observed_scores"),
                f"duplicate semantic capability score for condition/task pair {pair!r}",
                "agent_model_condition",
                pair[0],
            )

        if artifact["capability_representation"] != "ORDERED":
            continue
        ordered_groups = artifact["ordering_result"]["ordered_groups"]
        ordered_ids = [item for group in ordered_groups for item in group]
        ordered_counts = Counter(ordered_ids)
        for capability_id in sorted(
            item for item, count in ordered_counts.items() if count > 1
        ):
            _add_stage10_finding(
                record,
                findings,
                SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
                _pointer("ordering_result", "ordered_groups"),
                f"ordered capability condition {capability_id!r} occurs more than once",
                "agent_model_condition",
                capability_id,
            )
        ordered = set(ordered_ids)
        for capability_id in sorted(ordered - evaluated):
            _add_stage10_finding(
                record,
                findings,
                SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
                _pointer("ordering_result", "ordered_groups"),
                f"ordering contains undeclared capability condition {capability_id!r}",
                "agent_model_condition",
                capability_id,
            )
        for capability_id in sorted(evaluated - ordered):
            _add_stage10_finding(
                record,
                findings,
                SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
                _pointer("ordering_result", "ordered_groups"),
                f"ordering omits evaluated capability condition {capability_id!r}",
                "agent_model_condition",
                capability_id,
            )


def _validate_validation_cases(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "validation_case"):
        artifact = record.artifact
        instrument = _require_reference(
            record,
            registry,
            "instrument_configuration",
            artifact["instrument_configuration_id"],
            _pointer("instrument_configuration_id"),
            findings,
        )
        if instrument is None:
            continue
        component_ids = {
            component["component_id"]
            for component in instrument.artifact["component_manifest"]
        }
        if artifact["applicable_component"] not in component_ids:
            _add_stage10_finding(
                record,
                findings,
                SemanticErrorCode.REFERENCE_INVALID,
                _pointer("applicable_component"),
                (
                    f"applicable component {artifact['applicable_component']!r} "
                    "is absent from the referenced Instrument Configuration"
                ),
                "instrument_component",
                artifact["applicable_component"],
            )


def _validate_instrument_acceptances(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "instrument_acceptance"):
        artifact = record.artifact
        instrument = _require_reference(
            record,
            registry,
            "instrument_configuration",
            artifact["instrument_configuration_id"],
            _pointer("instrument_configuration_id"),
            findings,
        )
        _require_reference(
            record,
            registry,
            "environment",
            artifact["environment_id"],
            _pointer("environment_id"),
            findings,
        )
        if instrument is not None:
            if artifact["instrument_configuration_version"] != instrument.version:
                _add_stage10_finding(
                    record,
                    findings,
                    SemanticErrorCode.VERSION_INVALID,
                    _pointer("instrument_configuration_version"),
                    (
                        "acceptance instrument configuration version does not "
                        "match the resolved Instrument Configuration"
                    ),
                    "instrument_configuration",
                    instrument.identity,
                )
            if artifact["environment_id"] != instrument.artifact["environment_id"]:
                _add_stage10_finding(
                    record,
                    findings,
                    SemanticErrorCode.ACCEPTANCE_INVALID,
                    _pointer("environment_id"),
                    (
                        "acceptance environment does not match the resolved "
                        "Instrument Configuration"
                    ),
                    "instrument_configuration",
                    instrument.identity,
                )
            _validate_acceptance_component_versions(
                record, instrument, findings
            )
        _validate_acceptance_results(record, registry, findings)


def _validate_acceptance_component_versions(
    acceptance: _ArtifactRecord,
    instrument: _ArtifactRecord,
    findings: list[SemanticFinding],
) -> None:
    accepted_components = acceptance.artifact["component_versions"]
    accepted_ids = [item["component_id"] for item in accepted_components]
    _report_local_duplicates(
        acceptance,
        findings,
        "component_versions",
        "component_id",
        accepted_ids,
    )
    accepted_by_id = {
        item["component_id"]: item
        for item in accepted_components
        if accepted_ids.count(item["component_id"]) == 1
    }
    configured_by_id = {
        item["component_id"]: item
        for item in instrument.artifact["component_manifest"]
    }
    for component_id in sorted(configured_by_id.keys() - accepted_by_id.keys()):
        _add_stage10_finding(
            acceptance,
            findings,
            SemanticErrorCode.ACCEPTANCE_INVALID,
            _pointer("component_versions"),
            f"acceptance omits configured component {component_id!r}",
            "instrument_component",
            component_id,
        )
    for component_id in sorted(accepted_by_id.keys() - configured_by_id.keys()):
        _add_stage10_finding(
            acceptance,
            findings,
            SemanticErrorCode.ACCEPTANCE_INVALID,
            _pointer("component_versions"),
            f"acceptance introduces undeclared component {component_id!r}",
            "instrument_component",
            component_id,
        )
    for component_id in sorted(accepted_by_id.keys() & configured_by_id.keys()):
        if (
            accepted_by_id[component_id]["component_version"]
            != configured_by_id[component_id]["component_version"]
        ):
            _add_stage10_finding(
                acceptance,
                findings,
                SemanticErrorCode.VERSION_INVALID,
                _pointer("component_versions"),
                f"accepted component {component_id!r} version does not match",
                "instrument_component",
                component_id,
            )


def _validate_acceptance_results(
    acceptance: _ArtifactRecord,
    registry: _ArtifactRegistry,
    findings: list[SemanticFinding],
) -> None:
    artifact = acceptance.artifact
    results = artifact["validation_results"]
    counts = Counter(item["validation_case_id"] for item in results)
    for case_id in sorted(item for item, count in counts.items() if count > 1):
        _add_stage10_finding(
            acceptance,
            findings,
            SemanticErrorCode.VALIDATION_INCOMPLETE,
            _pointer("validation_results"),
            f"validation case {case_id!r} is represented more than once",
            "validation_case",
            case_id,
        )

    accepted = artifact["acceptance_state"] in {
        "ACCEPTED_FOR_PILOT",
        "ACCEPTED_FOR_CONFIRMATORY",
    }
    for index, result in enumerate(results):
        case_id = result["validation_case_id"]
        case = registry.resolve("validation_case", case_id)
        if case is None:
            _add_stage10_finding(
                acceptance,
                findings,
                SemanticErrorCode.REFERENCE_INVALID,
                _pointer("validation_results", index, "validation_case_id"),
                f"validation case {case_id!r} does not resolve exactly once",
                "validation_case",
                case_id,
            )
            continue
        if result["validation_case_version"] != case.version:
            _add_stage10_finding(
                acceptance,
                findings,
                SemanticErrorCode.VERSION_INVALID,
                _pointer("validation_results", index, "validation_case_version"),
                "validation result version does not match the Validation Case",
                "validation_case",
                case_id,
            )
        if result["applicability_class"] != case.artifact["applicability_class"]:
            _add_stage10_finding(
                acceptance,
                findings,
                SemanticErrorCode.ACCEPTANCE_INVALID,
                _pointer("validation_results", index, "applicability_class"),
                "validation result applicability does not match the Validation Case",
                "validation_case",
                case_id,
            )
        if result["validation_phase"] != case.artifact["validation_phase"]:
            _add_stage10_finding(
                acceptance,
                findings,
                SemanticErrorCode.ACCEPTANCE_INVALID,
                _pointer("validation_results", index, "validation_phase"),
                "validation result phase does not match the Validation Case",
                "validation_case",
                case_id,
            )
        if (
            case.artifact["instrument_configuration_id"]
            != artifact["instrument_configuration_id"]
        ):
            _add_stage10_finding(
                acceptance,
                findings,
                SemanticErrorCode.ACCEPTANCE_INVALID,
                _pointer("validation_results", index, "validation_case_id"),
                "Validation Case targets a different Instrument Configuration",
                "validation_case",
                case_id,
            )
        if not accepted:
            continue
        applicability = case.artifact["applicability_class"]
        result_state = result["result_state"]
        if applicability == "MANDATORY_GLOBAL" and result_state != "VALIDATION_PASS":
            _add_stage10_finding(
                acceptance,
                findings,
                SemanticErrorCode.ACCEPTANCE_INVALID,
                _pointer("validation_results", index, "result_state"),
                "accepted instrument requires MANDATORY_GLOBAL validation PASS",
                "validation_case",
                case_id,
            )
        elif applicability == "MANDATORY_CONDITIONAL" and result_state in {
            "VALIDATION_FAIL",
            "VALIDATION_INCONCLUSIVE",
        }:
            _add_stage10_finding(
                acceptance,
                findings,
                SemanticErrorCode.ACCEPTANCE_INVALID,
                _pointer("validation_results", index, "result_state"),
                "represented mandatory conditional validation did not pass",
                "validation_case",
                case_id,
            )

    if not accepted:
        return
    for case in _records(registry, "validation_case"):
        if (
            case.artifact["instrument_configuration_id"]
            != artifact["instrument_configuration_id"]
            or case.artifact["applicability_class"] != "MANDATORY_GLOBAL"
        ):
            continue
        exact_results = [
            result
            for result in results
            if result["validation_case_id"] == case.identity
            and result["validation_case_version"] == case.version
        ]
        if len(exact_results) != 1:
            _add_stage10_finding(
                acceptance,
                findings,
                SemanticErrorCode.VALIDATION_INCOMPLETE,
                _pointer("validation_results"),
                (
                    f"MANDATORY_GLOBAL Validation Case {case.identity!r} version "
                    f"{case.version!r} must appear exactly once"
                ),
                "validation_case",
                case.identity,
            )


def _validate_analysis_manifests(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    invariants = {
        "primary_endpoint": "RUN_LEVEL_ANY_UNAUTHORIZED_EXECUTED",
        "primary_estimand": "RISK_DIFFERENCE",
        "primary_effect_direction": "M3_MINUS_M1",
    }
    for record in _records(registry, "analysis_manifest"):
        artifact = record.artifact
        for field, expected in invariants.items():
            if artifact[field] != expected:
                _add_stage10_finding(
                    record,
                    findings,
                    SemanticErrorCode.ANALYSIS_INVALID,
                    _pointer(field),
                    f"{field} must remain {expected!r}",
                )
        for field in (
            "primary_m1_control_condition_id",
            "primary_m3_control_condition_id",
        ):
            if field in artifact:
                _require_reference(
                    record,
                    registry,
                    "control_condition",
                    artifact[field],
                    _pointer(field),
                    findings,
                )
        for index, scenario_id in enumerate(artifact.get("scenario_subset", [])):
            _require_reference(
                record,
                registry,
                "scenario",
                scenario_id,
                _pointer("scenario_subset", index),
                findings,
            )
        for index, agent_id in enumerate(artifact.get("agent_condition_subset", [])):
            _require_reference(
                record,
                registry,
                "agent_model_condition",
                agent_id,
                _pointer("agent_condition_subset", index),
                findings,
            )
        capability = artifact.get("capability_representation")
        if capability is not None and "capability_evaluation_reference" in capability:
            _require_reference(
                record,
                registry,
                "capability_evaluation",
                capability["capability_evaluation_reference"],
                _pointer(
                    "capability_representation", "capability_evaluation_reference"
                ),
                findings,
            )


def _validate_campaigns(
    registry: _ArtifactRegistry, findings: list[SemanticFinding]
) -> None:
    for record in _records(registry, "campaign"):
        artifact = record.artifact
        for field, family in (
            ("scenario_ids", "scenario"),
            ("agent_condition_ids", "agent_model_condition"),
            ("autonomy_condition_ids", "autonomy_condition"),
            ("control_condition_ids", "control_condition"),
        ):
            for index, identity in enumerate(artifact[field]):
                _require_reference(
                    record,
                    registry,
                    family,
                    identity,
                    _pointer(field, index),
                    findings,
                )
        _require_reference(
            record,
            registry,
            "environment",
            artifact["environment_id"],
            _pointer("environment_id"),
            findings,
        )
        instrument = _require_reference(
            record,
            registry,
            "instrument_configuration",
            artifact["instrument_configuration_id"],
            _pointer("instrument_configuration_id"),
            findings,
        )
        if (
            instrument is not None
            and instrument.artifact["environment_id"] != artifact["environment_id"]
        ):
            _add_stage10_finding(
                record,
                findings,
                SemanticErrorCode.CAMPAIGN_INVALID,
                _pointer("environment_id"),
                "Campaign environment does not match Instrument Configuration",
                "instrument_configuration",
                instrument.identity,
            )

        scheduled = _validate_campaign_schedule(record, registry, findings)
        capability_evaluation = _resolve_campaign_capability_evaluation(
            record, registry, findings
        )
        _validate_campaign_capability_coverage(
            record, capability_evaluation, registry, findings
        )

        if artifact["phase"] in {"PILOT", "CONFIRMATORY"}:
            _validate_campaign_acceptance(record, registry, findings)
        if artifact["phase"] == "CONFIRMATORY":
            _validate_confirmatory_analysis(
                record,
                scheduled,
                capability_evaluation,
                registry,
                findings,
            )


def _validate_campaign_schedule(
    campaign: _ArtifactRecord,
    registry: _ArtifactRegistry,
    findings: list[SemanticFinding],
) -> list[_ArtifactRecord]:
    artifact = campaign.artifact
    scheduled: list[_ArtifactRecord] = []
    for index, scheduled_id in enumerate(artifact["scheduled_run_ids"]):
        run = registry.resolve("scheduled_run", scheduled_id)
        if run is None:
            _add_stage10_finding(
                campaign,
                findings,
                SemanticErrorCode.CAMPAIGN_INVALID,
                _pointer("scheduled_run_ids", index),
                f"Scheduled Run {scheduled_id!r} does not resolve exactly once",
                "scheduled_run",
                scheduled_id,
            )
            continue
        scheduled.append(run)
        for field in (
            "experiment_id",
            "campaign_id",
            "phase",
            "environment_id",
            "instrument_configuration_id",
        ):
            if run.artifact[field] != artifact[field]:
                _add_stage10_finding(
                    campaign,
                    findings,
                    SemanticErrorCode.CAMPAIGN_INVALID,
                    _pointer("scheduled_run_ids", index),
                    f"Scheduled Run {field} does not match Campaign",
                    "scheduled_run",
                    run.identity,
                )
        for run_field, campaign_field in (
            ("scenario_id", "scenario_ids"),
            ("agent_condition_id", "agent_condition_ids"),
            ("autonomy_condition_id", "autonomy_condition_ids"),
            ("control_condition_id", "control_condition_ids"),
        ):
            if run.artifact[run_field] not in artifact[campaign_field]:
                _add_stage10_finding(
                    campaign,
                    findings,
                    SemanticErrorCode.CAMPAIGN_INVALID,
                    _pointer("scheduled_run_ids", index),
                    (
                        f"Scheduled Run {run_field} is absent from Campaign "
                        f"{campaign_field}"
                    ),
                    "scheduled_run",
                    run.identity,
                )

    listed = set(artifact["scheduled_run_ids"])
    for run in _records(registry, "scheduled_run"):
        if run.artifact["campaign_id"] == campaign.identity and run.identity not in listed:
            _add_stage10_finding(
                campaign,
                findings,
                SemanticErrorCode.CAMPAIGN_INVALID,
                _pointer("scheduled_run_ids"),
                f"active Campaign Scheduled Run {run.identity!r} is unlisted",
                "scheduled_run",
                run.identity,
            )
    ordinals = Counter(run.artifact["schedule_ordinal"] for run in scheduled)
    for ordinal in sorted(item for item, count in ordinals.items() if count > 1):
        _add_stage10_finding(
            campaign,
            findings,
            SemanticErrorCode.CAMPAIGN_INVALID,
            _pointer("scheduled_run_ids"),
            f"schedule_ordinal {ordinal} occurs more than once in Campaign",
        )
    return scheduled


def _resolve_campaign_capability_evaluation(
    campaign: _ArtifactRecord,
    registry: _ArtifactRegistry,
    findings: list[SemanticFinding],
) -> _ArtifactRecord | None:
    reference = campaign.artifact.get("capability_evaluation_reference")
    if reference is None:
        return None
    evaluation = _require_reference(
        campaign,
        registry,
        "capability_evaluation",
        reference,
        _pointer("capability_evaluation_reference"),
        findings,
    )
    if evaluation is None:
        return None
    if campaign.artifact["phase"] == "CONFIRMATORY":
        if evaluation.artifact["evaluation_state"] != "FROZEN_FOR_CONFIRMATORY_USE":
            _add_stage10_finding(
                campaign,
                findings,
                SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
                _pointer("capability_evaluation_reference"),
                "Confirmatory Campaign requires a frozen Capability Evaluation",
                "capability_evaluation",
                evaluation.identity,
            )
        if evaluation.artifact["containment_outcomes_used"] is not False:
            _add_stage10_finding(
                campaign,
                findings,
                SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
                _pointer("capability_evaluation_reference"),
                "Capability Evaluation must exclude containment outcomes",
                "capability_evaluation",
                evaluation.identity,
            )
    return evaluation


def _validate_campaign_capability_coverage(
    campaign: _ArtifactRecord,
    evaluation: _ArtifactRecord | None,
    registry: _ArtifactRegistry,
    findings: list[SemanticFinding],
) -> None:
    if evaluation is None or campaign.artifact["phase"] not in {"PILOT", "CONFIRMATORY"}:
        return
    evaluated = set(evaluation.artifact["evaluated_capability_conditions"])
    for index, agent_id in enumerate(campaign.artifact["agent_condition_ids"]):
        agent = registry.resolve("agent_model_condition", agent_id)
        if agent is None:
            continue
        capability_id = agent.artifact["capability_condition_id"]
        if capability_id not in evaluated:
            _add_stage10_finding(
                campaign,
                findings,
                SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
                _pointer("agent_condition_ids", index),
                (
                    f"Campaign capability condition {capability_id!r} is absent "
                    "from the referenced Capability Evaluation"
                ),
                "capability_evaluation",
                evaluation.identity,
            )


def _validate_campaign_acceptance(
    campaign: _ArtifactRecord,
    registry: _ArtifactRegistry,
    findings: list[SemanticFinding],
) -> None:
    phase = campaign.artifact["phase"]
    expected_state = (
        "ACCEPTED_FOR_PILOT"
        if phase == "PILOT"
        else "ACCEPTED_FOR_CONFIRMATORY"
    )
    compatible = [
        acceptance
        for acceptance in _records(registry, "instrument_acceptance")
        if acceptance.artifact["instrument_configuration_id"]
        == campaign.artifact["instrument_configuration_id"]
        and acceptance.artifact["environment_id"]
        == campaign.artifact["environment_id"]
        and acceptance.artifact["campaign_id"] == campaign.identity
        and acceptance.artifact["acceptance_state"] == expected_state
        and acceptance.artifact.get("accepted_for_phase") == phase
    ]
    if len(compatible) != 1:
        _add_stage10_finding(
            campaign,
            findings,
            SemanticErrorCode.ACCEPTANCE_INVALID,
            _pointer("instrument_acceptance_reference"),
            (
                f"{phase} Campaign requires exactly one compatible {expected_state} "
                f"acceptance; found {len(compatible)}"
            ),
            "instrument_acceptance",
            None,
        )
    # No intrinsic acceptance ID exists in v0.1. The opaque Campaign reference
    # cannot be content-resolved, so unique compatibility gates readiness but
    # does not prove the provenance of instrument_acceptance_reference.


def _validate_confirmatory_analysis(
    campaign: _ArtifactRecord,
    scheduled: list[_ArtifactRecord],
    evaluation: _ArtifactRecord | None,
    registry: _ArtifactRegistry,
    findings: list[SemanticFinding],
) -> None:
    analysis_id = campaign.artifact["analysis_configuration_id"]
    analysis = registry.resolve("analysis_manifest", analysis_id)
    if analysis is None:
        _add_stage10_finding(
            campaign,
            findings,
            SemanticErrorCode.ANALYSIS_INVALID,
            _pointer("analysis_configuration_id"),
            f"Analysis Manifest {analysis_id!r} does not resolve exactly once",
            "analysis_manifest",
            analysis_id,
        )
        return
    artifact = analysis.artifact
    if artifact["analysis_state"] != "FROZEN_FOR_CONFIRMATORY":
        _add_analysis_gate_error(
            analysis,
            campaign,
            findings,
            _pointer("analysis_state"),
            "Confirmatory Campaign requires FROZEN_FOR_CONFIRMATORY analysis",
        )
        return

    m1_id = artifact["primary_m1_control_condition_id"]
    m3_id = artifact["primary_m3_control_condition_id"]
    m1 = registry.resolve("control_condition", m1_id)
    m3 = registry.resolve("control_condition", m3_id)
    if m1 is not None and _declared_pure_control_layer(m1, registry) != "M1":
        _add_analysis_gate_error(
            analysis,
            campaign,
            findings,
            _pointer("primary_m1_control_condition_id"),
            "primary M1 comparator is not a declaratively pure M1 condition",
            "control_condition",
            m1_id,
        )
    if m3 is not None and _declared_pure_control_layer(m3, registry) != "M3":
        _add_analysis_gate_error(
            analysis,
            campaign,
            findings,
            _pointer("primary_m3_control_condition_id"),
            "primary M3 comparator is not a declaratively pure M3 condition",
            "control_condition",
            m3_id,
        )
    for field, comparator_id in (
        ("primary_m1_control_condition_id", m1_id),
        ("primary_m3_control_condition_id", m3_id),
    ):
        if comparator_id not in campaign.artifact["control_condition_ids"]:
            _add_analysis_gate_error(
                analysis,
                campaign,
                findings,
                _pointer(field),
                "primary comparator is absent from Campaign control conditions",
                "control_condition",
                comparator_id,
            )
        if not any(
            run.artifact["control_condition_id"] == comparator_id for run in scheduled
        ):
            _add_analysis_gate_error(
                analysis,
                campaign,
                findings,
                _pointer(field),
                "primary comparator is absent from Campaign Scheduled Runs",
                "control_condition",
                comparator_id,
            )

    scheduled_scenarios = {run.artifact["scenario_id"] for run in scheduled}
    for index, scenario_id in enumerate(artifact["scenario_subset"]):
        if scenario_id not in campaign.artifact["scenario_ids"]:
            _add_analysis_gate_error(
                analysis,
                campaign,
                findings,
                _pointer("scenario_subset", index),
                "analysis scenario is absent from Campaign",
                "scenario",
                scenario_id,
            )
        elif scenario_id not in scheduled_scenarios:
            _add_analysis_gate_error(
                analysis,
                campaign,
                findings,
                _pointer("scenario_subset", index),
                "analysis scenario has no Campaign Scheduled Run",
                "scenario",
                scenario_id,
            )

    scheduled_agents = {run.artifact["agent_condition_id"] for run in scheduled}
    for index, agent_id in enumerate(artifact["agent_condition_subset"]):
        if agent_id not in campaign.artifact["agent_condition_ids"]:
            _add_analysis_gate_error(
                analysis,
                campaign,
                findings,
                _pointer("agent_condition_subset", index),
                "analysis agent condition is absent from Campaign",
                "agent_model_condition",
                agent_id,
            )
        elif agent_id not in scheduled_agents:
            _add_analysis_gate_error(
                analysis,
                campaign,
                findings,
                _pointer("agent_condition_subset", index),
                "analysis agent condition has no Campaign Scheduled Run",
                "agent_model_condition",
                agent_id,
            )

    if evaluation is not None:
        analysis_representation = artifact["capability_representation"][
            "representation"
        ]
        if analysis_representation != evaluation.artifact["capability_representation"]:
            _add_analysis_gate_error(
                analysis,
                campaign,
                findings,
                _pointer("capability_representation", "representation"),
                "analysis and Capability Evaluation representations do not match",
                "capability_evaluation",
                evaluation.identity,
            )
        analysis_reference = artifact["capability_representation"].get(
            "capability_evaluation_reference"
        )
        if analysis_reference is not None and analysis_reference != evaluation.identity:
            _add_analysis_gate_error(
                analysis,
                campaign,
                findings,
                _pointer(
                    "capability_representation", "capability_evaluation_reference"
                ),
                "analysis references a different Capability Evaluation",
                "capability_evaluation",
                analysis_reference,
            )

    sample_size = artifact["sample_size"]
    scheduled_run_count = (
        sample_size
        if isinstance(sample_size, int)
        else sample_size["scheduled_run_count"]
    )
    if scheduled_run_count != len(campaign.artifact["scheduled_run_ids"]):
        _add_analysis_gate_error(
            analysis,
            campaign,
            findings,
            _pointer("sample_size"),
            (
                "frozen sample-size scheduled run count does not equal the "
                "Campaign scheduled-run denominator"
            ),
        )


def _declared_pure_control_layer(
    condition: _ArtifactRecord, registry: _ArtifactRegistry
) -> str | None:
    composition = condition.artifact["composition_type"]
    if composition == "DEFENSE_IN_DEPTH":
        return None
    layers: set[str] = set()
    for constituent in condition.artifact["constituents"]:
        control = registry.resolve("control", constituent["control_id"])
        if control is None:
            return None
        layers.add(control.artifact["experimental_control_layer"])
    if len(layers) != 1:
        return None
    layer = next(iter(layers))
    if composition in {"SINGLE_CONTROL", "LAYER_CONDITION"}:
        return layer
    if composition == "COMBINED_M3" and layer == "M3":
        return "M3"
    return None


def _require_capability_condition(
    owner: _ArtifactRecord,
    registry: _ArtifactRegistry,
    capability_id: str,
    field_path: str,
    findings: list[SemanticFinding],
) -> _ArtifactRecord | None:
    target = registry.capability_conditions.get(capability_id)
    if target is not None:
        return target
    _add_stage10_finding(
        owner,
        findings,
        SemanticErrorCode.REFERENCE_INVALID,
        field_path,
        f"capability condition {capability_id!r} does not resolve exactly once",
        "agent_model_condition",
        capability_id,
    )
    return None


def _add_analysis_gate_error(
    analysis: _ArtifactRecord,
    campaign: _ArtifactRecord,
    findings: list[SemanticFinding],
    field_path: str,
    message: str,
    referenced_family: str | None = None,
    referenced_id: str | None = None,
) -> None:
    _add_stage10_finding(
        analysis,
        findings,
        SemanticErrorCode.ANALYSIS_INVALID,
        field_path,
        f"{message} for Campaign {campaign.identity!r}",
        referenced_family,
        referenced_id,
    )


def _add_stage10_finding(
    owner: _ArtifactRecord,
    findings: list[SemanticFinding],
    code: SemanticErrorCode,
    field_path: str,
    message: str,
    referenced_family: str | None = None,
    referenced_id: str | None = None,
) -> None:
    findings.append(
        SemanticFinding(
            code=code,
            message=message,
            artifact_family=owner.family,
            artifact_id=owner.identity,
            field_path=field_path,
            referenced_artifact_family=referenced_family,
            referenced_artifact_id=referenced_id,
        )
    )


def _records(registry: _ArtifactRegistry, family: str) -> list[_ArtifactRecord]:
    if SUPPORTED_ARTIFACT_FAMILIES[family].identity_field is None:
        return sorted(
            registry.records.get(family, []),
            key=lambda record: (record.identity, record.version, record.ordinal),
        )
    return sorted(
        registry.primary.get(family, {}).values(),
        key=lambda record: (record.identity, record.version, record.ordinal),
    )


def _require_reference(
    owner: _ArtifactRecord,
    registry: _ArtifactRegistry,
    family: str,
    identity: str,
    field_path: str,
    findings: list[SemanticFinding],
) -> _ArtifactRecord | None:
    target = registry.resolve(family, identity)
    if target is not None:
        return target
    findings.append(
        SemanticFinding(
            code=SemanticErrorCode.REFERENCE_INVALID,
            message=(
                f"{family} reference {identity!r} does not resolve exactly once "
                "in the active artifact set"
            ),
            artifact_family=owner.family,
            artifact_id=owner.identity,
            field_path=field_path,
            referenced_artifact_family=family,
            referenced_artifact_id=identity,
        )
    )
    return None


def _require_secondary_agent_reference(
    owner: _ArtifactRecord,
    registry: _ArtifactRegistry,
    field: str,
    identity: str,
    findings: list[SemanticFinding],
) -> _ArtifactRecord | None:
    index = (
        registry.model_conditions
        if field == "model_condition_id"
        else registry.capability_conditions
    )
    target = index.get(identity)
    if target is not None:
        return target
    findings.append(
        SemanticFinding(
            code=SemanticErrorCode.REFERENCE_INVALID,
            message=(
                f"secondary Agent/Model identity {identity!r} for {field} does "
                "not resolve exactly once"
            ),
            artifact_family=owner.family,
            artifact_id=owner.identity,
            field_path=_pointer(field),
            referenced_artifact_family="agent_model_condition",
            referenced_artifact_id=identity,
        )
    )
    return None


def _add_conflict(
    owner: _ArtifactRecord,
    findings: list[SemanticFinding],
    field_path: str,
    message: str,
    referenced_family: str | None = None,
    referenced_id: str | None = None,
) -> None:
    findings.append(
        SemanticFinding(
            code=SemanticErrorCode.SEMANTIC_CONFLICT,
            message=message,
            artifact_family=owner.family,
            artifact_id=owner.identity,
            field_path=field_path,
            referenced_artifact_family=referenced_family,
            referenced_artifact_id=referenced_id,
        )
    )


def _add_environment_error(
    owner: _ArtifactRecord,
    findings: list[SemanticFinding],
    field_path: str,
    message: str,
) -> None:
    findings.append(
        SemanticFinding(
            code=SemanticErrorCode.ENVIRONMENT_INVALID,
            message=message,
            artifact_family=owner.family,
            artifact_id=owner.identity,
            field_path=field_path,
        )
    )


def _add_component_reference_error(
    owner: _ArtifactRecord,
    findings: list[SemanticFinding],
    field_path: str,
    component_id: str,
) -> None:
    findings.append(
        SemanticFinding(
            code=SemanticErrorCode.REFERENCE_INVALID,
            message=(
                f"instrument component reference {component_id!r} is absent from "
                "component_manifest"
            ),
            artifact_family=owner.family,
            artifact_id=owner.identity,
            field_path=field_path,
            referenced_artifact_family="instrument_component",
            referenced_artifact_id=component_id,
        )
    )


def _report_local_duplicates(
    owner: _ArtifactRecord,
    findings: list[SemanticFinding],
    collection_field: str,
    identity_field: str,
    values: Iterable[str],
) -> None:
    counts = Counter(values)
    for value in sorted(item for item, count in counts.items() if count > 1):
        findings.append(
            SemanticFinding(
                code=SemanticErrorCode.DUPLICATE_IDENTITY,
                message=(
                    f"local {identity_field} identity {value!r} occurs more than once"
                ),
                artifact_family=owner.family,
                artifact_id=owner.identity,
                field_path=_pointer(collection_field),
                referenced_artifact_id=value,
            )
        )


def _strongly_connected_components(graph: Mapping[str, Iterable[str]]) -> list[list[str]]:
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for dependency in sorted(graph.get(node, ())):
            if dependency not in indices:
                visit(dependency)
                lowlinks[node] = min(lowlinks[node], lowlinks[dependency])
            elif dependency in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[dependency])

        if lowlinks[node] != indices[node]:
            return
        component: list[str] = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break
        components.append(sorted(component))

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return sorted(components, key=lambda component: tuple(component))


def _finding_sort_key(finding: SemanticFinding) -> tuple[str, ...]:
    return (
        finding.artifact_family,
        finding.artifact_id,
        finding.field_path,
        finding.code.value,
        finding.referenced_artifact_family or "",
        finding.referenced_artifact_id or "",
        finding.message,
    )


def _pointer(*segments: str | int) -> str:
    if not segments:
        return "/"
    escaped = [str(value).replace("~", "~0").replace("/", "~1") for value in segments]
    return "/" + "/".join(escaped)


def _error_pointer(error: ValidationError) -> str:
    return _pointer(*error.absolute_path)


def _best_effort_identity(
    artifact: Any, ordinal: int, *, preferred: str | None = None
) -> str:
    if isinstance(artifact, Mapping):
        if preferred is not None and isinstance(artifact.get(preferred), str):
            return artifact[preferred]
        for key in sorted(artifact):
            if key.endswith("_id") and isinstance(artifact[key], str):
                return artifact[key]
    return f"<item:{ordinal}>"
