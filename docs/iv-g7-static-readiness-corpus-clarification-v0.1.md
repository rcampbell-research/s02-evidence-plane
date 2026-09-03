# IV-G7 Static Readiness Corpus Clarification v0.1

Status: prospective GREEN design contract.  This document authorizes no
runtime operation and creates no corpus artifact.

## 1. Base and purpose

IV-G7 is the deterministic construction and conformance definition for the
static Instrument Validation readiness corpus.  It follows the frozen G6
implementation at `implementation-iv-g6-runtime-adapters-v0.1` and the
`segmented-complete-suite-v0.1` regression method.  The corpus is a bounded
set of governed configuration, case, schedule, reference, and expected-oracle
records.  It is not a campaign record.

The corpus is consumed first by IV-R1 as static input to S0 Runtime Acceptance
and subsequently, after the applicable RED gates, by R2 and R3.  A valid corpus
does not establish S0 acceptance, M3 enforcement, execution, reset, evidence,
Instrument Acceptance, Pilot, Confirmatory, H1, Y, or any scientific result.

`STATIC_READINESS_CORPUS != RUNTIME_EVIDENCE != OBSERVED_IV_RESULT !=
INSTRUMENT_ACCEPTANCE != SCIENTIFIC_RESULT` is a mandatory invariant.

## 2. Boundaries

GREEN work is limited to deterministic in-memory construction, validation,
serialization, hashing, and inspection of the records defined here.  RED work
includes actor or scenario execution, provider invocation, execution, reset,
watchdog operation, fault injection, observation, evidence collection, S0
runtime, M3 enforcement, network access, R1-R5, Pilot, and Confirmatory work.
No G7 API may perform a RED operation or write during test execution.

G7 may contain static expected predicates, static expected validation results,
and static conformance examples.  It may not contain unmarked runtime Events,
observations, Derived Action/Run Outcomes, observed Validation Results, or
Instrument Acceptance results.

## 3. Active versions

New G7 Validation Case records use `validation-case` **0.2.0** exclusively.
Readiness-document 0.1.0 descriptions and historical fixtures remain
reference-only and are never emitted as active G7 records.  Scheduled Run,
Run Manifest, Runtime Plan, Evidence Event, and Instrument Acceptance versions
are respectively the already governed `0.1.0`, `0.1.0`, `0.2.0`, `0.2.0`, and
`0.2.0` contracts when such records are referenced.  No mixed active case
version is permitted.

## 4. Authoritative source tables

The literal case identifiers and category rows in the frozen readiness
clarification, Sections 27-35, are incorporated by reference in their
document order.  This incorporation is a frozen source table, not a runtime
lookup.  The table is copied into the implementation's independent oracle and
must not be regenerated from production objects.

The table contains exactly 136 unique IDs: V0=10, V1=58, V2=22, V3=35,
V4=4, V5=7.  A case ID is the exact literal `validation_case_id` from that
table; descriptive labels are not identities.  No new ID may be added and no
ID may be renamed without a new clarification.

For deterministic ordinal derivation, retain table order within each category
and concatenate categories in V0,V1,V2,V3,V4,V5 order.  Category ordinal is
one-based; global `case_ordinal` is one-based over that concatenation.  The
implementation must assert the literal set equality and the six category
counts, not merely the total count.

## 5. Case contract

Every active case is a complete `validation-case` 0.2.0 object.  Required
fields are exactly those required by `schemas/validation-case-v0.2.0.schema.json`:

`validation_case_id`, `validation_case_version`,
`instrument_configuration_id`, `display_name`, `description`, `phase`,
`applicability_class`, `applicable_component`, `applicable_scenario_families`,
`control_layers`, `preconditions`, `trigger`, `ground_truth`,
`expected_authorization`, `expected_approval`, `expected_control`,
`expected_execution`, `expected_effect`, `expected_evidence`,
`evidence_quality`, `terminal_outcome`, `run_validity`,
`primary_endpoint_observability`, `reset_cleanup_expectation`, and
`pass_criterion`.

The singleton bindings are `instrument:iv-core`, phase
`INSTRUMENT_VALIDATION`, `scenario:iv-s01-protected-record`,
`cond:s0-iv-core`, `envelope:iv-core`, `policy:iv-core-authorization`, and
`approvalpolicy:iv-core-deterministic`, unless an explicit readiness-table row
provides an already frozen conditional reference.  Every per-case value is
copied from the source row or is the stated singleton; no implementation may
choose a default for an omitted required field.

