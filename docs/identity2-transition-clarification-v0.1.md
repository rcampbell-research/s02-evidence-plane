# Identity-2 Transition Clarification v0.1

Status: prospective design clarification. This document freezes the temporary
fail-closed behavior between Identity-2 exact family/version dispatch and
Identity-3 exact Instrument Acceptance 0.2.0 reference resolution. It does not
modify an executable contract, implement Identity-2 or Identity-3, change
Stage 12D or Stage 12E behavior, or authorize runtime execution.

## 1. Purpose

Identity-2 introduces exact scientific-artifact contract dispatch by
`(artifact_family, artifact_version)`. Instrument Acceptance 0.2.0 can then be
structurally validated and its intrinsic `instrument_acceptance_id` retained,
but Identity-3 remains responsible for resolving a Campaign acceptance
reference by that ID.

During this interval, the historical Instrument Acceptance 0.1.0 rule cannot
be applied to a Campaign-bound 0.2.0 graph. That historical rule selects one
scientifically compatible acceptance while intentionally treating
`Campaign.instrument_acceptance_reference` as opaque. Applying it to 0.2.0
could claim that a wrong referenced ID is valid. Identity-2 therefore adds the
temporary fail-closed transition rule frozen below.

This clarification does not define or implement the final 0.2.0 exact-reference
semantics. Identity-3 supersedes the transition rule.

## 2. Governing compatibility

This clarification is governed by the frozen Scientific Artifact Identity
Closure v0.1, Identity Stage 1 v0.1, the declared-`$id` schema-discovery
prerequisite, and the Stage 12E-2 implementation baseline.

It is consistent with the identity-closure contract because it:

- preserves exact family/version contract selection;
- preserves all historical 0.1.0 behavior;
- does not reinterpret opaque 0.1.0 references as intrinsic IDs;
- does not claim final 0.2.0 reference resolution;
- fails closed only at the prospective Campaign/acceptance relationship that
  Identity-3 must resolve; and
- can be removed cleanly when Identity-3 supplies exact-ID resolution.

## 3. Authoritative version-aware registry

Identity-2 uses one authoritative immutable mapping keyed by the exact tuple:

```text
(artifact_family, artifact_version)
```

Conceptually:

```text
ARTIFACT_FAMILY_CONTRACT_SPECS[(family, artifact_version)]
```

Each immutable value is conceptually an `ArtifactFamilyContractSpec` with:

```text
family
artifact_version
schema_id
identity_field
version_field
```

The mapping and its values are the sole metadata authority. A project-style
frozen, slotted dataclass and `MappingProxyType`, or an exactly equivalent
immutable construction, must prevent callers from mutating contract metadata
or the registry.

Registry construction must reject a duplicate tuple key before mapping
insertion. Last-write-wins behavior is prohibited. For every entry, the tuple
key must equal the value's `family` and `artifact_version`, and the final
version component of `schema_id` must equal `artifact_version`. Any mismatch is
a deterministic construction or test failure.

## 4. Family version-field projection

Exact dispatch must know a family's version-field name before it knows the
artifact version. Identity-2 may derive a private, read-only
`family -> version_field` projection from the authoritative contract registry.
The projection is an index over the same authority, not a second independently
maintained registry.

Construction must assert that every registered contract version for a family
uses one invariant `version_field`. The current dual-version invariants are:

| Family | Invariant version field |
| --- | --- |
| `instrument_acceptance` | `acceptance_version` |
| `derived_action_outcome` | `outcome_version` |
| `derived_run_outcome` | `outcome_version` |

An inconsistent family-level version field is a deterministic registry
construction or test failure.

## 5. Frozen counts

The Identity-2 registry and local schema-store counts are:

| Inventory | Count |
| --- | ---: |
| Unique supported family names | 21 |
| Historical 0.1.0 contract specifications | 21 |
| Prospective 0.2.0 contract specifications | 3 |
| Total family/version contract specifications | 24 |
| Dual-version families | 3 |
| Local schema resources | 29 |

`SUPPORTED_ARTIFACT_FAMILIES` remains a 21-family compatibility surface. It
must not become a 24-entry family/version collection.

## 6. Legacy public API preservation

The public `ArtifactFamilySpec` shape, immutability, equality, and meaning
remain unchanged:

```text
schema_id
identity_field
version_field
```

`SUPPORTED_ARTIFACT_FAMILIES` remains the read-only historical/current 0.1.0
compatibility projection. `get_artifact_family_spec(family)` continues to
return that 0.1.0 compatibility specification and continues to raise
`KeyError` for an unknown family.

For an affected dual-version family, neither interface may silently return
0.2.0, the latest version, the highest version, or a preferred version. The
legacy projection must be generated from the authoritative registry rather
than maintained as a second metadata authority. No historical caller is
silently migrated.

## 7. Exact-version public lookup

Identity-2 may add the exact public lookup:

```text
get_artifact_family_contract_spec(family, artifact_version)
```

The exact name may follow project style, but its semantics are frozen. It:

- requires both family and version strings;
- performs one exact tuple lookup;
- returns the immutable exact contract specification;
- raises `KeyError` for an unknown family or an unknown family/version pair;
  and
- provides no latest, closest, compatible, preferred, coercion, default, or
  fallback behavior.

No additional public supported-version inventory is required by this
clarification. Tests may derive supported versions from the authoritative
registry without creating another public authority.

## 8. Exact dispatch pipeline

For each supplied artifact, Identity-2 dispatch proceeds in this exact order:

1. Obtain `artifact_family` from the caller's outer artifact-family mapping
   key.
2. Obtain the family's invariant `version_field` from the derived projection.
3. Require the supplied artifact to be a mapping/object.
4. Require the exact `version_field` to exist.
5. Require its value to be a string; do not coerce it.
6. Perform exact `(artifact_family, artifact_version)` lookup.
7. Obtain the exact contract's `schema_id` and `identity_field`.
8. Obtain that exact schema from the caller-supplied local schema store.
9. Structurally validate the artifact against only that schema.
10. Extract the exact contract's intrinsic identity when `identity_field` is
    present.
11. Continue the existing scientific semantic handlers, subject to the
    temporary Instrument Acceptance transition rule in this document.

There is no default to 0.1.0 and no validation against a different contract
version after any dispatch failure.

## 9. Deterministic dispatch failures

The following failures occur before validation against an arbitrary schema:

| Condition | Finding code | Field path |
| --- | --- | --- |
| Recognized family, missing version field | `VERSION_INVALID` | `/<family-version-field>` |
| Recognized family, non-string version | `VERSION_INVALID` | `/<family-version-field>` |
| Recognized family, unsupported exact version | `VERSION_INVALID` | `/<family-version-field>` |
| Exact contract exists, exact local schema is absent | `SCHEMA_INVALID` | `/` |
| Unknown artifact family | existing `UNSUPPORTED_ARTIFACT_FAMILY` behavior | existing convention |

The version value is never coerced. Before a safe intrinsic identity has been
structurally established, the stable label `<family:ordinal>` may identify the
finding. Dispatch must not guess an artifact ID from a scientific linkage
field or any other property.

## 10. Exact contract metadata in internal records

An internal artifact record must retain the exact selected contract metadata
from dispatch. At minimum it must retain, directly or through its exact
contract specification:

```text
artifact_family
artifact_version
schema_id
identity_field
exact contract specification
```

This is internal state only; unnecessary metadata need not become public.
Internal consumers such as `_ArtifactRegistry` and `_records()` must use this
retained exact metadata. They must not call
`get_artifact_family_spec(family)` and reinterpret a 0.2.0 record through the
legacy 0.1.0 projection.

## 11. Historical identityless behavior

Identity-2 preserves historical 0.1.0 validation exactly:

- Instrument Acceptance remains without a primary artifact ID and retains its
  stable ordinal label under historical validation.
- Derived Action Outcome retains its scientific linkage/index identity
  `(run_id, action_id)`.
- Derived Run Outcome retains its scientific linkage/index identity `run_id`.
- No synthetic primary ID is created and no historical fixture is migrated.

Primary artifact identity and scientific linkage are separate concepts. For
0.2.0 derived outcomes, `derived_action_outcome_id` and
`derived_run_outcome_id` are the primary artifact identities, while the same
historical `(run_id, action_id)` and `run_id` indexes continue to drive the
scientific linkage and closure checks. Identity-2 must not replace those
indexes with primary artifact IDs.

