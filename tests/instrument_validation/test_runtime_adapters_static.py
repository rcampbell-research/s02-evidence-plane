"""Independent behavioral tests for the pure IV-G6 inert adapter boundary."""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, replace
from enum import Enum
from pathlib import Path
from types import MappingProxyType

import pytest

from frontier_agent_containment.instrument_validation import adapters
from frontier_agent_containment.instrument_validation.actor_control_decisions import (
    ActionClass,
    ApprovalDecision,
    ApprovalResult,
    AuthorizationDecision,
    AuthorizationResult,
    ControlDecision,
    ControlLayer,
    ControlResult,
    RequestedAction,
    ScriptOperation,
)
from frontier_agent_containment.instrument_validation.adapters import (
    COMMAND_OWNERSHIP,
    COMPONENT_OWNERSHIP,
    EVENT_OWNERSHIP,
    AdapterContext,
    AdapterContractError,
    AdapterErrorCode,
    AdapterFamily,
    CommandOwnership,
    ComponentOwnership,
    EventOwnership,
    InstrumentConfigurationBinding,
    M3EnforcementIntent,
    ProviderBinding,
    ProviderRequest,
    ProviderResult,
    ProviderResultIdentity,
    ProviderResultStatus,
    adapter_context_from_validated_runtime_plan,
    build_provider_request,
    translate_provider_result,
)
from frontier_agent_containment.instrument_validation.observers import (
    ResourceObserverDeclaration,
    S0ObserverDeclaration,
    build_resource_observer_declaration,
    build_s0_observer_declaration,
)
from frontier_agent_containment.instrument_validation.orchestration import (
    CommandKind,
    DeadlineKind,
    EventKind,
    ExecutionMode,
    FrozenPayload,
    NonexecutionCause,
    OrchestrationCommand,
    OrchestrationEvent,
    OrchestrationScope,
    ScheduledValidationRepetition,
    TerminationCause,
    WatchdogDeadlineKey,
    frozen_payload,
)
from frontier_agent_containment.instrument_validation.s0 import (
    S0AdapterDeclaration,
    build_s0_adapter_declaration,
)
from frontier_agent_containment.instrument_validation.synthetic_scenario import (
    S01GroundTruth,
    SyntheticTransitionStimulus,
)


EXPECTED_COMPONENT_OWNERSHIP = {
    "validation_orchestrator": "NON_G6",
    "scripted_validation_actor": "NON_G6",
    "scenario_adapter": "G6_INERT_SURFACE",
    "authorization_service": "NON_G6",
    "approval_emulator": "NON_G6",
    "m1_policy_context_adapter": "NON_G6",
    "m2_policy_mediator": "NON_G6",
    "m3_external_enforcer": "G6_INERT_SURFACE",
    "action_execution_adapter": "G6_INERT_SURFACE",
    "s0_environment_boundary": "G6_INERT_SURFACE",
    "resource_state_observer": "G6_INERT_SURFACE",
    "s0_boundary_observer": "G6_INERT_SURFACE",
    "evidence_collector": "G6_INERT_SURFACE",
    "evidence_normalizer_store": "NON_G6",
    "action_outcome_evaluator": "NON_G6",
    "run_outcome_aggregator": "NON_G6",
    "validation_case_evaluator": "NON_G6",
    "instrument_acceptance_producer": "NON_G6",
    "reset_controller": "G6_INERT_SURFACE",
    "watchdog_controller": "G6_INERT_SURFACE",
    "failure_injection_controller": "G6_INERT_SURFACE",
}

EXPECTED_COMMAND_OWNERSHIP = {
    "REQUEST_BASELINE_VERIFICATION": "G6_ADAPTED",
    "REQUEST_RUN_INITIALIZATION": "G6_ADAPTED",
    "ARM_WATCHDOG": "G6_ADAPTED",
    "CANCEL_WATCHDOG": "G6_ADAPTED",
    "REQUEST_FAULT_APPLY": "G6_ADAPTED",
    "REQUEST_SCRIPT_PLAN": "INTERNAL_PURE",
    "REQUEST_BUDGET_PROBE": "INTERNAL_PURE",
    "REQUEST_AUTHORIZATION": "INTERNAL_PURE",
    "REQUEST_APPROVAL": "INTERNAL_PURE",
    "REQUEST_CONTROL_DECISION": "INTERNAL_PURE",
    "REQUEST_EXECUTION": "G6_ADAPTED",
    "REQUEST_NONEXECUTION_CONFIRMATION": "G6_ADAPTED",
    "REQUEST_TERMINATION": "G6_ADAPTED",
    "REQUEST_EVIDENCE_DRAIN": "G6_ADAPTED",
    "REQUEST_FAULT_REMOVAL": "G6_ADAPTED",
    "REQUEST_RESET": "G6_ADAPTED",
    "REQUEST_RESET_OBSERVATION": "G6_ADAPTED",
    "REQUEST_COLLECTION_CLOSURE": "G6_ADAPTED",
    "REQUEST_NORMALIZATION": "INTERNAL_PURE",
    "REQUEST_ACTION_EVALUATION": "INTERNAL_PURE",
    "REQUEST_RUN_AGGREGATION": "INTERNAL_PURE",
    "REQUEST_REPETITION_EVALUATION": "INTERNAL_PURE",
    "REQUEST_CASE_EVALUATION": "INTERNAL_PURE",
    "REQUEST_INSTRUMENT_ACCEPTANCE": "INTERNAL_PURE",
}

EXPECTED_EVENT_OWNERSHIP = {
    "START": "G5_LIFECYCLE_DELIVERY",
    "BASELINE_RESULT": "G6_TRANSLATED_PROVIDER_RESULT",
    "RUN_INITIALIZATION_RESULT": "G6_TRANSLATED_PROVIDER_RESULT",
    "FAULT_RESULT": "G6_TRANSLATED_PROVIDER_RESULT",
    "SCRIPT_PLAN_RESULT": "INTERNAL_PURE",
    "BUDGET_PROBE_RESULT": "INTERNAL_PURE",
    "AUTHORIZATION_RESULT": "INTERNAL_PURE",
    "APPROVAL_RESULT": "INTERNAL_PURE",
    "CONTROL_RESULT": "INTERNAL_PURE",
    "EXECUTION_RESULT": "G6_TRANSLATED_PROVIDER_RESULT",
    "NONEXECUTION_RESULT": "G6_TRANSLATED_PROVIDER_RESULT",
    "TERMINATION_RESULT": "G6_TRANSLATED_PROVIDER_RESULT",
    "DRAIN_RESULT": "G6_TRANSLATED_PROVIDER_RESULT",
    "RESET_RESULT": "G6_TRANSLATED_PROVIDER_RESULT",
    "RESET_OBSERVATION_RESULT": "G6_TRANSLATED_PROVIDER_RESULT",
    "COLLECTION_RESULT": "G6_TRANSLATED_PROVIDER_RESULT",
    "NORMALIZATION_RESULT": "INTERNAL_PURE",
    "ACTION_EVALUATION_RESULT": "INTERNAL_PURE",
    "RUN_AGGREGATION_RESULT": "INTERNAL_PURE",
    "REPETITION_EVALUATION_RESULT": "INTERNAL_PURE",
    "CASE_EVALUATION_RESULT": "INTERNAL_PURE",
    "ACCEPTANCE_RESULT": "INTERNAL_PURE",
    "WATCHDOG_CONTROL_RESULT": "G6_TRANSLATED_PROVIDER_RESULT",
    "WATCHDOG_TIMEOUT": "G6_TRANSLATED_PROVIDER_RESULT",
    "COMMAND_FAILURE": "G5_LIFECYCLE_DELIVERY",
}

EXPECTED_ROUND_TRIPS = {
    "REQUEST_BASELINE_VERIFICATION": ("BASELINE_OBSERVER", "resource_state_observer", "BASELINE_RESULT"),
    "REQUEST_RUN_INITIALIZATION": ("SCENARIO_INITIALIZATION", "scenario_adapter", "RUN_INITIALIZATION_RESULT"),
    "ARM_WATCHDOG": ("WATCHDOG", "watchdog_controller", "WATCHDOG_CONTROL_RESULT"),
    "CANCEL_WATCHDOG": ("WATCHDOG", "watchdog_controller", "WATCHDOG_CONTROL_RESULT"),
    "REQUEST_FAULT_APPLY": ("FAULT_CONTROL", "failure_injection_controller", "FAULT_RESULT"),
    "REQUEST_EXECUTION": ("EXECUTION", "action_execution_adapter", "EXECUTION_RESULT"),
    "REQUEST_NONEXECUTION_CONFIRMATION": ("NONEXECUTION_CONFIRMATION", "action_execution_adapter", "NONEXECUTION_RESULT"),
    "REQUEST_TERMINATION": ("TERMINATION", "watchdog_controller", "TERMINATION_RESULT"),
    "REQUEST_EVIDENCE_DRAIN": ("EVIDENCE_DRAIN", "evidence_collector", "DRAIN_RESULT"),
    "REQUEST_FAULT_REMOVAL": ("FAULT_CONTROL", "failure_injection_controller", "FAULT_RESULT"),
    "REQUEST_RESET": ("RESET_PROVIDER", "reset_controller", "RESET_RESULT"),
    "REQUEST_RESET_OBSERVATION": ("RESET_OBSERVER", "resource_state_observer", "RESET_OBSERVATION_RESULT"),
    "REQUEST_COLLECTION_CLOSURE": ("COLLECTION_CLOSURE", "evidence_collector", "COLLECTION_RESULT"),
}

