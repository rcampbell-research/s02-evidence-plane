# IV-G5 Orchestration State Machine Clarification v0.1

## 1. Status and purpose

This document freezes the pure, deterministic, non-executing orchestration
contract for IV-G5. It closes the state, event, command, schedule, budget,
watchdog, drain, reset, failure, evaluator-handoff, repetition, case, and
acceptance ambiguities identified by the IV-G5 semantic preflight.

This is a design clarification only. It creates no implementation, runtime
adapter, runtime evidence, S0 acceptance, Instrument Acceptance, Pilot or
Confirmatory result, or scientific finding.

Normative words such as MUST, MUST NOT, REQUIRED, and EXACT refer to the future
IV-G5 implementation. Examples are subordinate to the normative tables.

## 2. Frozen predecessor and compatibility base

The implementation base is commit:

```text
205ad17667a22abc6e210b2c773c8652d6d12c60
```

The required predecessor tags and peeled targets are:

| Milestone | Peeled target |
| --- | --- |
| `implementation-iv-g4-evidence-outcomes-v0.1` | `205ad17667a22abc6e210b2c773c8652d6d12c60` |
| `iv-g4-evidence-admission-ordering-outcomes-clarification-v0.1` | `7de2ba9e9566e4ed340d35769787a3e289c50aed` |
| `implementation-iv-g4-evidence-representation-benign-utility-contract-correction-v0.1` | `2fbb38e9a3b28d6bf73c4c69127b1e56da17ca1f` |
| `implementation-iv-g3-synthetic-scenario-v0.1` | `14a66bfdde19b5487adf1daf3835744a2c8a26f7` |
| `implementation-iv-g2-actor-control-decisions-v0.1` | `a6c2942256399a7b42e7d5117698667b97c2c354` |
| `implementation-iv-g1-runtime-contracts-v0.1` | `ec3fb9126c3c9cc7e54a85fd232711d024d498f4` |

The preserved complete regression baseline is 2709 passing tests, zero
failures, and no fatal signal in the successful recovery. The earlier Stage
12E-4 SIGSEGV remains a transient, non-reproduced process termination with
unknown root cause. The historical IV-G3 lifecycle-nullability test MINOR
remains an accepted nonsemantic finding and is not reopened.

## 3. Governing contract order

This clarification is interpreted with, and does not replace:

1. the Research Contract and Statistical Analysis Plan;
2. the Instrument Validation, Evidence, Control Architecture, and
   Implementation specifications;
3. the Instrument Validation implementation-readiness clarification;
4. the IV-G1 through IV-G4 clarifications and implementations; and
5. the active corrected Runtime Plan 0.2.0, Validation Case 0.2.0, Evidence
   Event 0.2.0, Derived Action Outcome 0.2.0, Derived Run Outcome 0.2.0, and
   Instrument Acceptance 0.2.0 contracts.

Where orchestration mechanics were previously open, this document selects an
implementation-internal rule. It does not change a scientific field, outcome,
authority, evidence class, or artifact family.

## 4. GREEN and RED boundary

IV-G5 is limited to immutable in-memory values and pure transition/evaluation
functions. It may represent symbolic requests to later providers. It MUST NOT:

- read a clock or sleep;
- start a thread or process;
- access a socket or network;
- read or write runtime files;
- execute an actor, scenario transition, control, adapter, reset, or fault;
- collect or manufacture runtime evidence;
- instantiate S0 or enforce M3;
- produce a real acceptance for an executed instrument; or
- perform Pilot, Confirmatory, campaign, or scientific analysis.

Configured durations, provider identities, evidence references, and proposed
artifact IDs are inert data only.

## 5. Exact G5 component boundary

| Component | G5 role | State machine | Pure evaluator/interface | Input | Output | Deferred runtime behavior |
| --- | --- | --- | --- | --- | --- | --- |
| `validation_orchestrator` | Own the schedule cursor and deterministic lifecycle | yes | no | trusted context plus internal orchestration events | immutable next state, symbolic commands, findings | command delivery and every provider side effect |
| `reset_controller` | Track one symbolic reset lifecycle per repetition | yes | no | reset commands and correlated results | reset state and reset/observation commands | scenario reset and resource observation |
| `watchdog_controller` | Track symbolic deadline slots | yes | no | arm/cancel operations and correlated timeout events | immutable deadline states and timer commands | clock observation and timeout delivery |
| `failure_injection_controller` | Track the selected bounded synthetic fault lifecycle | yes | no | selected fault binding and correlated apply/remove results | immutable fault state and apply/remove commands | applying or removing a fault |
| `validation_case_evaluator` | Compare governed repetition material with one Validation Case and aggregate repetitions | no | yes | case, applicability, governed results/evidence | exact case result and material references | authoritative runtime observation delivery |
| `instrument_acceptance_producer` | Apply the frozen acceptance aggregation rule | no | yes | exact configuration, target campaign, complete/retained case results | Instrument Acceptance 0.2.0 candidate | Pilot/Confirmatory execution and release selection |
| inert adapter interfaces | Type and correlate provider requests/results | no | yes | symbolic commands/results | internal events only | invocation, transport, retry, and side effects |

IV-G5 consumes, but does not reimplement, the IV-G2 actor/authorization/
approval/control calculations, IV-G3 scenario model, or IV-G4 evidence and
outcome evaluators.

## 6. No generic registered failure controller

There is no new generic failure-controller component. The existing runtime-plan
field `failure_controller_component_id` continues to resolve to
`failure_injection_controller`. That component manages only the frozen bounded
fault lifecycle.

Orchestration failures are immutable classifications and findings carried by
`validation_orchestrator` state. They are not a component, Evidence Event,
scientific result, or new registry entry.

## 7. Internal records and no new schema

All records in Sections 8 through 16 are implementation-internal frozen value
objects. Their collections are tuples or immutable mappings with explicitly
defined order. They require no top-level JSON Schema and are not added to the
IV-core or scientific artifact registries.

Structural equality is authoritative for controller state. No controller state
has a stable typed identifier, digest, UUID, timestamp, or scientific artifact
identity.

## 8. Orchestration scope and schedule records

`OrchestrationScope` is the exact structural tuple:

```text
(
  validation_campaign_id,
  runtime_plan_id,
  runtime_plan_version,
  instrument_configuration_id,
  validation_set_id,
  validation_set_version,
  target_campaign_id
)
```

`validation_campaign_id` is the prospectively governed opaque identity of one
validation-execution plan. It uses the existing local-identifier grammar, is
unique within the trusted validation-plan set, and MUST NOT be reused for a
rerun. Its inclusion makes event/command identity unique across orchestrator
instances without giving controller state an artifact identity.

`ScheduledValidationRepetition` contains exactly:

| Field | Rule |
| --- | --- |
| `validation_case_id` | exact Validation Case 0.2.0 identity |
| `validation_case_version` | exactly `0.2.0` |
| `validation_phase` | exact `V0` through `V5` |
| `repetition_id` | `rep_001` through the required phase count |
| `case_ordinal` | positive, unique, contiguous across all 136 cases |
| `schedule_ordinal` | positive, unique, contiguous across all scheduled repetitions |
| `execution_mode` | `PURE_EVALUATION` for V0/V5; `RUNTIME_REPETITION` for V1-V4 |
| `scheduled_run` | one validated Scheduled Run 0.1.0 object |
| `script_plan_reference` | exact governed ScriptPlan reference or absent when the case has no actor pipeline |
| `fault_class` | one frozen fault class or absent |

`ScheduledValidationCase` contains the governed Validation Case, case ordinal,
machine-resolved applicability, frozen false-predicate reason when not
applicable, and the exact repetition tuple. A not-applicable case has zero
scheduled repetitions. An applicable case has exactly the phase count.

`ValidationExecutionSchedule` contains exactly the scope, the 136 ordered case
entries, the flattened repetition tuple, and the validation-inventory digest.
It is internal governed configuration, not a new artifact family.

## 9. Opaque artifact ID allocation plan

`OpaqueArtifactIdPlan` is a producer-owned immutable input to the trusted
context. It contains:

- one proposed `actionoutcome:` ID for every potential requested action in each
  scheduled runtime repetition;
- one proposed `runoutcome:` ID for each scheduled runtime repetition; and
- one proposed `acceptance:` ID for the sole Instrument Acceptance 0.2.0
  candidate.

The action evaluator, run aggregator, and acceptance producer respectively own
those IDs. The orchestrator validates grammar, exact scope, and global
uniqueness and only routes them. It does not derive them from content, order,
Git state, time, or randomness. Unused preallocated IDs remain unused. Reuse or
rebinding rejects the trusted context.

## 10. Event identity and record

`OrchestrationEvent` contains exactly:

| Field | Rule |
| --- | --- |
| `kind` | one literal from Section 11 |
| `scope` | exact `OrchestrationScope` |
| `event_ordinal` | positive integer; new events are contiguous from 1 |
| `correlation_command_ordinal` | required for provider results/timeouts/failures; absent only for `START` |
| `case_id` | required exactly when a case is active |
| `repetition_id` | required exactly when a repetition is active |
| `run_id` | required after run initialization; otherwise absent |
| `action_id` | required exactly for action-scoped results |
| `payload` | one closed typed payload selected by `kind` |

The event identity is `(scope, event_ordinal)`. It is internal delivery identity,
not Evidence Event identity. There is no arbitrary metadata or free-form
payload map.

Event scope-field presence is exact:

- `case_id` is absent only on `START` and `ACCEPTANCE_RESULT`;
- `repetition_id` is absent on `START`, `CASE_EVALUATION_RESULT`, and
  `ACCEPTANCE_RESULT`, and required on every other event;
- `run_id` is absent on `START`, baseline events, run-initialization events,
  case/acceptance events, and their correlated failures; after successful
  initialization it is required on every repetition event; and
- `action_id` is required only on authorization, approval, control,
  execution/nonexecution, and action-evaluation results (and a command failure
  answering one of those commands); it is absent otherwise.

## 11. Closed event-kind vocabulary

The exact event kinds are:

```text
START
BASELINE_RESULT
RUN_INITIALIZATION_RESULT
FAULT_RESULT
SCRIPT_PLAN_RESULT
BUDGET_PROBE_RESULT
AUTHORIZATION_RESULT
APPROVAL_RESULT
CONTROL_RESULT
EXECUTION_RESULT
NONEXECUTION_RESULT
TERMINATION_RESULT
DRAIN_RESULT
RESET_RESULT
RESET_OBSERVATION_RESULT
COLLECTION_RESULT
NORMALIZATION_RESULT
ACTION_EVALUATION_RESULT
RUN_AGGREGATION_RESULT
REPETITION_EVALUATION_RESULT
CASE_EVALUATION_RESULT
ACCEPTANCE_RESULT
WATCHDOG_CONTROL_RESULT
WATCHDOG_TIMEOUT
COMMAND_FAILURE
```

`BUDGET_PROBE_RESULT` is accepted only for the frozen
`valcase:iv-v2-action-budget-termination` branch. Its controller transition is
pure even though the governed validation case is a RED runtime case. It
supplies a closed tuple of governed RequestedAction-shaped test inputs to the
same budget transition. It is not actor behavior, runtime evidence, or an
additional registered component.

Unknown event kinds fail event construction. They never reach `transition`.
The payload discriminant is total and exact:

| Event kind | Exact payload material |
| --- | --- |
| `START` | empty tuple |
| `BASELINE_RESULT` | status `CLEAN_BASELINE_OBSERVED`, `RESET_MISMATCH_OBSERVED`, `RESET_STATE_UNKNOWN`, or `FAILED`; exact authoritative observation reference required for the first three and absent for `FAILED` |
| `RUN_INITIALIZATION_RESULT` | status `PRODUCED`, `FAILED`, or `UNKNOWN`; exact Run Manifest candidate reference only for `PRODUCED` |
| `FAULT_RESULT` | requested operation `APPLY` or `REMOVE`; status `ACTIVE`, `CLEARED`, `FAILED`, or `UNKNOWN`; exact fault binding |
| `SCRIPT_PLAN_RESULT` | status `PRODUCED` or `FAILED`; exact governed ScriptPlan only for `PRODUCED` |
| `BUDGET_PROBE_RESULT` | status `PRODUCED` or `FAILED`; exact immutable governed request tuple only for `PRODUCED` |
| `AUTHORIZATION_RESULT` | one exact IV-G2 AuthorizationDecision |
| `APPROVAL_RESULT` | one exact IV-G2 ApprovalDecision |
| `CONTROL_RESULT` | one exact IV-G2 selected ControlDecision |
| `EXECUTION_RESULT` | Section 30 status; provider-result reference required except for `RESULT_UNKNOWN`; immutable authoritative-evidence reference tuple (possibly empty) retained without inference |
| `NONEXECUTION_RESULT` | status `NOT_ATTEMPTED`, `FAILED`, or `UNKNOWN`; exact frozen cause and authoritative evidence reference only for `NOT_ATTEMPTED` |
| `TERMINATION_RESULT` | status `OBSERVED`, `FAILED`, or `UNKNOWN`; requested termination class and authoritative termination reference only for `OBSERVED` |
| `DRAIN_RESULT` | Section 35 status; collector-operation reference required only for `READY_FOR_RESET` |
| `RESET_RESULT` | status `COMPLETED`, `FAILED`, or `UNKNOWN`; exact reset-plan always and result reference required only for `COMPLETED` |
| `RESET_OBSERVATION_RESULT` | `CLEAN_BASELINE_OBSERVED`, `RESET_MISMATCH_OBSERVED`, or `RESET_STATE_UNKNOWN`; exact independent observation reference |
| `COLLECTION_RESULT` | status `CLOSED`, `FAILED`, or `UNKNOWN`; exact Evidence Set and collection-health references required only for `CLOSED` |
| `NORMALIZATION_RESULT` | status `ACCEPTED`, `FAILED`, or `UNKNOWN`; exact authoritative normalizer/order reference required only for `ACCEPTED` |
| `ACTION_EVALUATION_RESULT` | status `PRODUCED` or `FAILED`; exact Derived Action Outcome candidate only for `PRODUCED` |
| `RUN_AGGREGATION_RESULT` | status `PRODUCED` or `FAILED`; exact Derived Run Outcome candidate only for `PRODUCED` |
| `REPETITION_EVALUATION_RESULT` | exactly `VALIDATION_PASS`, `VALIDATION_FAIL`, or `VALIDATION_INCONCLUSIVE`, with exact material references |
| `CASE_EVALUATION_RESULT` | exactly one Section 43 case result with exact repetition/material references |
| `ACCEPTANCE_RESULT` | status `PRODUCED` or `FAILED`; exact Instrument Acceptance 0.2.0 candidate only for `PRODUCED` |
| `WATCHDOG_CONTROL_RESULT` | Section 14 status, operation, and exact deadline key |
| `WATCHDOG_TIMEOUT` | exact armed deadline key |
| `COMMAND_FAILURE` | exact failed command kind and the literal status `FAILED`; no free-form exception material |

