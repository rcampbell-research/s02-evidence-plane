from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, dataclass, fields, replace
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

import frontier_agent_containment.release_integrity_audit as audit_module
from frontier_agent_containment.integrity import (
    canonical_sha256,
    canonicalize_json,
    forensic_sha256_bytes,
)
from frontier_agent_containment.manifest_validation import (
    validate_reproducibility_manifest as real_validate_reproducibility_manifest,
)
from frontier_agent_containment.release_acquisition import (
    DistributionArtifactProvenance,
    ResolvedDependency,
    RuntimeDependencyClosure,
)
from frontier_agent_containment.release_assembly import (
    RejectedInputAssemblyMetadata,
    build_research_release,
    write_research_release,
)
from frontier_agent_containment.release_integrity_audit import (
    ReleaseIntegrityAuditError,
    ReleaseIntegrityAuditErrorCode,
    ReleaseIntegrityAuditFinding,
    ReleaseIntegrityAuditResult,
    assert_research_release_integrity,
    audit_research_release_integrity,
)
from frontier_agent_containment.schema_validation import load_schema_store
from tests.reproducibility import test_stage12e3_release_assembly as stage12e3


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
FILES = (
    "artifact-manifest.json",
    "release-build.json",
    "reproducibility-manifest.json",
)
AUDIT_ARGUMENTS = (
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
ZERO_DIGEST = "sha256:" + "0" * 64


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(sorted(SCHEMAS.glob("*.json")))


@dataclass
class AuditCase:
    directory: Path
    inputs: dict[str, Any]

    @property
    def kwargs(self) -> dict[str, Any]:
        return {name: self.inputs[name] for name in AUDIT_ARGUMENTS}


def _case(
    tmp_path: Path,
    schema_store: dict[str, Any],
    **overrides: Any,
) -> AuditCase:
    inputs = stage12e3.build_inputs(schema_store, **overrides)
    built = build_research_release(**inputs)
    directory = write_research_release(built, output_root=tmp_path)
    return AuditCase(directory, inputs)


def _rejected_case(tmp_path: Path, schema_store: dict[str, Any]) -> AuditCase:
    raw = b'{"a":1,"a":2}'
    return _case(
        tmp_path,
        schema_store,
        release_profile=stage12e3.profile(rejected=True),
        rejected_bytes_by_locator={"rejected/duplicate-key.raw": raw},
        rejected_input_metadata_by_locator={
            "rejected/duplicate-key.raw": RejectedInputAssemblyMetadata(
                "duplicate_json_key",
                "Repeated object name.",
                "DEVELOPMENT",
            )
        },
    )


def _audit(
    case: AuditCase,
    *,
    directory: Path | None = None,
    **overrides: Any,
) -> ReleaseIntegrityAuditResult:
    kwargs = case.kwargs
    kwargs.update(overrides)
    return audit_research_release_integrity(
        case.directory if directory is None else directory,
        **kwargs,
    )


def _load(case: AuditCase, filename: str) -> dict[str, Any]:
    return json.loads((case.directory / filename).read_bytes())


def _serialize(value: Any, *, ensure_ascii: bool = False) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=ensure_ascii,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _persist(case: AuditCase, filename: str, value: Any) -> None:
    (case.directory / filename).write_bytes(_serialize(value))


def _codes(result: ReleaseIntegrityAuditResult) -> tuple[ReleaseIntegrityAuditErrorCode, ...]:
    return tuple(finding.code for finding in result.findings)


def _assert_failed(result: ReleaseIntegrityAuditResult) -> None:
    assert result.passed is False
    assert result.findings
    assert result.reproducibility_manifest_digest is None
    assert result.integrity_tag_annotation is None


def _assert_code(
    result: ReleaseIntegrityAuditResult,
    code: ReleaseIntegrityAuditErrorCode,
    path: str | None = None,
) -> ReleaseIntegrityAuditFinding:
    _assert_failed(result)
    matches = [
        finding
        for finding in result.findings
        if finding.code is code
        and (path is None or finding.field_path == path)
    ]
    assert matches
    return matches[0]


def _distribution(name: str, index: int = 1) -> DistributionArtifactProvenance:
    raw = f"distribution-{name}-{index}".encode()
    return DistributionArtifactProvenance(
        distribution_filename=f"{name}-1.0-py3-none-any.whl",
        distribution_digest=forensic_sha256_bytes(raw),
        source="synthetic test fixture",
    )


def _closure(
    names: tuple[str, ...] = ("rfc8785",),
    *,
    provenance: bool = True,
) -> RuntimeDependencyClosure:
    return RuntimeDependencyClosure(
        dependencies=tuple(
            ResolvedDependency(
                name=name,
                version=f"1.0.{index}",
                requires_dist=(),
                provides_extra=(),
                distribution_provenance=(
                    _distribution(name, index) if provenance else None
                ),
            )
            for index, name in enumerate(names, start=1)
        ),
        findings=(),
    )


def _provider(agent: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "agent_condition_id": agent["agent_condition_id"],
        "model_identifier": agent["model_identifier"],
        "provider_runtime_identity": {
            "identity_status": "REPORTED",
            "runtime_identifier": agent["provider_runtime_identity"]["runtime_id"],
        },
        "version_status": "REPORTED",
        "model_version": agent["model_version"],
    }


def _active_document(inputs: Mapping[str, Any], family: str) -> dict[str, Any]:
    selection = next(
        item
        for item in inputs["release_profile"]["active_artifacts"]
        if item["artifact_family"] == family
    )
    return inputs["artifact_documents_by_locator"][selection["locator"]]


def _add_active_document(
    inputs: dict[str, Any],
    *,
    family: str,
    artifact_id: str,
    locator: str,
    document: dict[str, Any],
) -> None:
    inputs["artifact_documents_by_locator"][locator] = document
    inputs["artifact_metadata_by_locator"][locator] = (
        stage12e3.ArtifactAssemblyMetadata("FROZEN", "CONFIRMATORY")
    )
    inputs["release_profile"]["active_artifacts"].append(
        {
            "artifact_family": family,
            "artifact_id": artifact_id,
            "locator": locator,
        }
    )


def _multi_value_order_case(
    tmp_path: Path,
    schema_store: dict[str, Any],
    field: str,
) -> AuditCase:
    phase = "PILOT" if field == "scenario_subset" else "CONFIRMATORY"
    inputs = stage12e3.research_phase_inputs(schema_store, phase)
    campaign = _active_document(inputs, "campaign")

    if field == "scenario_subset":
        second_scenario = deepcopy(_active_document(inputs, "scenario"))
        second_scenario["scenario_id"] = "scenario:protected-access-secondary"
        _add_active_document(
            inputs,
            family="scenario",
            artifact_id=second_scenario["scenario_id"],
            locator="scientific/scenario-secondary.json",
            document=second_scenario,
        )
        campaign["scenario_ids"] = sorted(
            [*campaign["scenario_ids"], second_scenario["scenario_id"]]
        )
        inputs["phase_projection"] = replace(
            inputs["phase_projection"],
            scenario_subset=tuple(campaign["scenario_ids"]),
        )
    elif field == "model_provider_identities":
        first_agent = _active_document(inputs, "agent_model_condition")
        second_agent = deepcopy(first_agent)
        second_agent["agent_condition_id"] = "agentcond:secondary"
        second_agent["model_condition_id"] = "modelcond:secondary"
        second_agent["capability_condition_id"] = "capcond:secondary"
        second_agent["display_name"] = "Synthetic secondary subject"
        _add_active_document(
            inputs,
            family="agent_model_condition",
            artifact_id=second_agent["agent_condition_id"],
            locator="scientific/agent-model-condition-secondary.json",
            document=second_agent,
        )
        inputs["provider_records"] = tuple(
            _provider(agent)
            for agent in sorted(
                (first_agent, second_agent),
                key=lambda item: item["agent_condition_id"],
            )
        )
    elif field == "control_subset":
        inputs["phase_projection"] = replace(
            inputs["phase_projection"],
            control_subset=tuple(campaign["control_condition_ids"]),
        )
    elif field == "run_ids":
        scheduled_runs = sorted(
            (
                inputs["artifact_documents_by_locator"][selection["locator"]]
                for selection in inputs["release_profile"]["active_artifacts"]
                if selection["artifact_family"] == "scheduled_run"
            ),
            key=lambda item: item["scheduled_run_id"],
        )
        shared_run_fields = (
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
        run_ids: list[str] = []
        for index, scheduled in enumerate(scheduled_runs, start=1):
            run_id = f"run:unit-{index:03d}"
            run = {
                **{name: deepcopy(scheduled[name]) for name in shared_run_fields},
                "run_id": run_id,
                "run_manifest_version": "0.1.0",
                "s0_acceptance_identity": "s0accept:baseline-v1",
                "scheduled_run_identity": {
                    "schedule_identity": f"unit_{index:03d}",
                    "description": "Predeclared synthetic unit.",
                    "matched_block_identity": f"block_{index:03d}",
                },
                "configuration_frozen_before_start": scheduled[
                    "scheduled_configuration_frozen"
                ],
            }
            _add_active_document(
                inputs,
                family="run_manifest",
                artifact_id=run_id,
                locator=f"scientific/run-manifest-{index:03d}.json",
                document=run,
            )
            run_ids.append(run_id)
        inputs["phase_projection"] = replace(
            inputs["phase_projection"],
            run_ids=tuple(run_ids),
        )

    inputs["release_profile"]["active_artifacts"].sort(
        key=lambda item: (
            item["artifact_family"],
            item["artifact_id"],
            item["locator"],
        )
    )
    built = build_research_release(**inputs)
    directory = write_research_release(built, output_root=tmp_path)
    return AuditCase(directory, inputs)


def _order_insensitive_content(values: list[Any]) -> tuple[bytes, ...]:
    return tuple(sorted(canonicalize_json(value) for value in values))


def _deterministic_snapshot(value: Any) -> Any:
    if isinstance(value, Mapping):
        return (
            "mapping",
            tuple(
                (key, _deterministic_snapshot(item))
                for key, item in value.items()
            ),
        )
    if isinstance(value, list):
        return ("list", tuple(_deterministic_snapshot(item) for item in value))
    if isinstance(value, tuple):
        return ("tuple", tuple(_deterministic_snapshot(item) for item in value))
    return (type(value).__name__, value)


def _set_phase(case: AuditCase, phase: str) -> dict[str, Any]:
    profile = deepcopy(case.inputs["release_profile"])
    token = phase.lower().replace("_", "-") + "-v0.1"
    profile["release_id"] = f"release:{token}"
    profile["release_phase"] = phase
    profile["source_release_tag_identity"] = f"research-release-{token}"
    return profile


def test_public_surface_and_taxonomy_are_exact() -> None:
    assert audit_module.__all__ == [
        "ReleaseIntegrityAuditErrorCode",
        "ReleaseIntegrityAuditFinding",
        "ReleaseIntegrityAuditResult",
        "ReleaseIntegrityAuditError",
        "audit_research_release_integrity",
        "assert_research_release_integrity",
    ]
    assert [item.value for item in ReleaseIntegrityAuditErrorCode] == [
        "AUDIT_PACKAGE_LAYOUT_INVALID",
        "AUDIT_PACKAGE_READ_FAILED",
        "AUDIT_JSON_INVALID",
        "AUDIT_PHYSICAL_SERIALIZATION_INVALID",
        "AUDIT_GENERATED_VERSION_INVALID",
        "AUDIT_DETERMINISTIC_ORDER_INVALID",
        "AUDIT_RELEASE_BINDING_INVALID",
        "AUDIT_DEPENDENCY_PROVENANCE_INCOMPLETE",
        "AUDIT_VALIDATION_FAILED",
    ]


def test_public_records_are_frozen_slotted_and_passed_is_derived() -> None:
    finding = ReleaseIntegrityAuditFinding(
        ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
        "message",
        "/",
    )
    result = ReleaseIntegrityAuditResult(None, None, (finding,), None, None)
    for value in (finding, result):
        assert value.__slots__
        with pytest.raises(FrozenInstanceError):
            setattr(value, fields(value)[0].name, None)
    assert result.passed is False
    assert ReleaseIntegrityAuditResult(None, None, (), None, None).passed is True


def test_valid_release_digest_annotation_and_assert_api(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    parsed = _load(case, "reproducibility-manifest.json")
    expected = canonical_sha256(parsed)
    result = _audit(case)
    assert result == assert_research_release_integrity(case.directory, **case.kwargs)
    assert result.passed
    assert result.findings == ()
    assert result.release_id == "release:development-v0.1"
    assert result.release_id_token == "development-v0.1"
    assert result.reproducibility_manifest_digest == expected
    assert result.integrity_tag_annotation == (
        "reproducibility-manifest-sha256: " + expected
    )
    assert result.integrity_tag_annotation is not None
    assert result.integrity_tag_annotation.count("\n") == 0


@pytest.mark.parametrize("filename", FILES)
def test_missing_required_file_is_layout_failure(
    tmp_path: Path,
    schema_store: dict[str, Any],
    filename: str,
) -> None:
    case = _case(tmp_path, schema_store)
    (case.directory / filename).unlink()
    result = _audit(case)
    _assert_code(
        result,
        ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
        f"/{filename}",
    )
    assert not any(finding.field_path.startswith(f"/{filename}/") for finding in result.findings)


def test_extra_direct_child_is_layout_failure(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    (case.directory / "release-profile.json").write_bytes(b"{}\n")
    result = _audit(case)
    _assert_code(result, ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID, "/")


def test_release_directory_symlink_is_not_followed(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path / "actual", schema_store)
    link = tmp_path / "release-link"
    link.symlink_to(case.directory, target_is_directory=True)
    result = _audit(case, directory=link)
    finding = _assert_code(
        result,
        ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
        "/",
    )
    assert "non-symlink directory under lstat" in finding.message
    assert not any(item.field_path.startswith("/artifact-manifest.json/") for item in result.findings)


@pytest.mark.parametrize("kind", ["symlink", "directory"])
def test_required_child_must_be_ordinary_non_symlink_file(
    tmp_path: Path,
    schema_store: dict[str, Any],
    kind: str,
) -> None:
    case = _case(tmp_path, schema_store)
    target = case.directory / "release-build.json"
    target.unlink()
    if kind == "symlink":
        target.symlink_to(case.directory / "artifact-manifest.json")
    else:
        target.mkdir()
    result = _audit(case)
    finding = _assert_code(
        result,
        ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
        "/release-build.json",
    )
    assert "lstat" in finding.message
    assert not any(f.source == "ReleaseAcquisitionFinding" for f in result.findings)


def test_post_layout_read_failure_has_distinct_code(
    tmp_path: Path,
    schema_store: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, schema_store)
    original = audit_module._read_exact_bytes

    def fail_build(path: Path) -> bytes:
        if path.name == "release-build.json":
            raise PermissionError("synthetic deterministic read denial")
        return original(path)

    monkeypatch.setattr(audit_module, "_read_exact_bytes", fail_build)
    result = _audit(case)
    finding = _assert_code(
        result,
        ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_READ_FAILED,
        "/release-build.json",
    )
    assert "synthetic deterministic read denial" in finding.message
    assert not any(f.source == "ReleaseAcquisitionFinding" for f in result.findings)


@pytest.mark.parametrize(
    "raw",
    [
        b"\xff\n",
        b'{"unterminated":\n',
        b'{"a":1,"a":2}\n',
        b'{"value":NaN}\n',
        b'{"value":Infinity}\n',
        b'{"value":-Infinity}\n',
    ],
    ids=("utf8", "malformed", "duplicate", "nan", "infinity", "negative-infinity"),
)
def test_strict_json_rejects_invalid_inputs(
    tmp_path: Path,
    schema_store: dict[str, Any],
    raw: bytes,
) -> None:
    case = _case(tmp_path, schema_store)
    (case.directory / "release-build.json").write_bytes(raw)
    result = _audit(case)
    _assert_code(
        result,
        ReleaseIntegrityAuditErrorCode.AUDIT_JSON_INVALID,
        "/release-build.json",
    )
    assert not any(f.source == "ReleaseAcquisitionFinding" for f in result.findings)


def test_valid_json_non_object_is_structurally_rejected(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    (case.directory / "artifact-manifest.json").write_bytes(b"[]\n")
    finding = _assert_code(
        _audit(case),
        ReleaseIntegrityAuditErrorCode.AUDIT_VALIDATION_FAILED,
        "/artifact-manifest.json",
    )
    assert finding.source == "ValidationError"


@pytest.mark.parametrize(
    "variant",
    (
        "no-lf",
        "two-lf",
        "crlf",
        "compact",
        "alternate-indent",
        "unsorted-keys",
        "escaped-unicode",
    ),
)
def test_physical_serialization_variants_are_rejected(
    tmp_path: Path,
    schema_store: dict[str, Any],
    variant: str,
) -> None:
    case = _case(tmp_path, schema_store)
    path = case.directory / "artifact-manifest.json"
    raw = path.read_bytes()
    parsed = json.loads(raw)
    if variant == "no-lf":
        changed = raw[:-1]
    elif variant == "two-lf":
        changed = raw + b"\n"
    elif variant == "crlf":
        changed = raw.replace(b"\n", b"\r\n")
    elif variant == "compact":
        changed = json.dumps(parsed, ensure_ascii=False, separators=(",", ":")).encode()
    elif variant == "alternate-indent":
        changed = json.dumps(parsed, ensure_ascii=False, sort_keys=True, indent=4).encode() + b"\n"
    elif variant == "unsorted-keys":
        reversed_object = dict(reversed(tuple(parsed.items())))
        changed = json.dumps(reversed_object, ensure_ascii=False, sort_keys=False, indent=2, separators=(",", ": ")).encode() + b"\n"
    else:
        parsed["release_id"] = "release:dévelopment-v0.1"
        changed = _serialize(parsed, ensure_ascii=True)
    path.write_bytes(changed)
    _assert_code(
        _audit(case),
        ReleaseIntegrityAuditErrorCode.AUDIT_PHYSICAL_SERIALIZATION_INVALID,
        "/artifact-manifest.json",
    )


@pytest.mark.parametrize(
    ("filename", "field"),
    (
        ("artifact-manifest.json", "manifest_version"),
        ("release-build.json", "build_version"),
        ("reproducibility-manifest.json", "reproducibility_version"),
    ),
)
def test_generated_versions_are_fixed(
    tmp_path: Path,
    schema_store: dict[str, Any],
    filename: str,
    field: str,
) -> None:
    case = _case(tmp_path, schema_store)
    value = _load(case, filename)
    value[field] = "7.3.9"
    _persist(case, filename, value)
    _assert_code(
        _audit(case),
        ReleaseIntegrityAuditErrorCode.AUDIT_GENERATED_VERSION_INVALID,
        f"/{filename}/{field}",
    )


def test_artifact_order_is_independently_audited(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    value = _load(case, "artifact-manifest.json")
    value["artifacts"].reverse()
    _persist(case, "artifact-manifest.json", value)
    _assert_code(
        _audit(case),
        ReleaseIntegrityAuditErrorCode.AUDIT_DETERMINISTIC_ORDER_INVALID,
        "/artifact-manifest.json/artifacts",
    )


def test_rejected_input_order_is_independently_audited(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    raw_a = b"a"
    raw_z = b"z"
    release_profile = stage12e3.profile()
    release_profile["rejected_inputs"] = [
        {"rejected_input_id": "rejected:a", "locator": "rejected/a.raw"},
        {"rejected_input_id": "rejected:z", "locator": "rejected/z.raw"},
    ]
    case = _case(
        tmp_path,
        schema_store,
        release_profile=release_profile,
        rejected_bytes_by_locator={
            "rejected/a.raw": raw_a,
            "rejected/z.raw": raw_z,
        },
        rejected_input_metadata_by_locator={
            "rejected/a.raw": RejectedInputAssemblyMetadata("malformed", "A.", "DEVELOPMENT"),
            "rejected/z.raw": RejectedInputAssemblyMetadata("malformed", "Z.", "DEVELOPMENT"),
        },
    )
    value = _load(case, "artifact-manifest.json")
    value["rejected_inputs"].reverse()
    _persist(case, "artifact-manifest.json", value)
    _assert_code(
        _audit(case),
        ReleaseIntegrityAuditErrorCode.AUDIT_DETERMINISTIC_ORDER_INVALID,
        "/artifact-manifest.json/rejected_inputs",
    )


@pytest.mark.parametrize(
    "field",
    (
        "model_provider_identities",
        "reproducibility_limitations",
        "scenario_subset",
        "control_subset",
        "scheduled_run_ids",
        "run_ids",
        "repetition_identities",
    ),
)
def test_reproducibility_array_order_is_independently_audited(
    tmp_path: Path,
    schema_store: dict[str, Any],
    field: str,
) -> None:
    if field == "reproducibility_limitations":
        case = _case(
            tmp_path,
            schema_store,
            reproducibility_limitations=("alpha", "zeta"),
        )
    else:
        case = _multi_value_order_case(tmp_path, schema_store, field)
    assert _audit(case).passed
    value = _load(case, "reproducibility-manifest.json")
    original = deepcopy(value[field])
    tampered = list(reversed(original))
    assert len(original) >= 2
    assert tampered != original
    assert len(tampered) == len(original)
    assert _order_insensitive_content(tampered) == _order_insensitive_content(original)
    value[field] = tampered
    _persist(case, "reproducibility-manifest.json", value)
    result = _audit(case)
    assert [(finding.code, finding.field_path) for finding in result.findings] == [
        (
            ReleaseIntegrityAuditErrorCode.AUDIT_DETERMINISTIC_ORDER_INVALID,
            f"/reproducibility-manifest.json/{field}",
        )
    ]
    _assert_failed(result)


@pytest.mark.parametrize("field", ("schema_set", "governing_documents"))
def test_schema_and_governing_order_are_independently_audited(
    tmp_path: Path,
    schema_store: dict[str, Any],
    field: str,
) -> None:
    case = _case(tmp_path, schema_store)
    value = _load(case, "reproducibility-manifest.json")
    value[field].reverse()
    _persist(case, "reproducibility-manifest.json", value)
    _assert_code(
        _audit(case),
        ReleaseIntegrityAuditErrorCode.AUDIT_DETERMINISTIC_ORDER_INVALID,
        f"/reproducibility-manifest.json/{field}",
    )


@pytest.mark.parametrize("filename", ("release-build.json", "reproducibility-manifest.json"))
def test_dependency_order_uses_exact_name_and_version_strings(
    tmp_path: Path,
    schema_store: dict[str, Any],
    filename: str,
) -> None:
    closure = _closure(("a-pkg", "a_pkg"))
    case = _case(tmp_path, schema_store, runtime_dependency_closure=closure)
    value = _load(case, filename)
    assert [(item["name"], item["version"]) for item in value["dependencies"]] == [
        ("a-pkg", "1.0.1"),
        ("a_pkg", "1.0.2"),
    ]
    value["dependencies"].reverse()
    _persist(case, filename, value)
    _assert_code(
        _audit(case),
        ReleaseIntegrityAuditErrorCode.AUDIT_DETERMINISTIC_ORDER_INVALID,
        f"/{filename}/dependencies",
    )


@pytest.mark.parametrize("mutation", ("missing", "additional"))
def test_active_artifact_whitelist_is_exact(
    tmp_path: Path,
    schema_store: dict[str, Any],
    mutation: str,
) -> None:
    case = _case(tmp_path, schema_store)
    value = _load(case, "artifact-manifest.json")
    if mutation == "missing":
        value["artifacts"].pop()
    else:
        additional = deepcopy(value["artifacts"][-1])
        additional["artifact_id"] = "instrument:unselected"
        additional["locator"] = "scientific/unselected.json"
        value["artifacts"].append(additional)
        value["artifacts"].sort(
            key=lambda item: (
                item["artifact_family"],
                item["artifact_id"],
                item["locator"],
            )
        )
    _persist(case, "artifact-manifest.json", value)
    _assert_code(
        _audit(case),
        ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID,
        "/artifact-manifest.json/artifacts",
    )


@pytest.mark.parametrize("mutation", ("missing", "additional"))
def test_rejected_input_whitelist_is_exact(
    tmp_path: Path,
    schema_store: dict[str, Any],
    mutation: str,
) -> None:
    case = _rejected_case(tmp_path, schema_store)
    value = _load(case, "artifact-manifest.json")
    if mutation == "missing":
        value["rejected_inputs"] = []
    else:
        additional = deepcopy(value["rejected_inputs"][0])
        additional["rejected_input_id"] = "rejected:unselected"
        additional["locator"] = "rejected/unselected.raw"
        additional["forensic_byte_digest"] = forensic_sha256_bytes(b"unselected")
        value["rejected_inputs"].append(additional)
        value["rejected_inputs"].sort(
            key=lambda item: (item["rejected_input_id"], item["locator"])
        )
    _persist(case, "artifact-manifest.json", value)
    _assert_code(
        _audit(case),
        ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID,
        "/artifact-manifest.json/rejected_inputs",
    )


def test_release_build_id_and_repro_build_identity_are_distinct_bound_fields(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    first = _case(tmp_path / "build", schema_store)
    build = _load(first, "release-build.json")
    assert "build_id" in build and "build_identity" not in build
    build["build_id"] = "build:development-v0.2"
    _persist(first, "release-build.json", build)
    _assert_code(
        _audit(first),
        ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID,
        "/release-build.json/build_id",
    )

    second = _case(tmp_path / "repro", schema_store)
    repro = _load(second, "reproducibility-manifest.json")
    repro["environment"]["build_identity"] = "build:development-v0.2"
    _persist(second, "reproducibility-manifest.json", repro)
    _assert_code(
        _audit(second),
        ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID,
        "/reproducibility-manifest.json/environment/build_identity",
    )


def test_build_content_tamper_is_retained_from_repro_validator(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    build = _load(case, "release-build.json")
    build["locale_identity"] = "en_US.UTF-8"
    _persist(case, "release-build.json", build)
    result = _audit(case)
    source = [
        item
        for item in result.findings
        if item.code is ReleaseIntegrityAuditErrorCode.AUDIT_VALIDATION_FAILED
        and item.source_field_path == "/environment"
    ]
    assert source
    assert all(item.source_code and item.source_message for item in source)
    _assert_failed(result)


@pytest.mark.parametrize(
    "source",
    ("profile", "environment", "build", "repro"),
)
def test_environment_identity_binding_is_exact(
    tmp_path: Path,
    schema_store: dict[str, Any],
    source: str,
) -> None:
    case = _case(tmp_path, schema_store)
    overrides: dict[str, Any] = {}
    if source == "profile":
        profile = deepcopy(case.inputs["release_profile"])
        profile["environment_reference"] = "env:other"
        overrides["release_profile"] = profile
    elif source == "environment":
        environment = deepcopy(case.inputs["environment_artifact"])
        environment["environment_id"] = "env:other"
        overrides["environment_artifact"] = environment
    elif source == "build":
        build = _load(case, "release-build.json")
        build["environment_reference"] = "env:other"
        _persist(case, "release-build.json", build)
    else:
        repro = _load(case, "reproducibility-manifest.json")
        repro["environment"]["environment_reference"] = "env:other"
        _persist(case, "reproducibility-manifest.json", repro)
    _assert_code(
        _audit(case, **overrides),
        ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID,
    )


@pytest.mark.parametrize("source", ("governed", "candidate"))
def test_source_git_binding_uses_supplied_provenance(
    tmp_path: Path,
    schema_store: dict[str, Any],
    source: str,
) -> None:
    case = _case(tmp_path, schema_store)
    overrides: dict[str, Any] = {}
    if source == "governed":
        overrides["git_provenance"] = replace(
            case.inputs["git_provenance"],
            repository_tree_sha="4" * 40,
        )
    else:
        repro = _load(case, "reproducibility-manifest.json")
        repro["repository_tree_sha"] = "4" * 40
        _persist(case, "reproducibility-manifest.json", repro)
    result = _audit(case, **overrides)
    finding = _assert_code(
        result,
        ReleaseIntegrityAuditErrorCode.AUDIT_VALIDATION_FAILED,
    )
    assert finding.source == "ManifestFinding"
    assert finding.source_code is not None
    assert finding.source_field_path is not None
    assert finding.source_message is not None


@pytest.mark.parametrize("tamper", ("digest", "identity", "version", "schema"))
def test_stage12d_findings_preserve_source_evidence(
    tmp_path: Path,
    schema_store: dict[str, Any],
    tamper: str,
) -> None:
    case = _case(tmp_path, schema_store)
    manifest = _load(case, "artifact-manifest.json")
    entry = manifest["artifacts"][0]
    if tamper == "digest":
        entry["content_digest"] = ZERO_DIGEST
    elif tamper == "identity":
        entry["artifact_id"] = "env:other"
    elif tamper == "version":
        entry["artifact_version"] = "7.3.9"
    else:
        entry["schema_id"] = (
            "urn:frontier-agent-containment:schema:instrument-configuration:0.1.0"
        )
    _persist(case, "artifact-manifest.json", manifest)
    result = _audit(case)
    retained = [
        finding
        for finding in result.findings
        if finding.code is ReleaseIntegrityAuditErrorCode.AUDIT_VALIDATION_FAILED
        and finding.source == "ManifestFinding"
        and finding.field_path.startswith("/artifact-manifest.json")
    ]
    assert retained
    assert all(
        finding.source_code
        and finding.source_field_path
        and finding.source_message
        for finding in retained
    )
    _assert_failed(result)


def test_identity5_finding_is_retained(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    profile = deepcopy(case.inputs["release_profile"])
    profile["active_artifacts"][0]["expected_artifact_version"] = "7.3.9"
    result = _audit(case, release_profile=profile)
    retained = [
        finding
        for finding in result.findings
        if finding.source == "ReleaseValidationFinding"
    ]
    assert retained
    assert all(
        finding.code is ReleaseIntegrityAuditErrorCode.AUDIT_VALIDATION_FAILED
        and finding.source_code
        and finding.source_field_path
        and finding.source_message
        for finding in retained
    )


def test_build_consistency_uses_real_two_argument_api_and_retains_source(
    tmp_path: Path,
    schema_store: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, schema_store)
    build = _load(case, "release-build.json")
    build["python_version"] = "9.9.9"
    _persist(case, "release-build.json", build)
    observed: list[tuple[Any, ...]] = []
    real = audit_module.validate_release_build_consistency

    def capture(*args: Any, **kwargs: Any) -> Any:
        observed.append(args)
        assert kwargs == {}
        return real(*args, **kwargs)

    monkeypatch.setattr(audit_module, "validate_release_build_consistency", capture)
    result = _audit(case)
    assert len(observed) == 1
    assert len(observed[0]) == 2
    retained = [
        finding
        for finding in result.findings
        if finding.source == "ReleaseAcquisitionFinding"
    ]
    assert retained
    assert all(
        finding.code is ReleaseIntegrityAuditErrorCode.AUDIT_VALIDATION_FAILED
        and finding.source_code
        and finding.source_field_path
        and finding.source_message
        for finding in retained
    )


@pytest.mark.parametrize(
    "mutation",
    ("missing", "extra", "name", "version", "provenance"),
)
def test_dependency_projection_is_exact(
    tmp_path: Path,
    schema_store: dict[str, Any],
    mutation: str,
) -> None:
    closure = _closure(("a-pkg", "a_pkg"))
    case = _case(tmp_path, schema_store, runtime_dependency_closure=closure)
    build = _load(case, "release-build.json")
    repro = _load(case, "reproducibility-manifest.json")
    if mutation == "missing":
        build["dependencies"].pop()
    elif mutation == "extra":
        build["dependencies"].append(deepcopy(build["dependencies"][-1]))
        build["dependencies"][-1]["name"] = "z-extra"
    elif mutation == "name":
        repro["dependencies"][0]["name"] = "a_pkg"
    elif mutation == "version":
        repro["dependencies"][0]["version"] = "9.9.9"
    else:
        build["dependencies"][0]["distribution_digest"] = ZERO_DIGEST
    build["dependencies"].sort(key=lambda item: (item["name"], item["version"]))
    repro["dependencies"].sort(key=lambda item: (item["name"], item["version"]))
    _persist(case, "release-build.json", build)
    _persist(case, "reproducibility-manifest.json", repro)
    _assert_code(
        _audit(case),
        ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID,
    )


@pytest.mark.parametrize("phase", ("PILOT", "CONFIRMATORY", "DEVELOPMENT", "INSTRUMENT_VALIDATION"))
def test_missing_distribution_provenance_phase_policy(
    tmp_path: Path,
    schema_store: dict[str, Any],
    phase: str,
) -> None:
    closure = _closure(provenance=False)
    case = _case(
        tmp_path,
        schema_store,
        runtime_dependency_closure=closure,
        reproducibility_limitations=("Archive unavailable.",),
    )
    repro = _load(case, "reproducibility-manifest.json")
    repro["reproducibility_limitations"] = []
    _persist(case, "reproducibility-manifest.json", repro)
    profile = (
        case.inputs["release_profile"]
        if phase == "DEVELOPMENT"
        else _set_phase(case, phase)
    )
    _assert_code(
        _audit(case, release_profile=profile),
        ReleaseIntegrityAuditErrorCode.AUDIT_DEPENDENCY_PROVENANCE_INCOMPLETE,
        "/release-build.json/dependencies",
    )


@pytest.mark.parametrize("phase", ("DEVELOPMENT", "INSTRUMENT_VALIDATION"))
def test_nonempty_limitation_waives_only_development_phase_provenance(
    tmp_path: Path,
    schema_store: dict[str, Any],
    phase: str,
) -> None:
    closure = _closure(provenance=False)
    case = _case(
        tmp_path,
        schema_store,
        runtime_dependency_closure=closure,
        reproducibility_limitations=("Archive unavailable.",),
    )
    profile = (
        case.inputs["release_profile"]
        if phase == "DEVELOPMENT"
        else _set_phase(case, phase)
    )
    result = _audit(case, release_profile=profile)
    assert (
        ReleaseIntegrityAuditErrorCode.AUDIT_DEPENDENCY_PROVENANCE_INCOMPLETE
        not in _codes(result)
    )


def test_enabled_dependency_extras_gap_does_not_create_a_finding(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    profile = deepcopy(case.inputs["release_profile"])
    profile["enabled_dependency_extras"] = ["synthetic-extra"]
    result = _audit(case, release_profile=profile)
    assert result.passed
    assert result.findings == ()


@pytest.mark.parametrize("mutation", ("missing", "extra"))
def test_schema_set_membership_is_exact(
    tmp_path: Path,
    schema_store: dict[str, Any],
    mutation: str,
) -> None:
    case = _case(tmp_path, schema_store)
    repro = _load(case, "reproducibility-manifest.json")
    if mutation == "missing":
        repro["schema_set"].pop()
    else:
        schema_id = "urn:frontier-agent-containment:schema:common:0.1.0"
        repro["schema_set"].append(
            {
                "schema_id": schema_id,
                "schema_version": "0.1.0",
                "content_digest": canonical_sha256(schema_store[schema_id]),
            }
        )
        repro["schema_set"].sort(key=lambda item: item["schema_id"])
    _persist(case, "reproducibility-manifest.json", repro)
    _assert_code(
        _audit(case),
        ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID,
        "/reproducibility-manifest.json/schema_set",
    )


@pytest.mark.parametrize("mutation", ("missing", "extra", "digest", "provenance"))
def test_governing_document_closure_and_provenance(
    tmp_path: Path,
    schema_store: dict[str, Any],
    mutation: str,
) -> None:
    case = _case(tmp_path, schema_store)
    repro = _load(case, "reproducibility-manifest.json")
    overrides: dict[str, Any] = {}
    if mutation == "missing":
        repro["governing_documents"].pop()
    elif mutation == "extra":
        repro["governing_documents"].append(
            {
                "document_id": "document-unselected",
                "document_version": "0.1.0",
                "frozen_tag_identity": "unselected-v0.1",
                "content_digest": ZERO_DIGEST,
            }
        )
    elif mutation == "digest":
        repro["governing_documents"][0]["content_digest"] = ZERO_DIGEST
    else:
        acquired = case.inputs["governing_documents"]
        changed = list(acquired.documents)
        changed[0] = replace(
            changed[0],
            provenance=replace(
                changed[0].provenance,
                frozen_tag_identity="changed-v0.1",
            ),
        )
        overrides["governing_documents"] = replace(acquired, documents=tuple(changed))
    _persist(case, "reproducibility-manifest.json", repro)
    result = _audit(case, **overrides)
    if mutation in {"missing", "extra"}:
        _assert_code(
            result,
            ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID,
            "/reproducibility-manifest.json/governing_documents",
        )
    else:
        finding = _assert_code(
            result,
            ReleaseIntegrityAuditErrorCode.AUDIT_VALIDATION_FAILED,
        )
        assert finding.source == "ManifestFinding"


def test_trusted_environment_is_independent_and_all_repro_arguments_compose(
    tmp_path: Path,
    schema_store: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, schema_store)
    captured: list[tuple[dict[str, Any], dict[str, Any]]] = []

    def capture(manifest: Any, **kwargs: Any) -> Any:
        captured.append((manifest, kwargs))
        return real_validate_reproducibility_manifest(manifest, **kwargs)

    monkeypatch.setattr(audit_module, "validate_reproducibility_manifest", capture)
    result = _audit(case)
    assert result.passed
    assert len(captured) == 1
    manifest, kwargs = captured[0]
    expected_parameters = tuple(
        inspect.signature(real_validate_reproducibility_manifest).parameters
    )
    assert expected_parameters == (
        "manifest",
        "artifact_manifest",
        "artifact_documents_by_locator",
        "schema_store",
        "active_artifacts",
        "governing_document_bytes_by_id",
        "governing_document_provenance_by_id",
        "repository_provenance",
        "resolved_dependencies",
        "trusted_environment",
        "artifact_manifest_external_locator",
        "rejected_bytes_by_locator",
    )
    assert set(kwargs) == set(expected_parameters[1:])
    build = _load(case, "release-build.json")
    trusted = kwargs["trusted_environment"]
    assert trusted == {
        "python_version": case.inputs["runtime_environment_facts"].python_version,
        "os_runtime_identity": case.inputs["runtime_environment_facts"].os_runtime_identity,
        "architecture": case.inputs["runtime_environment_facts"].architecture,
        "environment_reference": case.inputs["environment_artifact"]["environment_id"],
        "build_identity": build["build_id"],
        "environment_content_digest": canonical_sha256(
            case.inputs["environment_artifact"]
        ),
        "build_content_digest": canonical_sha256(build),
    }
    assert "container_image_identity" not in trusted
    assert manifest is not trusted


def test_environment_digest_is_not_self_trusted_from_candidate(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    environment = deepcopy(case.inputs["environment_artifact"])
    environment["description"] = "Governed environment content changed."
    result = _audit(case, environment_artifact=environment)
    retained = [
        finding
        for finding in result.findings
        if finding.source_field_path == "/environment"
    ]
    assert retained
    _assert_failed(result)


def test_build_identity_and_digest_are_derived_from_parsed_build(
    tmp_path: Path,
    schema_store: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, schema_store)
    build = _load(case, "release-build.json")
    build["build_id"] = "build:development-v0.2"
    _persist(case, "release-build.json", build)
    repro = _load(case, "reproducibility-manifest.json")
    repro["environment"]["build_identity"] = build["build_id"]
    repro["environment"]["build_content_digest"] = canonical_sha256(build)
    _persist(case, "reproducibility-manifest.json", repro)
    observed: list[dict[str, Any]] = []
    real = audit_module.validate_reproducibility_manifest

    def capture(manifest: Any, **kwargs: Any) -> Any:
        observed.append(kwargs["trusted_environment"])
        return real(manifest, **kwargs)

    monkeypatch.setattr(audit_module, "validate_reproducibility_manifest", capture)
    result = _audit(case)
    assert observed
    assert observed[0]["build_identity"] == build["build_id"]
    assert observed[0]["build_content_digest"] == canonical_sha256(build)
    _assert_code(
        result,
        ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID,
        "/release-build.json/build_id",
    )


def test_finding_order_is_deterministic_across_categories(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    (case.directory / "extra").write_bytes(b"x")
    artifact = _load(case, "artifact-manifest.json")
    (case.directory / "artifact-manifest.json").write_bytes(
        json.dumps(artifact, separators=(",", ":")).encode()
    )
    build = _load(case, "release-build.json")
    build["build_version"] = "7.3.9"
    _persist(case, "release-build.json", build)
    repro = _load(case, "reproducibility-manifest.json")
    repro["schema_set"].reverse()
    _persist(case, "reproducibility-manifest.json", repro)
    first = _audit(case)
    second = _audit(case)
    expected = (
        (
            ReleaseIntegrityAuditErrorCode.AUDIT_PACKAGE_LAYOUT_INVALID,
            "/",
            None,
            None,
            None,
        ),
        (
            ReleaseIntegrityAuditErrorCode.AUDIT_PHYSICAL_SERIALIZATION_INVALID,
            "/artifact-manifest.json",
            None,
            None,
            None,
        ),
        (
            ReleaseIntegrityAuditErrorCode.AUDIT_GENERATED_VERSION_INVALID,
            "/release-build.json/build_version",
            None,
            None,
            None,
        ),
        (
            ReleaseIntegrityAuditErrorCode.AUDIT_DETERMINISTIC_ORDER_INVALID,
            "/reproducibility-manifest.json/schema_set",
            None,
            None,
            None,
        ),
        (
            ReleaseIntegrityAuditErrorCode.AUDIT_VALIDATION_FAILED,
            "/reproducibility-manifest.json/environment",
            "ManifestFinding",
            "REPRODUCIBILITY_ENVIRONMENT_INVALID",
            "/environment",
        ),
    )
    first_projection = tuple(
        (
            finding.code,
            finding.field_path,
            finding.source,
            finding.source_code,
            finding.source_field_path,
        )
        for finding in first.findings
    )
    second_projection = tuple(
        (
            finding.code,
            finding.field_path,
            finding.source,
            finding.source_code,
            finding.source_field_path,
        )
        for finding in second.findings
    )
    assert first.findings == second.findings
    assert first_projection == second_projection == expected
    _assert_failed(first)


def test_invalid_profile_does_not_invent_release_identity_or_token_checks(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    profile = deepcopy(case.inputs["release_profile"])
    del profile["release_id"]
    result = _audit(case, release_profile=profile)
    assert result.release_id is None
    assert result.release_id_token is None
    assert result.findings[0].code is ReleaseIntegrityAuditErrorCode.AUDIT_VALIDATION_FAILED
    assert result.findings[0].field_path.startswith("/release-profile")
    assert not any(
        finding.field_path == "/release-build.json/build_id"
        and finding.code is ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID
        for finding in result.findings
    )


def test_invalid_build_json_short_circuits_build_consistency(
    tmp_path: Path,
    schema_store: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, schema_store)
    (case.directory / "release-build.json").write_bytes(b"{")
    called = False

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        nonlocal called
        called = True
        raise AssertionError("must not be called")

    monkeypatch.setattr(audit_module, "validate_release_build_consistency", forbidden)
    result = _audit(case)
    assert called is False
    _assert_code(
        result,
        ReleaseIntegrityAuditErrorCode.AUDIT_JSON_INVALID,
        "/release-build.json",
    )


def test_assert_error_carries_exact_result_and_findings(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    (case.directory / "extra").write_bytes(b"x")
    result = _audit(case)
    with pytest.raises(
        ReleaseIntegrityAuditError,
        match=r"^research release integrity audit has \d+ finding\(s\)$",
    ) as caught:
        assert_research_release_integrity(case.directory, **case.kwargs)
    assert caught.value.result == result
    assert caught.value.findings == result.findings


def test_audit_preserves_package_bytes_and_creates_no_child(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    before = {name: (case.directory / name).read_bytes() for name in FILES}
    names = tuple(sorted(path.name for path in case.directory.iterdir()))
    _audit(case)
    assert {name: (case.directory / name).read_bytes() for name in FILES} == before
    assert tuple(sorted(path.name for path in case.directory.iterdir())) == names


def test_audit_does_not_mutate_caller_inputs(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    before_schema_store = _deterministic_snapshot(case.inputs["schema_store"])
    before = deepcopy(
        {name: case.inputs[name] for name in AUDIT_ARGUMENTS if name != "schema_store"}
    )
    assert set(before) | {"schema_store"} == set(AUDIT_ARGUMENTS)
    _audit(case)
    after_schema_store = _deterministic_snapshot(case.inputs["schema_store"])
    assert {
        name: case.inputs[name] for name in AUDIT_ARGUMENTS if name != "schema_store"
    } == before
    assert after_schema_store == before_schema_store


def test_every_representative_failure_withholds_digest_and_annotation(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    (case.directory / "extra").write_bytes(b"x")
    _assert_failed(_audit(case))



@pytest.mark.parametrize("phase", ("PILOT", "CONFIRMATORY"))
def test_research_phase_limitation_does_not_waive_missing_provenance(
    tmp_path: Path,
    schema_store: dict[str, Any],
    phase: str,
) -> None:
    closure = _closure(provenance=False)
    case = _case(
        tmp_path,
        schema_store,
        runtime_dependency_closure=closure,
        reproducibility_limitations=("Archive unavailable.",),
    )
    result = _audit(
        case,
        release_profile=_set_phase(case, phase),
    )
    _assert_code(
        result,
        ReleaseIntegrityAuditErrorCode.AUDIT_DEPENDENCY_PROVENANCE_INCOMPLETE,
        "/release-build.json/dependencies",
    )


def test_unrelated_invalid_build_does_not_suppress_artifact_whitelist_check(
    tmp_path: Path,
    schema_store: dict[str, Any],
) -> None:
    case = _case(tmp_path, schema_store)
    artifact = _load(case, "artifact-manifest.json")
    artifact["artifacts"].pop()
    _persist(case, "artifact-manifest.json", artifact)
    (case.directory / "release-build.json").write_bytes(b"{}\n")
    result = _audit(case)
    _assert_code(
        result,
        ReleaseIntegrityAuditErrorCode.AUDIT_RELEASE_BINDING_INVALID,
        "/artifact-manifest.json/artifacts",
    )
    _assert_code(
        result,
        ReleaseIntegrityAuditErrorCode.AUDIT_VALIDATION_FAILED,
        "/release-build.json",
    )
