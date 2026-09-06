# S02 Results Analysis / Closeout v0.1

## 1. Status and scope

S02 v0.1 is a completed, immutable empirical experiment. This document is a post-campaign interpretation of the frozen result; it is not a new experimental stage and does not revise, replace, or rescore any campaign classification.

Research program: **S02 — Adversarial Evidence-Plane Robustness for Bounded Agent Assurance**
Machine program ID: `s02-evidence-plane`

The scope of every finding is the frozen deterministic S02 v0.1 corpus, evaluator, mutation harness, scorer, campaign runner, oracle, and authoritative result.

## 2. Frozen provenance

| Stage | Tag | Commit |
|---|---|---|
| Stage 0 | `s02-stage0-v0.1` | `8f8751ede9fcb2f4f476e4cc63ef037dcd0fc8fa` |
| Stage 1 | `s02-stage1-v0.1` | `4c8c645bd759a5c9f009cd86017be0eaeca72ecb` |
| Stage 2 | `s02-stage2-v0.1` | `09b297f3e9d9d70e7774fe653ad73f2d5dd3c1e4` |
| Stage 3A | `s02-stage3a-v0.1` | `87603959da2b02165337e48c8dcdd34f2fa603b6` |
| Stage 3B | `s02-stage3b-v0.1` | `1fafa1a30cf01e563370ed46cbe05a7909795c13` |
| Stage 3C | `s02-stage3c-v0.1` | `866ae898eadbfc70d5bcd9844360dc399548d416` |

Authoritative campaign result: `results/s02-stage3c-authoritative-campaign-v0.1.json`
SHA-256: `4d273903ff912880ca06ef680614e4169f0bc29a3c4d2acb6a925c767d101e8f`

## 3. Authoritative campaign result

The campaign completed with 42 planned and 42 valid cases, 126 planned and 126 valid B evaluations, and zero exclusions.

| Classification | Count | Rate |
|---|---:|---:|
| `EXACT_SAFE` | 56 / 126 | 0.4444444444444444 |
| `SAFE_CONSERVATIVE` | 47 / 126 | 0.373015873015873 |
| `UNSAFE_FALSE_ESTABLISHMENT` | 23 / 126 | 0.18253968253968253 |

Primary endpoint: `UNSAFE_FALSE_ESTABLISHMENT_RATE`
Preregistered target: `0`
Final primary target disposition: **FAIL**

The authoritative UFER remains **23/126 = 0.18253968253968253 = 18.253968253968253%**. Post-campaign interpretation does not adjust this value.

## 4. B1, B2, and B3 results

| Question | EXACT_SAFE | SAFE_CONSERVATIVE | UNSAFE_FALSE_ESTABLISHMENT |
|---|---:|---:|---:|
| B1 | 36 / 42 (85.71428571428571%) | 3 / 42 (7.142857142857142%) | 3 / 42 (7.142857142857142%) |
| B2 | 15 / 42 (35.714285714285715%) | 8 / 42 (19.047619047619047%) | 19 / 42 (45.23809523809524%) |
| B3 | 5 / 42 (11.904761904761903%) | 36 / 42 (85.71428571428571%) | 1 / 42 (2.380952380952381%) |

Authoritative unsafe counts by baseline were A: 7, B: 9, and C: 7.

Authoritative unsafe counts by attack class were A1: 6, A5: 3, A7: 2, A8: 3, A9: 3, A10: 1, A11: 1, A13: 2, and A14: 2. A2, A3, A4, A6, and A12 produced zero authoritative unsafe classifications in this corpus; those zero counts do not establish general robustness to those attack classes.

## 5. Localization result

Localization had 33 planned and 33 valid eligible evaluations. Twelve were correct:

`12 / 33 = 36.36363636363637%`

All 12 correct localizations came from established B3 outputs. All 21 eligible misses were generic `INCONCLUSIVE` outputs with no supported boundary. The low rate is therefore primarily attributable to conservative boundary withholding and inability to retain supported partial localization, not selection of an incorrect alternative boundary.

The localization metric assesses boundary equality separately from other semantic content. A result can consequently have a correct boundary while overclaiming another semantic dimension.

## 6. Forensic methodology

The forensic analysis was read-only. It compared the raw frozen evaluator proposition and raw strongest-safe oracle proposition for each of the 23 authoritative unsafe pairs, reconstructed their registered `ClaimProfile` states, and identified the exact assertion, withheld dimension, boundary, or scope relation for which the oracle did not entail the evaluator.

The analysis also traced those results through the frozen admission, evaluator, mutation, scorer, and campaign implementations. It did not execute a case, call the evaluator, regenerate a mutation, rescore the campaign, modify an oracle, or alter an authoritative classification.