A status/reference combination outside its row fails event construction. An
invalid governed candidate delivered under a `PRODUCED` status is consumed,
classified by the matching interface/evaluator failure rule, and is never
treated as a successful result.

## 12. Command identity and record

`OrchestrationCommand` contains exactly:

| Field | Rule |
| --- | --- |
| `kind` | one literal from Section 13 |
| `scope` | exact `OrchestrationScope` |
| `command_ordinal` | positive, contiguous, monotonically increasing in one orchestrator instance |
| `target_component_id` | exact registered component owning the requested operation |
| `case_id` | current governed case or absent only before case dispatch |
| `repetition_id` | current repetition where applicable |
| `run_id` | current run after initialization |
| `action_id` | current action where applicable |
| `payload` | closed typed payload for the command kind |

Command scope-field presence is exact:

- `case_id` is required except on `REQUEST_INSTRUMENT_ACCEPTANCE`;
- `repetition_id` is required except on `REQUEST_CASE_EVALUATION` and
  `REQUEST_INSTRUMENT_ACCEPTANCE`;
- `run_id` is absent on initial baseline/watchdog commands and
  `REQUEST_RUN_INITIALIZATION`, required on subsequent repetition commands,
  and absent on case/acceptance commands; and
- `action_id` is required only on authorization, approval, control,
  execution/nonexecution, and action-evaluation commands.

Command identity is `(scope, command_ordinal)`. It contains no digest, random
UUID, timestamp, callback, function, path, endpoint, or secret. Replay from the
same initial state and event sequence yields identical command identities.

## 13. Closed command-kind vocabulary

| Command kind | Exact target | Expected result event |
| --- | --- | --- |
| `REQUEST_BASELINE_VERIFICATION` | `resource_state_observer` | `BASELINE_RESULT` |
| `REQUEST_RUN_INITIALIZATION` | `scenario_adapter` | `RUN_INITIALIZATION_RESULT` |
| `ARM_WATCHDOG` | `watchdog_controller` | `WATCHDOG_CONTROL_RESULT`, then correlated `WATCHDOG_TIMEOUT` only if it later fires |
| `CANCEL_WATCHDOG` | `watchdog_controller` | `WATCHDOG_CONTROL_RESULT` |
| `REQUEST_FAULT_APPLY` | `failure_injection_controller` | `FAULT_RESULT` |
| `REQUEST_SCRIPT_PLAN` | `scripted_validation_actor` | `SCRIPT_PLAN_RESULT` |
| `REQUEST_BUDGET_PROBE` | `validation_orchestrator` pure fixture interface | `BUDGET_PROBE_RESULT` |
| `REQUEST_AUTHORIZATION` | `authorization_service` | `AUTHORIZATION_RESULT` |
| `REQUEST_APPROVAL` | `approval_emulator` | `APPROVAL_RESULT` |
| `REQUEST_CONTROL_DECISION` | selected M1/M2/M3 component | `CONTROL_RESULT` |
| `REQUEST_EXECUTION` | `action_execution_adapter` | `EXECUTION_RESULT` |
| `REQUEST_NONEXECUTION_CONFIRMATION` | `action_execution_adapter` | `NONEXECUTION_RESULT` |
| `REQUEST_TERMINATION` | `watchdog_controller` | `TERMINATION_RESULT` |
| `REQUEST_EVIDENCE_DRAIN` | `evidence_collector` | `DRAIN_RESULT` |
| `REQUEST_FAULT_REMOVAL` | `failure_injection_controller` | `FAULT_RESULT` |
| `REQUEST_RESET` | `reset_controller` | `RESET_RESULT` |
| `REQUEST_RESET_OBSERVATION` | `resource_state_observer` | `RESET_OBSERVATION_RESULT` |
| `REQUEST_COLLECTION_CLOSURE` | `evidence_collector` | `COLLECTION_RESULT` |
| `REQUEST_NORMALIZATION` | `evidence_normalizer_store` | `NORMALIZATION_RESULT` |
| `REQUEST_ACTION_EVALUATION` | `action_outcome_evaluator` | `ACTION_EVALUATION_RESULT` |
| `REQUEST_RUN_AGGREGATION` | `run_outcome_aggregator` | `RUN_AGGREGATION_RESULT` |
| `REQUEST_REPETITION_EVALUATION` | `validation_case_evaluator` | `REPETITION_EVALUATION_RESULT` |
| `REQUEST_CASE_EVALUATION` | `validation_case_evaluator` | `CASE_EVALUATION_RESULT` |
| `REQUEST_INSTRUMENT_ACCEPTANCE` | `instrument_acceptance_producer` | `ACCEPTANCE_RESULT` |

Unknown command kinds fail command construction.

The command payload discriminant is also closed. Scope fields already present on
the command are not repeated in its payload.

| Command kind | Exact payload material |
| --- | --- |
| `REQUEST_BASELINE_VERIFICATION` | reset plan/version, clean-state condition, frozen baseline identity |
| `REQUEST_RUN_INITIALIZATION` | Scheduled Run, Validation Case, repetition, selected treatment, and configuration references |
| `ARM_WATCHDOG` | deadline kind, configured duration, and new deadline key |
| `CANCEL_WATCHDOG` | exact armed deadline key |
| `REQUEST_FAULT_APPLY` | governed case fault binding and bounded fault-fixture reference |
| `REQUEST_SCRIPT_PLAN` | governed actor, case, scenario, and script references |
| `REQUEST_BUDGET_PROBE` | exact V2 case reference and governed probe-plan reference |
| `REQUEST_AUTHORIZATION` | RequestedAction plus policy/capability/governing-context references required by IV-G2 |
| `REQUEST_APPROVAL` | exact AuthorizationDecision plus approval-policy/action bindings required by IV-G2 |
| `REQUEST_CONTROL_DECISION` | exact action, authorization, optional approval, treatment, and layer-input references required by IV-G2 |
| `REQUEST_EXECUTION` | exact RequestedAction and retained authorization/approval/control references |
| `REQUEST_NONEXECUTION_CONFIRMATION` | exact action, retained decision references, and one frozen cause |
| `REQUEST_TERMINATION` | one exact termination class and retained causal command/result references |
| `REQUEST_EVIDENCE_DRAIN` | run, repetition, collector, reset-plan, and DRAIN-deadline references |
| `REQUEST_FAULT_REMOVAL` | exact active fault binding and apply-result reference |
| `REQUEST_RESET` | reset plan/version, exact baseline identity, and clean-state condition |
| `REQUEST_RESET_OBSERVATION` | reset plan/result, baseline identity, and independent observer reference |
| `REQUEST_COLLECTION_CLOSURE` | run/repetition, Evidence Set identity, and reset-observation references actually available |
| `REQUEST_NORMALIZATION` | exact Evidence Set and authoritative normalizer/source references |
| `REQUEST_ACTION_EVALUATION` | Section 40 trusted context, complete fixed evidence input, proposed opaque action-outcome ID, and derivation sequence |
| `REQUEST_RUN_AGGREGATION` | Section 41 trusted context/material, action universe/artifacts, and proposed opaque run-outcome ID |
| `REQUEST_REPETITION_EVALUATION` | Validation Case, repetition, and exact available evidence/derived-artifact references |
| `REQUEST_CASE_EVALUATION` | Validation Case, applicability decision, and exact ordered repetition-result tuple |
| `REQUEST_INSTRUMENT_ACCEPTANCE` | Section 47 configuration, target, complete case-result set, provenance, and proposed opaque acceptance ID |

Any extra, missing, wrongly scoped, or wrong-version payload material rejects
command construction.

The command-idempotence rule applies to every row above:

| Commands covered | Duplicate emission | Correlation | Duplicate result | Automatic retry |
| --- | --- | --- | --- | --- |
| every command kind | prohibited for one consumed event/transition | exact `(scope, command_ordinal)` plus matching case/repetition/run/action fields | identical event identity/material is a no-op; a later result for a completed/cancelled command is stale, except an armed watchdog's separately correlated timeout | never |
| `REQUEST_EXECUTION` only | still prohibited | same | one unique `ATTEMPTED` notification may precede one unique terminal result; replay rules still apply | never |

## 14. Correlation, acknowledgement, and outstanding commands

Every provider result event other than `WATCHDOG_TIMEOUT` names an outstanding
command ordinal, matches that command's expected event kind, and exactly
matches all scope fields. Arrival position is never correlation.
`WATCHDOG_CONTROL_RESULT` has exact status `ACKNOWLEDGED`, `FAILED`, or
`UNKNOWN` and repeats the deadline key and requested operation `ARM` or
`CANCEL`. Only `ACKNOWLEDGED` changes the deadline slot as requested. G5 waits
for this result before issuing the continuation that depends on the arm or
cancel.

`WATCHDOG_TIMEOUT` is the sole exception to the outstanding-command rule. It
names the already acknowledged ARM command ordinal embedded in its exact
deadline key and is accepted only while that key is `ARMED`; while the same key
is `CANCEL_REQUESTED`, Section 26 makes it stale. Thus an acknowledged ARM
command may be complete while its deadline remains active.

`EXECUTION_RESULT` is the sole multi-notification command response: one
`ATTEMPTED` result leaves the command outstanding; exactly one later terminal
result completes it. Every other successfully consumed provider result
completes its command immediately.

A wrong command, run, repetition, case, or action correlation is
`COMMAND_CORRELATION_INVALID`. It is never accepted as progress.

## 15. Duplicate, replay, and wrong-state rules

Rules are applied in this exact precedence:

1. invalid event structure or unknown kind is constructor rejection;
2. scope mismatch is `COMMAND_CORRELATION_INVALID`;
3. an already consumed event identity with structurally identical material is
   an idempotent no-op: state unchanged, no command, no new finding;
4. an already consumed event identity with different material is
   `EVENT_IDENTITY_REBINDING`;
5. a new noncontiguous ordinal is `EVENT_SEQUENCE_INVALID`;
6. except for a valid `WATCHDOG_TIMEOUT` on an ARMED acknowledged deadline, a
   correctly correlated event for a completed or cancelled command is a stale
   no-op with `STALE_CORRELATED_EVENT` finding;
7. an otherwise valid event not accepted by the current state is rejected with
   `WRONG_STATE_EVENT`, state unchanged, and no command; and
8. an accepted event follows the transition table.

Identity rebinding, sequence invalidity, and cross-scope/correlation invalidity
are material orchestration failures. An ordinary wrong-state event is a
retained rejected-input finding and does not itself create a scientific
INCONCLUSIVE result.

One newly consumed event can emit each command at most once. Duplicate delivery
does not increment command ordinal or re-emit a command. IV-G5 performs no
automatic command retransmission or retry.
A newly delivered event with the exact expected ordinal is retained and
increments `next_event_ordinal` even when it is rejected for wrong state,
stale correlation, or wrong command correlation. A duplicate/rebinding of an
old identity and a noncontiguous future ordinal do not increment it. Thus a
rejected new delivery cannot be silently replaced under the same identity.
"State unchanged" for a rejected event means state kind, cursors, counters,
controller states, and artifacts are unchanged; only delivery history and the
finding tuple advance.

## 16. Findings and internal failure classes

The closed finding codes are:

```text
WRONG_STATE_EVENT
STALE_CORRELATED_EVENT
TERMINAL_EVENT_REJECTED
EVENT_CONTRACT_REJECTED
```

The closed state-affecting `OrchestrationFailureClass` literals are:

```text
GOVERNING_CONTEXT_INVALID
INTERNAL_INVARIANT_VIOLATION
EVENT_IDENTITY_REBINDING
EVENT_SEQUENCE_INVALID
COMMAND_CORRELATION_INVALID
RUN_INITIALIZATION_FAILURE
WATCHDOG_INTERFACE_FAILURE
ACTOR_INTERFACE_FAILURE
AUTHORIZATION_INTERFACE_FAILURE
APPROVAL_INTERFACE_FAILURE
CONTROL_INTERFACE_FAILURE
EXECUTION_INTERFACE_FAILURE
TERMINATION_INTERFACE_FAILURE
DRAIN_FAILURE
DRAIN_TIMEOUT
FAULT_APPLY_FAILURE
FAULT_REMOVAL_FAILURE
RESET_COMMAND_FAILURE
RESET_MISMATCH
RESET_UNKNOWN
RESET_TIMEOUT
COLLECTION_CLOSURE_FAILURE
NORMALIZATION_FAILURE
ACTION_EVALUATOR_FAILURE
RUN_AGGREGATOR_FAILURE
CASE_EVALUATOR_FAILURE
ACCEPTANCE_PRODUCER_FAILURE
RUN_TIMEOUT
```

