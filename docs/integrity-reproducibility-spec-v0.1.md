# Integrity & Reproducibility Specification v0.1

## Governing Authority and Status

This design-only specification is subordinate to the frozen:

- Research Contract v0.1
- Threat & Scenario Specification v0.1
- Control Architecture Specification v0.1
- Evidence Specification v0.1
- Instrument Validation Specification v0.1
- Statistical Analysis Plan v0.1
- Implementation Contract / Executable Data Contract v0.1
- executable implementation milestones through
  `implementation-stage11-v0.1`

If this specification conflicts with any frozen governing artifact, the frozen
artifact governs. This document selects integrity and reproducibility semantics
only. It does not implement canonicalization, hashing, manifests, signatures,
storage, evidence collection, runtime validation, agents, controls, S0, M3,
networks, pilot runs, confirmatory runs, or statistical analysis.

Normative terms such as MUST, MUST NOT, REQUIRED, and MAY describe requirements
for later approved implementation stages. They do not authorize those stages.

## 1. Purpose

This specification freezes the semantics that must exist before cryptographic
digests are generated for scored pilot or confirmatory evidence. It distinguishes:

1. deterministic serialization of an eligible JSON value
2. content-integrity identifiers over exact canonical bytes
3. artifact identity established by the applicable artifact contract
4. provenance binding an artifact to its producer, configuration, phase, and
   derivation context
5. evidence ordering and linkage under the frozen Evidence Specification
6. repository and release provenance
7. artifact and reproducibility manifests
8. truth, authenticity, completeness, immutability, and security properties
   that are not established merely by canonicalization or a digest

These layers are complementary. None may silently substitute for another.

## 2. Claims Boundary

A digest under this specification MAY establish only:

- equality of content after both inputs have been accepted into the same frozen
  canonicalization domain and canonicalized by the same algorithm/version
- detection of a content difference relative to a previously trusted digest
- deterministic content identification under the declared digest procedure

A digest by itself DOES NOT establish:

- truth or correctness of an observation
- authenticity or authority of the producer
- immutability
- completeness or absence of omitted evidence
- authorization
- correct attribution, ordering, normalization, or derivation
- system security or containment effectiveness
- tamper-proof, append-only, or WORM storage

The term **tamper-evident** may be used only when a digest or link is compared
with an independently trusted prior value or anchor and only for the specific
content/linkage property checked. The terms **tamper-proof** and **immutable**
must not describe ordinary digests, Git references, filesystems, manifests, or
evidence stores without a separately specified, tested, and demonstrated
property.

The following implications are explicitly invalid:

```text
digest matches        != observation is true
schema valid          != observation is true
semantic checks pass  != system is secure
manifest exists       != package is complete or reproducible
```

## 3. Canonicalization Decision

### 3.1 Selected Standard

The project selects **RFC 8785 — JSON Canonicalization Scheme (JCS)** for v0.1
portable deterministic JSON serialization.

The frozen identifiers for later manifests are:

```text
canonicalization_id       = RFC8785-JCS
canonicalization_version  = RFC8785
canonical_encoding        = UTF-8
```

No Python-only canonical format is permitted. Ordinary use of
`json.dumps(..., sort_keys=True)` is not a claim of JCS conformance.

### 3.2 Compatibility Assessment

RFC 8785 is compatible with the project's JSON artifact model because the
executable contracts use JSON objects, arrays, strings, booleans, null,
integers, and JSON numbers. It is compatible with strict duplicate-member
rejection already implemented by the project. It is cross-language by design
and avoids dependence on insertion order, whitespace, host locale, or platform
default encoding.

Python 3.12 can support a conforming implementation, but later Stage 12B work
must implement or adopt the exact RFC 8785 rules, including ECMAScript-compatible
number serialization and property sorting by UTF-16 code units. Python's
standard JSON encoder alone must not be presumed conformant. Independent
standards-derived vectors are required before use.

