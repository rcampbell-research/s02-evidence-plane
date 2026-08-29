# Identity-5 Release Version Gate Clarification v0.1

Status: prospective design clarification. This document freezes only the
release-specific version-eligibility semantics required for Scientific Artifact
Identity Stage 5. It does not implement Identity-5, resume Stage 12E-3, modify
an executable contract, or authorize release assembly or execution.

## 1. Purpose and authority

This clarification is governed by:

- `scientific-artifact-identity-closure-v0.1`;
- `release-integrity-profile-v0.1`; and
- `identity-stage4-v0.1`.

It resolves the release-specific semantic design blockers identified during the
stopped Identity-5 preflight. It does not resolve the independent Python
illegal-instruction baseline blocker.

The affected scientific artifact families are exactly:

```text
instrument_acceptance
derived_action_outcome
derived_run_outcome
```

The required release-selected contract version for each affected family is:

```text
0.2.0
```

Identity-5 is release-eligibility policy. It does not change the historical
scientific validity of `0.1.0` artifacts under general semantic or manifest
validation.

## 2. Authoritative selected set

`Release Profile.active_artifacts` is the authoritative scientific-artifact
selection whitelist for Identity-5.

Identity-5 policy applies only to artifacts selected through
`active_artifacts`. It does not apply merely because an artifact is:

- present in caller-supplied scientific artifacts;
- present in `Artifact Manifest.artifacts`;
- present elsewhere in the repository; or
- available through a locator.

Identity-5 performs no repository scan, locator discovery, or inference of
additional release-selected artifacts. No second selection channel is created.

## 3. Affected selected-artifact rule

After an `active_artifacts` entry has resolved exactly to a scientific artifact
and its exact scientific contract, Identity-5 applies this rule:

```text
if artifact_family in {
    "instrument_acceptance",
    "derived_action_outcome",
    "derived_run_outcome",
}:
    resolved artifact contract version must equal "0.2.0"
```

A successfully resolved selected affected artifact using `0.1.0` does not
satisfy Stage 12E research-release eligibility. This finding does not change the
artifact's validity outside the release gate.

## 4. Release-specific finding code

Identity-5 introduces the release-specific finding code:

```text
RELEASE_ARTIFACT_VERSION_INELIGIBLE
```

This code means only that a successfully resolved scientific artifact selected
into a research release uses a contract version that is not eligible under the
frozen release profile for that affected family.

It does not mean that the artifact is scientifically invalid, insecure,
corrupt, globally deprecated, or unusable outside Stage 12E research releases.

## 5. Finding path

For a resolved selected affected artifact with an ineligible contract version,
attach `RELEASE_ARTIFACT_VERSION_INELIGIBLE` to the Release Profile active
artifact entry:

```text
/active_artifacts/<index>
```

The optional `expected_artifact_version` field need not exist. The violation is
that the selected artifact is not eligible for the research release, not merely
that an optional expected-version declaration is wrong.

## 6. Deterministic message

Use deterministic bounded wording equivalent to:

```text
selected <artifact_family> artifact uses contract version <actual_version>;
research release eligibility requires version 0.2.0 for this family
```

For example:

```text
selected instrument_acceptance artifact uses contract version 0.1.0;
research release eligibility requires version 0.2.0 for this family
```

Project-consistent punctuation and casing may be used. The family and actual
version must come only from the resolved, validated inputs. The message makes
no security or scientific-validity claim.

## 7. Resolution precedes version eligibility

Identity-5 validation order is:

1. structurally validate the Release Profile;
2. resolve each selected `active_artifacts` entry through the applicable exact
   manifest/scientific-artifact binding;
3. determine the exact resolved scientific contract; and
4. apply the affected-family version gate.

Identity-5 must not infer release-version eligibility from an unresolved
selection.

## 8. Unresolved selected artifact

If an `active_artifacts` entry cannot resolve exactly to a scientific artifact
and exact contract, do not emit
`RELEASE_ARTIFACT_VERSION_INELIGIBLE` for that selection.

Preserve or use the applicable release-selection, reference, or binding failure
defined by the release-validation architecture. Do not guess `0.1.0`, `0.2.0`,
`latest`, or an intended version from an unresolved reference.

## 9. Historical identityless affected artifacts

Affected historical `0.1.0` artifacts remain intrinsically identityless under
their frozen scientific contracts. Identity-4 already prevents them from being
successfully Artifact Manifest-bound as identified scientific artifacts.

When a purported Release Profile selection cannot resolve because the
historical affected artifact is identityless, preserve the earlier exact
resolution or binding failure. Do not additionally emit
`RELEASE_ARTIFACT_VERSION_INELIGIBLE` unless and until the selected artifact has
actually resolved to an exact scientific contract.

This prevents double classification based on an inferred contract.

## 10. Optional expected artifact version

`Release Profile.active_artifacts` may contain the optional field:

```text
expected_artifact_version
```

Identity-5 eligibility does not depend on this field being present. The
authoritative gate uses the resolved scientific artifact contract version.

