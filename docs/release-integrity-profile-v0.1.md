# Release Integrity Profile v0.1

## 1. Status and authority

This document defines the deterministic release profile used by the final
GREEN integrity and reproducibility layer. It supplements, and does not
replace or weaken:

- `integrity-reproducibility-spec-v0.1`;
- `integrity-reproducibility-clarification-v0.1`;
- the frozen Artifact Manifest and Reproducibility Manifest contracts; and
- the Stage 12D manifest-validation semantics.

Where an earlier frozen contract is narrower, that earlier rule continues to
govern. This profile defines release acquisition and assembly policy; it does
not redefine the manifest validation model.

## 2. Purpose

The profile resolves the release-policy inputs needed for deterministic local
acquisition, manifest assembly, and audit:

1. source-release and release-integrity tag semantics;
2. governing-document inventory and document-to-path authority;
3. runtime dependency scope and distribution provenance;
4. controlled execution-environment and build identity;
5. manifest creation responsibility and release layout;
6. explicit scientific artifact selection; and
7. an external Reproducibility Manifest digest anchor.

All completeness statements in this profile are bounded to an explicitly
defined profile scope.

## 3. Release phase and identifier

The release phase tokens are:

| Reproducibility Manifest phase | Release token |
| --- | --- |
| `DEVELOPMENT` | `development` |
| `INSTRUMENT_VALIDATION` | `instrument-validation` |
| `PILOT` | `pilot` |
| `CONFIRMATORY` | `confirmatory` |

A release instance is identified by its phase and `MAJOR.MINOR` release-profile
version. Its machine-safe identifier is:

```text
release:<phase-token>-v<MAJOR>.<MINOR>
```

Examples include `release:development-v0.1`, `release:pilot-v0.1`, and
`release:confirmatory-v0.1`. This is compatible with the frozen generic typed
identifier form. It is not a filesystem path.

The corresponding `release-id-token` is the identifier value after the
leading `release:`. For example, the token for `release:pilot-v0.1` is
`pilot-v0.1`.

## 4. Two-anchor release model

Each research release uses two distinct annotated Git tags.

### 4.1 Source Release Tag

The Source Release Tag has the form:

```text
research-release-<phase-token>-v<MAJOR>.<MINOR>
```

Examples are:

```text
research-release-development-v0.1
research-release-instrument-validation-v0.1
research-release-pilot-v0.1
research-release-confirmatory-v0.1
```

It identifies the exact source repository state described by the
Reproducibility Manifest. It MUST:

- be an annotated tag;
- target the exact source commit;
- identify exactly one release phase;
- never be lightweight; and
- never be moved after the release is frozen.

The Reproducibility Manifest fields `repository_commit_sha`,
`repository_tree_sha`, `release_tag_identity`, `release_tag_object_sha`, and
`release_tag_target_commit_sha` describe this Source Release Tag and its source
commit. The target commit SHA MUST equal `repository_commit_sha`.

### 4.2 Release Integrity Tag

The Release Integrity Tag has the form:

```text
research-integrity-<phase-token>-v<MAJOR>.<MINOR>
```

It is an annotated tag targeting the later integrity commit that contains the
release manifests and release-integrity metadata. It externally anchors the
Reproducibility Manifest. It is not the tag represented by the manifest's
`release_tag_*` fields.

The Release Integrity Tag MUST never be moved after freeze. No signature
requirement is introduced in v0.1.

## 5. Non-circularity and external digest anchor

The Source Release Tag exists before the final Reproducibility Manifest is
assembled, because that manifest records the source tag object, target, commit,
and tree facts. After the manifests and build metadata have been validated and
committed, the Release Integrity Tag targets the integrity commit.

The two anchors are therefore:

```text
Source Release Tag -> source commit described by the manifest
Release Integrity Tag -> integrity commit containing the manifest
```

The annotated Release Integrity Tag message MUST contain exactly one
authoritative machine-readable line of this form:

```text
reproducibility-manifest-sha256: sha256:<64-lowercase-hex>
```

The value is `canonical_sha256(complete Reproducibility Manifest JSON object)`
using the frozen RFC 8785 JCS primitive. The tag message MAY also contain
human-readable text, but it MUST NOT contain a second line with that field
name.

The external digest is not inserted into the Reproducibility Manifest. The
manifest also does not contain the integrity tag object SHA. The Artifact
Manifest likewise has no self-digest.

## 6. Release layout and Artifact Manifest locator

Release-integrity artifacts use this repository-relative layout:

```text
releases/<release-id-token>/artifact-manifest.json
releases/<release-id-token>/reproducibility-manifest.json
releases/<release-id-token>/release-build.json
```

Absolute paths and parent traversal are prohibited. The Reproducibility
Manifest's `artifact_manifest_locator` MUST equal exactly:

```text
releases/<release-id-token>/artifact-manifest.json
```

For a release assembled under this profile, the profile-defined layout and
committed release tree provide the authoritative local context supplied to
Stage 12D as `artifact_manifest_external_locator`. This comparison establishes
locator coherence in that release context. It does not turn the locator into
artifact identity or prove Git authenticity.

## 7. Governing-document registry

The following registry is the complete v0.1 governing-document scope. The
`document_id`, `document_version`, and `frozen_tag_identity` values conform to
the frozen Reproducibility Manifest governing-document record.

| `document_id` | `document_version` | `repository_path` | `frozen_tag_identity` |
| --- | --- | --- | --- |
| `research-contract` | `v0.1` | `docs/research-contract-v0.1.md` | `research-contract-v0.1` |
| `threat-scenario-spec` | `v0.1` | `docs/threat-scenario-spec-v0.1.md` | `threat-scenario-spec-v0.1` |
| `control-architecture-spec` | `v0.1` | `docs/control-architecture-spec-v0.1.md` | `control-architecture-spec-v0.1` |
| `evidence-spec` | `v0.1` | `docs/evidence-spec-v0.1.md` | `evidence-spec-v0.1` |
| `instrument-validation-spec` | `v0.1` | `docs/instrument-validation-spec-v0.1.md` | `instrument-validation-spec-v0.1` |
| `statistical-analysis-plan` | `v0.1` | `docs/statistical-analysis-plan-v0.1.md` | `statistical-analysis-plan-v0.1` |
| `implementation-contract` | `v0.1` | `docs/implementation-contract-v0.1.md` | `implementation-contract-v0.1` |
| `integrity-reproducibility-spec` | `v0.1` | `docs/integrity-reproducibility-spec-v0.1.md` | `integrity-reproducibility-spec-v0.1` |
| `integrity-reproducibility-clarification` | `v0.1` | `docs/integrity-reproducibility-clarification-v0.1.md` | `integrity-reproducibility-clarification-v0.1` |

This registry is the only authority for mapping a governing `document_id` to a
repository path. Stage 12E MUST NOT infer a path from a filename, document
title, tag name, or naming similarity, and MUST NOT embed a second hidden
mapping. An unregistered governing-document ID is a release-integrity failure.

## 8. Governing-document closure and byte acquisition

For a v0.1 release, the manifest governing-document ID set MUST equal the
active registry ID set exactly. Missing registered records and extra
unregistered records fail release integrity. This is exact closure over the
profile-defined governing scope; it does not classify every Markdown file as a
governing document.

For each registry entry, Stage 12E acquires the release copy from:

```text
<Source Release Tag>:<repository_path>
```

It also verifies the historical `frozen_tag_identity`: the tag exists, has the
form required by its historical freeze procedure, resolves to a commit, and
contains the registry path. The exact bytes at the historical tag and at the
Source Release Tag MUST agree with the manifest record's `content_digest`.
Any divergence is a release-integrity failure rather than a normalization
opportunity.

The governing-document digest is an exact-byte document content digest:

```text
SHA-256(exact supplied bytes)
```

represented as `sha256:<64 lowercase hexadecimal characters>`. There is no
JCS, JSON parsing, decoding/re-encoding, newline normalization, Unicode
normalization, or whitespace normalization. Although the frozen exact-byte
hash primitive may be reused internally, the governing document is not a
forensic or rejected input.

Git and tag facts establish local provenance coherence only; they do not
cryptographically authenticate Git history.

## 9. Authoritative dependency scope

The release dependency scope is the full transitive runtime dependency closure
starting from the project's declared runtime dependencies at the exact source
release commit.

Stage 12E MUST:

1. read direct runtime requirements from the source release's project metadata;
2. evaluate environment markers for the selected release runtime;
3. activate only extras explicitly enabled by the release profile, normally
   none;
4. recursively follow `Requires-Dist` for every included distribution; and
5. continue until the runtime closure is complete.

The authoritative resolved dependency set supplied to Stage 12D is exactly
this closure. It is not merely the direct requirements, every visible
distribution, test dependencies, build-system dependencies, or arbitrary
system/user packages.

Test-only tools such as `pytest` and build tooling such as `setuptools` are not
members merely because they are installed. A tool is included only if it is
required by the actual research runtime path. Audit/build tooling MAY be
recorded separately and MUST NOT be silently merged into the research runtime
set.

## 10. Dependency identity and versions

Dependency identity is the exact distribution `Name` obtained from
authoritative Python distribution metadata. Stage 12E introduces no package
name normalization. The exact acquired name is supplied to Stage 12D and MUST
be used in the manifest.

Within the selected closure:

- duplicate records with an identical exact Name and version collapse to one
  semantic dependency;
- the same exact Name with conflicting versions is invalid;
- each dependency MUST have one exact resolved version;
- no range, mutable alias, or compatible-version substitution is permitted in
  the final manifest; and
- a distribution Name that does not match the frozen manifest dependency-name
  grammar causes release acquisition to fail.

Names MUST NOT be lowercased, punctuation-normalized, or otherwise modified to
fit the schema. The currently observed names `jsonschema`, `attrs`,
`pyrsistent`, and `rfc8785` are representable.

Stage 12D exact-set closure remains controlling:

```text
manifest dependency Name/version set
== authoritative acquired runtime-closure Name/version set
```

## 11. Distribution artifact provenance

For PILOT and CONFIRMATORY releases, every Python dependency in the runtime
closure MUST have an original distribution artifact digest. The preferred
record is:

```text
SHA-256(original wheel bytes)
```

where that wheel is the artifact used to construct the controlled runtime.
The digest is represented using the frozen `sha256:<64 lowercase hex>` syntax.

An installed-directory hash, aggregate of `RECORD` entries, or imported-file
hash MUST NOT be substituted for an original wheel/distribution artifact
digest. If an authoritative artifact digest cannot be acquired and verified,
a PILOT or CONFIRMATORY release MUST stop before RED work.

For DEVELOPMENT and INSTRUMENT_VALIDATION releases, a missing original
distribution digest MAY be recorded as an explicit reproducibility limitation.
It is not silently treated as verified. When the manifest asserts an optional
`distribution_digest`, the authoritative resolved record supplied to Stage 12D
MUST contain the matching trusted digest.

## 12. Current development closure observation

The Stage 12E preflight observed the following four-package runtime closure in
the current development environment:

```text
jsonschema 4.10.3
attrs 23.2.0
pyrsistent 0.20.0
rfc8785 0.1.4
```

This is non-normative current-state evidence, not a permanent Pilot or
Confirmatory closure. Every release recalculates the closure from its exact
source commit and controlled runtime.

Original wheel provenance is currently verified for:

```text
rfc8785-0.1.4-py3-none-any.whl
sha256:520d690b448ecf0703691c76e1a34a24ddcd4fc5bc41d589cb7c58ec651bcd48
```

