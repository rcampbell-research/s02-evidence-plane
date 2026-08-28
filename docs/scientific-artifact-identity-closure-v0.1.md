# Scientific Artifact Identity Closure v0.1

Status: prospective design clarification. This document freezes identity-closure
architecture only. It does not modify an executable contract, implement the
architecture, resume Stage 12E-3, or authorize release assembly or execution.

## 1. Purpose and governing invariant

This clarification closes the intrinsic-identity gap for every currently
release-relevant supported scientific JSON artifact family whose frozen v0.1.0
contract lacks a primary artifact identity.

The governing release-selection invariant is:

```text
selected scientific JSON artifact
    -> Release Profile.active_artifacts
    -> Artifact Manifest.artifacts
```

`Release Profile.active_artifacts` remains the sole scientific-artifact
selection whitelist. No `support_artifacts`, `reference_only_artifacts`, hidden
active-artifact mechanism, or second scientific selection channel may be
introduced. Every scientific JSON artifact eligible for release selection must
therefore have a stable intrinsic primary artifact identity.

This clarification is governed by the frozen Implementation Contract, Release
Integrity Profile, release-acquisition clarification, and the Stage 12D,
12E-1, and 12E-2 milestones. Where historical behavior is described, the
historical frozen contract remains authoritative for historical content.

## 2. Exact affected-family closure

The current affected set is exactly:

| Artifact family | Historical schema ID | Historical identity field | Version field | Release relevance |
| --- | --- | --- | --- | --- |
| `instrument_acceptance` | `urn:frontier-agent-containment:schema:instrument-acceptance:0.1.0` | none | `acceptance_version` | Pilot/Confirmatory instrument-readiness binding |
| `derived_action_outcome` | `urn:frontier-agent-containment:schema:derived-action-outcome:0.1.0` | none | `outcome_version` | retained post-run action/effect result |
| `derived_run_outcome` | `urn:frontier-agent-containment:schema:derived-run-outcome:0.1.0` | none | `outcome_version` | retained post-run run/H1 result |

The public `SUPPORTED_ARTIFACT_FAMILIES` projection was inspected before this
clarification was authored. These are the only supported entries whose
`ArtifactFamilySpec.identity_field` is `None`; all three can occur in active
scientific graphs and are potentially release-selected. A family-specific fix
for Instrument Acceptance would therefore leave the release invariant open for
the two derived-outcome families. Identity closure is intentionally general.

If a later supported release-relevant family lacks intrinsic primary identity,
it is not silently included here. It requires a separately approved versioned
contract evolution before it is eligible for release selection.

## 3. Historical contract immutability

The historical v0.1.0 resources remain frozen and MUST NOT be modified:

```text
schemas/instrument-acceptance.schema.json
schemas/derived-action-outcome.schema.json
schemas/derived-run-outcome.schema.json
```

Their schema IDs, accepted and rejected instances, fixtures, tests, tags,
composite-resolution rules, and documented limitations remain historically
correct. No ID is inserted into historical artifacts. No historical tagged
content is rewritten, reinterpreted under a new schema, or silently migrated.

## 4. Pre-1.0 contract-version rule

For prospective executable scientific contracts below `1.0.0`:

- a PATCH increment is a backward-compatible correction that does not
  materially change the accepted/rejected instance set; and
- a MINOR increment is backward-incompatible contract evolution, including
  addition of a new required field.

Adding a required intrinsic primary artifact ID is backward-incompatible.
Accordingly, each affected executable contract advances from `0.1.0` to
`0.2.0`. This migration MUST NOT use `0.1.1`, and it does not jump to `1.0.0`
solely because of the required-ID addition.

## 5. Prospective contract resources

The identified contract versions and parallel resources are:

| Family | Version field/value | Prospective resource | Prospective schema ID |
| --- | --- | --- | --- |
| Instrument Acceptance | `acceptance_version = 0.2.0` | `schemas/instrument-acceptance-v0.2.0.schema.json` | `urn:frontier-agent-containment:schema:instrument-acceptance:0.2.0` |
| Derived Action Outcome | `outcome_version = 0.2.0` | `schemas/derived-action-outcome-v0.2.0.schema.json` | `urn:frontier-agent-containment:schema:derived-action-outcome:0.2.0` |
| Derived Run Outcome | `outcome_version = 0.2.0` | `schemas/derived-run-outcome-v0.2.0.schema.json` | `urn:frontier-agent-containment:schema:derived-run-outcome:0.2.0` |

