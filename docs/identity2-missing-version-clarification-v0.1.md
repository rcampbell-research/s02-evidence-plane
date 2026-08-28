# Identity-2 Missing-Version Compatibility Clarification v0.1

Status: prospective design clarification. This document narrowly supersedes
only the missing-version finding classification in Identity-2 Transition
Clarification v0.1. It does not modify an executable contract, schema, source,
or test; implement Identity-2; or authorize later identity or release stages.

## 1. Purpose

Identity-2 Transition Clarification v0.1 assigns `VERSION_INVALID` when a
recognized artifact family is supplied without its required family-level
version field. Protected historical semantic-validation behavior instead
classifies absence of that required structural field as `SCHEMA_INVALID`.

Confirmed historical examples are:

- a Campaign missing `campaign_version`; and
- a Derived Run Outcome missing `outcome_version`.

Both examples currently produce exactly one `SCHEMA_INVALID` finding. That
historical behavior must remain unchanged. This clarification resolves the
conflict without selecting a fallback contract version or weakening exact
version-aware dispatch.

## 2. Finding taxonomy

For this bounded dispatch boundary:

- `SCHEMA_INVALID` means that the artifact cannot satisfy a structural
  prerequisite needed for exact contract dispatch, including absence of the
  family's required version field; and
- `VERSION_INVALID` means that a version value was actually supplied but is
  unusable for exact contract selection because it is not a string or because
  no exact registered family/version contract exists.

These codes are deterministic validation findings. They are not security
verdicts and do not establish artifact truth, authenticity, eligibility, or
scientific validity.

## 3. Revised missing-version rule

If a recognized artifact family is supplied and its required family-level
`version_field` is absent, validation emits:

```text
code = SCHEMA_INVALID
field_path = /<version_field>
```

The version field remains a required structural contract field. Because no
version value exists, there is no value to classify as an invalid version.
Validation terminates dispatch for that artifact before exact contract lookup.

Absence must not default the artifact to `0.1.0`, `0.2.0`, a latest or current
version, or any other contract. It must not cause validation against a
historical schema merely because that schema is available.

## 4. Present but non-string version

If the required version field exists but its value is not a string, validation
emits:

```text
code = VERSION_INVALID
field_path = /<version_field>
```

Examples include:

```text
campaign_version = 0.1
outcome_version = null
acceptance_version = { ... }
```

The value is not coerced, normalized, stringified, or interpreted as a
different version.

## 5. Present but unsupported version

If the required version field exists as a string but the authoritative
registry contains no exact `(artifact_family, artifact_version)` contract,
validation emits:

```text
code = VERSION_INVALID
field_path = /<version_field>
```

For example:

```text
instrument_acceptance.acceptance_version = "0.3.0"
```

There is no closest-version, compatible-version, latest-version, or historical
fallback lookup.

## 6. Missing exact schema resource

If the version field exists, its value is a string, and an exact
family/version contract specification exists, but that contract's exact
declared schema resource is absent from the caller-supplied local schema store,
validation emits:

```text
code = SCHEMA_INVALID
field_path = /
```

The validator must not use another registered schema version as a fallback.

## 7. Unknown artifact family

An unknown outer artifact-family mapping key retains the existing result:

```text
UNSUPPORTED_ARTIFACT_FAMILY
```

This clarification does not change unknown-family detection, context, path, or
message behavior.

## 8. Frozen dispatch failure matrix

| Input state | Required finding or action |
| --- | --- |
| Unknown artifact family | `UNSUPPORTED_ARTIFACT_FAMILY` |
| Known family; version field absent | `SCHEMA_INVALID` at `/<version_field>` |
| Known family; version present but non-string | `VERSION_INVALID` at `/<version_field>` |
| Known family; version string unsupported | `VERSION_INVALID` at `/<version_field>` |
| Known family; supported version; exact schema absent | `SCHEMA_INVALID` at `/` |
| Known family; supported version; exact schema present | validate against that exact schema only |

No row permits version coercion, inference, schema fallback, latest-version
selection, or silent upgrade.

## 9. Deterministic finding context

Missing, non-string, and unsupported version findings use the exact family
version field path:

```text
/<version_field>
```

Examples include `/campaign_version`, `/outcome_version`, and
`/acceptance_version`.

Before exact contract dispatch and successful structural validation establish
a safe intrinsic identity, validation uses the existing deterministic
placeholder context, such as `<family:ordinal>`. It must not fabricate or guess
identity from `run_id`, `action_id`, an acceptance reference, a locator, or an
arbitrary artifact field.

## 10. Historical compatibility

The revised rule expressly preserves the protected historical behavior:

| Historical input | Result |
| --- | --- |
| Campaign without `campaign_version` | exactly one `SCHEMA_INVALID` |
| Derived Run Outcome without `outcome_version` | exactly one `SCHEMA_INVALID` |
| Equivalent omission of a recognized family's required version field | `SCHEMA_INVALID` |

Existing historical tests and their expectations remain unchanged. They must
not be edited merely to accommodate Identity-2.

Preserving the historical finding code does not mean selecting the historical
0.1.0 contract. The artifact fails before exact lookup because its required
dispatch discriminator is absent.

## 11. Prospective 0.2.0 compatibility

The same missing-field rule applies to prospective contracts. An artifact
supplied under `instrument_acceptance` without `acceptance_version` produces:

```text
SCHEMA_INVALID at /acceptance_version
```

It is not inferred to be Instrument Acceptance 0.1.0 or 0.2.0. By contrast:

- `acceptance_version = 0.2` produces `VERSION_INVALID`;
- `acceptance_version = "0.3.0"` produces `VERSION_INVALID`;
- `acceptance_version = "0.2.0"` with the exact 0.2.0 schema absent produces
  `SCHEMA_INVALID`; and
- `acceptance_version = "0.2.0"` with its exact schema present selects only
  `urn:frontier-agent-containment:schema:instrument-acceptance:0.2.0` for
  structural validation.

## 12. Exact dispatch remains unchanged

When the family version field is present and usable, the frozen Identity-2
architecture remains:

```text
family
    -> invariant version_field
    -> exact supplied string version
    -> exact (family, version) contract spec
    -> exact local schema
    -> structural validation
    -> exact identity-field extraction
```

When the required field is absent, processing for that artifact terminates
before the exact contract lookup with `SCHEMA_INVALID`. This is structural
failure, not fallback dispatch.

All authoritative-registry, immutable-projection, legacy-API, exact-lookup,
internal-record, identity-extraction, and scientific-handler semantics in the
transition clarification remain unchanged.

## 13. Narrow supersession

This document supersedes only statements in Identity-2 Transition
Clarification v0.1 that assign `VERSION_INVALID` to an absent required version
field. In particular, it supersedes that row of the deterministic dispatch
failure table and the corresponding missing-version test requirement.

It does not supersede or alter:

- one authoritative immutable `(family, version)` registry;
- 21 family names, 21 historical specs, three prospective specs, and 24 total
  family/version specs;
- historical `ArtifactFamilySpec`, `SUPPORTED_ARTIFACT_FAMILIES`, and
  `get_artifact_family_spec()` compatibility;
- exact-version lookup with no fallback;
- present non-string version -> `VERSION_INVALID`;
- present unsupported version -> `VERSION_INVALID`;
- supported version with missing exact schema -> `SCHEMA_INVALID`;
- historical identityless behavior;
- Derived Action Outcome `(run_id, action_id)` scientific linkage;
- Derived Run Outcome `run_id` scientific linkage;
- prospective derived-outcome handler compatibility;
- the temporary Campaign-bound Instrument Acceptance 0.2.0
  `PROVENANCE_UNRESOLVED` rule; or
- Identity-3 supersession of that temporary acceptance transition.

## 14. Protected-test audit

The protected historical cases were rerun without editing their source:

```text
tests/semantic/test_stage10_confirmatory_gating.py
    test_structural_validation_precedes_stage10_semantics

tests/semantic/test_stage11_postrun_evidence_closure.py
    test_structural_validation_precedes_postrun_semantics
```

Result:

```text
2 passed
```

Each test confirmed exactly one `SCHEMA_INVALID` finding for its missing
required version-field example.

## 15. Prospective matrix probe

A bounded in-memory prototype applied the revised classification without
modifying production source:

| Probe | Result |
| --- | --- |
| Missing `acceptance_version` | `SCHEMA_INVALID` at `/acceptance_version` |
| `acceptance_version = 0.2` | `VERSION_INVALID` at `/acceptance_version` |
| `acceptance_version = "0.3.0"` | `VERSION_INVALID` at `/acceptance_version` |
| `acceptance_version = "0.2.0"`, exact schema absent | `SCHEMA_INVALID` at `/` |
| `acceptance_version = "0.2.0"`, exact schema present | exact Instrument Acceptance 0.2.0 schema selected |

The probe used an explicit in-memory family/version registry and schema-ID
set. No case inferred or selected the historical schema when the version field
was absent.

## 16. Identity-2 implementation scope

After this clarification is frozen, Identity-2 remains limited to:

```text
MODIFY:
    src/frontier_agent_containment/semantic_validation.py

CREATE:
    tests/semantic/test_identity2_version_aware_dispatch.py
```

No existing historical test, schema, frozen document, manifest-validation
module, release-acquisition module, or release logic is modified by Identity-2
without a later explicit authorization.

## 17. Conflict audit

The revised matrix was audited against Identity-2 Transition Clarification
v0.1, Scientific Artifact Identity Closure v0.1, the two protected historical
tests, and the prospective 0.2.0 schema architecture.

The result is compatible:

- protected historical missing-field behavior is preserved;
- exact version-aware dispatch remains mandatory for present usable versions;
- absence never implies 0.1.0 or any other version;
- prospective 0.2.0 schemas remain exactly selected only by their explicit
  registered version;
- all present-value and missing-schema findings retain their frozen codes; and
- the Campaign-bound Instrument Acceptance 0.2.0 transition rule is unchanged.

No additional conflict was found.

## 18. Claims boundary

This clarification changes only the semantic finding classification for an
absent required family-level version field. It does not change artifact
scientific semantics, schema requirements, executable contract versions,
identity fields, acceptance eligibility, final exact acceptance-reference
semantics, manifest integration, release eligibility, evidence truth,
authenticity, containment, or security properties.

## 19. GREEN/RED boundary

This design clarification remains GREEN. It authorizes no model or agent
execution, attack-chain runtime, S0 or M3 runtime, network containment work,
Pilot execution, or Confirmatory execution. The RED boundary remains
unchanged.

## 20. Freeze conclusion

The missing-version conflict is resolved without fallback or semantic drift.
The corrected classification is `SCHEMA_INVALID` for absence and
`VERSION_INVALID` only when an unusable version value is actually present.
Identity-2 Missing-Version Compatibility Clarification v0.1 is semantically
ready to freeze. It does not itself authorize Identity-2 implementation.