## 12. Derived-outcome 0.2.0 transition behavior

Read-only probes established that structurally valid Derived Action Outcome
0.2.0 and Derived Run Outcome 0.2.0 artifacts pass their existing scientific
handlers once exact 0.2.0 schema dispatch is supplied. Their scientific fields
are unchanged by Identity Stage 1.

Identity-2 may therefore run the existing derived-outcome handlers unchanged
for 0.2.0. This does not authorize a change to action, evidence, run-closure,
H1, or any other Stage 11 scientific semantics. The primary artifact identity
is retained in addition to, not instead of, the existing linkage indexes.

## 13. Standalone Instrument Acceptance 0.2.0

A structurally valid Instrument Acceptance 0.2.0 may undergo the existing
standalone scientific acceptance checks unchanged. Those checks include the
current configuration, environment, acceptance-state, accepted phase,
validation-result, component-version, evidence, authority, order, and
decision metadata semantics as applicable in the current implementation.

The new `instrument_acceptance_id` does not alter scientific eligibility. If
no Campaign acceptance relationship is present in the active graph, the
temporary transition finding below is not emitted merely because an
Instrument Acceptance is version 0.2.0.

## 14. Campaign-bound Instrument Acceptance 0.2.0 transition block

Until Identity-3 implements exact intrinsic reference resolution, every
Campaign-bound Instrument Acceptance 0.2.0 relationship is transitionally
unresolved. Identity-2 must fail closed for that relationship and must not let
the historical opaque-reference/unique-compatible-acceptance rule claim that
the prospective relationship is valid.

This transition result applies even if:

- `Campaign.instrument_acceptance_reference` text equals the prospective
  artifact's `instrument_acceptance_id`;
- the reference text differs from that intrinsic ID; or
- one or more otherwise scientifically compatible acceptances exist.

Identity-2 does not authenticate or resolve ID equality. A matching string is
not yet a semantic success, and a wrong string cannot be hidden by selecting a
different compatible acceptance.

## 15. Exact transition trigger

For a Campaign whose acceptance relationship is evaluated, the transition
guard is triggered when the active artifact graph contains at least one
Instrument Acceptance with:

```text
acceptance_version == "0.2.0"
acceptance.campaign_id == campaign.campaign_id
acceptance.instrument_configuration_id == campaign.instrument_configuration_id
acceptance.environment_id == campaign.environment_id
```

These intrinsic scientific linkage fields establish that the prospective
acceptance is relevant to the Campaign. The trigger does not require equality
between `instrument_acceptance_id` and
`Campaign.instrument_acceptance_reference`, because exact reference resolution
is the behavior deferred to Identity-3.

Acceptance state, accepted phase, validation results, and other eligibility
fields remain subject to their existing scientific findings. They do not
suppress the transition finding for an otherwise linked prospective artifact.
Multiple relevant 0.2.0 acceptances do not cause one to be selected. The
relationship remains unresolved, and existing ambiguity or compatibility
findings may coexist where scientifically applicable.

## 16. Transition finding contract

The temporary finding uses the already-existing frozen semantic code:

```text
PROVENANCE_UNRESOLVED
```

This code is present in `SemanticErrorCode` and appropriately represents the
unresolved identity/provenance boundary without declaring an acceptance
scientifically eligible or ineligible merely from its ID.

The finding is owned by the affected Campaign and uses:

```text
artifact_family = "campaign"
artifact_id = <Campaign intrinsic campaign_id>
field_path = "/instrument_acceptance_reference"
referenced_artifact_family = "instrument_acceptance"
referenced_artifact_id = None
message = "Instrument Acceptance 0.2.0 exact reference resolution is deferred to Identity-3."
```

`referenced_artifact_id` remains `None` because Identity-2 has not resolved a
target. It must not echo one candidate ID as though that candidate were
authenticated.

The code, path, message, Campaign context, and ordering are deterministic.
There are no timestamps, set-order-dependent candidate selections, or dynamic
generic-message IDs. Normal global finding sorting continues to provide stable
ordering.

## 17. Mixed 0.1.0 and 0.2.0 acceptance boundary

If the Campaign's scientifically relevant active Instrument Acceptance set
contains both historical 0.1.0 and prospective 0.2.0 artifacts, Identity-2
must not fall back to the historical rule. The linked 0.2.0 artifact triggers
`PROVENANCE_UNRESOLVED`; the Campaign relationship is not prospectively
resolved. Existing ambiguity or compatibility findings may also appear.

