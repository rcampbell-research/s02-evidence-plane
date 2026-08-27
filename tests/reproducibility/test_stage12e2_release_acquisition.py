"""Stage 12E-2 read-only local release acquisition tests."""

from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, replace
import json
from pathlib import Path
import subprocess
from typing import Any

import pytest

import frontier_agent_containment.release_acquisition as acquisition
from frontier_agent_containment.integrity import forensic_sha256_bytes
from frontier_agent_containment.release_acquisition import (
    AcquisitionErrorCode,
    DistributionArtifactProvenance,
    GOVERNING_DOCUMENT_REGISTRY_V0_1,
    GoverningDocumentRegistryEntry,
    ReleaseAcquisitionError,
    ReleaseAcquisitionFinding,
    RuntimeEnvironmentFacts,
    acquire_git_provenance,
    acquire_governing_documents,
    acquire_runtime_dependency_closure,
    acquire_runtime_environment,
    construct_os_runtime_identity,
    validate_release_build_consistency,
)


ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv/bin/python"
SOURCE_TAG = "research-release-development-v0.1"
ZONEINFO_ROOT = Path("/usr/share/zoneinfo")
KNOWN_RFC8785_DIGEST = (
    "520d690b448ecf0703691c76e1a34a24ddcd4fc5bc41d589cb7c58ec651bcd48"
)
EXPECTED_REGISTRY = (
    (
        "research-contract",
        "v0.1",
        "docs/research-contract-v0.1.md",
        "research-contract-v0.1",
    ),
    (
        "threat-scenario-spec",
        "v0.1",
        "docs/threat-scenario-spec-v0.1.md",
        "threat-scenario-spec-v0.1",
    ),
    (
        "control-architecture-spec",
        "v0.1",
        "docs/control-architecture-spec-v0.1.md",
        "control-architecture-spec-v0.1",
    ),
    (
        "evidence-spec",
        "v0.1",
        "docs/evidence-spec-v0.1.md",
        "evidence-spec-v0.1",
    ),
    (
        "instrument-validation-spec",
        "v0.1",
        "docs/instrument-validation-spec-v0.1.md",
        "instrument-validation-spec-v0.1",
    ),
    (
        "statistical-analysis-plan",
        "v0.1",
        "docs/statistical-analysis-plan-v0.1.md",
        "statistical-analysis-plan-v0.1",
    ),
    (
        "implementation-contract",
        "v0.1",
        "docs/implementation-contract-v0.1.md",
        "implementation-contract-v0.1",
    ),
    (
        "integrity-reproducibility-spec",
        "v0.1",
        "docs/integrity-reproducibility-spec-v0.1.md",
        "integrity-reproducibility-spec-v0.1",
    ),
    (
        "integrity-reproducibility-clarification",
        "v0.1",
        "docs/integrity-reproducibility-clarification-v0.1.md",
        "integrity-reproducibility-clarification-v0.1",
    ),
)


def run_git(
    repository: Path,
    *arguments: str,
    binary_input: bytes | None = None,
) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        input=binary_input,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        shell=False,
    )
    return completed.stdout


def initialize_repository(
    tmp_path: Path,
    *,
    pyproject_dependencies: tuple[str, ...] = ("alpha==1.0",),
    governing_bytes: bytes | None = None,
) -> Path:
    repository = tmp_path / "repo"
    repository.mkdir()
    run_git(repository, "init", "-q")
    run_git(repository, "config", "user.name", "Stage 12E Test")
    run_git(repository, "config", "user.email", "stage12e@example.invalid")
    dependencies = ",\n".join(
        f'    "{requirement}"' for requirement in pyproject_dependencies
    )
    (repository / "pyproject.toml").write_text(
        "[project]\n"
        'name = "synthetic-release"\n'
        'version = "0.1.0"\n'
        "dependencies = [\n"
        f"{dependencies}\n"
        "]\n"
        "\n"
        "[project.optional-dependencies]\n"
        'feature = ["beta==2.0"]\n'
        'release-integrity = ["packaging==24.0"]\n',
        encoding="utf-8",
    )
    (repository / "README.md").write_text("synthetic\n", encoding="utf-8")
    if governing_bytes is not None:
        path = repository / "docs/example-v0.1.md"
        path.parent.mkdir()
        path.write_bytes(governing_bytes)
    run_git(repository, "add", "pyproject.toml", "README.md")
    if governing_bytes is not None:
        run_git(repository, "add", "docs/example-v0.1.md")
    run_git(repository, "commit", "-q", "-m", "source")
    return repository


def annotate(repository: Path, tag: str, target: str = "HEAD") -> None:
    run_git(repository, "tag", "-a", tag, target, "-m", f"Frozen {tag}")


def assert_error(
    error: pytest.ExceptionInfo[ReleaseAcquisitionError],
    code: AcquisitionErrorCode,
) -> ReleaseAcquisitionFinding:
    assert error.value.findings
    assert error.value.findings[0].code is code
    return error.value.findings[0]


def marker_environment(**updates: str) -> dict[str, str]:
    result = {
        "implementation_name": "cpython",
        "implementation_version": "3.12.3",
        "os_name": "posix",
        "platform_machine": "x86_64",
        "platform_release": "6.17.0-35-generic",
        "platform_system": "Linux",
        "platform_version": "test",
        "python_full_version": "3.12.3",
        "platform_python_implementation": "CPython",
        "python_version": "3.12",
        "sys_platform": "linux",
    }
    result.update(updates)
    return result


