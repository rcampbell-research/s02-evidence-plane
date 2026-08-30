# Stage 12E-5 Fixed Synthetic Release Corpus Clarification v0.1

Status: candidate clarification for separate review and freeze

This document freezes the remaining Stage 12E-5 corpus and regression
semantics. It creates no corpus, test, release, source tag, Integrity Tag, or
implementation tag. Stage 12E-5 implementation requires separate approval.

## 1. Governing predecessor

Stage 12E-5 has the exact implementation predecessor:

```text
required_predecessor_tag
    = implementation-stage12e4-v0.1

required_predecessor_commit
    = fb779d06746041e910c8998d4e26d52d03653b95
```

The predecessor freezes the Stage 12E-3 release builder, the Stage 12E-4
persisted-directory audit, the nine-code audit taxonomy, and the immutable
audit result model. Stage 12E-5 tests those interfaces. It does not revise
them.

## 2. Purpose

Stage 12E-5 is a fixed synthetic release corpus and deterministic regression
closure for the already-frozen Stage 12E-3 builder and Stage 12E-4 auditor.
It establishes both directions of this local synthetic pipeline:

```text
frozen synthetic governed inputs
    -> Stage 12E-3 build_research_release()
    -> Stage 12E-3 write_research_release()
    -> exact persisted three-file release-package bytes
```

and:

```text
exact persisted valid or deterministically tampered package
    + fixed governed external audit inputs
    -> Stage 12E-4 audit_research_release_integrity()
    -> exact stable ordered audit-result projection
```

Stage 12E-5 tests existing frozen behavior. It introduces no release-builder
semantics, audit semantics, new audit code, new validator, or new release
artifact.

## 3. Claim boundary

A successful Stage 12E-5 regression closure establishes deterministic
reproducibility and regression stability of the synthetic release-integrity
pipeline against its fixed inputs and expected outputs.

It does not establish:

- scientific truth;
- authenticity of synthetic trusted inputs;
- producer, signature, or trust-anchor authenticity;
- containment effectiveness or operational security;
- actual Instrument Validation, Pilot, or Confirmatory correctness;
- historical existence of a research release;
- actual model or agent execution; or
- historical proof that a supplied `RuntimeDependencyClosure` was acquired
  using exactly `Release Profile.enabled_dependency_extras`.

The `enabled_dependency_extras` limitation remains exactly the Stage 12E-4
trust boundary. The corpus proves only equality to the supplied synthetic
governed closure.

## 4. Architecture

Stage 12E-5 uses architecture C:

```text
CHECKED-IN CANONICAL FIXTURES
    + DETERMINISTIC TEMPORARY DERIVATION
    + REGENERATION/EQUIVALENCE TESTS
```

The implementation checks in:

- two canonical valid persisted three-file release packages;
- one governed synthetic trusted-input bundle for each valid base;
- exact rejected raw bytes referenced by those bases;
- six strict-JSON raw byte fixtures whose invalid representation is intrinsic;
  and
- one corpus index containing all registry, case, mutation, digest, and
  expected-result data.

It does not check in:

- a complete package tree for every tamper;
- symlink or directory-substitution fixtures;
- permission fixtures;
- temporary audit output;
- an audit report or digest sidecar; or
- generated research evidence.

Tests copy fixed base bytes into `tmp_path` and derive package-layout,
physical-serialization, generated-version, order-only, release-binding,
dependency, validator-envelope, and multi-defect cases there.

## 5. Corpus root and layout

The exact corpus root is:

```text
tests/fixtures/reproducibility/stage12e5/
```

Its v0.1 high-level layout is:

```text
tests/fixtures/reproducibility/stage12e5/
├── corpus-index.json
├── bases/
│   ├── development/
│   │   ├── package/
│   │   │   ├── artifact-manifest.json
│   │   │   ├── release-build.json
│   │   │   └── reproducibility-manifest.json
│   │   ├── trusted-inputs.json
│   │   └── rejected/
│   │       └── <only raw files referenced by this base>
│   └── confirmatory/
│       ├── package/
│       │   ├── artifact-manifest.json
│       │   ├── release-build.json
│       │   └── reproducibility-manifest.json
│       ├── trusted-inputs.json
│       └── rejected/
│           └── <only raw files referenced by this base, if any>
└── raw-tampers/
    ├── malformed-utf8.raw
    ├── malformed-json.raw
    ├── duplicate-key.raw
    ├── nan.raw
    ├── infinity.raw
    └── negative-infinity.raw
```

An empty `rejected/` directory is not checked in. A valid-base rejected raw
file is not duplicated merely because a strict-JSON tamper has a similar
name. The two byte roles are distinct.

## 6. Release-package boundary

Each checked-in base `package/` directory contains exactly these three direct
children:

```text
artifact-manifest.json
release-build.json
reproducibility-manifest.json
```

The Release Profile, scientific artifacts, rejected raw bytes, Environment,
schemas, governing documents, trusted inputs, expected results, and corpus
metadata remain outside that package directory. No corpus object is added to
the release package.

## 7. Corpus version

The sole v0.1 corpus version is:

```text
corpus_version = "0.1.0"
```

There is no separate expected-result version or mutation-schema version.

## 8. Case identity

Every regression case has one explicit stable `case_id` matching:

```regex
^stage12e5:[a-z0-9]+(?:-[a-z0-9]+)*$
```

`case_id` is identity. A filesystem path is only a locator. Directory renaming
does not implicitly rename a case. Case IDs are unique across the complete
`cases` array.

## 9. Exactly two valid bases

V0.1 contains exactly:

```text
stage12e5:valid-development
stage12e5:valid-confirmatory
```

It contains no checked-in Instrument Validation or Pilot base. Development
and Instrument Validation share the relevant missing-distribution-provenance
rule. Pilot and Confirmatory share the stricter complete-provenance rule.
Existing Stage 12E-3 and Stage 12E-4 unit tests retain explicit four-phase
coverage.

## 10. Development base

`stage12e5:valid-development` is a fully valid assembled DEVELOPMENT release.
It must:

- regenerate byte-for-byte through Stage 12E-3;
- audit with zero Stage 12E-4 findings;
- use an explicit valid Development build mode;
- contain at least one dependency without original distribution provenance;
- contain a nonempty `reproducibility_limitations` array as required by that
  absence;
- contain at least two limitations and two governed rejected-input records so
  their order-only cases can reverse existing valid members;
- include distinct exact dependency names `a-pkg` and `a_pkg`, which remain
  unequal and independently ordered;
- contain a non-ASCII value in a schema-valid free-text field for the escaped
  Unicode physical-byte case; and
- remain wholly synthetic.

No invalid field is inserted merely to make a test convenient.

## 11. Confirmatory base

`stage12e5:valid-confirmatory` is a fully valid assembled CONFIRMATORY release.
It must:

- regenerate byte-for-byte through Stage 12E-3;
- audit with zero Stage 12E-4 findings;
- use `CONTROLLED_RUNTIME`;
- contain complete original distribution filename and digest provenance for
  every dependency;
- select affected prospective artifact families at version `0.2.0` where the
  frozen release-version gates require them; and
- contain coherent multiplicity for order-only derivations.

The base contains at least two coherent members for provider identities,
`scenario_subset`, `control_subset`, `scheduled_run_ids`, `run_ids`, and
repetition identities. Each member must resolve through the existing
scientific graph. Multiplicity may not be manufactured with invalid or
unresolved references.

Between the two valid bases, every array used by an order-only case must have
at least two valid members before the order mutation.

## 12. Trusted-input bundles

Each base has one `trusted-inputs.json`. This is closed internal test corpus
data, not a production artifact and not a scientific artifact.

Its exact top-level fields are:

```text
release_profile
artifact_documents_by_locator
artifact_expectations_by_locator
artifact_metadata_by_locator
rejected_input_metadata_by_locator
git_provenance
runtime_dependency_closure
runtime_environment_facts
environment_artifact
phase_projection
provider_records
reproducibility_limitations
build_mode
```

No additional top-level field is permitted. `build_mode` is JSON `null` when
the Stage 12E-3 API requires omission/derivation rather than an explicit mode.

The test reconstructs the established immutable Stage 12E-3 and Stage 12E-4
data classes from these values. It does not invent new production input types.
Schema and governing-document sources are corpus-index records rather than
duplicated bundle fields.

Nested records are also closed. `git_provenance`,
`runtime_environment_facts`, `ArtifactAssemblyMetadata`,
`RejectedInputAssemblyMetadata`, `PhaseProjection`, and
`RepetitionIdentity` use exactly the fields of their frozen public data types.
`runtime_dependency_closure` contains exactly `dependency_scope`,
`dependencies`, and `findings`; a valid base has empty `findings`. Each
dependency contains exactly `name`, `version`, `requires_dist`,
`provides_extra`, and nullable `distribution_provenance`, whose non-null
object contains exactly `distribution_filename`, `distribution_digest`, and
`source`. Provider records and the Environment artifact use their existing
closed schema shapes. Unknown nested fields fail corpus validation.

## 13. Scientific artifacts

`artifact_documents_by_locator` contains complete synthetic scientific JSON
objects keyed by their frozen locators. Those artifacts remain external to the
release package. Corpus validation binds their exact locator, semantic
identity, artifact version, governing schema ID, and expected canonical
digest.

`artifact_expectations_by_locator` is keyed by the same exact locator set.
Each value contains exactly:

```text
artifact_family
artifact_id
artifact_version
schema_id
canonical_sha256
```

The stored canonical digest is independently established before freeze and is
not copied from the checked-in Artifact Manifest. The test recomputes the
trusted artifact digest before either builder regeneration or audit.

A locator is never substituted for an artifact identity. The corpus test
derives an artifact family contract only through the existing public semantic
metadata.

## 14. Builder-only metadata

`artifact_metadata_by_locator`, `rejected_input_metadata_by_locator`,
`phase_projection`, `provider_records`, `reproducibility_limitations`, and
`build_mode` are explicit Stage 12E-3 inputs. They are reconstructed from the
trusted bundle and never inferred from a candidate manifest.

