# Integrity & Reproducibility Clarification v0.1

## Governing Authority and Status

This document is a design clarification to the frozen:

- `integrity-reproducibility-spec-v0.1`
- `implementation-stage12c-v0.1`

It supplements, and does not rewrite or weaken, the Integrity &
Reproducibility Specification v0.1 or any earlier scientific, evidence,
implementation, or schema contract. If this clarification conflicts with a
previously frozen governing artifact outside the four ambiguities resolved
here, the previously frozen artifact controls and the conflict is a blocker.

Current stage:

```text
DESIGN CLARIFICATION ONLY
```

This document authorizes no implementation, schema change, manifest
generation, runtime execution, evidence collection, or security-boundary
testing. Stage 12D implementation requires separate approval after this
clarification is frozen.

Normative terms such as **MUST**, **MUST NOT**, **REQUIRED**, and **MAY** are
used to state the v0.1 clarification requirements.

## 1. Purpose and Scope

This clarification resolves exactly four semantics that were insufficiently
specified for deterministic Stage 12D implementation:

1. the digest semantics for non-JSON governing documents;
2. governing-document byte resolution when the frozen manifest record has no
   locator;
3. dependency-set closure against caller-supplied resolved dependencies; and
4. the stable public boundary for the semantic validator's existing artifact-
   family metadata.

It also preserves two explicit downstream limitations:

- an Artifact Manifest locator is not independently proven without trusted
  external locator context; and
- scenario and control release subsets have reference-membership semantics,
  not newly invented exact-set equality semantics.

All checks defined here are deterministic coherence checks over inputs supplied
explicitly by the caller.

## 2. Exact-Byte Governing-Document Content Digest

For a governing document that is not a JSON artifact, including a Markdown
research specification, v0.1 defines an **Exact-Byte Document Content Digest**
as:

```text
document_content_digest = SHA-256(exact_governing_document_bytes)
```

Its representation is exactly:

```text
sha256:<64 lowercase hexadecimal characters>
```

The input to SHA-256 is the exact supplied byte sequence. The calculation
performs no:

- RFC 8785 JCS canonicalization;
- JSON parsing;
- character decoding or re-encoding;
- newline normalization;
- Unicode normalization;
- whitespace normalization; or
- platform-default encoding conversion.

A one-byte change therefore changes the digest input and, except for the
ordinary collision limitations of SHA-256, changes the resulting identifier.
This digest establishes exact byte-content equality relative to a trusted
reference value. It does not establish the document's truth, authorship,
authenticity, completeness, authorization, historical existence, or immutable
storage.

## 3. Digest Terminology and Semantic Separation

The governing-document digest MUST be described as either:

- **exact-byte document content digest**; or
- **document byte-content digest**.

It MUST NOT be described as a:

- Canonical Artifact Digest;
- JCS digest; or
- Forensic Byte Digest.

The existing Forensic Byte Digest remains the semantic mechanism for exact raw
or rejected-input preservation. The Exact-Byte Document Content Digest binds
the retained bytes of a governing document. Both mechanisms use SHA-256 over
an exact byte sequence, but sharing the same primitive calculation does not
merge their distinct roles, lifecycle meanings, or claims boundaries.

A non-JSON governing document is not thereby classified as malformed,
rejected, forensic input, or a canonical JSON artifact.

## 4. Approved Low-Level Byte-Hashing Primitive

Stage 12D MAY reuse:

```text
frontier_agent_containment.integrity.forensic_sha256_bytes(...)
```

as the already frozen low-level implementation mechanism because that function
computes SHA-256 over exact supplied `bytes` without parsing, decoding,
normalizing, or rewriting them.

When the primitive is used for a governing document:

- public API names, comments, findings, tests, and reports MUST describe the
  result as an Exact-Byte Document Content Digest;
- the governing document MUST NOT be classified as rejected or forensic input;
- the manifest's `content_digest` retains governing-document content-binding
  semantics; and
- no canonical JSON digest may be claimed.

This reuse requires no modification to `integrity.py` and does not broaden that
module's claims.

## 5. Frozen Governing-Document Record

