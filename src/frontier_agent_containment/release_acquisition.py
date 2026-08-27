"""Read-only local release acquisition primitives for Stage 12E-2.

The functions in this module acquire bounded local Git, governing-document,
dependency, and runtime facts.  They do not assemble manifests or Release
Build Records, mutate repositories or environments, install packages, access
the network, execute scientific artifacts, or establish authenticity,
hermeticity, scientific validity, containment, or security.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import importlib.metadata as importlib_metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
from types import MappingProxyType
from typing import Any, Final, NoReturn, TypeAlias
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from frontier_agent_containment.integrity import forensic_sha256_bytes

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 import boundary
    tomllib = None  # type: ignore[assignment]

try:
    import packaging as _packaging
    from packaging.markers import Marker as _PackagingMarker
    from packaging.requirements import (
        InvalidRequirement as _InvalidRequirement,
    )
    from packaging.requirements import Requirement as _PackagingRequirement
    from packaging.utils import canonicalize_name as _canonicalize_name
    from packaging.version import InvalidVersion as _InvalidVersion
    from packaging.version import Version as _PackagingVersion
except ImportError:  # pragma: no cover - exercised through an injected gate
    _packaging = None  # type: ignore[assignment]
    _PackagingMarker = None  # type: ignore[assignment,misc]
    _InvalidRequirement = Exception  # type: ignore[assignment,misc]
    _PackagingRequirement = None  # type: ignore[assignment,misc]
    _canonicalize_name = None  # type: ignore[assignment]
    _InvalidVersion = Exception  # type: ignore[assignment,misc]
    _PackagingVersion = None  # type: ignore[assignment,misc]


PathInput: TypeAlias = str | os.PathLike[str]
JsonObject: TypeAlias = Mapping[str, Any]

PACKAGING_TOOLING_VERSION: Final = "24.0"
FULL_TRANSITIVE_RUNTIME: Final = "FULL_TRANSITIVE_RUNTIME"

_SOURCE_RELEASE_TAG_PATTERN: Final = re.compile(
    r"^research-release-(?:development|instrument-validation|pilot|confirmatory)"
    r"-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$"
)
_TAG_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_RELATIVE_PATH_PATTERN: Final = re.compile(
    r"^(?!/)(?![A-Za-z]:[\\/])(?!.*(?:^|/)\.\.(?:/|$))(?!.*\\)"
    r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$"
)
_OS_COMPONENT_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_BOUNDED_IDENTITY_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
_ENVIRONMENT_ID_PATTERN: Final = re.compile(
    r"^env:[a-z0-9][a-z0-9._-]*$"
)
_PYTHON_VERSION_PATTERN: Final = re.compile(
    r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$"
)
_MACHINE_IDENTIFIER_PATTERN: Final = re.compile(
    r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$"
)
_CONCRETE_VERSION_PATTERN: Final = re.compile(
    r"^(?!(?:latest|current|UNAVAILABLE|NOT_REPORTED)$)"
    r"(?!.*(?:>=|<=|~=|\^|\*|>|<|=|\s))"
    r"[0-9A-Za-z][0-9A-Za-z._+-]*$"
)
_DISTRIBUTION_FILENAME_PATTERN: Final = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._+-]*$"
)
_SHA256_HEX_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
_OS_RELEASE_KEY_PATTERN: Final = re.compile(r"^[A-Z][A-Z0-9_]*$")
_OS_RUNTIME_PATTERN: Final = re.compile(
    r"^system-[A-Za-z0-9][A-Za-z0-9._-]*"
    r"\+release-[A-Za-z0-9][A-Za-z0-9._-]*"
    r"\+kernel-[A-Za-z0-9][A-Za-z0-9._-]*"
    r"\+libc-[A-Za-z0-9][A-Za-z0-9._-]*$"
)
_LOCALE_CATEGORIES: Final = (
    "LC_COLLATE",
    "LC_CTYPE",
    "LC_MESSAGES",
    "LC_MONETARY",
    "LC_NUMERIC",
    "LC_TIME",
)
_ALLOWED_GIT_COMMANDS: Final = frozenset(
    {"cat-file", "rev-parse", "show", "status"}
)
_OBJECT_FORMATS: Final = {"sha1": "SHA-1", "sha256": "SHA-256"}


class AcquisitionErrorCode(str, Enum):
    """Bounded Stage 12E-2 acquisition finding codes."""

    ACQUISITION_GIT_INVALID = "ACQUISITION_GIT_INVALID"
    ACQUISITION_GOVERNING_DOCUMENT_INVALID = (
        "ACQUISITION_GOVERNING_DOCUMENT_INVALID"
    )
    ACQUISITION_DEPENDENCY_INVALID = "ACQUISITION_DEPENDENCY_INVALID"
    ACQUISITION_DEPENDENCY_CONFLICT = "ACQUISITION_DEPENDENCY_CONFLICT"
    ACQUISITION_DISTRIBUTION_PROVENANCE_UNAVAILABLE = (
        "ACQUISITION_DISTRIBUTION_PROVENANCE_UNAVAILABLE"
    )
    ACQUISITION_RUNTIME_INVALID = "ACQUISITION_RUNTIME_INVALID"
    ACQUISITION_OS_INVALID = "ACQUISITION_OS_INVALID"
    ACQUISITION_LOCALE_INVALID = "ACQUISITION_LOCALE_INVALID"
    ACQUISITION_TIMEZONE_INVALID = "ACQUISITION_TIMEZONE_INVALID"
    ACQUISITION_CONSISTENCY_INVALID = "ACQUISITION_CONSISTENCY_INVALID"
    ACQUISITION_TOOLING_INVALID = "ACQUISITION_TOOLING_INVALID"


@dataclass(frozen=True, slots=True)
class ReleaseAcquisitionFinding:
    """One immutable, deterministically ordered acquisition finding."""

    code: AcquisitionErrorCode
    message: str
    field_path: str
    document_id: str | None = None
    dependency_name: str | None = None
    source: str | None = None


class ReleaseAcquisitionError(ValueError):
    """Fail-closed aggregate exception for required acquisition facts."""

    def __init__(self, findings: Sequence[ReleaseAcquisitionFinding]) -> None:
        self.findings = _sorted_findings(findings)
        first = self.findings[0].code.value if self.findings else "UNKNOWN"
        super().__init__(
            f"release acquisition failed with {len(self.findings)} "
            f"finding(s); first={first}"
        )


@dataclass(frozen=True, slots=True)
class GoverningDocumentRegistryEntry:
    """One immutable projection of a frozen governing-document record."""

    document_id: str
    document_version: str
    repository_path: str
    frozen_tag_identity: str


GOVERNING_DOCUMENT_REGISTRY_V0_1: Final = (
    GoverningDocumentRegistryEntry(
        "research-contract",
        "v0.1",
        "docs/research-contract-v0.1.md",
        "research-contract-v0.1",
    ),
    GoverningDocumentRegistryEntry(
        "threat-scenario-spec",
        "v0.1",
        "docs/threat-scenario-spec-v0.1.md",
        "threat-scenario-spec-v0.1",
    ),
    GoverningDocumentRegistryEntry(
        "control-architecture-spec",
        "v0.1",
        "docs/control-architecture-spec-v0.1.md",
        "control-architecture-spec-v0.1",
    ),
    GoverningDocumentRegistryEntry(
        "evidence-spec",
        "v0.1",
        "docs/evidence-spec-v0.1.md",
        "evidence-spec-v0.1",
    ),
    GoverningDocumentRegistryEntry(
        "instrument-validation-spec",
        "v0.1",
        "docs/instrument-validation-spec-v0.1.md",
        "instrument-validation-spec-v0.1",
    ),
    GoverningDocumentRegistryEntry(
        "statistical-analysis-plan",
        "v0.1",
        "docs/statistical-analysis-plan-v0.1.md",
        "statistical-analysis-plan-v0.1",
    ),
    GoverningDocumentRegistryEntry(
        "implementation-contract",
        "v0.1",
        "docs/implementation-contract-v0.1.md",
        "implementation-contract-v0.1",
    ),
    GoverningDocumentRegistryEntry(
        "integrity-reproducibility-spec",
        "v0.1",
        "docs/integrity-reproducibility-spec-v0.1.md",
        "integrity-reproducibility-spec-v0.1",
    ),
    GoverningDocumentRegistryEntry(
        "integrity-reproducibility-clarification",
        "v0.1",
        "docs/integrity-reproducibility-clarification-v0.1.md",
        "integrity-reproducibility-clarification-v0.1",
    ),
)


@dataclass(frozen=True, slots=True)
class GitProvenance:
    """Locally acquired facts for one explicit annotated source-release tag."""

    repository_object_format: str
    repository_commit_sha: str
    repository_tree_sha: str
    release_tag_identity: str
    release_tag_object_sha: str
    release_tag_target_commit_sha: str
    repository_clean: bool


@dataclass(frozen=True, slots=True)
class GoverningDocumentProvenance:
    """Local historical provenance for one exact-byte governing document."""

    document_id: str
    document_version: str
    frozen_tag_identity: str
    frozen_tag_object_sha: str
    frozen_tag_target_commit_sha: str
    exact_byte_content_digest: str


@dataclass(frozen=True, slots=True)
class AcquiredGoverningDocument:
    """One acquired immutable governing-document byte/provenance pair."""

    exact_bytes: bytes
    provenance: GoverningDocumentProvenance


@dataclass(frozen=True, slots=True)
class GoverningDocumentAcquisition:
    """Exact governing bytes and provenance in frozen registry order."""

    documents: tuple[AcquiredGoverningDocument, ...]

    @property
    def governing_document_bytes_by_id(self) -> Mapping[str, bytes]:
        """Return an immutable Stage 12D byte mapping."""

        return MappingProxyType(
            {
                item.provenance.document_id: item.exact_bytes
                for item in self.documents
            }
        )

    @property
    def governing_document_provenance_by_id(
        self,
    ) -> Mapping[str, Mapping[str, str]]:
        """Return immutable Stage 12D provenance mappings."""

        return MappingProxyType(
            {
                item.provenance.document_id: MappingProxyType(
                    {
                        "document_version": item.provenance.document_version,
                        "frozen_tag_identity": (
                            item.provenance.frozen_tag_identity
                        ),
                    }
                )
                for item in self.documents
            }
        )


@dataclass(frozen=True, slots=True)
class DistributionArtifactProvenance:
    """Observed metadata binding an install record to an original archive."""

    distribution_filename: str
    distribution_digest: str
    source: str


@dataclass(frozen=True, slots=True)
class ResolvedDependency:
    """One exact emitted distribution identity in the runtime closure."""

    name: str
    version: str
    requires_dist: tuple[str, ...]
    provides_extra: tuple[str, ...]
    distribution_provenance: DistributionArtifactProvenance | None = None


@dataclass(frozen=True, slots=True)
class RuntimeDependencyClosure:
    """Deterministically ordered scientific runtime dependency closure."""

    dependencies: tuple[ResolvedDependency, ...]
    findings: tuple[ReleaseAcquisitionFinding, ...]
    dependency_scope: str = FULL_TRANSITIVE_RUNTIME

    @property
    def resolved_dependencies(self) -> tuple[Mapping[str, str], ...]:
        """Return immutable records directly consumable by Stage 12D."""

        records: list[Mapping[str, str]] = []
        for dependency in self.dependencies:
            record = {
                "name": dependency.name,
                "version": dependency.version,
            }
            if dependency.distribution_provenance is not None:
                record["distribution_digest"] = (
                    dependency.distribution_provenance.distribution_digest
                )
            records.append(MappingProxyType(record))
        return tuple(records)


@dataclass(frozen=True, slots=True)
class RuntimeEnvironmentFacts:
    """Immutable acquired selected-interpreter and host runtime facts."""

    python_executable: str
    venv_root: str
    python_implementation: str
    python_version: str
    python_build_string: str
    os_system: str
    os_release_identity: str
    kernel_release: str
    libc_identity: str
    architecture: str
    os_runtime_identity: str
    locale_identity: str
    timezone_identity: str
    environment_reference: str
    environment_mode: str
    system_site_packages_enabled: bool
    user_site_packages_enabled: bool


@dataclass(frozen=True, slots=True)
class _InstalledDistribution:
    name: str
    version: str
    requires_dist: tuple[str, ...] = ()
    provides_extra: tuple[str, ...] = ()
    direct_url_text: str | None = None
    origin: str | None = None
    record_present: bool = False


def acquire_git_provenance(
    repository: PathInput,
    source_release_tag_identity: str,
) -> GitProvenance:
    """Acquire local Git facts for one caller-selected Source Release Tag."""

    repo = _repository_path(repository)
    _validate_source_release_tag(source_release_tag_identity)
    object_format = _git_object_format(repo)
    tag_object, target_commit = _tag_object_and_commit(
        repo,
        source_release_tag_identity,
        code=AcquisitionErrorCode.ACQUISITION_GIT_INVALID,
        field_path="/release_tag_identity",
    )
    tree = _git_text(
        repo,
        ["rev-parse", "--verify", f"{target_commit}^{{tree}}"],
        code=AcquisitionErrorCode.ACQUISITION_GIT_INVALID,
        field_path="/repository_tree_sha",
    )
    status = _git_bytes(
        repo,
        ["status", "--porcelain=v1", "--untracked-files=all"],
        code=AcquisitionErrorCode.ACQUISITION_GIT_INVALID,
        field_path="/repository_clean",
    )
    return GitProvenance(
        repository_object_format=object_format,
        repository_commit_sha=target_commit,
        repository_tree_sha=tree,
        release_tag_identity=source_release_tag_identity,
        release_tag_object_sha=tag_object,
        release_tag_target_commit_sha=target_commit,
        repository_clean=status == b"",
    )


def acquire_governing_documents(
    repository: PathInput,
    source_release_tag_identity: str,
    registry: Sequence[GoverningDocumentRegistryEntry] = (
        GOVERNING_DOCUMENT_REGISTRY_V0_1
    ),
) -> GoverningDocumentAcquisition:
    """Acquire exact historical/source bytes using only the supplied registry."""

    repo = _repository_path(repository)
    _validate_source_release_tag(source_release_tag_identity)
    _tag_object_and_commit(
        repo,
        source_release_tag_identity,
        code=AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
        field_path="/source_release_tag_identity",
    )
    entries = tuple(registry)
    identifiers = [entry.document_id for entry in entries]
    if len(set(identifiers)) != len(identifiers):
        _raise(
            AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
            "governing-document registry contains duplicate document_id values",
            "/governing_document_registry",
        )

    acquired: list[AcquiredGoverningDocument] = []
    for index, entry in enumerate(entries):
        base = f"/governing_documents/{index}"
        _validate_registry_entry(entry, base)
        tag_object, tag_target = _tag_object_and_commit(
            repo,
            entry.frozen_tag_identity,
            code=(
                AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID
            ),
            field_path=f"{base}/frozen_tag_identity",
            document_id=entry.document_id,
        )
        historical = _git_blob_at(
            repo,
            entry.frozen_tag_identity,
            entry.repository_path,
            field_path=f"{base}/historical_bytes",
            document_id=entry.document_id,
        )
        source = _git_blob_at(
            repo,
            source_release_tag_identity,
            entry.repository_path,
            field_path=f"{base}/source_release_bytes",
            document_id=entry.document_id,
        )
        if source != historical:
            _raise(
                AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
                "source-release governing bytes differ from historical frozen bytes",
                f"{base}/source_release_bytes",
                document_id=entry.document_id,
                source=entry.repository_path,
            )
        acquired.append(
            AcquiredGoverningDocument(
                exact_bytes=source,
                provenance=GoverningDocumentProvenance(
                    document_id=entry.document_id,
                    document_version=entry.document_version,
                    frozen_tag_identity=entry.frozen_tag_identity,
                    frozen_tag_object_sha=tag_object,
                    frozen_tag_target_commit_sha=tag_target,
                    exact_byte_content_digest=forensic_sha256_bytes(source),
                ),
            )
        )
    return GoverningDocumentAcquisition(tuple(acquired))


def acquire_runtime_dependency_closure(
    repository: PathInput,
    source_release_tag_identity: str,
    python_executable: PathInput,
    enabled_dependency_extras: Sequence[str] = (),
) -> RuntimeDependencyClosure:
    """Acquire the exact scientific FULL_TRANSITIVE_RUNTIME closure."""

    _require_packaging_tooling()
    repo = _repository_path(repository)
    _validate_source_release_tag(source_release_tag_identity)
    _tag_object_and_commit(
        repo,
        source_release_tag_identity,
        code=AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
        field_path="/source_release_tag_identity",
    )
    project = _tagged_project_metadata(repo, source_release_tag_identity)
    payload = _probe_interpreter(
        python_executable,
        include_distributions=True,
        code=AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
        field_path="/python_executable",
    )
    inventory, marker_environment = _inventory_from_probe(payload)
    return _resolve_dependency_closure(
        project,
        inventory,
        marker_environment,
        enabled_dependency_extras,
    )


def acquire_runtime_environment(
    python_executable: PathInput,
    *,
    environment_mode: str,
    environment_reference: str,
    environment: Mapping[str, str] | None = None,
) -> RuntimeEnvironmentFacts:
    """Acquire immutable PEP 405 selected-runtime facts without assembly."""

    if environment_mode not in {"DEVELOPMENT_TOOLING", "CONTROLLED_RUNTIME"}:
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "environment_mode must be DEVELOPMENT_TOOLING or CONTROLLED_RUNTIME",
            "/environment_mode",
        )
    _validate_environment_reference(environment_reference)
    selected_environment = _copy_environment(environment)
    payload = _probe_interpreter(
        python_executable,
        environment=selected_environment if environment is not None else None,
        include_distributions=False,
        code=AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
        field_path="/python_executable",
    )

    prefix = _required_probe_string(payload, "prefix", "/venv_root")
    base_prefix = _required_probe_string(
        payload, "base_prefix", "/venv_root"
    )
    executable = _required_probe_string(
        payload, "executable", "/python_executable"
    )
    if prefix == base_prefix:
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "selected interpreter is not running in a PEP 405 virtual environment",
            "/python_executable",
            source=executable,
        )

    venv_root = Path(prefix)
    pyvenv_path = venv_root / "pyvenv.cfg"
    system_site = _read_system_site_packages(pyvenv_path)
    user_site = _derive_user_site_enabled(
        payload.get("enable_user_site"),
        payload.get("no_user_site"),
    )
    if environment_mode == "CONTROLLED_RUNTIME" and (
        system_site or user_site
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "CONTROLLED_RUNTIME requires system-site and user-site disabled",
            "/environment_mode",
        )

    implementation = _required_probe_string(
        payload, "python_implementation", "/python_implementation"
    )
    _validate_bounded_identity(
        implementation,
        "/python_implementation",
        AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
    )
    python_version = _required_probe_string(
        payload, "python_version", "/python_version"
    )
    if _PYTHON_VERSION_PATTERN.fullmatch(python_version) is None:
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "python_version is not exact MAJOR.MINOR.PATCH",
            "/python_version",
        )
    build_string = _required_probe_string(
        payload, "python_build_string", "/python_build_string"
    )
    if (
        len(build_string) > 1000
        or any(
            ord(character) < 32 or ord(character) == 127
            for character in build_string
        )
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "python_build_string violates the frozen bounded metadata contract",
            "/python_build_string",
        )

    os_system = _required_probe_string(payload, "os_system", "/os_system")
    _validate_os_component(
        os_system, "/os_system", AcquisitionErrorCode.ACQUISITION_OS_INVALID
    )
    if os_system != "Linux":
        _raise(
            AcquisitionErrorCode.ACQUISITION_OS_INVALID,
            "Stage 12E v0.1 defines only the Linux OS-release backend",
            "/os_system",
        )
    os_release = _acquire_os_release_identity()
    kernel = _required_probe_string(
        payload, "kernel_release", "/kernel_release"
    )
    _validate_os_component(
        kernel,
        "/kernel_release",
        AcquisitionErrorCode.ACQUISITION_OS_INVALID,
    )
    libc_pair = payload.get("libc")
    if (
        not isinstance(libc_pair, list)
        or len(libc_pair) != 2
        or not all(isinstance(value, str) for value in libc_pair)
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_OS_INVALID,
            "platform.libc_ver() probe did not return two strings",
            "/libc_identity",
        )
    libc_identity = _serialize_libc_identity(libc_pair[0], libc_pair[1])
    architecture = _required_probe_string(
        payload, "architecture", "/architecture"
    )
    _validate_bounded_identity(
        architecture,
        "/architecture",
        AcquisitionErrorCode.ACQUISITION_OS_INVALID,
    )

    locale_identity = _acquire_locale_identity(selected_environment)
    timezone_identity = _acquire_timezone_identity(selected_environment)
    os_runtime_identity = construct_os_runtime_identity(
        os_system,
        os_release,
        kernel,
        libc_identity,
    )

    return RuntimeEnvironmentFacts(
        python_executable=executable,
        venv_root=prefix,
        python_implementation=implementation,
        python_version=python_version,
        python_build_string=build_string,
        os_system=os_system,
        os_release_identity=os_release,
        kernel_release=kernel,
        libc_identity=libc_identity,
        architecture=architecture,
        os_runtime_identity=os_runtime_identity,
        locale_identity=locale_identity,
        timezone_identity=timezone_identity,
        environment_reference=environment_reference,
        environment_mode=environment_mode,
        system_site_packages_enabled=system_site,
        user_site_packages_enabled=user_site,
    )


def construct_os_runtime_identity(
    os_system: str,
    os_release_identity: str,
    kernel_release: str,
    libc_identity: str,
) -> str:
    """Construct the exact frozen aggregate without normalization."""

    fields = (
        ("os_system", os_system),
        ("os_release_identity", os_release_identity),
        ("kernel_release", kernel_release),
        ("libc_identity", libc_identity),
    )
    for field, value in fields:
        _validate_os_component(
            value,
            f"/{field}",
            AcquisitionErrorCode.ACQUISITION_OS_INVALID,
        )
    identity = (
        f"system-{os_system}"
        f"+release-{os_release_identity}"
        f"+kernel-{kernel_release}"
        f"+libc-{libc_identity}"
    )
    if len(identity) > 240 or _OS_RUNTIME_PATTERN.fullmatch(identity) is None:
        _raise(
            AcquisitionErrorCode.ACQUISITION_OS_INVALID,
            "os_runtime_identity violates the frozen aggregate contract",
            "/os_runtime_identity",
        )
    return identity


def validate_release_build_consistency(
    candidate: Mapping[str, Any],
    acquired: RuntimeEnvironmentFacts,
) -> tuple[ReleaseAcquisitionFinding, ...]:
    """Purely compare acquisition-derived build fields without assembly."""

    expected = {
        "python_implementation": acquired.python_implementation,
        "python_version": acquired.python_version,
        "python_build_string": acquired.python_build_string,
        "os_system": acquired.os_system,
        "os_release_identity": acquired.os_release_identity,
        "kernel_release": acquired.kernel_release,
        "libc_identity": acquired.libc_identity,
        "architecture": acquired.architecture,
        "os_runtime_identity": acquired.os_runtime_identity,
        "locale_identity": acquired.locale_identity,
        "timezone_identity": acquired.timezone_identity,
        "environment_reference": acquired.environment_reference,
        "environment_mode": acquired.environment_mode,
        "system_site_packages_enabled": (
            acquired.system_site_packages_enabled
        ),
        "user_site_packages_enabled": acquired.user_site_packages_enabled,
    }
    findings: list[ReleaseAcquisitionFinding] = []
    for field in sorted(expected):
        if candidate.get(field) != expected[field]:
            findings.append(
                ReleaseAcquisitionFinding(
                    code=(
                        AcquisitionErrorCode.ACQUISITION_CONSISTENCY_INVALID
                    ),
                    message=(
                        f"candidate {field} does not match the acquired local fact"
                    ),
                    field_path=f"/{field}",
                )
            )

    component_fields = (
        "os_system",
        "os_release_identity",
        "kernel_release",
        "libc_identity",
    )
    if all(isinstance(candidate.get(field), str) for field in component_fields):
        try:
            aggregate = construct_os_runtime_identity(
                candidate["os_system"],
                candidate["os_release_identity"],
                candidate["kernel_release"],
                candidate["libc_identity"],
            )
        except ReleaseAcquisitionError:
            aggregate = None
        if aggregate is None or candidate.get("os_runtime_identity") != aggregate:
            finding = ReleaseAcquisitionFinding(
                code=AcquisitionErrorCode.ACQUISITION_CONSISTENCY_INVALID,
                message=(
                    "candidate os_runtime_identity does not equal its exact components"
                ),
                field_path="/os_runtime_identity",
            )
            if finding not in findings:
                findings.append(finding)
    return _sorted_findings(findings)


def _repository_path(repository: PathInput) -> Path:
    path = Path(repository)
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        _raise(
            AcquisitionErrorCode.ACQUISITION_GIT_INVALID,
            f"repository path is unavailable: {error}",
            "/repository",
            source=os.fspath(path),
        )
    if not resolved.is_dir():
        _raise(
            AcquisitionErrorCode.ACQUISITION_GIT_INVALID,
            "repository path is not a directory",
            "/repository",
            source=os.fspath(path),
        )
    return resolved


def _validate_source_release_tag(tag: str) -> None:
    if (
        not isinstance(tag, str)
        or _SOURCE_RELEASE_TAG_PATTERN.fullmatch(tag) is None
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_GIT_INVALID,
            "source release tag does not match the frozen naming contract",
            "/source_release_tag_identity",
        )


def _git_object_format(repository: Path) -> str:
    raw = _git_text(
        repository,
        ["rev-parse", "--show-object-format"],
        code=AcquisitionErrorCode.ACQUISITION_GIT_INVALID,
        field_path="/repository_object_format",
    )
    mapped = _OBJECT_FORMATS.get(raw)
    if mapped is None:
        _raise(
            AcquisitionErrorCode.ACQUISITION_GIT_INVALID,
            f"unsupported Git object format: {raw}",
            "/repository_object_format",
        )
    return mapped


def _tag_object_and_commit(
    repository: Path,
    tag: str,
    *,
    code: AcquisitionErrorCode,
    field_path: str,
    document_id: str | None = None,
) -> tuple[str, str]:
    if _TAG_PATTERN.fullmatch(tag) is None:
        _raise(
            code,
            "tag identity violates the frozen bounded tag grammar",
            field_path,
            document_id=document_id,
        )
    ref = f"refs/tags/{tag}"
    tag_object = _git_text(
        repository,
        ["rev-parse", "--verify", ref],
        code=code,
        field_path=field_path,
        document_id=document_id,
    )
    object_type = _git_text(
        repository,
        ["cat-file", "-t", tag_object],
        code=code,
        field_path=field_path,
        document_id=document_id,
    )
    if object_type != "tag":
        _raise(
            code,
            "required tag is missing or lightweight rather than annotated",
            field_path,
            document_id=document_id,
            source=tag,
        )
    commit = _git_text(
        repository,
        ["rev-parse", "--verify", f"{ref}^{{commit}}"],
        code=code,
        field_path=field_path,
        document_id=document_id,
    )
    commit_type = _git_text(
        repository,
        ["cat-file", "-t", commit],
        code=code,
        field_path=field_path,
        document_id=document_id,
    )
    if commit_type != "commit":
        _raise(
            code,
            "annotated tag does not peel to a commit",
            field_path,
            document_id=document_id,
            source=tag,
        )
    return tag_object, commit


def _git_blob_at(
    repository: Path,
    tag: str,
    path: str,
    *,
    field_path: str,
    document_id: str,
) -> bytes:
    object_id = _git_text(
        repository,
        ["rev-parse", "--verify", f"refs/tags/{tag}:{path}"],
        code=AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
        field_path=field_path,
        document_id=document_id,
    )
    object_type = _git_text(
        repository,
        ["cat-file", "-t", object_id],
        code=AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
        field_path=field_path,
        document_id=document_id,
    )
    if object_type != "blob":
        _raise(
            AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
            "registered governing path is not a Git blob",
            field_path,
            document_id=document_id,
            source=path,
        )
    return _git_bytes(
        repository,
        ["cat-file", "blob", object_id],
        code=AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
        field_path=field_path,
        document_id=document_id,
    )


def _git_text(
    repository: Path,
    arguments: Sequence[str],
    *,
    code: AcquisitionErrorCode,
    field_path: str,
    document_id: str | None = None,
) -> str:
    raw = _git_bytes(
        repository,
        arguments,
        code=code,
        field_path=field_path,
        document_id=document_id,
    )
    try:
        return raw.decode("ascii").strip()
    except UnicodeDecodeError as error:
        _raise(
            code,
            f"Git identity output was not ASCII: {error}",
            field_path,
            document_id=document_id,
        )


def _git_bytes(
    repository: Path,
    arguments: Sequence[str],
    *,
    code: AcquisitionErrorCode,
    field_path: str,
    document_id: str | None = None,
) -> bytes:
    if not arguments or arguments[0] not in _ALLOWED_GIT_COMMANDS:
        raise AssertionError("internal Git command is not read-only")
    command = ["git", "-C", os.fspath(repository), *arguments]
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        _raise(
            code,
            f"read-only Git acquisition failed: {error}",
            field_path,
            document_id=document_id,
        )
    if completed.returncode != 0:
        detail = _bounded_process_error(completed.stderr)
        _raise(
            code,
            f"read-only Git acquisition failed: {detail}",
            field_path,
            document_id=document_id,
        )
    return completed.stdout


def _validate_registry_entry(
    entry: GoverningDocumentRegistryEntry,
    field_path: str,
) -> None:
    if not isinstance(entry, GoverningDocumentRegistryEntry):
        _raise(
            AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
            "registry contains an unsupported entry value",
            field_path,
        )
    if (
        _MACHINE_IDENTIFIER_PATTERN.fullmatch(entry.document_id) is None
        or len(entry.document_id) > 128
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
            "registered document_id is not schema-representable",
            f"{field_path}/document_id",
        )
    if re.fullmatch(r"^[vV]?[0-9]+(?:\.[0-9]+)+$", entry.document_version) is None:
        _raise(
            AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
            "registered document_version is not schema-representable",
            f"{field_path}/document_version",
            document_id=entry.document_id,
        )
    if _RELATIVE_PATH_PATTERN.fullmatch(entry.repository_path) is None:
        _raise(
            AcquisitionErrorCode.ACQUISITION_GOVERNING_DOCUMENT_INVALID,
            "registered repository_path is not a safe relative path",
            f"{field_path}/repository_path",
            document_id=entry.document_id,
        )


def _tagged_project_metadata(
    repository: Path,
    source_release_tag_identity: str,
) -> Mapping[str, Any]:
    raw = _git_blob_at_project(
        repository, source_release_tag_identity, "pyproject.toml"
    )
    if tomllib is None:
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "Python tomllib is unavailable for tagged project metadata",
            "/project_metadata",
        )
    try:
        decoded = raw.decode("utf-8")
        document = tomllib.loads(decoded)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            f"tagged pyproject.toml is invalid: {error}",
            "/project_metadata",
        )
    project = document.get("project")
    if not isinstance(project, dict):
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "tagged pyproject.toml has no project table",
            "/project_metadata/project",
        )
    return project


def _git_blob_at_project(
    repository: Path,
    tag: str,
    path: str,
) -> bytes:
    object_id = _git_text(
        repository,
        ["rev-parse", "--verify", f"refs/tags/{tag}:{path}"],
        code=AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
        field_path="/project_metadata",
    )
    object_type = _git_text(
        repository,
        ["cat-file", "-t", object_id],
        code=AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
        field_path="/project_metadata",
    )
    if object_type != "blob":
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "tagged pyproject.toml is not a Git blob",
            "/project_metadata",
        )
    return _git_bytes(
        repository,
        ["cat-file", "blob", object_id],
        code=AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
        field_path="/project_metadata",
    )


def _require_packaging_tooling() -> None:
    if (
        _packaging is None
        or _PackagingRequirement is None
        or _PackagingVersion is None
        or _PackagingMarker is None
        or _canonicalize_name is None
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_TOOLING_INVALID,
            "packaging acquisition tooling is unavailable",
            "/tooling/packaging",
        )
    try:
        version = importlib_metadata.version("packaging")
    except importlib_metadata.PackageNotFoundError:
        _raise(
            AcquisitionErrorCode.ACQUISITION_TOOLING_INVALID,
            "packaging distribution metadata is unavailable",
            "/tooling/packaging",
        )
    loaded_version = getattr(_packaging, "__version__", None)
    if (
        version != PACKAGING_TOOLING_VERSION
        or loaded_version != PACKAGING_TOOLING_VERSION
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_TOOLING_INVALID,
            (
                f"packaging=={PACKAGING_TOOLING_VERSION} is required; "
                f"metadata={version}, loaded={loaded_version}"
            ),
            "/tooling/packaging",
        )


_INTERPRETER_PROBE: Final = r"""
import importlib.metadata
import json
import os
import platform
import site
import sys

