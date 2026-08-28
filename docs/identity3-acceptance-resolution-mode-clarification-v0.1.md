# Identity-3 Acceptance Resolution Mode Clarification v0.1

Status: prospective design clarification. This document freezes the remaining
Identity-3 semantics needed to replace the temporary Identity-2 Instrument
Acceptance 0.2.0 transition guard. It does not modify an executable contract,
implement Identity-3, change a schema, begin Identity-4 or Identity-5, resume
Stage 12E-3, or authorize runtime execution.

## 1. Purpose and governing scope

Identity-3 resolves:

```text
Campaign.instrument_acceptance_reference
    -> Instrument Acceptance 0.2.0.instrument_acceptance_id
```

This clarification freezes:

- historical-versus-prospective resolution-mode selection;
- deterministic mixed 0.1.0/0.2.0 artifact-set behavior;
- no historical fallback after prospective mode is selected;
- exact-reference result taxonomy;
- Pilot behavior when the reference is optional; and
- narrow supersession of temporary Identity-2 tests.

It is governed by Scientific Artifact Identity Closure v0.1, Identity-2
Transition Clarification v0.1, Identity-2 Missing-Version Compatibility
Clarification v0.1, and Scientific Artifact Identity Stage 2 v0.1. Existing
Stage 10 acceptance eligibility and scientific validation remain authoritative.

## 2. Existing executable foundation

Identity-2 already supplies all structural and indexing prerequisites:

- exact Instrument Acceptance 0.2.0 schema dispatch;
- the required intrinsic `instrument_acceptance_id`;
- exact contract metadata retained in `_ArtifactRecord`;
- generic primary-identity indexing in `_ArtifactRegistry.primary`;
- duplicate intrinsic-identity detection; and
- exact lookup through `_ArtifactRegistry.resolve()` and the existing
  `_require_reference()` helper.

Identity-3 requires no new artifact authority, public API, or schema.

## 3. Frozen non-eligibility association fields

The current data model provides exactly three non-eligibility fields that link
an Instrument Acceptance to a Campaign context:

```text
acceptance.campaign_id == campaign.campaign_id
acceptance.instrument_configuration_id == campaign.instrument_configuration_id
acceptance.environment_id == campaign.environment_id
```

In the current internal representation, `campaign.identity` is the structurally
validated `campaign_id`, so implementation may compare
`acceptance.artifact["campaign_id"]` with `campaign.identity`.

The mode-selection association predicate MUST NOT require:

```text
acceptance_state
accepted_for_phase
```

or any validation-result, evidence, component, authority, order, or decision
criterion. Those are scientific compatibility or eligibility checks performed
after identity resolution, not indicators of resolution mode.

## 4. Reference-absent boundary

Resolution-mode selection applies only when the structurally valid Campaign
contains `instrument_acceptance_reference`.

If the field is absent where the Campaign schema permits absence, Identity-3
does not run exact-reference resolution and does not emit a finding solely for
that absence. Existing independent Campaign and acceptance semantics continue.

If the field is absent where structurally required, schema validation remains
authoritative and excludes the invalid Campaign from semantic resolution.

## 5. Prospective mode trigger A: exact 0.2.0 ID claim

When `instrument_acceptance_reference` is present, select prospective 0.2.0
exact-ID mode if its value equals `instrument_acceptance_id` on any
structurally valid Instrument Acceptance 0.2.0 artifact in the active artifact
set.

This trigger applies even when:

- the exact target is linked to a different Campaign or context;
- the exact target is incompatible or ineligible; or
- multiple 0.2.0 artifacts duplicate the referenced ID.

Mode selection may inspect the structurally valid 0.2.0 records and their
retained exact identities before duplicate groups are excluded from successful
primary-ID resolution. It does not select a duplicate target.

## 6. Prospective mode trigger B: linked 0.2.0 acceptance

Also select prospective 0.2.0 exact-ID mode when at least one structurally valid
Instrument Acceptance 0.2.0 artifact satisfies all three association
comparisons in Section 3 for the Campaign.