JCS uses the I-JSON/IEEE 754 binary64 number model. Some frozen schemas permit
integer values without an explicit cross-language safe-integer maximum. This
does not require changing those schemas, but it does mean that schema validity
alone does not establish canonical-digest eligibility. The later canonicalizer
must reject an artifact containing a number outside the domain in Section 5;
it must never silently round, truncate, coerce, or stringify the value.

This bounded eligibility rule resolves the implementation risk without changing
any frozen artifact meaning. Values requiring precision beyond the JCS number
domain need a future, explicitly versioned string representation in a newly
approved contract; Stage 12A does not retrofit such a representation.

## 4. Duplicate-Key Precondition

Duplicate JSON object member names are invalid.

- Duplicate rejection occurs while parsing the original JSON and before JCS
  canonicalization.
- No last-write-wins, first-write-wins, merge, or repair interpretation is
  permitted.
- Duplicate rejection applies recursively to every object.
- Ambiguous duplicate-key input must not receive a Canonical Artifact Digest or
  be registered as a valid scientific artifact.
- The exact original bytes and a Forensic Byte Digest may still be retained as
  a rejected input under Section 21.

Repeated values in an array are not duplicate object member names; their
validity remains governed by the applicable schema and semantic contract.

## 5. JSON Canonicalization Domain

The accepted canonicalization domain contains only:

- objects whose member names are valid Unicode strings and unique within each
  object
- arrays
- strings
- integers within the interoperable range `-(2^53 - 1)` through `2^53 - 1`
- finite JSON numbers interpreted under IEEE 754 binary64 semantics
- booleans
- null

The following are outside the domain and MUST be rejected before a Canonical
Artifact Digest is assigned:

- NaN, positive Infinity, and negative Infinity
- integers outside the frozen interoperable safe-integer range
- values whose required scientific precision cannot be represented by the
  binary64/JCS model
- unpaired Unicode surrogate code points or otherwise invalid Unicode strings
- bytes, tuples, sets, dates, decimals, custom Python objects, or other
  language-specific values
- mappings with non-string keys
- duplicate object member names

Under JCS, distinct source number spellings that parse to the same permitted
binary64 value may produce the same canonical number serialization. That is a
property of the selected standard, not permission to coerce schema types or to
discard a raw input representation. Scientific quantities requiring decimal or
integer precision beyond this domain must not be represented as ordinary JSON
numbers under v0.1.

## 6. Character Encoding and Unicode

Canonical serialized bytes use UTF-8 without a byte-order mark. Platform-default
encodings are prohibited.

JCS string escaping and object-member ordering apply exactly. Member names are
sorted using their unescaped Unicode string data represented as UTF-16 code
units, as specified by RFC 8785. A later implementation must not substitute
locale collation, UTF-8 byte ordering, Python insertion order, or a different
Unicode comparison.

No Unicode normalization is performed. In particular, canonically equivalent
Unicode sequences remain distinct content when their code-point sequences
differ. Implementations must preserve the parsed string value and must not
silently apply NFC, NFD, NFKC, NFKD, case folding, or locale transformation.

Original raw bytes remain separately preservable under Section 22 even when a
valid JSON string is later represented using JCS escapes.

## 7. Content Digest Algorithm

The v0.1 content-integrity algorithm is SHA-256.

The external text representation is exactly:

```text
sha256:<64 lowercase hexadecimal characters>
```

The algorithm identifier for manifests is `SHA-256`. Uppercase hexadecimal,
omitted algorithm prefixes, base64 substitutions, and implicit algorithm
selection are not equivalent v0.1 digest representations.

SHA-256 is used here as a content-integrity identifier. It is not a digital
signature, does not authenticate a producer, and is not proof of truth,
authority, completeness, or security.

## 8. Artifact Content Digest

For an eligible artifact:

```text
canonical_bytes = RFC8785_JCS(complete_artifact)
artifact_content_digest = SHA-256(canonical_bytes)
```