ADAPTED_KINDS = tuple(CommandKind[name] for name in EXPECTED_ROUND_TRIPS)
INTERNAL_KINDS = tuple(
    CommandKind[name]
    for name, ownership in EXPECTED_COMMAND_OWNERSHIP.items()
    if ownership == "INTERNAL_PURE"
)


def _scope() -> OrchestrationScope:
    return OrchestrationScope(
        "iv_g6_campaign_001",
        "ivplan:iv-core-001",
        "0.2.0",
        "instrument:iv-core",
        "iv_core",
        "0.1.0",
        "campaign:iv-validation",
    )


@pytest.fixture(scope="module")
def runtime_plan() -> dict[str, object]:
    path = Path(__file__).parents[2] / "tests/fixtures/instrument_validation/v0.2/configuration/runtime-plan.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def context(runtime_plan: dict[str, object]) -> AdapterContext:
    return adapter_context_from_validated_runtime_plan(_scope(), runtime_plan)


def _action() -> RequestedAction:
    return RequestedAction(
        "action:sha256-" + "a" * 64,
        "agentcond:scripted-validation-actor",
        "script:iv-core-sequence",
        "0.1.0",
        1,
        ScriptOperation.READ_PROTECTED,
        ActionClass.READ,
        "resource:protected-store",
        "instrument:iv-core",
        "scenario:iv-s01-protected-record",
    )


def _authorization(action: RequestedAction) -> AuthorizationDecision:
    return AuthorizationDecision(
        "authorization:iv-g6-001",
        action.action_id,
        "policy:iv-core-authorization",
        "0.1.0",
        "envelope:iv-core",
        "0.1.0",
        "authorization_service",
        "instrument:iv-core",
        "sha256:" + "b" * 64,
        "sha256:" + "c" * 64,
        AuthorizationResult.ALLOWED,
        (),
    )


def _approval(action: RequestedAction, authorization: AuthorizationDecision) -> ApprovalDecision:
    return ApprovalDecision(
        "approval:iv-g6-001",
        action.action_id,
        authorization.authorization_decision_id,
        "approvalpolicy:iv-core-deterministic",
        "0.1.0",
        "approval_emulator",
        "instrument:iv-core",
        1,
        "sha256:" + "d" * 64,
        ApprovalResult.APPROVED,
    )


def _control(
    action: RequestedAction,
    authorization: AuthorizationDecision,
    *,
    layer: ControlLayer = ControlLayer.M1,
    approval: ApprovalDecision | None = None,
    result: ControlResult = ControlResult.PROCEED,
) -> ControlDecision:
    component = {
        ControlLayer.M1: "m1_policy_context_adapter",
        ControlLayer.M2: "m2_policy_mediator",
        ControlLayer.M3: "m3_external_enforcer",
    }[layer]
    return ControlDecision(
        "controldecision:iv-g6-001",
        action.action_id,
        authorization.authorization_decision_id,
        approval.approval_decision_id if approval else None,
        layer,
        f"ctrlcond:iv-core-{layer.value.lower()}",
        f"control:iv-core-{layer.value.lower()}",
        f"cond:iv-core-{layer.value.lower()}",
        component,
        "instrument:iv-core",
        "sha256:" + "e" * 64,
        result,
    )


def _repetition() -> ScheduledValidationRepetition:
    scheduled = tuple(
        sorted(
            {
                "scheduled_run_id": "scheduledrun:iv-g6-001",
                "scenario_id": "scenario:iv-s01-protected-record",
                "environment_id": "env:iv-synthetic-lab",
                "instrument_configuration_id": "instrument:iv-core",
                "capability_envelope_id": "envelope:iv-core",
                "policy_id": "policy:iv-core-authorization",
                "control_condition_id": "ctrlcond:iv-core-m1",
            }.items()
        )
    )
    return ScheduledValidationRepetition(
        "valcase:iv-v2-authorized-executed",
        "0.2.0",
        "V2",
        "rep_001",
        1,
        1,
        ExecutionMode.RUNTIME_REPETITION,
        scheduled,
        "script:iv-core-sequence@0.1.0",
    )


def _payload_for_command(kind: CommandKind, scope: OrchestrationScope, ordinal: int) -> FrozenPayload:
    action = _action()
    authorization = _authorization(action)
    control = _control(action, authorization)
    repetition = _repetition()
    scheduled = repetition.scheduled_run
    case = tuple(
        sorted(
            {
                "validation_case_id": repetition.validation_case_id,
                "validation_case_version": repetition.validation_case_version,
                "validation_phase": repetition.validation_phase,
            }.items()
        )
    )
    run_key = WatchdogDeadlineKey(DeadlineKind.RUN, scope, ordinal)
    drain_key = WatchdogDeadlineKey(DeadlineKind.EVIDENCE_DRAIN, scope, ordinal)
    if kind is CommandKind.REQUEST_BASELINE_VERIFICATION:
        return frozen_payload(
            reset_plan_id="resetplan:iv-core",
            reset_plan_version="0.1.0",
            clean_state_condition="cond:iv-core-clean-state",
            baseline_identity="cond:iv-core-clean-state",
        )
    if kind is CommandKind.REQUEST_RUN_INITIALIZATION:
        return frozen_payload(
            scheduled_run=scheduled,
            validation_case=case,
            repetition=repetition,
            selected_treatment="ctrlcond:iv-core-m1",
            configuration_references=(
                "instrument:iv-core",
                "scenario:iv-s01-protected-record",
                "env:iv-synthetic-lab",
                "envelope:iv-core",
                "policy:iv-core-authorization",
                "ctrlcond:iv-core-m1",
            ),
        )
    if kind is CommandKind.ARM_WATCHDOG:
        return frozen_payload(deadline_key=run_key, duration_seconds=30)
    if kind is CommandKind.CANCEL_WATCHDOG:
        return frozen_payload(deadline_key=run_key)
    if kind is CommandKind.REQUEST_FAULT_APPLY:
        return frozen_payload(
            fault_binding="observer_missing",
            fault_fixture_reference="faultfixture:observer-missing",
        )
    if kind is CommandKind.REQUEST_EXECUTION:
        return frozen_payload(action=action, authorization=authorization, approval=None, control=control)
    if kind is CommandKind.REQUEST_NONEXECUTION_CONFIRMATION:
        return frozen_payload(
            action=action,
            authorization=authorization,
            approval=None,
            control=replace(control, result=ControlResult.BLOCK),
            cause=NonexecutionCause.CONTROL_BLOCKED,
        )
    if kind is CommandKind.REQUEST_TERMINATION:
        return frozen_payload(cause=TerminationCause.NORMAL_TERMINAL, causal_references=())
    if kind is CommandKind.REQUEST_EVIDENCE_DRAIN:
        return frozen_payload(
            run_reference="run:iv-g6-001",
            repetition_reference="rep_001",
            collector_reference="evidence_collector",
            reset_plan_reference=("resetplan:iv-core", "0.1.0", "cond:iv-core-clean-state"),
            drain_deadline_key=drain_key,
        )
    if kind is CommandKind.REQUEST_FAULT_REMOVAL:
        return frozen_payload(
            fault_binding="observer_missing",
            apply_result_reference=frozen_payload(
                operation="APPLY", status="ACTIVE", fault_binding="observer_missing"
            ),
        )
    if kind is CommandKind.REQUEST_RESET:
        return frozen_payload(
            reset_plan_id="resetplan:iv-core",
            reset_plan_version="0.1.0",
            baseline_identity="cond:iv-core-clean-state",
            clean_state_condition="cond:iv-core-clean-state",
        )
    if kind is CommandKind.REQUEST_RESET_OBSERVATION:
        return frozen_payload(
            reset_plan_id="resetplan:iv-core",
            reset_result_reference="providerresult:reset-001",
            baseline_identity="cond:iv-core-clean-state",
            observer_reference="resource_state_observer",
        )
    if kind is CommandKind.REQUEST_COLLECTION_CLOSURE:
        return frozen_payload(
            run_reference="run:iv-g6-001",
            repetition_reference="rep_001",
            evidence_set_identity=("iv_g6_campaign_001", "run:iv-g6-001"),
            reset_observation_references=("event:reset-observation-001",),
        )
    raise AssertionError(f"no adapted test payload for {kind.value}")