The reference need not equal that linked artifact's ID for this trigger.
Accordingly, a missing or wrong prospective ID cannot cause historical
fallback merely because a historical acceptance is otherwise compatible.

An ineligible, rejected, expired, or wrong-phase 0.2.0 acceptance remains
capable of selecting prospective mode when it satisfies the three
non-eligibility association fields. Eligibility is evaluated only after exact
identity resolution.

## 7. Historical mode selection

When a reference is present, select historical 0.1 compatibility mode only if:

1. its value does not equal any structurally valid Instrument Acceptance 0.2.0
   intrinsic ID in the active artifact set; and
2. no structurally valid Instrument Acceptance 0.2.0 artifact satisfies the
   three Campaign association fields in Section 3.

An unrelated 0.2.0 acceptance belonging only to another Campaign, Instrument
Configuration, or Environment does not globally force prospective mode unless
the Campaign reference names that artifact exactly.

Reference grammar alone does not select historical mode. Historical and
prospective references intentionally share the `acceptance:<opaque-token>`
shape.

## 8. No historical fallback

Once prospective mode is selected, historical 0.1.0 compatible-candidate
resolution MUST NOT run as a fallback.

This remains true when:

- no exact 0.2.0 ID matches;
- the exact target is incompatible;
- the exact target is ineligible;
- the referenced ID is duplicated; or
- exactly one compatible historical 0.1.0 acceptance exists.

Prospective failure remains prospective failure. No compatible 0.1.0 or
different 0.2.0 artifact may substitute for the referenced target.

## 9. Pure 0.2.0 exact-reference success

In prospective mode, resolve `instrument_acceptance_reference` only against
Instrument Acceptance 0.2.0 `instrument_acceptance_id` values.

Reference resolution succeeds when:

1. exactly one structurally valid 0.2.0 artifact has the referenced ID; and
2. that exact artifact satisfies the existing Campaign acceptance
   compatibility and eligibility requirements.

Successful resolution emits no `PROVENANCE_UNRESOLVED`, `REFERENCE_INVALID`,
or historical compatibility-ambiguity finding. The temporary Identity-2
transition result is superseded.

## 10. Reference does not resolve exactly once

If prospective mode is selected and the reference identifies no unique
Instrument Acceptance 0.2.0 primary record, emit:

```text
code = REFERENCE_INVALID
artifact_family = campaign
field_path = /instrument_acceptance_reference
referenced_artifact_family = instrument_acceptance
referenced_artifact_id = <the supplied reference>
```

Use the existing deterministic message form:

```text
instrument_acceptance reference '<id>' does not resolve exactly once in the active artifact set
```

The exact Python representation may continue to use the existing project
quoting produced by `{identity!r}`. No compatible substitute is considered.

## 11. Duplicate referenced primary identity

When two or more structurally valid Instrument Acceptance 0.2.0 artifacts
carry the same `instrument_acceptance_id`, preserve the existing generic:

```text
DUPLICATE_IDENTITY at /instrument_acceptance_id
```

The duplicated group remains absent from the successful primary index. If a
Campaign references that duplicated ID, prospective mode is selected through
trigger A and `REFERENCE_INVALID` is also emitted at
`/instrument_acceptance_reference` because the reference does not resolve
exactly once.

No duplicate member is selected by input order, version order, or any other
preference.

## 12. Exact target compatibility failure

Identity resolution and scientific compatibility are separate operations. If
the reference resolves to exactly one 0.2.0 artifact but the exact target fails
Campaign, Instrument Configuration, or Environment compatibility, identity
resolution remains successful and the relationship emits existing
`ACCEPTANCE_INVALID` semantics.

The Campaign-owned relationship finding uses:

```text
field_path = /instrument_acceptance_reference
referenced_artifact_family = instrument_acceptance
referenced_artifact_id = <the resolved ID>
```

