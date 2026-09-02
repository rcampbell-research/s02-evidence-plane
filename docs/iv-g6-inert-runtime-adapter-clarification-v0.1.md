# IV-G6 Inert Runtime Adapter Clarification v0.1

## 1. Status and purpose

This document freezes the complete deterministic contract for IV-G6 Inert
Runtime Adapters. It closes component and command ownership, provider request
and supplied-result structures, identity, correlation, translation, failure,
duplicate, authority, and later-runtime boundaries without implementing or
invoking a runtime.

IV-G6 is an inert translation and validation layer. It may validate an already
constructed IV-G5 symbolic command, construct an immutable provider request,
validate an explicitly supplied immutable provider result, and translate that
result into an IV-G5 `OrchestrationEvent`. It MUST NOT obtain a result by
invoking a provider.

This is a design clarification only. It creates no adapter implementation,
schema, fixture, runtime request, provider result, Evidence Event, S0
acceptance, Instrument Acceptance, Pilot or Confirmatory result, or scientific
finding. Normative words such as MUST, MUST NOT, REQUIRED, and EXACT govern a
later separately authorized IV-G6 implementation.

## 2. Frozen predecessor chain and preserved evidence

The implementation base is:

```text
b053347e3f9440c49e684fe423677efe98f1e60c
```

The required predecessor tags and peeled targets are:

| Milestone | Peeled target |
| --- | --- |
| `implementation-iv-g5-orchestration-state-machines-v0.1` | `b053347e3f9440c49e684fe423677efe98f1e60c` |
| `iv-g5-orchestration-state-machine-clarification-v0.1` | `4ba50bc969f5c1b4c00291a1361a074dccc0e60b` |
| `implementation-iv-g4-evidence-outcomes-v0.1` | `205ad17667a22abc6e210b2c773c8652d6d12c60` |
| `implementation-iv-g3-synthetic-scenario-v0.1` | `14a66bfdde19b5487adf1daf3835744a2c8a26f7` |

The preserved exact-byte complete-suite baseline is 3797 passing tests, zero
failures, and no fatal signal. The historical pre-correction G5 evidence of
159 focused and 2868 full tests is obsolete. The earlier Stage 12E-4 SIGSEGV
remains a transient, non-reproduced process termination with unknown root
cause. The historical IV-G3 accepted nonsemantic MINOR remains unchanged.

## 3. Governing order

This clarification is interpreted with, and does not replace:

1. the Research Contract and Statistical Analysis Plan;
2. the Instrument Validation, Evidence, Control Architecture, and
   Implementation specifications;
3. the Instrument Validation implementation-readiness clarification;
4. the IV-G1 reference-closure clarification and corrected Runtime Plan
   0.2.0/source catalog;
5. the IV-G2 actor, authorization, approval, and control clarifications;
6. the IV-G3 synthetic S01 GroundTruth clarification;
7. the IV-G4 representation, admission, ordering, and outcome clarifications;
   and
8. the IV-G5 orchestration clarification and implementation.

Where G6 transport mechanics were open, this document selects an internal
engineering rule. It does not change a scientific field, G5 state/event/
command literal, provider component, authority source, artifact family, or RED
gate.

## 4. Fundamental GREEN/RED boundary

The normative invariant is:

```text
ADAPTER CONSTRUCTION OR TRANSLATION != RUNTIME EXECUTION
```

G6 MAY only:

- validate a frozen G5 symbolic command;
- resolve exact governed component, build, and local-channel bindings from an
  explicit immutable adapter context;
- construct an immutable inert `ProviderRequest`;
- validate a supplied inert `ProviderResult`;
- preserve command identity and all applicable scope fields;
- translate a valid supplied result into an immutable G5 event using a
  G5-supplied event ordinal;
- transport governed opaque references without asserting their truth; and
- deterministically reject malformed or mismatched input.

G6 MUST NOT:

- invoke a provider, callback, actor, scenario, control, observer, collector,
  normalizer, reset, watchdog, fault mechanism, or model;
- execute or dispatch an action;
- enforce M3;
- instantiate or accept S0;
- read a clock, wait, sleep, start a thread/process, or detect a timeout;
- inspect or mutate a resource, S01 state, filesystem, namespace, process, or
  network;
- collect, normalize, admit, derive, or write evidence;
- create authoritative runtime facts or Evidence Events; or
- perform IV-R1 through IV-R5, Pilot, Confirmatory, or scientific execution.

Configured durations, component builds, channels, supplied statuses, and
opaque references are inert data only.

## 5. No new schema, registry, component, or authority

`ProviderRequest`, `ProviderResult`, their identities and payloads,
`AdapterContext`, S0 declarations, observer declarations, and G6 diagnostics
are internal immutable implementation records. They require no top-level JSON
Schema and are not scientific artifacts.

The public architecture remains exactly the existing 21 components. G6 does
not register an adapter component in addition to those components. The local
source-channel adapter is an internal helper owned beneath
`evidence_collector`; it has no component ID, source registration, build,
authority property, or independent lifecycle.

The active corrected authority remains 17 properties and 15 sources. A
provider component or successful provider result is not automatically an
evidence authority. No new source, schema, scientific family, family/version
entry, authority property, or validation case is introduced.

## 6. Exact component inventory and later ownership

`YES` means G6 defines an inert descriptor or command/result translation for
the existing component. It does not mean the component is invoked. Every one
of the 21 components is closed below.

| Existing component | G6 | Exact inert G6 role | G5 request/result family | First actual-effect stage |
| --- | --- | --- | --- | --- |
| `validation_orchestrator` | NO | G5 owns schedule, command, event, pending correlation, and delivery history | internal G5 | R2 invokes an integrated orchestrator |
| `scripted_validation_actor` | NO | closed script selection/parsing remains pure G2/G5 | `REQUEST_SCRIPT_PLAN` / `SCRIPT_PLAN_RESULT` internal | R2 actor delivery |
| `scenario_adapter` | YES | translate run-initialization command/result only; never apply an S01 transition | `SCENARIO_INITIALIZATION` | R2 scenario initialization/mutation |
| `authorization_service` | NO | pure G2 authorization calculation remains in process | authorization internal | R2 integrated delivery only |
| `approval_emulator` | NO | pure deterministic G2 approval calculation remains in process | approval internal | R2 integrated delivery only |
| `m1_policy_context_adapter` | NO | pure selected M1 calculation remains G2-owned | control internal | R2 delivery of actual M1 context |
| `m2_policy_mediator` | NO | pure selected M2 calculation remains G2-owned | control internal | R2 actual M2 mediation |
| `m3_external_enforcer` | YES | validate an immutable `M3EnforcementIntent` embedded in execution/nonexecution requests; no separate G5 command | descriptor/intent only | R2 actual external enforcement |
| `action_execution_adapter` | YES | execution and positive-nonexecution request/result translation | `EXECUTION`, `NONEXECUTION_CONFIRMATION` | R2 actual dispatch/execution |
| `s0_environment_boundary` | YES | construct and validate one inert `S0AdapterDeclaration`; no G5 command/result | descriptor only | R1 S0 construction and acceptance |
| `resource_state_observer` | YES | baseline and independent reset-observation request/result translation plus inert observer declaration | `BASELINE_OBSERVER`, `RESET_OBSERVER` | R1 reset/baseline observation; R2 effect observation |
| `s0_boundary_observer` | YES | inert observer declaration only; no G5 command/result in G6 v0.1 | descriptor only | R1 S0 observation and acceptance |
| `evidence_collector` | YES | drain and collection-closure request/result translation; own the local source-channel helper | `EVIDENCE_DRAIN`, `COLLECTION_CLOSURE` | R1 interface/health acceptance; R2/R3 collection |
| `evidence_normalizer_store` | NO | normalization remains pure G4/G5 in v0.1 | normalization internal | R2/R3 runtime normalization/store operation |
| `action_outcome_evaluator` | NO | G4 owns pure action derivation | action evaluation internal | R3 campaign use of frozen evaluator |
| `run_outcome_aggregator` | NO | G4 owns pure run aggregation | run aggregation internal | R3 campaign use of frozen aggregator |
| `validation_case_evaluator` | NO | G5 owns pure repetition/case evaluation | repetition/case internal | R3 campaign evaluation |
| `instrument_acceptance_producer` | NO | G5 owns pure complete-inventory acceptance | acceptance internal | R3 produces runtime-backed acceptance |
| `reset_controller` | YES | reset request/result translation only | `RESET_PROVIDER` | R1 reset acceptance; R2 reset use |
| `watchdog_controller` | YES | watchdog arm/cancel, supplied timeout, and termination translation only | `WATCHDOG`, `TERMINATION` | R1 real-time acceptance; R2 enforcement/use |
| `failure_injection_controller` | YES | fault apply/remove request/result translation only | `FAULT_CONTROL` | R2 actual bounded fault application/removal |

