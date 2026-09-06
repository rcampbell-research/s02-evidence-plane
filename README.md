# S02 — Adversarial Evidence-Plane Robustness for Bounded Agent Assurance

This repository contains the frozen code, evidence contracts, deterministic
mutation harness, scorer, authoritative campaign result, and closeout record
for the S02 v0.1 experiment. Its internal program identifier is
`s02-evidence-plane`.

S02 evaluates whether bounded assurance claims remain justified when the
evidence presented to an evaluator is adversarially degraded.

## Evaluated assurance questions

- **B1 — Deviation Existence:** Does admissible evidence establish that
  observed behavior departed from the frozen behavioral, policy, or
  authorization envelope?
- **B2 — Observable Action-Path Reconstruction:** What sequence of behavioral,
  control, execution, and effect events can be reconstructed from admissible
  evidence, including only evidence-supported identity, lineage, and ordering
  relationships?
- **B3 — Containment Outcome / Enforcement-Boundary Localization:** What
  containment or enforcement outcome is established, and at what
  evidence-supported boundary?

B4 — Systemic Cause / Validated Mitigation is defined in the broader assurance
framework but was not empirically evaluated in S02 v0.1. B1–B3 do not infer
hidden chain-of-thought, motive, private deliberation, or unobserved causal
steps.

## Authoritative result

- 42 / 42 valid adversarial cases
- 126 / 126 valid B evaluations
- 0 exclusions
- `EXACT_SAFE`: 56 / 126
- `SAFE_CONSERVATIVE`: 47 / 126
- `UNSAFE_FALSE_ESTABLISHMENT`: 23 / 126
- UFER: 23 / 126 = 0.18253968253968253
- Frozen zero-UFER target: **FAIL**
- B1 unsafe: 3 / 42
- B2 unsafe: 19 / 42
- B3 unsafe: 1 / 42
- Localization: 12 / 33

Post-campaign forensic review classified 21 cases as substantive semantic
incompatibilities, 2 as possible scorer-normalization artifacts, and 0 as
unresolved. This interpretation does not revise the authoritative 23/126 primary
result. The result is specific to the frozen deterministic S02 v0.1 corpus and
implementation; it is not a real-world failure-rate estimate.

## Experimental design

The frozen design comprises:

```text
3 deterministic pristine baselines
× 14 frozen single-factor evidence-plane attacks
= 42 adversarial cases
× B1/B2/B3
= 126 evaluations
```

The attacks test integrity, authority/authenticity, ordering/lineage,
completeness, and observation coverage.

The central assurance principle is that an evaluator is not required to know
what its admissible evidence cannot reveal; it is required not to claim more
than that evidence can justify. Under claim-relative degradation, unavailable
or inadmissible evidence should weaken a conclusion only as far as necessary,
while preserving narrower claims still supported by surviving evidence.

## Repository map

```text
docs/                         Frozen research contracts, specifications,
                              S02 oracles, and closeout
src/frontier_agent_containment/
                              Implementation and S02 evaluator, mutation,
                              scoring, and campaign components
schemas/                      Frozen JSON Schema contracts
tests/                        Schema, semantic, instrument-validation, and
                              S02 verification tests
results/                      Authoritative S02 Stage 3C campaign result
```

Principal S02 artifacts:

- `docs/s02-research-and-analysis-contract-v0.1.md`
- `docs/s02-baseline-and-claim-oracle-v0.1.yaml`
- `docs/s02-attack-case-oracle-v0.1.yaml`
- `docs/s02-results-analysis-closeout-v0.1.md`
- `docs/s02-closeout-manifest-v0.1.json`
- `src/frontier_agent_containment/s02_evidence_plane.py`
- `src/frontier_agent_containment/s02_mutations.py`
- `src/frontier_agent_containment/s02_scoring.py`
- `src/frontier_agent_containment/s02_campaign.py`
- `results/s02-stage3c-authoritative-campaign-v0.1.json`

## Frozen provenance

The S02 v0.1 chain is identified by these tags:

- `s02-stage0-v0.1`
- `s02-stage1-v0.1`
- `s02-stage2-v0.1`
- `s02-stage3a-v0.1`
- `s02-stage3b-v0.1`
- `s02-stage3c-v0.1`
- `s02-closeout-v0.1`

`s02-closeout-v0.1` peels to commit
`02ba4a726104298f1cd7d3ee623fa81b1a1f8731`.

| Artifact | SHA-256 |
| --- | --- |
| `results/s02-stage3c-authoritative-campaign-v0.1.json` | `4d273903ff912880ca06ef680614e4169f0bc29a3c4d2acb6a925c767d101e8f` |
| `docs/s02-results-analysis-closeout-v0.1.md` | `537966129647c9d74acd03b15265c8db73bae8f3b455172ab4413a87909231f8` |

## Reproducibility

The authoritative campaign's tested and frozen environment used Python
3.12.3, jsonschema 4.10.3, and rfc8785 0.1.4. `pyproject.toml` documents the
project dependencies.

Read-only identity and syntax checks from the repository root:

```bash
git rev-parse 's02-closeout-v0.1^{}'

sha256sum \
  results/s02-stage3c-authoritative-campaign-v0.1.json \
  docs/s02-results-analysis-closeout-v0.1.md

python3 -m json.tool \
  results/s02-stage3c-authoritative-campaign-v0.1.json >/dev/null
```

The test suite exercises the implementation, but it is not a substitute for
the frozen Stage 3C result. Primary-result verification does not rerun or
replace the authoritative campaign.

## Data and code availability

Repository:
https://github.com/rcampbell-research/s02-evidence-plane

The frozen authoritative result and supporting S02 artifacts are included
directly in this repository. The repository contains deterministic synthetic
research evidence; it contains no S01 empirical data used as S02 evidence.

SHA-256 provides exact byte-identity binding only. It does not by itself
establish semantic truth, scientific validity, completeness, or external
validity.

## Limitations

- Deterministic synthetic corpus
- Three constructed D/X/E baseline truth classes
- Exactly 14 single-factor frozen attack classes
- One evaluator implementation
- One frozen scorer
- One campaign
- No live-agent primary run
- No frontier-model primary adversary
- No real-world prevalence sampling model
- Closed-world scorer language
- Two possible scorer-normalization artifacts
- No mitigation experiment under S02 v0.1

## Citation and license

If using this repository before publication of the associated paper, cite the
repository using `CITATION.cff`.

Code is available under Apache License 2.0; project-authored research evidence,
results, and documentation are available under Creative Commons Attribution
4.0 International. See `LICENSE` for the file-level scope and third-party
boundary.

## Publication boundary

**S02 v0.1 is CLOSED.**

The frozen experiment ends at tag `s02-closeout-v0.1`, commit
`02ba4a726104298f1cd7d3ee623fa81b1a1f8731`.

Any commits after that tag are publication/repository metadata only unless
explicitly identified as a separately versioned future study. No
post-closeout metadata commit revises the S02 v0.1 empirical result.