`ACTION_BUDGET_EXHAUSTED` is a valid termination cause, not an orchestration
failure. A valid control `INDETERMINATE` is not `CONTROL_INTERFACE_FAILURE`.

## 17. Orchestrator state record

`ValidationOrchestratorState` contains exactly:

- one state kind from Section 18;
- the trusted scope and schedule;
- case/repetition/run/action cursors;
- immutable script/action work queues;
- global and actor resource-action counters;
- next event and command ordinals;
- consumed events and outstanding/completed command records;
- watchdog, reset, and fault-controller states;
- retained evidence/artifact/result references;
- ordered internal findings and failure classes;
- `halt_after_closure` and `fresh_s0_required` booleans derived only by the
  transition rules; and
- no other field.

The record is immutable. Transition never mutates an input record or governed
artifact.

## 18. Closed validation-orchestrator state vocabulary

```text
VALIDATING_CONTEXT
AWAITING_BASELINE
AWAITING_RUN_INITIALIZATION
AWAITING_FAULT_APPLY
AWAITING_SCRIPT_PLAN
AWAITING_AUTHORIZATION
AWAITING_APPROVAL
AWAITING_CONTROL
AWAITING_EXECUTION_RESULT
AWAITING_NONEXECUTION_RESULT
AWAITING_TERMINATION
AWAITING_DRAIN_READY
AWAITING_FAULT_REMOVAL
AWAITING_RESET_RESULT
AWAITING_RESET_OBSERVATION
AWAITING_COLLECTION_CLOSURE
AWAITING_NORMALIZATION
AWAITING_ACTION_DERIVATION
AWAITING_RUN_AGGREGATION
AWAITING_REPETITION_EVALUATION
AWAITING_CASE_EVALUATION
AWAITING_ACCEPTANCE
AWAITING_WATCHDOG_CONTROL
COMPLETED
HALTED
BLOCKED_FRESH_S0
```

Each nonterminal state waits for exactly the named result family. There is no
generic `READY`, `DONE`, or caller-defined state.

`AWAITING_WATCHDOG_CONTROL` carries one closed continuation literal from
Section 26. It waits only for the acknowledgement of one arm/cancel command;
it is not a runtime waiting clock.

## 19. Initial and terminal states

`VALIDATING_CONTEXT` is the sole initial state. Its counters and cursors are
zero/empty, next event and command ordinals are 1, and it has no consumed event
or outstanding command.

The sole accepted event is `START`. Its guard validates:

- Runtime Plan 0.2.0, exact Instrument Configuration, component DAG, corrected
  authority closure, and S0 acceptance/configuration references;
- the exact 136-case Validation Case 0.2.0 inventory and digest;
- the schedule, applicability, repetition, and dispatch rules in Sections 43 through 46;
- selected treatment and scenario/configuration bindings;
- every Scheduled Run reference;
- the opaque artifact ID plan; and
- target campaign/phase eligibility without executing that campaign.

Success dispatches the first case. Failure enters `HALTED` with
`GOVERNING_CONTEXT_INVALID` and emits no runtime command.

Terminal states are:

| State | Meaning | Reset already complete | New run/case | External rerun |
| --- | --- | --- | --- | --- |
| `COMPLETED` | schedule and acceptance production completed | yes for every runtime repetition | prohibited | new governed schedule only |
| `HALTED` | internal orchestration integrity/producer failure made this instance unusable | completed when a run had started, otherwise not applicable | prohibited | new governed scope only |
| `BLOCKED_FRESH_S0` | reset/baseline/fault-cleanliness failure requires fresh accepted S0 | no valid clean reset | prohibited | new governed scope after fresh S0 |

All are absorbing. Exact duplicate events are no-ops. A new event is rejected
with `TERMINAL_EVENT_REJECTED`; it cannot emit a command or resurrect state.

## 20. Pure transition interface and totality

The exact conceptual interface is:

```text
transition(state, event, trusted_context)
  -> (next_state, commands, findings)
```

It is pure and deterministic. Before state-specific rows it applies Sections
14 and 15. Each row in Section 21 lists every accepted event for a state. The
final `ALL OTHER` row for each state covers the rest of the closed event
vocabulary; therefore the table is total over every valid state/event-kind pair.

Helpers named `dispatch_schedule`, `advance_script`, `route_failure`, and
`close_repetition` below are normative algorithms defined in later sections,
not implementation discretion.

## 21. Exhaustive orchestrator transition table

Abbreviations: `WR` means the Section 15 wrong-state rejection; `FH` means
`route_failure`; `DS` means `dispatch_schedule`; `AS` means `advance_script`.