There are ten existing components with a G6 inert surface and eleven without
one. The descriptor-only S0, S0-observer, and M3 surfaces do not add G5
commands or events.

## 7. Local source-channel ownership

`LocalSourceChannelBinding` is an internal immutable G6 helper owned by
`evidence_collector`. It contains exactly:

| Field | Rule |
| --- | --- |
| `source_registration_id` | one exact existing source ID |
| `source_component_id` | exact registered component |
| `source_version` | exact registered component/source version |
| `source_build_id` | exact Runtime Plan/component-catalog build |
| `instrument_configuration_id` | exactly the active scope configuration |
| `dedicated_local_channel_id` | exact existing registered local channel |
| `authoritative_properties` | exact ordered frozen property tuple for that source |

It validates data already supplied in `AdapterContext`. It opens no channel,
receives no bytes, authenticates no remote party, allocates no source identity,
and confers no authority. Cryptographic source authentication remains deferred.

The relevant existing channel bindings are exact:

| Provider component | Source/channel used by G6 |
| --- | --- |
| `action_execution_adapter` | `source:execution` / `channel_execution` |
| `resource_state_observer` | `source:resource` / `channel_resource` |
| `s0_boundary_observer` | `source:s0` / `channel_s0` (descriptor only) |
| `watchdog_controller` | `source:watchdog` / `channel_watchdog` |
| `evidence_collector` | `source:collector` / `channel_collector` |
| `m3_external_enforcer` | `source:m3` / `channel_m3` (intent binding only) |

`scenario_adapter`, `reset_controller`, and
`failure_injection_controller` have no evidence-source registration. Their G6
provider binding MUST carry `source_registration_id=None` and
`dedicated_local_channel_id=None`. G6 MUST NOT invent a channel for them.

## 8. Closed adapter-family vocabulary

The exact G6 request/result adapter families are:

```text
BASELINE_OBSERVER
SCENARIO_INITIALIZATION
WATCHDOG
FAULT_CONTROL
EXECUTION
NONEXECUTION_CONFIRMATION
TERMINATION
EVIDENCE_DRAIN
RESET_PROVIDER
RESET_OBSERVER
COLLECTION_CLOSURE
```

S0 declaration, S0-observer declaration, and M3 enforcement intent are exact
descriptor types, not additional adapter-family literals.

## 9. All 24 G5 command kinds: closed ownership

The ownership values are exactly `INTERNAL_PURE`, `G6_ADAPTED`,
`DEFERRED_RED`, and `INVALID_FOR_G6`. Actual later execution of a
`G6_ADAPTED` request is RED, but construction of that request is GREEN.

| G5 command kind | Ownership | Adapter family / provider | Permitted supplied-result event |
| --- | --- | --- | --- |
| `REQUEST_BASELINE_VERIFICATION` | `G6_ADAPTED` | `BASELINE_OBSERVER` / `resource_state_observer` | `BASELINE_RESULT` |
| `REQUEST_RUN_INITIALIZATION` | `G6_ADAPTED` | `SCENARIO_INITIALIZATION` / `scenario_adapter` | `RUN_INITIALIZATION_RESULT` |
| `ARM_WATCHDOG` | `G6_ADAPTED` | `WATCHDOG` / `watchdog_controller` | `WATCHDOG_CONTROL_RESULT`, later `WATCHDOG_TIMEOUT` |
| `CANCEL_WATCHDOG` | `G6_ADAPTED` | `WATCHDOG` / `watchdog_controller` | `WATCHDOG_CONTROL_RESULT` |
| `REQUEST_FAULT_APPLY` | `G6_ADAPTED` | `FAULT_CONTROL` / `failure_injection_controller` | `FAULT_RESULT` |
| `REQUEST_SCRIPT_PLAN` | `INTERNAL_PURE` | G2/G5 closed-script interface | `SCRIPT_PLAN_RESULT` |
| `REQUEST_BUDGET_PROBE` | `INTERNAL_PURE` | G5 pure fixture interface | `BUDGET_PROBE_RESULT` |
| `REQUEST_AUTHORIZATION` | `INTERNAL_PURE` | G2 authorization | `AUTHORIZATION_RESULT` |
| `REQUEST_APPROVAL` | `INTERNAL_PURE` | G2 approval | `APPROVAL_RESULT` |
| `REQUEST_CONTROL_DECISION` | `INTERNAL_PURE` | one selected G2 M1/M2/M3 calculation | `CONTROL_RESULT` |
| `REQUEST_EXECUTION` | `G6_ADAPTED` | `EXECUTION` / `action_execution_adapter` | `EXECUTION_RESULT` |
| `REQUEST_NONEXECUTION_CONFIRMATION` | `G6_ADAPTED` | `NONEXECUTION_CONFIRMATION` / `action_execution_adapter` | `NONEXECUTION_RESULT` |
| `REQUEST_TERMINATION` | `G6_ADAPTED` | `TERMINATION` / `watchdog_controller` | `TERMINATION_RESULT` |
| `REQUEST_EVIDENCE_DRAIN` | `G6_ADAPTED` | `EVIDENCE_DRAIN` / `evidence_collector` | `DRAIN_RESULT` |
| `REQUEST_FAULT_REMOVAL` | `G6_ADAPTED` | `FAULT_CONTROL` / `failure_injection_controller` | `FAULT_RESULT` |
| `REQUEST_RESET` | `G6_ADAPTED` | `RESET_PROVIDER` / `reset_controller` | `RESET_RESULT` |
| `REQUEST_RESET_OBSERVATION` | `G6_ADAPTED` | `RESET_OBSERVER` / `resource_state_observer` | `RESET_OBSERVATION_RESULT` |
| `REQUEST_COLLECTION_CLOSURE` | `G6_ADAPTED` | `COLLECTION_CLOSURE` / `evidence_collector` | `COLLECTION_RESULT` |
| `REQUEST_NORMALIZATION` | `INTERNAL_PURE` | G4 normalization/admission interface | `NORMALIZATION_RESULT` |
| `REQUEST_ACTION_EVALUATION` | `INTERNAL_PURE` | G4 action evaluator | `ACTION_EVALUATION_RESULT` |
| `REQUEST_RUN_AGGREGATION` | `INTERNAL_PURE` | G4 run aggregator | `RUN_AGGREGATION_RESULT` |
| `REQUEST_REPETITION_EVALUATION` | `INTERNAL_PURE` | G5 case evaluator | `REPETITION_EVALUATION_RESULT` |
| `REQUEST_CASE_EVALUATION` | `INTERNAL_PURE` | G5 case evaluator | `CASE_EVALUATION_RESULT` |
| `REQUEST_INSTRUMENT_ACCEPTANCE` | `INTERNAL_PURE` | G5 acceptance producer | `ACCEPTANCE_RESULT` |

Totals are exactly 13 `G6_ADAPTED`, 11 `INTERNAL_PURE`, zero
`DEFERRED_RED`, and zero `INVALID_FOR_G6`. G6 MUST reject construction for any
of the eleven internal commands with `COMMAND_NOT_ADAPTED`.

## 10. All 25 G5 event kinds: closed ownership