def _command(kind: CommandKind) -> OrchestrationCommand:
    scope = _scope()
    ordinal = ADAPTED_KINDS.index(kind) + 1
    family, target, _ = EXPECTED_ROUND_TRIPS[kind.value]
    del family
    runless = {
        CommandKind.REQUEST_BASELINE_VERIFICATION,
        CommandKind.REQUEST_RUN_INITIALIZATION,
    }
    action_kind = {
        CommandKind.REQUEST_EXECUTION,
        CommandKind.REQUEST_NONEXECUTION_CONFIRMATION,
    }
    return OrchestrationCommand(
        kind=kind,
        scope=scope,
        command_ordinal=ordinal,
        target_component_id=target,
        case_id="valcase:iv-v2-authorized-executed",
        repetition_id="rep_001",
        run_id=None if kind in runless else "run:iv-g6-001",
        action_id=_action().action_id if kind in action_kind else None,
        payload=_payload_for_command(kind, scope, ordinal),
    )


@pytest.fixture(scope="module")
def commands() -> MappingProxyType:
    return MappingProxyType({kind: _command(kind) for kind in ADAPTED_KINDS})


def _result_payload(
    kind: CommandKind,
    status: ProviderResultStatus,
    request: ProviderRequest,
) -> FrozenPayload:
    if request.adapter_family in {AdapterFamily.BASELINE_OBSERVER, AdapterFamily.RESET_OBSERVER}:
        if status in {
            ProviderResultStatus.CLEAN_BASELINE_OBSERVED,
            ProviderResultStatus.RESET_MISMATCH_OBSERVED,
            ProviderResultStatus.RESET_STATE_UNKNOWN,
        }:
            return frozen_payload(observation_reference="event:reset-observation-001")
        return frozen_payload()
    if request.adapter_family is AdapterFamily.SCENARIO_INITIALIZATION:
        if status is ProviderResultStatus.PRODUCED:
            candidate = {
                "run_id": "run:iv-g6-produced-001",
                "run_manifest_version": "0.1.0",
                "configuration_frozen_before_start": True,
            }
            return frozen_payload(run_id="run:iv-g6-produced-001", candidate=candidate)
        return frozen_payload()
    if request.adapter_family is AdapterFamily.WATCHDOG:
        if status is ProviderResultStatus.TIMEOUT:
            return frozen_payload(deadline_key=request.payload.get("deadline_key"))
        operation = "ARM" if kind is CommandKind.ARM_WATCHDOG else "CANCEL"
        return frozen_payload(operation=operation, deadline_key=request.payload.get("deadline_key"))
    if request.adapter_family is AdapterFamily.FAULT_CONTROL:
        operation = "APPLY" if kind is CommandKind.REQUEST_FAULT_APPLY else "REMOVE"
        return frozen_payload(operation=operation, fault_binding=request.payload.get("fault_binding"))
    if request.adapter_family is AdapterFamily.EXECUTION:
        if status in {ProviderResultStatus.RESULT_UNKNOWN, ProviderResultStatus.UNAVAILABLE}:
            return frozen_payload(evidence_references=())
        return frozen_payload(
            provider_result_reference="providerresult:execution-001",
            evidence_references=("event:execution-dispatch-001",),
        )
    if request.adapter_family is AdapterFamily.NONEXECUTION_CONFIRMATION:
        cause = request.payload.get("cause").value
        if status is ProviderResultStatus.NOT_ATTEMPTED:
            return frozen_payload(cause=cause, evidence_reference="event:nonexecution-001")
        return frozen_payload(cause=cause)
    if request.adapter_family is AdapterFamily.TERMINATION:
        termination_class = request.payload.get("cause").value
        if status is ProviderResultStatus.OBSERVED:
            return frozen_payload(
                termination_class=termination_class,
                evidence_reference="event:termination-001",
            )
        return frozen_payload(termination_class=termination_class)
    if request.adapter_family is AdapterFamily.EVIDENCE_DRAIN:
        if status is ProviderResultStatus.READY_FOR_RESET:
            return frozen_payload(collector_reference="providerresult:drain-001")
        return frozen_payload()
    if request.adapter_family is AdapterFamily.RESET_PROVIDER:
        base = {"reset_plan_id": "resetplan:iv-core", "reset_plan_version": "0.1.0"}
        if status is ProviderResultStatus.COMPLETED:
            base["result_reference"] = "providerresult:reset-001"
        return frozen_payload(**base)
    if request.adapter_family is AdapterFamily.COLLECTION_CLOSURE:
        if status is ProviderResultStatus.CLOSED:
            return frozen_payload(
                evidence_set_reference="evidenceset:iv-g6-001",
                collection_health_reference="event:collection-health-001",
            )
        return frozen_payload()
    raise AssertionError("unhandled result family")


SUCCESS_STATUS = {
    CommandKind.REQUEST_BASELINE_VERIFICATION: ProviderResultStatus.CLEAN_BASELINE_OBSERVED,
    CommandKind.REQUEST_RUN_INITIALIZATION: ProviderResultStatus.PRODUCED,
    CommandKind.ARM_WATCHDOG: ProviderResultStatus.ACKNOWLEDGED,
    CommandKind.CANCEL_WATCHDOG: ProviderResultStatus.ACKNOWLEDGED,
    CommandKind.REQUEST_FAULT_APPLY: ProviderResultStatus.ACTIVE,
    CommandKind.REQUEST_EXECUTION: ProviderResultStatus.SUCCEEDED,
    CommandKind.REQUEST_NONEXECUTION_CONFIRMATION: ProviderResultStatus.NOT_ATTEMPTED,
    CommandKind.REQUEST_TERMINATION: ProviderResultStatus.OBSERVED,
    CommandKind.REQUEST_EVIDENCE_DRAIN: ProviderResultStatus.READY_FOR_RESET,
    CommandKind.REQUEST_FAULT_REMOVAL: ProviderResultStatus.CLEARED,
    CommandKind.REQUEST_RESET: ProviderResultStatus.COMPLETED,
    CommandKind.REQUEST_RESET_OBSERVATION: ProviderResultStatus.CLEAN_BASELINE_OBSERVED,
    CommandKind.REQUEST_COLLECTION_CLOSURE: ProviderResultStatus.CLOSED,
}


def _result(
    kind: CommandKind,
    request: ProviderRequest,
    status: ProviderResultStatus | None = None,
) -> ProviderResult:
    status = status or SUCCESS_STATUS[kind]
    ordinal = 2 if request.adapter_family is AdapterFamily.EXECUTION and status is not ProviderResultStatus.ATTEMPTED else 2 if request.adapter_family is AdapterFamily.WATCHDOG and status is ProviderResultStatus.TIMEOUT else 1
    return ProviderResult(
        result_identity=ProviderResultIdentity(
            request.provider_binding.component_id,
            request.command_identity,
            ordinal,
        ),
        adapter_family=request.adapter_family,
        provider_binding=request.provider_binding,
        command_identity=request.command_identity,
        scope=request.scope,
        instrument_configuration_binding=request.instrument_configuration_binding,
        case_id=request.case_id,
        repetition_id=request.repetition_id,
        run_id=request.run_id,
        action_id=request.action_id,
        status=status,
        payload=_result_payload(kind, status, request),
    )


def _event(kind: CommandKind, context: AdapterContext, *, status: ProviderResultStatus | None = None) -> OrchestrationEvent:
    command = _command(kind)
    request = build_provider_request(command, context)
    return translate_provider_result(command, request, _result(kind, request, status), context, 77)


def test_component_ownership_oracle_is_exact_and_independent() -> None:
    actual = {key: value.value for key, value in COMPONENT_OWNERSHIP.items()}
    assert actual == EXPECTED_COMPONENT_OWNERSHIP
    assert len(actual) == 21
    assert sum(value == "G6_INERT_SURFACE" for value in actual.values()) == 10
    assert sum(value == "NON_G6" for value in actual.values()) == 11


def test_command_ownership_oracle_is_exact_and_independent() -> None:
    actual = {key.value: value.value for key, value in COMMAND_OWNERSHIP.items()}
    assert actual == EXPECTED_COMMAND_OWNERSHIP
    assert len(actual) == 24
    assert sum(value == "G6_ADAPTED" for value in actual.values()) == 13
    assert sum(value == "INTERNAL_PURE" for value in actual.values()) == 11


def test_event_ownership_oracle_is_exact_and_independent() -> None:
    actual = {key.value: value.value for key, value in EVENT_OWNERSHIP.items()}
    assert actual == EXPECTED_EVENT_OWNERSHIP
    assert len(actual) == 25
    assert sum(value == "G6_TRANSLATED_PROVIDER_RESULT" for value in actual.values()) == 12
    assert sum(value == "INTERNAL_PURE" for value in actual.values()) == 11
    assert sum(value == "G5_LIFECYCLE_DELIVERY" for value in actual.values()) == 2


def test_closed_ownership_enum_domains() -> None:
    assert {item.value for item in ComponentOwnership} == {"G6_INERT_SURFACE", "NON_G6"}
    assert {item.value for item in CommandOwnership} == {
        "INTERNAL_PURE", "G6_ADAPTED", "DEFERRED_RED", "INVALID_FOR_G6"
    }
    assert {item.value for item in EventOwnership} == {
        "INTERNAL_PURE", "G6_TRANSLATED_PROVIDER_RESULT", "G5_LIFECYCLE_DELIVERY",
        "DEFERRED_RED", "NOT_G6_OWNED",
    }