- If the field is absent, a resolved affected `0.1.0` artifact still receives
  `RELEASE_ARTIFACT_VERSION_INELIGIBLE`.
- If the field is present, any declaration/resolution consistency rule is a
  separate release-validation concern.
- If a selection is unresolved and declares `expected_artifact_version =
  "0.1.0"`, the declaration alone does not produce
  `RELEASE_ARTIFACT_VERSION_INELIGIBLE`.

Expected-version declaration mismatch and release-version eligibility must not
be conflated. The continued read-only preflight must determine whether a
separate declaration-consistency finding is already required and supported.

## 11. Mixed-version consequence

Identity-5 does not require a separate
`RELEASE_MIXED_ARTIFACT_VERSIONS` finding or equivalent. The required-version
rule is sufficient and supplies precise selected-entry attribution.

For selected artifacts from one affected family:

```text
0.2.0 + 0.2.0
    -> version-policy pass

0.2.0 + 0.1.0
    -> 0.2.0 selection passes
    -> 0.1.0 selection receives RELEASE_ARTIFACT_VERSION_INELIGIBLE
    -> release fails eligibility

0.1.0 only
    -> selection receives RELEASE_ARTIFACT_VERSION_INELIGIBLE
    -> release fails eligibility
```

No version is silently upgraded, preferred, repaired, or substituted.

## 12. Multiple valid prospective artifacts

Identity-5 does not prohibit multiple distinct selected artifacts from the same
affected family when every resolved contract is `0.2.0`.

For example, multiple distinct `derived_action_outcome/0.2.0` artifacts pass
the Identity-5 version gate, subject to all independent selection, manifest,
and scientific rules. Artifact multiplicity is not version mixing.

## 13. Absent affected families

Identity-5 does not require all three affected families to appear in every
release. The rule is:

```text
if selected, the resolved affected artifact must use 0.2.0
```

Absence of an affected family is not itself an Identity-5 finding. Separate
phase or cardinality requirements remain outside this clarification.

## 14. Unselected historical artifacts

If caller-supplied scientific artifacts include an affected-family `0.1.0`
artifact that `Release Profile.active_artifacts` does not select, Identity-5
emits no version finding for it. Its existence in the supplied universe is
irrelevant to this release-eligibility gate.

If `Artifact Manifest.artifacts` lists both historical and prospective
artifacts while `Release Profile.active_artifacts` selects only valid
prospective `0.2.0` affected artifacts, Identity-5 likewise emits no version
finding merely because the historical artifact is manifest-listed.

This statement is limited to the Identity-5 version gate. It does not decide or
weaken any independent future release-package membership, assembly, or
completeness rule.

## 15. Unaffected families

For any `artifact_family` outside the exact three-family affected set,
Identity-5 adds no version-eligibility requirement. Existing exact contracts
remain authoritative. Identity-5 does not create a rule that every release
artifact must use `0.2.0`.

## 16. Phase scope

The Identity-5 affected-family version gate applies to all Stage 12E research
release phases:

```text
DEVELOPMENT
INSTRUMENT_VALIDATION
PILOT
CONFIRMATORY
```

Whenever an affected family is selected into any of these phases, its resolved
contract version must be `0.2.0`.

- DEVELOPMENT: selected affected `0.2.0` passes; resolved selected affected
  `0.1.0` is ineligible.
- INSTRUMENT_VALIDATION: the same selected-version rule applies.
- PILOT: the same rule applies without changing the existing nonempty-active
  structural requirement.
- CONFIRMATORY: the same rule applies without changing existing confirmatory
  scientific or acceptance semantics.

Identity-5 creates no new affected-family presence requirement in any phase.

## 17. Dedicated release-validation taxonomy

`ManifestErrorCode` describes Stage 12D manifest defects, and
`AcquisitionErrorCode` describes Stage 12E-2 acquisition defects. Identity-5
must not misuse either code family.

Identity-5 therefore uses a release-specific semantic validation taxonomy. The
future enum and finding type names should follow project style; preferred
conceptual naming is `ReleaseValidationErrorCode` together with an immutable,
deterministically ordered release-validation finding type.

At minimum the taxonomy must support
`RELEASE_ARTIFACT_VERSION_INELIGIBLE`. This clarification adds no unrelated
release finding code.

The exact complete finding type remains a continued-preflight question.

## 18. Dedicated release-validation layer

Identity-5 release-selection policy belongs in a dedicated release-validation
layer. It must not be added to:

```text
semantic_validation.py
manifest_validation.py
release_acquisition.py
```

The stopped preflight found no existing dedicated release validator. The
expected future direction is therefore a dedicated module conceptually named:

```text
src/frontier_agent_containment/release_validation.py
```

The final API and input shape remain subject to completion of the read-only
preflight after baseline health is established. This clarification does not
authorize creating that module.

## 19. General-validator neutrality

Identity-5 must not change the behavior of:

```text
validate_artifact_set()
validate_artifact_manifest()
validate_reproducibility_manifest()
```