## 6. Category semantics

V0 is pure static contract/configuration validation; it is `MG`, has no fault,
no treatment, and has two repetitions.  V1 validates authorization, approval,
control, execution-boundary, evidence, watchdog, and S0 boundary mechanics;
its row supplies applicability and any frozen fault, it has three repetitions.
V2 validates outcome/evidence quality and benign-utility rules; it has three
repetitions.  V3 validates bounded fault and failure semantics; it has three
repetitions.  V4 validates reset, architecture/treatment binding, and
termination/cleanup mechanics; it has five repetitions.  V5 is pure static
readiness/confirmatory configuration validation; it has no fault, no runtime
treatment, and two repetitions.

The exact expected predicate, applicability, scenario, control layer, and
fault text for each row remains the literal readiness source-table value.  A
case passes when its instrument-mechanics predicate is satisfied, including a
correctly rejected or inconclusive operational condition.

## 7. Applicability and repetitions

Applicability is copied from each source row: `MANDATORY_GLOBAL` (MG),
`MANDATORY_CONDITIONAL` (MC), or `OPTIONAL_DIAGNOSTIC` (OD).  The only
conditional predicates are those written in the row (for example, named S03,
S05, S06, S08, target campaign, or final-analysis conditions).  Resolution is a
pure function of the frozen core configuration; unresolved conditions are an
error, never an implicit NOT_APPLICABLE.

For the core G7 static corpus all 136 rows are materialized, including MC/OD
rows as static case records.  A schedule repetition is materialized only when
the resolved schedule predicate says the row is applicable; a false predicate
creates one case-level `VALIDATION_NOT_APPLICABLE` oracle and zero runtime
repetitions.  The core configuration and source table resolve all 136 rows as
applicable for this prospective corpus, so the schedule cardinality is exactly
399.

Repetition counts are V0=2, V1=3, V2=3, V3=3, V4=5, V5=2.  IDs are
`rep_001` through the category count, unique per case/configuration.

## 8. Schedule

G7 commits one static schedule manifest, not 399 runtime Run Manifests.  Each
entry contains `schedule_entry_id`, `case_id`, `case_ordinal`, `rep_id`,
`schedule_ordinal`, category, applicability, treatment, scenario reference,
fault-plan reference, Runtime Plan reference, and static expected-oracle
reference.  It uses the existing Scheduled Run 0.1.0 field vocabulary where a
field is present.

The canonical order is category order V0..V5, then global case ordinal, then
repetition ordinal.  `schedule_ordinal` is contiguous 1..399 in that order.
`schedule_entry_id` is `sched:iv-g7-` plus six-digit zero-padded ordinal.
No filesystem, mapping, or dictionary iteration may affect order.

G7 does not fabricate runtime `run_id`.  RED execution allocates that identity
under G5.  The static schedule entry and repetition IDs are the sole G7
identities.  Any materialized Scheduled Run snapshot must omit runtime run ID
and be explicitly labeled static schedule data.

## 9. Treatment, S0, scenario, and scripts

Treatment assignment is deterministic and literal: V0 and V5 are `NO_RUNTIME`
static evaluations; V1-V4 use the treatment named by their frozen readiness
row.  The allowed runtime values are exactly M1, M2, and M3; no balancing or
randomization is performed.  The implementation must publish counts derived
from the table and reject any assignment not present in the table.  S0 is not a
treatment and is mandatory through `cond:s0-iv-core` and `safetycfg:iv-core`.

All core rows bind S01.  A row naming S03, S05, S06, or S08 retains that exact
already-frozen conditional scenario reference; no new scenario is introduced.
GroundTruth and SyntheticTransitionStimulus are static oracle references only.
They can explain an expected predicate but can never be emitted as Evidence
Event input or observation.

The deterministic actor reference is `script:iv-core-sequence`; any row with a
named existing variant uses that literal variant.  Scripts contain at most
four actor/resource actions.  Global action budget is 8; the ninth-action
condition is a static expected `ACTION_BUDGET_EXHAUSTED` predicate, not an
observed termination.

## 10. Fault plan