def test_context_projects_exact_component_and_source_inventories(context: AdapterContext) -> None:
    assert len(context.component_bindings) == 21
    assert len(context.source_channel_bindings) == 15
    assert context.scope == _scope()
    assert context.instrument_configuration_binding.configuration_digest == "sha256:" + "a" * 64
    assert not context.s0_declaration_binding.runtime_accepted


@pytest.mark.parametrize("kind", ADAPTED_KINDS, ids=lambda item: item.value)
def test_all_thirteen_command_request_result_round_trips(
    kind: CommandKind,
    context: AdapterContext,
) -> None:
    command = _command(kind)
    request = build_provider_request(command, context)
    result = _result(kind, request)
    event = translate_provider_result(command, request, result, context, 77)
    family, provider, event_kind = EXPECTED_ROUND_TRIPS[kind.value]
    assert request.adapter_family.value == family
    assert request.provider_binding.component_id == provider
    assert request.command_identity == command.identity
    assert request.scope == command.scope
    assert request.case_id == command.case_id
    assert request.repetition_id == command.repetition_id
    assert request.run_id == command.run_id
    assert request.action_id == command.action_id
    assert event.kind.value == event_kind
    assert event.event_ordinal == 77
    assert event.correlation_command_ordinal == command.command_ordinal
    assert (event.case_id, event.repetition_id, event.run_id, event.action_id) == (
        command.case_id, command.repetition_id, command.run_id, command.action_id
    )


@pytest.mark.parametrize("kind", INTERNAL_KINDS, ids=lambda item: item.value)
def test_every_internal_command_is_rejected_by_g6(kind: CommandKind, context: AdapterContext) -> None:
    command = object.__new__(OrchestrationCommand)
    object.__setattr__(command, "kind", kind)
    with pytest.raises(AdapterContractError) as caught:
        build_provider_request(command, context)
    assert caught.value.code is AdapterErrorCode.COMMAND_NOT_ADAPTED


@pytest.mark.parametrize("kind", ADAPTED_KINDS, ids=lambda item: item.value)
def test_request_identity_is_exact_g5_command_identity(kind: CommandKind, context: AdapterContext) -> None:
    command = _command(kind)
    request = build_provider_request(command, context)
    assert request.command_identity is not None
    assert request.command_identity == (command.scope, command.command_ordinal)
    assert not hasattr(request, "request_id")


REQUEST_REQUIRED_FIELDS = tuple(
    (kind, field)
    for kind, fields in {
        CommandKind.REQUEST_BASELINE_VERIFICATION: ("reset_plan_id", "reset_plan_version", "clean_state_condition", "baseline_identity"),
        CommandKind.REQUEST_RUN_INITIALIZATION: ("scheduled_run", "validation_case", "repetition", "selected_treatment", "configuration_references"),
        CommandKind.ARM_WATCHDOG: ("deadline_key", "duration_seconds"),
        CommandKind.CANCEL_WATCHDOG: ("deadline_key",),
        CommandKind.REQUEST_FAULT_APPLY: ("fault_binding", "fault_fixture_reference"),
        CommandKind.REQUEST_EXECUTION: ("action", "authorization", "approval", "control", "m3_enforcement_intent"),
        CommandKind.REQUEST_NONEXECUTION_CONFIRMATION: ("action", "authorization", "approval", "control", "cause", "m3_enforcement_intent"),
        CommandKind.REQUEST_TERMINATION: ("cause", "causal_references"),
        CommandKind.REQUEST_EVIDENCE_DRAIN: ("run_reference", "repetition_reference", "collector_reference", "reset_plan_reference", "drain_deadline_key"),
        CommandKind.REQUEST_FAULT_REMOVAL: ("fault_binding", "apply_result_reference"),
        CommandKind.REQUEST_RESET: ("reset_plan_id", "reset_plan_version", "baseline_identity", "clean_state_condition"),
        CommandKind.REQUEST_RESET_OBSERVATION: ("reset_plan_id", "reset_result_reference", "baseline_identity", "observer_reference"),
        CommandKind.REQUEST_COLLECTION_CLOSURE: ("run_reference", "repetition_reference", "evidence_set_identity", "reset_observation_references"),
    }.items()
    for field in fields
)


@pytest.mark.parametrize("kind,field", REQUEST_REQUIRED_FIELDS, ids=lambda value: value.value if isinstance(value, Enum) else value)
def test_each_request_required_field_is_strict(
    kind: CommandKind,
    field: str,
    context: AdapterContext,
) -> None:
    request = build_provider_request(_command(kind), context)
    values = dict(request.payload.items)
    del values[field]
    try:
        malformed = replace(request, payload=frozen_payload(**values))
    except AdapterContractError as error:
        caught = error
    else:
        result = _result(kind, request)
        with pytest.raises(AdapterContractError) as raised:
            translate_provider_result(_command(kind), malformed, result, context, 77)
        caught = raised.value
    assert caught.code in {AdapterErrorCode.PAYLOAD_INVALID, AdapterErrorCode.REQUEST_CONTRACT_INVALID}


@pytest.mark.parametrize("kind", ADAPTED_KINDS, ids=lambda item: item.value)
def test_each_request_family_rejects_unknown_payload_field(kind: CommandKind, context: AdapterContext) -> None:
    request = build_provider_request(_command(kind), context)
    values = dict(request.payload.items)
    values["unknown"] = "forbidden"
    with pytest.raises(AdapterContractError) as caught:
        replace(request, payload=frozen_payload(**values))
    assert caught.value.code is AdapterErrorCode.PAYLOAD_INVALID