def distribution(
    name: str,
    version: str,
    *,
    requires: tuple[str, ...] = (),
    extras: tuple[str, ...] = (),
    direct_url: dict[str, Any] | None = None,
    direct_url_text: str | None = None,
    record_present: bool = False,
) -> acquisition._InstalledDistribution:
    if direct_url is not None:
        direct_url_text = json.dumps(direct_url, sort_keys=True)
    return acquisition._InstalledDistribution(
        name=name,
        version=version,
        requires_dist=requires,
        provides_extra=extras,
        direct_url_text=direct_url_text,
        origin="/synthetic/site-packages",
        record_present=record_present,
    )


def resolve(
    project: dict[str, Any],
    inventory: tuple[acquisition._InstalledDistribution, ...],
    *,
    extras: tuple[str, ...] = (),
    markers: dict[str, str] | None = None,
):
    return acquisition._resolve_dependency_closure(
        project,
        inventory,
        marker_environment() if markers is None else markers,
        extras,
    )


def probe_payload(
    venv_root: Path,
    *,
    user_site: bool | None,
    no_user_site: int,
) -> dict[str, Any]:
    return {
        "prefix": str(venv_root),
        "base_prefix": str(venv_root.parent / "base-python"),
        "executable": str(venv_root / "bin/python"),
        "python_implementation": "CPython",
        "python_version": "3.12.3",
        "python_build_string": "3.12.3 (synthetic build) [GCC 13.3.0]",
        "os_system": "Linux",
        "kernel_release": "6.17.0-35-generic",
        "libc": ["glibc", "2.39"],
        "architecture": "x86_64",
        "enable_user_site": user_site,
        "no_user_site": no_user_site,
        "marker_environment": marker_environment(),
    }


def install_runtime_mocks(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
) -> None:
    monkeypatch.setattr(
        acquisition,
        "_probe_interpreter",
        lambda *args, **kwargs: deepcopy(payload),
    )
    monkeypatch.setattr(
        acquisition,
        "_acquire_os_release_identity",
        lambda *args, **kwargs: "ubuntu-24.04",
    )
    monkeypatch.setattr(
        acquisition,
        "_acquire_timezone_identity",
        lambda *args, **kwargs: "UTC",
    )


def make_runtime_facts() -> RuntimeEnvironmentFacts:
    return RuntimeEnvironmentFacts(
        python_executable="/venv/bin/python",
        venv_root="/venv",
        python_implementation="CPython",
        python_version="3.12.3",
        python_build_string="3.12.3 test",
        os_system="Linux",
        os_release_identity="ubuntu-24.04",
        kernel_release="6.17.0-35-generic",
        libc_identity="glibc-2.39",
        architecture="x86_64",
        os_runtime_identity=(
            "system-Linux+release-ubuntu-24.04"
            "+kernel-6.17.0-35-generic+libc-glibc-2.39"
        ),
        locale_identity="C.UTF-8",
        timezone_identity="America/New_York",
        environment_reference="env:synthetic",
        environment_mode="DEVELOPMENT_TOOLING",
        system_site_packages_enabled=True,
        user_site_packages_enabled=True,
    )


def candidate_build(facts: RuntimeEnvironmentFacts) -> dict[str, Any]:
    excluded = {"python_executable", "venv_root"}
    return {
        key: value
        for key, value in asdict(facts).items()
        if key not in excluded
    }


def test_registry_is_exact_frozen_nine_entry_projection() -> None:
    actual = tuple(
        (
            entry.document_id,
            entry.document_version,
            entry.repository_path,
            entry.frozen_tag_identity,
        )
        for entry in GOVERNING_DOCUMENT_REGISTRY_V0_1
    )
    assert actual == EXPECTED_REGISTRY
    assert len(actual) == 9
    assert len({entry[0] for entry in actual}) == 9


@pytest.mark.parametrize(
    ("index", "expected"),
    list(enumerate(EXPECTED_REGISTRY)),
)
def test_registry_entry_order_and_fields(
    index: int,
    expected: tuple[str, str, str, str],
) -> None:
    entry = GOVERNING_DOCUMENT_REGISTRY_V0_1[index]
    assert (
        entry.document_id,
        entry.document_version,
        entry.repository_path,
        entry.frozen_tag_identity,
    ) == expected


def test_registry_entries_and_tuple_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        GOVERNING_DOCUMENT_REGISTRY_V0_1[0].document_id = (  # type: ignore[misc]
            "changed"
        )
    with pytest.raises(TypeError):
        GOVERNING_DOCUMENT_REGISTRY_V0_1[0] = (  # type: ignore[index]
            GOVERNING_DOCUMENT_REGISTRY_V0_1[1]
        )


@pytest.mark.parametrize("entry", GOVERNING_DOCUMENT_REGISTRY_V0_1)
def test_real_historical_tag_is_annotated_and_contains_registered_path(
    entry: GoverningDocumentRegistryEntry,
) -> None:
    object_type = run_git(ROOT, "cat-file", "-t", entry.frozen_tag_identity)
    assert object_type == b"tag\n"
    run_git(
        ROOT,
        "cat-file",
        "-e",
        f"{entry.frozen_tag_identity}:{entry.repository_path}",
    )


def test_git_provenance_accepts_annotated_source_tag(tmp_path: Path) -> None:
    repository = initialize_repository(tmp_path)
    annotate(repository, SOURCE_TAG)
    result = acquire_git_provenance(repository, SOURCE_TAG)
    assert result.repository_object_format == "SHA-1"
    assert result.release_tag_identity == SOURCE_TAG
    assert result.repository_commit_sha == result.release_tag_target_commit_sha
    assert run_git(
        repository, "cat-file", "-t", result.release_tag_object_sha
    ) == b"tag\n"
    assert run_git(
        repository, "cat-file", "-t", result.repository_commit_sha
    ) == b"commit\n"
    assert run_git(
        repository, "cat-file", "-t", result.repository_tree_sha
    ) == b"tree\n"
    assert result.repository_clean is True