The displayed value is encoded as specified in Section 7. Every field in the
complete artifact participates. No field is excluded, redacted, defaulted,
normalized, repaired, or transformed during digest calculation unless a future
version of this specification explicitly defines a different artifact type and
boundary.

Two artifacts with identical JCS bytes have the same Artifact Content Digest.
Moving or renaming the file does not change it. Changing any value in the
complete canonical artifact changes the digest except for the theoretical
collision limitation inherent to the algorithm.

The content digest itself does not supply artifact-family, schema, or lifecycle
meaning. A future Artifact Manifest binds the digest to those declarations.
This manifest binding supplies type/version domain separation without changing
the formula above.

Artifact content must not contain a field intended to equal its own complete
content digest. V0.1 uses external manifests, avoiding circular self-digests.

## 9. Artifact Identity and Artifact Manifest

Artifact identity comes from the primary identity and version semantics of the
applicable frozen contract. A digest identifies content; it does not silently
replace `event_id`, `run_id`, `(run_id, action_id)`, configuration identity, or
any other contract identity.

A future Artifact Manifest must bind each retained artifact entry to at least:

- artifact family
- primary artifact ID, or the frozen composite identity where no intrinsic
  artifact ID exists
- artifact version
- relative logical path or another declared locator
- schema ID and schema version
- `canonicalization_id` and `canonicalization_version`
- digest algorithm
- Artifact Content Digest
- lifecycle state where the artifact contract defines one
- run phase where applicable
- validation/acceptance status needed to interpret rejected or retained entries

Filename, path, display name, or digest alone is not artifact identity. Manifest
validation must prove that the identity recorded in an entry matches the
artifact content and the applicable contract.

## 10. Manifest Digests and Circularity

An Artifact Manifest is itself an ordinary versioned JSON artifact eligible for
JCS and SHA-256 after it passes its future structural and semantic validation.
Its digest is computed over its complete content with no self-digest field.

The Artifact Manifest Digest is stored externally, for example in the
Reproducibility Manifest. The Reproducibility Manifest likewise contains no
self-digest field. Its digest is recorded outside that manifest in the release
anchor, such as annotated-tag metadata, release metadata, or a publication
supplement.

This external-digest approach is the v0.1 rule. No implicit field-exclusion
procedure or blank-before-hash convention is permitted.

## 11. Evidence Event Cryptographic Linkage

Run-local cryptographic event hash chaining is **deferred from v0.1**.

The frozen `sequence_number`, `event_id`, `run_id`, and `prior_event_ids`
semantics already establish the authoritative logical ordering and declared
linkage model. A hash chain would add representation and anchoring complexity
without proving event truth or completeness, and the current frozen Evidence
Event Contract does not contain a cryptographic-link field.

V0.1 instead requires individual Evidence Event content digests plus complete
manifest enumeration and an externally anchored manifest digest. A later
approved version may add a run-local `previous_event_digest` mechanism only if
it defines:

- explicit genesis/no-prior representation for the first event
- the exact immediately prior event selected under the run-local total order
- link calculation and verification
- late arrival, gaps, corrections, forks, and reruns
- the trusted anchor and failure behavior

Any future chain supplements rather than replaces `event_id`, `run_id`,
`sequence_number`, and `prior_event_ids`. Even with a trusted chain head, it
could support only bounded tamper-evident ordering/linkage. It would not prove
event truth, completeness, authenticity, causality, or that an omitted event
never existed.

## 12. Ordering and Digests

`sequence_number` remains the authoritative run-local logical ordering
mechanism. Evidence content digests and manifest order must not replace it.

Artifact Manifest entries must not use file enumeration, lexicographic digest
order, filesystem modification time, Git tree order, or wall-clock time as a
substitute for Evidence Event ordering. A digest does not encode elapsed time.
Wall-clock and monotonic-time evidence remain governed separately by the frozen
Evidence Specification.