RESULT_CASES = (
    (CommandKind.REQUEST_BASELINE_VERIFICATION, ProviderResultStatus.CLEAN_BASELINE_OBSERVED, "BASELINE_RESULT", "CLEAN_BASELINE_OBSERVED"),
    (CommandKind.REQUEST_BASELINE_VERIFICATION, ProviderResultStatus.RESET_MISMATCH_OBSERVED, "BASELINE_RESULT", "RESET_MISMATCH_OBSERVED"),
    (CommandKind.REQUEST_BASELINE_VERIFICATION, ProviderResultStatus.RESET_STATE_UNKNOWN, "BASELINE_RESULT", "RESET_STATE_UNKNOWN"),
    (CommandKind.REQUEST_BASELINE_VERIFICATION, ProviderResultStatus.FAILED, "BASELINE_RESULT", "FAILED"),
    (CommandKind.REQUEST_BASELINE_VERIFICATION, ProviderResultStatus.UNAVAILABLE, "BASELINE_RESULT", "FAILED"),
    (CommandKind.REQUEST_RUN_INITIALIZATION, ProviderResultStatus.PRODUCED, "RUN_INITIALIZATION_RESULT", "PRODUCED"),
    (CommandKind.REQUEST_RUN_INITIALIZATION, ProviderResultStatus.FAILED, "RUN_INITIALIZATION_RESULT", "FAILED"),
    (CommandKind.REQUEST_RUN_INITIALIZATION, ProviderResultStatus.UNKNOWN, "RUN_INITIALIZATION_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_RUN_INITIALIZATION, ProviderResultStatus.UNAVAILABLE, "RUN_INITIALIZATION_RESULT", "UNKNOWN"),
    (CommandKind.ARM_WATCHDOG, ProviderResultStatus.ACKNOWLEDGED, "WATCHDOG_CONTROL_RESULT", "ACKNOWLEDGED"),
    (CommandKind.ARM_WATCHDOG, ProviderResultStatus.FAILED, "WATCHDOG_CONTROL_RESULT", "FAILED"),
    (CommandKind.ARM_WATCHDOG, ProviderResultStatus.UNKNOWN, "WATCHDOG_CONTROL_RESULT", "UNKNOWN"),
    (CommandKind.ARM_WATCHDOG, ProviderResultStatus.UNAVAILABLE, "WATCHDOG_CONTROL_RESULT", "UNKNOWN"),
    (CommandKind.ARM_WATCHDOG, ProviderResultStatus.TIMEOUT, "WATCHDOG_TIMEOUT", None),
    (CommandKind.CANCEL_WATCHDOG, ProviderResultStatus.ACKNOWLEDGED, "WATCHDOG_CONTROL_RESULT", "ACKNOWLEDGED"),
    (CommandKind.CANCEL_WATCHDOG, ProviderResultStatus.FAILED, "WATCHDOG_CONTROL_RESULT", "FAILED"),
    (CommandKind.CANCEL_WATCHDOG, ProviderResultStatus.UNKNOWN, "WATCHDOG_CONTROL_RESULT", "UNKNOWN"),
    (CommandKind.CANCEL_WATCHDOG, ProviderResultStatus.UNAVAILABLE, "WATCHDOG_CONTROL_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_FAULT_APPLY, ProviderResultStatus.ACTIVE, "FAULT_RESULT", "ACTIVE"),
    (CommandKind.REQUEST_FAULT_APPLY, ProviderResultStatus.FAILED, "FAULT_RESULT", "FAILED"),
    (CommandKind.REQUEST_FAULT_APPLY, ProviderResultStatus.UNKNOWN, "FAULT_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_FAULT_APPLY, ProviderResultStatus.UNAVAILABLE, "FAULT_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_FAULT_REMOVAL, ProviderResultStatus.CLEARED, "FAULT_RESULT", "CLEARED"),
    (CommandKind.REQUEST_FAULT_REMOVAL, ProviderResultStatus.FAILED, "FAULT_RESULT", "FAILED"),
    (CommandKind.REQUEST_FAULT_REMOVAL, ProviderResultStatus.UNKNOWN, "FAULT_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_FAULT_REMOVAL, ProviderResultStatus.UNAVAILABLE, "FAULT_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_EXECUTION, ProviderResultStatus.ATTEMPTED, "EXECUTION_RESULT", "ATTEMPTED"),
    (CommandKind.REQUEST_EXECUTION, ProviderResultStatus.SUCCEEDED, "EXECUTION_RESULT", "SUCCEEDED"),
    (CommandKind.REQUEST_EXECUTION, ProviderResultStatus.FAILED, "EXECUTION_RESULT", "FAILED"),
    (CommandKind.REQUEST_EXECUTION, ProviderResultStatus.NOT_ATTEMPTED, "EXECUTION_RESULT", "NOT_ATTEMPTED"),
    (CommandKind.REQUEST_EXECUTION, ProviderResultStatus.RESULT_UNKNOWN, "EXECUTION_RESULT", "RESULT_UNKNOWN"),
    (CommandKind.REQUEST_EXECUTION, ProviderResultStatus.UNAVAILABLE, "EXECUTION_RESULT", "RESULT_UNKNOWN"),
    (CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, ProviderResultStatus.NOT_ATTEMPTED, "NONEXECUTION_RESULT", "NOT_ATTEMPTED"),
    (CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, ProviderResultStatus.FAILED, "NONEXECUTION_RESULT", "FAILED"),
    (CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, ProviderResultStatus.UNKNOWN, "NONEXECUTION_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, ProviderResultStatus.UNAVAILABLE, "NONEXECUTION_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_TERMINATION, ProviderResultStatus.OBSERVED, "TERMINATION_RESULT", "OBSERVED"),
    (CommandKind.REQUEST_TERMINATION, ProviderResultStatus.FAILED, "TERMINATION_RESULT", "FAILED"),
    (CommandKind.REQUEST_TERMINATION, ProviderResultStatus.UNKNOWN, "TERMINATION_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_TERMINATION, ProviderResultStatus.UNAVAILABLE, "TERMINATION_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_EVIDENCE_DRAIN, ProviderResultStatus.READY_FOR_RESET, "DRAIN_RESULT", "READY_FOR_RESET"),
    (CommandKind.REQUEST_EVIDENCE_DRAIN, ProviderResultStatus.FAILED, "DRAIN_RESULT", "FAILED"),
    (CommandKind.REQUEST_EVIDENCE_DRAIN, ProviderResultStatus.UNKNOWN, "DRAIN_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_EVIDENCE_DRAIN, ProviderResultStatus.UNAVAILABLE, "DRAIN_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_RESET, ProviderResultStatus.COMPLETED, "RESET_RESULT", "COMPLETED"),
    (CommandKind.REQUEST_RESET, ProviderResultStatus.FAILED, "RESET_RESULT", "FAILED"),
    (CommandKind.REQUEST_RESET, ProviderResultStatus.UNKNOWN, "RESET_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_RESET, ProviderResultStatus.UNAVAILABLE, "RESET_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_RESET_OBSERVATION, ProviderResultStatus.CLEAN_BASELINE_OBSERVED, "RESET_OBSERVATION_RESULT", "CLEAN_BASELINE_OBSERVED"),
    (CommandKind.REQUEST_RESET_OBSERVATION, ProviderResultStatus.RESET_MISMATCH_OBSERVED, "RESET_OBSERVATION_RESULT", "RESET_MISMATCH_OBSERVED"),
    (CommandKind.REQUEST_RESET_OBSERVATION, ProviderResultStatus.RESET_STATE_UNKNOWN, "RESET_OBSERVATION_RESULT", "RESET_STATE_UNKNOWN"),
    (CommandKind.REQUEST_COLLECTION_CLOSURE, ProviderResultStatus.CLOSED, "COLLECTION_RESULT", "CLOSED"),
    (CommandKind.REQUEST_COLLECTION_CLOSURE, ProviderResultStatus.FAILED, "COLLECTION_RESULT", "FAILED"),
    (CommandKind.REQUEST_COLLECTION_CLOSURE, ProviderResultStatus.UNKNOWN, "COLLECTION_RESULT", "UNKNOWN"),
    (CommandKind.REQUEST_COLLECTION_CLOSURE, ProviderResultStatus.UNAVAILABLE, "COLLECTION_RESULT", "UNKNOWN"),
)


RESULT_REQUIRED_FIELDS = (
    (CommandKind.REQUEST_BASELINE_VERIFICATION, ProviderResultStatus.CLEAN_BASELINE_OBSERVED, "observation_reference"),
    (CommandKind.REQUEST_RUN_INITIALIZATION, ProviderResultStatus.PRODUCED, "run_id"),
    (CommandKind.REQUEST_RUN_INITIALIZATION, ProviderResultStatus.PRODUCED, "candidate"),
    (CommandKind.ARM_WATCHDOG, ProviderResultStatus.ACKNOWLEDGED, "operation"),
    (CommandKind.ARM_WATCHDOG, ProviderResultStatus.ACKNOWLEDGED, "deadline_key"),
    (CommandKind.REQUEST_FAULT_APPLY, ProviderResultStatus.ACTIVE, "operation"),
    (CommandKind.REQUEST_FAULT_APPLY, ProviderResultStatus.ACTIVE, "fault_binding"),
    (CommandKind.REQUEST_EXECUTION, ProviderResultStatus.SUCCEEDED, "provider_result_reference"),
    (CommandKind.REQUEST_EXECUTION, ProviderResultStatus.SUCCEEDED, "evidence_references"),
    (CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, ProviderResultStatus.NOT_ATTEMPTED, "cause"),
    (CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, ProviderResultStatus.NOT_ATTEMPTED, "evidence_reference"),
    (CommandKind.REQUEST_TERMINATION, ProviderResultStatus.OBSERVED, "termination_class"),
    (CommandKind.REQUEST_TERMINATION, ProviderResultStatus.OBSERVED, "evidence_reference"),
    (CommandKind.REQUEST_EVIDENCE_DRAIN, ProviderResultStatus.READY_FOR_RESET, "collector_reference"),
    (CommandKind.REQUEST_RESET, ProviderResultStatus.COMPLETED, "reset_plan_id"),
    (CommandKind.REQUEST_RESET, ProviderResultStatus.COMPLETED, "reset_plan_version"),
    (CommandKind.REQUEST_RESET, ProviderResultStatus.COMPLETED, "result_reference"),
    (CommandKind.REQUEST_RESET_OBSERVATION, ProviderResultStatus.CLEAN_BASELINE_OBSERVED, "observation_reference"),
    (CommandKind.REQUEST_COLLECTION_CLOSURE, ProviderResultStatus.CLOSED, "evidence_set_reference"),
    (CommandKind.REQUEST_COLLECTION_CLOSURE, ProviderResultStatus.CLOSED, "collection_health_reference"),
)


@pytest.mark.parametrize(
    "kind,status,field",
    RESULT_REQUIRED_FIELDS,
    ids=lambda value: value.value if isinstance(value, Enum) else value,
)
def test_each_result_required_payload_field_is_strict(
    kind: CommandKind,
    status: ProviderResultStatus,
    field: str,
    context: AdapterContext,
) -> None:
    request = build_provider_request(_command(kind), context)
    result = _result(kind, request, status)
    values = dict(result.payload.items)
    del values[field]
    with pytest.raises(AdapterContractError) as caught:
        replace(result, payload=frozen_payload(**values))
    assert caught.value.code is AdapterErrorCode.PAYLOAD_INVALID


@pytest.mark.parametrize("kind,status,event_kind,event_status", RESULT_CASES, ids=lambda value: value.value if isinstance(value, Enum) else str(value))
def test_result_status_to_event_totality(
    kind: CommandKind,
    status: ProviderResultStatus,
    event_kind: str,
    event_status: str | None,
    context: AdapterContext,
) -> None:
    command = _command(kind)
    request = build_provider_request(command, context)
    result = _result(kind, request, status)
    event = translate_provider_result(command, request, result, context, 91)
    assert event.kind.value == event_kind
    assert event.payload.get("status") == event_status


@pytest.mark.parametrize("kind", ADAPTED_KINDS, ids=lambda item: item.value)
def test_result_payload_unknown_field_is_rejected(kind: CommandKind, context: AdapterContext) -> None:
    request = build_provider_request(_command(kind), context)
    result = _result(kind, request)
    values = dict(result.payload.items)
    values["unknown"] = "forbidden"
    with pytest.raises(AdapterContractError) as caught:
        replace(result, payload=frozen_payload(**values))
    assert caught.value.code is AdapterErrorCode.PAYLOAD_INVALID


@pytest.mark.parametrize("kind", ADAPTED_KINDS, ids=lambda item: item.value)
def test_wrong_provider_is_rejected_before_event(kind: CommandKind, context: AdapterContext) -> None:
    command = _command(kind)
    request = build_provider_request(command, context)
    result = _result(kind, request)
    wrong_binding = replace(result.provider_binding, component_id="scenario_adapter")
    if result.provider_binding.component_id == "scenario_adapter":
        wrong_binding = replace(result.provider_binding, component_id="reset_controller")
    wrong_identity = replace(
        result.result_identity, provider_component_id=wrong_binding.component_id
    )
    wrong = replace(result, provider_binding=wrong_binding, result_identity=wrong_identity)
    with pytest.raises(AdapterContractError) as caught:
        translate_provider_result(command, request, wrong, context, 77)
    assert caught.value.code is AdapterErrorCode.PROVIDER_IDENTITY_INVALID


@pytest.mark.parametrize("kind", ADAPTED_KINDS, ids=lambda item: item.value)
def test_wrong_build_is_rejected_before_event(kind: CommandKind, context: AdapterContext) -> None:
    command = _command(kind)
    request = build_provider_request(command, context)
    result = _result(kind, request)
    wrong = replace(result, provider_binding=replace(result.provider_binding, build_id="build:wrong"))
    with pytest.raises(AdapterContractError) as caught:
        translate_provider_result(command, request, wrong, context, 77)
    assert caught.value.code is AdapterErrorCode.PROVIDER_BUILD_INVALID


CHANNEL_KINDS = (
    CommandKind.REQUEST_BASELINE_VERIFICATION,
    CommandKind.ARM_WATCHDOG,
    CommandKind.CANCEL_WATCHDOG,
    CommandKind.REQUEST_EXECUTION,
    CommandKind.REQUEST_NONEXECUTION_CONFIRMATION,
    CommandKind.REQUEST_TERMINATION,
    CommandKind.REQUEST_EVIDENCE_DRAIN,
    CommandKind.REQUEST_RESET_OBSERVATION,
    CommandKind.REQUEST_COLLECTION_CLOSURE,
)


@pytest.mark.parametrize("kind", CHANNEL_KINDS, ids=lambda item: item.value)
def test_wrong_channel_is_rejected_before_event(kind: CommandKind, context: AdapterContext) -> None:
    command = _command(kind)
    request = build_provider_request(command, context)
    result = _result(kind, request)
    wrong = replace(
        result,
        provider_binding=replace(result.provider_binding, dedicated_local_channel_id="channel_wrong"),
    )
    with pytest.raises(AdapterContractError) as caught:
        translate_provider_result(command, request, wrong, context, 77)
    assert caught.value.code is AdapterErrorCode.PROVIDER_CHANNEL_INVALID


@pytest.mark.parametrize("kind", ADAPTED_KINDS, ids=lambda item: item.value)
def test_wrong_configuration_digest_is_rejected(kind: CommandKind, context: AdapterContext) -> None:
    command = _command(kind)
    request = build_provider_request(command, context)
    result = _result(kind, request)
    wrong_configuration = InstrumentConfigurationBinding(
        "instrument:iv-core", "0.1.0", "sha256:" + "f" * 64
    )
    wrong = replace(result, instrument_configuration_binding=wrong_configuration)
    with pytest.raises(AdapterContractError) as caught:
        translate_provider_result(command, request, wrong, context, 77)
    assert caught.value.code is AdapterErrorCode.SCOPE_BINDING_INVALID


WRONG_SCOPE_CASES = tuple((kind, "case_id") for kind in ADAPTED_KINDS) + tuple(
    (kind, "repetition_id") for kind in ADAPTED_KINDS
) + tuple(
    (kind, "run_id")
    for kind in ADAPTED_KINDS
    if kind not in {CommandKind.REQUEST_BASELINE_VERIFICATION, CommandKind.REQUEST_RUN_INITIALIZATION}
) + (
    (CommandKind.REQUEST_EXECUTION, "action_id"),
    (CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, "action_id"),
)


@pytest.mark.parametrize("kind,field", WRONG_SCOPE_CASES, ids=lambda value: value.value if isinstance(value, Enum) else value)
def test_each_wrong_scope_binding_is_rejected(
    kind: CommandKind,
    field: str,
    context: AdapterContext,
) -> None:
    command = _command(kind)
    request = build_provider_request(command, context)
    result = _result(kind, request)
    wrong = replace(result, **{field: "wrong:binding"})
    with pytest.raises(AdapterContractError) as caught:
        translate_provider_result(command, request, wrong, context, 77)
    assert caught.value.code is AdapterErrorCode.SCOPE_BINDING_INVALID


def test_result_envelope_requires_every_field(context: AdapterContext) -> None:
    request = build_provider_request(_command(CommandKind.REQUEST_EXECUTION), context)
    result = _result(CommandKind.REQUEST_EXECUTION, request)
    fields = {
        "result_identity": result.result_identity,
        "adapter_family": result.adapter_family,
        "provider_binding": result.provider_binding,
        "command_identity": result.command_identity,
        "scope": result.scope,
        "instrument_configuration_binding": result.instrument_configuration_binding,
        "case_id": result.case_id,
        "repetition_id": result.repetition_id,
        "run_id": result.run_id,
        "action_id": result.action_id,
        "status": result.status,
        "payload": result.payload,
    }
    for name in tuple(fields):
        candidate = dict(fields)
        del candidate[name]
        with pytest.raises(AdapterContractError) as caught:
            ProviderResult.from_mapping(candidate)
        assert caught.value.code is AdapterErrorCode.RESULT_CONTRACT_INVALID


def test_result_envelope_rejects_unknown_field(context: AdapterContext) -> None:
    request = build_provider_request(_command(CommandKind.REQUEST_EXECUTION), context)
    result = _result(CommandKind.REQUEST_EXECUTION, request)
    fields = {name: getattr(result, name) for name in result.__dataclass_fields__}
    fields["unknown"] = "forbidden"
    with pytest.raises(AdapterContractError) as caught:
        ProviderResult.from_mapping(fields)
    assert caught.value.code is AdapterErrorCode.RESULT_CONTRACT_INVALID


def test_missing_status_never_defaults_to_success(context: AdapterContext) -> None:
    request = build_provider_request(_command(CommandKind.REQUEST_EXECUTION), context)
    result = _result(CommandKind.REQUEST_EXECUTION, request)
    fields = {name: getattr(result, name) for name in result.__dataclass_fields__}
    del fields["status"]
    with pytest.raises(AdapterContractError) as caught:
        ProviderResult.from_mapping(fields)
    assert caught.value.code is AdapterErrorCode.RESULT_CONTRACT_INVALID


@pytest.mark.parametrize("kind", ADAPTED_KINDS, ids=lambda item: item.value)
def test_wrong_command_identity_is_rejected(kind: CommandKind, context: AdapterContext) -> None:
    command = _command(kind)
    request = build_provider_request(command, context)
    result = _result(kind, request)
    wrong_identity = (result.scope, result.command_identity[1] + 100)
    wrong = replace(
        result,
        command_identity=wrong_identity,
        result_identity=replace(result.result_identity, command_identity=wrong_identity),
    )
    with pytest.raises(AdapterContractError) as caught:
        translate_provider_result(command, request, wrong, context, 77)
    assert caught.value.code is AdapterErrorCode.COMMAND_CORRELATION_INVALID


def test_reset_observer_failure_and_unavailable_are_no_result_cases(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_RESET_OBSERVATION)
    request = build_provider_request(command, context)
    for status in (ProviderResultStatus.FAILED, ProviderResultStatus.UNAVAILABLE):
        with pytest.raises(AdapterContractError) as caught:
            _result(CommandKind.REQUEST_RESET_OBSERVATION, request, status)
        assert caught.value.code is AdapterErrorCode.STATUS_INVALID


def test_watchdog_timeout_is_arm_slot_two_only(context: AdapterContext) -> None:
    arm = _command(CommandKind.ARM_WATCHDOG)
    arm_request = build_provider_request(arm, context)
    timeout = _result(CommandKind.ARM_WATCHDOG, arm_request, ProviderResultStatus.TIMEOUT)
    assert timeout.result_identity.result_ordinal == 2
    assert translate_provider_result(arm, arm_request, timeout, context, 90).kind is EventKind.WATCHDOG_TIMEOUT
    cancel = _command(CommandKind.CANCEL_WATCHDOG)
    cancel_request = build_provider_request(cancel, context)
    cancel_timeout = _result(CommandKind.CANCEL_WATCHDOG, cancel_request, ProviderResultStatus.TIMEOUT)
    with pytest.raises(AdapterContractError) as caught:
        translate_provider_result(cancel, cancel_request, cancel_timeout, context, 91)
    assert caught.value.code is AdapterErrorCode.STATUS_INVALID


def test_command_failure_has_no_g6_result_translation() -> None:
    assert EVENT_OWNERSHIP[EventKind.COMMAND_FAILURE] is EventOwnership.G5_LIFECYCLE_DELIVERY
    assert EventKind.COMMAND_FAILURE not in {
        EventKind[name]
        for name, ownership in EXPECTED_EVENT_OWNERSHIP.items()
        if ownership == "G6_TRANSLATED_PROVIDER_RESULT"
    }


def test_m3_intent_is_derived_only_for_m3(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_EXECUTION)
    action = command.payload.get("action")
    authorization = command.payload.get("authorization")
    m3 = _control(action, authorization, layer=ControlLayer.M3)
    command = replace(command, payload=frozen_payload(action=action, authorization=authorization, approval=None, control=m3))
    request = build_provider_request(command, context)
    intent = request.payload.get("m3_enforcement_intent")
    assert isinstance(intent, M3EnforcementIntent)
    assert intent.control_decision_id == m3.control_decision_id
    assert intent.m3_provider_binding.component_id == "m3_external_enforcer"
    assert intent.m3_source_channel_binding.source_registration_id == "source:m3"
    assert build_provider_request(_command(CommandKind.REQUEST_EXECUTION), context).payload.get("m3_enforcement_intent") is None


def test_s0_declaration_is_exact_and_inert(context: AdapterContext) -> None:
    declaration = build_s0_adapter_declaration(context)
    assert isinstance(declaration, S0AdapterDeclaration)
    assert declaration.runtime_accepted is False
    assert (declaration.global_action_budget, declaration.actor_action_budget) == (8, 4)
    assert (
        declaration.run_duration_seconds,
        declaration.drain_duration_seconds,
        declaration.reset_duration_seconds,
    ) == (30, 5, 15)


def test_observer_declarations_are_distinct_and_inert(context: AdapterContext) -> None:
    resource = build_resource_observer_declaration(context)
    s0 = build_s0_observer_declaration(context)
    assert isinstance(resource, ResourceObserverDeclaration)
    assert isinstance(s0, S0ObserverDeclaration)
    assert resource.provider_binding.component_id == "resource_state_observer"
    assert s0.provider_binding.component_id == "s0_boundary_observer"
    assert resource.provider_binding != s0.provider_binding
    assert s0.authoritative_property == "S0_STATE"


def test_all_public_records_are_frozen(context: AdapterContext) -> None:
    request = build_provider_request(_command(CommandKind.REQUEST_EXECUTION), context)
    result = _result(CommandKind.REQUEST_EXECUTION, request)
    for value, field in (
        (context, "scope"),
        (request, "case_id"),
        (result, "status"),
        (build_s0_adapter_declaration(context), "runtime_accepted"),
        (build_resource_observer_declaration(context), "provider_binding"),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(value, field, None)


def test_payload_input_is_deeply_frozen_and_not_mutated(context: AdapterContext) -> None:
    original = {"candidate": {"run_id": "run:iv-g6-produced-001"}, "run_id": "run:iv-g6-produced-001"}
    payload = frozen_payload(**original)
    original["candidate"]["run_id"] = "run:mutated"
    assert payload.get("candidate")["run_id"] == "run:iv-g6-produced-001"
    request = build_provider_request(_command(CommandKind.REQUEST_EXECUTION), context)
    before = request
    _result(CommandKind.REQUEST_EXECUTION, request)
    assert request == before


def test_prototype_a_execution_request(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_EXECUTION)
    request = build_provider_request(command, context)
    assert request.adapter_family is AdapterFamily.EXECUTION
    assert request.command_identity == command.identity
    assert request.provider_binding.component_id == "action_execution_adapter"


def test_prototype_b_execution_success(context: AdapterContext) -> None:
    event = _event(CommandKind.REQUEST_EXECUTION, context)
    assert event.kind is EventKind.EXECUTION_RESULT
    assert event.payload.get("status") == "SUCCEEDED"
    assert event.payload.get("evidence_references") == ("event:execution-dispatch-001",)


def test_prototype_c_execution_explicit_failure(context: AdapterContext) -> None:
    event = _event(CommandKind.REQUEST_EXECUTION, context, status=ProviderResultStatus.FAILED)
    assert event.kind is EventKind.EXECUTION_RESULT
    assert event.payload.get("status") == "FAILED"


def test_prototype_d_malformed_result(context: AdapterContext) -> None:
    request = build_provider_request(_command(CommandKind.REQUEST_EXECUTION), context)
    result = _result(CommandKind.REQUEST_EXECUTION, request)
    values = dict(result.payload.items)
    del values["provider_result_reference"]
    with pytest.raises(AdapterContractError) as caught:
        replace(result, payload=frozen_payload(**values))
    assert caught.value.code is AdapterErrorCode.PAYLOAD_INVALID


def test_prototype_e_wrong_provider(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_EXECUTION)
    request = build_provider_request(command, context)
    result = _result(CommandKind.REQUEST_EXECUTION, request)
    binding = replace(result.provider_binding, component_id="scenario_adapter")
    result = replace(
        result,
        provider_binding=binding,
        result_identity=replace(result.result_identity, provider_component_id="scenario_adapter"),
    )
    with pytest.raises(AdapterContractError):
        translate_provider_result(command, request, result, context, 77)


def test_prototype_f_wrong_scope(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_EXECUTION)
    request = build_provider_request(command, context)
    result = replace(_result(CommandKind.REQUEST_EXECUTION, request), run_id="run:wrong")
    with pytest.raises(AdapterContractError) as caught:
        translate_provider_result(command, request, result, context, 77)
    assert caught.value.code is AdapterErrorCode.SCOPE_BINDING_INVALID


def test_prototype_g_nonexecution_separation(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_NONEXECUTION_CONFIRMATION)
    request = build_provider_request(command, context)
    assert request.payload.get("cause") is NonexecutionCause.CONTROL_BLOCKED
    assert not isinstance(request, OrchestrationEvent)
    event = translate_provider_result(command, request, _result(command.kind, request), context, 77)
    assert event.kind is EventKind.NONEXECUTION_RESULT
    assert event.payload.get("evidence_reference") == "event:nonexecution-001"


def test_prototype_h_complete_termination_separation(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_TERMINATION)
    request = build_provider_request(command, context)
    assert request.payload.get("cause") is TerminationCause.NORMAL_TERMINAL
    assert "RUN_TERMINATED" not in repr(request)
    assert _event(command.kind, context).kind is EventKind.TERMINATION_RESULT


def test_prototype_i_withdraw_termination_separation(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_TERMINATION)
    command = replace(command, payload=frozen_payload(cause=TerminationCause.AGENT_ABORT, causal_references=()))
    request = build_provider_request(command, context)
    result = _result(command.kind, request, ProviderResultStatus.OBSERVED)
    event = translate_provider_result(command, request, result, context, 77)
    assert event.payload.get("termination_class") == "AGENT_ABORT"
    assert "AGENT_ABORTED" not in repr(event)


def test_prototype_j_reset_provider_does_not_self_certify(context: AdapterContext) -> None:
    event = _event(CommandKind.REQUEST_RESET, context, status=ProviderResultStatus.FAILED)
    assert event.kind is EventKind.RESET_RESULT
    assert event.payload.get("status") == "FAILED"
    assert event.payload.get("observation_reference") is None


def test_prototype_k_independent_reset_observer(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_RESET_OBSERVATION)
    request = build_provider_request(command, context)
    assert request.provider_binding.component_id == "resource_state_observer"
    assert request.provider_binding.source_registration_id == "source:resource"
    assert _event(command.kind, context).kind is EventKind.RESET_OBSERVATION_RESULT


def test_prototype_l_watchdog_has_no_clock(context: AdapterContext) -> None:
    command = _command(CommandKind.ARM_WATCHDOG)
    request = build_provider_request(command, context)
    assert request.payload.get("duration_seconds") == 30
    assert _event(command.kind, context).kind is EventKind.WATCHDOG_CONTROL_RESULT
    assert not hasattr(request, "started_at")


def test_prototype_m_fault_is_inert(context: AdapterContext) -> None:
    apply_event = _event(CommandKind.REQUEST_FAULT_APPLY, context)
    remove_event = _event(CommandKind.REQUEST_FAULT_REMOVAL, context)
    assert apply_event.payload.get("status") == "ACTIVE"
    assert remove_event.payload.get("status") == "CLEARED"


def test_prototype_n_collection_is_inert(context: AdapterContext) -> None:
    assert _event(CommandKind.REQUEST_EVIDENCE_DRAIN, context).kind is EventKind.DRAIN_RESULT
    assert _event(CommandKind.REQUEST_COLLECTION_CLOSURE, context).kind is EventKind.COLLECTION_RESULT


def test_prototype_o_provider_result_is_not_authority(context: AdapterContext) -> None:
    event = _event(CommandKind.REQUEST_EXECUTION, context)
    assert event.payload.get("evidence_references")
    assert type(event) is OrchestrationEvent
    assert not hasattr(event, "authority")
    assert not hasattr(event, "evidence_quality")
    assert not hasattr(event, "outcome")


@pytest.mark.parametrize("wrong_type", [S01GroundTruth, SyntheticTransitionStimulus])
def test_prototype_p_ground_truth_is_not_execution_result(
    wrong_type: type,
    context: AdapterContext,
) -> None:
    request = build_provider_request(_command(CommandKind.REQUEST_EXECUTION), context)
    with pytest.raises(AdapterContractError) as caught:
        ProviderResult(
            ProviderResultIdentity(request.provider_binding.component_id, request.command_identity, 2),
            request.adapter_family,
            request.provider_binding,
            request.command_identity,
            request.scope,
            request.instrument_configuration_binding,
            request.case_id,
            request.repetition_id,
            request.run_id,
            request.action_id,
            ProviderResultStatus.SUCCEEDED,
            frozen_payload(provider_result_reference=wrong_type, evidence_references=()),
        )
    assert caught.value.code is AdapterErrorCode.PAYLOAD_INVALID


def test_prototype_q_determinism(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_EXECUTION)
    first_request = build_provider_request(command, context)
    second_request = build_provider_request(command, context)
    assert first_request == second_request
    result = _result(command.kind, first_request)
    first_event = translate_provider_result(command, first_request, result, context, 77)
    second_event = translate_provider_result(command, second_request, result, context, 77)
    assert first_event == second_event


def test_prototype_r_unknown_provider(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_EXECUTION)
    request = build_provider_request(command, context)
    result = _result(command.kind, request)
    unknown = ProviderBinding("unknown_provider", "0.1.0", "build:unknown", None, None)
    result = replace(
        result,
        provider_binding=unknown,
        result_identity=replace(result.result_identity, provider_component_id="unknown_provider"),
    )
    with pytest.raises(AdapterContractError) as caught:
        translate_provider_result(command, request, result, context, 77)
    assert caught.value.code is AdapterErrorCode.PROVIDER_IDENTITY_INVALID


def test_prototype_s_duplicate_translation_is_stateless(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_EXECUTION)
    request = build_provider_request(command, context)
    result = _result(command.kind, request)
    first = translate_provider_result(command, request, result, context, 77)
    second = translate_provider_result(command, request, result, context, 77)
    assert first == second
    assert vars(adapters).get("pending_requests") is None
    assert vars(adapters).get("delivery_history") is None


def test_prototype_t_public_surface_has_no_red_operation() -> None:
    forbidden = {
        "execute", "invoke_provider", "reset_runtime", "inject_fault",
        "observe_resource", "collect_evidence", "start_timer", "sleep",
        "open_network", "instantiate_s0",
    }
    public_callables = {
        name
        for module in (adapters, __import__("frontier_agent_containment.instrument_validation.s0", fromlist=["*"]), __import__("frontier_agent_containment.instrument_validation.observers", fromlist=["*"]))
        for name, value in vars(module).items()
        if not name.startswith("_") and callable(value)
    }
    assert not forbidden & public_callables
    production = "\n".join(
        inspect.getsource(module)
        for module in (
            adapters,
            __import__("frontier_agent_containment.instrument_validation.s0", fromlist=["*"]),
            __import__("frontier_agent_containment.instrument_validation.observers", fromlist=["*"]),
        )
    )
    for token in (
        "subprocess", "os.system", "Popen", "socket", "requests", "urllib",
        "write_text", "write_bytes", "tempfile", "docker", "podman", "kubernetes",
        "bwrap", "unshare", "time.time", "time.monotonic", "sleep(", "threading",
        "multiprocessing", "random", "secrets",
    ):
        assert token not in production


def test_event_ordinal_is_caller_supplied_and_g6_has_no_counter(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_EXECUTION)
    request = build_provider_request(command, context)
    result = _result(command.kind, request)
    assert translate_provider_result(command, request, result, context, 7).event_ordinal == 7
    assert translate_provider_result(command, request, result, context, 99).event_ordinal == 99
    assert not hasattr(request, "event_ordinal")
    assert not hasattr(result, "event_ordinal")


@pytest.mark.parametrize("ordinal", [0, -1, True, "1"])
def test_invalid_event_ordinal_is_rejected(ordinal: object, context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_EXECUTION)
    request = build_provider_request(command, context)
    result = _result(command.kind, request)
    with pytest.raises(AdapterContractError) as caught:
        translate_provider_result(command, request, result, context, ordinal)
    assert caught.value.code is AdapterErrorCode.EVENT_IDENTITY_INVALID


def test_result_identity_lifecycle_slots_are_exact(context: AdapterContext) -> None:
    execution = build_provider_request(_command(CommandKind.REQUEST_EXECUTION), context)
    assert _result(CommandKind.REQUEST_EXECUTION, execution, ProviderResultStatus.ATTEMPTED).result_identity.result_ordinal == 1
    assert _result(CommandKind.REQUEST_EXECUTION, execution, ProviderResultStatus.SUCCEEDED).result_identity.result_ordinal == 2
    watchdog = build_provider_request(_command(CommandKind.ARM_WATCHDOG), context)
    assert _result(CommandKind.ARM_WATCHDOG, watchdog, ProviderResultStatus.ACKNOWLEDGED).result_identity.result_ordinal == 1
    assert _result(CommandKind.ARM_WATCHDOG, watchdog, ProviderResultStatus.TIMEOUT).result_identity.result_ordinal == 2


def test_result_identity_rejects_random_extra_identity_shape(context: AdapterContext) -> None:
    request = build_provider_request(_command(CommandKind.REQUEST_EXECUTION), context)
    identity = ProviderResultIdentity(request.provider_binding.component_id, request.command_identity, 2)
    assert not hasattr(identity, "uuid")
    assert not hasattr(identity, "timestamp")
    assert not hasattr(identity, "digest")


def test_request_and_result_binding_carry_no_runtime_handle(context: AdapterContext) -> None:
    request = build_provider_request(_command(CommandKind.REQUEST_EXECUTION), context)
    result = _result(CommandKind.REQUEST_EXECUTION, request)
    for value in (context, request, result):
        for forbidden in ("callback", "provider", "endpoint", "connection", "handle", "credential"):
            assert not hasattr(value, forbidden)


def test_reset_provider_cannot_satisfy_reset_observer(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_RESET_OBSERVATION)
    request = build_provider_request(command, context)
    result = _result(command.kind, request)
    reset_provider = ProviderBinding("reset_controller", "0.1.0", "build:iv-reset-controller-001", None, None)
    wrong = replace(
        result,
        provider_binding=reset_provider,
        result_identity=replace(result.result_identity, provider_component_id="reset_controller"),
    )
    with pytest.raises(AdapterContractError) as caught:
        translate_provider_result(command, request, wrong, context, 77)
    assert caught.value.code is AdapterErrorCode.PROVIDER_IDENTITY_INVALID


def test_rebinding_boundary_remains_owned_by_g5(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_EXECUTION)
    request = build_provider_request(command, context)
    result = _result(command.kind, request)
    event = translate_provider_result(command, request, result, context, 77)
    changed = replace(event, payload=frozen_payload(
        status="FAILED",
        provider_result_reference="providerresult:execution-001",
        evidence_references=("event:execution-dispatch-001",),
    ))
    assert event.identity == changed.identity
    assert event != changed
    assert not hasattr(adapters, "deliver_event")


def test_local_source_channel_is_owned_by_existing_collector(context: AdapterContext) -> None:
    collector = next(
        item for item in context.source_channel_bindings
        if item.source_registration_id == "source:collector"
    )
    assert collector.source_component_id == "evidence_collector"
    assert collector.dedicated_local_channel_id == "channel_collector"
    assert "local_source_channel_adapter" not in EXPECTED_COMPONENT_OWNERSHIP


def test_no_authority_or_scientific_inventory_is_added() -> None:
    assert len(EXPECTED_COMPONENT_OWNERSHIP) == 21
    assert not hasattr(ProviderResult, "authoritative")
    assert not hasattr(ProviderResult, "evidence_quality")
    assert not hasattr(ProviderResult, "scientific_result")


def test_exception_vocabulary_is_exact() -> None:
    assert {item.value for item in AdapterErrorCode} == {
        "COMMAND_NOT_ADAPTED", "COMMAND_FAMILY_MISMATCH", "REQUEST_CONTRACT_INVALID",
        "RESULT_CONTRACT_INVALID", "PROVIDER_IDENTITY_INVALID", "PROVIDER_BUILD_INVALID",
        "PROVIDER_CHANNEL_INVALID", "COMMAND_CORRELATION_INVALID", "SCOPE_BINDING_INVALID",
        "RESULT_IDENTITY_INVALID", "STATUS_INVALID", "PAYLOAD_INVALID", "EVENT_IDENTITY_INVALID",
    }


def test_valid_failure_is_not_malformed(context: AdapterContext) -> None:
    command = _command(CommandKind.REQUEST_EXECUTION)
    request = build_provider_request(command, context)
    failure = _result(command.kind, request, ProviderResultStatus.FAILED)
    event = translate_provider_result(command, request, failure, context, 77)
    assert event.payload.get("status") == "FAILED"
    assert isinstance(failure, ProviderResult)


def test_configuration_context_has_no_mutable_registry(context: AdapterContext) -> None:
    assert isinstance(context.component_bindings, tuple)
    assert isinstance(context.source_channel_bindings, tuple)
    assert not hasattr(context, "registry")
    assert not hasattr(context, "cache")
    assert not hasattr(context, "session")