These remain general-purpose validators and retain historically valid or
otherwise valid mixed artifact universes outside release-policy enforcement.
Release eligibility is opt-in through the dedicated release-validation layer.

## 20. Identity-4 binding authority

Identity-5 consumes or reuses the exact scientific-artifact identity and
version binding established by Identity-4. It must not recreate competing
semantics for:

- intrinsic identity;
- canonical digest;
- schema binding; or
- locator binding.

Identity-5 answers only whether the resolved selected artifact version is
eligible for the research release.

## 21. Pure validation boundary

Identity-5 performs validation only. It does not:

- create Release Profile files;
- create Artifact Manifests;
- create Reproducibility Manifests;
- create Release Build Records;
- create release directories;
- acquire dependencies, environments, or Git facts;
- create source release tags; or
- create integrity tags.

Those activities remain Stage 12E-3 or later freeze operations.

## 22. Input immutability

Future Identity-5 validation must not upgrade historical artifacts, modify
`active_artifacts`, remove selections, insert
`expected_artifact_version`, rewrite identities, repair digests, or modify
manifests. Validation is read-only over caller-supplied structures.

## 23. Determinism

For identical Release Profile selection and resolved artifact bindings,
Identity-5 requires stable finding code, path, message, and ordering. Findings
must not depend on hash or set iteration order.

Where `active_artifacts` ordering is represented by array index, finding paths
retain those indices. No first-match selection is permitted.

## 24. Claims boundary

`RELEASE_ARTIFACT_VERSION_INELIGIBLE` means only that a selected artifact fails
the frozen research-release contract. It does not prove or imply:

- cryptographic weakness;
- a security vulnerability;
- scientific invalidity;
- artifact corruption;
- historical contract invalidity;
- evidence truth;
- release authenticity; or
- containment or system security.

## 25. Remaining preflight questions

This clarification intentionally does not freeze:

- exact release-validation function signatures;
- the complete release-validation finding dataclass shape;
- the exact selected-entry resolution helper;
- `expected_artifact_version` declaration-consistency taxonomy;
- unresolved active-artifact release-specific finding taxonomy;
- assertion API shape; or
- package export behavior.

These questions must be answered by completing the read-only Identity-5
preflight after the baseline execution blocker is cleared. Identity-5 must not
be implemented from this clarification alone.

## 26. Baseline illegal-instruction blocker

The previous required `1774`-test baseline did not complete. It terminated near
81 percent with:

```text
Fatal Python error: Illegal instruction
```

The termination occurred during:

```text
test_identity3_findings_are_deterministic
```

inside `jsonschema` execution. No inference has been made that this is a
repository defect or an environment defect.

This is an independent BLOCKER. Identity-5 implementation may not begin until
a later authorized read-only baseline-health check establishes an acceptable
clean baseline. The crash is not diagnosed or rerun by this clarification.

## 27. Compatibility audit

The frozen scientific-artifact identity closure, Release Integrity Profile,
Release Profile schema, Stage 12D manifest-validation implementation, and Stage
12E-2 acquisition implementation were re-examined for this clarification.

The audit confirms:

- `Release Profile.active_artifacts` remains the sole Identity-5 scientific
  selection whitelist;
- the version gate applies only after exact selected-artifact resolution;
- all four Stage 12E research-release phases are governed;
- historical general validation remains supported;
- no Identity-5 rule is added to Stage 12D;
- Stage 12E-2 acquisition findings are not repurposed as release-eligibility
  findings;
- no release assembly or acquisition behavior is introduced; and
- no schema change is required by these clarified semantics.

The rule for a manifest-listed but unselected historical artifact is limited to
absence of an Identity-5 version finding. Any independent release membership or
assembly rule remains outside this clarification, avoiding a reinterpretation
of the Release Integrity Profile.

No semantic conflict requiring this document to stop was found.

## 28. Stage 12E-3 boundary

This clarification does not resolve or begin the remaining Stage 12E-3 assembly
questions, including build and manifest versions, lifecycle and phase-context
sourcing, rejected-input metadata, limitation taxonomy, phase subsets and
cardinality, provider metadata, or the `NOT_APPLICABLE` Environment assembly
rule.

Identity-5 pure eligibility validation and Stage 12E-3 deterministic assembly
remain separate work.

## 29. GREEN / RED boundary

This clarification remains GREEN. It authorizes no model or agent execution,
attack-chain runtime, S0 or M3 runtime, containment or network/egress testing,
instrument-validation runtime, Pilot execution, or Confirmatory execution.

## 30. Implementation gate

This document is design only. It does not implement Identity-5, create a
release-validation module, modify tests or schemas, resume Stage 12E-3, stage or
commit content, create a tag, or push repository state.

Identity-5 implementation requires separate approval after:

1. this clarification is reviewed and frozen;
2. the illegal-instruction baseline blocker is cleared by a separately
   authorized read-only health check; and
3. the remaining preflight questions in Section 25 are fully determined.