| Current state | Accepted event | Guard/result | Next state | Commands / counter change |
| --- | --- | --- | --- | --- |
| `VALIDATING_CONTEXT` | `START` | context valid | result of `DS` | first exact command; counters unchanged |
| `VALIDATING_CONTEXT` | `START` | context invalid | `HALTED` | no command; context failure |
| `VALIDATING_CONTEXT` | ALL OTHER | any | unchanged | WR |
| `AWAITING_BASELINE` | `BASELINE_RESULT` | `CLEAN_BASELINE_OBSERVED` | `AWAITING_WATCHDOG_CONTROL` | cancel RESET; continuation requests run initialization |
| `AWAITING_BASELINE` | `BASELINE_RESULT` | mismatch/unknown/failed | `AWAITING_WATCHDOG_CONTROL` | retain exact failure and fresh-S0 block; cancel RESET; continuation requests repetition evaluation |
| `AWAITING_BASELINE` | `WATCHDOG_TIMEOUT` | correlated RESET deadline | `AWAITING_REPETITION_EVALUATION` | retain `RESET_TIMEOUT` and fresh-S0 block; request repetition evaluation |
| `AWAITING_BASELINE` | `COMMAND_FAILURE` | correlated baseline command | `AWAITING_WATCHDOG_CONTROL` | retain failure and fresh-S0 block; cancel RESET; continuation requests repetition evaluation |
| `AWAITING_BASELINE` | ALL OTHER | any | unchanged | WR |
| `AWAITING_RUN_INITIALIZATION` | `RUN_INITIALIZATION_RESULT` | valid unique runtime Run Manifest/run ID | `AWAITING_WATCHDOG_CONTROL` | arm RUN; continuation applies fault or requests script/budget probe |
| `AWAITING_RUN_INITIALIZATION` | `RUN_INITIALIZATION_RESULT` | valid unique pure-evaluation Run Manifest/run ID | `AWAITING_REPETITION_EVALUATION` | request repetition evaluation; no watchdog/reset command |
| `AWAITING_RUN_INITIALIZATION` | `RUN_INITIALIZATION_RESULT` | invalid/failed | `AWAITING_REPETITION_EVALUATION` | retain `RUN_INITIALIZATION_FAILURE`, set `halt_after_closure`, and request repetition evaluation |
| `AWAITING_RUN_INITIALIZATION` | `COMMAND_FAILURE` | correlated | `AWAITING_REPETITION_EVALUATION` | retain initialization failure, set `halt_after_closure`, and request repetition evaluation |
| `AWAITING_RUN_INITIALIZATION` | ALL OTHER | any | unchanged | WR |
| `AWAITING_FAULT_APPLY` | `FAULT_RESULT` | exact `ACTIVE`; budget case | `AWAITING_SCRIPT_PLAN` | request budget probe |
| `AWAITING_FAULT_APPLY` | `FAULT_RESULT` | exact `ACTIVE`; ordinary actor case | `AWAITING_SCRIPT_PLAN` | request script plan |
| `AWAITING_FAULT_APPLY` | `FAULT_RESULT` | failed/unknown | `AWAITING_TERMINATION` | mark fault failure; request infrastructure termination |
| `AWAITING_FAULT_APPLY` | `WATCHDOG_TIMEOUT` | RUN | `AWAITING_TERMINATION` | mark run timeout; request timeout termination |
| `AWAITING_FAULT_APPLY` | `COMMAND_FAILURE` | correlated | `AWAITING_TERMINATION` | mark fault failure; request infrastructure termination |
| `AWAITING_FAULT_APPLY` | ALL OTHER | any | unchanged | WR |
| `AWAITING_SCRIPT_PLAN` | `SCRIPT_PLAN_RESULT` | exact valid governed ScriptPlan | result of AS | actor count validated; admit next request or terminate |
| `AWAITING_SCRIPT_PLAN` | `BUDGET_PROBE_RESULT` | exact budget case and valid tuple | result of AS | global-only probe queue |
| `AWAITING_SCRIPT_PLAN` | either result | invalid | `AWAITING_TERMINATION` | actor failure; request run invalidation |
| `AWAITING_SCRIPT_PLAN` | `WATCHDOG_TIMEOUT` | RUN | `AWAITING_TERMINATION` | request timeout termination |
| `AWAITING_SCRIPT_PLAN` | `COMMAND_FAILURE` | correlated | `AWAITING_TERMINATION` | actor failure; request run invalidation |
| `AWAITING_SCRIPT_PLAN` | ALL OTHER | any | unchanged | WR |
| `AWAITING_AUTHORIZATION` | `AUTHORIZATION_RESULT` | valid non-approval state | `AWAITING_CONTROL` | request selected control |
| `AWAITING_AUTHORIZATION` | `AUTHORIZATION_RESULT` | valid `APPROVAL_REQUIRED` | `AWAITING_APPROVAL` | request approval |
| `AWAITING_AUTHORIZATION` | `AUTHORIZATION_RESULT` | rejected/invalid | `AWAITING_TERMINATION` | authorization failure; request run invalidation |
| `AWAITING_AUTHORIZATION` | `WATCHDOG_TIMEOUT` | RUN | `AWAITING_TERMINATION` | request timeout termination |
| `AWAITING_AUTHORIZATION` | `COMMAND_FAILURE` | correlated | `AWAITING_TERMINATION` | authorization failure; request run invalidation |
| `AWAITING_AUTHORIZATION` | ALL OTHER | any | unchanged | WR |
| `AWAITING_APPROVAL` | `APPROVAL_RESULT` | any valid six-state result | `AWAITING_CONTROL` | derive frozen posture; request selected control |
| `AWAITING_APPROVAL` | `APPROVAL_RESULT` | invalid binding/contract | `AWAITING_TERMINATION` | approval failure; request run invalidation |
| `AWAITING_APPROVAL` | `WATCHDOG_TIMEOUT` | RUN | `AWAITING_TERMINATION` | request timeout termination |
| `AWAITING_APPROVAL` | `COMMAND_FAILURE` | correlated | `AWAITING_TERMINATION` | approval failure; request run invalidation |
| `AWAITING_APPROVAL` | ALL OTHER | any | unchanged | WR |
| `AWAITING_CONTROL` | `CONTROL_RESULT` | valid `PROCEED` | `AWAITING_EXECUTION_RESULT` | request execution; no authorization rewrite |
| `AWAITING_CONTROL` | `CONTROL_RESULT` | valid `BLOCK` | `AWAITING_NONEXECUTION_RESULT` | request positive nonexecution confirmation |
| `AWAITING_CONTROL` | `CONTROL_RESULT` | valid `INDETERMINATE` | `AWAITING_NONEXECUTION_RESULT` | request nonexecution with declared precondition cause; mark terminate-after-action |
| `AWAITING_CONTROL` | `CONTROL_RESULT` | invalid/rejected | `AWAITING_TERMINATION` | control failure; request run invalidation |
| `AWAITING_CONTROL` | `WATCHDOG_TIMEOUT` | RUN | `AWAITING_TERMINATION` | request timeout termination |
| `AWAITING_CONTROL` | `COMMAND_FAILURE` | correlated | `AWAITING_TERMINATION` | control failure; request run invalidation |
| `AWAITING_CONTROL` | ALL OTHER | any | unchanged | WR |
| `AWAITING_EXECUTION_RESULT` | `EXECUTION_RESULT` | `ATTEMPTED` first | unchanged | retain attempt; command remains outstanding |
| `AWAITING_EXECUTION_RESULT` | `EXECUTION_RESULT` | `SUCCEEDED`, `FAILED`, or `NOT_ATTEMPTED` | result of AS | close action; no effect inference |
| `AWAITING_EXECUTION_RESULT` | `EXECUTION_RESULT` | `RESULT_UNKNOWN` | `AWAITING_TERMINATION` | request run invalidation |
| `AWAITING_EXECUTION_RESULT` | `WATCHDOG_TIMEOUT` | RUN | `AWAITING_TERMINATION` | request timeout termination |
| `AWAITING_EXECUTION_RESULT` | `COMMAND_FAILURE` | correlated | `AWAITING_TERMINATION` | execution failure; request infrastructure termination |
| `AWAITING_EXECUTION_RESULT` | ALL OTHER | any | unchanged | WR |
| `AWAITING_NONEXECUTION_RESULT` | `NONEXECUTION_RESULT` | `NOT_ATTEMPTED/CONTROL_BLOCKED` | result of AS | close action and continue script |
| `AWAITING_NONEXECUTION_RESULT` | `NONEXECUTION_RESULT` | `NOT_ATTEMPTED/PRECONDITION_UNMET` after INDETERMINATE | `AWAITING_TERMINATION` | close action; request RUN_INVALIDATION termination |
| `AWAITING_NONEXECUTION_RESULT` | `NONEXECUTION_RESULT` | `NOT_ATTEMPTED/AGENT_WITHDREW` | `AWAITING_TERMINATION` | close targeted action; request AGENT_ABORT termination |
| `AWAITING_NONEXECUTION_RESULT` | `NONEXECUTION_RESULT` | unknown/invalid | `AWAITING_TERMINATION` | request run invalidation |
| `AWAITING_NONEXECUTION_RESULT` | `WATCHDOG_TIMEOUT` | RUN | `AWAITING_TERMINATION` | request timeout termination |
| `AWAITING_NONEXECUTION_RESULT` | `COMMAND_FAILURE` | correlated | `AWAITING_TERMINATION` | execution interface failure; request infrastructure termination |
| `AWAITING_NONEXECUTION_RESULT` | ALL OTHER | any | unchanged | WR |
| `AWAITING_TERMINATION` | `TERMINATION_RESULT` | valid expected class/evidence reference | `AWAITING_WATCHDOG_CONTROL` | cancel RUN; continuation arms DRAIN and requests drain |
| `AWAITING_TERMINATION` | `WATCHDOG_TIMEOUT` | RUN; non-timeout termination command outstanding | unchanged | fire RUN, cancel ordinary termination command, request TIMEOUT termination once |
| `AWAITING_TERMINATION` | `COMMAND_FAILURE` | termination command | `AWAITING_WATCHDOG_CONTROL` | termination evidence remains missing; cancel RUN; continuation arms DRAIN and requests drain |
| `AWAITING_TERMINATION` | ALL OTHER | any | unchanged | WR |
| `AWAITING_DRAIN_READY` | `DRAIN_RESULT` | `READY_FOR_RESET`; fault active | `AWAITING_FAULT_REMOVAL` | keep DRAIN armed; request fault removal |
| `AWAITING_DRAIN_READY` | `DRAIN_RESULT` | `READY_FOR_RESET`; no fault | `AWAITING_WATCHDOG_CONTROL` | keep DRAIN armed; arm RESET; continuation requests reset |
| `AWAITING_DRAIN_READY` | `DRAIN_RESULT` | failed/unknown; fault active | `AWAITING_FAULT_REMOVAL` | record drain failure; request fault removal |
| `AWAITING_DRAIN_READY` | `DRAIN_RESULT` | failed/unknown; no fault | `AWAITING_WATCHDOG_CONTROL` | record drain failure; arm RESET; continuation requests reset |
| `AWAITING_DRAIN_READY` | `WATCHDOG_TIMEOUT` | DRAIN; fault active | `AWAITING_FAULT_REMOVAL` | mark drain timeout; request fault removal |
| `AWAITING_DRAIN_READY` | `WATCHDOG_TIMEOUT` | DRAIN; no fault | `AWAITING_WATCHDOG_CONTROL` | mark drain timeout; arm RESET; continuation requests reset |
| `AWAITING_DRAIN_READY` | `COMMAND_FAILURE` | drain; fault active | `AWAITING_FAULT_REMOVAL` | mark drain failure; request fault removal |
| `AWAITING_DRAIN_READY` | `COMMAND_FAILURE` | drain; no fault | `AWAITING_WATCHDOG_CONTROL` | mark drain failure; arm RESET; continuation requests reset |
| `AWAITING_DRAIN_READY` | ALL OTHER | any | unchanged | WR |
| `AWAITING_FAULT_REMOVAL` | `FAULT_RESULT` | exact `CLEARED` | `AWAITING_WATCHDOG_CONTROL` | arm RESET; continuation requests reset |
| `AWAITING_FAULT_REMOVAL` | `FAULT_RESULT` | failed/unknown | `AWAITING_WATCHDOG_CONTROL` | mark removal/reset block; arm RESET; continuation requests reset |
| `AWAITING_FAULT_REMOVAL` | `WATCHDOG_TIMEOUT` | DRAIN | `AWAITING_WATCHDOG_CONTROL` | mark drain timeout and removal unknown, cancel removal command, require fresh S0, arm RESET |
| `AWAITING_FAULT_REMOVAL` | `COMMAND_FAILURE` | removal | `AWAITING_WATCHDOG_CONTROL` | mark removal failure; arm RESET; continuation requests reset |
| `AWAITING_FAULT_REMOVAL` | ALL OTHER | any | unchanged | WR |
| `AWAITING_RESET_RESULT` | `RESET_RESULT` | completed | `AWAITING_RESET_OBSERVATION` | request independent observation |
| `AWAITING_RESET_RESULT` | `RESET_RESULT` | failed/unknown | `AWAITING_RESET_OBSERVATION` | mark reset block; still request observation |
| `AWAITING_RESET_RESULT` | `WATCHDOG_TIMEOUT` | RESET | `AWAITING_RESET_OBSERVATION` | mark reset timeout/block; request observation |
| `AWAITING_RESET_RESULT` | `WATCHDOG_TIMEOUT` | DRAIN | unchanged | mark drain timeout; reset continues |
| `AWAITING_RESET_RESULT` | `COMMAND_FAILURE` | reset | `AWAITING_RESET_OBSERVATION` | mark reset block; request observation |
| `AWAITING_RESET_RESULT` | ALL OTHER | any | unchanged | WR |
| `AWAITING_RESET_OBSERVATION` | `RESET_OBSERVATION_RESULT` | `CLEAN_BASELINE_OBSERVED`; no prior reset/fault failure | `AWAITING_WATCHDOG_CONTROL` | retain clean observation; cancel RESET; continuation routes collection by drain-timeout flag |
| `AWAITING_RESET_OBSERVATION` | `RESET_OBSERVATION_RESULT` | `CLEAN_BASELINE_OBSERVED`; prior reset/fault failure | `AWAITING_WATCHDOG_CONTROL` | set fresh-S0 block; cancel RESET; continuation routes collection |
| `AWAITING_RESET_OBSERVATION` | `RESET_OBSERVATION_RESULT` | `RESET_MISMATCH_OBSERVED` | `AWAITING_WATCHDOG_CONTROL` | retain mismatch/fresh-S0 block; cancel RESET; continuation routes collection |
| `AWAITING_RESET_OBSERVATION` | `RESET_OBSERVATION_RESULT` | `RESET_STATE_UNKNOWN` | `AWAITING_WATCHDOG_CONTROL` | retain unknown/fresh-S0 block; cancel RESET; continuation routes collection |
| `AWAITING_RESET_OBSERVATION` | `WATCHDOG_TIMEOUT` | RESET; drain not timed out | `AWAITING_COLLECTION_CLOSURE` | mark reset timeout/block; request collection closure |
| `AWAITING_RESET_OBSERVATION` | `WATCHDOG_TIMEOUT` | RESET; drain timed out | `AWAITING_NORMALIZATION` | mark reset timeout/block and collection missing; request normalization |
| `AWAITING_RESET_OBSERVATION` | `WATCHDOG_TIMEOUT` | DRAIN | unchanged | mark drain timeout; cancel any drain command; observation still required |
| `AWAITING_RESET_OBSERVATION` | `COMMAND_FAILURE` | observation | `AWAITING_WATCHDOG_CONTROL` | mark reset unknown/block; cancel RESET; continuation routes collection |
| `AWAITING_RESET_OBSERVATION` | ALL OTHER | any | unchanged | WR |
| `AWAITING_COLLECTION_CLOSURE` | `COLLECTION_RESULT` | valid; DRAIN ARMED | `AWAITING_WATCHDOG_CONTROL` | cancel DRAIN; continuation requests normalization |
| `AWAITING_COLLECTION_CLOSURE` | `COLLECTION_RESULT` | valid; DRAIN FIRED | `AWAITING_NORMALIZATION` | retain closure; request normalization directly |
| `AWAITING_COLLECTION_CLOSURE` | `WATCHDOG_TIMEOUT` | DRAIN | `AWAITING_NORMALIZATION` | mark drain timeout and collection missing, cancel collection command, request normalization |
| `AWAITING_COLLECTION_CLOSURE` | `COMMAND_FAILURE` | collection; DRAIN ARMED | `AWAITING_WATCHDOG_CONTROL` | collection remains missing; cancel DRAIN; continuation requests normalization |
| `AWAITING_COLLECTION_CLOSURE` | `COMMAND_FAILURE` | collection; DRAIN FIRED | `AWAITING_NORMALIZATION` | collection remains missing; request normalization directly |
| `AWAITING_COLLECTION_CLOSURE` | ALL OTHER | any | unchanged | WR |
| `AWAITING_NORMALIZATION` | `NORMALIZATION_RESULT` | valid; action universe nonempty | `AWAITING_ACTION_DERIVATION` | request first canonical action evaluation |
| `AWAITING_NORMALIZATION` | `NORMALIZATION_RESULT` | valid; action universe empty | `AWAITING_RUN_AGGREGATION` | request run aggregation |
| `AWAITING_NORMALIZATION` | `COMMAND_FAILURE` | action universe nonempty | `AWAITING_ACTION_DERIVATION` | retain normalization missing; request first canonical action evaluation |
| `AWAITING_NORMALIZATION` | `COMMAND_FAILURE` | action universe empty | `AWAITING_RUN_AGGREGATION` | retain normalization missing; request run aggregation |
| `AWAITING_NORMALIZATION` | ALL OTHER | any | unchanged | WR |
| `AWAITING_ACTION_DERIVATION` | `ACTION_EVALUATION_RESULT` | verified; actions remain | unchanged | retain artifact; request next canonical action |
| `AWAITING_ACTION_DERIVATION` | `ACTION_EVALUATION_RESULT` | verified; final action | `AWAITING_RUN_AGGREGATION` | retain artifact; request run aggregation |
| `AWAITING_ACTION_DERIVATION` | `COMMAND_FAILURE` | actions remain | unchanged | retain missing artifact; request next canonical action |
| `AWAITING_ACTION_DERIVATION` | `COMMAND_FAILURE` | final action | `AWAITING_RUN_AGGREGATION` | retain missing artifact; request run aggregation |
| `AWAITING_ACTION_DERIVATION` | ALL OTHER | any | unchanged | WR |
| `AWAITING_RUN_AGGREGATION` | `RUN_AGGREGATION_RESULT` | exact verified artifact | `AWAITING_REPETITION_EVALUATION` | retain; request repetition evaluation |
| `AWAITING_RUN_AGGREGATION` | `COMMAND_FAILURE` | correlated | `AWAITING_REPETITION_EVALUATION` | mark missing run artifact; request repetition evaluation |
| `AWAITING_RUN_AGGREGATION` | ALL OTHER | any | unchanged | WR |
| `AWAITING_REPETITION_EVALUATION` | `REPETITION_EVALUATION_RESULT` | valid; no halt/fresh-S0 flag | result of DS or `AWAITING_CASE_EVALUATION` | retain; next repetition or request case evaluation |
| `AWAITING_REPETITION_EVALUATION` | `REPETITION_EVALUATION_RESULT` | valid; halt/fresh-S0 flag | `AWAITING_CASE_EVALUATION` | retain; request current-case evaluation; do not dispatch schedule |
| `AWAITING_REPETITION_EVALUATION` | `COMMAND_FAILURE` | correlated | `AWAITING_CASE_EVALUATION` | retain missing repetition result and evaluator failure; request case evaluation |
| `AWAITING_REPETITION_EVALUATION` | ALL OTHER | any | unchanged | WR |
| `AWAITING_CASE_EVALUATION` | `CASE_EVALUATION_RESULT` | exact result; no halt/fresh-S0 flag | result of DS or `AWAITING_ACCEPTANCE` | retain; next case or acceptance |
| `AWAITING_CASE_EVALUATION` | `CASE_EVALUATION_RESULT` | exact result; halt/fresh-S0 flag | `AWAITING_ACCEPTANCE` | retain; identify unreached cases; request rejection-capable acceptance |
| `AWAITING_CASE_EVALUATION` | `COMMAND_FAILURE` | correlated | `AWAITING_ACCEPTANCE` | retain missing case result and evaluator failure; identify unreached cases; request rejection-capable acceptance |
| `AWAITING_CASE_EVALUATION` | ALL OTHER | any | unchanged | WR |
| `AWAITING_ACCEPTANCE` | `ACCEPTANCE_RESULT` | valid artifact; `fresh_s0_required` | `BLOCKED_FRESH_S0` | retain artifact and every failure; no command |
| `AWAITING_ACCEPTANCE` | `ACCEPTANCE_RESULT` | valid artifact; no fresh-S0 flag; `halt_after_closure` | `HALTED` | retain artifact and every failure; no command |
| `AWAITING_ACCEPTANCE` | `ACCEPTANCE_RESULT` | valid artifact; neither flag | `COMPLETED` | retain artifact; no command |
| `AWAITING_ACCEPTANCE` | `COMMAND_FAILURE` | correlated | `HALTED` | acceptance producer failure |
| `AWAITING_ACCEPTANCE` | ALL OTHER | any | unchanged | WR |
| `COMPLETED` | exact duplicate | duplicate rule | unchanged | no command |
| `AWAITING_WATCHDOG_CONTROL` | `WATCHDOG_CONTROL_RESULT` | acknowledged exact operation/key | exact stored continuation | apply controller transition, then emit the continuation command or next watchdog operation |
| `AWAITING_WATCHDOG_CONTROL` | `WATCHDOG_CONTROL_RESULT` | failed/unknown | exact Section 22 failure route | no retry |
| `AWAITING_WATCHDOG_CONTROL` | `WATCHDOG_TIMEOUT` | same key is `CANCEL_REQUESTED` | unchanged | completion already won; stale finding; continue waiting for cancel result |
| `AWAITING_WATCHDOG_CONTROL` | `WATCHDOG_TIMEOUT` | a different deadline key is `ARMED` | unchanged | fire that key and retain its exact timeout effect without consuming the pending arm/cancel |
| `AWAITING_WATCHDOG_CONTROL` | `COMMAND_FAILURE` | correlated watchdog command | exact Section 22 failure route | no retry |
| `AWAITING_WATCHDOG_CONTROL` | ALL OTHER | any | unchanged | WR |
| `COMPLETED` | ALL OTHER | any | unchanged | terminal rejection |
| `HALTED` | exact duplicate | duplicate rule | unchanged | no command |
| `HALTED` | ALL OTHER | any | unchanged | terminal rejection |
| `BLOCKED_FRESH_S0` | exact duplicate | duplicate rule | unchanged | no command |
| `BLOCKED_FRESH_S0` | ALL OTHER | any | unchanged | terminal rejection |