Original distribution artifacts are not currently established for the
observed `jsonschema 4.10.3`, `attrs 23.2.0`, and `pyrsistent 0.20.0` records.
They may be acquired only under a separate, narrowly bounded GREEN network
approval. Nothing is downloaded during this design stage.

## 13. Controlled research runtime

The existing `.venv --system-site-packages` is permanently classified for this
project version as a DEVELOPMENT TOOLING ENVIRONMENT. It MUST NOT be promoted
to the PILOT or CONFIRMATORY scientific runtime.

A controlled scientific runtime MUST:

- use a dedicated environment;
- have `include-system-site-packages = false`;
- disable user-site package inclusion;
- use one explicitly selected Python interpreter;
- contain the exact resolved runtime dependency closure plus only explicitly
  approved runtime tooling; and
- contain no accidental inherited system or user distributions.

A clean Python virtual environment is an acceptable v0.1 mechanism. A
container is not mandatory. This policy does not claim a virtual environment
is hermetic at the OS or kernel level.

Before PILOT or CONFIRMATORY execution, the runtime MUST be reconstructable
from an explicitly selected interpreter and exact verified dependency
artifacts with system-site and user-site inheritance disabled. If those inputs
cannot be acquired and verified, release integrity fails and RED work does not
begin.

## 14. Python and Release Build Record

The controlled runtime records the Python implementation, exact
`MAJOR.MINOR.PATCH`, and complete interpreter build string. The frozen
Reproducibility Manifest `python_version` contains exactly
`MAJOR.MINOR.PATCH`; it never contains a range. The full implementation and
build string belongs in `release-build.json`.

`release-build.json` is a machine-readable reproducibility metadata record for
controlled-runtime acquisition and build. Stage 12E-1 MUST define and freeze a
dedicated schema before operational use. The complete record MUST contain at
least:

- `build_id`;
- `build_version`;
- `release_id`;
- `python_implementation`;
- `python_version`;
- `python_build_string`;
- `os_system`;
- `os_release_identity`;
- `kernel_release`;
- `libc_identity`;
- `architecture`;
- `locale_identity`;
- `timezone_identity`;
- `environment_reference`;
- `environment_mode`;
- `system_site_packages_enabled`;
- `user_site_packages_enabled`;
- `dependency_scope`; and
- `dependencies`.

Each dependency contains at least `name` and `version`, and, where required or
available, `distribution_filename` and `distribution_digest`. The record MUST
contain no credentials or host-user identity and no precise host paths beyond
bounded release-metadata needs.

## 15. Build identity and content binding

The Release Build Record identity is:

```text
build:<release-id-token>
```

For example, `build:pilot-v0.1`. It is compatible with the frozen shared
`build_id` syntax. The Reproducibility Manifest `build_identity` MUST equal the
Release Build Record `build_id`. It is not derived from a hostname, username,
PID, timestamp, or random value.

The Reproducibility Manifest `build_content_digest` is:

```text
canonical_sha256(complete release-build.json object)
```

using the frozen RFC 8785 JCS primitive. The build record MUST first be valid
JSON and structurally valid against its Stage 12E-1 schema. Its path is not
hashed, and a raw-file-byte digest is not substituted for the canonical JSON
digest.

This profile narrows the frozen environment record's otherwise general
`build_identity` and `build_content_digest` to the Release Build Record for
v0.1 releases. It does not add a field to the closed Reproducibility Manifest.

## 16. Normative `os_runtime_identity`

The Reproducibility Manifest `os_runtime_identity` is a deterministic bounded
token with this exact component order and form:

```text
system-<system>+release-<os-release>+kernel-<kernel-release>+libc-<libc-identity>
```

Every component value MUST independently match:

```text
[A-Za-z0-9][A-Za-z0-9._-]*
```

Consequently, a component value cannot contain `+`, whitespace, `/`, `=`, `;`,
or any character outside ASCII letters, digits, `.`, `_`, and `-`. No escaping
scheme exists in v0.1.