Its deterministic bounded message must state that the referenced Instrument
Acceptance is incompatible with the applicable Campaign phase, using current
Stage 10 message style. Identity-3 does not emit `REFERENCE_INVALID` for
scientifically incompatible content and does not search for another candidate.

## 13. Exact target eligibility failure

If the exact target exists but fails the existing acceptance-state or
accepted-phase gate, use existing `ACCEPTANCE_INVALID` semantics at the
Campaign relationship. The exact identity remains resolved.

Configuration and Environment mismatches remain governed by the existing
Stage 10 findings as well. Identity-3 neither weakens nor strengthens any
eligibility criterion and never replaces an ineligible referenced target with
an eligible unreferenced acceptance.

## 14. Other acceptance-owned scientific defects

After successful exact identity resolution, existing acceptance-owned
validators continue independently. Validation-result, component-version,
evidence, authority, order, decision-rule, reference, version, completeness,
and other frozen scientific defects retain their existing codes, paths, and
owners.

Those findings do not make the identity unresolved. Identity-3 adds no
`REFERENCE_INVALID` merely because the resolved artifact is scientifically
defective.

## 15. Multiple compatible prospective acceptances

If multiple Instrument Acceptance 0.2.0 artifacts are scientifically
compatible with the Campaign but exactly one has the referenced ID, resolve
that exact artifact.

Historical unique-compatible-candidate ambiguity does not apply in prospective
mode. Other compatible prospective artifacts neither invalidate nor satisfy
the reference.

## 16. Historical 0.1.0 behavior

Historical mode retains the exact existing Stage 10 behavior:

- Instrument Acceptance 0.1.0 has no intrinsic primary ID;
- `instrument_acceptance_reference` remains opaque;
- its literal value is not compared with acceptance content;
- exactly one scientifically compatible historical acceptance is required;
- zero compatible candidates retain existing `ACCEPTANCE_INVALID` behavior;
  and
- multiple compatible candidates retain existing `ACCEPTANCE_INVALID`
  behavior.

Strings that happen to satisfy the `acceptance:<opaque-token>` grammar do not
become prospective references without trigger A or B. Historical fixtures and
Stage 10 expected findings remain unchanged.

## 17. Mixed graph: exact 0.2.0 target

When a Campaign reference exactly identifies one 0.2.0 artifact, trigger A
selects prospective mode even if one or more compatible 0.1.0 acceptances are
also active.

Only the exact 0.2.0 target is considered. A compatible and eligible target
resolves without a reference finding. An incompatible or ineligible target
produces existing `ACCEPTANCE_INVALID` behavior. Historical fallback is
prohibited.

## 18. Mixed graph: linked 0.2.0 with no exact target

When a linked 0.2.0 acceptance satisfies trigger B but the reference identifies
no unique 0.2.0 artifact, prospective mode emits `REFERENCE_INVALID` at
`/instrument_acceptance_reference`.

This result is unchanged by the presence of a unique compatible historical
acceptance. The 0.1.0 candidate does not rescue the prospective reference.

## 19. Mixed graph: opaque-looking reference

When the reference could historically be treated as opaque but a linked 0.2.0
acceptance satisfies trigger B, prospective mode wins. If the value does not
resolve exactly once to a 0.2.0 ID, emit `REFERENCE_INVALID` without historical
fallback.

The shared lexical grammar is not a historical-mode signal.

## 20. Unrelated 0.2.0 acceptance

A valid historical Campaign remains in historical mode when:

- no 0.2.0 acceptance satisfies the three association fields;
- its reference names no 0.2.0 intrinsic ID anywhere in the active set; and
- its historical compatible-candidate relation otherwise satisfies Stage 10.

An unrelated 0.2.0 artifact therefore does not contaminate historical
validation merely by existing in the same active set.

## 21. Cross-Campaign exact target

If Campaign A's reference exactly names a 0.2.0 acceptance linked to Campaign
B, trigger A selects prospective mode for Campaign A. The identity resolves,
but the target fails Campaign compatibility and produces
`ACCEPTANCE_INVALID`.