| G5 event kind | Ownership | Exact producer/translation owner |
| --- | --- | --- |
| `START` | `G5_LIFECYCLE_DELIVERY` | G5 delivery owner |
| `BASELINE_RESULT` | `G6_TRANSLATED_PROVIDER_RESULT` | `BASELINE_OBSERVER` |
| `RUN_INITIALIZATION_RESULT` | `G6_TRANSLATED_PROVIDER_RESULT` | `SCENARIO_INITIALIZATION` |
| `FAULT_RESULT` | `G6_TRANSLATED_PROVIDER_RESULT` | `FAULT_CONTROL` |
| `SCRIPT_PLAN_RESULT` | `INTERNAL_PURE` | G2/G5 script-plan interface |
| `BUDGET_PROBE_RESULT` | `INTERNAL_PURE` | G5 pure budget probe |
| `AUTHORIZATION_RESULT` | `INTERNAL_PURE` | G2 authorization |
| `APPROVAL_RESULT` | `INTERNAL_PURE` | G2 approval |
| `CONTROL_RESULT` | `INTERNAL_PURE` | selected G2 control calculation |
| `EXECUTION_RESULT` | `G6_TRANSLATED_PROVIDER_RESULT` | `EXECUTION` |
| `NONEXECUTION_RESULT` | `G6_TRANSLATED_PROVIDER_RESULT` | `NONEXECUTION_CONFIRMATION` |
| `TERMINATION_RESULT` | `G6_TRANSLATED_PROVIDER_RESULT` | `TERMINATION` |
| `DRAIN_RESULT` | `G6_TRANSLATED_PROVIDER_RESULT` | `EVIDENCE_DRAIN` |
| `RESET_RESULT` | `G6_TRANSLATED_PROVIDER_RESULT` | `RESET_PROVIDER` |
| `RESET_OBSERVATION_RESULT` | `G6_TRANSLATED_PROVIDER_RESULT` | `RESET_OBSERVER` |
| `COLLECTION_RESULT` | `G6_TRANSLATED_PROVIDER_RESULT` | `COLLECTION_CLOSURE` |
| `NORMALIZATION_RESULT` | `INTERNAL_PURE` | G4/G5 normalization interface |
| `ACTION_EVALUATION_RESULT` | `INTERNAL_PURE` | G4 action evaluator |
| `RUN_AGGREGATION_RESULT` | `INTERNAL_PURE` | G4 run aggregator |
| `REPETITION_EVALUATION_RESULT` | `INTERNAL_PURE` | G5 case evaluator |
| `CASE_EVALUATION_RESULT` | `INTERNAL_PURE` | G5 case evaluator |
| `ACCEPTANCE_RESULT` | `INTERNAL_PURE` | G5 acceptance producer |
| `WATCHDOG_CONTROL_RESULT` | `G6_TRANSLATED_PROVIDER_RESULT` | `WATCHDOG` control response |
| `WATCHDOG_TIMEOUT` | `G6_TRANSLATED_PROVIDER_RESULT` | supplied `WATCHDOG` timeout notification |
| `COMMAND_FAILURE` | `G5_LIFECYCLE_DELIVERY` | G5 command-delivery owner when no valid provider result exists |

Totals are exactly 12 `G6_TRANSLATED_PROVIDER_RESULT`, 11 `INTERNAL_PURE`,
two `G5_LIFECYCLE_DELIVERY`, zero `DEFERRED_RED`, and zero
`NOT_G6_OWNED`. G6 does not translate a supplied `ProviderResult` into
`COMMAND_FAILURE`.

## 11. Exact immutable adapter context

`AdapterContext` is explicitly supplied to every G6 function. It is built
only from a Runtime Plan 0.2.0 already validated against the independent G1
trusted catalog. It contains exactly:

| Field | Exact rule |
| --- | --- |
| `scope` | exact G5 `OrchestrationScope`; Runtime Plan must be `ivplan:iv-core-001` version `0.2.0` |
| `instrument_configuration_binding` | exact configuration ID, version, and digest from the validated Runtime Plan and public artifact catalog |
| `environment_binding` | exact environment ID, version, and build from the trusted plan/catalog |
| `s0_declaration_binding` | exact `cond:s0-iv-core`, version, `s0_environment_boundary`, and `s0plan:iv-core` |
| `scenario_binding` | exact immutable Runtime Plan scenario-binding projection, including scenario, adapter, GroundTruth observer, reset controller, safety configuration, and all synthetic/public/credential flags |
| `capability_envelope_binding` | exact capability-envelope ID and version from the validated Runtime Plan |
| `reset_binding` | exact `resetplan:iv-core`, version `0.1.0`, baseline `cond:iv-core-clean-state`, and `reset_controller` |
| `control_bindings` | exact immutable Runtime Plan M1/M2/M3, authorization/policy, approval/policy, and execution-adapter binding projection |
| `source_registry_binding` | exact `sourceregistry:iv-core` version `0.1.0` |
| `component_bindings` | exact ordered immutable 21-component tuple from the validated Runtime Plan and build catalog |
| `source_channel_bindings` | exact ordered immutable 15-source tuple from `sourceregistry:iv-core` version `0.1.0` |

Each `ComponentBinding` contains exactly `component_id`, `component_role`,
`component_version`, `build_id`, `implementation_reference`, `trust_context`,
the ordered `frozen_zones` tuple, and ordered
`dependency_component_ids` tuple. Each source-channel binding has the exact
Section 7 fields.

The context contains no callback, provider object, open handle, endpoint,
credential, mutable registry, runtime state, or ambient lookup. Candidate
request/result material cannot populate the expected context against which it
is validated.

## 12. Provider binding and build/channel rules

`ProviderBinding` contains exactly:

```text
component_id
component_version
build_id
source_registration_id
dedicated_local_channel_id
```

The first three fields are mandatory and exactly equal the matching trusted
`ComponentBinding`. The last two are either both the exact matching source
registration/channel or both `None` according to Section 7. No arbitrary
provider name, version alias, build alias, fallback channel, path, URI,
endpoint, or runtime handle is permitted.

Every request and result repeats this exact provider binding. A wrong component,
version, build, source registration, or channel is rejected before event
construction. This validates interface binding only; it does not authenticate
runtime truth.

Build binding is mandatory for every family. Source/channel applicability is
exactly:

| Adapter family | Source/channel rule |
| --- | --- |
| `BASELINE_OBSERVER` | mandatory `source:resource` / `channel_resource` |
| `SCENARIO_INITIALIZATION` | not applicable; both fields MUST be `None` |
| `WATCHDOG` | mandatory `source:watchdog` / `channel_watchdog` |
| `FAULT_CONTROL` | not applicable; both fields MUST be `None` |
| `EXECUTION` | mandatory `source:execution` / `channel_execution` |
| `NONEXECUTION_CONFIRMATION` | mandatory `source:execution` / `channel_execution` |
| `TERMINATION` | mandatory `source:watchdog` / `channel_watchdog` |
| `EVIDENCE_DRAIN` | mandatory `source:collector` / `channel_collector` |
| `RESET_PROVIDER` | not applicable; both fields MUST be `None` |
| `RESET_OBSERVER` | mandatory `source:resource` / `channel_resource` |
| `COLLECTION_CLOSURE` | mandatory `source:collector` / `channel_collector` |

The descriptor-only M3 intent binding requires `source:m3` / `channel_m3`;
the S0-observer declaration requires `source:s0` / `channel_s0`.

## 13. Common ProviderRequest envelope and identity

`ProviderRequest` is an immutable internal record with exactly:

| Field | Rule |
| --- | --- |
| `adapter_family` | one Section 8 literal selected by command kind |
| `provider_binding` | exact Section 12 target binding |
| `command_identity` | exact originating G5 command identity |
| `scope` | exact command scope |
| `instrument_configuration_binding` | exact context configuration ID, version, and digest; the ID/version equal the command scope |
| `case_id` | exact command value, including exact absence |
| `repetition_id` | exact command value, including exact absence |
| `run_id` | exact command value, including exact absence |
| `action_id` | exact command value, including exact absence |
| `payload` | one exact family request payload from Section 14 |

Provider request identity IS the G5 command identity:

```text
(scope, command_ordinal)
```

There is no second request ID. `build_provider_request(command, context)` first
requires a structurally valid G5 command, then validates exact family, target,
scope, component/build/channel, and payload. It constructs data only.

Request and result `payload` reuse the existing immutable G5 `FrozenPayload`
representation: a key-sorted tuple of unique `(name, frozen_value)` pairs.
G6 introduces no arbitrary mapping or second payload container. The exact key
sets and value contracts in Sections 14 and 17 are discriminated by family;
unknown keys are rejected.

## 14. Exact family request payloads

Every field below is required unless explicitly marked nullable. Unknown fields
are forbidden. Values are the exact already-validated immutable values from
the G5 command except for the G6-derived `m3_enforcement_intent`.

