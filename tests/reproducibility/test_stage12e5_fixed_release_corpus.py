"""Fixed Stage 12E-5 synthetic release corpus regression closure."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
from typing import Any

import pytest

from frontier_agent_containment.integrity import (
    canonical_sha256,
    canonicalize_json,
    forensic_sha256_bytes,
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
)
from frontier_agent_containment.release_assembly import (
    ArtifactAssemblyMetadata,
    PhaseProjection,
    RejectedInputAssemblyMetadata,
    RepetitionIdentity,
    build_research_release,
    write_research_release,
)
import frontier_agent_containment.release_integrity_audit as audit_module
from frontier_agent_containment.release_integrity_audit import (
    ReleaseIntegrityAuditErrorCode,
    audit_research_release_integrity,
)
from frontier_agent_containment.schema_validation import load_schema_store
from frontier_agent_containment.semantic_validation import (
    get_artifact_family_contract_spec,
    get_artifact_family_spec,
)


ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = ROOT / "tests" / "fixtures" / "reproducibility" / "stage12e5"
INDEX_PATH = CORPUS_ROOT / "corpus-index.json"
PACKAGE_FILES = (
    "artifact-manifest.json",
    "release-build.json",
    "reproducibility-manifest.json",
)
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
CASE_ID_PATTERN = re.compile(r"^stage12e5:[a-z0-9]+(?:-[a-z0-9]+)*$")

CASE_IDS = (
    "stage12e5:binding-active-artifact",
    "stage12e5:binding-build-id",
    "stage12e5:binding-dependency-projection",
    "stage12e5:binding-environment-content",
    "stage12e5:binding-environment-reference",
    "stage12e5:binding-governing-document",
    "stage12e5:binding-rejected-input",
    "stage12e5:binding-repro-build-identity",
    "stage12e5:binding-schema-set",
    "stage12e5:binding-source-git",
    "stage12e5:dependency-confirmatory-missing-provenance",
    "stage12e5:dependency-development-empty-limitations",
    "stage12e5:dependency-development-nonempty-limitations",
    "stage12e5:dependency-name",
    "stage12e5:dependency-order",
    "stage12e5:dependency-provenance-projection",
    "stage12e5:dependency-version",
    "stage12e5:json-duplicate-key",
    "stage12e5:json-infinity",
    "stage12e5:json-malformed-json",
    "stage12e5:json-malformed-utf8",
    "stage12e5:json-nan",
    "stage12e5:json-negative-infinity",
    "stage12e5:layout-directory-child",
    "stage12e5:layout-extra-child",
    "stage12e5:layout-missing-file",
    "stage12e5:layout-symlink-child",
    "stage12e5:multi-five-finding-order",
    "stage12e5:order-artifacts",
    "stage12e5:order-control-subset",
    "stage12e5:order-dependencies",
    "stage12e5:order-governing-documents",
    "stage12e5:order-limitations",
    "stage12e5:order-providers",
    "stage12e5:order-rejected-inputs",
    "stage12e5:order-repetitions",
    "stage12e5:order-run-ids",
    "stage12e5:order-scenario-subset",
    "stage12e5:order-scheduled-run-ids",
    "stage12e5:order-schema-set",
    "stage12e5:package-read-failed",
    "stage12e5:physical-compact-json",
    "stage12e5:physical-crlf",
    "stage12e5:physical-double-terminal-lf",
    "stage12e5:physical-escaped-unicode",
    "stage12e5:physical-no-terminal-lf",
    "stage12e5:physical-unsorted-keys",
    "stage12e5:valid-confirmatory",
    "stage12e5:valid-development",
    "stage12e5:validation-build-consistency",
    "stage12e5:validation-build-schema",
    "stage12e5:validation-identity5-version",
    "stage12e5:validation-repro-environment",
    "stage12e5:validation-stage12d-artifact-digest",
    "stage12e5:version-artifact-manifest",
    "stage12e5:version-release-build",
    "stage12e5:version-reproducibility-manifest",
)

EXPECTED_AUDIT_CODES = {
    "AUDIT_PACKAGE_LAYOUT_INVALID",
    "AUDIT_PACKAGE_READ_FAILED",
    "AUDIT_JSON_INVALID",
    "AUDIT_PHYSICAL_SERIALIZATION_INVALID",
    "AUDIT_GENERATED_VERSION_INVALID",
    "AUDIT_DETERMINISTIC_ORDER_INVALID",
    "AUDIT_RELEASE_BINDING_INVALID",
    "AUDIT_DEPENDENCY_PROVENANCE_INCOMPLETE",
    "AUDIT_VALIDATION_FAILED",
}

MUTATION_FIELDS = {
    "none": {"kind", "target"},
    "remove-package-child": {"kind", "target"},
    "add-package-child": {"kind", "target", "content_utf8"},
    "symlink-package-child": {"kind", "target", "link_target"},
    "directory-package-child": {"kind", "target"},
    "inject-read-failure": {"kind", "target"},
    "replace-package-bytes": {"kind", "target", "fixture_path"},
    "physical-no-terminal-lf": {"kind", "target", "derived_file_sha256"},
    "physical-double-terminal-lf": {"kind", "target", "derived_file_sha256"},
    "physical-crlf": {"kind", "target", "derived_file_sha256"},
    "physical-compact-json": {"kind", "target", "derived_file_sha256"},
    "physical-unsorted-keys": {"kind", "target", "derived_file_sha256"},
    "physical-escaped-unicode": {"kind", "target", "derived_file_sha256"},
    "set-package-json-value": {
        "kind",
        "target",
        "json_pointer",
        "value",
    },
    "reverse-package-array": {
        "kind",
        "target",
        "json_pointer",
        "derived_file_sha256",
    },
    "remove-package-array-item": {
        "kind",
        "target",
        "json_pointer",
        "index",
    },
    "append-package-array-item": {
        "kind",
        "target",
        "json_pointer",
        "value",
    },
    "set-trusted-json-value": {
        "kind",
        "target",
        "json_pointer",
        "value",
    },
    "replace-trusted-dependency-provenance": {
        "kind",
        "target",
        "dependency_name",
        "provenance",
    },
    "multi-five-finding-order": {"kind", "target", "operations"},
}

CONFIRMATORY_CASE_IDS = {
    "stage12e5:valid-confirmatory",
    "stage12e5:order-providers",
    "stage12e5:order-scenario-subset",
    "stage12e5:order-control-subset",
    "stage12e5:order-scheduled-run-ids",
    "stage12e5:order-run-ids",
    "stage12e5:order-repetitions",
    "stage12e5:dependency-provenance-projection",
    "stage12e5:dependency-confirmatory-missing-provenance",
}

CASE_TARGETS = {
    "stage12e5:valid-development": None,
    "stage12e5:valid-confirmatory": None,
    "stage12e5:layout-missing-file": "release-build.json",
    "stage12e5:layout-extra-child": "unexpected.txt",
    "stage12e5:layout-symlink-child": "release-build.json",
    "stage12e5:layout-directory-child": "release-build.json",
    "stage12e5:package-read-failed": "release-build.json",
    "stage12e5:version-artifact-manifest": "artifact-manifest.json",
    "stage12e5:version-release-build": "release-build.json",
    "stage12e5:version-reproducibility-manifest": (
        "reproducibility-manifest.json"
    ),
    "stage12e5:order-artifacts": "artifact-manifest.json",
    "stage12e5:order-rejected-inputs": "artifact-manifest.json",
    "stage12e5:order-providers": "reproducibility-manifest.json",
    "stage12e5:order-limitations": "reproducibility-manifest.json",
    "stage12e5:order-schema-set": "reproducibility-manifest.json",
    "stage12e5:order-governing-documents": "reproducibility-manifest.json",
    "stage12e5:order-dependencies": "release-build.json",
    "stage12e5:order-scenario-subset": "reproducibility-manifest.json",
    "stage12e5:order-control-subset": "reproducibility-manifest.json",
    "stage12e5:order-scheduled-run-ids": "reproducibility-manifest.json",
    "stage12e5:order-run-ids": "reproducibility-manifest.json",
    "stage12e5:order-repetitions": "reproducibility-manifest.json",
    "stage12e5:binding-active-artifact": "artifact-manifest.json",
    "stage12e5:binding-rejected-input": "artifact-manifest.json",
    "stage12e5:binding-build-id": "release-build.json",
    "stage12e5:binding-repro-build-identity": (
        "reproducibility-manifest.json"
    ),
    "stage12e5:binding-environment-reference": "release-build.json",
    "stage12e5:binding-environment-content": "trusted-inputs",
    "stage12e5:binding-source-git": "trusted-inputs",
    "stage12e5:binding-schema-set": "reproducibility-manifest.json",
    "stage12e5:binding-dependency-projection": (
        "reproducibility-manifest.json"
    ),
    "stage12e5:binding-governing-document": (
        "reproducibility-manifest.json"
    ),
    "stage12e5:dependency-name": "reproducibility-manifest.json",
    "stage12e5:dependency-version": "reproducibility-manifest.json",
    "stage12e5:dependency-order": "reproducibility-manifest.json",
    "stage12e5:dependency-provenance-projection": "release-build.json",
    "stage12e5:dependency-confirmatory-missing-provenance": (
        "runtime_dependency_closure"
    ),
    "stage12e5:dependency-development-empty-limitations": (
        "reproducibility-manifest.json"
    ),
    "stage12e5:dependency-development-nonempty-limitations": None,
    "stage12e5:validation-stage12d-artifact-digest": (
        "artifact-manifest.json"
    ),
    "stage12e5:validation-identity5-version": "trusted-inputs",
    "stage12e5:validation-build-schema": "release-build.json",
    "stage12e5:validation-build-consistency": "release-build.json",
    "stage12e5:validation-repro-environment": (
        "reproducibility-manifest.json"
    ),
    "stage12e5:multi-five-finding-order": None,
}
CASE_TARGETS.update(
    {
        case_id: "release-build.json"
        for case_id in CASE_IDS
        if case_id.startswith("stage12e5:json-")
    }
)
CASE_TARGETS.update(
    {
        case_id: "reproducibility-manifest.json"
        for case_id in CASE_IDS
        if case_id.startswith("stage12e5:physical-")
    }
)

RAW_FIXTURES = {
    "raw-tampers/malformed-utf8.raw": bytes.fromhex(
        "7b2278223a22ff227d0a"
    ),
    "raw-tampers/malformed-json.raw": b'{"x":\n',
    "raw-tampers/duplicate-key.raw": b'{"x":1,"x":2}\n',
    "raw-tampers/nan.raw": b'{"x":NaN}\n',
    "raw-tampers/infinity.raw": b'{"x":Infinity}\n',
    "raw-tampers/negative-infinity.raw": b'{"x":-Infinity}\n',
}


class _DuplicateJsonKeyError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _strict_json(raw: bytes) -> Any:
    return json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_constant,
    )


def _strict_object(path: Path) -> dict[str, Any]:
    value = _strict_json(path.read_bytes())
    assert isinstance(value, dict), path
    return value


def _serialize(
    value: Any,
    *,
    ensure_ascii: bool = False,
    sort_keys: bool = True,
) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys,
            indent=2,
            separators=(",", ": "),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _physical_sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _require_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    assert set(value) == expected, (label, set(value), expected)


def _assert_safe_relative(raw: str, root: Path) -> Path:
    assert isinstance(raw, str) and raw
    assert "\\" not in raw and "\x00" not in raw
    assert not raw.startswith("/")
    assert not PureWindowsPath(raw).drive
    parts = raw.split("/")
    assert all(part not in {"", ".", ".."} for part in parts)
    assert PurePosixPath(raw).as_posix() == raw
    result = root.joinpath(*parts)
    assert result.resolve(strict=False).is_relative_to(root.resolve())
    return result


def _assert_path_has_no_symlink(root: Path, relative: str) -> Path:
    path = _assert_safe_relative(relative, root)
    current = root
    for part in relative.split("/"):
        current = current / part
        if current.exists() or current.is_symlink():
            assert not stat.S_ISLNK(current.lstat().st_mode), current
    return path


def _validate_index(index: dict[str, Any]) -> None:
    _require_keys(
        index,
        {
            "corpus_version",
            "required_predecessor",
            "files",
            "schemas",
            "governing_documents",
            "bases",
            "cases",
        },
        "index",
    )
    assert index["corpus_version"] == "0.1.0"
    assert index["required_predecessor"] == {
        "tag": "implementation-stage12e4-v0.1",
        "commit": "fb779d06746041e910c8998d4e26d52d03653b95",
    }

    file_paths: list[str] = []
    for record in index["files"]:
        _require_keys(record, {"path", "sha256"}, "file record")
        assert SHA256_PATTERN.fullmatch(record["sha256"])
        assert record["path"] != "corpus-index.json"
        _assert_safe_relative(record["path"], CORPUS_ROOT)
        file_paths.append(record["path"])
    assert file_paths == sorted(file_paths)
    assert len(file_paths) == len(set(file_paths))

    schema_ids: list[str] = []
    schema_paths: list[str] = []
    for record in index["schemas"]:
        _require_keys(
            record,
            {"path", "schema_id", "physical_sha256", "canonical_sha256"},
            "schema record",
        )
        assert record["path"].startswith("schemas/")
        _assert_safe_relative(record["path"], ROOT)
        assert SHA256_PATTERN.fullmatch(record["physical_sha256"])
        assert SHA256_PATTERN.fullmatch(record["canonical_sha256"])
        schema_ids.append(record["schema_id"])
        schema_paths.append(record["path"])
    assert schema_ids == sorted(schema_ids)
    assert len(schema_ids) == len(set(schema_ids))
    assert len(schema_paths) == len(set(schema_paths))

    governing_ids: list[str] = []
    for record in index["governing_documents"]:
        _require_keys(
            record,
            {"document_id", "path", "physical_sha256", "provenance"},
            "governing record",
        )
        _assert_safe_relative(record["path"], ROOT)
        assert SHA256_PATTERN.fullmatch(record["physical_sha256"])
        _require_keys(
            record["provenance"],
            {
                "document_version",
                "frozen_tag_identity",
                "frozen_tag_object_sha",
                "frozen_tag_target_commit_sha",
                "exact_byte_content_digest",
            },
            "governing provenance",
        )
        assert record["provenance"]["exact_byte_content_digest"] == record[
            "physical_sha256"
        ]
        governing_ids.append(record["document_id"])
    assert governing_ids == [
        value.document_id for value in GOVERNING_DOCUMENT_REGISTRY_V0_1
    ]

    base_ids: list[str] = []
    for record in index["bases"]:
        _require_keys(
            record,
            {
                "base_case_id",
                "phase",
                "package_path",
                "trusted_inputs_path",
                "rejected_input_paths",
            },
            "base record",
        )
        assert record["phase"] in {"DEVELOPMENT", "CONFIRMATORY"}
        _assert_safe_relative(record["package_path"], CORPUS_ROOT)
        _assert_safe_relative(record["trusted_inputs_path"], CORPUS_ROOT)
        rejected_locators: list[str] = []
        for rejected in record["rejected_input_paths"]:
            _require_keys(
                rejected,
                {"locator", "path", "forensic_sha256"},
                "rejected path",
            )
            _assert_safe_relative(rejected["path"], CORPUS_ROOT)
            assert SHA256_PATTERN.fullmatch(rejected["forensic_sha256"])
            rejected_locators.append(rejected["locator"])
        assert rejected_locators == sorted(rejected_locators)
        base_ids.append(record["base_case_id"])
    assert base_ids == sorted(
        {"stage12e5:valid-development", "stage12e5:valid-confirmatory"}
    )

    observed_ids = [record["case_id"] for record in index["cases"]]
    assert observed_ids == list(CASE_IDS)
    assert all(CASE_ID_PATTERN.fullmatch(case_id) for case_id in observed_ids)
    assert len(observed_ids) == len(set(observed_ids)) == 57
    covered_codes: set[str] = set()
    for record in index["cases"]:
        _require_keys(
            record,
            {"case_id", "base_case_id", "mutation", "expected"},
            "case record",
        )
        expected_base = (
            "stage12e5:valid-confirmatory"
            if record["case_id"] in CONFIRMATORY_CASE_IDS
            else "stage12e5:valid-development"
        )
        assert record["base_case_id"] == expected_base
        mutation = record["mutation"]
        assert mutation["kind"] in MUTATION_FIELDS
        _require_keys(
            mutation,
            MUTATION_FIELDS[mutation["kind"]],
            f"mutation {record['case_id']}",
        )
        assert mutation["target"] == CASE_TARGETS[record["case_id"]]
        if mutation["kind"] == "multi-five-finding-order":
            assert len(mutation["operations"]) == 5
            for operation in mutation["operations"]:
                assert operation["kind"] in MUTATION_FIELDS
                _require_keys(
                    operation,
                    MUTATION_FIELDS[operation["kind"]],
                    "multi operation",
                )
        if "fixture_path" in mutation:
            _assert_safe_relative(mutation["fixture_path"], CORPUS_ROOT)
        if "derived_file_sha256" in mutation:
            assert SHA256_PATTERN.fullmatch(mutation["derived_file_sha256"])

        expected = record["expected"]
        _require_keys(
            expected,
            {
                "passed",
                "release_id",
                "release_id_token",
                "findings",
                "reproducibility_manifest_digest",
                "integrity_tag_annotation",
            },
            "expected result",
        )
        for finding in expected["findings"]:
            _require_keys(
                finding,
                {
                    "code",
                    "field_path",
                    "source",
                    "source_code",
                    "source_field_path",
                },
                "expected finding",
            )
            assert finding["code"] in EXPECTED_AUDIT_CODES
            covered_codes.add(finding["code"])
        if expected["passed"]:
            assert expected["findings"] == []
            assert SHA256_PATTERN.fullmatch(
                expected["reproducibility_manifest_digest"]
            )
            assert expected["integrity_tag_annotation"] == (
                "reproducibility-manifest-sha256: "
                + expected["reproducibility_manifest_digest"]
            )
        else:
            assert expected["findings"]
            assert expected["reproducibility_manifest_digest"] is None
            assert expected["integrity_tag_annotation"] is None
    assert covered_codes == EXPECTED_AUDIT_CODES

    multi = next(
        value
        for value in index["cases"]
        if value["case_id"] == "stage12e5:multi-five-finding-order"
    )
    assert [value["code"] for value in multi["expected"]["findings"]] == [
        "AUDIT_PACKAGE_LAYOUT_INVALID",
        "AUDIT_PHYSICAL_SERIALIZATION_INVALID",
        "AUDIT_GENERATED_VERSION_INVALID",
        "AUDIT_DETERMINISTIC_ORDER_INVALID",
        "AUDIT_VALIDATION_FAILED",
    ]


def _load_schema_store(index: dict[str, Any]) -> dict[str, Any]:
    paths: list[Path] = []
    expected_ids: list[str] = []
    for record in index["schemas"]:
        path = _assert_path_has_no_symlink(ROOT, record["path"])
        raw = path.read_bytes()
        assert _physical_sha256(raw) == record["physical_sha256"]
        parsed = _strict_json(raw)
        assert isinstance(parsed, dict)
        assert parsed["$id"] == record["schema_id"]
        assert canonical_sha256(parsed) == record["canonical_sha256"]
        paths.append(path)
        expected_ids.append(record["schema_id"])
    store = load_schema_store(paths)
    assert list(store) == expected_ids
    return store


def _load_governing_documents(
    index: dict[str, Any],
) -> GoverningDocumentAcquisition:
    acquired: list[AcquiredGoverningDocument] = []
    assert len(index["governing_documents"]) == 9
    for registry, record in zip(
        GOVERNING_DOCUMENT_REGISTRY_V0_1,
        index["governing_documents"],
        strict=True,
    ):
        assert record["document_id"] == registry.document_id
        assert record["path"] == registry.repository_path
        provenance = record["provenance"]
        assert provenance["document_version"] == registry.document_version
        assert provenance["frozen_tag_identity"] == registry.frozen_tag_identity
        path = _assert_path_has_no_symlink(ROOT, record["path"])
        raw = path.read_bytes()
        assert _physical_sha256(raw) == record["physical_sha256"]
        assert forensic_sha256_bytes(raw) == provenance[
            "exact_byte_content_digest"
        ]
        assert re.fullmatch(
            r"[0-9a-f]{40}|[0-9a-f]{64}", provenance["frozen_tag_object_sha"]
        )
        assert re.fullmatch(
            r"[0-9a-f]{40}|[0-9a-f]{64}",
            provenance["frozen_tag_target_commit_sha"],
        )
        acquired.append(
            AcquiredGoverningDocument(
                exact_bytes=raw,
                provenance=GoverningDocumentProvenance(
                    document_id=registry.document_id,
                    document_version=provenance["document_version"],
                    frozen_tag_identity=provenance["frozen_tag_identity"],
                    frozen_tag_object_sha=provenance["frozen_tag_object_sha"],
                    frozen_tag_target_commit_sha=provenance[
                        "frozen_tag_target_commit_sha"
                    ],
                    exact_byte_content_digest=provenance[
                        "exact_byte_content_digest"
                    ],
                ),
            )
        )
    return GoverningDocumentAcquisition(tuple(acquired))


TRUSTED_KEYS = {
    "release_profile",
    "artifact_documents_by_locator",
    "artifact_expectations_by_locator",
    "artifact_metadata_by_locator",
    "rejected_input_metadata_by_locator",
    "git_provenance",
    "runtime_dependency_closure",
    "runtime_environment_facts",
    "environment_artifact",
    "phase_projection",
    "provider_records",
    "reproducibility_limitations",
    "build_mode",
}


def _field_names(value: type[Any]) -> set[str]:
    return {field.name for field in fields(value)}


def _validate_bundle(
    bundle: dict[str, Any], base_record: dict[str, Any]
) -> None:
    _require_keys(bundle, TRUSTED_KEYS, "trusted bundle")
    _require_keys(
        bundle["git_provenance"], _field_names(GitProvenance), "GitProvenance"
    )
    _require_keys(
        bundle["runtime_environment_facts"],
        _field_names(RuntimeEnvironmentFacts),
        "RuntimeEnvironmentFacts",
    )
    closure = bundle["runtime_dependency_closure"]
    _require_keys(
        closure,
        {"dependency_scope", "dependencies", "findings"},
        "RuntimeDependencyClosure",
    )
    assert closure["findings"] == []
    for dependency in closure["dependencies"]:
        _require_keys(
            dependency,
            {
                "name",
                "version",
                "requires_dist",
                "provides_extra",
                "distribution_provenance",
            },
            "ResolvedDependency",
        )
        if dependency["distribution_provenance"] is not None:
            _require_keys(
                dependency["distribution_provenance"],
                _field_names(DistributionArtifactProvenance),
                "DistributionArtifactProvenance",
            )
    for metadata in bundle["artifact_metadata_by_locator"].values():
        _require_keys(
            metadata, _field_names(ArtifactAssemblyMetadata), "artifact metadata"
        )
    for metadata in bundle["rejected_input_metadata_by_locator"].values():
        _require_keys(
            metadata,
            _field_names(RejectedInputAssemblyMetadata),
            "rejected metadata",
        )
    phase = bundle["phase_projection"]
    _require_keys(phase, _field_names(PhaseProjection), "PhaseProjection")
    for repetition in phase["repetition_identities"]:
        _require_keys(
            repetition, _field_names(RepetitionIdentity), "RepetitionIdentity"
        )
    for provider in bundle["provider_records"]:
        _require_keys(
            provider,
            {
                "agent_condition_id",
                "model_identifier",
                "provider_runtime_identity",
                "version_status",
                "model_version",
            },
            "provider record",
        )
        _require_keys(
            provider["provider_runtime_identity"],
            {"identity_status", "runtime_identifier"},
            "provider runtime identity",
        )

    documents = bundle["artifact_documents_by_locator"]
    expectations = bundle["artifact_expectations_by_locator"]
    metadata = bundle["artifact_metadata_by_locator"]
    selections = bundle["release_profile"]["active_artifacts"]
    selected_locators = {value["locator"] for value in selections}
    assert set(documents) == set(expectations) == set(metadata) == selected_locators
    family_by_locator = {
        value["locator"]: value["artifact_family"] for value in selections
    }
    for locator, document in documents.items():
        expected = expectations[locator]
        _require_keys(
            expected,
            {
                "artifact_family",
                "artifact_id",
                "artifact_version",
                "schema_id",
                "canonical_sha256",
            },
            "artifact expectation",
        )
        family = family_by_locator[locator]
        family_spec = get_artifact_family_spec(family)
        version = document[family_spec.version_field]
        contract = get_artifact_family_contract_spec(family, version)
        assert expected == {
            "artifact_family": family,
            "artifact_id": document[contract.identity_field],
            "artifact_version": version,
            "schema_id": contract.schema_id,
            "canonical_sha256": canonical_sha256(document),
        }

    rejected_records = base_record["rejected_input_paths"]
    rejected_locators = {value["locator"] for value in rejected_records}
    assert rejected_locators == {
        value["locator"] for value in bundle["release_profile"]["rejected_inputs"]
    }
    assert rejected_locators == set(bundle["rejected_input_metadata_by_locator"])


def _inputs_from_bundle(
    bundle: dict[str, Any],
    schema_store: dict[str, Any],
    governing_documents: GoverningDocumentAcquisition,
    rejected_bytes: dict[str, bytes],
) -> dict[str, Any]:
    dependencies: list[ResolvedDependency] = []
    for value in bundle["runtime_dependency_closure"]["dependencies"]:
        raw_provenance = value["distribution_provenance"]
        provenance = (
            None
            if raw_provenance is None
            else DistributionArtifactProvenance(**raw_provenance)
        )
        dependencies.append(
            ResolvedDependency(
                name=value["name"],
                version=value["version"],
                requires_dist=tuple(value["requires_dist"]),
                provides_extra=tuple(value["provides_extra"]),
                distribution_provenance=provenance,
            )
        )
    raw_phase = bundle["phase_projection"]
    return {
        "release_profile": deepcopy(bundle["release_profile"]),
        "artifact_documents_by_locator": deepcopy(
            bundle["artifact_documents_by_locator"]
        ),
        "artifact_metadata_by_locator": {
            key: ArtifactAssemblyMetadata(**value)
            for key, value in bundle["artifact_metadata_by_locator"].items()
        },
        "rejected_bytes_by_locator": dict(rejected_bytes),
        "rejected_input_metadata_by_locator": {
            key: RejectedInputAssemblyMetadata(**value)
            for key, value in bundle[
                "rejected_input_metadata_by_locator"
            ].items()
        },
        "schema_store": schema_store,
        "git_provenance": GitProvenance(**bundle["git_provenance"]),
        "governing_documents": governing_documents,
        "runtime_dependency_closure": RuntimeDependencyClosure(
            dependencies=tuple(dependencies),
            findings=(),
            dependency_scope=bundle["runtime_dependency_closure"][
                "dependency_scope"
            ],
        ),
        "runtime_environment_facts": RuntimeEnvironmentFacts(
            **bundle["runtime_environment_facts"]
        ),
        "environment_artifact": deepcopy(bundle["environment_artifact"]),
        "phase_projection": PhaseProjection(
            scenario_subset=tuple(raw_phase["scenario_subset"]),
            control_subset=tuple(raw_phase["control_subset"]),
            instrument_configuration_id=raw_phase[
                "instrument_configuration_id"
            ],
            instrument_acceptance_reference=raw_phase[
                "instrument_acceptance_reference"
            ],
            capability_evaluation_reference=raw_phase[
                "capability_evaluation_reference"
            ],
            analysis_configuration_id=raw_phase["analysis_configuration_id"],
            campaign_id=raw_phase["campaign_id"],
            scheduled_run_ids=tuple(raw_phase["scheduled_run_ids"]),
            run_ids=tuple(raw_phase["run_ids"]),
            repetition_identities=tuple(
                RepetitionIdentity(**value)
                for value in raw_phase["repetition_identities"]
            ),
        ),
        "provider_records": tuple(deepcopy(bundle["provider_records"])),
        "reproducibility_limitations": tuple(
            bundle["reproducibility_limitations"]
        ),
        "build_mode": bundle["build_mode"],
    }


@dataclass(slots=True)
class _Base:
    record: dict[str, Any]
    package_path: Path
    bundle: dict[str, Any]
    rejected_bytes: dict[str, bytes]


@dataclass(slots=True)
class _Context:
    index: dict[str, Any]
    schema_store: dict[str, Any]
    governing_documents: GoverningDocumentAcquisition
    bases: dict[str, _Base]


def _load_context() -> _Context:
    raw_index = INDEX_PATH.read_bytes()
    index = _strict_json(raw_index)
    assert isinstance(index, dict)
    assert raw_index == _serialize(index)
    _validate_index(index)
    schema_store = _load_schema_store(index)
    governing_documents = _load_governing_documents(index)
    bases: dict[str, _Base] = {}
    for record in index["bases"]:
        package_path = _assert_path_has_no_symlink(
            CORPUS_ROOT, record["package_path"]
        )
        bundle_path = _assert_path_has_no_symlink(
            CORPUS_ROOT, record["trusted_inputs_path"]
        )
        raw_bundle = bundle_path.read_bytes()
        bundle = _strict_json(raw_bundle)
        assert isinstance(bundle, dict)
        assert raw_bundle == _serialize(bundle)
        _validate_bundle(bundle, record)
        rejected: dict[str, bytes] = {}
        for item in record["rejected_input_paths"]:
            path = _assert_path_has_no_symlink(CORPUS_ROOT, item["path"])
            raw = path.read_bytes()
            assert forensic_sha256_bytes(raw) == item["forensic_sha256"]
            rejected[item["locator"]] = raw
        bases[record["base_case_id"]] = _Base(
            record=record,
            package_path=package_path,
            bundle=bundle,
            rejected_bytes=rejected,
        )
    return _Context(index, schema_store, governing_documents, bases)


@pytest.fixture(scope="module")
def context() -> _Context:
    return _load_context()


def _pointer_parent(value: Any, pointer: str) -> tuple[Any, str]:
    assert pointer.startswith("/")
    parts = [
        part.replace("~1", "/").replace("~0", "~")
        for part in pointer.split("/")[1:]
    ]
    parent = value
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    return parent, parts[-1]


def _get_pointer(value: Any, pointer: str) -> Any:
    parent, key = _pointer_parent(value, pointer)
    return parent[int(key)] if isinstance(parent, list) else parent[key]


def _set_pointer(value: Any, pointer: str, replacement: Any) -> None:
    parent, key = _pointer_parent(value, pointer)
    if isinstance(parent, list):
        parent[int(key)] = deepcopy(replacement)
    else:
        parent[key] = deepcopy(replacement)


def _apply_operation(
    operation: dict[str, Any],
    directory: Path,
    bundle: dict[str, Any],
) -> None:
    kind = operation["kind"]
    target = operation["target"]
    path = None if target is None else directory / target
    if kind in {"none", "inject-read-failure"}:
        return
    if kind == "remove-package-child":
        assert path is not None
        path.unlink()
        return
    if kind == "add-package-child":
        assert path is not None
        path.write_bytes(operation["content_utf8"].encode("utf-8"))
        return
    if kind == "symlink-package-child":
        assert path is not None
        path.unlink()
        outside = directory.parent / "outside-release-build.json"
        outside.write_bytes(b"outside")
        path.symlink_to(operation["link_target"])
        return
    if kind == "directory-package-child":
        assert path is not None
        path.unlink()
        path.mkdir()
        return
    if kind == "replace-package-bytes":
        assert path is not None
        fixture = _assert_path_has_no_symlink(
            CORPUS_ROOT, operation["fixture_path"]
        )
        path.write_bytes(fixture.read_bytes())
        return
    if kind.startswith("physical-"):
        assert path is not None
        raw = path.read_bytes()
        parsed = _strict_json(raw)
        if kind == "physical-no-terminal-lf":
            changed = raw[:-1]
        elif kind == "physical-double-terminal-lf":
            changed = raw + b"\n"
        elif kind == "physical-crlf":
            changed = raw.replace(b"\n", b"\r\n")
        elif kind == "physical-compact-json":
            changed = (
                json.dumps(
                    parsed,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
                + b"\n"
            )
        elif kind == "physical-unsorted-keys":
            assert isinstance(parsed, dict)
            changed = _serialize(
                {key: parsed[key] for key in sorted(parsed, reverse=True)},
                sort_keys=False,
            )
        elif kind == "physical-escaped-unicode":
            changed = _serialize(parsed, ensure_ascii=True)
        else:
            raise AssertionError(f"unknown physical mutation: {kind}")
        assert changed != raw
        assert _strict_json(changed) == parsed
        assert _physical_sha256(changed) == operation["derived_file_sha256"]
        path.write_bytes(changed)
        return
    if kind in {
        "set-package-json-value",
        "reverse-package-array",
        "remove-package-array-item",
        "append-package-array-item",
    }:
        assert path is not None
        parsed = _strict_json(path.read_bytes())
        pointer = operation["json_pointer"]
        if kind == "set-package-json-value":
            _set_pointer(parsed, pointer, operation["value"])
        else:
            array = _get_pointer(parsed, pointer)
            assert isinstance(array, list)
            if kind == "reverse-package-array":
                original = deepcopy(array)
                array.reverse()
                assert len(original) == len(array) >= 2
                assert original != array
                assert sorted(canonicalize_json(item) for item in original) == sorted(
                    canonicalize_json(item) for item in array
                )
            elif kind == "remove-package-array-item":
                array.pop(operation["index"])
            else:
                array.append(deepcopy(operation["value"]))
        changed = _serialize(parsed)
        if kind == "reverse-package-array":
            assert _physical_sha256(changed) == operation[
                "derived_file_sha256"
            ]
        path.write_bytes(changed)
        return
    if kind == "set-trusted-json-value":
        _set_pointer(bundle, operation["json_pointer"], operation["value"])
        return
    if kind == "replace-trusted-dependency-provenance":
        dependency = next(
            value
            for value in bundle["runtime_dependency_closure"]["dependencies"]
            if value["name"] == operation["dependency_name"]
        )
        dependency["distribution_provenance"] = deepcopy(operation["provenance"])
        return
    raise AssertionError(f"unknown mutation kind: {kind}")


def _snapshot_package(directory: Path) -> tuple[Any, ...]:
    result: list[Any] = []
    for path in sorted(directory.iterdir(), key=lambda value: value.name):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            payload = ("symlink", path.readlink().as_posix())
        elif stat.S_ISREG(mode):
            payload = ("file", path.read_bytes())
        elif stat.S_ISDIR(mode):
            payload = (
                "directory",
                tuple(sorted(value.name for value in path.iterdir())),
            )
        else:
            payload = ("other", mode)
        result.append((path.name, stat.S_IFMT(mode), payload))
    return tuple(result)


def _snapshot_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return (
            type(value).__name__,
            tuple(
                (field.name, _snapshot_value(getattr(value, field.name)))
                for field in fields(value)
            ),
        )
    if isinstance(value, Mapping):
        return (
            "mapping",
            tuple((key, _snapshot_value(item)) for key, item in value.items()),
        )
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(_snapshot_value(item) for item in value))
    if isinstance(value, bytes):
        return ("bytes", value.hex())
    return (type(value).__name__, value)


def _audit_arguments(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        key: inputs[key]
        for key in (
            "release_profile",
            "artifact_documents_by_locator",
            "rejected_bytes_by_locator",
            "schema_store",
            "git_provenance",
            "governing_documents",
            "runtime_dependency_closure",
            "runtime_environment_facts",
            "environment_artifact",
        )
    }


def _project_result(result: Any) -> dict[str, Any]:
    return {
        "passed": result.passed,
        "release_id": result.release_id,
        "release_id_token": result.release_id_token,
        "findings": [
            {
                "code": finding.code.value,
                "field_path": finding.field_path,
                "source": finding.source,
                "source_code": finding.source_code,
                "source_field_path": finding.source_field_path,
            }
            for finding in result.findings
        ],
        "reproducibility_manifest_digest": (
            result.reproducibility_manifest_digest
        ),
        "integrity_tag_annotation": result.integrity_tag_annotation,
    }


def _audit_once(
    directory: Path,
    inputs: dict[str, Any],
    mutation: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    if mutation["kind"] != "inject-read-failure":
        return audit_research_release_integrity(
            directory, **_audit_arguments(inputs)
        )
    original = audit_module._read_exact_bytes

    def fail(path: Path) -> bytes:
        if path.name == mutation["target"]:
            raise OSError("synthetic exact-byte read failure")
        return original(path)

    with monkeypatch.context() as scoped:
        scoped.setattr(audit_module, "_read_exact_bytes", fail)
        return audit_research_release_integrity(
            directory, **_audit_arguments(inputs)
        )


def test_corpus_index_is_closed_and_physically_deterministic() -> None:
    raw = INDEX_PATH.read_bytes()
    index = _strict_json(raw)
    assert isinstance(index, dict)
    assert raw == _serialize(index)
    _validate_index(index)


def test_corpus_file_registry_is_complete_and_exact(
    context: _Context,
) -> None:
    for root, directories, files in os.walk(CORPUS_ROOT, followlinks=False):
        for name in [*directories, *files]:
            assert not (Path(root) / name).is_symlink()
    actual = sorted(
        path.relative_to(CORPUS_ROOT).as_posix()
        for path in CORPUS_ROOT.rglob("*")
        if path.is_file() and path != INDEX_PATH
    )
    indexed = [value["path"] for value in context.index["files"]]
    assert actual == indexed
    assert "corpus-index.json" not in indexed
    for record in context.index["files"]:
        path = _assert_path_has_no_symlink(CORPUS_ROOT, record["path"])
        assert _physical_sha256(path.read_bytes()) == record["sha256"]


def test_explicit_schema_registry_is_exact(context: _Context) -> None:
    assert len(context.index["schemas"]) == 26
    assert list(context.schema_store) == [
        value["schema_id"] for value in context.index["schemas"]
    ]


def test_governing_document_registry_is_exact(context: _Context) -> None:
    assert len(context.governing_documents.documents) == 9
    assert [
        value.provenance.document_id
        for value in context.governing_documents.documents
    ] == [value.document_id for value in GOVERNING_DOCUMENT_REGISTRY_V0_1]


@pytest.mark.parametrize(
    "base_case_id",
    ("stage12e5:valid-development", "stage12e5:valid-confirmatory"),
)
def test_trusted_bundle_is_closed_and_independent(
    context: _Context, base_case_id: str
) -> None:
    base = context.bases[base_case_id]
    _validate_bundle(base.bundle, base.record)
    assert set(path.name for path in base.package_path.iterdir()) == set(
        PACKAGE_FILES
    )
    assert not any(
        key in base.bundle
        for key in (
            "artifact_manifest",
            "release_build",
            "reproducibility_manifest",
        )
    )
    if base_case_id.endswith("development"):
        dependencies = base.bundle["runtime_dependency_closure"]["dependencies"]
        assert [value["name"] for value in dependencies] == ["a-pkg", "a_pkg"]
        assert all(value["distribution_provenance"] is None for value in dependencies)
        assert base.bundle["reproducibility_limitations"]
    else:
        assert base.bundle["runtime_environment_facts"]["environment_mode"] == (
            "CONTROLLED_RUNTIME"
        )
        assert all(
            value["distribution_provenance"] is not None
            for value in base.bundle["runtime_dependency_closure"]["dependencies"]
        )


def test_strict_json_raw_fixtures_are_exact(context: _Context) -> None:
    indexed = {value["path"]: value["sha256"] for value in context.index["files"]}
    for relative, expected in RAW_FIXTURES.items():
        path = CORPUS_ROOT / relative
        raw = path.read_bytes()
        assert raw == expected
        assert _physical_sha256(raw) == indexed[relative]
    with pytest.raises(UnicodeDecodeError):
        (CORPUS_ROOT / "raw-tampers/malformed-utf8.raw").read_bytes().decode(
            "utf-8"
        )


@pytest.mark.parametrize(
    "base_case_id",
    ("stage12e5:valid-development", "stage12e5:valid-confirmatory"),
)
def test_real_stage12e3_regeneration_is_byte_exact(
    context: _Context, base_case_id: str, tmp_path: Path
) -> None:
    base = context.bases[base_case_id]
    bundle = deepcopy(base.bundle)
    inputs = _inputs_from_bundle(
        bundle,
        context.schema_store,
        context.governing_documents,
        base.rejected_bytes,
    )
    before = _snapshot_value(inputs)
    built = build_research_release(**inputs)
    directory = write_research_release(built, output_root=tmp_path)
    assert tuple(sorted(value.name for value in directory.iterdir())) == tuple(
        sorted(PACKAGE_FILES)
    )
    for name in PACKAGE_FILES:
        assert (directory / name).read_bytes() == (base.package_path / name).read_bytes()
        assert _physical_sha256((directory / name).read_bytes()) == _physical_sha256(
            (base.package_path / name).read_bytes()
        )
    assert _snapshot_value(inputs) == before


@pytest.mark.parametrize("case_id", CASE_IDS, ids=CASE_IDS)
def test_fixed_corpus_case(
    context: _Context,
    case_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = next(
        value for value in context.index["cases"] if value["case_id"] == case_id
    )
    base = context.bases[record["base_case_id"]]
    directory = tmp_path / "package"
    shutil.copytree(base.package_path, directory)
    bundle = deepcopy(base.bundle)
    mutation = record["mutation"]

    if mutation["kind"] == "reverse-package-array":
        pristine_inputs = _inputs_from_bundle(
            deepcopy(bundle),
            context.schema_store,
            context.governing_documents,
            base.rejected_bytes,
        )
        assert audit_research_release_integrity(
            directory, **_audit_arguments(pristine_inputs)
        ).passed

    operations = (
        mutation["operations"]
        if mutation["kind"] == "multi-five-finding-order"
        else [mutation]
    )
    for operation in operations:
        _apply_operation(operation, directory, bundle)

    inputs = _inputs_from_bundle(
        bundle,
        context.schema_store,
        context.governing_documents,
        base.rejected_bytes,
    )
    before_package = _snapshot_package(directory)
    before_inputs = (
        _snapshot_value(inputs)
        if case_id
        in {"stage12e5:valid-development", "stage12e5:valid-confirmatory"}
        else None
    )
    first = _audit_once(directory, inputs, mutation, monkeypatch)
    second = _audit_once(directory, inputs, mutation, monkeypatch)
    assert first == second
    assert _project_result(first) == record["expected"]
    assert _snapshot_package(directory) == before_package
    if before_inputs is not None:
        assert _snapshot_value(inputs) == before_inputs

    if first.passed:
        parsed = _strict_object(directory / "reproducibility-manifest.json")
        independent_digest = canonical_sha256(parsed)
        assert independent_digest == record["expected"][
            "reproducibility_manifest_digest"
        ]
        assert first.reproducibility_manifest_digest == independent_digest
        assert first.integrity_tag_annotation == (
            "reproducibility-manifest-sha256: " + independent_digest
        )
    else:
        assert first.reproducibility_manifest_digest is None
        assert first.integrity_tag_annotation is None


def test_taxonomy_and_indexed_coverage_are_exact(context: _Context) -> None:
    assert {value.value for value in ReleaseIntegrityAuditErrorCode} == (
        EXPECTED_AUDIT_CODES
    )
    covered = {
        finding["code"]
        for case in context.index["cases"]
        for finding in case["expected"]["findings"]
    }
    assert covered == EXPECTED_AUDIT_CODES