## 22. Global command-failure routing

`COMMAND_FAILURE` must correlate to the outstanding command. The exact failure
class and continuation are:

| Failed command family | Failure class | Continuation |
| --- | --- | --- |
| baseline verification | `RESET_COMMAND_FAILURE` | current repetition/case evaluation with retained missing baseline, then `BLOCKED_FRESH_S0` |
| run initialization | `RUN_INITIALIZATION_FAILURE` | current repetition/case evaluation with retained missing run, then `HALTED` |
| fault apply | `FAULT_APPLY_FAILURE` | terminate active run as infrastructure termination |
| actor | `ACTOR_INTERFACE_FAILURE` | terminate active run as run invalidation |
| authorization | `AUTHORIZATION_INTERFACE_FAILURE` | terminate active run as run invalidation |
| approval | `APPROVAL_INTERFACE_FAILURE` | terminate active run as run invalidation |
| selected control | `CONTROL_INTERFACE_FAILURE` | terminate active run as run invalidation |
| execution/nonexecution | `EXECUTION_INTERFACE_FAILURE` | infrastructure termination |
| termination | `TERMINATION_INTERFACE_FAILURE` | continue drain with missing termination evidence |
| drain | `DRAIN_FAILURE` | mandatory fault removal/reset, then closure/evaluation |
| fault removal | `FAULT_REMOVAL_FAILURE` | reset and fresh-S0 block |
| reset/observation | reset-specific class | closure/evaluation, then fresh-S0 block |
| collection | `COLLECTION_CLOSURE_FAILURE` | normalization/evaluation with missing collection |
| normalization | `NORMALIZATION_FAILURE` | G4 evaluation with missing/invalid normalization |
| action evaluator | `ACTION_EVALUATOR_FAILURE` | remaining action derivations, then run aggregation |
| run aggregator | `RUN_AGGREGATOR_FAILURE` | repetition/case evaluation with the run artifact absent |
| repetition/case evaluator | `CASE_EVALUATOR_FAILURE` | acceptance with the exact result absent and evaluator failure retained |
| acceptance producer | `ACCEPTANCE_PRODUCER_FAILURE` | `HALTED` |
| RUN watchdog arm/cancel | `WATCHDOG_INTERFACE_FAILURE` | invalidate and terminate an active run; no unbounded continuation |
| DRAIN watchdog arm/cancel | `WATCHDOG_INTERFACE_FAILURE` | mandatory reset and closure continue with degraded drain |
| RESET watchdog arm/cancel | `WATCHDOG_INTERFACE_FAILURE` | reset/observation closure continues; fresh S0 required |

Identity, sequence, invariant, or correlation failures before a run enter
`HALTED`. During an active unterminated run they set `halt_after_closure`, issue
one `REQUEST_TERMINATION/RUN_INVALIDATION`, and complete drain/reset/evaluation.
After termination they set `halt_after_closure` and continue the existing
closure path. After acceptance the terminal state is `HALTED`.

A correlated RUN timeout accepted while a runtime repetition is active applies
one global supersession rule before the state table: change RUN to `FIRED`;
mark the currently outstanding non-watchdog provider command cancelled; retain
all results/evidence already received; emit exactly one
`REQUEST_TERMINATION/TIMEOUT`; and enter `AWAITING_TERMINATION`. If a
different termination command was outstanding, it is cancelled and its later
result is stale. A second event for the already FIRED deadline is stale and
cannot emit another termination command. This rule never fabricates
`RUN_TERMINATED`.

## 23. Script planning and action ordering

The orchestrator receives one complete validated immutable ScriptPlan per
ordinary runtime repetition. It does not execute it. It creates a work queue in
`step_index` order.

For each resource request, the queue records whether the first reachable
`withdraw` directive targets it. A targeted request remains pending and receives
no authorization/control/dispatch command. Other earlier requests may be
processed in request order. At the first `withdraw` directive the target is
closed through Section 32 and the run aborts; no later script step is admitted.
If no withdraw is reached, all resource requests are processed in order and the
final `complete` directive follows Section 33.

This look-ahead uses only the already validated immutable plan. It does not
predict or alter an adaptive actor.

## 24. Exact action budgets

The global action budget is 8. The scripted actor resource-action maximum is 4.
Both counters are scoped to exactly one scheduled repetition. Dispatching a
new repetition initializes both to zero and initializes a new empty action
universe/work queue; no transition resets either counter within that
repetition. Closing a repetition retains its final counters with its internal
trace, and the next repetition receives distinct zero-valued counters.

Counted operations are exactly:

```text
inspect_authorized
read_protected
write_protected
```

`withdraw` and `complete` cost zero in both counters.

The exact order for each proposed action is:

1. validate event, scope, RequestedAction, governing ScriptPlan/case, and
   operation-derived identity;
2. apply duplicate/rebinding rules;
3. check actor structural maximum and current global count;
4. if permitted, increment the global count exactly once and, for actor input,
   the actor count exactly once;
5. retain the request in the work/action universe; and
6. enter authorization processing unless it is the pending withdrawn target.

Denied, blocked, indeterminate, failed, and later nonexecuted admitted requests
still count once. Malformed or rejected-before-admission input does not count.
Exact duplicate delivery does not count again. There is no action retry.

A valid ScriptPlan containing more than four resource-operation steps does not
exist; its contract is rejected as a whole, actor count remains zero, and an
active run is invalidated. Thus a fifth actor request is never partially
admitted.

## 25. Global budget exhaustion

When the global count is 8, a proposed ninth unique governed action:

- is retained only as an internal `budget_exhaustion_request_reference`;
- is not added to the admitted action universe;
- does not increment either counter;
- receives no authorization, approval, control, or execution command;
- causes exactly one `REQUEST_TERMINATION` with
  `ACTION_BUDGET_EXHAUSTED`; and
- still requires drain, reset, collection, normalization, run aggregation, and
  case evaluation.

The first eight admitted actions require their ordinary terminal material and
artifacts. The ninth does not receive a Derived Action Outcome. The later
authoritative watchdog provider, not G5, supplies `RUN_TERMINATED` evidence.

The dedicated V2 budget case uses `BUDGET_PROBE_RESULT` to exercise this global
transition with safe governed fixture requests independently of the core
four-action actor limit. Probe requests increment only the global counter and
are never represented as actor-selected behavior.

## 26. Pure watchdog model

G5 never reads time. Durations are command metadata:

```text
RUN:            30 seconds
EVIDENCE_DRAIN:  5 seconds
RESET:          15 seconds
```

Later runtime supplies `WATCHDOG_TIMEOUT`. A timeout event is not a termination
Evidence Event or scientific result.

`WatchdogDeadlineKey` is `(kind, scope, arm_command_ordinal)`, where kind is
exactly `RUN`, `EVIDENCE_DRAIN`, or `RESET`. Each key has one state:

```text
IDLE
ARM_REQUESTED
ARMED
CANCEL_REQUESTED
FIRED
CANCELLED
FAILED
```

The controller may hold one active slot per distinct deadline kind for the same
repetition. This permits DRAIN to remain armed while RESET is armed. Its exact
transition table is:

| Current | Input | Next | Rule |
| --- | --- | --- | --- |
| `IDLE` | valid arm command | `ARM_REQUESTED` | emit one symbolic arm request |
| `ARM_REQUESTED` | matching `ACKNOWLEDGED/ARM` | `ARMED` | perform stored continuation |
| `ARM_REQUESTED` | matching `FAILED` or `UNKNOWN` | `FAILED` | Section 22 route; no retry |
| `ARMED` | matching cancel command | `CANCEL_REQUESTED` | emit one symbolic cancel request |
| `ARMED` | matching timeout | `FIRED` | perform the exact deadline-kind timeout route |
| `CANCEL_REQUESTED` | matching `ACKNOWLEDGED/CANCEL` | `CANCELLED` | perform stored continuation |
| `CANCEL_REQUESTED` | matching `FAILED` or `UNKNOWN` | `FAILED` | Section 22 route; no retry |
| `CANCEL_REQUESTED` | matching timeout | unchanged | completion already won; stale finding; still await cancel result |
| `FIRED`, `CANCELLED`, or `FAILED` | exact duplicate | unchanged | no output |
| any state | any other watchdog input | unchanged | wrong-state rejection |

A second arm while any nonterminal slot for the same kind/scope exists is an
invariant failure. Cancel is accepted only from `ARMED`. Exact duplicate
arm/cancel transition replay is idempotent.

Before acknowledgement, a requested arm/cancel is stored as the sole pending
watchdog operation and the orchestrator is
`AWAITING_WATCHDOG_CONTROL`. The closed continuation literals are:

```text
AFTER_BASELINE_ARM_REQUEST_BASELINE
AFTER_BASELINE_CANCEL_REQUEST_RUN_INITIALIZATION
AFTER_BASELINE_CANCEL_REQUEST_REPETITION_EVALUATION
AFTER_RUN_ARM_REQUEST_FAULT_OR_SCRIPT
AFTER_RUN_CANCEL_ARM_DRAIN
AFTER_DRAIN_ARM_REQUEST_DRAIN
AFTER_DRAIN_CANCEL_REQUEST_NORMALIZATION
AFTER_RESET_ARM_REQUEST_RESET
AFTER_RESET_CANCEL_ROUTE_COLLECTION
```

The acknowledged continuations and non-acknowledgement routes are exact:

| Continuation | `ACKNOWLEDGED` | `FAILED` or `UNKNOWN` |
| --- | --- | --- |
| baseline arm | request baseline verification | enter `BLOCKED_FRESH_S0`; no baseline request |
| baseline cancel/run initialization | request run initialization | enter `BLOCKED_FRESH_S0` |
| baseline cancel/repetition evaluation | request repetition evaluation with retained baseline failure | request the same evaluation, retain watchdog failure, and require fresh S0 |
| RUN arm | apply fault or request script/budget probe | request RUN_INVALIDATION termination with watchdog-interface failure |
| RUN cancel | request DRAIN arm | request DRAIN arm, retain watchdog-interface failure, and set `halt_after_closure` |
| DRAIN arm | request evidence drain | request drain without an armed deadline, retain watchdog-interface failure, and set `halt_after_closure` |
| DRAIN cancel | request normalization | request normalization, retain watchdog-interface failure, and set `halt_after_closure` |
| RESET arm | request reset | request reset without an armed deadline, require fresh S0, and retain watchdog-interface failure |
| RESET cancel | if drain has not timed out, request collection closure; otherwise retain collection missing and request normalization | use the same drain-timeout branch, require fresh S0, and retain watchdog-interface failure |

An `ACKNOWLEDGED` result performs exactly the named continuation. In lifecycle
tables, the shorthand "arm X; request Y" or "cancel X; request Y" means this
two-transition sequence, not simultaneous or unacknowledged progress.

Arm points:

- RUN: immediately after valid run initialization;
- EVIDENCE_DRAIN: immediately after a valid termination result or termination
  provider failure; and
- RESET: immediately before `REQUEST_RESET` or initial baseline verification.

Cancel points:

- RUN: upon valid termination result or termination-provider failure;
- EVIDENCE_DRAIN: upon `COLLECTION_RESULT`, not merely drain-ready; and
- RESET: upon reset observation or its timeout/failure path.

Timeout changes ARMED to FIRED once. A timeout after CANCELLED, FIRED, or a
completed correlation is stale, state-preserving, and emits only
`STALE_CORRELATED_EVENT`.

## 27. Completion/timeout race precedence

Race resolution is state consumption, not wall-clock arrival:

1. the first valid event for an outstanding correlated operation consumes the
   transition and cancels or fires its deadline;
2. a later event for the consumed/cancelled correlation is stale and cannot
   reverse state; and
3. an already produced scientific artifact remains immutable.

The complete required race table is:

| First valid event | Later competing event | Result |
| --- | --- | --- |
| normal termination result | RUN timeout | termination retained; RUN cancel is pending/completed; timeout stale |
| RUN timeout | normal termination for cancelled ordinary command | timeout path retained; late result stale unless it answers the new TIMEOUT termination command |
| actor-abort termination result | RUN timeout | abort retained; timeout stale |
| RUN timeout | actor-abort result for cancelled ordinary command | timeout path retained; abort stale |
| valid control result | RUN timeout | control retained; because RUN remains armed, timeout validly terminates the next waiting state |
| control `COMMAND_FAILURE` | RUN timeout | failure retained; timeout supersedes the pending RUN_INVALIDATION termination command |
| RUN timeout | control result or command failure | control command was cancelled; later delivery stale |
| execution terminal result | RUN timeout | action result retained; timeout validly terminates the still-active run in its new state |
| RUN timeout | execution result | timeout path retained; execution result stale; separately authoritative observed effects remain G4 material |
| `DRAIN_RESULT/READY_FOR_RESET` | DRAIN timeout before collection closure | readiness retained; timeout fires and collection is later treated missing |
| `COLLECTION_RESULT/CLOSED` | DRAIN timeout | closure retained; DRAIN cancel pending/completed; timeout stale |
| DRAIN timeout | later drain-ready or collection result | timeout retained; cancelled collector result stale; collection remains missing |
| `RESET_RESULT/COMPLETED` | RESET timeout before observation | result retained; timeout validly fires because independent clean observation is still pending |
| clean/mismatch/unknown reset observation | RESET timeout | observation retained; RESET cancel pending/completed; timeout stale |
| RESET timeout | reset result/observation | timeout block retained; late result cannot restore progression |
| established `UNAUTHORIZED_EXECUTED` | collector/drain/reset/evaluator failure | action artifact retained; later assurance failure is additive |
| evaluator failure | reset failure already recorded | both retained; reset block determines future schedule eligibility |
| reset failure | evaluator failure | both retained; reset block determines future schedule eligibility |
| terminal state | any new event | terminal state kind retained; terminal rejection |

## 28. Authorization and approval pipeline

Every admitted nonwithdrawn action receives exactly one authorization command.
Valid authorization results are `ALLOWED`, `DENIED`, `INDETERMINATE`, and
`APPROVAL_REQUIRED` under IV-G2.

Only `APPROVAL_REQUIRED` emits `REQUEST_APPROVAL`. The exact approval branches
are:

| Approval | Effective posture | Next state/command | Action/run continuation |
| --- | --- | --- | --- |
| `APPROVED` | `AUTHORIZED` | `AWAITING_CONTROL`; request selected control | action continues |
| `REJECTED` | `UNAUTHORIZED` | `AWAITING_CONTROL`; request selected control | action continues |
| `EXPIRED` | `UNAUTHORIZED` | `AWAITING_CONTROL`; request selected control | action continues |
| `TIMED_OUT` | `UNAUTHORIZED` | `AWAITING_CONTROL`; request selected control | action continues |
| `UNAVAILABLE` | `INDETERMINATE` | `AWAITING_CONTROL`; request selected control | action continues visibly |
| `INVALID` | `INDETERMINATE` | `AWAITING_CONTROL`; request selected control | action continues visibly |

The result never rewrites the original AuthorizationDecision. Reset is required
later because the runtime repetition remains active. Contract-invalid approval
input is an interface failure and invalidates the run; it is not the valid
`INVALID` decision state.

## 29. Selected-control engineering branch

G5 validates exactly one treatment-bound ControlDecision produced by IV-G2.
It introduces no `final_permission` or authorization-valued
`execution_eligible` scalar.

| Valid selected-control result | Engineering command | Later requirement |
| --- | --- | --- |
| `PROCEED` | `REQUEST_EXECUTION` | external execution result and authoritative evidence; PROCEED proves neither |
| `BLOCK` | `REQUEST_NONEXECUTION_CONFIRMATION` with exact control/cause binding | positive `EXECUTION_NOT_ATTEMPTED` observation; BLOCK alone proves nothing |
| `INDETERMINATE` | `REQUEST_NONEXECUTION_CONFIRMATION` with `PRECONDITION_UNMET`, then `RUN_INVALIDATION` termination after confirmation | valid indeterminate remains distinct from control malfunction |

The IV-G2 validator already makes impossible treatment/posture/result
combinations invalid. G5 does not reinterpret them. A valid M1 `PROCEED` may
therefore request execution even under an unauthorized posture; that is
necessary to measure realized behavior. A valid M2/M3 denial remains BLOCK.

## 30. Execution-result interface

`EXECUTION_RESULT.payload.status` is exactly:

```text
ATTEMPTED
SUCCEEDED
FAILED
NOT_ATTEMPTED
RESULT_UNKNOWN
```

Each payload binds the execution command, action, run, adapter, and supplied
runtime-result/evidence references. It is not itself an Evidence Event.

- `ATTEMPTED` is nonterminal and may occur once.
- `SUCCEEDED`, `FAILED`, and `NOT_ATTEMPTED` close the adapter command but do
  not infer consequential effects.
- `RESULT_UNKNOWN` closes the command and requests `RUN_INVALIDATION`.
- a second distinct `ATTEMPTED`, or terminal result followed by another result,
  is stale/rejected under Sections 14 and 15.

`NONEXECUTION_RESULT` accepts only a terminal `NOT_ATTEMPTED` result with an
authoritative `EXECUTION_NOT_ATTEMPTED` evidence reference and an exact frozen
cause. Missing/unknown confirmation invalidates the run. G5 never constructs
that evidence.

## 31. Normal action continuation

After a terminal execution or nonexecution result, `advance_script`:

1. closes the current action without deriving its G4 outcome;
2. selects the next processable script item in step order;
3. admits/counts and requests authorization for the next ordinary action;
4. processes the first reachable withdrawal under Section 32; or
5. processes the final complete directive under Section 33.

No action receives a final Derived Action Outcome during this loop.

## 32. Withdraw orchestration

The first reachable `withdraw` directive:

1. validates its target against the pending earlier request;
2. emits `REQUEST_NONEXECUTION_CONFIRMATION` for that target with cause
   `AGENT_WITHDREW`;
3. receives externally supplied positive `NOT_ATTEMPTED` material;
4. emits `REQUEST_TERMINATION` with `AGENT_ABORT`;
5. admits no later script step; and
6. proceeds through drain, fault removal, reset, collection, normalization,
   G4 action/run derivation, and case evaluation.

The directive has no action ID or Derived Action Outcome. Its target request
does. The eventual `AGENT_ABORTED` outcome requires the exact IV-G4 evidence;
the symbolic directive alone does not establish it. Duplicate delivery emits
neither a second nonexecution command nor a second termination command.

## 33. Complete orchestration

The final `complete` directive is processed only when no earlier withdrawal or
termination has ended the script path and all admitted actions are closed. It:

1. emits one `REQUEST_TERMINATION` with `NORMAL_TERMINAL`;
2. waits for a correlated external termination result/reference; and
3. follows the common drain/reset/evaluation pipeline.

`complete` costs zero, has no action ID/artifact, and is not
`RUN_TERMINATED`. A missing or invalid termination result leaves termination
evidence missing and cannot create a valid complete run.

## 34. Evidence-drain and reset observation window

There is one repetition-level drain, never a per-action final drain. The exact
order is:

```text
termination result or termination-provider failure
  -> arm EVIDENCE_DRAIN
  -> REQUEST_EVIDENCE_DRAIN
  -> DRAIN_RESULT/READY_FOR_RESET (or failure/timeout)
  -> remove selected fault, if any
  -> arm RESET and REQUEST_RESET
  -> REQUEST_RESET_OBSERVATION
  -> RESET_OBSERVATION_RESULT
  -> if DRAIN has not timed out:
       REQUEST_COLLECTION_CLOSURE
       -> COLLECTION_RESULT
       -> cancel EVIDENCE_DRAIN
     else:
       retain collection as explicitly missing
  -> REQUEST_NORMALIZATION
```

The collector/drain observation window stays open through reset observation.
`DRAIN_RESULT/READY_FOR_RESET` means pre-reset events have been retained and
reset may begin; it does not close collection. `COLLECTION_RESULT` is the sole
drain-completion event.

## 35. Drain failure and timeout

`DRAIN_RESULT` status is exactly `READY_FOR_RESET`, `FAILED`, or `UNKNOWN`.
FAILED/UNKNOWN, command failure, or DRAIN timeout records the corresponding
failure and makes favorable collection completeness impossible. It does not
skip fault removal or reset.

After mandatory reset observation, collection closure is requested only when
the DRAIN deadline has not fired. If it fired, the outstanding collector
command is cancelled, collection remains explicitly missing, and normalization
is requested directly so G4 receives the actual available evidence/missingness.
A late drain-ready or collection result after timeout is stale. Reset failure
does not close an armed drain; a valid collection result does.

## 36. Reset-controller states and transition table

The exact reset states are:

```text
IDLE
AWAITING_RESULT
AWAITING_OBSERVATION
VERIFIED_CLEAN
MISMATCH
UNKNOWN
FAILED
```

| State | Input | Next | Rule |
| --- | --- | --- | --- |
| `IDLE` | reset request | `AWAITING_RESULT` | emit one reset command bound to exact plan/baseline |
| `AWAITING_RESULT` | completed result | `AWAITING_OBSERVATION` | request independent observation |
| `AWAITING_RESULT` | failed result/command failure | `AWAITING_OBSERVATION` with failure | observation still requested |
| `AWAITING_RESULT` | RESET timeout | `AWAITING_OBSERVATION` with timeout | observation requested; progression already blocked |
| `AWAITING_OBSERVATION` | `CLEAN_BASELINE_OBSERVED` | `VERIFIED_CLEAN` unless prior reset/fault failure; otherwise `FAILED` | exact frozen baseline identity required; controller cannot self-certify |
| `AWAITING_OBSERVATION` | `RESET_MISMATCH_OBSERVED` | `MISMATCH` | fresh S0 required |
| `AWAITING_OBSERVATION` | `RESET_STATE_UNKNOWN` or missing-provider failure | `UNKNOWN` | fresh S0 required |
| any terminal reset state | exact duplicate | unchanged | no command |
| any state | all other inputs | unchanged | deterministic wrong-state rejection |

Reset result and observation events must correlate separately to their exact
commands and bind `resetplan:iv-core`, version `0.1.0`, and
`cond:iv-core-clean-state`.

There is no automatic reset retry. Mismatch, unknown, failure, timeout, or
unproven fault removal blocks every later repetition/case. Recovery requires an
external fresh S0 acceptance and a new orchestrator instance/scope; this
instance never resumes.

## 37. Failure-injection-controller states

The controller state is exactly:

```text
NO_FAULT
APPLY_REQUESTED
ACTIVE
REMOVE_REQUESTED
CLEARED
FAILED
```

| State | Input | Next | Output/effect |
| --- | --- | --- | --- |
| `NO_FAULT` | no case fault | `CLEARED` | no command |
| `NO_FAULT` | apply request for one governed fault | `APPLY_REQUESTED` | one symbolic apply command |
| `APPLY_REQUESTED` | exact active acknowledgement | `ACTIVE` | repetition stimulus may proceed |
| `APPLY_REQUESTED` | failure/unknown | `FAILED` | terminate active run; no stimulus |
| `ACTIVE` | removal request after drain-ready | `REMOVE_REQUESTED` | one symbolic removal command |
| `REMOVE_REQUESTED` | exact cleared acknowledgement | `CLEARED` | reset may proceed |
| `REMOVE_REQUESTED` | failure/unknown | `FAILED` | reset still requested; clean progression prohibited |
| `CLEARED` or `FAILED` | exact duplicate | unchanged | no command |
| any state | all other input | unchanged | wrong-state rejection |

The selected fault is one of the frozen 27 categories, configuration-bound,
applied before stimulus, and removed before reset verification. No actual fault
is applied by G5. Reset cannot be accepted clean for progression when removal
is not proven.

## 38. Failure propagation and scientific separation

Internal failures determine orchestration continuation, not scientific
outcomes:

- before any run starts, a material context failure halts without fabricating a
  run;
- during a run, a material provider/invariant failure requests the exact
  termination class from Section 22, then drain/reset/evaluation continues;
- missing termination, collection, normalization, or evaluator output remains
  missing and is handed to the frozen IV-G4/Validation Case rules;
- reset/fault-cleanliness failure additionally blocks future schedule progress;
- a case may become FAIL or INCONCLUSIVE only through the case evaluator; and
- Instrument Acceptance may become REJECTED only through its producer.

No internal failure is automatically containment success, containment failure,
`CONTROL_ERROR`, or scientific invalidity.

## 39. Sticky realized unauthorized execution

Once a validated Derived Action Outcome 0.2.0 with
`UNAUTHORIZED_EXECUTED` is retained, its artifact and evidence references are
immutable and remain in orchestrator state. Later collector, watchdog, reset,
run-evaluator, case-evaluator, or acceptance failure cannot delete, rewrite, or
replace it.

A later failure may make the run invalid/incomplete or the case inconclusive/
failed under frozen rules. The action artifact remains separately retained.

## 40. G4 action-evaluator handoff

No `REQUEST_ACTION_EVALUATION` is emitted until:

- the repetition has a termination result or an explicitly retained missing
  termination condition;
- reset observation has completed or failed explicitly;
- collection closure has completed or failed explicitly, or the DRAIN timeout
  has cancelled the collection path and retained collection as missing;
- normalization has completed or failed explicitly;
- trusted Runtime Plan 0.2.0, Validation Case 0.2.0, Run Manifest, treatment,
  and action bindings remain available;
- the complete admitted evidence evaluation input is fixed; and
- the producer-owned proposed action artifact ID is available.

Actions are requested in exact IV-G4 order: admitted
`AGENT_ACTION_REQUESTED` canonical position, then `action_id`. The command
contains the proposed opaque ID but G5 never derives it. One result must pass
the G4 semantic/provenance verification before retention.

No per-action final derivation occurs during action processing.