## 13. Provenance Trust Anchor

The minimum v0.1 research-release provenance anchor consists of:

- the repository's full Git commit object ID and Git object-format identity
- the repository tree state identified by that commit
- an annotated Git tag name, tag object ID, and dereferenced target commit
- an Artifact Manifest Digest
- a Reproducibility Manifest Digest recorded outside that manifest
- the environment/build manifest identity and digest

A Git commit object ID fixes the content addressed by that object, but does not
make repository storage or a movable/deletable reference immutable. An annotated
tag supplies reviewable release provenance; its continued availability and the
trust placed in the repository remain explicit assumptions.

Public Git hosting is not required. A trusted reference may be retained in a
controlled local repository, approved release metadata, a publication
supplement, or more than one independent location. Git provenance does not
prove that a security observation is true or that evidence collection was
complete.

## 14. Reproducibility Manifest

A future Reproducibility Manifest must bind at least:

- repository commit object ID, tree identity, and Git object format
- release/tag name, annotated-tag object ID, and dereferenced target
- Artifact Manifest Digest
- governing document identities and frozen tags
- schema set, schema IDs, and versions
- environment/build identity
- exact dependency identities and versions
- scenario and control subsets
- instrument configuration identity
- instrument acceptance identity/reference and its documented reference limits
- capability evaluation identity
- analysis configuration identity
- campaign, Scheduled Run, Run Manifest, run phase, random-seed, and repetition
  identities
- model/provider identities and configuration where available
- evidence, derived-outcome, exclusion/invalidation, rerun, and analytic-result
  package identities as applicable
- documented unavailable artifacts and resulting reproducibility limitations

Provider-controlled values that cannot be obtained must use an explicit state
such as `UNAVAILABLE` or `NOT_REPORTED`, with the responsible provider/source
and limitation. They must never be guessed, synthesized, or recorded as
`latest`.

The manifest records the package that was declared and checked. Its existence
does not prove that all relevant artifacts were collected or disclosed.

## 15. Environment Reproducibility

The executed research environment must eventually record at least:

- Python implementation and exact version
- every resolved dependency name and exact version
- operating-system/runtime identity and version
- relevant machine architecture
- build configuration and build identity
- locale, timezone, and other execution settings where they can affect results
- container image identity and digest if containers are later adopted
- instrument component implementations/configurations
- evidence, evaluator, canonicalization, and analysis implementation versions

Stage 12A does not select a container runtime, package-lock technology, build
system, or operating system.

## 16. Dependency Freeze

Before pilot or confirmatory execution, the actual executed environment must
have a resolved dependency set containing exact versions. Frozen research
release records must not rely on `latest`, an unbounded compatible range, or a
resolver decision made after execution.

Development packaging may retain version ranges, but those declarations do not
substitute for the resolved environment record. Stage 12A does not create a
lock file or select a dependency-freeze implementation.

## 17. Model and Provider Reproducibility Limits

Hosted frontier-model services may not expose model weights, exact serving
builds, every inference implementation detail, stable deterministic seed
behavior, or historical replay capability.

Every available model name/version, provider identifier, endpoint/configuration
identity, inference parameter, tool/interface version, seed declaration, and
provider-reported build identity must be captured. Unavailable internals must
be marked `UNAVAILABLE` or `NOT_REPORTED` with the resulting limitation.

The project must not fabricate determinism or claim bitwise/model-behavior
reproducibility when the provider cannot support it. Configuration
reproducibility and complete behavioral determinism are distinct claims.

## 18. Raw, Normalized, Derived, and Analytic Integrity

Separate artifact identities, manifest entries, and digests are required for:

1. RAW OBSERVATION
2. NORMALIZED EVIDENCE
3. DERIVED ACTION OUTCOME
4. DERIVED RUN OUTCOME
5. ANALYTIC RESULT