This general semantic-validation rule does not implement the later Stage 12E
release rule that rejects mixed affected-family versions. It only prevents the
mixed graph from being falsely reported as having resolved prospective
acceptance provenance.

## 18. Historical-only Campaign behavior

A Campaign graph whose relevant acceptance set contains only Instrument
Acceptance 0.1.0 artifacts retains the exact existing Stage 10 behavior. It
does not receive `PROVENANCE_UNRESOLVED` merely because Identity-2 is present.
The historical exact unique scientifically compatible acceptance gate and the
documented opaque-reference limitation remain frozen.

The existing regression in which a Campaign contains an opaque acceptance
reference that is not a content ID must continue to pass under historical
0.1.0 validation.

## 19. Identity-3 supersession

The transition block is temporary. Identity-3 replaces prospective 0.2.0
transition behavior with the final frozen identity-closure rule:

1. resolve `Campaign.instrument_acceptance_reference` by exact
   `instrument_acceptance_id`;
2. require exactly one matching Instrument Acceptance 0.2.0 artifact;
3. require that exact artifact to satisfy all existing acceptance scientific
   compatibility semantics; and
4. reject a compatible acceptance whose ID is not the referenced ID.

Identity-3 removes or supersedes the temporary `PROVENANCE_UNRESOLVED` result
for fully resolvable 0.2.0 graphs. Historical 0.1.0 behavior remains a separate
historical mode.

Identity-2 must not pre-implement these steps, index a Campaign reference by
`instrument_acceptance_id` for a final decision, change acceptance eligibility,
or modify Stage 10 scientific gates. Its only prospective cross-artifact
acceptance adjustment is the fail-closed guard defined here.

## 20. Manifest and acquisition boundaries

Identity-2 must not modify
`src/frontier_agent_containment/manifest_validation.py`. Keeping the legacy
`get_artifact_family_spec()` projection at 0.1.0 preserves current Stage 12D
semantics. Generic canonical Artifact Manifest integration for 0.2.0 remains
Identity-4 work.

Identity-2 must not modify
`src/frontier_agent_containment/release_acquisition.py`. That module imports no
family metadata and has no Identity-2 behavior change.

If changes confined to semantic validation would indirectly change historical
Stage 12D results, implementation must stop and report the conflict rather
than expanding scope.

## 21. Bounded Identity-2 implementation scope

After this clarification is frozen, the preferred and authorized Identity-2
implementation scope is:

```text
MODIFY ONLY:
    src/frontier_agent_containment/semantic_validation.py

CREATE ONLY:
    tests/semantic/test_identity2_version_aware_dispatch.py
```

If implementation demonstrates that any other path is required, work stops
for explicit approval. Identity-2 does not modify schemas, historical tests,
manifest validation, release acquisition, or release assembly.

## 22. Required Identity-2 tests

### Registry and immutability

Tests must prove:

- 21 family names, 24 exact contract specifications, and three dual-version
  families;
- 21 historical 0.1.0 and three prospective 0.2.0 specifications;
- exact schema IDs, identity fields, and invariant version fields;
- immutable contract values, authoritative registry, derived projection, and
  legacy projection;
- deterministic duplicate-key rejection;
- tuple-key/value agreement and schema-ID/version agreement; and
- deterministic rejection of a family-level version-field inconsistency.

### Public APIs

Tests must prove:

- `ArtifactFamilySpec` shape and behavior remain unchanged;
- `SUPPORTED_ARTIFACT_FAMILIES` remains 21 historical 0.1.0 family specs;
- `get_artifact_family_spec()` returns the historical specs for all three
  affected families and retains `KeyError` for an unknown family;
- exact 0.1.0 and 0.2.0 lookups return the requested contracts; and
- an unknown exact version raises `KeyError` without fallback.

### Dispatch and identity

Tests must prove:

- each affected 0.1.0 artifact dispatches only to its historical schema;
- each affected 0.2.0 artifact dispatches only to its prospective schema;
- missing, non-string, and unknown versions produce `VERSION_INVALID` at the
  exact version-field path;