| Command | Exact ProviderRequest payload fields and rules |
| --- | --- |
| `REQUEST_BASELINE_VERIFICATION` | `reset_plan_id`, `reset_plan_version`, `clean_state_condition`, `baseline_identity` copied exactly; frozen singleton values required |
| `REQUEST_RUN_INITIALIZATION` | `scheduled_run`, `validation_case`, `repetition`, `selected_treatment`, `configuration_references` copied exactly |
| `ARM_WATCHDOG` | `deadline_key`, `duration_seconds` copied exactly; duration MUST be RUN 30, EVIDENCE_DRAIN 5, or RESET 15 according to key |
| `CANCEL_WATCHDOG` | exact copied `deadline_key` |
| `REQUEST_FAULT_APPLY` | exact copied `fault_binding`, `fault_fixture_reference`; category must be one of the frozen 27 |
| `REQUEST_EXECUTION` | exact copied `action`, `authorization`, nullable `approval`, `control`; derived nullable `m3_enforcement_intent` under Section 15 |
| `REQUEST_NONEXECUTION_CONFIRMATION` | exact copied `action`, nullable `approval`, `cause`; `authorization` and `control` are nullable only for `AGENT_WITHDREW` and otherwise are exact retained G2 decisions; derived nullable `m3_enforcement_intent` under Section 15 |
| `REQUEST_TERMINATION` | exact copied `cause`, `causal_references` |
| `REQUEST_EVIDENCE_DRAIN` | exact copied `run_reference`, `repetition_reference`, `collector_reference`, `reset_plan_reference`, `drain_deadline_key` |
| `REQUEST_FAULT_REMOVAL` | exact copied `fault_binding`, `apply_result_reference` |
| `REQUEST_RESET` | exact copied `reset_plan_id`, `reset_plan_version`, `baseline_identity`, `clean_state_condition` |
| `REQUEST_RESET_OBSERVATION` | exact copied `reset_plan_id`, `reset_result_reference`, `baseline_identity`, `observer_reference` |
| `REQUEST_COLLECTION_CLOSURE` | exact copied `run_reference`, `repetition_reference`, `evidence_set_identity`, nullable `reset_observation_references` |

Nested G2/G5 objects retain their frozen types and identities. Arbitrary
`Mapping[str, Any]`, truthy permission, alternate enum spelling, missing field,
or implicit default is forbidden.

## 15. Exact M3 enforcement intent

G2 owns the pure M3 decision. G6 does not recalculate it and there is no
separate G5 enforcement command. For execution/nonexecution only,
`M3EnforcementIntent` contains exactly:

```text
control_decision_id
authorization_decision_id
approval_decision_id
m3_provider_binding
m3_source_channel_binding
```

The approval ID is nullable exactly when the retained G2 decision has no
approval. `m3_provider_binding` must resolve to `m3_external_enforcer` version
`0.1.0` and the trusted build. The source binding must be exactly
`source:m3` / `channel_m3`.

The intent is REQUIRED iff the retained `ControlDecision.control_layer` is
`M3`, and MUST be absent for M1 or M2. It repeats no scalar permission and
does not mean authorization, enforcement, execution, or effect. R2 owns actual
M3 consumption and enforcement.

## 16. Common ProviderResult envelope and result identity

`ProviderResult` is supplied as data. It is never acquired by G6. It is an
immutable internal record with exactly:

| Field | Rule |
| --- | --- |
| `result_identity` | exact structural identity below |
| `adapter_family` | exact family of the originating request |
| `provider_binding` | exactly the request provider binding |
| `command_identity` | exactly the request/originating command identity |
| `scope` | exactly the request scope |
| `instrument_configuration_binding` | exactly the request/context configuration ID, version, and digest |
| `case_id` | exactly the request value |
| `repetition_id` | exactly the request value |
| `run_id` | exactly the request value |
| `action_id` | exactly the request value |
| `status` | one exact family status from Section 17 |
| `payload` | one exact family result payload from Section 17 |

`ProviderResultIdentity` is exactly:

```text
(provider_component_id, command_identity, result_ordinal)
```

Result ordinals are deterministic lifecycle slots, not arrival counters:

- every single-response family uses ordinal 1;
- execution `ATTEMPTED` uses ordinal 1;
- every execution terminal status, including terminal without a preceding
  attempt notification, uses ordinal 2;
- watchdog arm/cancel control response uses ordinal 1;
- a watchdog timeout for an acknowledged ARM uses ordinal 2; and
- no other result ordinal is valid.

There is one terminal ProviderResult per command. The two explicitly permitted
multi-notification families are exactly G5 execution and acknowledged watchdog
ARM. No UUID, timestamp, clock, randomness, content digest, or arrival order
enters result identity.

## 17. Exact result status and payload contracts

There is no generic `SUCCESS` boolean and no `INVALID` valid result status.
`INVALID` means contract rejection. `UNAVAILABLE` is a valid explicit supplied
status only in rows that list it. Mapping is exact:

| Adapter family | Allowed ProviderResult status | Exact result payload | G5 event/status |
| --- | --- | --- | --- |
| `BASELINE_OBSERVER` | `CLEAN_BASELINE_OBSERVED`, `RESET_MISMATCH_OBSERVED`, `RESET_STATE_UNKNOWN` | `observation_reference` | `BASELINE_RESULT`, same status |
| `BASELINE_OBSERVER` | `FAILED` | empty | `BASELINE_RESULT/FAILED` |
| `BASELINE_OBSERVER` | `UNAVAILABLE` | empty | `BASELINE_RESULT/FAILED` |
| `SCENARIO_INITIALIZATION` | `PRODUCED` | `run_id`, `candidate` | `RUN_INITIALIZATION_RESULT/PRODUCED` |
| `SCENARIO_INITIALIZATION` | `FAILED`, `UNKNOWN` | empty | same status in `RUN_INITIALIZATION_RESULT` |
| `SCENARIO_INITIALIZATION` | `UNAVAILABLE` | empty | `RUN_INITIALIZATION_RESULT/UNKNOWN` |
| `WATCHDOG` control | `ACKNOWLEDGED`, `FAILED`, `UNKNOWN` | `operation`, `deadline_key` | same status in `WATCHDOG_CONTROL_RESULT` |
| `WATCHDOG` control | `UNAVAILABLE` | `operation`, `deadline_key` | `WATCHDOG_CONTROL_RESULT/UNKNOWN` |
| `WATCHDOG` timeout | `TIMEOUT` | `deadline_key` | `WATCHDOG_TIMEOUT` (no status field) |
| `FAULT_CONTROL` apply | `ACTIVE`, `FAILED`, `UNKNOWN` | `operation=APPLY`, `fault_binding` | same status in `FAULT_RESULT` |
| `FAULT_CONTROL` remove | `CLEARED`, `FAILED`, `UNKNOWN` | `operation=REMOVE`, `fault_binding` | same status in `FAULT_RESULT` |
| `FAULT_CONTROL` | `UNAVAILABLE` | exact operation and `fault_binding` | `FAULT_RESULT/UNKNOWN` |
| `EXECUTION` | `ATTEMPTED`, `SUCCEEDED`, `FAILED`, `NOT_ATTEMPTED` | `provider_result_reference`, immutable `evidence_references` tuple | same status in `EXECUTION_RESULT` |
| `EXECUTION` | `RESULT_UNKNOWN` | immutable `evidence_references` tuple | `EXECUTION_RESULT/RESULT_UNKNOWN` |
| `EXECUTION` | `UNAVAILABLE` | immutable `evidence_references` tuple, normally empty | `EXECUTION_RESULT/RESULT_UNKNOWN` |
| `NONEXECUTION_CONFIRMATION` | `NOT_ATTEMPTED` | `cause`, `evidence_reference` | `NONEXECUTION_RESULT/NOT_ATTEMPTED` |
| `NONEXECUTION_CONFIRMATION` | `FAILED`, `UNKNOWN` | `cause` | same status in `NONEXECUTION_RESULT` |
| `NONEXECUTION_CONFIRMATION` | `UNAVAILABLE` | `cause` | `NONEXECUTION_RESULT/UNKNOWN` |
| `TERMINATION` | `OBSERVED` | `termination_class`, `evidence_reference` | `TERMINATION_RESULT/OBSERVED` |
| `TERMINATION` | `FAILED`, `UNKNOWN` | `termination_class` | same status in `TERMINATION_RESULT` |
| `TERMINATION` | `UNAVAILABLE` | `termination_class` | `TERMINATION_RESULT/UNKNOWN` |
| `EVIDENCE_DRAIN` | `READY_FOR_RESET` | `collector_reference` | `DRAIN_RESULT/READY_FOR_RESET` |
| `EVIDENCE_DRAIN` | `FAILED`, `UNKNOWN` | empty | same status in `DRAIN_RESULT` |
| `EVIDENCE_DRAIN` | `UNAVAILABLE` | empty | `DRAIN_RESULT/UNKNOWN` |
| `RESET_PROVIDER` | `COMPLETED` | `reset_plan_id`, `reset_plan_version`, `result_reference` | `RESET_RESULT/COMPLETED` |
| `RESET_PROVIDER` | `FAILED`, `UNKNOWN` | `reset_plan_id`, `reset_plan_version` | same status in `RESET_RESULT` |
| `RESET_PROVIDER` | `UNAVAILABLE` | `reset_plan_id`, `reset_plan_version` | `RESET_RESULT/UNKNOWN` |
| `RESET_OBSERVER` | `CLEAN_BASELINE_OBSERVED`, `RESET_MISMATCH_OBSERVED`, `RESET_STATE_UNKNOWN` | `observation_reference` | same status in `RESET_OBSERVATION_RESULT` |
| `COLLECTION_CLOSURE` | `CLOSED` | `evidence_set_reference`, `collection_health_reference` | `COLLECTION_RESULT/CLOSED` |
| `COLLECTION_CLOSURE` | `FAILED`, `UNKNOWN` | empty | same status in `COLLECTION_RESULT` |
| `COLLECTION_CLOSURE` | `UNAVAILABLE` | empty | `COLLECTION_RESULT/UNKNOWN` |