The complete identity MUST match the frozen `bounded_identity` pattern:

```text
^[A-Za-z0-9][A-Za-z0-9._+-]*$
```

and its frozen length bound.

The normative positive vector is:

```text
system-Linux+release-Ubuntu-24.04.3-LTS+kernel-6.17.0-35-generic+libc-glibc-2.39
```

The component sources are:

- `system`: the controlled runtime's operating-system family, conceptually
  equivalent to `platform.system()`;
- `release`: a stable machine-readable distribution/runtime release identity
  selected from controlled OS release metadata. On Linux, Stage 12E SHOULD
  prefer machine-readable `/etc/os-release` fields such as distribution ID and
  `VERSION_ID`, rather than `PRETTY_NAME`;
- `kernel`: the controlled runtime kernel release, conceptually equivalent to
  `platform.release()`; and
- `libc`: the C runtime implementation and version, such as `glibc-2.39`.

The `release` component may be assembled from explicitly selected
machine-readable source fields only under the deterministic acquisition rule
frozen by Stage 12E-2. This profile does not authorize ad hoc rewriting of a
free-form source value. In particular, acquisition MUST distinguish selecting
an already machine-safe identity from altering a source string to fit.

If any authoritative component cannot be represented without transformation,
release acquisition fails. Stage 12E MUST NOT silently map spaces to hyphens,
slashes to hyphens, remove punctuation, change case, transliterate, percent
encode, or drop characters. A future profile may define a different encoding.

`platform.platform()` is not the normative aggregate identity.

Future Stage 12E-1/12E-2 tests MUST include the positive vector above, another
representable architecture-independent identity, and rejection of at least:

```text
system=Linux;release=Ubuntu
system-Linux+release-Ubuntu 24.04
```

They MUST also reject a component containing `+` and a component containing
`/`, without coercion.

## 17. Architecture

The Reproducibility Manifest `architecture` is the exact normalized machine
architecture reported by the controlled runtime acquisition source, and it
MUST satisfy the frozen `bounded_identity` contract. The currently observed
value is `x86_64`; this profile does not make `x86_64` the only permitted
architecture.

If the authoritative architecture value cannot be represented without an
unfrozen transformation, acquisition fails.

## 18. Scientific Environment reference and digest

The Reproducibility Manifest `environment_reference` identifies the selected
scientific Environment Contract. It MUST equal that artifact's typed
`environment_id`. It is not a virtual-environment path, host-environment ID,
container ID, or build ID.

The `environment_content_digest` is:

```text
canonical_sha256(complete selected Environment Contract JSON object)
```

using the frozen Stage 12B RFC 8785 JCS primitive. It is not a digest of the
`.venv` directory, OS installation, `sys.path`, or environment variables.
Those runtime facts belong in the Release Build Record.

If a selected Environment artifact does not exist, a PILOT or CONFIRMATORY
release cannot be frozen. For a DEVELOPMENT infrastructure-only audit without
an active experimental Environment artifact, research-release manifest
generation is inapplicable; Stage 12E MUST NOT fabricate an `env:` value.

The closed Reproducibility Manifest has no locale or timezone fields. Exact
locale and timezone identities belong in `release-build.json` and are bound
transitively by `build_content_digest`.

## 19. Manifest creation responsibility

Stage 12E responsibility is deterministic assembly, local acquisition, and
audit. It MAY create an actual Artifact Manifest, Reproducibility Manifest, and
Release Build Record only from:

- an explicit, caller-authored release profile;
- explicitly selected active scientific artifacts;
- the governing-document registry in this profile;
- locally acquired Source Release Tag and Git object facts;
- locally acquired controlled-runtime facts; and
- the exact resolved transitive runtime dependency closure.

Stage 12E MUST NOT recursively scan the repository to discover the scientific
release set or silently create its own artifact-selection policy.