implementation = sys.implementation.version
implementation_version = (
    f"{implementation.major}.{implementation.minor}.{implementation.micro}"
)
if implementation.releaselevel != "final":
    implementation_version += implementation.releaselevel[0] + str(
        implementation.serial
    )

payload = {
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "executable": sys.executable,
    "python_implementation": platform.python_implementation(),
    "python_version": platform.python_version(),
    "python_build_string": sys.version,
    "os_system": platform.system(),
    "kernel_release": platform.release(),
    "libc": list(platform.libc_ver()),
    "architecture": platform.machine(),
    "enable_user_site": site.ENABLE_USER_SITE,
    "no_user_site": sys.flags.no_user_site,
    "marker_environment": {
        "implementation_name": sys.implementation.name,
        "implementation_version": implementation_version,
        "os_name": os.name,
        "platform_machine": platform.machine(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_full_version": platform.python_version(),
        "platform_python_implementation": platform.python_implementation(),
        "python_version": ".".join(platform.python_version_tuple()[:2]),
        "sys_platform": sys.platform,
    },
}
if len(sys.argv) > 1 and sys.argv[1] == "1":
    distributions = []
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name")
        version = distribution.version
        requires = distribution.metadata.get_all("Requires-Dist") or []
        extras = distribution.metadata.get_all("Provides-Extra") or []
        direct_url = distribution.read_text("direct_url.json")
        record = distribution.read_text("RECORD")
        distributions.append(
            {
                "name": name,
                "version": version,
                "requires_dist": list(requires),
                "provides_extra": list(extras),
                "direct_url_text": direct_url,
                "origin": str(distribution.locate_file("")),
                "record_present": record is not None,
            }
        )
    payload["distributions"] = distributions
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
"""


def _explicit_python_path(python_executable: PathInput) -> Path:
    raw = Path(python_executable)
    if not raw.is_absolute() and raw.parent == Path("."):
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "python_executable must be an explicit path, not a PATH lookup",
            "/python_executable",
            source=os.fspath(raw),
        )
    candidate = raw if raw.is_absolute() else Path.cwd() / raw
    executable = candidate.absolute()
    if not executable.exists():
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "selected Python executable is unavailable",
            "/python_executable",
            source=os.fspath(raw),
        )
    if not executable.is_file() or not os.access(executable, os.X_OK):
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "selected Python path is not an executable file",
            "/python_executable",
            source=os.fspath(raw),
        )
    return executable


def _probe_interpreter(
    python_executable: PathInput,
    *,
    environment: Mapping[str, str] | None = None,
    include_distributions: bool,
    code: AcquisitionErrorCode,
    field_path: str,
) -> Mapping[str, Any]:
    try:
        executable = _explicit_python_path(python_executable)
    except ReleaseAcquisitionError as error:
        if code is AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID:
            raise
        finding = error.findings[0]
        _raise(
            code,
            finding.message,
            field_path,
            source=finding.source,
        )

    command = [
        os.fspath(executable),
        "-c",
        _INTERPRETER_PROBE,
        "1" if include_distributions else "0",
    ]
    subprocess_environment = (
        None if environment is None else dict(environment)
    )
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
            timeout=30,
            env=subprocess_environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        _raise(
            code,
            f"selected-interpreter probe failed: {error}",
            field_path,
            source=os.fspath(executable),
        )
    if completed.returncode != 0:
        _raise(
            code,
            "selected-interpreter probe failed: "
            + _bounded_process_error(completed.stderr),
            field_path,
            source=os.fspath(executable),
        )
    if len(completed.stdout) > 20_000_000:
        _raise(
            code,
            "selected-interpreter probe output exceeded the bounded limit",
            field_path,
            source=os.fspath(executable),
        )
    try:
        payload = json.loads(completed.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        _raise(
            code,
            f"selected-interpreter probe returned invalid JSON: {error}",
            field_path,
            source=os.fspath(executable),
        )
    if not isinstance(payload, dict):
        _raise(
            code,
            "selected-interpreter probe did not return an object",
            field_path,
            source=os.fspath(executable),
        )
    return payload


def _inventory_from_probe(
    payload: Mapping[str, Any],
) -> tuple[tuple[_InstalledDistribution, ...], Mapping[str, str]]:
    raw_distributions = payload.get("distributions")
    raw_environment = payload.get("marker_environment")
    if not isinstance(raw_distributions, list):
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "selected-interpreter distribution inventory is missing",
            "/dependencies",
        )
    if not isinstance(raw_environment, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in raw_environment.items()
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "selected-interpreter marker environment is malformed",
            "/marker_environment",
        )

    inventory: list[_InstalledDistribution] = []
    for index, raw in enumerate(raw_distributions):
        if not isinstance(raw, dict):
            _raise(
                AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
                "distribution inventory entry is not an object",
                f"/dependencies/{index}",
            )
        name = raw.get("name")
        version = raw.get("version")
        if not isinstance(name, str) or not name or not isinstance(version, str):
            continue
        requires = raw.get("requires_dist", [])
        extras = raw.get("provides_extra", [])
        if not isinstance(requires, list) or not all(
            isinstance(value, str) for value in requires
        ):
            _raise(
                AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
                "Requires-Dist metadata is malformed",
                f"/dependencies/{index}/requires_dist",
                dependency_name=name,
            )
        if not isinstance(extras, list) or not all(
            isinstance(value, str) for value in extras
        ):
            _raise(
                AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
                "Provides-Extra metadata is malformed",
                f"/dependencies/{index}/provides_extra",
                dependency_name=name,
            )
        direct_url = raw.get("direct_url_text")
        origin = raw.get("origin")
        record_present = raw.get("record_present", False)
        if direct_url is not None and not isinstance(direct_url, str):
            _raise(
                AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
                "direct_url.json metadata is malformed",
                f"/dependencies/{index}/direct_url",
                dependency_name=name,
            )
        if origin is not None and not isinstance(origin, str):
            origin = None
        inventory.append(
            _InstalledDistribution(
                name=name,
                version=version,
                requires_dist=tuple(requires),
                provides_extra=tuple(extras),
                direct_url_text=direct_url,
                origin=origin,
                record_present=record_present is True,
            )
        )
    return tuple(inventory), MappingProxyType(dict(raw_environment))


def _resolve_dependency_closure(
    project: Mapping[str, Any],
    inventory: Sequence[_InstalledDistribution],
    marker_environment: Mapping[str, str],
    enabled_dependency_extras: Sequence[str],
) -> RuntimeDependencyClosure:
    """Pure deterministic closure over tagged project and probed metadata."""

    _require_packaging_tooling()
    roots = project.get("dependencies")
    optional = project.get("optional-dependencies", {})
    if not isinstance(roots, list) or not all(
        isinstance(value, str) for value in roots
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "tagged project.dependencies must be an array of requirement strings",
            "/project_metadata/dependencies",
        )
    if not isinstance(optional, dict):
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "tagged project.optional-dependencies must be a table",
            "/project_metadata/optional-dependencies",
        )

    enabled = tuple(enabled_dependency_extras)
    if not all(isinstance(extra, str) for extra in enabled):
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "enabled dependency extras must be strings",
            "/enabled_dependency_extras",
        )
    if len(set(enabled)) != len(enabled):
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "enabled dependency extras contain duplicates",
            "/enabled_dependency_extras",
        )
    for extra in sorted(enabled):
        if extra not in optional:
            _raise(
                AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
                f"requested runtime extra is not declared: {extra}",
                "/enabled_dependency_extras",
                source=extra,
            )
        values = optional[extra]
        if not isinstance(values, list) or not all(
            isinstance(value, str) for value in values
        ):
            _raise(
                AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
                f"declared runtime extra is not a requirement array: {extra}",
                f"/project_metadata/optional-dependencies/{extra}",
            )

    by_resolution_key: dict[str, list[_InstalledDistribution]] = {}
    for distribution in inventory:
        key = _resolution_key(distribution.name)
        by_resolution_key.setdefault(key, []).append(distribution)

    included: dict[str, _InstalledDistribution] = {}
    active_extras: dict[str, set[str]] = {}
    processed_states: dict[str, frozenset[str]] = {}

    def include_requirement(raw: str, contexts: Sequence[str], path: str) -> None:
        requirement = _parse_requirement(raw, path)
        if not _marker_applies(
            requirement.marker, marker_environment, contexts, path
        ):
            return
        key = _resolution_key(requirement.name)
        distribution = _select_distribution(
            requirement.name, by_resolution_key.get(key, ()), path
        )
        _validate_dependency_identity(distribution, path)
        try:
            version = _PackagingVersion(distribution.version)
        except _InvalidVersion as error:
            _raise(
                AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
                f"installed dependency version is invalid: {error}",
                path,
                dependency_name=distribution.name,
            )
        if requirement.specifier and not requirement.specifier.contains(
            version, prereleases=None
        ):
            _raise(
                AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
                (
                    f"installed {distribution.name} {distribution.version} "
                    f"does not satisfy {requirement.specifier}"
                ),
                path,
                dependency_name=distribution.name,
            )
        existing = included.get(key)
        if existing is not None and (
            existing.name != distribution.name
            or existing.version != distribution.version
        ):
            _raise(
                AcquisitionErrorCode.ACQUISITION_DEPENDENCY_CONFLICT,
                "one dependency resolution key selected conflicting identities",
                path,
                dependency_name=distribution.name,
            )
        included[key] = distribution
        active_extras.setdefault(key, set()).update(requirement.extras)

    for index, raw in enumerate(sorted(roots)):
        include_requirement(
            raw,
            ("",),
            f"/project_metadata/dependencies/{index}",
        )
    for extra in sorted(enabled):
        values = optional[extra]
        for index, raw in enumerate(sorted(values)):
            include_requirement(
                raw,
                (extra,),
                (
                    f"/project_metadata/optional-dependencies/"
                    f"{extra}/{index}"
                ),
            )

    while True:
        pending = [
            key
            for key in included
            if processed_states.get(key)
            != frozenset(active_extras.get(key, set()))
        ]
        if not pending:
            break
        pending.sort(
            key=lambda key: (
                included[key].name,
                included[key].version,
            )
        )
        for key in pending:
            distribution = included[key]
            state = frozenset(active_extras.get(key, set()))
            processed_states[key] = state
            contexts = ("", *sorted(state))
            for index, raw in enumerate(sorted(distribution.requires_dist)):
                include_requirement(
                    raw,
                    contexts,
                    (
                        f"/dependencies/{distribution.name}/"
                        f"requires_dist/{index}"
                    ),
                )

    resolved: list[ResolvedDependency] = []
    findings: list[ReleaseAcquisitionFinding] = []
    for distribution in sorted(
        included.values(), key=lambda item: (item.name, item.version)
    ):
        provenance, finding = _distribution_provenance(distribution)
        if finding is not None:
            findings.append(finding)
        resolved.append(
            ResolvedDependency(
                name=distribution.name,
                version=distribution.version,
                requires_dist=tuple(sorted(distribution.requires_dist)),
                provides_extra=tuple(sorted(distribution.provides_extra)),
                distribution_provenance=provenance,
            )
        )
    return RuntimeDependencyClosure(
        dependencies=tuple(resolved),
        findings=_sorted_findings(findings),
    )


def _parse_requirement(raw: str, field_path: str) -> Any:
    try:
        return _PackagingRequirement(raw)
    except _InvalidRequirement as error:
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            f"invalid PEP 508 requirement: {error}",
            field_path,
        )


def _marker_applies(
    marker: Any,
    environment: Mapping[str, str],
    contexts: Sequence[str],
    field_path: str,
) -> bool:
    if marker is None:
        return True
    try:
        for context in contexts:
            values = dict(environment)
            values["extra"] = context
            if marker.evaluate(environment=values):
                return True
        return False
    except (KeyError, ValueError) as error:
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            f"environment marker evaluation failed: {error}",
            field_path,
        )


def _resolution_key(name: str) -> str:
    return str(_canonicalize_name(name))


def _select_distribution(
    requirement_name: str,
    candidates: Sequence[_InstalledDistribution],
    field_path: str,
) -> _InstalledDistribution:
    if not candidates:
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            f"required distribution is not installed: {requirement_name}",
            field_path,
            dependency_name=requirement_name,
        )
    unique: dict[tuple[str, str], _InstalledDistribution] = {}
    versions_by_exact_name: dict[str, set[str]] = {}
    for candidate in candidates:
        unique.setdefault((candidate.name, candidate.version), candidate)
        versions_by_exact_name.setdefault(candidate.name, set()).add(
            candidate.version
        )
    conflicts = [
        name
        for name, versions in versions_by_exact_name.items()
        if len(versions) > 1
    ]
    if conflicts:
        name = sorted(conflicts)[0]
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_CONFLICT,
            "same exact METADATA Name has multiple installed versions",
            field_path,
            dependency_name=name,
        )
    if len(unique) != 1:
        names = ", ".join(
            f"{name} {version}" for name, version in sorted(unique)
        )
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_CONFLICT,
            (
                "standards-equivalent requirement key resolves to multiple "
                f"exact METADATA identities: {names}"
            ),
            field_path,
            dependency_name=requirement_name,
        )
    return next(iter(unique.values()))


def _validate_dependency_identity(
    distribution: _InstalledDistribution,
    field_path: str,
) -> None:
    if (
        len(distribution.name) > 128
        or _MACHINE_IDENTIFIER_PATTERN.fullmatch(distribution.name) is None
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "exact METADATA Name is not representable without normalization",
            field_path,
            dependency_name=distribution.name,
        )
    if (
        len(distribution.version) > 128
        or _CONCRETE_VERSION_PATTERN.fullmatch(distribution.version) is None
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "exact installed version is not schema-representable",
            field_path,
            dependency_name=distribution.name,
        )


def _distribution_provenance(
    distribution: _InstalledDistribution,
) -> tuple[
    DistributionArtifactProvenance | None,
    ReleaseAcquisitionFinding | None,
]:
    field_path = f"/dependencies/{distribution.name}/distribution_digest"
    if distribution.direct_url_text is None:
        return None, ReleaseAcquisitionFinding(
            code=(
                AcquisitionErrorCode
                .ACQUISITION_DISTRIBUTION_PROVENANCE_UNAVAILABLE
            ),
            message="original distribution provenance is unavailable",
            field_path=field_path,
            dependency_name=distribution.name,
            source="installed metadata",
        )
    try:
        document = json.loads(distribution.direct_url_text)
    except json.JSONDecodeError as error:
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            f"direct_url.json is invalid JSON: {error}",
            field_path,
            dependency_name=distribution.name,
            source="direct_url.json",
        )
    if not isinstance(document, dict):
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "direct_url.json is not an object",
            field_path,
            dependency_name=distribution.name,
            source="direct_url.json",
        )
    url = document.get("url")
    archive = document.get("archive_info")
    if not isinstance(url, str) or not isinstance(archive, dict):
        return None, ReleaseAcquisitionFinding(
            code=(
                AcquisitionErrorCode
                .ACQUISITION_DISTRIBUTION_PROVENANCE_UNAVAILABLE
            ),
            message="direct installation record has no archive provenance",
            field_path=field_path,
            dependency_name=distribution.name,
            source="direct_url.json",
        )

    hashes: set[str] = set()
    singular = archive.get("hash")
    if isinstance(singular, str) and singular.startswith("sha256="):
        hashes.add(singular.removeprefix("sha256="))
    plural = archive.get("hashes")
    if isinstance(plural, dict) and isinstance(plural.get("sha256"), str):
        hashes.add(plural["sha256"])
    if not hashes:
        return None, ReleaseAcquisitionFinding(
            code=(
                AcquisitionErrorCode
                .ACQUISITION_DISTRIBUTION_PROVENANCE_UNAVAILABLE
            ),
            message="direct installation record has no SHA-256 archive hash",
            field_path=field_path,
            dependency_name=distribution.name,
            source="direct_url.json",
        )
    if len(hashes) != 1:
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "direct installation record contains conflicting SHA-256 hashes",
            field_path,
            dependency_name=distribution.name,
            source="direct_url.json",
        )
    digest_hex = next(iter(hashes))
    if _SHA256_HEX_PATTERN.fullmatch(digest_hex) is None:
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "direct installation record has malformed SHA-256 archive hash",
            field_path,
            dependency_name=distribution.name,
            source="direct_url.json",
        )

    parsed = urlsplit(url)
    filename = PurePosixPath(unquote(parsed.path)).name
    if (
        len(filename) > 255
        or _DISTRIBUTION_FILENAME_PATTERN.fullmatch(filename) is None
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
            "original distribution filename is not schema-representable",
            f"/dependencies/{distribution.name}/distribution_filename",
            dependency_name=distribution.name,
            source="direct_url.json",
        )

    expected = f"sha256:{digest_hex}"
    if parsed.scheme == "file" and parsed.netloc in {"", "localhost"}:
        original = Path(unquote(parsed.path))
        if original.exists():
            if not original.is_file():
                _raise(
                    AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
                    "local original distribution reference is not a file",
                    field_path,
                    dependency_name=distribution.name,
                    source="direct_url.json",
                )
            actual = forensic_sha256_bytes(original.read_bytes())
            if actual != expected:
                _raise(
                    AcquisitionErrorCode.ACQUISITION_DEPENDENCY_INVALID,
                    "local original distribution bytes do not match direct_url SHA-256",
                    field_path,
                    dependency_name=distribution.name,
                    source="direct_url.json",
                )
    return (
        DistributionArtifactProvenance(
            distribution_filename=filename,
            distribution_digest=expected,
            source="direct_url.json",
        ),
        None,
    )


def _copy_environment(
    environment: Mapping[str, str] | None,
) -> dict[str, str]:
    source = os.environ if environment is None else environment
    copied: dict[str, str] = {}
    for key, value in source.items():
        if not isinstance(key, str) or not isinstance(value, str):
            _raise(
                AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
                "runtime environment keys and values must be strings",
                "/environment",
            )
        copied[key] = value
    return copied


def _read_system_site_packages(pyvenv_path: Path) -> bool:
    try:
        text = pyvenv_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            f"PEP 405 pyvenv.cfg is unavailable: {error}",
            "/system_site_packages_enabled",
            source=os.fspath(pyvenv_path),
        )
    values: list[str] = []
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip().lower() == "include-system-site-packages":
            values.append(value.strip().lower())
    if len(values) != 1 or values[0] not in {"true", "false"}:
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "include-system-site-packages must occur once as true or false",
            "/system_site_packages_enabled",
            source=os.fspath(pyvenv_path),
        )
    return values[0] == "true"


def _derive_user_site_enabled(
    enable_user_site: Any,
    no_user_site: Any,
) -> bool:
    if enable_user_site not in {True, False, None}:
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "site.ENABLE_USER_SITE probe returned an unsupported value",
            "/user_site_packages_enabled",
        )
    if type(no_user_site) is not int or no_user_site not in {0, 1}:
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "sys.flags.no_user_site probe returned an unsupported value",
            "/user_site_packages_enabled",
        )
    if no_user_site == 1 and enable_user_site is True:
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "site.ENABLE_USER_SITE contradicts sys.flags.no_user_site",
            "/user_site_packages_enabled",
        )
    return enable_user_site is True


def _acquire_os_release_identity(
    etc_path: Path = Path("/etc/os-release"),
    usr_path: Path = Path("/usr/lib/os-release"),
) -> str:
    selected = etc_path if etc_path.exists() else usr_path
    if not selected.exists():
        _raise(
            AcquisitionErrorCode.ACQUISITION_OS_INVALID,
            "neither /etc/os-release nor /usr/lib/os-release exists",
            "/os_release_identity",
        )
    try:
        text = selected.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        _raise(
            AcquisitionErrorCode.ACQUISITION_OS_INVALID,
            f"os-release metadata is unreadable: {error}",
            "/os_release_identity",
            source=os.fspath(selected),
        )
    values = _parse_os_release(text)
    identifier = values.get("ID")
    version = values.get("VERSION_ID")
    if identifier is None or not identifier:
        _raise(
            AcquisitionErrorCode.ACQUISITION_OS_INVALID,
            "os-release ID is missing or empty",
            "/os_release_identity/ID",
            source=os.fspath(selected),
        )
    if version is None or not version:
        _raise(
            AcquisitionErrorCode.ACQUISITION_OS_INVALID,
            "os-release VERSION_ID is missing or empty",
            "/os_release_identity/VERSION_ID",
            source=os.fspath(selected),
        )
    _validate_os_component(
        identifier,
        "/os_release_identity/ID",
        AcquisitionErrorCode.ACQUISITION_OS_INVALID,
    )
    _validate_os_component(
        version,
        "/os_release_identity/VERSION_ID",
        AcquisitionErrorCode.ACQUISITION_OS_INVALID,
    )
    result = f"{identifier}-{version}"
    _validate_os_component(
        result,
        "/os_release_identity",
        AcquisitionErrorCode.ACQUISITION_OS_INVALID,
    )
    return result


def _parse_os_release(text: str) -> Mapping[str, str]:
    values: dict[str, str] = {}
    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            _raise(
                AcquisitionErrorCode.ACQUISITION_OS_INVALID,
                "malformed os-release assignment",
                f"/os_release/{number}",
            )
        key, raw_value = line.split("=", 1)
        if _OS_RELEASE_KEY_PATTERN.fullmatch(key) is None:
            _raise(
                AcquisitionErrorCode.ACQUISITION_OS_INVALID,
                "malformed os-release field name",
                f"/os_release/{number}",
            )
        try:
            lexer = shlex.shlex(raw_value, posix=True)
            lexer.whitespace_split = True
            lexer.commenters = "#"
            tokens = list(lexer)
        except ValueError as error:
            _raise(
                AcquisitionErrorCode.ACQUISITION_OS_INVALID,
                f"malformed os-release quoted value: {error}",
                f"/os_release/{number}",
            )
        if len(tokens) != 1:
            _raise(
                AcquisitionErrorCode.ACQUISITION_OS_INVALID,
                "os-release value is missing or contains unquoted whitespace",
                f"/os_release/{number}",
            )
        if key in values:
            _raise(
                AcquisitionErrorCode.ACQUISITION_OS_INVALID,
                "duplicate os-release field is ambiguous",
                f"/os_release/{key}",
            )
        values[key] = tokens[0]
    return MappingProxyType(values)


def _serialize_libc_identity(implementation: str, version: str) -> str:
    if not implementation:
        _raise(
            AcquisitionErrorCode.ACQUISITION_OS_INVALID,
            "platform.libc_ver() implementation is empty",
            "/libc_identity",
        )
    if not version:
        _raise(
            AcquisitionErrorCode.ACQUISITION_OS_INVALID,
            "platform.libc_ver() version is empty",
            "/libc_identity",
        )
    _validate_os_component(
        implementation,
        "/libc_identity/implementation",
        AcquisitionErrorCode.ACQUISITION_OS_INVALID,
    )
    _validate_os_component(
        version,
        "/libc_identity/version",
        AcquisitionErrorCode.ACQUISITION_OS_INVALID,
    )
    result = f"{implementation}-{version}"
    _validate_os_component(
        result,
        "/libc_identity",
        AcquisitionErrorCode.ACQUISITION_OS_INVALID,
    )
    return result


def _acquire_locale_identity(environment: Mapping[str, str]) -> str:
    lc_all = environment.get("LC_ALL")
    if lc_all:
        result = lc_all
    else:
        lang = environment.get("LANG")
        if not lang:
            _raise(
                AcquisitionErrorCode.ACQUISITION_LOCALE_INVALID,
                "LANG is required when LC_ALL is absent or empty",
                "/locale_identity",
            )
        effective = tuple(
            environment.get(category) or lang
            for category in _LOCALE_CATEGORIES
        )
        if len(set(effective)) != 1:
            _raise(
                AcquisitionErrorCode.ACQUISITION_LOCALE_INVALID,
                "effective locale categories are mixed",
                "/locale_identity",
            )
        result = effective[0]
    _validate_bounded_identity(
        result,
        "/locale_identity",
        AcquisitionErrorCode.ACQUISITION_LOCALE_INVALID,
    )
    return result


def _acquire_timezone_identity(
    environment: Mapping[str, str],
    *,
    localtime_path: Path = Path("/etc/localtime"),
    timezone_path: Path = Path("/etc/timezone"),
    zoneinfo_root: Path = Path("/usr/share/zoneinfo"),
) -> str:
    explicit = environment.get("TZ")
    if explicit:
        return _validate_timezone_candidate(explicit)

    symlink_identity: str | None = None
    if localtime_path.is_symlink():
        try:
            resolved_localtime = localtime_path.resolve(strict=True)
            resolved_root = zoneinfo_root.resolve(strict=True)
            relative = resolved_localtime.relative_to(resolved_root)
        except (OSError, RuntimeError, ValueError):
            symlink_identity = None
        else:
            symlink_identity = _validate_timezone_candidate(relative.as_posix())

    timezone_identity: str | None = None
    if timezone_path.exists():
        timezone_identity = _parse_timezone_file(timezone_path)

    if symlink_identity is not None:
        if (
            timezone_identity is not None
            and timezone_identity != symlink_identity
        ):
            _raise(
                AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID,
                "/etc/localtime and /etc/timezone identities differ",
                "/timezone_identity",
            )
        return symlink_identity

    if timezone_identity is not None:
        zonefile = zoneinfo_root / PurePosixPath(timezone_identity)
        try:
            local_bytes = localtime_path.read_bytes()
            zone_bytes = zonefile.read_bytes()
        except OSError as error:
            _raise(
                AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID,
                f"timezone byte-consistency check failed: {error}",
                "/timezone_identity",
            )
        if local_bytes != zone_bytes:
            _raise(
                AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID,
                "/etc/localtime bytes do not match the selected zoneinfo file",
                "/timezone_identity",
            )
        return timezone_identity

    _raise(
        AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID,
        "no authoritative IANA timezone identity is available",
        "/timezone_identity",
    )


def _parse_timezone_file(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as error:
        _raise(
            AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID,
            f"/etc/timezone is unreadable: {error}",
            "/timezone_identity",
            source=os.fspath(path),
        )
    if raw.endswith(b"\r\n"):
        raw = raw[:-2]
    elif raw.endswith((b"\n", b"\r")):
        raw = raw[:-1]
    raw = raw.strip(b" \t")
    if b"\n" in raw or b"\r" in raw:
        _raise(
            AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID,
            "/etc/timezone must contain one identity line",
            "/timezone_identity",
            source=os.fspath(path),
        )
    try:
        candidate = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        _raise(
            AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID,
            f"/etc/timezone is not valid UTF-8: {error}",
            "/timezone_identity",
            source=os.fspath(path),
        )
    return _validate_timezone_candidate(candidate)


def _validate_timezone_candidate(candidate: str) -> str:
    if (
        not candidate
        or len(candidate) > 200
        or candidate.startswith(":")
        or PurePosixPath(candidate).is_absolute()
        or any(ord(character) < 32 or ord(character) == 127 for character in candidate)
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID,
            "timezone identity is empty, path-like, or not schema-representable",
            "/timezone_identity",
        )
    try:
        ZoneInfo(candidate)
    except (ZoneInfoNotFoundError, ValueError) as error:
        _raise(
            AcquisitionErrorCode.ACQUISITION_TIMEZONE_INVALID,
            f"timezone identity is not a resolvable IANA key: {error}",
            "/timezone_identity",
        )
    return candidate


def _validate_environment_reference(value: str) -> None:
    if (
        not isinstance(value, str)
        or _ENVIRONMENT_ID_PATTERN.fullmatch(value) is None
    ):
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            "environment_reference is not a scientific environment_id",
            "/environment_reference",
        )


def _validate_os_component(
    value: str,
    field_path: str,
    code: AcquisitionErrorCode,
) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 120
        or _OS_COMPONENT_PATTERN.fullmatch(value) is None
    ):
        _raise(
            code,
            "acquired OS component is not exactly schema-representable",
            field_path,
        )


def _validate_bounded_identity(
    value: str,
    field_path: str,
    code: AcquisitionErrorCode,
) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 240
        or _BOUNDED_IDENTITY_PATTERN.fullmatch(value) is None
    ):
        _raise(
            code,
            "acquired identity is not exactly schema-representable",
            field_path,
        )


def _required_probe_string(
    payload: Mapping[str, Any],
    field: str,
    field_path: str,
) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        _raise(
            AcquisitionErrorCode.ACQUISITION_RUNTIME_INVALID,
            f"selected-interpreter probe omitted {field}",
            field_path,
        )
    return value


def _bounded_process_error(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    compact = " ".join(text.split())
    return compact[:500] or "command returned a nonzero status"


def _sorted_findings(
    findings: Sequence[ReleaseAcquisitionFinding],
) -> tuple[ReleaseAcquisitionFinding, ...]:
    return tuple(
        sorted(
            findings,
            key=lambda finding: (
                finding.code.value,
                finding.field_path,
                finding.document_id or "",
                finding.dependency_name or "",
                finding.source or "",
                finding.message,
            ),
        )
    )


def _raise(
    code: AcquisitionErrorCode,
    message: str,
    field_path: str,
    *,
    document_id: str | None = None,
    dependency_name: str | None = None,
    source: str | None = None,
) -> NoReturn:
    raise ReleaseAcquisitionError(
        (
            ReleaseAcquisitionFinding(
                code=code,
                message=message,
                field_path=field_path,
                document_id=document_id,
                dependency_name=dependency_name,
                source=source,
            ),
        )
    )


__all__ = [
    "AcquiredGoverningDocument",
    "AcquisitionErrorCode",
    "DistributionArtifactProvenance",
    "GOVERNING_DOCUMENT_REGISTRY_V0_1",
    "GitProvenance",
    "GoverningDocumentAcquisition",
    "GoverningDocumentProvenance",
    "GoverningDocumentRegistryEntry",
    "ReleaseAcquisitionError",
    "ReleaseAcquisitionFinding",
    "ResolvedDependency",
    "RuntimeDependencyClosure",
    "RuntimeEnvironmentFacts",
    "acquire_git_provenance",
    "acquire_governing_documents",
    "acquire_runtime_dependency_closure",
    "acquire_runtime_environment",
    "construct_os_runtime_identity",
    "validate_release_build_consistency",
]