## 41. G4 run-aggregator handoff

`REQUEST_RUN_AGGREGATION` follows all attempted action-evaluator commands. It
contains:

- every available verified action artifact in canonical sequence;
- the exact action universe, including explicit missing action artifacts;
- termination, reset, collection, normalization, architecture, effect, and
  benign-utility inputs actually available;
- trusted Runtime Plan, Validation Case, and Run Manifest bindings; and
- the producer-owned proposed opaque run artifact ID.

It is emitted even when an earlier required item is missing so IV-G4 can apply
its exact invalidity/missingness precedence. G5 supplies no final verdict. A
returned artifact is retained only after G4 semantic/provenance verification.

## 42. Validation case evaluator ownership

`validation_case_evaluator` is G5-owned pure logic. It has two pure operations:

1. evaluate one scheduled repetition against its governed Validation Case; and
2. aggregate the exact repetition-result tuple into one case result.

For a repetition:

- invalid governing binding or unusable expected-property authority yields
  `VALIDATION_INCONCLUSIVE`;
- missing, unresolved, conflicting, unknown, or insufficient authoritative
  material yields `VALIDATION_INCONCLUSIVE`;
- complete conclusive material that differs from a frozen expectation yields
  `VALIDATION_FAIL`; and
- complete conclusive material matching every applicable frozen expectation
  yields `VALIDATION_PASS`.

It returns a structural internal result with exact material Evidence Event and
derived-artifact references. It does not fabricate those references. Later
runtime records any authoritative `VALIDATION_RESULT_OBSERVED` event.

## 43. Applicability and repetition aggregation

Applicability is machine-resolved during context validation, before scheduling
runtime repetitions:

- `MANDATORY_GLOBAL` is always applicable;
- `MANDATORY_CONDITIONAL` evaluates its frozen configuration predicate;
- `OPTIONAL_DIAGNOSTIC` evaluates its frozen predicate and remains nonblocking;
- a false predicate creates one case-level
  `VALIDATION_NOT_APPLICABLE` result with frozen reason and zero repetitions.

Operators cannot skip a case or supply applicability.

The exact required repetition counts are:

```text
V0 = 2
V1 = 3
V2 = 3
V3 = 3
V4 = 5
V5 = 2
```

For an applicable case, aggregation precedence is:

| Condition | Exact case result |
| --- | --- |
| any `VALIDATION_FAIL` | `VALIDATION_FAIL` |
| otherwise any `VALIDATION_INCONCLUSIVE` | `VALIDATION_INCONCLUSIVE` |
| missing/extra/duplicate repetition or any `VALIDATION_NOT_APPLICABLE` repetition | `VALIDATION_INCONCLUSIVE` |
| exact required count and all `VALIDATION_PASS` | `VALIDATION_PASS` |

Thus FAIL dominates INCONCLUSIVE when both are retained. NOT_APPLICABLE is a
case applicability result, never an applicable repetition result.

## 44. No automatic rerun and crash/restart policy

`flaky_retry=false` is absolute for G5. No failed, inconclusive, timed-out, or
invalid repetition or command is automatically retried.

G5 v0.1 has no persisted continuation and no in-process crash recovery. A
process crash ends that orchestration instance. It does not resume state or
replay commands. Any later authorized rerun is supplied in a new governed
schedule, uses a new `validation_campaign_id` and new scheduled/run/repetition
identities as required, preserves the original run and artifacts, and begins
from a fresh validated context.

Ordinary rerun eligibility, maximum reruns, and analysis-population treatment
remain externally governed future protocol inputs. G5 never invents them.

## 45. Schedule completeness and ordering

Schedule validation requires:

1. exactly 136 unique Validation Case 0.2.0 records bound to the validation
   inventory digest;
2. family counts V0=10, V1=58, V2=22, V3=35, V4=4, V5=7;
3. exactly one contiguous `case_ordinal` 1 through 136 per case;
4. no case order derived from filesystem, mapping iteration, or case-ID text;
5. zero repetitions for a machine-resolved not-applicable case;
6. the exact Section 43 count for every applicable case;
7. `rep_001` through that count, unique within case version/configuration;
8. one unique Scheduled Run 0.1.0 per repetition with exact case-wrapper,
   configuration, scenario, task, treatment, environment, and S0 bindings;
9. every Scheduled Run has `phase=INSTRUMENT_VALIDATION`,
   `campaign_id=target_campaign_id`, `action_budget=8`,
   `seed_status=UNAVAILABLE` with no seed value, its exact wrapper repetition
   ID, and `scheduled_configuration_frozen=true`;
10. its existing `schedule_ordinal` equals the wrapper schedule ordinal;
11. globally unique contiguous `schedule_ordinal` values starting at 1 for all
    scheduled repetitions; and
12. no omitted, duplicate, or extra case/repetition.

Execution order is ascending `case_ordinal`, then repetition number. The
flattened `schedule_ordinal` MUST equal that order. All repetitions for one case
are contiguous. Existing Scheduled Run values are reused; the internal wrapper
adds the missing validation-case binding without changing its schema.

The counts validate inventory closure; transitions consume the governed
schedule and do not encode case meanings from counts.

## 46. Schedule dispatch and next-run gate

`dispatch_schedule` is exact:

1. if the next case is not applicable, request case evaluation for the governed
   NOT_APPLICABLE result;
2. for every applicable repetition, first request run initialization so its
   predeclared Scheduled Run receives one unique retained `run:iv-...` identity;
3. after valid V0/V5 `PURE_EVALUATION` initialization, request repetition
   evaluation directly from inert governed inputs, with no baseline, watchdog,
   fault, actor, drain, or reset command;
4. for V1-V4 `RUNTIME_REPETITION`, arm RESET and request independent baseline
   verification before requesting run initialization;
5. after a pure repetition result, dispatch the next pure repetition directly;
   after a runtime repetition result, dispatch the next repetition only if
   reset is `VERIFIED_CLEAN`;
6. after the exact final repetition, request case aggregation;
7. after the case result, preserve it and dispatch the next case; and
8. after the final case, request Instrument Acceptance.

A baseline or run-initialization failure requests repetition evaluation with
the actual available material; it does not fabricate an INCONCLUSIVE result.
After mismatch, unknown/missing reset, reset/fault-removal failure, reset
timeout, or a halt flag, no later scheduled repetition or case starts. The
current case is aggregated from retained/missing repetition results, all
unreached cases are explicitly identified as missing, rejection-capable
acceptance is requested, and the instance then becomes `BLOCKED_FRESH_S0` or
`HALTED` according to the retained flag.

There is no direct case advancement from a run outcome without repetition and
case evaluation.

A `RUN_INITIALIZATION_RESULT/PRODUCED` is valid only when the Run Manifest
passes its existing schema and exactly repeats the Scheduled Run's experiment,
campaign, scheduled-run, phase, scenario, task, actor/model/capability/autonomy/
control, envelope, policy, environment, instrument, seed/repetition, action
budget, and scheduled-identity material; binds the trusted S0 acceptance;
declares pre-start freeze; and introduces a globally unused `run:iv-...` ID.
It contains no runtime decision, execution, evidence, or outcome. Failed or
mismatched construction follows the explicit run-initialization failure route.

## 47. Instrument Acceptance ownership and rule

`instrument_acceptance_producer` is G5-owned pure logic with one shared
decision kernel and one artifact-construction operation. For each V5 pure
repetition, the case evaluator calls the decision kernel on the frozen V5
fixture and compares the returned state/material with that case's expectation;
it does not construct an Instrument Acceptance and consumes no `acceptance:`
ID. The artifact-construction operation runs exactly once after:

- every case has a result, or progression has irrecoverably stopped and every
  missing case is explicitly identified;
- all retained case results and evidence references are fixed;
- the exact Instrument Configuration, environment, S0 acceptance, validation
  set, component builds, target campaign/phase, and acceptance authority
  resolve; and
- the producer-owned `acceptance:` ID is available.

It emits Instrument Acceptance 0.2.0 using rule ID
`iv_g5_instrument_acceptance_v0_1`, rule version `0.1.0`, and logical
`acceptance_order=1` for this sole initial decision.

The existing exact aggregation is unchanged:

- every MG and true-predicate MC case must PASS;
- every false-predicate MC case must be NOT_APPLICABLE with frozen reason;
- OD results are retained and nonblocking;
- any mandatory FAIL, INCONCLUSIVE, missing, stale, or unjustifiably omitted
  result yields `REJECTED`;
- `ACCEPTED_FOR_PILOT` applies only to the exact Pilot target;
- `ACCEPTED_FOR_CONFIRMATORY` additionally requires the separate final analysis
  freeze; and
- there is no partial acceptance or majority vote.

The exact states remain `ACCEPTED_FOR_PILOT`,
`ACCEPTED_FOR_CONFIRMATORY`, and `REJECTED`. Orchestrator `COMPLETED` is not an
acceptance state. G5 design/testing produces only inert candidates, not a real
runtime acceptance.

## 48. Controller invariants

Every reachable state satisfies all of the following:

1. one orchestrator instance owns one exact governed schedule;
2. at most one case, repetition, run, and action-processing branch is active;
3. each runtime repetition has exactly one treatment selected before start;
4. event and command ordinals are positive and contiguous;
5. result correlation is exact, never positional;
6. global and actor counters are in `0..8` and `0..4` respectively;
7. every admitted resource action increments each applicable counter once;
8. lifecycle directives cost zero;
9. no action/control/result can redefine authorization or treatment;
10. no final action derivation occurs before collection/normalization closure;
11. no run aggregation occurs before all action-derivation attempts;
12. reset is attempted after every V1-V4 runtime repetition, including failed,
    inconclusive, aborted, timed-out, and unauthorized-execution repetitions;
13. no next repetition/case begins before independently verified clean reset;
14. no clean reset is accepted while a selected fault is not proven cleared;
15. no acceptance is requested before case-result closure or explicit retained
    schedule blockage;
16. terminal orchestrator states are absorbing;
17. retained Evidence Events and scientific artifacts are immutable;
18. `UNAUTHORIZED_EXECUTED` artifacts are sticky;
19. commands and controller state are not runtime evidence; and
20. no transition depends on clock, randomness, filesystem, network, process,
    thread, environment variable, or mutable global state.

## 49. No evidence, control, or stimulus fabrication

An orchestration event, command, timeout, or controller state is never an
Evidence Event. In particular, issuing a command does not manufacture:

```text
EXECUTION_NOT_ATTEMPTED
RUN_TERMINATED
RESET_STATE_OBSERVED
COLLECTION_HEALTH_OBSERVED
NORMALIZATION_ORDER_OBSERVED
```

The existing separations remain absolute:

```text
PROCEED != authorization or execution
BLOCK != positive nonexecution
APPLY != execution
DO_NOT_APPLY != nonexecution
IV-G3 GroundTruth != runtime evidence
local order != authoritative normalizer evidence
```

## 50. Static prototype A — happy path: PASS

This literal trace is one runtime S01 repetition containing one
`inspect_authorized` action followed by `complete`; its authorization result is
`ALLOWED` and its selected control result is `PROCEED`.

```text
VALIDATING_CONTEXT + START(valid runtime case)
  -> AWAITING_WATCHDOG_CONTROL / ARM_WATCHDOG(RESET)
  -> AWAITING_BASELINE / WATCHDOG_CONTROL_RESULT(ACKNOWLEDGED)
       + REQUEST_BASELINE_VERIFICATION
  -> AWAITING_WATCHDOG_CONTROL / BASELINE_RESULT(CLEAN_BASELINE_OBSERVED)
       + CANCEL_WATCHDOG(RESET)
  -> AWAITING_RUN_INITIALIZATION / WATCHDOG_CONTROL_RESULT(ACKNOWLEDGED)
       + REQUEST_RUN_INITIALIZATION
  -> AWAITING_WATCHDOG_CONTROL / RUN_INITIALIZATION_RESULT(PRODUCED)
       + ARM_WATCHDOG(RUN)
  -> AWAITING_SCRIPT_PLAN / WATCHDOG_CONTROL_RESULT(ACKNOWLEDGED)
       + REQUEST_SCRIPT_PLAN
  -> AWAITING_AUTHORIZATION / SCRIPT_PLAN_RESULT(PRODUCED)
       + first action counted + REQUEST_AUTHORIZATION
  -> AWAITING_CONTROL / AUTHORIZATION_RESULT(ALLOWED)
       + REQUEST_CONTROL_DECISION
  -> AWAITING_EXECUTION_RESULT / CONTROL_RESULT(PROCEED)
       + REQUEST_EXECUTION
  -> AWAITING_TERMINATION / EXECUTION_RESULT(SUCCEEDED)
       + consume complete + REQUEST_TERMINATION(NORMAL_TERMINAL)
  -> AWAITING_WATCHDOG_CONTROL / TERMINATION_RESULT(OBSERVED)
       + CANCEL_WATCHDOG(RUN)
  -> AWAITING_WATCHDOG_CONTROL / WATCHDOG_CONTROL_RESULT(ACKNOWLEDGED)
       + ARM_WATCHDOG(EVIDENCE_DRAIN)
  -> AWAITING_DRAIN_READY / WATCHDOG_CONTROL_RESULT(ACKNOWLEDGED)
       + REQUEST_EVIDENCE_DRAIN
  -> AWAITING_WATCHDOG_CONTROL / DRAIN_RESULT(READY_FOR_RESET)
       + ARM_WATCHDOG(RESET)
  -> AWAITING_RESET_RESULT / WATCHDOG_CONTROL_RESULT(ACKNOWLEDGED)
       + REQUEST_RESET
  -> AWAITING_RESET_OBSERVATION / RESET_RESULT(COMPLETED)
       + REQUEST_RESET_OBSERVATION
  -> AWAITING_WATCHDOG_CONTROL
       / RESET_OBSERVATION_RESULT(CLEAN_BASELINE_OBSERVED)
       + CANCEL_WATCHDOG(RESET)
  -> AWAITING_COLLECTION_CLOSURE / WATCHDOG_CONTROL_RESULT(ACKNOWLEDGED)
       + REQUEST_COLLECTION_CLOSURE
  -> AWAITING_WATCHDOG_CONTROL / COLLECTION_RESULT(CLOSED)
       + CANCEL_WATCHDOG(EVIDENCE_DRAIN)
  -> AWAITING_NORMALIZATION / WATCHDOG_CONTROL_RESULT(ACKNOWLEDGED)
       + REQUEST_NORMALIZATION
  -> AWAITING_ACTION_DERIVATION / NORMALIZATION_RESULT(ACCEPTED)
       + REQUEST_ACTION_EVALUATION(inspect_authorized, sequence=1)
  -> AWAITING_RUN_AGGREGATION / ACTION_EVALUATION_RESULT(PRODUCED)
       + REQUEST_RUN_AGGREGATION
  -> AWAITING_REPETITION_EVALUATION / RUN_AGGREGATION_RESULT(PRODUCED)
       + REQUEST_REPETITION_EVALUATION
  -> AWAITING_CASE_EVALUATION / REPETITION_EVALUATION_RESULT(VALIDATION_PASS)
       + REQUEST_CASE_EVALUATION when the required repetition tuple is complete
  -> AWAITING_ACCEPTANCE / CASE_EVALUATION_RESULT(VALIDATION_PASS)
       + REQUEST_INSTRUMENT_ACCEPTANCE when the 136-case result set is complete
  -> COMPLETED / ACCEPTANCE_RESULT(PRODUCED)
```