An incompatible future version MUST use a parallel, version-qualified schema
resource rather than overwrite a resource contained in a frozen milestone.
The repository presently has no conflicting version-qualified scientific
schema-path convention, so the paths above are frozen for this migration.

Each prospective schema MUST discriminate the exact `0.2.0` version. It MUST
NOT accept `0.1.0` content as an identified contract. Apart from the new
schema `$id`, exact contract version, required identity property, and lexical
identity constraint, its scientific fields and conditional rules remain the
historical v0.1.0 semantics.

## 6. Instrument Acceptance intrinsic identity

Instrument Acceptance 0.2.0 requires:

```text
instrument_acceptance_id
```

Its lexical form is:

```text
acceptance:<opaque-token>
```

The field MUST satisfy the shared
`common:0.1.0#/$defs/stable_typed_identifier` rule, the exact `^acceptance:`
type prefix, and the existing Campaign/Reproducibility acceptance-reference
limit of 200 characters. The opaque token is nonempty, lower-case under the
shared typed-identifier grammar, contains no whitespace or secrets, and may
use only the existing token characters.

The producer or caller creating the Instrument Acceptance artifact assigns the
ID. Release assembly and manifest assembly only read, validate, and bind the
already-present value. They MUST NOT derive it from a locator, content digest,
Instrument Configuration, Environment, Campaign, acceptance state, Git
identity, or array position.

The ID is ordinary artifact content. The canonical digest of the complete
Instrument Acceptance JSON object therefore binds it naturally. The ID is not
itself a digest.

## 7. Exact Instrument Acceptance reference resolution

For an identified 0.2.0 release graph, both:

```text
Campaign.instrument_acceptance_reference
Reproducibility Manifest.instrument_acceptance_reference
```

MUST equal the exact `instrument_acceptance_id` of the referenced Instrument
Acceptance 0.2.0 artifact.

Prospective validation MUST:

1. resolve the reference by exact intrinsic acceptance ID;
2. require exactly one matching artifact; and
3. require that artifact to pass every existing scientific acceptance
   compatibility rule.

A different acceptance artifact is not sufficient merely because it is
otherwise compatible. Conversely, the new ID is not an acceptance-eligibility
criterion. Eligibility continues to depend on the existing phase,
configuration, environment, Campaign, acceptance state, validation-result,
component-version, evidence, authority, order, and decision-rule semantics.

## 8. Historical Instrument Acceptance mode

Instrument Acceptance 0.1.0 remains identityless. Historical validation may
continue to use the frozen exact unique campaign-compatible match and opaque
reference limitation. Historical fixtures and expected findings MUST remain
unchanged.

Stage 12E release assembly MUST NOT select Instrument Acceptance 0.1.0. Any
Stage 12E release that requires Instrument Acceptance must select an identified
0.2.0 artifact. There is no retroactive ID, synthetic ID, or silent migration.

## 9. Stage 10 acceptance regression boundary

The existing acceptance gates remain authoritative. Prospective implementation
must preserve the behavior exercised through:

- `_validate_instrument_acceptances`;
- `_validate_acceptance_component_versions`;
- `_validate_acceptance_results`;
- `_validate_campaign_acceptance`;
- `_validate_acceptance_evidence`; and
- Stage 12D `_validate_acceptance_context`.

New tests MUST prove that the ID does not alter acceptance eligibility, exact
references resolve by ID, a referenced incompatible acceptance fails, a
compatible wrong-ID acceptance does not satisfy the reference, duplicate
identified acceptance IDs fail, and historical 0.1.0 validation behavior
remains available in historical mode. No scientific acceptance gate may be
weakened.

## 10. Derived Action Outcome intrinsic identity

Derived Action Outcome 0.2.0 requires:

```text
derived_action_outcome_id
```

Its lexical form is:

```text
actionoutcome:<opaque-token>
```

The field MUST satisfy the shared stable typed-identifier rule and exact
`^actionoutcome:` type prefix. The producer creating the outcome supplies the
ID. Release assembly MUST NOT generate it.

`run_id` and `action_id` retain their existing scientific linkage meanings and
are not substitutes for the new primary artifact ID. Terminal-action,
observed-effect, evidence-linkage, authorization, derivation, architecture, and
completeness semantics remain unchanged. Artifact Manifest identity binds to
`derived_action_outcome_id`; semantic linkage continues to be validated
independently through `run_id`, `action_id`, evidence references, and result
rules.