The 27 fault categories are exactly the frozen readiness/G5 list.  G7 stores a
literal `fault_plan:iv-core` reference and a case's literal fault category (or
`NO_FAULT`) from the source table.  It does not execute, apply, remove, or
observe a fault.  Fault parameters are retained in the governed fault-plan
reference; no new parameter values are selected in G7.  The validator asserts
the exact case-to-fault map and exact multiplicity, including NO_FAULT, from the
source table; “at least once” is insufficient.

## 11. Expected-oracle model

Expected fields are structurally named and classified as one of:
`STATIC_EXPECTED_PREDICATE`, `STATIC_EXPECTED_VALIDATION_RESULT`,
`STATIC_EXPECTED_ACTION_OUTCOME`, `STATIC_EXPECTED_RUN_OUTCOME`, or
`STATIC_EXPECTED_BENIGN_UTILITY`.  Valid validation literals are
`VALIDATION_PASS`, `VALIDATION_FAIL`, `VALIDATION_INCONCLUSIVE`, and
`VALIDATION_NOT_APPLICABLE`.

V0-V5 are instrument-mechanics/readiness cases.  No empirical campaign result
is predetermined.  Static action/run outcomes, where present in a source row,
are oracle examples and never `DerivedActionOutcome`, `DerivedRunOutcome`, or
observed results.  `record_read`, `record_correct`, evaluable, and task-success
predicates preserve `false != unevaluable`.

ProviderRequest and ProviderResult examples are excluded from the G7 corpus;
their conformance remains in G6.  Evidence Event fixtures are also excluded;
G7 contains no campaign-like evidence.  This makes prototypes involving those
fixtures explicitly PASS-NOT-IN-CORPUS rather than ambiguous.

## 12. Runtime Plan and references

G7 materializes exactly one canonical Runtime Plan 0.2.0 snapshot,
`runtime-plan/ivplan-iv-core-001.json`.  It references the active 0.2.0 case
set, the static schedule manifest, S0 declaration, singleton envelope/policies,
script and source registries, watchdog constants, action budgets, and the
27-category fault plan.  It contains no placeholder digest.

`validation_set_digest` is SHA-256 of the canonical ordered concatenation of
the raw UTF-8 bytes of the 136 case files, each preceded by its UTF-8 relative
path and one LF.  Runtime Plan and schedule references are by exact literal
ID/version; provider, build, channel, and configuration bindings are the
shared frozen G6 AdapterContext values, with no live discovery.

G7 does not materialize Run Manifest artifacts or runtime IDs.  RED G5 creates
those from the static schedule entry and Runtime Plan after R1 requirements
are met.

## 13. Corpus layout and file inventory

The exact root is `tests/fixtures/instrument_validation/v0.1/corpus/`.  The
complete tree is:

```text
runtime-plan/ivplan-iv-core-001.json                 (1)
cases/<exact 136 validation_case_id>.json            (136)
schedule/schedule-manifest.json                      (1)
scripts/iv-core-sequence.json                        (1)
faults/fault-plan-iv-core.json                       (1)
manifest/corpus-manifest.json                        (1)
```

Total corpus files: **141**.  Case filenames are the literal case ID followed
by `.json`; all other names are literal above.  No additional directory or
file is permitted.  The future test is exactly
`tests/instrument_validation/test_static_readiness_corpus.py`.  The future
source implementation is exactly
`src/frontier_agent_containment/instrument_validation/readiness_corpus.py`.
No `__init__.py` change is required.  Future implementation tag:
`implementation-iv-g7-static-readiness-corpus-v0.1`.

## 14. Corpus manifest and identity

`manifest/corpus-manifest.json` is required.  Its fields, in this order, are
`corpus_id`, `corpus_version`, `artifact_count`, and `artifacts`.  Each artifact
entry has `ordinal`, `family`, `artifact_id`, `contract_version`, `path`, and
`sha256`.  The artifact order is Runtime Plan, cases in canonical case order,
schedule, script, fault plan, then manifest (the manifest entry omits its own
raw-file digest).  `corpus_id` is the literal `corpus:iv-g7-static-readiness`
and `corpus_version` is `0.1.0`.

Manifest JSON and every JSON artifact use UTF-8, no Unicode normalization,
sorted object keys, compact separators `,` and `:`, finite JSON numbers only,
and one final LF.  Arrays retain governed order.  This is not RFC 8785/JCS.
Raw artifact digests are SHA-256 over exact committed bytes, including the
final LF, represented as lowercase hexadecimal without a prefix.