Normalization, derivation, and analysis create new artifacts. They must never
overwrite the original raw bytes or reuse the source artifact's identity.
Corrections and reclassifications create traceable new versions/artifacts and
retain the prior records.

Where raw evidence is not itself eligible JSON, its exact bytes receive a
Forensic Byte Digest rather than a Canonical Artifact Digest. A normalized JSON
artifact may separately receive a Canonical Artifact Digest after validation.

## 19. Derivation Traceability

A future derivation manifest or equivalent structured reference must record:

- output artifact family, identity, version, and content digest
- every material input artifact family, identity, version, and content digest
- derivation or normalization rule identity/version
- evaluator/software/build identity
- configuration and environment identity
- derivation ordering or record identity where applicable

The derivation binding makes exact inputs auditable. It does not prove that the
rule was scientifically correct, that the inputs were true, or that the
implementation executed faithfully; those claims require their own validation.

## 20. Pilot and Confirmatory Separation

Integrity and reproducibility metadata must preserve exactly one original run
phase:

- DEVELOPMENT
- INSTRUMENT_VALIDATION
- PILOT
- CONFIRMATORY

Phase is provenance, not an outcome or mutable publication label. Artifact
manifests, derivation records, release metadata, and reproducibility manifests
must preserve it. A pilot, development, or validation artifact must never be
relabeled as confirmatory. Publication views may select phases but may not
rewrite their original identities.

## 21. Invalid and Rejected Artifacts

V0.1 distinguishes two digest scopes.

### 21.1 Forensic Byte Digest

```text
forensic_byte_digest = SHA-256(exact_original_bytes)
```

This MAY be calculated for any retained byte sequence, including malformed
JSON, duplicate-key JSON, invalid UTF-8, schema-invalid input, or a semantically
rejected artifact. It preserves byte equality only. It does not make the input
a valid JSON artifact or assign scientific artifact identity.

The record must label the digest scope as `FORENSIC_RAW_BYTES`, retain the
rejection reason, and keep the bytes separately from any parsed representation.

### 21.2 Canonical Artifact Digest

A Canonical Artifact Digest is assigned only after:

1. successful strict UTF-8 JSON parsing without duplicate keys
2. successful JCS-domain validation
3. successful applicable structural schema validation
4. successful applicable cross-contract semantic validation
5. deterministic JCS serialization

An invalid or rejected input must not be registered as a valid canonical
scientific artifact. A future diagnostic tool may display canonical bytes for
a domain-valid test value, but that output is not a Canonical Artifact Digest
or artifact registration unless the requirements above are satisfied.

## 22. Original-Byte Preservation

Where raw input/evidence is retained, the exact received bytes must be retained
separately from parsed, canonicalized, normalized, redacted, or derived content.
Canonicalization must never replace the original bytes.

The retained record must bind the original bytes to their Forensic Byte Digest,
source/collection provenance, receipt identity/order, parsing result, and any
later normalized artifact. This requirement applies especially to malformed,
duplicate-key, invalid-Unicode, or otherwise rejected input.

This section defines retention semantics only; it does not select storage.

## 23. Manifest Completeness

A manifest profile must explicitly define the expected artifact classes and
cardinality for its scope. A complete run-level manifest must be capable of
enumerating, as applicable:

- Scheduled Run and Run Manifest
- exact prospective scenario/task/resource, policy/envelope, agent/model,
  autonomy, control, environment, and instrument bindings
- every retained raw and normalized Evidence Event/artifact
- evidence-quality, conflict, correction, invalidation, and rejection records
- every Derived Action Outcome for the run
- the Derived Run Outcome
- benign-utility evidence/results
- rerun relationships
- phase and acceptance/configuration provenance

An analysis/release manifest additionally enumerates campaign, analysis input,
inclusion/exclusion, analysis configuration, analytic-result, and publication
transformation artifacts as applicable.