Historical 0.1.0 outcomes remain identityless and retain their frozen same-run
composite semantic resolution.

## 11. Derived Run Outcome intrinsic identity

Derived Run Outcome 0.2.0 requires:

```text
derived_run_outcome_id
```

Its lexical form is:

```text
runoutcome:<opaque-token>
```

The field MUST satisfy the shared stable typed-identifier rule and exact
`^runoutcome:` type prefix. The producer creating the run outcome supplies the
ID. Release assembly MUST NOT generate it.

The existing `run_id` remains the scientific linkage to the Run Manifest and
experimental run. It MUST NOT be overloaded as the primary identity of the
derived result artifact describing that run. H1 exactness, action-outcome
closure, validity, observability, missingness, utility, rerun, evidence, and
derivation semantics remain unchanged. Artifact Manifest identity binds to
`derived_run_outcome_id`; `run_id` linkage remains independently validated.

Historical 0.1.0 run outcomes remain identityless and retain their frozen
run-based semantic resolution.

## 12. Creation-time identity and uniqueness

For all three 0.2.0 families, the producer/caller assigns the primary artifact
ID when the artifact is created. Validation never repairs a missing value, and
Stage 12E-3 contains no ID-generation behavior.

No UUID, randomness, timestamp, or digest-derived allocation rule is imposed.
The token contains no secret. Uniqueness is bounded to the existing
artifact-set and release semantic domain; this clarification makes no claim of
universal cross-repository uniqueness.

Structural validation checks lexical form and required presence. Semantic
artifact-set validation checks duplicate intrinsic IDs. Artifact Manifest
validation checks family/ID uniqueness and exact document binding. Release
Profile selection binds to the same intrinsic ID.

## 13. Release Profile compatibility and sole-whitelist closure

The existing Release Profile `active_artifacts[]` structure already accepts
all three prospective typed IDs and executable version `0.2.0`. No Release
Profile schema change is required.

A prospective Instrument Acceptance selection is represented normally:

```json
{
  "artifact_family": "instrument_acceptance",
  "artifact_id": "acceptance:confirmatory-001",
  "locator": "artifacts/instrument-acceptance.json",
  "expected_artifact_version": "0.2.0"
}
```

Equivalent selections use `actionoutcome:...` and `runoutcome:...`. The
profile selection's `artifact_id` MUST equal the supplied document's intrinsic
primary ID. The optional expected version, when supplied, MUST equal the exact
document version.

Intrinsic identity closure makes all three families selectable through the
sole whitelist. It eliminates any need for a reference-only or hidden artifact
selection channel.

## 14. Artifact Manifest compatibility

The frozen Artifact Manifest contract already provides the generic canonical
entry fields required for each identified 0.2.0 artifact:

```text
artifact_family
artifact_id
artifact_version
locator
schema_id
schema_version
lifecycle_state
phase_context
content_digest
```

No Artifact Manifest schema change and no family-specific manifest algorithm
is required. After version-aware family-contract lookup selects the 0.2.0
specification, the existing generic identity path can compare `artifact_id`
with the corresponding intrinsic field, compare versions and schema identity,
and verify the complete-content digest.

Lifecycle-state and phase-context sourcing are separate Stage 12E-3 assembly
questions and are not resolved or changed by this clarification.

## 15. Reproducibility Manifest and Campaign compatibility

The frozen Reproducibility Manifest and Campaign acceptance-reference grammars
already accept `acceptance:<opaque-token>` and specifically accept
`acceptance:confirmatory-001`. No change to either schema is required.

For an identified 0.2.0 graph, the unchanged reference field prospectively
becomes an exact intrinsic artifact reference through semantic validation.
The field's shape is unchanged; only version-aware resolution distinguishes
identified 0.2.0 behavior from historical opaque 0.1.0 behavior.

The new derived-outcome IDs require no new Reproducibility Manifest fields.
No manifest field is invented for them.

## 16. Common schema compatibility

All three prefixes satisfy the existing stable typed-identifier grammar:

```text
^[a-z][a-z0-9]*:[a-z0-9][a-z0-9._-]*$
```

The 0.2.0 family schemas can reference that existing definition and add their
family-specific prefix constraint locally. `common.schema.json` does not need
to change. It MAY be changed in a future authorized implementation only if an
objective incompatibility is demonstrated; that discovery is a blocker and
requires separate approval rather than a convenience edit.

## 17. Version-aware authoritative family-contract registry