Construction is acyclic: write non-manifest artifacts, hash them, write the
manifest with those hashes, then hash the manifest only as an external
verification value.  The manifest never contains its own digest.  No semantic
identifier is derived from a content digest.

## 15. Authority and regeneration

The literal tables in this clarification plus the incorporated frozen
readiness case rows are the normative source.  The deterministic generator is
an implementation mechanism, never the expected-value oracle.  Committed
fixture bytes are the fixed corpus authority; tests independently reconstruct
case IDs, categories, schedule, treatments, faults, and manifest order from
this clarification.

There is no implicit regeneration, auto-fix, or write-on-mismatch.  Tests are
read-only.  An intentional corpus change requires a new clarification/version
and a new explicit freeze authorization.

## 16. Static validators

G7 validation must prove schema validity; active version closure; literal case
set equality; category counts; case ordinals; applicability; exact repetition
and schedule-entry set equality; treatment and fault maps/counts; reference
resolution; provider/build/channel/configuration binding; expected-oracle
classification; absence of runtime artifacts; canonical serialization; raw
digests; and manifest closure.  Count equality alone is never sufficient.

Negative conformance fixtures are not corpus files.  The permanent test suite
constructs in-memory one-defect mutations for duplicate case, missing
repetition, wrong treatment, wrong fault, wrong reference, and byte/digest
mismatch.  Positive validation covers every 141 committed artifact.  Each
negative mutation has exactly one intentional defect.

## 17. R1/R2/R3 handoff

The exact R1 static subset is Runtime Plan 0.2.0, S0 declaration/configuration,
S0 observer declaration, watchdog configuration, baseline reference, relevant
adapter declarations, and the case/schedule references required by S0.  R1
entry requires G7 corpus validation PASS, exact manifest/digest closure, all
references resolved, no runtime artifacts, and unchanged bytes.  This is not
S0 acceptance.

R2 may consume the schedule, G5 bindings, adapters, actor scripts, fault-plan
references, and runtime-plan subset only after R1 acceptance.  R3 may consume
the resulting RED runtime records only after R1/R2 gates.  G7 itself produces
no acceptance, evidence, treatment comparison, campaign result, H1, or Y.

## 18. Static prototypes A-Q

A exact 136-case set: PASS.  B exact 399-entry schedule: PASS.  C duplicate
case rejection: PASS.  D missing repetition rejection: PASS.  E wrong treatment
rejection: PASS.  F wrong fault rejection: PASS.  G GroundTruth separation:
PASS.  H ProviderResult: PASS-NOT-IN-CORPUS.  I manifest byte mutation: PASS.
J wrong reference: PASS.  K expected-versus-observed separation: PASS.  L
readiness-versus-acceptance: PASS.  M deterministic bytes/digests: PASS. N
iteration-order independence: PASS. O no RED side effect: PASS. P active
0.2.0 representative case and rejection of historical 0.1.0: PASS. Q exact
R1 handoff subset: PASS.

## 19. Semantic totality

All implementation-significant items are closed YES by Sections 3-17:
active version and required fields; 136 IDs and grammar; category,
applicability, repetitions, schedule, ordinals, run-ID policy; treatment,
S0, scenario, GroundTruth, scripts, faults and multiplicities; expected
oracles; adapter/evidence exclusion; Runtime Plan and Run Manifest policy;
references; root/tree/names/counts; manifest identity and fields;
serialization, encoding, newline, digests, closure; source-of-truth,
fixed/generated, regeneration; validators; exact R1 predicate and subset;
R2/R3 boundaries; deterministic implementation; and no RED side effects.

## 20. Non-impact and next authorization

No schema, registry, scientific family, authority source, G1-G6 semantic, H1,
Y, primary unit, estimand, Pilot, or Confirmatory definition changes. Inventories
remain 36 generic, 24 IV-core, 21 scientific families, 26 family/version;
corrected authority 17/15 and historical authority 16/15.

This clarification authorizes no implementation.  The next separate
authorization may implement the exact five future paths and 141 corpus files,
then run the static G7 tests.  IV-R1 remains deferred until that implementation
and its GREEN review are complete.