Each expected item is represented as present, `MISSING_EXPECTED`, or
`REJECTED`, with reason and any available Forensic Byte Digest. Unexpected
retained artifacts are recorded as `UNEXPECTED_RETAINED` and handled under the
frozen profile; they are not silently discarded. A scored release profile may
prohibit unexpected artifacts from the declared analysis set while preserving
them in the audit record.

Manifest enumeration can establish consistency with the declared package. It
does not prove that the collection process observed every event or that no
artifact was omitted outside the declared package.

## 24. Directory and Path Semantics

Paths are locators, not identities.

Manifests may record stable repository-relative paths for reproduction. Paths
must not replace artifact IDs or versions, and path bytes are not included in
an Artifact Content Digest unless the path is an ordinary declared field of a
different manifest artifact.

Moving or renaming an artifact without changing its canonical content does not
change its Artifact Content Digest. A path change may change the containing
manifest, because the manifest's locator field changed, but not the artifact
content digest.

Absolute host paths, credentials, and machine-local secrets must not be placed
in reproducibility metadata.

## 25. Storage Trust Model

V0.1 assumes neither local filesystems nor ordinary Git repositories are
append-only, WORM, tamper-proof, or immutable.

Repository/version-control history supplies traceable content-addressed objects
and references. Digests detect changes only relative to trusted recorded
values. Deletion, replacement of a reference, compromised storage, incomplete
collection, or loss of every trusted anchor remains possible unless a later
storage specification establishes stronger properties.

No storage engine, archival service, retention duration, or public-release
repository is selected here.

## 26. Digital Signatures

Digital signatures are deferred for v0.1. Producer-authentication identities,
key custody, rotation, revocation, verification policy, and failure behavior
are not yet sufficiently defined to select signing keys or algorithms.

SHA-256 plus frozen Git and release provenance is sufficient for the initial
local reproducibility integrity layer, but it does not authenticate an external
producer. If producer authentication becomes required, a separately approved
specification must define the complete signature trust model before signatures
are generated.

## 27. Trust-Anchor Limitation

An unanchored digest is only an assertion about some content at the time it is
presented. Historical integrity checking requires a trusted reference retained
independently of the content being checked.

Expected research anchors include:

- an approved frozen Git commit and annotated tag
- an Artifact or Reproducibility Manifest Digest recorded in release metadata
- an approved publication supplement
- another controlled, independently retained release record

The anchor's provenance and custody must be documented. No artifact may claim
it is trustworthy because its own unanchored digest says so.

## 28. Reproducible Fixture Classes

Future fixture classes are:

- **VALID FIXTURES** — structurally and semantically valid artifact graphs
- **NEGATIVE FIXTURES** — each intentionally violates one identified invariant
- **INTEGRITY FIXTURES** — fixed JCS bytes and independently expected digests
- **REJECTED-INPUT FIXTURES** — malformed JSON, duplicate keys, invalid UTF-8,
  invalid Unicode, non-finite numbers, and other canonicalization-domain errors

Each fixture must have a stable fixture ID, purpose, expected result, and exact
input bytes where byte representation matters. Fixtures must be synthetic and
must not contain real targets, credentials, victims, or production data.

Stage 12A creates no fixture files.

## 29. Canonicalization Test Requirements

Stage 12B tests must cover at least:

- object member ordering, including UTF-16 ordering edge cases
- nested objects and arrays
- Unicode and escaping without undocumented normalization
- integers at accepted boundaries
- representative supported finite binary64 numbers and JCS number rendering
- booleans and null
- equivalent insignificant JSON formatting producing identical canonical bytes
- different content producing independently expected different digests
- duplicate keys rejected before canonicalization
- NaN and positive/negative Infinity rejected
- out-of-range integers and non-JSON Python values rejected
- invalid Unicode rejected
- original raw bytes preserved independently

Appropriate RFC 8785 standards-derived reference vectors should be used without
network retrieval during implementation and without reproducing copyrighted
material beyond applicable licensing limits.