def test_git_provenance_reports_dirty_without_mutation(tmp_path: Path) -> None:
    repository = initialize_repository(tmp_path)
    annotate(repository, SOURCE_TAG)
    (repository / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    before = (repository / "dirty.txt").read_bytes()
    result = acquire_git_provenance(repository, SOURCE_TAG)
    assert result.repository_clean is False
    assert (repository / "dirty.txt").read_bytes() == before


def test_git_provenance_is_deterministic(tmp_path: Path) -> None:
    repository = initialize_repository(tmp_path)
    annotate(repository, SOURCE_TAG)
    assert acquire_git_provenance(
        repository, SOURCE_TAG
    ) == acquire_git_provenance(repository, SOURCE_TAG)


def test_git_provenance_missing_tag_fails(tmp_path: Path) -> None:
    repository = initialize_repository(tmp_path)
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquire_git_provenance(repository, SOURCE_TAG)
    assert_error(error, AcquisitionErrorCode.ACQUISITION_GIT_INVALID)


def test_git_provenance_lightweight_tag_fails(tmp_path: Path) -> None:
    repository = initialize_repository(tmp_path)
    run_git(repository, "tag", SOURCE_TAG)
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquire_git_provenance(repository, SOURCE_TAG)
    finding = assert_error(error, AcquisitionErrorCode.ACQUISITION_GIT_INVALID)
    assert "lightweight" in finding.message


def test_git_provenance_noncommit_target_fails(tmp_path: Path) -> None:
    repository = initialize_repository(tmp_path)
    blob = run_git(
        repository,
        "hash-object",
        "-w",
        "--stdin",
        binary_input=b"not a commit",
    ).decode().strip()
    annotate(repository, SOURCE_TAG, blob)
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquire_git_provenance(repository, SOURCE_TAG)
    assert_error(error, AcquisitionErrorCode.ACQUISITION_GIT_INVALID)


@pytest.mark.parametrize(
    "tag",
    ["latest", "research-release-development-v01.0", "other-v0.1"],
)
def test_git_provenance_rejects_unfrozen_source_tag_syntax(
    tmp_path: Path, tag: str
) -> None:
    repository = initialize_repository(tmp_path)
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquire_git_provenance(repository, tag)
    assert_error(error, AcquisitionErrorCode.ACQUISITION_GIT_INVALID)


def custom_registry(
    tag: str = "example-spec-v0.1",
) -> tuple[GoverningDocumentRegistryEntry, ...]:
    return (
        GoverningDocumentRegistryEntry(
            "example-spec",
            "v0.1",
            "docs/example-v0.1.md",
            tag,
        ),
    )


def test_governing_acquisition_accepts_exact_source_copy(tmp_path: Path) -> None:
    raw = b"# Example\r\nexact bytes\n"
    repository = initialize_repository(tmp_path, governing_bytes=raw)
    annotate(repository, "example-spec-v0.1")
    annotate(repository, SOURCE_TAG)
    result = acquire_governing_documents(
        repository, SOURCE_TAG, custom_registry()
    )
    assert result.governing_document_bytes_by_id["example-spec"] == raw
    provenance = result.documents[0].provenance
    assert provenance.exact_byte_content_digest == forensic_sha256_bytes(raw)
    assert result.governing_document_provenance_by_id["example-spec"] == {
        "document_version": "v0.1",
        "frozen_tag_identity": "example-spec-v0.1",
    }
    with pytest.raises(TypeError):
        result.governing_document_bytes_by_id["new"] = b"x"  # type: ignore[index]


def test_governing_source_copy_mismatch_fails(tmp_path: Path) -> None:
    repository = initialize_repository(tmp_path, governing_bytes=b"frozen\n")
    annotate(repository, "example-spec-v0.1")
    path = repository / "docs/example-v0.1.md"
    path.write_bytes(b"changed\n")
    run_git(repository, "add", "docs/example-v0.1.md")
    run_git(repository, "commit", "-q", "-m", "changed")
    annotate(repository, SOURCE_TAG)
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquire_governing_documents(
            repository, SOURCE_TAG, custom_registry()
        )
    finding = assert_error(
        error,
        AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
    )
    assert finding.document_id == "example-spec"


def test_governing_missing_registered_path_fails(tmp_path: Path) -> None:
    repository = initialize_repository(tmp_path)
    annotate(repository, "example-spec-v0.1")
    annotate(repository, SOURCE_TAG)
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquire_governing_documents(
            repository, SOURCE_TAG, custom_registry()
        )
    assert_error(
        error,
        AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
    )


def test_governing_lightweight_historical_tag_fails(tmp_path: Path) -> None:
    repository = initialize_repository(tmp_path, governing_bytes=b"frozen\n")
    run_git(repository, "tag", "example-spec-v0.1")
    annotate(repository, SOURCE_TAG)
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquire_governing_documents(
            repository, SOURCE_TAG, custom_registry()
        )
    assert_error(
        error,
        AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
    )


def test_governing_newline_change_changes_exact_byte_digest(tmp_path: Path) -> None:
    first = b"# Example\n"
    second = b"# Example\r\n"
    assert forensic_sha256_bytes(first) != forensic_sha256_bytes(second)
    repository = initialize_repository(tmp_path, governing_bytes=first)
    annotate(repository, "example-spec-v0.1")
    annotate(repository, SOURCE_TAG)
    result = acquire_governing_documents(
        repository, SOURCE_TAG, custom_registry()
    )
    assert result.documents[0].provenance.exact_byte_content_digest == (
        forensic_sha256_bytes(first)
    )


def test_governing_registry_input_is_not_mutated(tmp_path: Path) -> None:
    repository = initialize_repository(tmp_path, governing_bytes=b"frozen\n")
    annotate(repository, "example-spec-v0.1")
    annotate(repository, SOURCE_TAG)
    registry = custom_registry()
    before = deepcopy(registry)
    acquire_governing_documents(repository, SOURCE_TAG, registry)
    assert registry == before


def test_duplicate_governing_registry_identity_fails(tmp_path: Path) -> None:
    repository = initialize_repository(tmp_path, governing_bytes=b"frozen\n")
    annotate(repository, "example-spec-v0.1")
    annotate(repository, SOURCE_TAG)
    registry = custom_registry() + custom_registry()
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquire_governing_documents(repository, SOURCE_TAG, registry)
    assert_error(
        error,
        AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
    )


def test_packaging_24_tooling_gate_accepts_current_runtime() -> None:
    acquisition._require_packaging_tooling()


def test_packaging_tooling_gate_rejects_wrong_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        acquisition.importlib_metadata,
        "version",
        lambda name: "25.0",
    )
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._require_packaging_tooling()
    assert_error(error, AcquisitionErrorCode.ACQUISITION_TOOLING_INVALID)