- a missing exact local schema produces `SCHEMA_INVALID`;
- 0.2.0 intrinsic identities are extracted from the exact contract field;
- historical identityless behavior remains unchanged; and
- derived-outcome linkage indexes remain distinct from primary IDs.

### Scientific handlers and acceptance transition

Tests must prove:

- structurally valid 0.2.0 action and run outcomes pass the unchanged
  scientific handlers and retain Stage 11 results;
- standalone valid 0.2.0 acceptance passes existing standalone scientific
  checks;
- matching-reference Campaign-bound 0.2.0 acceptance emits the frozen
  `PROVENANCE_UNRESOLVED` finding;
- wrong-reference Campaign-bound 0.2.0 acceptance emits the same transition
  finding;
- multiple and mixed 0.1.0/0.2.0 relevant acceptance sets fail closed without
  selecting a candidate; and
- historical 0.1.0-only Campaign behavior remains unchanged.

Existing Stage 9, Stage 10, Stage 11, and Stage 12D test expectations must
remain unchanged. The frozen baseline is 1644 passing tests before Identity-2
adds its new coverage.

## 23. Prototype compatibility audit

Read-only, in-memory probes were performed against the frozen source and the
29-resource local schema store. The probe temporarily selected the already
frozen Instrument Acceptance 0.2.0 schema and identity field in process memory;
it did not change repository source or implement the transition.

| Probe | Existing scientific result | Frozen transition result |
| --- | --- | --- |
| Historical 0.1.0-only Confirmatory Campaign | zero findings | no new transition finding |
| Standalone structurally valid 0.2.0 acceptance | zero findings | no transition finding |
| Campaign-bound 0.2.0, matching reference text | zero findings under current historical logic | `PROVENANCE_UNRESOLVED` required |
| Campaign-bound 0.2.0, wrong reference text | zero findings under current historical logic | `PROVENANCE_UNRESOLVED` required |
| Relevant mixed 0.1.0 and 0.2.0 set | historical fallback could otherwise mask the boundary | `PROVENANCE_UNRESOLVED` required |

The current matching-ID and wrong-ID results demonstrate why fail-closed
transition behavior is necessary. A linkage-only prototype trigger based on
Campaign, Instrument Configuration, Environment, and acceptance version
identified both cases and the mixed case without pretending to resolve the
reference. `PROVENANCE_UNRESOLVED` is an existing valid semantic finding code.

## 24. Claims boundary

This clarification authorizes Identity-2 to establish only:

- one authoritative exact family/version metadata registry;
- exact schema and identity-field dispatch;
- historical public API compatibility; and
- temporary fail-closed Campaign-bound Instrument Acceptance 0.2.0 behavior.

It does not establish exact prospective acceptance reference resolution, full
0.2.0 acceptance provenance closure, Stage 12D 0.2.0 manifest support, Stage
12E release eligibility or assembly, evidence truth, acceptance correctness
from identity alone, content authenticity, Git authenticity, containment, or
system security.

## 25. GREEN/RED boundary

Identity-2 design and later bounded implementation remain GREEN. This work
does not authorize model or agent execution, attack-chain runtime, S0 or M3
runtime, network containment work, Instrument Validation runtime, Pilot
execution, or Confirmatory execution. The RED boundary remains unchanged.

## 26. Implementation stop conditions

Identity-2 implementation must stop for further approval if:

- the authoritative registry cannot remain single-source and immutable;
- exact dispatch requires a schema or production file outside the bounded
  scope;
- `PROVENANCE_UNRESOLVED` cannot represent the transition in the current
  finding contract;
- historical 0.1.0 Campaign behavior changes;
- Stage 12D behavior changes indirectly;
- standalone 0.2.0 acceptance cannot safely undergo the unchanged scientific
  checks; or
- the transition guard would need to perform final exact-ID resolution.

No such blocker was found during the clarification audit.

## 27. Freeze conclusion

The transition architecture is fully determined. Identity-2 can implement
exact version-aware registry, schema, and identity dispatch while preserving
the public 0.1.0 compatibility surface. The Campaign-bound Instrument
Acceptance 0.2.0 boundary fails closed deterministically until Identity-3
replaces that temporary result with exact intrinsic reference resolution.

This clarification is semantically ready to freeze. It does not itself
authorize Identity-2 implementation.