This prevents a candidate package from supplying its own expected builder
inputs.

## 15. Rejected raw inputs

Valid-base rejected bytes remain separate ordinary files below the base's
`rejected/` directory. A base record maps each Release Profile rejected-input
locator to exactly one corpus-relative raw path.

For each raw file, the corpus freezes:

- its locator;
- its physical file SHA-256 through the common file registry; and
- its expected `forensic_sha256_bytes` result in the base record
  `rejected_input_paths` projection.

The bytes are read in binary mode and are not parsed or newline-normalized.

## 16. SchemaStore strategy

Stage 12E-5 uses SchemaStore strategy C: load only an explicit corpus-indexed
list of repository schema files and bind every entry before use.

For each schema, the index stores exactly:

```text
path
schema_id
physical_sha256
canonical_sha256
```

The test requires:

- a unique, exact indexed path set;
- every indexed path to exist as an ordinary non-symlink repository file;
- the parsed `$id` to equal `schema_id`;
- the exact physical digest to equal `physical_sha256`;
- the canonical JSON digest to equal `canonical_sha256`; and
- the constructed `SchemaStore` identity set to equal the indexed set.

The test does not glob or otherwise discover a replacement schema set at
runtime. Complete schema bytes are not duplicated in the corpus.

## 17. Governing-document strategy

Governing-document bytes are read from the exact repository paths frozen by
the public nine-entry registry. They are not duplicated in the corpus.

Each index record contains exactly:

```text
document_id
path
physical_sha256
provenance
```

The closed `provenance` object contains exactly:

```text
document_version
frozen_tag_identity
frozen_tag_object_sha
frozen_tag_target_commit_sha
exact_byte_content_digest
```

`exact_byte_content_digest` must equal the record's `physical_sha256`. The
nine records occur in the exact public registry order. Before constructing
`GoverningDocumentAcquisition`, tests verify record identity, path, registry
metadata, exact bytes, and all fixed provenance fields. No document
acquisition or Git lookup occurs.

## 18. Synthetic Git provenance

Each base's `git_provenance` is fixed synthetic trusted data. It is
independent of the candidate Reproducibility Manifest and is used to construct
the real `GitProvenance` input.

Corpus tests perform no Git lookup for package semantics. The production
auditor continues to run no Git subprocess and accepts only the supplied
governed provenance.

## 19. Predecessor metadata

The index contains exactly:

```json
{
  "tag": "implementation-stage12e4-v0.1",
  "commit": "fb779d06746041e910c8998d4e26d52d03653b95"
}
```

Routine tests compare these fixed metadata values. The Stage 12E-5 freeze
gate, not routine corpus tests, verifies that the actual annotated predecessor
tag dereferences to that commit.

## 20. Exact dependency semantics

`RuntimeDependencyClosure` is reconstructed as explicit governed synthetic
input. Dependency identity and order use the exact stored strings:

```text
(name, version)
```

The corpus performs no PEP 503 canonicalization, lowercasing, case folding,
underscore/hyphen rewriting, whitespace transformation, Unicode
normalization, or version normalization. In particular:

```text
a-pkg != a_pkg
```

## 21. Enabled-extras boundary

The corpus may prove that package Build/Repro dependency projections equal the
supplied synthetic `RuntimeDependencyClosure`. It must not claim historical
proof that the closure was acquired using exactly the Release Profile's
`enabled_dependency_extras`.

The absence of that unpreserved evidence produces no corpus or audit finding.

## 22. Corpus index

The exact index path is:

```text
tests/fixtures/reproducibility/stage12e5/corpus-index.json
```

Its exact closed top-level field set is:

```text
corpus_version
required_predecessor
files
schemas
governing_documents
bases
cases
```

No additional top-level field is permitted.

## 23. File registry

`files` contains every other checked-in ordinary file below the corpus root
exactly once. It excludes only `corpus-index.json`. Each record contains
exactly:

```text
path
sha256
```

`path` is relative to the corpus root. `sha256` has the form
`sha256:<64 lowercase hex>` and covers exact physical bytes.

The registry rejects duplicate paths, missing files, stale records, extra
unindexed files, directories represented as files, and symlinks. No index
entry may name `corpus-index.json`.

## 24. No corpus self-digest

The index contains no digest of itself. Its exact bytes are anchored later by
the Stage 12E-5 implementation commit, annotated implementation tag, and
freeze-time exact-byte digest report. This avoids a self-referential cycle.

## 25. Schema records and order

`schemas` records have exactly the four fields in Section 16. They are unique
by both `path` and `schema_id` and occur in exact `schema_id` order.

## 26. Governing-document records and order

`governing_documents` records have exactly the fields in Section 17. They are
unique by both `path` and `document_id` and occur in the frozen nine-entry
registry order, not alphabetical order.

## 27. Base records

`bases` contains exactly two records ordered by `base_case_id`. Each record
contains exactly:

```text
base_case_id
phase
package_path
trusted_inputs_path
rejected_input_paths
```

`rejected_input_paths` is an array ordered by exact rejected-input locator.
Each item contains exactly:

```text
locator
path
forensic_sha256
```

`forensic_sha256` is independently established over the exact raw bytes and
must equal the Artifact Manifest forensic projection produced during
regeneration. The common `files` record separately binds the raw file's
physical bytes.

The two `base_case_id` values are the valid case IDs in Section 9. `phase`
equals `DEVELOPMENT` or `CONFIRMATORY` respectively. Package and trusted-input
paths resolve beneath the corpus root.

## 28. Case records

`cases` contains every valid and tamper case exactly once in `case_id` order.
Each record contains exactly:

```text
case_id
base_case_id
mutation
expected
```

`base_case_id` resolves to one base record. Valid-base cases use a `mutation`
of kind `none`. Unknown case IDs, base references, mutation kinds, or mutation
fields fail corpus validation.

## 29. Closed mutation vocabulary

Mutations are declarative data interpreted only by fixed test helpers. They
are not executable code and do not form a general patch language.

Every mutation has `kind` and `target`. The supported v0.1 kinds and additional
fields are exactly:

| Kind | Additional fields | Purpose |
| --- | --- | --- |
| `none` | none; `target` is null | Valid base |
| `remove-package-child` | none | Missing required file |
| `add-package-child` | `content_utf8` | Extra ordinary child |
| `symlink-package-child` | `link_target` | Child symlink in temporary package |
| `directory-package-child` | none | Child directory substitution |
| `inject-read-failure` | none | Narrow exact-byte read fault |
| `replace-package-bytes` | `fixture_path` | Strict-JSON raw substitution |
| `physical-no-terminal-lf` | `derived_file_sha256` | Physical mutation |
| `physical-double-terminal-lf` | `derived_file_sha256` | Physical mutation |
| `physical-crlf` | `derived_file_sha256` | Physical mutation |
| `physical-compact-json` | `derived_file_sha256` | Physical mutation |
| `physical-unsorted-keys` | `derived_file_sha256` | Physical mutation |
| `physical-escaped-unicode` | `derived_file_sha256` | Physical mutation |
| `set-package-json-value` | `json_pointer`, `value` | Closed case-specific scalar/object replacement |
| `reverse-package-array` | `json_pointer`, `derived_file_sha256` | True order-only reversal |
| `remove-package-array-item` | `json_pointer`, `index` | Whitelist/closure omission |
| `append-package-array-item` | `json_pointer`, `value` | Whitelist/closure addition |
| `set-trusted-json-value` | `json_pointer`, `value` | External trusted-input mismatch |
| `replace-trusted-dependency-provenance` | `dependency_name`, `provenance` | Dependency provenance case |
| `multi-five-finding-order` | `operations` | One exact closed compound recipe |

For `multi-five-finding-order`, `operations` is not arbitrary: it must equal
the exact five operation records frozen for that one case in the index and is
rejected for every other case. Each JSON-pointer mutation is further
whitelisted by `case_id`; a case may not redirect a generic kind to a new
semantic target.

`derived_file_sha256` is mandatory for every derived physical representation
and order-only file. It freezes the exact target file bytes independently of
the mutation helper and has `sha256:<64 lowercase hex>` form.

## 30. Expected result shape

Every `expected` object contains exactly:

```text
passed
release_id
release_id_token
findings
reproducibility_manifest_digest
integrity_tag_annotation
```

`case_id` remains outside this object in the case record.

Each `findings` item contains exactly:

```text
code
field_path
source
source_code
source_field_path
```

Finding array order is significant. `message` and `source_message` are not
stored because their prose is not the frozen corpus regression interface.
Tests additionally compare complete repeated `ReleaseIntegrityAuditResult`
instances to detect nondeterminism within an execution environment.

## 31. Success expectations

For each successful case:

```text
passed = true
findings = []
release_id = exact expected release ID
release_id_token = exact expected token
reproducibility_manifest_digest = independently frozen canonical digest
integrity_tag_annotation =
    "reproducibility-manifest-sha256: "
    + reproducibility_manifest_digest
```

The annotation has no newline or additional whitespace.

## 32. Failure expectations

For each failing case:

```text
passed = false
findings = exact complete ordered stable projection
reproducibility_manifest_digest = null
integrity_tag_annotation = null
```

`release_id` and `release_id_token` retain their expected values only when the
Release Profile prerequisites remain valid. They are `null` when Stage 12E-4
short-circuit semantics cannot safely derive them.

## 33. Digest domains

Three digest domains remain distinct:

```text
physical file digest
    = SHA-256 over exact checked-in or derived file bytes

canonical JSON digest
    = canonical_sha256(parsed JSON object)

forensic raw digest
    = forensic_sha256_bytes(exact rejected raw bytes)
```

Pretty-JSON bytes are not substituted for canonical content bytes. Rejected
raw bytes are not parsed to obtain a forensic digest. The corpus index's file
registry uses only the physical role.

## 34. Physical JSON representation

`corpus-index.json` and both `trusted-inputs.json` files use exactly:

```python
json.dumps(
    value,
    ensure_ascii=False,
    sort_keys=True,
    indent=2,
    separators=(",", ": "),
    allow_nan=False,
).encode("utf-8") + b"\n"
```

Arrays use these deterministic semantic orders:

```text
files                  path
schemas                schema_id
governing_documents    frozen registry order
bases                  base_case_id
cases                  case_id
```

This physical rule is fixture reproducibility metadata. It does not make the
index or trusted bundle a release-package artifact.

## 35. Strict-JSON raw fixtures

V0.1 freezes exactly:

```text
raw-tampers/malformed-utf8.raw
raw-tampers/malformed-json.raw
raw-tampers/duplicate-key.raw
raw-tampers/nan.raw
raw-tampers/infinity.raw
raw-tampers/negative-infinity.raw
```

They are read as exact bytes. No newline normalization, text decoding, or JSON
parsing occurs during file-integrity verification. Their physical SHA-256
values occur in `files`. Their exact v0.1 byte contents are:

| Path | Exact bytes |
| --- | --- |
| `malformed-utf8.raw` | hexadecimal `7b2278223a22ff227d0a` |
| `malformed-json.raw` | ASCII `{"x":` followed by LF |
| `duplicate-key.raw` | ASCII `{"x":1,"x":2}` followed by LF |
| `nan.raw` | ASCII `{"x":NaN}` followed by LF |
| `infinity.raw` | ASCII `{"x":Infinity}` followed by LF |
| `negative-infinity.raw` | ASCII `{"x":-Infinity}` followed by LF |

The malformed-UTF-8 fixture therefore represents `{"x":"`, byte `0xff`,
then `"}` and LF. The table is the normative byte definition; an editor
rendering is not.

## 36. Strict-JSON cases

The fixed case IDs are:

```text
stage12e5:json-malformed-utf8
stage12e5:json-malformed-json
stage12e5:json-duplicate-key
stage12e5:json-nan
stage12e5:json-infinity
stage12e5:json-negative-infinity
```

Each uses `replace-package-bytes` to replace
`release-build.json` in a temporary copy of the Development package. The
replacement bytes come from the corresponding indexed raw fixture. Each exact
expected result contains `AUDIT_JSON_INVALID` at
`/release-build.json`, with no speculative Build consistency finding.

## 37. Physical-serialization cases

The fixed cases are:

```text
stage12e5:physical-no-terminal-lf
stage12e5:physical-double-terminal-lf
stage12e5:physical-crlf
stage12e5:physical-compact-json
stage12e5:physical-unsorted-keys
stage12e5:physical-escaped-unicode
```

They derive exact bytes in `tmp_path` from the fixed Development base
`reproducibility-manifest.json`. The Development limitation required by
Section 10 contains the schema-valid non-ASCII source value needed by the
escaped-Unicode case. All six cases therefore use the same exact target.

Each mutation must retain the same parsed JSON value and change only physical
representation. The exact derivations from the canonical target bytes are:

- `physical-no-terminal-lf`: remove the single final LF;
- `physical-double-terminal-lf`: append one LF;
- `physical-crlf`: replace every LF byte with CRLF;
- `physical-compact-json`: strict-parse, then `json.dumps` with
  `ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")`,
  `allow_nan=False`, no indentation, UTF-8 encoding, and one final LF;
- `physical-unsorted-keys`: strict-parse, rebuild only the top-level mapping in
  reverse lexicographic key order, then use the normal two-space pretty
  serializer with `sort_keys=False` and one final LF; and
- `physical-escaped-unicode`: strict-parse, then use the normal two-space
  pretty serializer with `ensure_ascii=True`, `sort_keys=True`, and one final
  LF.

No derivation uses the private Stage 12E-3 serializer or the Stage 12E-4
physical helper. The test first proves strict parsing yields the original
value. `derived_file_sha256` must equal the independently established physical
SHA-256 of the derived target bytes before audit. Each expected result contains
`AUDIT_PHYSICAL_SERIALIZATION_INVALID` at the target file path.

## 38. Package-layout cases

V0.1 freezes at least:

```text
stage12e5:layout-missing-file
stage12e5:layout-extra-child
stage12e5:layout-symlink-child
stage12e5:layout-directory-child
```

The missing/substituted child is `release-build.json`; the extra child is
`unexpected.txt`. The symlink target is a temporary ordinary file outside the
temporary package but inside the test-owned temporary root. Stage 12E-4 must
not follow it.

Each case invokes the public auditor and freezes its exact
`AUDIT_PACKAGE_LAYOUT_INVALID` path. No filesystem object is stored as a Git
symlink or created outside test-owned temporary storage.

## 39. Package read failure

The fixed identity is:

```text
stage12e5:package-read-failed
```

An OS read failure is not representable portably as checked-in bytes. This one
case permits narrow fault injection at the Stage 12E-4 exact-byte read
boundary while calling the real `audit_research_release_integrity()` API on an
otherwise valid package.

It may not mock Stage 12D, Identity-5, Release Build, Reproducibility, or other
semantic validators. It must yield `AUDIT_PACKAGE_READ_FAILED`, prove that no
package state changed, and use automatically restored test monkeypatch state.