## 30. Digest Test Requirements

Fixed fixtures must carry independently established expected canonical bytes
and exact expected SHA-256 strings. Tests compare output to those fixed values.

The expected value must not be produced at test time by the same implementation
under test. Self-comparisons such as `digest1 == digest1`, round-tripping only,
or computing both expected and actual through one code path are insufficient.
At least one independent implementation or standards-derived vector must
establish each normative expected result before it is frozen.

## 31. Release Freeze Requirements

Before a publishable pilot or confirmatory artifact set is described as frozen,
the release process must establish:

- clean Git status
- full repository commit object ID and tree identity
- annotated tag and dereferenced target
- complete Artifact Manifest
- externally recorded Artifact Manifest Digest
- Reproducibility Manifest and externally recorded digest
- complete structural schema validation
- complete applicable semantic validation
- instrument acceptance identity/reference and its documented resolution status
- exact dependency and environment/build records
- retained invalid/rejected artifact records and declared package completeness

A confirmatory release additionally requires the frozen Analysis Manifest,
Campaign configuration, confirmatory Scheduled Runs, and preserved confirmatory
phase identities.

No release check converts a null result into a security claim or repairs
missing/invalid evidence.

## 32. No Self-Referential Assurance

The following reasoning is prohibited:

```text
the evidence is trustworthy because its own digest says it is trustworthy
the package is complete because its own manifest says it is complete
the observation is true because its schema validates
the system is secure because semantic validation passes
```

Integrity claims require an external trust anchor. Truth, authority,
completeness, experimental validity, and security require their separately
frozen evidence and validation paths.

## 33. Implementation Staging Plan

After this specification is separately approved and frozen, the proposed GREEN
implementation sequence is:

- **Stage 12B — Canonicalization and digest primitives:** strict domain checks,
  RFC 8785 JCS, SHA-256 representation, forensic-byte hashing, and independent
  fixed vectors.
- **Stage 12C — Manifest schemas:** Artifact Manifest, Reproducibility Manifest,
  environment/build, and derivation-binding structural contracts.
- **Stage 12D — Manifest semantic validation and fixture corpus:** identity,
  digest, completeness-profile, phase, derivation, and release-reference checks
  using fixed synthetic fixtures.
- **Stage 12E — Release-integrity audit/freeze:** deterministic package audit,
  anchor verification, release record, and freeze procedure.

Stage 12A does not begin or authorize any of these implementation stages.

## 34. GREEN/RED Boundary

Stages 12A–12E remain GREEN only while they use deterministic local artifacts,
synthetic fixtures, Git, schema validation, semantic validation, digest
calculation, and pure unit tests.

The project becomes RED before any execution of:

- S0 isolation
- M3 enforcement
- network containment
- synthetic attack actions against running services
- actual agents or models
- instrument-validation runtime
- pilot runs
- confirmatory runs

In RED stages, outside-sandbox execution is not authorized. A failed isolation
or sandbox environment must be repaired and revalidated rather than bypassed.

## 35. Current Stage Gate

Current stage:

```text
DESIGN ONLY — INTEGRITY & REPRODUCIBILITY
```

Before Integrity & Reproducibility Specification v0.1 may freeze:

1. Read the complete specification.
2. Re-read the frozen Evidence Specification and Implementation Contract.
3. Audit for contradictions with frozen evidence semantics, overclaimed digest
   properties, ambiguous canonicalization, circular self-digests, path/identity
   confusion, duplicate-key ambiguity, raw-byte loss, digest/authentication
   confusion, unanchored tamper-evidence claims, phase confusion, fabricated
   provider determinism, premature signature/key choices, and runtime scope
   expansion.
4. Classify every finding as BLOCKER, MAJOR, MINOR, or DEFERRED.
5. Verify every prior frozen artifact and tag remains unchanged.
6. Do not stage, commit, tag, or begin Stage 12B without explicit approval.