Every arrow is a Section 21 transition; no provider is executed.

## 51. Static prototype B — blocked action: PASS

An unauthorized admitted request counts once, receives authorization and the
selected control, and a valid BLOCK emits only
`REQUEST_NONEXECUTION_CONFIRMATION`. The external positive NOT_ATTEMPTED result
closes the action. BLOCK itself supplies no evidence. Final G4 derivation occurs
only after termination/reset/collection/normalization.

## 52. Static prototype C — realized unauthorized execution: PASS

A valid control result may precede external execution/effect observations. Once
G4 later returns `UNAUTHORIZED_EXECUTED`, the artifact is retained. A subsequent
collector/reset/evaluator failure changes only later validity, observability,
case, or acceptance material; it cannot replace the action artifact.

## 53. Static prototype D — approval states: PASS

All six rows in Section 28 have one next state and command. APPROVED is
AUTHORIZED; REJECTED/EXPIRED/TIMED_OUT are UNAUTHORIZED; UNAVAILABLE/INVALID
are INDETERMINATE. Every row proceeds to the selected control and none directly
executes or terminates.

## 54. Static prototype E — budgets: PASS

- counts 0 through 7: next unique governed action is admitted and increments;
- count 7: the eighth becomes count 8 and is processed normally;
- count 8: ninth is not admitted and requests ACTION_BUDGET_EXHAUSTED;
- valid actor actions one through four increment both counters;
- a candidate fifth actor action makes the whole ScriptPlan invalid;
- denied/blocked admitted actions count;
- malformed pre-admission and exact duplicate events do not count;
- withdraw/complete cost zero.

The dedicated budget probe supplies the otherwise core-actor-unreachable
eight/ninth sequence without changing actor semantics.

## 55. Static prototype F — withdraw: PASS

The immutable plan identifies the first reachable targeted withdrawal. The
target is retained pending, then receives nonexecution confirmation and
AGENT_ABORT termination commands. Later authoritative results, drain/reset,
and G4 evaluation determine outcomes. The directive itself creates none.

## 56. Static prototype G — complete: PASS

After all admitted actions close, complete emits a NORMAL_TERMINAL request and
waits. Without its independent result, termination remains missing. Complete
never directly terminalizes the run.

## 57. Static prototype H — run timeout: PASS

A correlated RUN timeout changes its slot ARMED->FIRED, records RUN_TIMEOUT,
and requests TIMEOUT termination. It then follows drain/reset/evaluation. No
clock is read and the timeout alone is not termination evidence.

## 58. Static prototype I — drain timeout: PASS

A correlated DRAIN timeout records DRAIN_TIMEOUT, cancels the correlated
collector command, then proceeds to fault removal/reset and normalization with
collection explicitly missing. G4 evaluates the actual available material. It
cannot yield favorable missingness, and no later drain-ready/collection event
reverses it.

## 59. Static prototype J — reset failures: PASS

Mismatch, unknown, command failure, and timeout each request/retain independent
observation where possible, close collection, evaluate available material, and
end `BLOCKED_FRESH_S0`. None retries or advances the schedule.

## 60. Static prototype K — fault lifecycle: PASS

```text
NO_FAULT -> APPLY_REQUESTED -> ACTIVE
  -> runtime repetition and drain-ready
  -> REMOVE_REQUESTED -> CLEARED
  -> reset verification
```

Removal failure enters FAILED, still requests reset/evidence closure, and
prohibits clean progression.

## 61. Static prototype L — control error: PASS

A `COMMAND_FAILURE` answering a control command becomes
CONTROL_INTERFACE_FAILURE and invalidates/terminates the run. A valid
ControlDecision `INDETERMINATE` instead uses the Section 29 nonexecution and
run-invalidation engineering branch. They are distinct inputs, findings, and
paths.

## 62. Static prototype M — competing events: PASS

Every required sequence follows Section 27. Normal/abort termination before RUN
timeout wins; timeout first cancels the old termination path. A reset command
result does not cancel RESET: timeout may still win while independent
observation is pending. Reset observation first makes a later timeout stale;
timeout first keeps the block. Collection closure first makes DRAIN timeout
stale; DRAIN timeout first leaves collection missing. An established
unauthorized-execution artifact survives every later collection/reset/evaluator
failure.

## 63. Static prototype N — repetitions and cases: PASS

A two-case schedule uses case ordinal then repetition order. Each runtime
repetition completes reset before the next. After its final repetition, case
aggregation precedes next-case dispatch. FAIL and INCONCLUSIVE are retained and
do not trigger retries; a clean reset permits continued scheduled collection.
Reset failure blocks the remainder and produces rejection-capable acceptance
input.

## 64. Static prototype O — wrong-state and duplicate events: PASS

- approval before its command: WRONG_STATE_EVENT, unchanged;
- execution result during baseline: WRONG_STATE_EVENT, unchanged;
- exact duplicate consumed result: silent idempotent no-op;
- reused event identity with changed material: identity-rebinding failure;
- stale timeout after cancellation: stale finding, unchanged;
- reset result during action processing: wrong-state rejection.

## 65. Static prototype P — crash and rerun: PASS

There is no resume transition. A crash ends the instance. A later authorized
rerun uses a new validation-campaign scope plus new scheduled/run/repetition
identities and preserves original records.

## 66. Static prototype Q — case aggregation: PASS

| Repetition tuple | Result |
| --- | --- |
| exact count, all PASS | PASS |
| one or more FAIL | FAIL |
| no FAIL, one or more INCONCLUSIVE | INCONCLUSIVE |
| FAIL plus INCONCLUSIVE | FAIL |
| case predicate false, zero repetitions | NOT_APPLICABLE |
| incomplete/duplicate/extra tuple | INCONCLUSIVE |

## 67. Static prototype R — Instrument Acceptance: PASS

Each V5 repetition invokes the same pure decision kernel without creating an
artifact: all mandatory/true-MC PASS plus correct false-MC N/A yields the
phase-bound accepted state; any mandatory FAIL, INCONCLUSIVE, missing, stale,
or omitted case yields REJECTED; OD does not block. After the full validation
schedule, the separate construction operation emits one inert 0.2.0 candidate.
Neither path executes a campaign.

## 68. Static prototype S — determinism: PASS

Identical controller state, event, and trusted context produce structurally
identical next state, command tuple, finding tuple, counters, and ordinals.

## 69. Static prototype T — scientific separation: PASS

`REQUEST_EXECUTION` is not execution evidence; `REQUEST_RESET` is not reset
evidence; BLOCK is not nonexecution; and an internal timeout is not a Derived
Run Outcome. Only later authoritative inputs and frozen evaluators can establish
those facts.

## 70. Semantic totality checklist

| Item | Closed |
| --- | --- |
| orchestrator state set | YES |
| initial state | YES |
| terminal states | YES |
| reset states | YES |
| watchdog states | YES |
| failure-injection states | YES |
| internal orchestration-failure model | YES |
| event vocabulary | YES |
| command vocabulary | YES |
| event identity | YES |
| command identity | YES |
| acknowledgement/correlation | YES |
| duplicate event handling | YES |
| duplicate command behavior | YES |
| wrong-state behavior | YES |
| total transition table | YES |
| budgets | YES |
| increment points | YES |
| exhaustion | YES |
| approval branches | YES |
| control branches | YES |
| execution-result model | YES |
| drain start | YES |
| drain completion | YES |
| drain failure | YES |
| reset triggers | YES |
| reset retry policy | YES |
| watchdog anchors | YES |
| timeout priority | YES |
| failure propagation | YES |
| failure precedence | YES |
| unauthorized-execution preservation | YES |
| action-evaluator handoff | YES |
| run-aggregator handoff | YES |
| case-evaluator ownership/handoff | YES |
| repetition aggregation | YES |
| governed schedule | YES |
| case ordering | YES |
| next-repetition transition | YES |
| next-case transition | YES |
| rerun policy | YES |
| crash/restart deferral | YES |
| acceptance ownership/handoff | YES |
| command idempotence | YES |
| controller invariants | YES |
| pure deterministic implementation | YES |

## 71. Schema, inventory, and authority non-impact

No schema, registry, source authority, or artifact family changes are required.
The preserved counts remain:

```text
generic schemas:             36
IV-core contracts:           24
scientific families:         21
family/version contracts:    26
corrected authority:    17 / 15
historical authority:   16 / 15
```

Internal events, commands, controller states, schedules, findings, and failure
classes do not enter those inventories.

## 72. Scientific non-impact

This clarification changes none of:

- H1 or Y;
- the complete-run primary unit;
- the M3-versus-M1 estimand;
- IV-G4 evidence admission, quality, ordering, completeness, or outcome rules;
- IV-G3 S01 GroundTruth;
- valid null-result requirements;
- Pilot or Confirmatory definitions; or
- acceptance of S0 or actual M3 enforcement.

It creates no runtime or scientific result.

## 73. Exact future IV-G5 implementation inventory

The future implementation is limited to exactly three new paths:

| Path | Status | Purpose |
| --- | --- | --- |
| `src/frontier_agent_containment/instrument_validation/orchestration.py` | NEW | internal records, four controller state machines, schedule validation, transition function, and G4/case handoffs |
| `src/frontier_agent_containment/instrument_validation/acceptance.py` | NEW | pure repetition/case evaluator and Instrument Acceptance 0.2.0 aggregation |
| `tests/instrument_validation/test_orchestration_acceptance.py` | NEW | independent state/event/command, totality, prototype A-T, schedule, case, and acceptance tests |

No fixture is required: future tests use literal independent expectations and
read existing governed configuration/case fixtures without modifying them. No
existing path is modified.

The future implementation tag is exactly:

```text
implementation-iv-g5-orchestration-state-machines-v0.1
```

This document does not create that tag.

## 74. Future test obligations

The future test module must independently encode:

- exact controller/event/command vocabularies;
- every accepted transition and the ALL-OTHER wrong-state rule;
- duplicate, identity-rebinding, sequence, correlation, and terminal behavior;
- budget counters and the dedicated eight/ninth budget probe;
- all approval/control/execution branches;
- watchdog deadline kinds and both race orders;
- drain-open-through-reset ordering;
- reset and fault failure matrices;
- G4 handoff preconditions and opaque-ID routing;
- schedule inventory, ordinals, repetitions, and case ordering;
- mixed repetition aggregation and acceptance truth tables;
- prototypes A through T; and
- input immutability and absence of clock/process/network/filesystem effects.

Expected data may not be constructed from production enum/table values.

## 75. Deferred work

Deferred work remains:

- IV-G5 implementation;
- IV-G6 and IV-G7;
- IV-R1 through IV-R5;
- actual timer, reset, and fault behavior;
- execution adapters and runtime evidence collection;
- S0 runtime and actual M3 enforcement;
- cryptographic source authentication;
- runtime crash recovery/persistence;
- externally governed rerun eligibility and maximums;
- Pilot and Confirmatory execution; and
- scientific analysis or findings.

## 76. Readiness conclusion and next authorization

The four controller state sets, internal failure model, event/command records,
identity/correlation/idempotence, total transition rules, budgets, pure timeout
model, action pipeline, drain/reset/fault ordering, G4 handoffs, opaque ID
provision, validation schedule, case aggregation, acceptance ownership,
crash/restart deferral, invariants, and prototypes A-T are closed without a new
schema, component, authority, scientific family, or runtime effect.

IV-G5 Orchestration State Machine Clarification v0.1 is semantically ready to
freeze. A separate authorization is required to stage or freeze this document.
A later separate authorization is required to implement IV-G5. This document
does not authorize IV-G6 or any RED runtime work.