The current `ArtifactFamilySpec` projection assumes one schema/identity
specification per family. Supporting frozen historical and prospective
contracts simultaneously requires one authoritative VERSION-AWARE
family-contract registry keyed by:

```text
(artifact_family, artifact_version)
```

Each family/version contract specification contains at least:

```text
family
artifact_version
schema_id
identity_field
version_field
```

plus the existing metadata needed by semantic validation. The version field is
an invariant discoverable from the entries for one family; any helper that
needs it before dispatch MUST derive it from this same authoritative registry,
not from a second mapping.

Required affected-family entries include:

| Key | Schema ID | Identity field | Version field |
| --- | --- | --- | --- |
| `instrument_acceptance / 0.1.0` | `...:instrument-acceptance:0.1.0` | none | `acceptance_version` |
| `instrument_acceptance / 0.2.0` | `...:instrument-acceptance:0.2.0` | `instrument_acceptance_id` | `acceptance_version` |
| `derived_action_outcome / 0.1.0` | `...:derived-action-outcome:0.1.0` | none | `outcome_version` |
| `derived_action_outcome / 0.2.0` | `...:derived-action-outcome:0.2.0` | `derived_action_outcome_id` | `outcome_version` |
| `derived_run_outcome / 0.1.0` | `...:derived-run-outcome:0.1.0` | none | `outcome_version` |
| `derived_run_outcome / 0.2.0` | `...:derived-run-outcome:0.2.0` | `derived_run_outcome_id` | `outcome_version` |

Ellipses in the table abbreviate only the already-stated project URN prefix;
production values use the complete exact schema IDs in Section 5.

There MUST NOT be two independent registries. One immutable version-aware
registry is the machine authority.

## 18. Legacy public API compatibility

The existing public `SUPPORTED_ARTIFACT_FAMILIES` and
`get_artifact_family_spec(...)` interfaces MUST NOT silently change meaning.
The preferred implementation is a read-only compatibility projection,
generated from the authoritative version-aware registry, that preserves the
historical/current 0.1.0 behavior required by existing callers.

Validators that require exact contract dispatch use a new version-aware lookup,
conceptually:

```text
get_artifact_family_contract_spec(artifact_family, artifact_version)
```

The exact API name may follow project style. The compatibility projection is
not a second metadata authority and MUST NOT be independently maintained.

## 19. Exact version dispatch

Validation first obtains the affected family's established version-field name
from the authoritative registry, reads that exact field from the artifact, and
looks up the exact `(family, version)` contract. Dispatch has no `latest`,
closest, compatible, fallback, or default-upgrade behavior.

An unknown version fails deterministically. A `0.1.0` artifact is validated
against only its historical schema and semantics. A `0.2.0` artifact is
validated against only the identified schema and semantics. Version labels do
not cause content migration or repair.

`validate_artifact_set(...)`, or its prospectively evolved equivalent, MUST
support this exact dispatch while preserving every non-identity scientific
meaning.

## 20. Local schema-store compatibility

The local schema mechanism loads an explicit set of documents keyed by unique
project `$id`, rejects duplicate IDs, validates all references against that
exact local set, and disables external resolution. It does not require one
physical resource per artifact-family name.

The three unique 0.2.0 schema IDs can therefore coexist with the three
historical 0.1.0 IDs in one local store without `$id` collision or remote
resolution. Parallel-resource loading was verified with in-memory prototype
schemas referencing the current common schema. Version-aware dispatch remains
implementable through the current local-only store architecture.

## 21. Stage 12E release-version and mixing gates

For a Stage 12E release, a selected artifact from any affected family MUST use
the identified `0.2.0` contract. Historical `0.1.0` artifacts remain valid for
historical validation but are ineligible for release selection.

Within one active Stage 12E release graph, an affected family MUST NOT contain
both `0.1.0` and `0.2.0` instances. Mixed-version selection fails release
validation. No version is silently upgraded or preferred.

The gate is release-specific and does not delete the ability to validate
historical artifacts independently.

## 22. Artifact-set and manifest uniqueness

For identified artifacts, duplicate primary IDs in the applicable artifact-set
domain fail deterministic semantic validation. Instrument Acceptance reference
resolution requires exactly one artifact with the referenced ID. Artifact
Manifest family/ID uniqueness and exact profile/document/manifest identity
equality continue to apply through the generic path.

For Derived Action Outcome and Derived Run Outcome, the intrinsic primary ID
adds provenance identity but does not replace the frozen composite/run
scientific linkage checks.

## 23. Producer migration boundary