Campaign A does not fall back to a compatible historical acceptance. This is
resolved identity with incompatible scientific content, not unresolved
identity.

## 22. Pilot reference behavior

The current Campaign schema requires `instrument_acceptance_reference` for
Confirmatory Campaigns but permits it to be absent for Pilot Campaigns.

For Pilot:

- absence causes no Identity-3 reference finding solely because the field is
  absent;
- exact-reference mode selection does not run for the absent field;
- existing Pilot acceptance and scientific behavior remains unchanged; and
- when the optional reference is present, all mode-selection, exact-resolution,
  compatibility, duplicate, and no-fallback rules in this document apply.

Optional presence does not make a supplied value ignorable.

## 23. Confirmatory and malformed-field behavior

The current Campaign schema remains authoritative:

- a missing Confirmatory `instrument_acceptance_reference` fails structural
  validation before Identity-3;
- a malformed reference fails Campaign structural validation before
  Identity-3; and
- a malformed 0.2.0 `instrument_acceptance_id` fails exact Instrument
  Acceptance schema validation and is not indexed.

Identity-3 performs no coercion, normalization, repair, or identity injection.

## 24. Frozen finding matrix

| Prospective condition | Required result |
| --- | --- |
| Exact ID resolves once; target compatible and eligible | no reference finding |
| Reference does not resolve exactly once | `REFERENCE_INVALID` at `/instrument_acceptance_reference` |
| Referenced ID is duplicated | `DUPLICATE_IDENTITY` at `/instrument_acceptance_id` plus `REFERENCE_INVALID` at the Campaign reference |
| Exact target has Campaign/configuration/environment incompatibility | `ACCEPTANCE_INVALID`; identity remains resolved |
| Exact target has state/phase ineligibility | `ACCEPTANCE_INVALID`; identity remains resolved |
| Exact target has another acceptance-owned defect | existing acceptance-owned finding(s); identity remains resolved |
| Multiple compatible 0.2.0 artifacts; one exact target | resolve exact target; no compatibility ambiguity solely from other candidates |

`PROVENANCE_UNRESOLVED` is not a compatibility alias for
`REFERENCE_INVALID` after Identity-3.

## 25. Temporary transition supersession

Identity-3 removes or supersedes the temporary block in
`_validate_campaign_acceptance()` that unconditionally emits:

```text
PROVENANCE_UNRESOLVED
Instrument Acceptance 0.2.0 exact reference resolution is deferred to Identity-3.
```

For prospective Campaign reference resolution after Identity-3:

- a resolvable valid exact reference has no transition finding;
- an unresolvable exact reference uses `REFERENCE_INVALID`; and
- a resolved but incompatible or ineligible artifact uses
  `ACCEPTANCE_INVALID` or its existing acceptance-owned scientific findings.

Unrelated uses of `PROVENANCE_UNRESOLVED`, if any, are outside this
clarification.

## 26. Recorded temporary-trigger defect

Preflight found that the current temporary Identity-2 implementation includes
expected acceptance state and accepted phase in its prospective trigger. The
frozen transition design identified Campaign, Instrument Configuration, and
Environment as the non-eligibility linkage fields and stated that eligibility
must not suppress the transition.

The implementation remained fail-closed because incompatible cases still
produced historical `ACCEPTANCE_INVALID`. Identity-3 supersedes the temporary
trigger and MUST NOT carry its state/phase mode-selection condition forward.
This correction changes no historical Stage 10 behavior.

## 27. No generic mixed-version verdict

Identity-3 adds no `MIXED_VERSION` or equivalent family-level finding. Mixed
artifact sets receive deterministic per-Campaign resolution under Sections
17-21.

Identity-5 remains solely responsible for the later release-level prohibition
on mixed affected-family versions.

## 28. Preferred bounded implementation

Future implementation should:

1. detect reference absence before mode selection;
2. inspect structurally valid 0.2.0 records for exact ID claims and the three
   association fields;