The frozen Reproducibility Manifest governing-document record contains exactly
the relevant fields:

```text
document_id
document_version
frozen_tag_identity
content_digest
```

It contains no locator. Stage 12D MUST NOT add, derive, synthesize, or assume a
locator for this record.

`document_id` is the governing document's manifest identity for Stage 12D
resolution. It is not a repository path, filename, display title, or Git tag.

## 6. Governing-Document Byte Resolution

The authoritative Stage 12D byte input is conceptually:

```text
governing_document_bytes_by_id:
    Mapping[document_id, exact_bytes]
```

Each governing-document record resolves by exact `document_id` lookup.
Resolution MUST NOT use filename, path, title text, tag name, inferred naming
conventions, or repository traversal.

For the explicitly supplied active governing-document set:

- every manifest `document_id` MUST resolve exactly once;
- a missing `document_id` produces a reproducibility/reference finding;
- duplicate semantic governing-document identities are invalid;
- every supplied governing-document byte entry declared part of the active set
  MUST appear exactly once in the manifest; and
- an unlisted supplied document produces a supplied-set completeness finding.

Mapping key uniqueness supplies at most one byte sequence per `document_id` in
ordinary in-memory mappings. Stage 12D still validates duplicate
`document_id` records in the manifest independently.

This closure is limited to the explicitly supplied active set. It does not
prove that no other governing document existed or was omitted elsewhere.

## 7. Governing-Document Metadata and Tag Coherence

For every governing-document record, Stage 12D validates:

- exact `document_id` resolution;
- `content_digest` against the Exact-Byte Document Content Digest of the
  supplied bytes;
- `document_version` against caller-supplied trusted document metadata when
  that metadata is supplied; and
- `frozen_tag_identity` against caller-supplied trusted document provenance
  when that provenance is supplied.

Trusted metadata MAY be supplied conceptually as:

```text
governing_document_provenance_by_id:
    Mapping[document_id, trusted_document_metadata]
```

Trusted document metadata may contain only the explicitly acquired facts
needed for coherence checks, including `document_version` and
`frozen_tag_identity`.

Stage 12D does not invoke Git. A tag string in the manifest does not prove that
the tag exists, is annotated, targets the declared commit, or binds the
supplied document bytes. Stage 12E is responsible for acquiring and validating
actual local Git release provenance.

## 8. Prohibition on Governing-Document Path Inference

Stage 12D MUST NOT contain or derive hidden mappings such as:

```text
research-contract -> docs/research-contract-v0.1.md
```

No unstated repository path may be derived from:

- `document_id`;
- `document_version`;
- `frozen_tag_identity`;
- display or title text; or
- naming conventions observed in the current repository.

The caller supplies exact bytes and any trusted metadata explicitly. Production
manifest validation does not read governing documents from the filesystem.

## 9. Exact Dependency-Set Closure

For Stage 12D reproducibility validation, the dependency entries in the
Reproducibility Manifest MUST equal the caller-supplied authoritative resolved-
dependency set for the declared dependency scope.

Let:

```text
M = dependency name identities recorded in the Reproducibility Manifest
R = dependency name identities in the caller-supplied resolved_dependencies
```

Stage 12D requires:

```text
M == R
```

For each identity in that exact set, the manifest version MUST equal the
authoritative resolved version exactly.

Consequently:

- a manifest dependency absent from `R` is invalid;
- a resolved dependency absent from the manifest is a manifest-incomplete or
  reproducibility-dependency finding;
- a version mismatch is invalid;
- duplicate manifest dependency identities are invalid even if their versions
  differ;
- compatible-version substitution is prohibited;
- `latest` and mutable aliases are prohibited; and
- open ranges or post-execution resolver interpretation are prohibited.

The validator performs no version ordering, compatibility, or constraint
solving.

## 10. Dependency Scope and Acquisition Boundary

Stage 12D does not decide which installed components belong to the research
dependency scope. The caller-supplied `resolved_dependencies` collection is the
authoritative set for the scope being validated.

Stage 12D validates deterministic exact equality against that supplied set. It
does not inspect:

- pip or another package manager;
- the running interpreter;
- installed distributions;
- lock files not explicitly supplied; or
- the operating system environment.

Stage 12E is responsible for acquiring the actual frozen execution-environment
dependency facts and establishing the applicable release dependency scope.
Stage 12D does not claim that caller-supplied dependency facts are
self-authenticating.

## 11. Exact Dependency Name Matching

Dependency names are compared using the exact identity strings already present
in the frozen Reproducibility Manifest record and the caller-supplied
authoritative resolved-dependency records.

Stage 12D MUST NOT perform undocumented package-name normalization, including
case folding, punctuation replacement, distribution-name canonicalization, or
alias resolution. It does not infer that two differently represented names
identify the same dependency.

If a later release-acquisition layer needs Python distribution-name
normalization, that rule must be explicitly designed and frozen at that layer.

## 12. Dependency Distribution Digest Coherence

The frozen dependency entry permits an optional `distribution_digest`.

Where both the manifest entry and authoritative resolved-dependency record
contain a distribution digest, Stage 12D requires exact equality.

If the manifest contains `distribution_digest` but the authoritative record
lacks a trusted digest, Stage 12D reports the dependency/provenance validation
as unresolved or invalid. It MUST NOT accept a manifest's self-asserted digest
as independently verified.

If the authoritative record contains a distribution digest but the manifest
omits the optional field, that omission alone does not violate exact dependency
identity/version closure. A later frozen contract may make distribution
digests mandatory without retroactively changing v0.1.

## 13. Existing Artifact-Family Metadata

The semantic validator already maintains one authoritative mapping of supported
artifact families to:

- schema identity;
- primary identity field, where one exists; and
- version field.

Stage 12D MUST reuse that metadata. It MUST NOT create a second independent
artifact-family registry, copy the mapping into manifest validation, or infer
family metadata from filenames.

Stage 12D MUST NOT import or depend directly on the private `_FamilySpec`
implementation type.

## 14. Stable Public Artifact-Family Boundary

A later separately approved Stage 12D implementation is authorized to make one
minimal forward-compatible change to:

```text
src/frontier_agent_containment/semantic_validation.py
```

The change may expose the already-existing family metadata through a stable
public interface. The preferred shape is conceptually:

```text
ArtifactFamilySpec
ARTIFACT_FAMILY_SPECS
```

or an equivalent read-only accessor such as:

```text
get_artifact_family_spec(family)
```

The public immutable value representation contains only metadata already held
by the semantic validator, conceptually:

```text
family
schema_id
id_field
version_field
```

Exact names may follow existing project conventions.

The public boundary MUST:

- use an immutable/frozen value representation;
- prevent callers from mutating the authoritative registry;
- cover every and only currently supported artifact family;
- preserve existing `SUPPORTED_ARTIFACT_FAMILIES` compatibility;
- fail explicitly for an unknown family; and
- avoid exposing private `_FamilySpec` values as the supported integration
  contract.

This is API exposure of one existing registry, not creation of another
registry.

## 15. Minimal Public-Boundary Change Rule

The future Stage 12D change to `semantic_validation.py` may only expose the
existing metadata. It MUST NOT:

- add or remove a supported artifact family;
- redefine a family name;
- alter a schema ID;
- alter an identity field;
- alter a version field;
- change identity construction for intrinsically unkeyed or composite-
  identity artifacts;
- change structural or semantic validation behavior; or
- change any Stage 9, Stage 10, or Stage 11 finding semantics.

The implementation must derive the public view from the authoritative existing
registry so the two cannot drift independently.

## 16. Public-Boundary Verification

Future Stage 12D tests must establish that:

- every supported family has exactly one public metadata specification;
- public family keys equal `SUPPORTED_ARTIFACT_FAMILIES` keys;
- public specifications cannot mutate the authoritative registry;
- known family metadata matches the semantic validator's actual schema,
  identity-field, and version-field behavior;
- unknown family access fails explicitly; and
- the complete existing Stage 9 through Stage 11 test behavior remains
  unchanged.