Any producer or fixture that intentionally creates a prospective 0.2.0
Instrument Acceptance, Derived Action Outcome, or Derived Run Outcome MUST
explicitly supply its new primary ID. Schema validation, semantic validation,
and release assembly MUST NOT auto-inject one.

Historical v0.1.0 fixtures remain untouched. Prospective fixtures are new
objects or intentional copies evolved to `0.2.0`; they do not repair or rewrite
historical fixtures.

## 24. Schema-change minimality

Each prospective 0.2.0 schema differs from its historical contract only as
necessary to:

- declare the new unique schema `$id`;
- discriminate the exact `0.2.0` version;
- define the new intrinsic primary ID with its exact lexical constraint; and
- add that ID to `required`.

Every existing required scientific field and conditional rule remains. An
unrelated defect discovered during implementation is reported separately and
is not bundled into identity closure.

## 25. Derived-outcome regression boundary

Prospective Stage 11 tests MUST prove that primary IDs do not change action
terminal-outcome semantics, observed-effect requirements,
unauthorized-executed or unauthorized-blocked logic, run closure, H1 exactness,
evidence linkage, validity, observability, utility, missingness, or rerun
semantics. Only intrinsic artifact identity and exact contract-version binding
change.

## 26. Stage 12D regression boundary

Prospective Stage 12D coverage MUST include:

- generic canonical Artifact Manifest binding for all three 0.2.0 families;
- exact intrinsic-ID binding and mismatch rejection;
- duplicate family/ID rejection;
- schema/version mismatch rejection;
- exact acceptance-reference resolution followed by scientific compatibility;
- continued rejection of identityless 0.1.0 canonical entries; and
- proof that no family-specific Artifact Manifest algorithm was added.

## 27. Stage 12E regression boundary

Prospective Stage 12E coverage MUST prove:

- every selected scientific JSON artifact is selected only through
  `Release Profile.active_artifacts`;
- no reference-only, support-artifact, or hidden selection channel exists;
- the affected families require identified `0.2.0` contracts;
- profile `artifact_id`, document intrinsic ID, and Artifact Manifest
  `artifact_id` are exactly equal;
- profile/document/schema/manifest versions close exactly; and
- mixed 0.1.0/0.2.0 affected-family release selection fails.

## 28. Historical test-preservation inventory

The following current coverage is HISTORICAL — MUST REMAIN:

| Area | Historical dependency that remains frozen |
| --- | --- |
| `tests/schema/test_stage7_contracts.py` | all current Instrument Acceptance v0.1.0 fixtures and structural/conditional tests omit an intrinsic ID and exercise the closed historical schema |
| `tests/semantic/test_stage10_confirmatory_gating.py` | unique compatibility, configuration/environment/phase/state/component/result/evidence gates; `test_opaque_acceptance_reference_is_not_falsely_content_resolved` explicitly preserves v0.1.0 opaque-reference behavior |
| `tests/schema/test_stage6_contracts.py` | current Derived Action/Run Outcome v0.1.0 fixtures and structural/conditional tests omit primary IDs |
| `tests/semantic/test_stage11_postrun_evidence_closure.py` | same-run `(run_id, action_id)` action-outcome resolution, `run_id` run-outcome resolution, duplicate composite identities, closure, H1, evidence, utility, and rerun behavior |
| `tests/schema/test_stage12c_manifest_contracts.py` | existing generic stable artifact-ID and acceptance-reference syntax |
| `tests/reproducibility/test_stage12d_manifest_validation.py` | generic identity/schema/version/digest binding and historical rejection where a family has no bindable intrinsic primary ID |

Prospective coverage is added separately for the new schemas, version-aware
registry and dispatch, exact acceptance reference, unchanged derived-outcome
semantics with IDs, generic Stage 12D bindings, and Stage 12E release gates.
Historical expected behavior is not rewritten to make a prospective test pass.

## 29. Future implementation impact classification

MUST CREATE:

```text
schemas/instrument-acceptance-v0.2.0.schema.json
schemas/derived-action-outcome-v0.2.0.schema.json
schemas/derived-run-outcome-v0.2.0.schema.json
```

and bounded prospective structural/regression tests.

MUST MODIFY prospectively:

- `src/frontier_agent_containment/semantic_validation.py` for one
  version-aware authority, exact dispatch, 0.2.0 identity indexes, and exact
  acceptance-reference semantics;
- `src/frontier_agent_containment/manifest_validation.py` to consume the exact
  version-aware family contract through the existing generic manifest path;