## 20. Scientific artifact-class boundaries

The Artifact Manifest represents only explicitly selected active scientific
JSON artifacts for the release. It does not automatically include all
repository files, source code, tests, fixture corpora, governing Markdown, or
schema documents.

The release classes are represented as follows:

| Class | Binding |
| --- | --- |
| Active scientific JSON artifacts | Artifact Manifest |
| Governing documents | Reproducibility Manifest `governing_documents` |
| Schemas required by Stage 12D closure | Reproducibility Manifest `schema_set` |
| Source, tests, and fixture tree | Source commit and tree provenance |
| Runtime build metadata | `release-build.json` and `build_content_digest` |
| Runtime dependencies | Reproducibility Manifest `dependencies` |

This separation is normative. A path is never substituted for scientific
artifact identity.

For PILOT and CONFIRMATORY, the explicitly selected active set MUST satisfy all
applicable frozen Stage 9, 10, 11, and 12D semantic gates. The existence of a
valid JSON file in the repository does not select it for a release.

## 21. Release profile input

Before production assembly, Stage 12E MUST define and freeze a machine-readable
release-profile input schema. A caller-authored instance identifies at least:

- `release_id`;
- `release_phase`;
- `source_release_tag_identity`;
- active artifact identities and locators;
- rejected-input locators, if applicable;
- the selected Environment artifact;
- governing-document profile version; and
- explicitly enabled dependency extras, normally none.

This input is frozen before release assembly. It is the whitelist for
scientific artifact selection, not a repository-discovery request.

## 22. Schema-set closure

This profile preserves the already-frozen Stage 12D closure rule without
expansion:

```text
Reproducibility Manifest.schema_set includes the schemas referenced by
canonical Artifact Manifest artifact entries.
```

Stage 12D requires each referenced schema to occur exactly once, resolve in the
supplied local schema store, match its schema identity and executable version,
and match its canonical schema-content digest.

The profile does not automatically require the schemas for the Artifact
Manifest, Reproducibility Manifest, Release Build Record, or release-profile
record merely because Stage 12E uses those objects. It does not require every
schema in the repository. Any Stage 12E-specific schema is still locally
applied for structural validation, but its existence alone does not add it to
`schema_set`.

If an earlier frozen contract independently requires an additional schema,
that earlier requirement governs. Stage 12E MUST NOT broaden closure by
inference.

## 23. Current DEVELOPMENT limitation

The Stage 12D repository state has no selected active scientific
Environment/Campaign/Instrument release set and no actual non-test release
manifests. Stage 12E MUST NOT fabricate a research DEVELOPMENT release merely
to exercise implementation.

Stage 12E may be implemented and frozen with synthetic fixtures. Actual
release manifests are assembled only at the first real release gate after the
required active scientific artifacts and explicit profile exist. Test fixtures
do not become release artifacts.

## 24. Integrity commit and tag sequence

After the Source Release Tag exists, the release profile is frozen, active
artifacts are selected, controlled-runtime facts are acquired, release files
are assembled, and Stage 12D returns zero blocking findings, Stage 12E may
create one integrity commit containing release integrity artifacts under:

```text
releases/<release-id-token>/
```

The source commit recorded in the Reproducibility Manifest remains the Source
Release Tag target, not this later integrity commit.

Stage 12E then creates the annotated Release Integrity Tag targeting the
integrity commit and verifies:

- the tag exists and is annotated;
- its target is the integrity commit;
- the tagged release files match the committed bytes; and
- the Reproducibility Manifest's recomputed canonical digest equals the one
  authoritative tag-message digest line.

Neither annotated tag is claimed to be cryptographically authenticated.

## 25. Stage 12E implementation sequence

Implementation proceeds in bounded sub-stages:

1. **12E-1:** release-profile and Release Build Record schemas and tests,
   including the fixed `os_runtime_identity` vectors;