## 40. Generated-version cases

V0.1 freezes:

```text
stage12e5:version-artifact-manifest
stage12e5:version-release-build
stage12e5:version-reproducibility-manifest
```

Each changes only the relevant version field to schema-valid `7.3.9`, then
uses the correct physical serializer. The expected result includes
`AUDIT_GENERATED_VERSION_INVALID` at the exact field path and freezes every
other legitimate cross-object finding, if any.

## 41. Order-only inventory

V0.1 freezes every Stage 12E-4 deterministic collection:

```text
stage12e5:order-artifacts
stage12e5:order-rejected-inputs
stage12e5:order-providers
stage12e5:order-limitations
stage12e5:order-schema-set
stage12e5:order-governing-documents
stage12e5:order-dependencies
stage12e5:order-scenario-subset
stage12e5:order-control-subset
stage12e5:order-scheduled-run-ids
stage12e5:order-run-ids
stage12e5:order-repetitions
```

Every case begins from a base that passes audit, reverses an array containing
at least two members, preserves exact count and content, reserializes the file
correctly, verifies `derived_file_sha256`, and expects
`AUDIT_DETERMINISTIC_ORDER_INVALID` at the exact collection path.

For object arrays, sorted RFC 8785 JCS bytes before and after must be equal.
For scalar arrays, sorted exact strings and member counts must be equal. The
original and mutated sequences must differ. Replacement, insertion, deletion,
identity mutation, reference mutation, and dependency-name normalization are
prohibited.

## 42. Release-binding inventory

V0.1 freezes at least:

```text
stage12e5:binding-active-artifact
stage12e5:binding-rejected-input
stage12e5:binding-build-id
stage12e5:binding-repro-build-identity
stage12e5:binding-environment-reference
stage12e5:binding-environment-content
stage12e5:binding-source-git
stage12e5:binding-schema-set
stage12e5:binding-dependency-projection
stage12e5:binding-governing-document
```

Each index mutation identifies whether it changes temporary persisted package
bytes or a deep-copied external trusted input. It changes only one side unless
the case is explicitly a cross-object coherence case. The index freezes all
legitimate findings produced by a minimal mutation; it does not suppress a
secondary digest or coherence finding.

The field relationship remains:

```text
Release Build.build_id
    == "build:<release-id-token>"

Reproducibility Manifest.environment.build_identity
    == Release Build.build_id
```

## 43. Dependency inventory

V0.1 freezes:

```text
stage12e5:dependency-name
stage12e5:dependency-version
stage12e5:dependency-order
stage12e5:dependency-provenance-projection
stage12e5:dependency-confirmatory-missing-provenance
stage12e5:dependency-development-empty-limitations
stage12e5:dependency-development-nonempty-limitations
```

The first four prove exact closure projection. The Confirmatory case requires
complete original distribution provenance and fails when it is absent. The
Development empty-limitations case fails when provenance is absent. The
Development nonempty-limitations case succeeds and may be satisfied by the
valid Development base.

No limitation prose is interpreted. `a-pkg` and `a_pkg` remain distinct.

## 44. Wrapped-validator inventory

V0.1 freezes at least:

```text
stage12e5:validation-stage12d-artifact-digest
stage12e5:validation-identity5-version
stage12e5:validation-build-schema
stage12e5:validation-build-consistency
stage12e5:validation-repro-environment
```

Each uses the real public validator composition reached through the real public
auditor. Its expected outer code is `AUDIT_VALIDATION_FAILED`. Expected data
retains `source`, `source_code`, and `source_field_path`, but not message prose.

## 45. Multi-defect ordering case

The fixed identity is:

```text
stage12e5:multi-five-finding-order
```

It produces an exact complete sequence with these high-level categories:

1. `AUDIT_PACKAGE_LAYOUT_INVALID`;
2. `AUDIT_PHYSICAL_SERIALIZATION_INVALID`;
3. `AUDIT_GENERATED_VERSION_INVALID`;
4. `AUDIT_DETERMINISTIC_ORDER_INVALID`; and
5. `AUDIT_VALIDATION_FAILED`.

The index freezes the actual Stage 12E-5 paths and source fields established by
the temporary prototype. Tests compare all five projected findings, not a
prefix. The compound operation list is fixed only for this case.

## 46. Nine-code taxonomy closure

The corpus/test inventory mechanically covers exactly:

```text
AUDIT_PACKAGE_LAYOUT_INVALID
AUDIT_PACKAGE_READ_FAILED
AUDIT_JSON_INVALID
AUDIT_PHYSICAL_SERIALIZATION_INVALID
AUDIT_GENERATED_VERSION_INVALID
AUDIT_DETERMINISTIC_ORDER_INVALID
AUDIT_RELEASE_BINDING_INVALID
AUDIT_DEPENDENCY_PROVENANCE_INCOMPLETE
AUDIT_VALIDATION_FAILED
```

Tests also assert that the public enum contains exactly these nine values and
no alias or tenth code. Not every code requires a persisted tampered tree.

## 47. Real public auditor

Every acceptance case ultimately calls:

```python
audit_research_release_integrity(...)
```

Private Stage 12E-4 helpers are not final acceptance oracles. Semantic
validators are not mocked. The narrow exact-byte read fault in Section 39 is
the sole fault-injection exception.

## 48. Stage 12E-3 regeneration

For both valid bases, tests:

1. validate and reconstruct all trusted builder inputs;
2. verify and load the explicit schema set;
3. verify and construct the governing-document acquisition;
4. call real `build_research_release()`;
5. call real `write_research_release()` into a temporary root;
6. compare the direct child set to the checked-in package;
7. require exactly the three frozen filenames;
8. compare every file byte-for-byte; and
9. confirm no fourth child exists.

The checked-in bytes are the fixed expectation. Ordinary test collection does
not regenerate or rewrite them.

## 49. Auditor trusted projection

The test constructs Stage 12E-4 arguments from the trusted bundle and
independently verified schema/governing sources. It does not copy expected Git,
dependency, Environment, Build, governing-document, Artifact Manifest, or
scientific values out of the candidate Reproducibility Manifest when an
independent corpus source exists.

The Stage 12E-4 seven-field `trusted_environment` remains constructed inside
the auditor from governed inputs. The corpus does not add an auditor input or
candidate self-trust path.

## 50. Repeatability

Every normal corpus audit case is executed exactly twice. Tests require:

```text
result_1 == result_2
```

for the complete immutable `ReleaseIntegrityAuditResult`, then compare its
stable projection to the indexed `expected` object. Two executions are
sufficient for v0.1.

The read-failure injection case may also execute twice when the injected fault
is safely repeatable; otherwise one execution plus exact expected projection
is sufficient because monkeypatch state is itself the induced condition.

## 51. No-write proof

Before the first audit of each persisted-package case, tests capture:

- exact direct child names; and
- exact bytes of every ordinary direct child.

After both audits, names and bytes must be identical. No report, sidecar,
digest file, temporary child, repair, or permission change is requested.

For symlink and directory layout cases, tests snapshot and compare the
`lstat`-visible object type, name, and applicable exact bytes without following
the symlink.

## 52. Index validation

No production JSON Schema governs the corpus index. The Stage 12E-5 test module
implements strict closed validation for test data before consuming a case.

It validates:

- exact top-level keys and `corpus_version`;
- exact predecessor object shape and constants;
- exact record field sets;
- unique case IDs and the case-ID grammar;
- exact two-base set and valid base references;
- known mutation kinds and case-specific allowed targets;
- closed mutation fields for each kind;
- closed expected-result and finding shapes;
- file registry uniqueness and completeness;
- schema registry identity, uniqueness, digest, and order;
- governing registry exact membership, provenance, and order;
- absence of an index self-digest;
- relative path syntax and containment; and
- existence and ordinary-file type of all referenced fixed files.

## 53. Path safety

Every corpus-relative path string is relative, uses forward slashes, is
nonempty, is not absolute, contains no `.` or `..` component, and resolves
beneath the corpus root. This applies to file, base, rejected-input, and raw
fixture paths.

Schema and governing-document `path` values are separately repository-relative.
They obey the same lexical restrictions, resolve beneath the repository root,
and are restricted respectively to the explicit `schemas/` entries and exact
public governing-document registry paths. They are never resolved beneath the
corpus root. Backslashes, drive-qualified paths, and NUL are prohibited in all
path strings.

Index validation uses `lstat` semantics. It does not follow a corpus, schema, or
governing-document symlink. The checked-in corpus contains ordinary directories
and ordinary files only. Symlink test objects exist only in `tmp_path`.

## 54. Frozen constants

Every checked-in non-index file receives an exact physical SHA-256 in `files`.
Every derived physical/order target receives a fixed
`derived_file_sha256`. Success Reproducibility Manifest canonical digests and
all indexed schema/artifact canonical digests are established independently
before freeze.

Expected constants may not be populated from
`audit_result.reproducibility_manifest_digest` or another value produced by the
acceptance execution being tested. Freeze review must compare canonical bytes
and hashes through a separately inspected calculation and exact-byte tools.

## 55. Fixture generation boundary

Implementation may use a bounded deterministic temporary generator to create
candidate fixture bytes. Before freeze, every candidate byte is reviewed,
indexed, independently digested, and reproduced from the fixed trusted inputs.

No permanent production generator is required. Ordinary collection and tests
consume checked-in bytes and never silently update them. Test-generated
packages and mutations exist only in test-owned temporary directories.

## 56. No production schema or source change

Stage 12E-5 v0.1 adds no production schema. The index and trusted bundles are
strict internal test-data contracts.

Expected implementation scope is only:

```text
tests/fixtures/reproducibility/stage12e5/**
tests/reproducibility/test_stage12e5_fixed_release_corpus.py
```

It modifies no Stage 12E-3 source, Stage 12E-4 source, package export,
existing test, schema, dependency, or configuration. A need for any production
change is a blocker requiring separate review.

## 57. Final regression closure

Stage 12E-5 implementation must prove all of:

A. both valid packages regenerate exactly through Stage 12E-3;

B. both valid packages audit with zero Stage 12E-4 findings;

C. success canonical digests equal independently frozen constants;

D. success annotations exactly bind those digests;

E. every indexed tamper case produces its complete ordered expected projection;

F. every failed audit returns digest and annotation `None`;

G. every ordinary case audited twice returns the same complete result;

H. persisted package bytes and children remain unchanged;

I. the Stage 12E-4 public taxonomy remains exactly nine codes;

J. index keys, case IDs, base references, mutation kinds, expected shapes, and
file coverage are closed and unique;

K. every indexed non-index corpus file physical digest verifies;

L. every indexed schema ID, physical digest, and canonical digest verifies;

M. every indexed governing-document ID, path, physical digest, provenance,
and registry position verifies;

N. exact dependency name/version behavior and no normalization remain proven;

O. the enabled-extras historical-proof limitation remains preserved;

P. predecessor metadata equals the frozen tag and commit in Section 1;

Q. the later freeze gate verifies the real predecessor tag target; and

R. the complete repository test suite remains green.

## 58. Temporary prototype matrix

Before clarification freeze, a temporary-only prototype must exercise:

| Probe | Required observation |
| --- | --- |
| A | Development trusted inputs can be constructed |
| B | Confirmatory trusted inputs can be constructed |
| C | Both build through real Stage 12E-3 |
| D | Both persist only to temporary roots |
| E | Both packages contain exactly three children |
| F | Both audit twice through the real Stage 12E-4 API |
| G | Both return zero findings and repeat exactly |
| H | Development missing provenance plus limitations succeeds |
| I | Confirmatory complete provenance succeeds |
| J | `a-pkg` and `a_pkg` remain distinct without normalization |
| K | One strict-JSON substitution yields JSON invalid |
| L | One physical mutation yields physical invalid |
| M | One true order-only reversal yields deterministic-order invalid |
| N | Build `build_id` mutation yields release-binding invalid |
| O | Stage 12D source finding remains wrapped and preserved |
| P | Confirmatory missing provenance yields provenance incomplete |
| Q | Development missing provenance and empty limitations fails |
| R | Development missing provenance and nonempty limitations succeeds |
| S | Five-defect case yields the fixed five-category sequence |
| T | Every failure withholds digest and annotation |
| U | Audited package bytes and children remain unchanged |
| V | Closed index shape, paths, and digest registry are representable |
| W | Index omission of its own digest creates no integrity cycle |
| X | Read failure requires narrow injection, not fixed repository bytes |

Prototype observations are recorded in the separate clarification review
report. The prototype creates no repository fixture.

## 59. Prototype stop conditions

Stage 12E-5 is blocked if the prototype reveals a need for a production schema,
Stage 12E-3 or Stage 12E-4 source change, inability to construct either valid
base, non-three-file package output, hidden dependency normalization, candidate
self-trust, an unstable expected projection, a corpus self-digest, unstable
finding order, nondeterministic bytes, or a portable persisted-read-failure
assumption.

Frozen production behavior is not repaired during clarification work.

## 60. Compatibility

This design preserves all frozen constraints:

- a persisted release package has exactly three direct files;
- the Release Profile and scientific artifacts remain external;
- rejected raw bytes remain external and forensic;
- locators remain locators rather than identities;
- physical, canonical, and forensic digest roles remain distinct;
- no release object or corpus index contains a self-digest;
- Release Build uses `build_id`;
- Reproducibility Environment uses `build_identity`;
- Reproducibility `build_identity` binds to Release Build `build_id`;
- dependency order is exact `(name, version)` with no normalization;
- enabled-extras acquisition history remains unproven;
- the Stage 12E-4 auditor remains read-only and creates no Integrity Tag;
- corpus trusted inputs never come from candidate self-trust;
- historical v0.1 scientific artifacts remain unchanged;
- affected prospective artifacts remain v0.2 where required; and
- no corpus object is registered as a scientific release artifact.

The earlier Stage 12E-3 phrase concerning normalized distribution-name
ordering is governed by the explicit corrected Stage 12E-4 rule: exact stored
`(name, version)` strings without normalization.

## 61. GREEN boundary

Stage 12E-5 remains GREEN. It uses local synthetic data, deterministic
temporary filesystem operations, schemas, validators, hashing, and unit tests.
It authorizes no network, service, credential, package installation,
dependency acquisition, project model or agent, S0/M3 runtime, containment
experiment, Instrument Validation runtime, Pilot, or Confirmatory execution.

## 62. Implementation and completion tags

The later implementation freeze tag is expected to be:

```text
implementation-stage12e5-v0.1
```

This clarification does not create that tag and does not complete Stage 12E-5.
Successful implementation review, full regression, commit, and annotated tag
freeze are separately required.

## 63. Stage 12E completion boundary

Successful freeze of `implementation-stage12e5-v0.1` completes the Stage 12E
release-integrity engineering sequence. It does not authorize Instrument
Validation, Pilot, Confirmatory campaigns, model or agent execution, or
containment experiments. Each requires subsequent explicit authorization.