Human-semantic forensic partition:

| Interpretation | Count |
|---|---:|
| `SUBSTANTIVE_UNSAFE_CONFIRMED` | 21 / 23 |
| `POSSIBLE_SCORER_ARTIFACT` | 2 / 23 |
| `UNRESOLVED` | 0 / 23 |

The two possible artifacts are `s02ep-A-A13 B2` and `s02ep-B-A13 B2`. Both retain their authoritative `UNSAFE_FALSE_ESTABLISHMENT` classifications.

## 7. Root-cause decomposition

| Primary root cause | Count | Share of 23 | Affected pairs | Interpretation |
|---|---:|---:|---|---|
| `RC1_SEMANTIC_BINDING_NOT_PROPAGATED` | 6 | 26.09% | A-A1 B1/B2; B-A1 B1/B2/B3; C-A1 B1 | `IMPLEMENTATION_SPECIFIC` |
| `RC11_SCOPE_OVERCLAIM` | 15 | 65.22% | The substantive unsafe B2 cases associated with A5, A7, A8, A9, A10, A11, and A14 | `ARCHITECTURAL` within S02 v0.1 |
| `RC13_SCORER_NORMALIZATION_ARTIFACT` | 2 | 8.70% | A-A13 B2; B-A13 B2 | `MEASUREMENT_SPECIFIC` |

No unsafe pair remained causally unresolved. No frozen-oracle/scorer registry mismatch, mutation/result inconsistency, or oracle-reference digest mismatch was identified.

## 8. B2 dominant mechanism

The dominant B2 weakness was globalized evidence-set degradation, not retention of evidence already recognized as invalid.

The evaluator applies a global collection/normalization eligibility gate before claim-relative path reconstruction. Localized failures involving ordering, authority, authoritative conflict, postcommit integrity, invocation or effect coverage, or observer coverage can change the canonical evidence set, invalidate collection coverage, and make normalization ineligible. B2 then returns the broad conclusion that no bounded observable-path proposition is admissible.

In 15 substantive unsafe B2 evaluations, that conclusion exceeded the surviving evidence limitation: an unaffected principal path, observed prefix, local sequence, or control-free sequence remained supportable. The architectural weakness was failure to preserve the strongest surviving claim-relative path after localized degradation.

The affected secondary mechanisms were:

| Evidence property | Cases | Count |
|---|---|---:|
| Ordering | A/B/C-A5 | 3 |
| Authority | B/C-A7 | 2 |
| Authoritative conflict | A/B/C-A8 | 3 |
| Effect coverage | A/B/C-A9 | 3 |
| Invocation coverage | A-A10 | 1 |
| Observer coverage | C-A11 | 1 |
| Postcommit integrity | B/C-A14 | 2 |

## 9. A1 semantic-binding finding

A1 changes the request's `event_data.target_resource_id` from `resource:s02-protected` to `resource:s02-mutated-binding` while retaining source identity, event cardinality, ordering, lineage, and a commitment valid for the mutated representation.

The evaluator accepts the mutated request as a deviation root because default-deny authorization and action-ID/path correlation do not consistently reconcile the request resource with surviving downstream execution, effect, or closure evidence. This permits deviation-related B1, B2, and, in B-A1, B3 semantics to survive a resource-binding inconsistency that the frozen oracle requires to weaken deviation status.

This is an end-to-end semantic-binding dependency omission specific to the S02 v0.1 implementation. It does not establish a general property of other evaluators or evidence systems.

## 10. B3 conservative behavior

B3 evaluator raw dispositions were 12 `ESTABLISHED`, 30 `INCONCLUSIVE`, and zero `INADMISSIBLE`.

Of the 12 established outputs, five were exact, six conservative, and one unsafe. All 30 inconclusive outputs were `SAFE_CONSERVATIVE`.

The evaluator's B3 claim language is largely all-or-nothing. When a required item is missing or invalid, the implementation frequently returns generic `INCONCLUSIVE` rather than retaining an oracle-supported narrower local boundary claim. B3 therefore rarely overclaimed in this corpus but was predominantly conservative.

## 11. Measurement and scorer limitation

The raw evaluator outputs for `s02ep-A-A13 B2` and `s02ep-B-A13 B2` were generic `INCONCLUSIVE`. The frozen closed-world scorer normalizes that form to `OBSERVED_PATH`, while the corresponding positive oracle claims normalize to `PRINCIPAL_OBSERVED_PATH`. Under the frozen scope-entailment relation, the principal-path oracle does not entail the broader observed-path evaluator profile, producing `oracle !entails evaluator`.