Manifest validation MUST depend only on the stable public boundary, not private
attributes or `_FamilySpec`.

## 17. Stage 12D Reproducibility API Clarification

The Stage 12D Reproducibility Manifest validation API accepts conceptually:

```text
governing_document_bytes_by_id
```

rather than `governing_document_bytes_by_locator`.

It MAY additionally accept:

```text
governing_document_provenance_by_id
```

when trusted `document_version` or `frozen_tag_identity` facts are available.
Neither input authorizes implicit filesystem access.

## 18. External Artifact-Manifest Locator Limitation

The Reproducibility Manifest records `artifact_manifest_locator`, while the
Stage 12D validator receives an Artifact Manifest object directly. Without a
separately supplied authoritative external locator/context, Stage 12D:

- validates the Artifact Manifest's complete JCS content digest;
- preserves the locator string as declared reproducibility metadata; and
- does not claim that the locator was independently proven to identify the
  supplied object or to exist on a filesystem.

Stage 12D MUST NOT open the locator. External locator validation remains
DEFERRED to caller-supplied trusted locator provenance or Stage 12E local
release acquisition.

## 19. Scenario and Control Subset Semantics

Stage 12D validates that every `scenario_subset` identity and every
`control_subset` identity resolves within the explicitly supplied active
artifact set.

For a PILOT or CONFIRMATORY release with a Campaign, every declared release
scenario and control condition must be a member of the Campaign's corresponding
declared set. Phase and Campaign compatibility are validated where the frozen
contracts make them unambiguous.

This clarification does not define exact equality between a release subset and
the Campaign set. Stage 12D MUST NOT reject a proper subset solely because it
does not enumerate every Campaign scenario or control condition. Exact-set
closure remains DEFERRED unless a later frozen profile explicitly defines it.

These checks validate declarative membership only. They do not evaluate control
effectiveness or establish runtime M3 independence.

## 20. Claims Boundary

This clarification establishes deterministic content binding, supplied-set
completeness, and provenance coherence rules over explicitly supplied inputs.
It does not establish:

- governing-document truth or authenticity;
- repository or tag authenticity;
- completeness beyond the explicitly supplied active set;
- evidence truth or collection completeness;
- actual dependency or environment acquisition;
- perfect reproducibility of hosted provider services;
- Artifact Manifest locator authenticity;
- immutable or tamper-proof storage;
- authorization;
- system security;
- S0 validity; or
- runtime M3 independence.

A matching digest proves only equality to the bytes or canonical content used
for the comparison, relative to a trusted reference. Caller-supplied provenance
is not self-authenticating. Passing a future Stage 12D validator does not prove
that the declared research package is complete outside the supplied set or
that the evaluated system is secure.

## 21. GREEN/RED Boundary

This clarification and later deterministic Stage 12D manifest validation
remain GREEN only while using caller-supplied local objects, bytes, schema
stores, provenance facts, fixtures, and unit tests.

No runtime isolation, containment, observation, campaign, or model execution is
authorized here.

Before any actual:

- S0 isolation validation;
- M3 enforcement validation;
- network containment validation;
- agent or model execution;
- instrument-validation runtime;
- pilot execution; or
- confirmatory execution,

the project enters a RED stage and:

```text
OUTSIDE-SANDBOX EXECUTION IS NOT AUTHORIZED.
```

A failed sandbox or isolation environment in a RED stage must be repaired and
revalidated rather than bypassed.

## 22. Implementation Gate

This document freezes no source or schema implementation. After this
clarification is separately reviewed and frozen, Stage 12D may be resumed only
under explicit approval and its approved path constraints.

The resumed Stage 12D design must preserve:

- the Exact-Byte Document Content Digest terminology and byte semantics;
- `document_id`-keyed governing-document resolution;
- exact dependency-set closure;
- the single public artifact-family metadata source;
- the external Artifact Manifest locator limitation;
- scenario/control membership without invented equality; and
- all claims and RED-boundary limitations in this document and the frozen
  Integrity & Reproducibility Specification v0.1.

This clarification does not begin Stage 12D implementation or Stage 12E.