def test_packaging_tooling_gate_rejects_loaded_module_version_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(acquisition._packaging, "__version__", "23.2")
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._require_packaging_tooling()
    assert_error(error, AcquisitionErrorCode.ACQUISITION_TOOLING_INVALID)


def test_packaging_tooling_gate_rejects_absent_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(acquisition, "_PackagingRequirement", None)
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._require_packaging_tooling()
    assert_error(error, AcquisitionErrorCode.ACQUISITION_TOOLING_INVALID)


def test_simple_direct_dependency_closure() -> None:
    result = resolve(
        {"dependencies": ["alpha==1.0"], "optional-dependencies": {}},
        (distribution("alpha", "1.0"),),
    )
    assert [(item.name, item.version) for item in result.dependencies] == [
        ("alpha", "1.0")
    ]
    assert result.dependency_scope == "FULL_TRANSITIVE_RUNTIME"


def test_transitive_dependency_closure() -> None:
    result = resolve(
        {"dependencies": ["alpha==1.0"], "optional-dependencies": {}},
        (
            distribution("alpha", "1.0", requires=("beta>=2",)),
            distribution("beta", "2.1"),
        ),
    )
    assert [item.name for item in result.dependencies] == ["alpha", "beta"]


@pytest.mark.parametrize(
    ("requirement", "expected"),
    [
        ("beta; python_version < '3.0'", ["alpha"]),
        ("beta; python_version >= '3.0'", ["alpha", "beta"]),
    ],
)
def test_dependency_markers_use_selected_environment(
    requirement: str, expected: list[str]
) -> None:
    result = resolve(
        {"dependencies": ["alpha"], "optional-dependencies": {}},
        (
            distribution("alpha", "1.0", requires=(requirement,)),
            distribution("beta", "2.0"),
        ),
    )
    assert [item.name for item in result.dependencies] == expected


def test_explicit_declared_project_extra_is_included() -> None:
    result = resolve(
        {
            "dependencies": ["alpha"],
            "optional-dependencies": {"feature": ["beta==2.0"]},
        },
        (distribution("alpha", "1.0"), distribution("beta", "2.0")),
        extras=("feature",),
    )
    assert [item.name for item in result.dependencies] == ["alpha", "beta"]


def test_project_extra_is_not_implicitly_included() -> None:
    result = resolve(
        {
            "dependencies": ["alpha"],
            "optional-dependencies": {"feature": ["beta==2.0"]},
        },
        (distribution("alpha", "1.0"), distribution("beta", "2.0")),
    )
    assert [item.name for item in result.dependencies] == ["alpha"]


def test_transitive_requested_extra_enables_extra_marker() -> None:
    result = resolve(
        {"dependencies": ["alpha[feature]"], "optional-dependencies": {}},
        (
            distribution(
                "alpha",
                "1.0",
                requires=("beta; extra == 'feature'",),
                extras=("feature",),
            ),
            distribution("beta", "2.0"),
        ),
    )
    assert [item.name for item in result.dependencies] == ["alpha", "beta"]


def test_unknown_project_extra_fails() -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        resolve(
            {"dependencies": ["alpha"], "optional-dependencies": {}},
            (distribution("alpha", "1.0"),),
            extras=("unknown",),
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID)


def test_missing_required_distribution_fails() -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        resolve(
            {"dependencies": ["missing>=1"], "optional-dependencies": {}},
            (),
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID)


def test_unsatisfied_dependency_edge_fails() -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        resolve(
            {"dependencies": ["alpha>=2"], "optional-dependencies": {}},
            (distribution("alpha", "1.0"),),
        )
    finding = assert_error(
        error, AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID
    )
    assert "does not satisfy" in finding.message


def test_duplicate_exact_name_version_collapses() -> None:
    duplicate = distribution("alpha", "1.0")
    result = resolve(
        {"dependencies": ["alpha"], "optional-dependencies": {}},
        (duplicate, duplicate),
    )
    assert len(result.dependencies) == 1