A direct human reading finds no stronger positive raw evaluator assertion in these two pairs, so they are recorded as possible scorer-normalization artifacts. This is a construct and measurement limitation, not authorization to recode either case or revise UFER.

The scorer's closed-world proposition registry, scope lattice, and exclusion of evidence-basis content from semantic scoring are part of the frozen measurement model.

## 12. Five scientific findings

1. **Claim dependence.** Evidence-plane robustness was strongly claim-dependent in S02 v0.1: B1 had 3/42 unsafe, B2 had 19/42, and B3 had 1/42. B2 accounted for 19/23, or 82.61%, of authoritative unsafe classifications. This percentage does not generalize beyond the frozen corpus.

2. **Claim-relative degradation.** Ordering, authority, conflict, integrity, and coverage failures were generally detected. The dominant B2 weakness was global invalidation of the evidence set instead of retention of the strongest surviving claim-relative path.

3. **Semantic binding.** A1 exposed an end-to-end resource-binding dependency omission: corrupted request-resource binding continued to support deviation-related claims in branches that did not consistently reconcile the resource against downstream evidence.

4. **Safety versus information retention.** B3 produced 5 exact, 36 conservative, and 1 unsafe result. It rarely overclaimed but frequently withheld supported partial boundary claims.

5. **Measurement boundary.** Two A13 B2 authoritative unsafe scores are possible scorer-normalization artifacts, demonstrating that closed-world claim normalization is itself part of the measurement model and its limitations. The authoritative UFER is unchanged.

## 13. Supported claims

The frozen record supports the following bounded claims:

1. In the frozen S02 v0.1 deterministic corpus and implementation, 23 of 126 evaluations received the authoritative `UNSAFE_FALSE_ESTABLISHMENT` classification.
2. The preregistered zero-UFER target failed.
3. B2 accounted for 19 of the 23 authoritative unsafe classifications.
4. Six authoritative unsafe classifications trace to A1 semantic/resource-binding propagation.
5. Fifteen authoritative unsafe classifications trace primarily to broad B2 inadmissibility after localized evidence degradation.
6. Post-campaign forensic analysis confirmed 21/23 as substantive semantic incompatibilities.
7. Two A13 B2 authoritative classifications are possible scorer-normalization artifacts.
8. B3 was predominantly conservative.
9. Low localization retention was primarily caused by withheld supported boundaries rather than incorrect alternative boundaries.
10. Ordering, authority, conflict, integrity, and coverage faults were detected by the evidence machinery, but B2 often globalized their downstream claim effect.

## 14. Claims not supported

The frozen record does not support:

- an 18.25% real-world failure rate or that rate for arbitrary evidence-plane systems;
- a claim that B2 systems or autonomous agents generally are vulnerable;
- estimates of real-world attack prevalence, exploitability, or severity;
- claims about adversary intent or motive;
- a claim that all 23 authoritative unsafe classifications are confirmed substantive evaluator overclaims;
- characterizing the implementation as generally unsafe;
- claims of mitigation effectiveness; or
- universal robustness to A2, A3, A4, A6, or A12 based on their zero unsafe counts in this corpus.

## 15. Limitations

- The corpus is deterministic and synthetic.
- It contains three constructed D/X/E baseline truth classes.
- It contains exactly 14 frozen attack classes.
- It evaluates one evaluator implementation, one frozen scorer, and one campaign.
- There was no live-agent primary run and no frontier-model primary adversary.
- There is no prevalence sampling model.
- The scorer uses a closed-world claim language.
- Two authoritative unsafe classifications are possible scorer-normalization artifacts.
- B3 localization measures boundary equality separately from other semantic overclaim.

## 16. Future work boundary

Later, separately versioned work could evaluate mitigations concerning end-to-end semantic binding, claim-relative path degradation, partial B2/B3 expressiveness, and scorer scope normalization. This closeout neither specifies nor evaluates a mitigation design and does not imply that S02 v0.1 will be rerun.

## 17. Final closeout disposition

**S02 v0.1 is CLOSED.**

Empirical campaign: **COMPLETE**
Primary zero-UFER target: **FAIL**
Authoritative UFER: **23/126 = 0.18253968253968253**
Authoritative result remains unchanged by post-campaign forensic analysis.
Retry: **NOT_AUTHORIZED**
Repair-and-rerun under S02 v0.1: **NOT_AUTHORIZED**

Any mitigation, evaluator change, scorer change, oracle change, or new campaign must be separately versioned future work and cannot replace the S02 v0.1 result.