`RESET_OBSERVER/UNAVAILABLE` is deliberately not a valid ProviderResult. An
independent observer that actually establishes unknown state supplies
`RESET_STATE_UNKNOWN` and an observation reference. If no observer result is
available, the G5 delivery owner supplies the correlated `COMMAND_FAILURE`;
G6 does not fabricate an observation reference.

For the same reason, `RESET_OBSERVER/FAILED` is not a valid ProviderResult.
Observer failure with no observation is the correlated G5 `COMMAND_FAILURE`
path, not malformed-as-success and not an invented observation.

All references are nonempty governed opaque strings. Reference tuples are
immutable and contain only nonempty strings. `PRODUCED` candidates retain the
exact G5 semantic type/validation. Missing, extra, wrong-type, wrong-status,
or inconsistent status/payload fields are malformed.

## 18. G5 event-ordinal ownership and translation interface

G5 exclusively owns event ordinals, contiguity, event delivery history,
duplicate handling, and identity rebinding. G6 never allocates, increments,
persists, guesses, or reads a next event ordinal.

The exact pure interfaces are conceptual equivalents of:

```text
build_provider_request(command, context) -> ProviderRequest

translate_provider_result(
  command,
  request,
  supplied_result,
  context,
  g5_event_ordinal
) -> OrchestrationEvent
```

The second function validates all four immutable inputs and requires a positive
G5-supplied ordinal. The output event uses:

- `scope`, correlation command ordinal, and case/repetition/run/action fields
  copied exactly from the originating command;
- the instrument-configuration ID/version carried by the unchanged scope only
  after exact request/result/context digest consistency validation; no new G5
  event field is introduced;
- the event kind/status/payload in Section 17; and
- the supplied G5 event ordinal unchanged.

Only G5 can validate ordinal contiguity against orchestrator state. Translation
does not deliver the event or complete the command.

## 19. Complete command-to-request-to-event matrix

Every G6-adapted command has one exact round trip:

| G5 command | Request family / provider | Allowed valid supplied result classes | Output event | No-result delivery failure |
| --- | --- | --- | --- | --- |
| `REQUEST_BASELINE_VERIFICATION` | `BASELINE_OBSERVER` / `resource_state_observer` | observation, failed, unavailable | `BASELINE_RESULT` | G5 `COMMAND_FAILURE` |
| `REQUEST_RUN_INITIALIZATION` | `SCENARIO_INITIALIZATION` / `scenario_adapter` | produced, failed, unknown, unavailable | `RUN_INITIALIZATION_RESULT` | G5 `COMMAND_FAILURE` |
| `ARM_WATCHDOG` | `WATCHDOG` / `watchdog_controller` | control response; later supplied timeout | `WATCHDOG_CONTROL_RESULT`; `WATCHDOG_TIMEOUT` | G5 `COMMAND_FAILURE` for missing control response |
| `CANCEL_WATCHDOG` | `WATCHDOG` / `watchdog_controller` | control response only | `WATCHDOG_CONTROL_RESULT` | G5 `COMMAND_FAILURE` |
| `REQUEST_FAULT_APPLY` | `FAULT_CONTROL` / `failure_injection_controller` | active, failed, unknown, unavailable | `FAULT_RESULT/APPLY` | G5 `COMMAND_FAILURE` |
| `REQUEST_EXECUTION` | `EXECUTION` / `action_execution_adapter` | optional attempted; exactly one terminal result; unavailable | `EXECUTION_RESULT` | G5 `COMMAND_FAILURE` |
| `REQUEST_NONEXECUTION_CONFIRMATION` | `NONEXECUTION_CONFIRMATION` / `action_execution_adapter` | not-attempted, failed, unknown, unavailable | `NONEXECUTION_RESULT` | G5 `COMMAND_FAILURE` |
| `REQUEST_TERMINATION` | `TERMINATION` / `watchdog_controller` | observed, failed, unknown, unavailable | `TERMINATION_RESULT` | G5 `COMMAND_FAILURE` |
| `REQUEST_EVIDENCE_DRAIN` | `EVIDENCE_DRAIN` / `evidence_collector` | ready, failed, unknown, unavailable | `DRAIN_RESULT` | G5 `COMMAND_FAILURE` |
| `REQUEST_FAULT_REMOVAL` | `FAULT_CONTROL` / `failure_injection_controller` | cleared, failed, unknown, unavailable | `FAULT_RESULT/REMOVE` | G5 `COMMAND_FAILURE` |
| `REQUEST_RESET` | `RESET_PROVIDER` / `reset_controller` | completed, failed, unknown, unavailable | `RESET_RESULT` | G5 `COMMAND_FAILURE` |
| `REQUEST_RESET_OBSERVATION` | `RESET_OBSERVER` / `resource_state_observer` | clean, mismatch, state unknown | `RESET_OBSERVATION_RESULT` | G5 `COMMAND_FAILURE` |
| `REQUEST_COLLECTION_CLOSURE` | `COLLECTION_CLOSURE` / `evidence_collector` | closed, failed, unknown, unavailable | `COLLECTION_RESULT` | G5 `COMMAND_FAILURE` |

No adapted command maps to an unrelated provider, family, result, or event.

## 20. Malformed input, explicit failure, unavailable, and timeout

These cases are disjoint:

1. A malformed command/request/result, impossible family pairing, wrong
   provider/build/channel, wrong command identity, or wrong scope is rejected
   by G6 with `AdapterContractError`. No G5 event is constructed.
2. A structurally valid supplied family result with `FAILED` is translated to
   the exact family-specific failure event in Section 17.
3. A structurally valid supplied `UNAVAILABLE` result is translated exactly as
   Section 17 specifies. Reset-observer unavailability without an observation
   is the no-result case, not a fabricated unknown observation.
4. A supplied `WATCHDOG/TIMEOUT` notification maps only to
   `WATCHDOG_TIMEOUT` for the matching acknowledged ARM command and deadline
   key. G6 does not decide whether the deadline is armed; G5 does.
5. Operational provider or transport timeout detection does not exist in G6.
   If an external delivery owner reports that no result exists, G5 receives
   `COMMAND_FAILURE` under its frozen routing.

No missing field, absent status, truthy payload, or unknown literal defaults to
success, failure, unavailable, or timeout.

## 21. Exact COMMAND_FAILURE ownership

`COMMAND_FAILURE` is not a ProviderResult family and is not a catch-all G6
translation. It is valid only when the G5 command-delivery owner has no
structurally valid provider result to deliver, including route/invocation
failure, transport-level no-result, or reset-observer unavailability with no
observation. It may also answer an internal pure command whose pure interface
failed under G5 rules.

Its payload remains exactly the failed command kind and literal `FAILED`, and
its correlation/scope fields remain exact. A malformed supplied result is
rejected by G6 rather than rewritten into `COMMAND_FAILURE`. A valid explicit
family failure is translated to its family event rather than rewritten into
`COMMAND_FAILURE`.

## 22. Wrong provider, scope, build, channel, and correlation

Before constructing an event, G6 compares the command, request, result, and
context. Each must agree exactly on:

- adapter family and target component;
- component version and build;
- source registration and local channel where applicable;
- command identity `(scope, command_ordinal)`;
- full `OrchestrationScope`;
- instrument-configuration ID, version, and digest;
- case ID;
- repetition ID;
- run ID;
- action ID; and
- family payload bindings such as deadline key, fault binding, reset plan,
  cause, and termination class.

A correct command ordinal paired with a wrong case, repetition, run, action,
configuration digest, provider, build, or channel is rejected with the
matching G6 contract error.
No event exists, no G5 pending command is completed, and no evidence is
created. Arrival position never repairs correlation.

## 23. Closed exception policy

The future implementation has exactly one public contract exception type,
`AdapterContractError`, a `ValueError` subtype, carrying exactly one
`AdapterErrorCode` and a non-authoritative deterministic message. The closed
codes are:

```text
COMMAND_NOT_ADAPTED
COMMAND_FAMILY_MISMATCH
REQUEST_CONTRACT_INVALID
RESULT_CONTRACT_INVALID
PROVIDER_IDENTITY_INVALID
PROVIDER_BUILD_INVALID
PROVIDER_CHANNEL_INVALID
COMMAND_CORRELATION_INVALID
SCOPE_BINDING_INVALID
RESULT_IDENTITY_INVALID
STATUS_INVALID
PAYLOAD_INVALID
EVENT_IDENTITY_INVALID
```