def test_same_exact_name_different_version_fails() -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        resolve(
            {"dependencies": ["alpha"], "optional-dependencies": {}},
            (
                distribution("alpha", "1.0"),
                distribution("alpha", "2.0"),
            ),
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_DEPENDENCY_CONFLICT)


def test_standards_equivalent_names_remain_ambiguous() -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        resolve(
            {"dependencies": ["alpha-beta"], "optional-dependencies": {}},
            (
                distribution("alpha-beta", "1.0"),
                distribution("alpha_beta", "1.0"),
            ),
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_DEPENDENCY_CONFLICT)


def test_unrepresentable_exact_metadata_name_fails_without_normalization() -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        resolve(
            {"dependencies": ["Alpha"], "optional-dependencies": {}},
            (distribution("Alpha", "1.0"),),
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID)


def test_dependency_closure_order_is_deterministic() -> None:
    project = {
        "dependencies": ["zeta", "alpha", "middle"],
        "optional-dependencies": {},
    }
    inventory = (
        distribution("zeta", "1.0"),
        distribution("middle", "1.0"),
        distribution("alpha", "1.0"),
    )
    first = resolve(project, inventory)
    second = resolve(deepcopy(project), tuple(reversed(inventory)))
    assert first == second
    assert [item.name for item in first.dependencies] == [
        "alpha",
        "middle",
        "zeta",
    ]


def test_release_integrity_tooling_not_implicitly_scientific() -> None:
    result = resolve(
        {
            "dependencies": ["alpha"],
            "optional-dependencies": {
                "release-integrity": ["packaging==24.0"]
            },
        },
        (
            distribution("alpha", "1.0"),
            distribution("packaging", "24.0"),
        ),
    )
    assert [item.name for item in result.dependencies] == ["alpha"]


def test_dependency_inputs_are_not_mutated() -> None:
    project = {"dependencies": ["alpha"], "optional-dependencies": {}}
    inventory = (distribution("alpha", "1.0"),)
    markers = marker_environment()
    before = deepcopy((project, inventory, markers))
    resolve(project, inventory, markers=markers)
    assert (project, inventory, markers) == before


def dependency_probe_payload() -> dict[str, Any]:
    return {
        "marker_environment": marker_environment(),
        "distributions": [
            {
                "name": "alpha",
                "version": "1.0",
                "requires_dist": [],
                "provides_extra": [],
                "direct_url_text": None,
                "origin": "/synthetic",
                "record_present": True,
            },
            {
                "name": "beta",
                "version": "2.0",
                "requires_dist": [],
                "provides_extra": [],
                "direct_url_text": None,
                "origin": "/synthetic",
                "record_present": True,
            },
        ],
    }


def test_dependency_roots_come_from_source_tag_not_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = initialize_repository(
        tmp_path, pyproject_dependencies=("alpha==1.0",)
    )
    annotate(repository, SOURCE_TAG)
    (repository / "pyproject.toml").write_text(
        "[project]\n"
        'name = "changed"\n'
        'version = "0.1.0"\n'
        'dependencies = ["beta==2.0"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        acquisition,
        "_probe_interpreter",
        lambda *args, **kwargs: dependency_probe_payload(),
    )
    result = acquire_runtime_dependency_closure(
        repository, SOURCE_TAG, PYTHON
    )
    assert [item.name for item in result.dependencies] == ["alpha"]