3. select prospective mode before historical compatible-candidate logic;
4. reuse the generic Instrument Acceptance primary-ID index;
5. reuse `_require_reference()` where its exact-once semantics apply;
6. validate the exact target against existing Campaign compatibility and
   eligibility fields;
7. preserve the existing historical compatible-candidate block for historical
   mode; and
8. preserve all existing standalone acceptance validators unchanged.

No broad refactor, second identity index, new artifact authority, or public API
is required.

## 29. Identity-2 temporary-test supersession

The following tests in
`tests/semantic/test_identity2_version_aware_dispatch.py` intentionally encode
temporary Identity-2 transition behavior and may be modified narrowly during
Identity-3 implementation:

```text
test_campaign_bound_prospective_acceptance_is_transitionally_unresolved
test_multiple_prospective_acceptances_are_not_arbitrarily_selected
test_mixed_historical_and_prospective_acceptances_fail_closed
test_transition_findings_are_deterministic
```

They may be renamed or have their expectations updated only as necessary to
express Identity-3 supersession. They must not be deleted merely to obtain a
passing suite.

All other Identity-2 registry and dispatch tests remain protected unless a
direct unavoidable dependency is identified and reported before editing.

## 30. Historical-test protection

Repository history establishes that a later frozen stage may narrowly update
an earlier test that explicitly encodes temporary behavior. That convention
does not authorize rewriting historical scientific semantics.

In particular:

```text
tests/semantic/test_stage10_confirmatory_gating.py
```

remains unchanged. Historical Stage 9, Stage 10, Stage 11, and Stage 12D
assertions remain executable regressions.

## 31. Future implementation scope

After this clarification freezes, expected Identity-3 implementation scope is:

```text
MODIFY:
    src/frontier_agent_containment/semantic_validation.py

MODIFY NARROWLY:
    tests/semantic/test_identity2_version_aware_dispatch.py

CREATE:
    tests/semantic/test_identity3_acceptance_reference_resolution.py
```

No other path is required. Identity-3 changes no schema, frozen document,
manifest validator, release-acquisition code, release gate, or public API. If
implementation demonstrates another required path, work stops for explicit
approval.

## 32. Future test requirements

Identity-3 tests must cover at minimum:

### Historical

1. Valid 0.1.0-only Campaign behavior is unchanged.
2. Zero compatible historical candidates retain the current finding.
3. Multiple compatible historical candidates retain the current finding.
4. A historical opaque reference remains opaque.

### Pure prospective

5. Exact valid 0.2.0 match succeeds.
6. A nonexistent 0.2.0 reference fails exactly.
7. Exact target Campaign mismatch fails compatibility.
8. Exact target Instrument Configuration mismatch fails compatibility.
9. Exact target Environment mismatch fails compatibility.
10. Exact target acceptance-state ineligibility fails eligibility.
11. Exact target accepted-phase ineligibility fails eligibility.
12. Other acceptance-owned defects retain their existing findings.
13. Multiple compatible 0.2.0 acceptances with one exact target resolve it.
14. A duplicated referenced ID fails deterministically.

### Mixed and cross-context

15. Exact 0.2.0 target plus compatible 0.1.0 uses prospective mode.
16. Linked 0.2.0 with no exact target plus compatible 0.1.0 fails without
    fallback.
17. Opaque-looking reference plus linked 0.2.0 uses prospective mode.
18. Unrelated 0.2.0 elsewhere preserves historical mode.
19. Cross-Campaign exact 0.2.0 target resolves identity then fails
    compatibility.

### Pilot and structural behavior

20. Optional Pilot reference absence produces no Identity-3 reference finding.
21. Present valid Pilot reference resolves normally.
22. Present invalid Pilot reference fails normally.
23. Malformed Campaign reference fails structurally.
24. Malformed acceptance ID fails structurally.

### Determinism and immutability

25. Repeated prospective success is identical.
26. Repeated prospective failure is identical.
27. Candidate-order permutations produce identical findings.
28. Validation does not mutate caller input.