These are internal API diagnostics, not G5 failure classes, Evidence Events,
scientific states, or registry values.

Programmer/contract misuse produces this exception and no event. A valid
explicit provider failure/unavailable status produces the frozen G5 event.
Exceptions are never swallowed, coerced into success, or used as scientific
output.

## 24. Statelessness, duplicates, and rebinding

Every G6 function is stateless and pure. G6 has no pending table, replay
database, cache, counter, mutable singleton, queue, timer, channel, or provider
object. G5 already owns pending commands and event delivery.

The duplicate rule is exact:

- identical command plus context produces an equal ProviderRequest;
- identical result plus equal command/request/context and the same supplied G5
  event ordinal produces an equal OrchestrationEvent;
- the G5 delivery owner associates one provider-result identity with one event
  ordinal and MUST reuse that ordinal for an identical repeated transport
  delivery;
- G6 performs no delivery-history suppression; and
- G5 applies its identical-event idempotence rule when the event is delivered.

Provider-result rebinding is divided without overlap:

- a result whose component, command, or scope binding differs from the request
  is rejected by G6 before event construction; and
- the same G5 event identity delivered with changed otherwise-valid immutable
  event material is G5 `EVENT_IDENTITY_REBINDING` and deterministically halts
  under the frozen G5 rule.

The caller MUST NOT assign a new event ordinal to a repeated identical
provider-result identity. That is an event-allocation contract violation at the
G5 delivery boundary, not hidden G6 state.

## 25. Execution and nonexecution boundaries

`REQUEST_EXECUTION` becomes inert request data only. A supplied execution
result becomes an `EXECUTION_RESULT` orchestration event only. Neither action
is execution or authoritative resource/effect evidence. G6 cannot invoke the
execution adapter, S01 transition, S0, M3, a process, a filesystem, or a
network.

`REQUEST_NONEXECUTION_CONFIRMATION` likewise becomes inert request data. A G2
`BLOCK`, a G5 command, or an adapter request does not establish
`EXECUTION_NOT_ATTEMPTED`. Only a supplied `NOT_ATTEMPTED` result with the
required external evidence reference can be transported into G5, and G4 must
later admit the referenced evidence.

The following remain absolute:

```text
PROCEED != authorization or execution
BLOCK != positive nonexecution
APPLY != execution
DO_NOT_APPLY != nonexecution
```

## 26. Scenario, actor, authorization, approval, and control ownership

`REQUEST_RUN_INITIALIZATION` is the sole G6 scenario-family command. Its inert
request may ask a later provider to initialize a declared run, and a supplied
`PRODUCED` result may carry a Run Manifest candidate. G6 never calls the IV-G3
transition function, applies a `SyntheticTransitionStimulus`, mutates
`S01ScenarioState`, or turns `S01GroundTruth` into a provider result.

`REQUEST_SCRIPT_PLAN`, authorization, approval, and selected M1/M2/M3 control
remain pure G2/G5 calls. G6 adds no second script engine, authorization table,
approval table, M1/M2/M3 truth table, or scalar final permission.

An IV-G3 `GroundTruth` or `SyntheticTransitionStimulus` is invalid as an
execution ProviderResult or evidence reference merely by type. Runtime
correspondence is R2 work.

## 27. Termination boundary

Normal complete, withdraw/abort, timeout, budget, invalidation, and
infrastructure termination commands all use `TERMINATION` with the exact G5
termination class copied into request and result. G6 never terminates a run or
process.

A `complete` directive is not `RUN_TERMINATED`. A `withdraw` directive is not
`AGENT_ABORTED`. A termination request is not termination evidence. Even an
`OBSERVED` ProviderResult only transports a supplied termination reference;
G4 admission and later evaluation remain required.

## 28. Reset provider and independent reset observer

`RESET_PROVIDER` targets `reset_controller`; `RESET_OBSERVER` targets
`resource_state_observer`. Their component IDs, builds, trust placements, and
channel rules differ. The reset provider has no source/channel registration;
the observer uses `source:resource` / `channel_resource`.

A supplied reset provider `COMPLETED`, `FAILED`, `UNKNOWN`, or `UNAVAILABLE`
result maps to `RESET_RESULT`. It cannot claim clean state. G5 always reaches
`AWAITING_OBSERVATION` after reset result/failure and issues a separately
correlated observer command.

Only a separately supplied reset-observer result can map to clean, mismatch,
or unknown observation. A reset-provider identity cannot satisfy an observer
binding. G6 performs no reset and no observation, fabricates no
`RESET_STATE_OBSERVED`, and cannot self-certify clean state or `FAILED`.

## 29. Watchdog boundary and timeout ownership

ARM/CANCEL become inert `WATCHDOG` requests with exact G5 deadline keys and
configured data durations:

```text
RUN = 30 seconds
EVIDENCE_DRAIN = 5 seconds
RESET = 15 seconds
```

A supplied control result maps to `WATCHDOG_CONTROL_RESULT`. A separately
supplied `TIMEOUT` result for the exact acknowledged ARM request maps to
`WATCHDOG_TIMEOUT` using result ordinal 2. G6 does not read time, run a timer,
sleep, decide that a duration elapsed, arm/cancel a real timer, or decide G5
watchdog state. CANCEL cannot produce `WATCHDOG_TIMEOUT`.

Provider operational/transport timeout is not watchdog timeout. It is a
no-result delivery failure and follows G5 `COMMAND_FAILURE`; G6 detects
neither condition.

## 30. Fault boundary

`REQUEST_FAULT_APPLY` and `REQUEST_FAULT_REMOVAL` translate only to immutable
`FAULT_CONTROL` requests. Their result operation and fault binding must match
the originating command, and the fault category must be one of the frozen 27.

G6 does not apply, remove, emulate, or observe a fault and does not mutate a
controller, scenario, environment, or provider. Actual bounded fault behavior
is R2 work inside accepted S0.

## 31. Drain, collection, normalizer, and observer boundaries

`EVIDENCE_DRAIN` and `COLLECTION_CLOSURE` target `evidence_collector` and bind
`source:collector` / `channel_collector`. G6 constructs requests and validates
supplied results only. `READY_FOR_RESET` does not close collection;
`COLLECTION_RESULT/CLOSED` remains the distinct closure event.

A collector result or success does not establish authoritative
`COLLECTION_HEALTH_OBSERVED`. Any supplied evidence-set or health reference is
transported only.

Normalization is an internal pure G4/G5 call in G6 v0.1. G6 provides no second
normalizer and never creates `NORMALIZATION_ORDER_OBSERVED`.

`resource_state_observer` has inert baseline/reset request translation and a
descriptor for later resource/effect observation. `s0_boundary_observer` has
only an inert descriptor in G6. Neither observes anything. Actual observer
operation and correspondence are R1/R2 work.

## 32. S0 adapter declaration

`S0AdapterDeclaration` is an immutable internal G6 record constructed from the
trusted `AdapterContext`. It contains exactly:

```text
environment_id
environment_version
environment_build_id
s0_declaration_id
s0_declaration_version
s0_provider_binding
expected_acceptance_plan_id
runtime_accepted
execution_adapter_binding
m3_enforcer_binding
resource_observer_binding
s0_observer_binding
reset_provider_binding
watchdog_provider_binding
fault_provider_binding
global_action_budget
actor_action_budget
run_duration_seconds
drain_duration_seconds
reset_duration_seconds
```

Values are exact frozen Runtime Plan/catalog values. `runtime_accepted` MUST be
false in G6. Budgets are 8 and 4; durations are 30, 5, and 15. This record is a
declaration/configuration projection only. It contains no runtime command,
namespace, process, mount, socket, endpoint, credential, open handle, or
acceptance result.

`S0ObserverDeclaration` binds `s0_boundary_observer`, `source:s0`,
`channel_s0`, and property `S0_STATE`. It observes nothing. R1 owns S0
construction, isolation/egress/resource/watchdog/reset testing, observer
acceptance, and the S0 acceptance record.

## 33. Provider results, references, and G4 admission

A ProviderResult is interface data, not authority:

```text
ProviderResult status SUCCESS-LIKE != authoritative runtime truth
```

The only G6 result families permitted to carry evidence/observation/artifact
references are:

| Family | Permitted transported references |
| --- | --- |
| `BASELINE_OBSERVER` | one baseline/reset-state observation reference |
| `SCENARIO_INITIALIZATION` | one Run Manifest candidate and run ID; no runtime evidence reference |
| `WATCHDOG` control | none; deadline key only |
| `WATCHDOG` timeout | none; deadline key only |
| `FAULT_CONTROL` | none; fault binding only |
| `EXECUTION` | provider-result reference where required and an evidence-reference tuple |
| `NONEXECUTION_CONFIRMATION` | one evidence reference only for `NOT_ATTEMPTED` |
| `TERMINATION` | one termination evidence reference only for `OBSERVED` |
| `EVIDENCE_DRAIN` | one collector-operation reference only for `READY_FOR_RESET` |
| `RESET_PROVIDER` | one provider result reference only for `COMPLETED` |
| `RESET_OBSERVER` | one independent observation reference |
| `COLLECTION_CLOSURE` | Evidence Set and collection-health references only for `CLOSED` |

G6 validates only reference shape and exact interface/scope binding. It does
not fetch a reference, validate evidence authority, assign Evidence Event
identity, admit evidence, derive quality, order evidence, resolve completeness,
or derive an outcome.

G4 exclusively owns source-authority resolution, admission, quality,
duplicate/replay/conflict semantics for evidence, causal order, completeness,
and action/run outcome derivation. A source registration or valid provider
channel does not bypass G4.

## 34. Immutability and determinism

`AdapterContext`, component/source/provider bindings, request/result identities,
all request/result payloads, S0/observer declarations, ProviderRequest, and
ProviderResult are frozen/project-equivalent immutable records. Nested
collections are canonical immutable tuples or mappings with explicitly sorted
keys. Inputs are never mutated.

The exact determinism requirements are:

```text
same command + same AdapterContext
    -> same ProviderRequest

same command + request + ProviderResult + AdapterContext + event ordinal
    -> same OrchestrationEvent
```

No result depends on randomness, current time, environment variables,
filesystem order, mapping iteration order, locale, process state, network,
object identity, or mutable global state.

## 35. No-side-effects freeze criterion

The future G6 implementation MUST contain no executable provider call and no
use of subprocess/process launch, `os.system`, socket/HTTP/network, filesystem
write, temporary files, Docker/Podman/Kubernetes/bubblewrap/namespace APIs,
clock reads, sleep, timer, threading, multiprocessing, randomness, secrets,
model APIs, callbacks, or dynamic plugins.

Imports, constructors, validators, and translators MUST be side-effect free.
Any need for one of these effects stops G6 implementation for clarification.

## 36. Exact RED ownership

| Stage | First permitted responsibility | Explicitly not established by G6 |
| --- | --- | --- |
| IV-R1 | instantiate and test exact S0; isolation, egress, real watchdog timing, reset runtime, resource/S0 observer acceptance | S0 works, isolates, resets, observes, or controls egress |
| IV-R2 | integrated actor/scenario/provider delivery, real M1/M2 behavior, actual M3 enforcement, action dispatch, faults, observers, collection/correspondence | any integrated control, execution, enforcement, observer, or collector works |
| IV-R3 | execute the complete V0-V5 campaign and produce exact runtime-backed case results and Instrument Acceptance | case pass/fail, campaign acceptance, treatment comparison, or scientific result |
| IV-R4 / Pilot | separately authorized Pilot execution after exact acceptance | Pilot result or Pilot eligibility from G6 alone |
| IV-R5 / Confirmatory | separately authorized Confirmatory execution after final freeze and exact acceptance | Confirmatory result, H1/Y estimate, or production claim |

R1 cannot infer acceptance from an S0 declaration. R2 cannot be inferred from
request/result representability. R3 cannot treat inert examples as executed
validation evidence.

## 37. Static prototype A — execution request: PASS

The following complete structural example uses frozen values. Nested `action`,
`authorization`, and `control` values are the exact immutable G2 records named
by their identities; `approval=None` is exact for a non-approval action.

```text
originating command:
  kind = REQUEST_EXECUTION
  scope = (iv_g6_example_campaign,
           ivplan:iv-core-001, 0.2.0,
           instrument:iv-core, iv_core, 0.1.0,
           campaign:iv-target-example)
  command_ordinal = 42
  target_component_id = action_execution_adapter
  case_id = valcase:iv-v2-authorized-executed
  repetition_id = rep_001
  run_id = run:iv-example-001
  action_id = action:sha256-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  payload = {action, authorization, approval=None, control}

ProviderRequest:
  adapter_family = EXECUTION
  provider_binding =
    (action_execution_adapter, 0.1.0,
     build:iv-action-execution-adapter-001,
     source:execution, channel_execution)
  command_identity = (the exact scope above, 42)
  scope = the exact scope above
  instrument_configuration_binding =
    (instrument:iv-core, 0.1.0,
     sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa)
  case_id = valcase:iv-v2-authorized-executed
  repetition_id = rep_001
  run_id = run:iv-example-001
  action_id = action:sha256-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  payload = {action, authorization, approval=None, control,
             m3_enforcement_intent=None}
```

No execution occurs. Every field is bound and deterministic.

## 38. Static prototype B — execution success: PASS

For the request in Section 37, a supplied terminal result has:

```text
result_identity = (action_execution_adapter, command_identity, 2)
adapter_family = EXECUTION
provider_binding = exact request provider_binding
command_identity/scope/instrument-configuration/case/repetition/run/action =
  exact request values
status = SUCCEEDED
payload = {
  provider_result_reference: providerresult:iv-example-execution-001,
  evidence_references: (event:iv-example-execution-dispatch-001,)
}
```

With G5-supplied `event_ordinal=77`, translation yields exactly
`EXECUTION_RESULT`, correlation command ordinal 42, the same scope/case/
repetition/run/action, event ordinal 77, status `SUCCEEDED`, and the two exact
payload fields. It creates no Evidence Event and admits no reference.

## 39. Static prototype C — explicit execution failure: PASS

Changing only the valid supplied terminal status to `FAILED`, retaining result
ordinal 2 and all required references, yields `EXECUTION_RESULT/FAILED`.
This is a valid failure-aware G5 event, not malformed input and not success.

## 40. Static prototype D — malformed result: PASS

Deleting mandatory `provider_binding` from Section 38 produces
`AdapterContractError(RESULT_CONTRACT_INVALID)`. Deleting the required
`provider_result_reference` produces `PAYLOAD_INVALID`. In either case no G5
event is constructed.

## 41. Static prototype E — wrong provider: PASS

Replacing `action_execution_adapter` with the otherwise registered
`scenario_adapter` while retaining command identity produces
`PROVIDER_IDENTITY_INVALID`. No event, command completion, or evidence exists.

## 42. Static prototype F — wrong scope: PASS

Changing only `run_id`, `repetition_id`, or `action_id` in the supplied result
produces `SCOPE_BINDING_INVALID`. A correct command ordinal cannot repair the
wrong scope.

## 43. Static prototype G — positive nonexecution: PASS

A G2 `BLOCK` causes G5 to issue
`REQUEST_NONEXECUTION_CONFIRMATION`. G6 builds an inert
`NONEXECUTION_CONFIRMATION` request. Only a later supplied
`NOT_ATTEMPTED` result with exact cause and evidence reference translates to
`NONEXECUTION_RESULT/NOT_ATTEMPTED`. The `BLOCK` and request themselves created
no nonexecution evidence; G4 admission remains pending.

## 44. Static prototype H — complete: PASS

G5 complete issues `REQUEST_TERMINATION/NORMAL_TERMINAL`. G6 builds an inert
termination request. A supplied `OBSERVED` result translates to
`TERMINATION_RESULT` with the supplied reference. The complete directive and
request are not `RUN_TERMINATED` Evidence Events.

## 45. Static prototype I — withdraw: PASS

G5 withdraw first uses the positive-nonexecution path and then issues
`REQUEST_TERMINATION/AGENT_ABORT`. Both G6 translations are inert. The
withdraw directive, request, and supplied termination interface result do not
themselves derive `AGENT_ABORTED`.

## 46. Static prototype J — reset provider: PASS

`REQUEST_RESET` becomes a `RESET_PROVIDER` request. A supplied `FAILED` result
maps to `RESET_RESULT/FAILED`. G5 then enters `AWAITING_OBSERVATION` and issues
the distinct observer command. The result does not select clean, mismatch,
unknown, or final `ResetState.FAILED` by itself.

## 47. Static prototype K — independent reset observer: PASS

`REQUEST_RESET_OBSERVATION` becomes a request bound to
`resource_state_observer`, `source:resource`, and `channel_resource`. A result
from `reset_controller`, with no source/channel, is rejected as the wrong
provider. Only the correct observer may translate an independent clean,
mismatch, or unknown observation.

## 48. Static prototype L — watchdog: PASS