def test_runtime_dependency_public_result_has_immutable_stage12d_view(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = initialize_repository(tmp_path)
    annotate(repository, SOURCE_TAG)
    monkeypatch.setattr(
        acquisition,
        "_probe_interpreter",
        lambda *args, **kwargs: dependency_probe_payload(),
    )
    result = acquire_runtime_dependency_closure(
        repository, SOURCE_TAG, PYTHON
    )
    record = result.resolved_dependencies[0]
    assert record == {"name": "alpha", "version": "1.0"}
    with pytest.raises(TypeError):
        record["version"] = "changed"  # type: ignore[index]


def direct_url(
    url: str,
    digest: str,
    *,
    plural_digest: str | None = None,
) -> dict[str, Any]:
    archive: dict[str, Any] = {"hash": f"sha256={digest}"}
    if plural_digest is not None:
        archive["hashes"] = {"sha256": plural_digest}
    return {"url": url, "archive_info": archive}


def test_known_rfc8785_direct_url_provenance_is_recognized() -> None:
    item = distribution(
        "rfc8785",
        "0.1.4",
        direct_url=direct_url(
            "file:///nonexistent/rfc8785-0.1.4-py3-none-any.whl",
            KNOWN_RFC8785_DIGEST,
        ),
    )
    provenance, finding = acquisition._distribution_provenance(item)
    assert finding is None
    assert provenance == DistributionArtifactProvenance(
        distribution_filename="rfc8785-0.1.4-py3-none-any.whl",
        distribution_digest=f"sha256:{KNOWN_RFC8785_DIGEST}",
        source="direct_url.json",
    )


def test_local_original_distribution_exact_hash_is_verified(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "alpha-1.0-py3-none-any.whl"
    wheel.write_bytes(b"synthetic wheel bytes")
    digest = forensic_sha256_bytes(wheel.read_bytes()).removeprefix("sha256:")
    item = distribution(
        "alpha",
        "1.0",
        direct_url=direct_url(wheel.as_uri(), digest),
    )
    provenance, finding = acquisition._distribution_provenance(item)
    assert finding is None
    assert provenance is not None
    assert provenance.distribution_filename == wheel.name


def test_local_original_distribution_hash_mismatch_fails(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "alpha-1.0-py3-none-any.whl"
    wheel.write_bytes(b"synthetic wheel bytes")
    item = distribution(
        "alpha",
        "1.0",
        direct_url=direct_url(wheel.as_uri(), "0" * 64),
    )
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._distribution_provenance(item)
    assert_error(error, AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID)


def test_conflicting_direct_url_hashes_fail() -> None:
    item = distribution(
        "alpha",
        "1.0",
        direct_url=direct_url(
            "https://example.invalid/alpha-1.0.whl",
            "0" * 64,
            plural_digest="1" * 64,
        ),
    )
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._distribution_provenance(item)
    assert_error(error, AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID)


@pytest.mark.parametrize(
    "item",
    [
        distribution("alpha", "1.0"),
        distribution("alpha", "1.0", record_present=True),
        distribution(
            "alpha",
            "1.0",
            direct_url={"url": "file:///tmp/alpha.whl", "dir_info": {}},
        ),
    ],
)
def test_missing_original_provenance_is_nonfatal_and_not_fabricated(
    item: acquisition._InstalledDistribution,
) -> None:
    provenance, finding = acquisition._distribution_provenance(item)
    assert provenance is None
    assert finding is not None
    assert finding.code is (
        AcquisitionErrorCode.ACQUISITION_DISTRIBUTION_PROVENANCE_UNAVAILABLE
    )


@pytest.mark.parametrize(
    "direct_url_document",
    [
        direct_url("file:///tmp/alpha.whl", "ABC"),
        direct_url("file:///tmp/bad%5Cname.whl", "0" * 64),
    ],
)
def test_malformed_distribution_provenance_fails(
    direct_url_document: dict[str, Any],
) -> None:
    item = distribution("alpha", "1.0", direct_url=direct_url_document)
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._distribution_provenance(item)
    assert_error(error, AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("include-system-site-packages = true\n", True),
        ("include-system-site-packages = FALSE\n", False),
    ],
)
def test_system_site_fact_comes_from_pyvenv_cfg(
    tmp_path: Path, text: str, expected: bool
) -> None:
    config = tmp_path / "pyvenv.cfg"
    config.write_text(text, encoding="utf-8")
    assert acquisition._read_system_site_packages(config) is expected


@pytest.mark.parametrize(
    "text",
    [
        "home = /usr/bin\n",
        "include-system-site-packages = maybe\n",
        (
            "include-system-site-packages = true\n"
            "include-system-site-packages = false\n"
        ),
    ],
)
def test_invalid_system_site_configuration_fails(
    tmp_path: Path, text: str
) -> None:
    config = tmp_path / "pyvenv.cfg"
    config.write_text(text, encoding="utf-8")
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._read_system_site_packages(config)
    assert_error(error, AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID)


@pytest.mark.parametrize(
    ("enable", "flag", "expected"),
    [
        (True, 0, True),
        (False, 0, False),
        (None, 0, False),
        (False, 1, False),
        (None, 1, False),
    ],
)
def test_user_site_acquisition(
    enable: bool | None, flag: int, expected: bool
) -> None:
    assert acquisition._derive_user_site_enabled(enable, flag) is expected


def test_user_site_contradiction_fails() -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._derive_user_site_enabled(True, 1)
    assert_error(error, AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID)


def test_non_venv_probe_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = probe_payload(tmp_path / "venv", user_site=False, no_user_site=0)
    payload["base_prefix"] = payload["prefix"]
    install_runtime_mocks(monkeypatch, payload)
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquire_runtime_environment(
            PYTHON,
            environment_mode="DEVELOPMENT_TOOLING",
            environment_reference="env:synthetic",
            environment={"LC_ALL": "C.UTF-8", "TZ": "UTC"},
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID)


def test_missing_pyvenv_cfg_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    venv = tmp_path / "venv"
    venv.mkdir()
    payload = probe_payload(venv, user_site=False, no_user_site=0)
    install_runtime_mocks(monkeypatch, payload)
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquire_runtime_environment(
            PYTHON,
            environment_mode="DEVELOPMENT_TOOLING",
            environment_reference="env:synthetic",
            environment={"LC_ALL": "C.UTF-8", "TZ": "UTC"},
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID)


@pytest.mark.parametrize(
    ("mode", "system_site", "user_site", "accepted"),
    [
        ("DEVELOPMENT_TOOLING", True, True, True),
        ("CONTROLLED_RUNTIME", False, False, True),
        ("CONTROLLED_RUNTIME", True, False, False),
        ("CONTROLLED_RUNTIME", False, True, False),
        ("CONTROLLED_RUNTIME", True, True, False),
    ],
)
def test_environment_mode_consistency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    system_site: bool,
    user_site: bool,
    accepted: bool,
) -> None:
    venv = tmp_path / "venv"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text(
        f"include-system-site-packages = {str(system_site).lower()}\n",
        encoding="utf-8",
    )
    payload = probe_payload(venv, user_site=user_site, no_user_site=0)
    install_runtime_mocks(monkeypatch, payload)
    call = lambda: acquire_runtime_environment(
        PYTHON,
        environment_mode=mode,
        environment_reference="env:synthetic",
        environment={"LC_ALL": "C.UTF-8", "TZ": "UTC"},
    )
    if accepted:
        result = call()
        assert result.environment_mode == mode
        assert result.system_site_packages_enabled is system_site
        assert result.user_site_packages_enabled is user_site
    else:
        with pytest.raises(ReleaseAcquisitionError) as error:
            call()
        assert_error(error, AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID)


def test_os_release_exact_serialization(tmp_path: Path) -> None:
    etc = tmp_path / "etc-os-release"
    usr = tmp_path / "usr-os-release"
    etc.write_text("ID=ubuntu\nVERSION_ID=24.04\n", encoding="utf-8")
    usr.write_text("ID=ignored\nVERSION_ID=9\n", encoding="utf-8")
    assert acquisition._acquire_os_release_identity(etc, usr) == "ubuntu-24.04"


def test_os_release_falls_back_only_when_etc_absent(tmp_path: Path) -> None:
    etc = tmp_path / "absent"
    usr = tmp_path / "usr-os-release"
    usr.write_text("ID=example\nVERSION_ID=1.2.3\n", encoding="utf-8")
    assert acquisition._acquire_os_release_identity(etc, usr) == "example-1.2.3"


def test_os_release_quoted_syntax_is_parsed_without_normalization(
    tmp_path: Path,
) -> None:
    etc = tmp_path / "os-release"
    etc.write_text('ID="Ubuntu"\nVERSION_ID="24.04"\n', encoding="utf-8")
    assert acquisition._acquire_os_release_identity(
        etc, tmp_path / "absent"
    ) == "Ubuntu-24.04"


@pytest.mark.parametrize(
    "text",
    [
        "VERSION_ID=24.04\nPRETTY_NAME=Ubuntu\n",
        "ID=ubuntu\nPRETTY_NAME=Ubuntu\n",
        "PRETTY_NAME=Ubuntu\n",
        "ID=ubuntu linux\nVERSION_ID=24.04\n",
        "ID=ubuntu\nVERSION_ID=24/04\n",
    ],
)
def test_invalid_os_release_metadata_fails(
    tmp_path: Path, text: str
) -> None:
    etc = tmp_path / "os-release"
    etc.write_text(text, encoding="utf-8")
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._acquire_os_release_identity(
            etc, tmp_path / "absent"
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_OS_INVALID)


def test_libc_exact_serialization() -> None:
    assert acquisition._serialize_libc_identity("glibc", "2.39") == "glibc-2.39"


@pytest.mark.parametrize(
    ("implementation", "version"),
    [
        ("", "2.39"),
        ("glibc", ""),
        ("glibc/linux", "2.39"),
        ("glibc", "2 39"),
    ],
)
def test_invalid_libc_components_fail(
    implementation: str, version: str
) -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._serialize_libc_identity(implementation, version)
    assert_error(error, AcquisitionErrorCode.ACQUISITION_OS_INVALID)


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        (
            {"LC_ALL": "C.UTF-8", "LANG": "en_US.UTF-8"},
            "C.UTF-8",
        ),
        ({"LANG": "en_US.UTF-8"}, "en_US.UTF-8"),
        (
            {"LANG": "en_US.UTF-8", "LC_CTYPE": "en_US.UTF-8"},
            "en_US.UTF-8",
        ),
    ],
)
def test_locale_precedence(
    environment: dict[str, str], expected: str
) -> None:
    before = deepcopy(environment)
    assert acquisition._acquire_locale_identity(environment) == expected
    assert environment == before