2. **12E-2:** read-only local acquisition primitives for Git provenance,
   governing registry/tagged bytes, dependency closure, distribution
   provenance, and controlled-runtime metadata;
3. **12E-3:** deterministic manifest and build-record assembly from the
   explicit release profile;
4. **12E-4:** release-integrity audit orchestration using the Stage 12D
   validators; and
5. **12E-5:** a fixed synthetic release corpus and implementation freeze.

These sub-stages do not create a second manifest semantic validator.

## 26. GREEN / RED boundary

Everything through Stage 12E remains GREEN. GREEN work includes bounded local
Git object inspection, approved exact dependency artifact acquisition, clean
environment construction, schema and manifest generation, deterministic
hashing, release audit, and synthetic fixtures.

RED begins before any frontier model or agent execution, synthetic attack-chain
execution, S0 runtime validation, M3 enforcement validation, network/egress
containment test, instrument-validation runtime, Pilot, or Confirmatory
experiment.

At the RED transition:

```text
OUTSIDE-SANDBOX EXECUTION IS PROHIBITED.
```

If the approved containment sandbox fails during RED work, the work stops; the
sandbox is not bypassed.

## 27. Claims boundary

This profile establishes deterministic local release assembly policy,
content binding, a scoped exact dependency closure, bounded environment
identity, local Git provenance coherence, and an external manifest digest
anchor.

It does not establish evidence truth, Git authenticity, universal repository
completeness, perfect OS reproduction, perfect hosted-model reproduction,
cryptographic tag authentication, immutable history, containment
effectiveness, system security, or certification.

## 28. Compatibility and conflict resolution

### 28.1 Two-tag compatibility

The frozen Reproducibility Manifest describes a release tag and explicitly
requires its target commit to match `repository_commit_sha`; it does not state
that this tag must target the later commit containing the manifest. Stage 12D
validates the same source-tag relationship using caller-supplied facts.
Therefore the `release_tag_*` fields can consistently describe the Source
Release Tag while the Release Integrity Tag and external manifest digest remain
outside the closed manifest. No circular field or self-digest is introduced.

### 28.2 Build-record compatibility

The frozen `build_identity` is a shared `build_id`, and
`build_content_digest` is a SHA-256 content identifier within the frozen
environment record. No earlier description assigns them to an incompatible
object or byte representation. This profile narrows them for v0.1 to the
Release Build Record identity and the canonical digest of its complete JSON
object.

### 28.3 Environment compatibility

The frozen `environment_reference` uses the shared typed `environment_id`, so
it is compatible with the selected scientific Environment Contract. The
associated `environment_content_digest` consistently binds the complete
canonical Environment Contract JSON object. Runtime and host-build facts remain
separate in the Release Build Record.

### 28.4 OS identity compatibility

The normative positive vector:

```text
system-Linux+release-Ubuntu-24.04.3-LTS+kernel-6.17.0-35-generic+libc-glibc-2.39
```

matches the frozen `bounded_identity` grammar. The former representation:

```text
system=Linux;release=Ubuntu-24.04.3-LTS
```

does not match because `=` and `;` are prohibited. The component grammar and
fail-without-coercion rule preserve an unambiguous serialization.

### 28.5 Schema-set compatibility

The schema-set rule is exactly the Stage 12D closure over schema identities
referenced by canonical Artifact Manifest entries. The profile does not
automatically add the manifest, build-record, or release-profile schemas and
does not require all repository schemas.

### 28.6 Closed-manifest compatibility

The release identifier, governing-document paths, Release Build Record fields,
locale/timezone identities, and external integrity-tag anchor live outside the
closed Reproducibility Manifest except where an existing manifest field
explicitly carries their bound identity or digest. This profile introduces no
undeclared Reproducibility Manifest property.

## 29. Implementation gate

This document is a design contract only. It does not authorize Stage 12E-1,
release-manifest creation, environment construction, package acquisition,
runtime experiments, or RED work. Implementation begins only after this
profile is separately reviewed and frozen.