- prospective Stage 7, 10, 11, 12D, and 12E tests as applicable, while
  preserving historical assertions.

MUST NOT MODIFY for identity closure:

- the three historical v0.1.0 schemas;
- frozen design documents or tags;
- `schemas/release-profile.schema.json`;
- `schemas/artifact-manifest.schema.json`;
- `schemas/reproducibility-manifest.schema.json`; or
- `schemas/campaign.schema.json`.

`schemas/common.schema.json` MAY change only if implementation proves an
objective requirement. The compatibility probes establish no such requirement,
so no common-schema change is planned or authorized by this design artifact.

## 30. Bounded implementation sequence

Implementation after this design freezes MUST be split into:

1. **Identity-1 — schemas:** create only the three parallel 0.2.0 schema
   resources and their structural tests.
2. **Identity-2 — registry/dispatch:** implement the single version-aware
   family-contract registry, legacy compatibility projection, local exact
   schema dispatch, and registry tests.
3. **Identity-3 — semantics:** add identified acceptance exact-ID resolution
   and identified derived-outcome validation while preserving historical
   behavior and all existing scientific gates.
4. **Identity-4 — Stage 12D:** add generic manifest integration and regression
   tests for the three identified families.
5. **Identity-5 — Stage 12E:** add release-version eligibility,
   sole-whitelist, exact identity/version closure, and mixed-version rejection
   tests.

These stages require separate authorization. This document implements none of
them.

## 31. Compatibility and conflict-audit record

Read-only and in-memory pre-freeze probes established:

| Probe | Result |
| --- | --- |
| Public family registry has exactly the three affected `identity_field=None` entries | PASS |
| `acceptance:confirmatory-001` satisfies the shared typed-ID rule | PASS |
| `actionoutcome:example-001` satisfies the shared typed-ID rule | PASS |
| `runoutcome:example-001` satisfies the shared typed-ID rule | PASS |
| Existing Release Profile represents all three IDs with expected version `0.2.0` | PASS |
| Existing Artifact Manifest represents generic entries for all three IDs | PASS |
| Existing Reproducibility Manifest accepts `acceptance:confirmatory-001` | PASS |
| Existing Campaign accepts `acceptance:confirmatory-001` | PASS |
| Current local schema store supports simultaneous unique 0.1.0/0.2.0 IDs | PASS |

The audit found no conflict with the Implementation Contract's stable identity,
exact-version, historical-evidence, semantic-breaking-change, or preservation
requirements. It found no conflict with the Release Integrity Profile's sole
caller-authored whitelist, active-scientific-artifact/Artifact-Manifest
boundary, or prohibition on path substitution and repository discovery.

No second registry or second release-selection channel is introduced. The
release, artifact-manifest, reproducibility-manifest, Campaign, and common
schemas need no change for this closure.

## 32. Remaining Stage 12E-3 blockers

Identity closure does not resume or otherwise approve Stage 12E-3. Separate
assembly semantics remain pending for:

- `build_version`;
- Artifact Manifest `manifest_version`;
- Reproducibility Manifest `reproducibility_version`;
- Artifact Manifest `lifecycle_state`;
- Artifact Manifest `phase_context`;
- rejected-input representation metadata;
- the reproducibility-limitation taxonomy and triggers;
- phase-specific subset, reference, and cardinality rules;
- provider metadata; and
- the `NOT_APPLICABLE` Environment assembly rule.

Stage 12E-3 MUST NOT resume until identity-closure implementation is frozen and
the remaining assembly blockers are resolved through separately approved
design.

## 33. Claims boundary

Scientific Artifact Identity Closure establishes only:

- intrinsic primary artifact identity for the three prospective contracts;
- exact version-aware local schema and metadata binding;
- representability through the sole Release Profile whitelist and generic
  Artifact Manifest entry; and
- exact acceptance-reference resolution for identified 0.2.0 graphs.

It does not establish evidence truth, acceptance correctness merely from an
ID, content or Git authenticity, universal uniqueness, package authenticity,
experimental validity, environment hermeticity, containment, or system
security.

## 34. GREEN/RED boundary

Identity-closure design and the bounded future implementation stages remain
GREEN. Synthetic schema and manifest validation does not constitute scientific
or experimental execution.

The RED boundary remains before model or agent execution, attack-chain runtime,
S0 or M3 runtime, network-containment testing, instrument-validation runtime,
Pilot execution, or Confirmatory execution. This clarification authorizes none
of those activities.