@pytest.mark.parametrize(
    "environment",
    [
        {"LANG": "en_US.UTF-8", "LC_TIME": "C.UTF-8"},
        {},
        {"LC_ALL": "America/New_York"},
    ],
)
def test_invalid_or_mixed_locale_fails(environment: dict[str, str]) -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._acquire_locale_identity(environment)
    assert_error(error, AcquisitionErrorCode.ACQUISITION_LOCALE_INVALID)


def test_explicit_valid_timezone_wins(tmp_path: Path) -> None:
    result = acquisition._acquire_timezone_identity(
        {"TZ": "America/New_York"},
        localtime_path=tmp_path / "missing-localtime",
        timezone_path=tmp_path / "missing-timezone",
        zoneinfo_root=ZONEINFO_ROOT,
    )
    assert result == "America/New_York"


@pytest.mark.parametrize("candidate", [":America/New_York", "/etc/localtime", "EDT"])
def test_invalid_explicit_timezone_fails(
    tmp_path: Path, candidate: str
) -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._acquire_timezone_identity(
            {"TZ": candidate},
            localtime_path=tmp_path / "missing-localtime",
            timezone_path=tmp_path / "missing-timezone",
            zoneinfo_root=ZONEINFO_ROOT,
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID)


def test_localtime_zoneinfo_symlink_is_accepted(tmp_path: Path) -> None:
    localtime = tmp_path / "localtime"
    localtime.symlink_to(ZONEINFO_ROOT / "UTC")
    result = acquisition._acquire_timezone_identity(
        {},
        localtime_path=localtime,
        timezone_path=tmp_path / "missing-timezone",
        zoneinfo_root=ZONEINFO_ROOT,
    )
    assert result == "Etc/UTC"


def test_matching_localtime_and_timezone_are_accepted(tmp_path: Path) -> None:
    localtime = tmp_path / "localtime"
    localtime.symlink_to(ZONEINFO_ROOT / "UTC")
    timezone = tmp_path / "timezone"
    timezone.write_text(" \tEtc/UTC\t\r\n", encoding="utf-8")
    assert acquisition._acquire_timezone_identity(
        {},
        localtime_path=localtime,
        timezone_path=timezone,
        zoneinfo_root=ZONEINFO_ROOT,
    ) == "Etc/UTC"