Primary final-semantic coverage belongs in the new Identity-3 test file. Narrow
Identity-2 test updates preserve evidence that its temporary boundary was
explicit and is now deterministically superseded without weakening registry or
dispatch coverage.

## 33. Determinism and input immutability

Mode selection uses existential predicates and exact identity counts, not
first-match selection. Exact resolution uses the unique primary index, while
duplicate recognition uses the structurally valid records retained before
duplicate groups are excluded.

Findings retain the project's stable sorting key. Messages contain only stable
Campaign, family, reference, version, and count context. No timestamp, random
value, set iteration, hash iteration, or unstable object representation may
affect output.

Implementation must not mutate Campaigns, Instrument Acceptances, artifact
records, registries, or caller collections. It injects no ID, rewrites no
reference, and performs no in-place candidate sorting.

## 34. Read-only prototype audit

A bounded in-memory prototype applied triggers A and B using the exact current
field names. It kept eligibility outside mode selection and performed no
repository or production-source mutation.

| Probe | Result |
| --- | --- |
| Exact valid 0.2.0 target | prospective success; no finding |
| Exact 0.2.0 target with Campaign incompatibility | prospective `ACCEPTANCE_INVALID` |
| No exact target; linked 0.2.0; compatible 0.1.0 | prospective `REFERENCE_INVALID`; no fallback |
| Exact 0.2.0 target plus compatible 0.1.0 | prospective exact-target success |
| Unrelated 0.2.0 elsewhere plus valid historical relation | historical success |
| Duplicated exact 0.2.0 ID | prospective `DUPLICATE_IDENTITY` plus `REFERENCE_INVALID` |
| Optional Pilot reference absent | no reference resolution or finding solely for absence |
| Optional Pilot reference present and exact | prospective success |
| Cross-Campaign exact target plus compatible historical candidate | prospective `ACCEPTANCE_INVALID`; no fallback |

The probe result was invariant under the tested candidate construction and
requires no data-model or schema evolution.

## 35. Compatibility and supersession audit

This clarification is compatible with the governing artifacts because it:

- implements the identity closure's exact 0.2.0 reference requirement;
- preserves historical 0.1.0 opaque-reference and unique-compatible behavior;
- replaces only the temporary Identity-2 prospective guard;
- retains Identity-2 exact schema and identity dispatch;
- leaves missing-version dispatch semantics unchanged;
- prevents historical fallback after prospective intent is established;
- does not redefine acceptance compatibility or eligibility;
- requires no Campaign, Instrument Acceptance, common, or other schema change;
  and
- keeps release-level mixed-version rejection exclusively in Identity-5.

No additional semantic conflict was found.

## 36. Claims boundary

Identity-3 establishes only:

- deterministic per-Campaign historical/prospective acceptance resolution;
- exact Instrument Acceptance 0.2.0 primary-ID binding;
- no-fallback prospective semantics;
- separation of identity resolution from existing scientific compatibility
  and eligibility; and
- supersession of temporary Identity-2 prospective deferral.

It does not establish artifact authenticity, cryptographic trust, signature
validity, evidence truth, release eligibility, release-level mixed-version
compliance, experimental validity, containment, or system security.

## 37. GREEN/RED boundary

Identity-3 design and its later bounded schema/semantic tests remain GREEN.
This clarification authorizes no model or agent execution, attack-chain
runtime, S0 or M3 runtime, network or egress testing, containment work, Pilot
execution, or Confirmatory execution.

## 38. Freeze conclusion

The historical/prospective mode boundary, mixed-version behavior, exact
reference findings, Pilot optional-reference behavior, and temporary-test
supersession are fully determined. The design fits the current exact contract
metadata, primary-ID index, and schema-first validation pipeline without a new
authority, public API, schema, or historical scientific change.

Identity-3 Acceptance Resolution Mode Clarification v0.1 is semantically ready
to freeze. It does not itself authorize Identity-3 implementation.