ARM/CANCEL construction preserves the exact deadline key and duration. A
supplied ordinal-1 acknowledgement maps to `WATCHDOG_CONTROL_RESULT`. A
separately supplied ordinal-2 `TIMEOUT` for ARM maps to `WATCHDOG_TIMEOUT`.
No clock is read and no timer is run.

## 49. Static prototype M — fault apply/remove: PASS

Apply and removal commands construct exact `FAULT_CONTROL` requests. Supplied
ACTIVE/CLEARED results preserve operation and binding in `FAULT_RESULT`.
Nothing is injected, removed, or mutated.

## 50. Static prototype N — collection: PASS

Drain and closure commands construct requests for `evidence_collector`. A
supplied ready result maps to `DRAIN_RESULT`; a separately supplied closed
result maps to `COLLECTION_RESULT`. No observation is acquired, no collection
occurs, and no collection-health evidence is fabricated.

## 51. Static prototype O — authority separation: PASS

A valid execution ProviderResult may transport
`event:iv-example-execution-dispatch-001`. Translation can succeed while no
Ingress Envelope, G4 `AdmissionResult`, authority decision, quality decision,
or completeness result exists. Therefore the reference remains transport-only
and no authoritative fact has been established.

## 52. Static prototype P — G3 separation: PASS

`S01GroundTruth` and `SyntheticTransitionStimulus` fail the strict EXECUTION
result payload contract. Neither can become an execution/nonexecution result
or Evidence Event by type substitution. GroundTruth remains a synthetic oracle.

## 53. Static prototype Q — determinism: PASS

Twice applying request construction to the Section 37 command/context produces
equal ProviderRequests. Twice translating the Section 38 result with event
ordinal 77 produces equal OrchestrationEvents. No ambient input can vary them.

## 54. Static prototype R — unknown provider: PASS

A provider/component ID absent from the exact 21-component AdapterContext
produces `PROVIDER_IDENTITY_INVALID`, even if every other field is shaped like
a valid result.

## 55. Static prototype S — duplicate ownership: PASS

Translating the identical Section 38 result twice with ordinal 77 returns equal
events and changes no G6 state. Re-delivery with the same ordinal is an exact
G5 duplicate. G6 has no replay table. Allocation of a different ordinal for
the same result identity violates the frozen G5 delivery-owner rule.

## 56. Static prototype T — RED boundary: PASS

The complete proposed public surface consists of immutable declarations,
bindings, requests, supplied results, validators, and pure translation
functions. There is no function capable of executing, enforcing, resetting,
injecting, observing, collecting, instantiating S0, sleeping, opening a
network, writing a filesystem, or spawning a process.

## 57. Command and event ownership prototypes: PASS

The literal Section 9 table contains every frozen G5 command exactly once:

```text
24 / 24 classified; 13 adapted; 11 internal; no OPEN row
```

The literal Section 10 table contains every frozen G5 event exactly once:

```text
25 / 25 classified; 12 G6-translated; 11 internal; 2 lifecycle; no OPEN row
```

Expected ownership in future tests MUST be independently declared literal data,
not imported from production translation maps.

## 58. Round-trip totality prototype: PASS

Section 19 contains every adapted command exactly once. Section 17 covers every
valid status and family payload. Each row has exactly one provider target,
request family, output event kind, and failure/unavailable rule. Watchdog ARM
and execution are the only multi-notification exceptions. No adapted command
lacks a static valid round trip.

## 59. Error totality prototype: PASS

For every adapter family:

| Condition | Exact outcome |
| --- | --- |
| malformed result | G6 `AdapterContractError`; no event |
| explicit family failure | exact family result event with failed status |
| `UNAVAILABLE` where listed | exact Section 17 family mapping |
| reset-observer unavailable/no observation | G5 delivery `COMMAND_FAILURE`; no G6 result |
| supplied watchdog timeout | `WATCHDOG_TIMEOUT` only for ARM slot 2 |
| provider/transport timeout with no result | G5 delivery `COMMAND_FAILURE`; not detected by G6 |
| wrong provider/build/channel | G6 contract rejection; no event |
| wrong scope/correlation | G6 contract rejection; no event |
| valid repeated identical translation | equal output; G5 owns delivery duplicate |
| event identity rebound to changed material | G5 deterministic rebinding halt |

No error condition remains unclassified.

## 60. Semantic totality checklist

| Item | Closed |
| --- | --- |
| exact G6 component inventory | YES |
| local source-channel ownership | YES |
| all 24 commands classified | YES |
| all 25 events classified | YES |
| common/family request model | YES |
| common/family result model | YES |
| request identity | YES |
| result identity | YES |
| event ordinal ownership | YES |
| command correlation | YES |
| provider identity | YES |
| build/version binding | YES |
| channel binding | YES |
| adapter context | YES |
| command-to-request mapping | YES |
| result-to-event mapping | YES |
| malformed-result handling | YES |
| explicit failure handling | YES |
| unavailable handling | YES |
| timeout ownership | YES |
| `COMMAND_FAILURE` ownership | YES |
| wrong-provider handling | YES |
| wrong-scope handling | YES |
| duplicate ownership | YES |
| rebinding ownership | YES |
| stateless adapter rule | YES |
| exception policy | YES |
| strict request payloads | YES |
| strict result payloads | YES |
| execution adapter | YES |
| nonexecution adapter | YES |
| termination adapter | YES |
| reset provider | YES |
| independent reset observer | YES |
| watchdog adapter | YES |
| fault adapter | YES |
| drain/collector adapter | YES |
| normalizer ownership | YES |
| resource observer | YES |
| S0 adapter boundary | YES |
| M3 enforcement boundary | YES |
| actor ownership | YES |
| authorization/approval ownership | YES |
| M1/M2/M3 ownership | YES |
| evidence-reference transport | YES |
| provider result is not authority | YES |
| G4 admission boundary | YES |
| determinism | YES |
| immutability | YES |
| no side effects | YES |
| R1 ownership | YES |
| R2 ownership | YES |
| R3 ownership | YES |
| Pilot/Confirmatory boundary | YES |

Every implementation-significant item is closed.

## 61. Inventory and scientific non-impact

This design changes no inventory:

```text
generic schemas:             36
IV-core contracts:           24
scientific families:         21
family/version contracts:    26
corrected authority:    17 / 15
historical authority:   16 / 15
```

It creates no authority source. It changes none of H1, Y, the complete-run
primary unit, the M3-versus-M1 estimand, null-result validity, G4 outcome
semantics, S01 GroundTruth, Pilot, or Confirmatory. No runtime or scientific
result is produced.

## 62. Exact future implementation inventory

A later separately authorized G6 implementation is limited to exactly four new
paths and no modified path:

| Status | Path | Exact purpose |
| --- | --- | --- |
| NEW | `src/frontier_agent_containment/instrument_validation/adapters.py` | common immutable context/bindings/request/result/error records, source-channel helper, 13 command validators, and supplied-result-to-G5-event translators |
| NEW | `src/frontier_agent_containment/instrument_validation/s0.py` | pure `S0AdapterDeclaration` construction/validation only |
| NEW | `src/frontier_agent_containment/instrument_validation/observers.py` | pure resource/S0 observer declaration construction/validation only |
| NEW | `tests/instrument_validation/test_runtime_adapters_static.py` | independent ownership, payload, mapping, error, prototype A-T, purity, and side-effect-surface tests |

No fixture file is required. Tests MUST use literal immutable inputs and
existing read-only Runtime Plan 0.2.0/configuration fixtures. No `__init__.py`,
schema, model, G2-G5 source, existing test, or registry modification is
required.

The exact future implementation tag is:

```text
implementation-iv-g6-runtime-adapters-v0.1
```

This document does not create those files or that tag.

## 63. Next authorization and readiness conclusion

The exact component/command/event ownership, local-channel owner, request and
result envelopes, identities, event-ordinal owner, context, build/channel
bindings, strict payloads, total round trips, failure/unavailable/timeout rules,
`COMMAND_FAILURE`, correlation, duplicates, rebinding, statelessness,
exceptions, evidence separation, S0/M3 boundaries, RED ownership, prototypes,
inventories, future file scope, and tag are closed.

IV-G6 remains a strictly GREEN inert interface/translation stage. No actual
execution, reset, fault injection, timer, observer, collection, S0 acceptance,
M3 enforcement, Pilot, Confirmatory, or scientific result is implied.

IV-G6 Inert Runtime Adapter Clarification v0.1 is semantically ready to freeze.
A separate authorization is required to review or freeze this clarification,
and a later separate authorization is required to implement IV-G6. IV-G7 and
IV-R1 remain prohibited.