def test_mismatching_localtime_and_timezone_fail(tmp_path: Path) -> None:
    localtime = tmp_path / "localtime"
    localtime.symlink_to(ZONEINFO_ROOT / "UTC")
    timezone = tmp_path / "timezone"
    timezone.write_text("America/New_York\n", encoding="utf-8")
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._acquire_timezone_identity(
            {},
            localtime_path=localtime,
            timezone_path=timezone,
            zoneinfo_root=ZONEINFO_ROOT,
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID)


def test_regular_localtime_exact_zonefile_bytes_are_accepted(
    tmp_path: Path,
) -> None:
    localtime = tmp_path / "localtime"
    localtime.write_bytes((ZONEINFO_ROOT / "UTC").read_bytes())
    timezone = tmp_path / "timezone"
    timezone.write_text("UTC\n", encoding="utf-8")
    assert acquisition._acquire_timezone_identity(
        {},
        localtime_path=localtime,
        timezone_path=timezone,
        zoneinfo_root=ZONEINFO_ROOT,
    ) == "UTC"


def test_regular_localtime_byte_mismatch_fails(tmp_path: Path) -> None:
    localtime = tmp_path / "localtime"
    localtime.write_bytes(b"not a zonefile")
    timezone = tmp_path / "timezone"
    timezone.write_text("UTC\n", encoding="utf-8")
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._acquire_timezone_identity(
            {},
            localtime_path=localtime,
            timezone_path=timezone,
            zoneinfo_root=ZONEINFO_ROOT,
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID)


def test_abbreviation_only_timezone_information_fails(tmp_path: Path) -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        acquisition._acquire_timezone_identity(
            {},
            localtime_path=tmp_path / "missing-localtime",
            timezone_path=tmp_path / "missing-timezone",
            zoneinfo_root=ZONEINFO_ROOT,
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID)


def test_os_runtime_aggregate_is_exact() -> None:
    assert construct_os_runtime_identity(
        "Linux", "ubuntu-24.04", "6.17.0-35-generic", "glibc-2.39"
    ) == (
        "system-Linux+release-ubuntu-24.04"
        "+kernel-6.17.0-35-generic+libc-glibc-2.39"
    )


@pytest.mark.parametrize(
    "component",
    ["Ubuntu 24.04", "Ubuntu/24.04", "Ubuntu+24.04"],
)
def test_os_runtime_aggregate_rejects_unrepresentable_component(
    component: str,
) -> None:
    with pytest.raises(ReleaseAcquisitionError) as error:
        construct_os_runtime_identity(
            "Linux", component, "6.17.0-35-generic", "glibc-2.39"
        )
    assert_error(error, AcquisitionErrorCode.ACQUISITION_OS_INVALID)


def test_release_build_consistency_accepts_matching_candidate() -> None:
    facts = make_runtime_facts()
    candidate = candidate_build(facts)
    before = deepcopy(candidate)
    assert validate_release_build_consistency(candidate, facts) == ()
    assert candidate == before


def test_release_build_consistency_findings_are_deterministic() -> None:
    facts = make_runtime_facts()
    candidate = candidate_build(facts)
    candidate["python_version"] = "3.11.0"
    candidate["timezone_identity"] = "UTC"
    first = validate_release_build_consistency(candidate, facts)
    second = validate_release_build_consistency(deepcopy(candidate), facts)
    assert first == second
    assert [finding.field_path for finding in first] == sorted(
        finding.field_path for finding in first
    )


def test_release_build_consistency_detects_component_aggregate_mismatch() -> None:
    facts = make_runtime_facts()
    candidate = candidate_build(facts)
    candidate["os_runtime_identity"] = (
        "system-Linux+release-ubuntu-24.04"
        "+kernel-6.17.0-35-generic+libc-musl-1.2"
    )
    findings = validate_release_build_consistency(candidate, facts)
    assert any(
        finding.field_path == "/os_runtime_identity"
        for finding in findings
    )


def test_findings_and_runtime_results_are_immutable() -> None:
    finding = ReleaseAcquisitionFinding(
        AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
        "message",
        "/field",
    )
    with pytest.raises(FrozenInstanceError):
        finding.message = "changed"  # type: ignore[misc]
    facts = make_runtime_facts()
    with pytest.raises(FrozenInstanceError):
        facts.python_version = "changed"  # type: ignore[misc]


def test_current_development_venv_acquisition_is_bounded_and_read_only() -> None:
    before = subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--porcelain=v1"],
    )
    facts = acquire_runtime_environment(
        PYTHON,
        environment_mode="DEVELOPMENT_TOOLING",
        environment_reference="env:local-stage12e2-test",
    )
    assert facts.python_implementation
    assert facts.python_version.count(".") == 2
    assert facts.os_system == "Linux"
    assert facts.os_runtime_identity == construct_os_runtime_identity(
        facts.os_system,
        facts.os_release_identity,
        facts.kernel_release,
        facts.libc_identity,
    )
    assert subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--porcelain=v1"],
    ) == before


def test_production_module_has_only_approved_io_boundaries() -> None:
    path = ROOT / "src/frontier_agent_containment/release_acquisition.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {
                    "write_bytes",
                    "write_text",
                    "mkdir",
                    "touch",
                    "unlink",
                    "rename",
                    "replace",
                }
            for keyword in node.keywords:
                if keyword.arg == "shell":
                    assert isinstance(keyword.value, ast.Constant)
                    assert keyword.value.value is False
    assert imported_roots.isdisjoint(
        {"requests", "httpx", "socket", "urllib3"}
    )
    assert "release-integrity-profile-v0.1.md" not in source
    assert "build_artifact_manifest" not in source
    assert "build_reproducibility_manifest" not in source
    assert "assemble_release" not in source
    assert "create_release_manifest" not in source
