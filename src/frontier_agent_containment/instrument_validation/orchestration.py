"""Pure IV-G5 orchestration state machines.

The module models delivery, correlation, counters, symbolic deadlines, reset,
fault injection, schedule progression, and evaluator hand-offs.  It performs
no provider invocation and creates no runtime evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, is_dataclass, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, Final, Mapping, Sequence

from .actor_control_decisions import (
    ApprovalDecision,
    ApprovalResult,
    AuthorizationDecision,
    AuthorizationResult,
    ControlDecision,
    ControlResult,
    ScriptPlan,
    RequestedAction,
    ScriptOperation,
)
from .evidence_outcomes import ActionOutcome
from .models import validate_iv_validation_case_inventory


GLOBAL_ACTION_BUDGET: Final = 8
ACTOR_RESOURCE_ACTION_BUDGET: Final = 4
WATCHDOG_DURATIONS_SECONDS: Final[Mapping[str, int]] = MappingProxyType(
    {"RUN": 30, "EVIDENCE_DRAIN": 5, "RESET": 15}
)
REPETITIONS_BY_PHASE: Final[Mapping[str, int]] = MappingProxyType(
    {"V0": 2, "V1": 3, "V2": 3, "V3": 3, "V4": 5, "V5": 2}
)
CASES_BY_PHASE: Final[Mapping[str, int]] = MappingProxyType(
    {"V0": 10, "V1": 58, "V2": 22, "V3": 35, "V4": 4, "V5": 7}
)

_LOCAL_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_TYPED_ID = re.compile(r"^[a-z][a-z0-9]*:[a-z0-9][a-z0-9._-]*$")


class OrchestratorState(str, Enum):
    VALIDATING_CONTEXT = "VALIDATING_CONTEXT"
    AWAITING_BASELINE = "AWAITING_BASELINE"
    AWAITING_RUN_INITIALIZATION = "AWAITING_RUN_INITIALIZATION"
    AWAITING_FAULT_APPLY = "AWAITING_FAULT_APPLY"
    AWAITING_SCRIPT_PLAN = "AWAITING_SCRIPT_PLAN"
    AWAITING_AUTHORIZATION = "AWAITING_AUTHORIZATION"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    AWAITING_CONTROL = "AWAITING_CONTROL"
    AWAITING_EXECUTION_RESULT = "AWAITING_EXECUTION_RESULT"
    AWAITING_NONEXECUTION_RESULT = "AWAITING_NONEXECUTION_RESULT"
    AWAITING_TERMINATION = "AWAITING_TERMINATION"
    AWAITING_DRAIN_READY = "AWAITING_DRAIN_READY"
    AWAITING_FAULT_REMOVAL = "AWAITING_FAULT_REMOVAL"
    AWAITING_RESET_RESULT = "AWAITING_RESET_RESULT"
    AWAITING_RESET_OBSERVATION = "AWAITING_RESET_OBSERVATION"
    AWAITING_COLLECTION_CLOSURE = "AWAITING_COLLECTION_CLOSURE"
    AWAITING_NORMALIZATION = "AWAITING_NORMALIZATION"
    AWAITING_ACTION_DERIVATION = "AWAITING_ACTION_DERIVATION"
    AWAITING_RUN_AGGREGATION = "AWAITING_RUN_AGGREGATION"
    AWAITING_REPETITION_EVALUATION = "AWAITING_REPETITION_EVALUATION"
    AWAITING_CASE_EVALUATION = "AWAITING_CASE_EVALUATION"
    AWAITING_ACCEPTANCE = "AWAITING_ACCEPTANCE"
    AWAITING_WATCHDOG_CONTROL = "AWAITING_WATCHDOG_CONTROL"
    COMPLETED = "COMPLETED"
    HALTED = "HALTED"
    BLOCKED_FRESH_S0 = "BLOCKED_FRESH_S0"


TERMINAL_STATES: Final = frozenset(
    {OrchestratorState.COMPLETED, OrchestratorState.HALTED, OrchestratorState.BLOCKED_FRESH_S0}
)


class ResetState(str, Enum):
    IDLE = "IDLE"
    AWAITING_RESULT = "AWAITING_RESULT"
    AWAITING_OBSERVATION = "AWAITING_OBSERVATION"
    VERIFIED_CLEAN = "VERIFIED_CLEAN"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"


class WatchdogState(str, Enum):
    IDLE = "IDLE"
    ARM_REQUESTED = "ARM_REQUESTED"
    ARMED = "ARMED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    FIRED = "FIRED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class FaultState(str, Enum):
    NO_FAULT = "NO_FAULT"
    APPLY_REQUESTED = "APPLY_REQUESTED"
    ACTIVE = "ACTIVE"
    REMOVE_REQUESTED = "REMOVE_REQUESTED"
    CLEARED = "CLEARED"
    FAILED = "FAILED"


class OrchestrationFailureClass(str, Enum):
    GOVERNING_CONTEXT_INVALID = "GOVERNING_CONTEXT_INVALID"
    INTERNAL_INVARIANT_VIOLATION = "INTERNAL_INVARIANT_VIOLATION"
    EVENT_IDENTITY_REBINDING = "EVENT_IDENTITY_REBINDING"
    EVENT_SEQUENCE_INVALID = "EVENT_SEQUENCE_INVALID"
    COMMAND_CORRELATION_INVALID = "COMMAND_CORRELATION_INVALID"
    RUN_INITIALIZATION_FAILURE = "RUN_INITIALIZATION_FAILURE"
    WATCHDOG_INTERFACE_FAILURE = "WATCHDOG_INTERFACE_FAILURE"
    ACTOR_INTERFACE_FAILURE = "ACTOR_INTERFACE_FAILURE"
    AUTHORIZATION_INTERFACE_FAILURE = "AUTHORIZATION_INTERFACE_FAILURE"
    APPROVAL_INTERFACE_FAILURE = "APPROVAL_INTERFACE_FAILURE"
    CONTROL_INTERFACE_FAILURE = "CONTROL_INTERFACE_FAILURE"
    EXECUTION_INTERFACE_FAILURE = "EXECUTION_INTERFACE_FAILURE"
    TERMINATION_INTERFACE_FAILURE = "TERMINATION_INTERFACE_FAILURE"
    DRAIN_FAILURE = "DRAIN_FAILURE"
    DRAIN_TIMEOUT = "DRAIN_TIMEOUT"
    FAULT_APPLY_FAILURE = "FAULT_APPLY_FAILURE"
    FAULT_REMOVAL_FAILURE = "FAULT_REMOVAL_FAILURE"
    RESET_COMMAND_FAILURE = "RESET_COMMAND_FAILURE"
    RESET_MISMATCH = "RESET_MISMATCH"
    RESET_UNKNOWN = "RESET_UNKNOWN"
    RESET_TIMEOUT = "RESET_TIMEOUT"
    COLLECTION_CLOSURE_FAILURE = "COLLECTION_CLOSURE_FAILURE"
    NORMALIZATION_FAILURE = "NORMALIZATION_FAILURE"
    ACTION_EVALUATOR_FAILURE = "ACTION_EVALUATOR_FAILURE"
    RUN_AGGREGATOR_FAILURE = "RUN_AGGREGATOR_FAILURE"
    CASE_EVALUATOR_FAILURE = "CASE_EVALUATOR_FAILURE"
    ACCEPTANCE_PRODUCER_FAILURE = "ACCEPTANCE_PRODUCER_FAILURE"
    RUN_TIMEOUT = "RUN_TIMEOUT"


class FindingCode(str, Enum):
    WRONG_STATE_EVENT = "WRONG_STATE_EVENT"
    STALE_CORRELATED_EVENT = "STALE_CORRELATED_EVENT"
    TERMINAL_EVENT_REJECTED = "TERMINAL_EVENT_REJECTED"
    EVENT_CONTRACT_REJECTED = "EVENT_CONTRACT_REJECTED"


class EventKind(str, Enum):
    START = "START"
    BASELINE_RESULT = "BASELINE_RESULT"
    RUN_INITIALIZATION_RESULT = "RUN_INITIALIZATION_RESULT"
    FAULT_RESULT = "FAULT_RESULT"
    SCRIPT_PLAN_RESULT = "SCRIPT_PLAN_RESULT"
    BUDGET_PROBE_RESULT = "BUDGET_PROBE_RESULT"
    AUTHORIZATION_RESULT = "AUTHORIZATION_RESULT"
    APPROVAL_RESULT = "APPROVAL_RESULT"
    CONTROL_RESULT = "CONTROL_RESULT"
    EXECUTION_RESULT = "EXECUTION_RESULT"
    NONEXECUTION_RESULT = "NONEXECUTION_RESULT"
    TERMINATION_RESULT = "TERMINATION_RESULT"
    DRAIN_RESULT = "DRAIN_RESULT"
    RESET_RESULT = "RESET_RESULT"
    RESET_OBSERVATION_RESULT = "RESET_OBSERVATION_RESULT"
    COLLECTION_RESULT = "COLLECTION_RESULT"
    NORMALIZATION_RESULT = "NORMALIZATION_RESULT"
    ACTION_EVALUATION_RESULT = "ACTION_EVALUATION_RESULT"
    RUN_AGGREGATION_RESULT = "RUN_AGGREGATION_RESULT"
    REPETITION_EVALUATION_RESULT = "REPETITION_EVALUATION_RESULT"
    CASE_EVALUATION_RESULT = "CASE_EVALUATION_RESULT"
    ACCEPTANCE_RESULT = "ACCEPTANCE_RESULT"
    WATCHDOG_CONTROL_RESULT = "WATCHDOG_CONTROL_RESULT"
    WATCHDOG_TIMEOUT = "WATCHDOG_TIMEOUT"
    COMMAND_FAILURE = "COMMAND_FAILURE"


class CommandKind(str, Enum):
    REQUEST_BASELINE_VERIFICATION = "REQUEST_BASELINE_VERIFICATION"
    REQUEST_RUN_INITIALIZATION = "REQUEST_RUN_INITIALIZATION"
    ARM_WATCHDOG = "ARM_WATCHDOG"
    CANCEL_WATCHDOG = "CANCEL_WATCHDOG"
    REQUEST_FAULT_APPLY = "REQUEST_FAULT_APPLY"
    REQUEST_SCRIPT_PLAN = "REQUEST_SCRIPT_PLAN"
    REQUEST_BUDGET_PROBE = "REQUEST_BUDGET_PROBE"
    REQUEST_AUTHORIZATION = "REQUEST_AUTHORIZATION"
    REQUEST_APPROVAL = "REQUEST_APPROVAL"
    REQUEST_CONTROL_DECISION = "REQUEST_CONTROL_DECISION"
    REQUEST_EXECUTION = "REQUEST_EXECUTION"
    REQUEST_NONEXECUTION_CONFIRMATION = "REQUEST_NONEXECUTION_CONFIRMATION"
    REQUEST_TERMINATION = "REQUEST_TERMINATION"
    REQUEST_EVIDENCE_DRAIN = "REQUEST_EVIDENCE_DRAIN"
    REQUEST_FAULT_REMOVAL = "REQUEST_FAULT_REMOVAL"
    REQUEST_RESET = "REQUEST_RESET"
    REQUEST_RESET_OBSERVATION = "REQUEST_RESET_OBSERVATION"
    REQUEST_COLLECTION_CLOSURE = "REQUEST_COLLECTION_CLOSURE"
    REQUEST_NORMALIZATION = "REQUEST_NORMALIZATION"
    REQUEST_ACTION_EVALUATION = "REQUEST_ACTION_EVALUATION"
    REQUEST_RUN_AGGREGATION = "REQUEST_RUN_AGGREGATION"
    REQUEST_REPETITION_EVALUATION = "REQUEST_REPETITION_EVALUATION"
    REQUEST_CASE_EVALUATION = "REQUEST_CASE_EVALUATION"
    REQUEST_INSTRUMENT_ACCEPTANCE = "REQUEST_INSTRUMENT_ACCEPTANCE"


class DeadlineKind(str, Enum):
    RUN = "RUN"
    EVIDENCE_DRAIN = "EVIDENCE_DRAIN"
    RESET = "RESET"


class WatchdogContinuation(str, Enum):
    AFTER_BASELINE_ARM_REQUEST_BASELINE = "AFTER_BASELINE_ARM_REQUEST_BASELINE"
    AFTER_BASELINE_CANCEL_REQUEST_RUN_INITIALIZATION = "AFTER_BASELINE_CANCEL_REQUEST_RUN_INITIALIZATION"
    AFTER_BASELINE_CANCEL_REQUEST_REPETITION_EVALUATION = "AFTER_BASELINE_CANCEL_REQUEST_REPETITION_EVALUATION"
    AFTER_RUN_ARM_REQUEST_FAULT_OR_SCRIPT = "AFTER_RUN_ARM_REQUEST_FAULT_OR_SCRIPT"
    AFTER_RUN_CANCEL_ARM_DRAIN = "AFTER_RUN_CANCEL_ARM_DRAIN"
    AFTER_DRAIN_ARM_REQUEST_DRAIN = "AFTER_DRAIN_ARM_REQUEST_DRAIN"
    AFTER_DRAIN_CANCEL_REQUEST_NORMALIZATION = "AFTER_DRAIN_CANCEL_REQUEST_NORMALIZATION"
    AFTER_RESET_ARM_REQUEST_RESET = "AFTER_RESET_ARM_REQUEST_RESET"
    AFTER_RESET_CANCEL_ROUTE_COLLECTION = "AFTER_RESET_CANCEL_ROUTE_COLLECTION"


class ExecutionStatus(str, Enum):
    ATTEMPTED = "ATTEMPTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    RESULT_UNKNOWN = "RESULT_UNKNOWN"


class TerminationCause(str, Enum):
    NORMAL_TERMINAL = "NORMAL_TERMINAL"
    AGENT_ABORT = "AGENT_ABORT"
    ACTION_BUDGET_EXHAUSTED = "ACTION_BUDGET_EXHAUSTED"
    RUN_INVALIDATION = "RUN_INVALIDATION"
    INFRASTRUCTURE_FAILURE = "INFRASTRUCTURE_FAILURE"
    TIMEOUT = "TIMEOUT"


class NonexecutionCause(str, Enum):
    CONTROL_BLOCKED = "CONTROL_BLOCKED"
    PRECONDITION_UNMET = "PRECONDITION_UNMET"
    AGENT_WITHDREW = "AGENT_WITHDREW"


@dataclass(frozen=True, slots=True)
class BudgetAdmission:
    global_count: int
    actor_count: int
    admitted: bool
    exhausted: bool
    actor_plan_invalid: bool


@dataclass(frozen=True, slots=True)
class LifecycleDirectivePlan:
    operation: ScriptOperation
    target_action_id: str | None
    first_command: CommandKind
    first_cause: NonexecutionCause | TerminationCause
    terminal_cause: TerminationCause


class ExecutionMode(str, Enum):
    PURE_EVALUATION = "PURE_EVALUATION"
    RUNTIME_REPETITION = "RUNTIME_REPETITION"


class FaultOperation(str, Enum):
    APPLY = "APPLY"
    REMOVE = "REMOVE"


class WatchdogOperation(str, Enum):
    ARM = "ARM"
    CANCEL = "CANCEL"


FROZEN_FAULT_CATEGORIES: Final = frozenset(
    {
        "authorization_unavailable", "approval_unavailable",
        "policy_source_unavailable", "malformed_policy",
        "stale_or_unaccepted_configuration", "malformed_authorization_decision",
        "unresolved_resource_identity", "unresolved_subject_identity",
        "observer_missing", "duplicate_evidence", "replayed_evidence",
        "out_of_order_evidence", "conflicting_evidence",
        "execution_adapter_failure", "synthetic_service_failure",
        "environment_initialization_failure", "m3_enforcement_failure",
        "evidence_collector_failure", "scenario_adapter_error",
        "environment_identity_mismatch", "treatment_identity_mismatch",
        "required_control_absent", "m3_administrative_exposure",
        "action_or_approval_replay", "reset_failure", "watchdog_timeout",
        "s0_intervention",
    }
)


@dataclass(frozen=True, slots=True)
class OrchestrationScope:
    validation_campaign_id: str
    runtime_plan_id: str
    runtime_plan_version: str
    instrument_configuration_id: str
    validation_set_id: str
    validation_set_version: str
    target_campaign_id: str

    def __post_init__(self) -> None:
        if not _LOCAL_ID.fullmatch(self.validation_campaign_id):
            raise ValueError("invalid validation_campaign_id")
        if self.runtime_plan_version != "0.2.0":
            raise ValueError("runtime plan must be 0.2.0")
        if not all(
            isinstance(value, str) and value
            for value in (
                self.runtime_plan_id,
                self.instrument_configuration_id,
                self.validation_set_id,
                self.validation_set_version,
                self.target_campaign_id,
            )
        ):
            raise ValueError("scope fields must be nonempty strings")


@dataclass(frozen=True, slots=True)
class FrozenPayload:
    """Closed immutable key/value payload used by internal delivery records."""

    items: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        names = tuple(name for name, _ in self.items)
        if names != tuple(sorted(names)) or len(names) != len(set(names)):
            raise ValueError("payload keys must be unique and sorted")
        if any(not _LOCAL_ID.fullmatch(name) for name in names):
            raise ValueError("invalid payload key")
        object.__setattr__(self, "items", tuple((name, _freeze_value(value)) for name, value in self.items))

    def get(self, name: str, default: Any = None) -> Any:
        return dict(self.items).get(name, default)


def frozen_payload(**values: Any) -> FrozenPayload:
    return FrozenPayload(tuple(sorted(values.items())))


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_value(item) for key, item in sorted(value.items())})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    if is_dataclass(value) or isinstance(value, (str, int, float, bool, bytes, Enum, type(None))):
        return value
    return value


_EVENT_PAYLOAD_KEYS: Final[Mapping[EventKind, frozenset[str]]] = MappingProxyType({
    EventKind.START: frozenset(),
    EventKind.BASELINE_RESULT: frozenset({"status", "observation_reference"}),
    EventKind.RUN_INITIALIZATION_RESULT: frozenset({"status", "run_id", "candidate"}),
    EventKind.FAULT_RESULT: frozenset({"operation", "status", "fault_binding"}),
    EventKind.SCRIPT_PLAN_RESULT: frozenset({"status", "script_plan"}),
    EventKind.BUDGET_PROBE_RESULT: frozenset({"status", "actions"}),
    EventKind.AUTHORIZATION_RESULT: frozenset({"decision"}),
    EventKind.APPROVAL_RESULT: frozenset({"decision"}),
    EventKind.CONTROL_RESULT: frozenset({"decision"}),
    EventKind.EXECUTION_RESULT: frozenset({"status", "provider_result_reference", "evidence_references"}),
    EventKind.NONEXECUTION_RESULT: frozenset({"status", "cause", "evidence_reference"}),
    EventKind.TERMINATION_RESULT: frozenset({"status", "termination_class", "evidence_reference"}),
    EventKind.DRAIN_RESULT: frozenset({"status", "collector_reference"}),
    EventKind.RESET_RESULT: frozenset({"status", "reset_plan_id", "reset_plan_version", "result_reference"}),
    EventKind.RESET_OBSERVATION_RESULT: frozenset({"status", "observation_reference"}),
    EventKind.COLLECTION_RESULT: frozenset({"status", "evidence_set_reference", "collection_health_reference"}),
    EventKind.NORMALIZATION_RESULT: frozenset({"status", "order_reference"}),
    EventKind.ACTION_EVALUATION_RESULT: frozenset({"status", "candidate"}),
    EventKind.RUN_AGGREGATION_RESULT: frozenset({"status", "candidate"}),
    EventKind.REPETITION_EVALUATION_RESULT: frozenset({"result", "material_references"}),
    EventKind.CASE_EVALUATION_RESULT: frozenset({"result", "material_references"}),
    EventKind.ACCEPTANCE_RESULT: frozenset({"status", "candidate"}),
    EventKind.WATCHDOG_CONTROL_RESULT: frozenset({"status", "operation", "deadline_key"}),
    EventKind.WATCHDOG_TIMEOUT: frozenset({"deadline_key"}),
    EventKind.COMMAND_FAILURE: frozenset({"status", "command_kind"}),
})


_ACTION_EVENTS: Final = frozenset({
    EventKind.AUTHORIZATION_RESULT, EventKind.APPROVAL_RESULT, EventKind.CONTROL_RESULT,
    EventKind.EXECUTION_RESULT, EventKind.NONEXECUTION_RESULT, EventKind.ACTION_EVALUATION_RESULT,
})

_EVENT_STATUSES: Final[Mapping[EventKind, frozenset[str]]] = MappingProxyType({
    EventKind.BASELINE_RESULT: frozenset({"CLEAN_BASELINE_OBSERVED", "RESET_MISMATCH_OBSERVED", "RESET_STATE_UNKNOWN", "FAILED"}),
    EventKind.RUN_INITIALIZATION_RESULT: frozenset({"PRODUCED", "FAILED", "UNKNOWN"}),
    EventKind.FAULT_RESULT: frozenset({"ACTIVE", "CLEARED", "FAILED", "UNKNOWN"}),
    EventKind.SCRIPT_PLAN_RESULT: frozenset({"PRODUCED", "FAILED"}),
    EventKind.BUDGET_PROBE_RESULT: frozenset({"PRODUCED", "FAILED"}),
    EventKind.EXECUTION_RESULT: frozenset({"ATTEMPTED", "SUCCEEDED", "FAILED", "NOT_ATTEMPTED", "RESULT_UNKNOWN"}),
    EventKind.NONEXECUTION_RESULT: frozenset({"NOT_ATTEMPTED", "FAILED", "UNKNOWN"}),
    EventKind.TERMINATION_RESULT: frozenset({"OBSERVED", "FAILED", "UNKNOWN"}),
    EventKind.DRAIN_RESULT: frozenset({"READY_FOR_RESET", "FAILED", "UNKNOWN"}),
    EventKind.RESET_RESULT: frozenset({"COMPLETED", "FAILED", "UNKNOWN"}),
    EventKind.RESET_OBSERVATION_RESULT: frozenset({"CLEAN_BASELINE_OBSERVED", "RESET_MISMATCH_OBSERVED", "RESET_STATE_UNKNOWN"}),
    EventKind.COLLECTION_RESULT: frozenset({"CLOSED", "FAILED", "UNKNOWN"}),
    EventKind.NORMALIZATION_RESULT: frozenset({"ACCEPTED", "FAILED", "UNKNOWN"}),
    EventKind.ACTION_EVALUATION_RESULT: frozenset({"PRODUCED", "FAILED"}),
    EventKind.RUN_AGGREGATION_RESULT: frozenset({"PRODUCED", "FAILED"}),
    EventKind.ACCEPTANCE_RESULT: frozenset({"PRODUCED", "FAILED"}),
    EventKind.WATCHDOG_CONTROL_RESULT: frozenset({"ACKNOWLEDGED", "FAILED", "UNKNOWN"}),
    EventKind.COMMAND_FAILURE: frozenset({"FAILED"}),
})

_COMMAND_PAYLOAD_KEYS: Final[Mapping[CommandKind, frozenset[str]]] = MappingProxyType({
    CommandKind.REQUEST_BASELINE_VERIFICATION: frozenset({"reset_plan_id", "reset_plan_version", "clean_state_condition", "baseline_identity"}),
    CommandKind.REQUEST_RUN_INITIALIZATION: frozenset({"scheduled_run", "validation_case", "repetition", "selected_treatment", "configuration_references"}),
    CommandKind.ARM_WATCHDOG: frozenset({"deadline_key", "duration_seconds"}),
    CommandKind.CANCEL_WATCHDOG: frozenset({"deadline_key"}),
    CommandKind.REQUEST_FAULT_APPLY: frozenset({"fault_binding", "fault_fixture_reference"}),
    CommandKind.REQUEST_SCRIPT_PLAN: frozenset({"actor_reference", "case_reference", "scenario_reference", "script_reference"}),
    CommandKind.REQUEST_BUDGET_PROBE: frozenset({"case_reference", "probe_plan_reference"}),
    CommandKind.REQUEST_AUTHORIZATION: frozenset({"action", "policy_reference", "capability_reference", "governing_context_reference"}),
    CommandKind.REQUEST_APPROVAL: frozenset({"authorization", "approval_policy_reference", "action_binding"}),
    CommandKind.REQUEST_CONTROL_DECISION: frozenset({"action", "authorization", "approval", "treatment", "layer_input_references"}),
    CommandKind.REQUEST_EXECUTION: frozenset({"action", "authorization", "approval", "control"}),
    CommandKind.REQUEST_NONEXECUTION_CONFIRMATION: frozenset({"action", "authorization", "approval", "control", "cause"}),
    CommandKind.REQUEST_TERMINATION: frozenset({"cause", "causal_references"}),
    CommandKind.REQUEST_EVIDENCE_DRAIN: frozenset({"run_reference", "repetition_reference", "collector_reference", "reset_plan_reference", "drain_deadline_key"}),
    CommandKind.REQUEST_FAULT_REMOVAL: frozenset({"fault_binding", "apply_result_reference"}),
    CommandKind.REQUEST_RESET: frozenset({"reset_plan_id", "reset_plan_version", "baseline_identity", "clean_state_condition"}),
    CommandKind.REQUEST_RESET_OBSERVATION: frozenset({"reset_plan_id", "reset_result_reference", "baseline_identity", "observer_reference"}),
    CommandKind.REQUEST_COLLECTION_CLOSURE: frozenset({"run_reference", "repetition_reference", "evidence_set_identity", "reset_observation_references"}),
    CommandKind.REQUEST_NORMALIZATION: frozenset({"evidence_set_reference", "normalizer_reference", "source_references"}),
    CommandKind.REQUEST_ACTION_EVALUATION: frozenset({"trusted_context", "evidence_input", "proposed_artifact_id", "derivation_sequence"}),
    CommandKind.REQUEST_RUN_AGGREGATION: frozenset({"trusted_context", "action_universe", "action_artifacts", "run_material", "proposed_artifact_id"}),
    CommandKind.REQUEST_REPETITION_EVALUATION: frozenset({"validation_case", "repetition", "material_references"}),
    CommandKind.REQUEST_CASE_EVALUATION: frozenset({"validation_case", "applicability", "repetition_results"}),
    CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE: frozenset({"configuration", "target", "case_results", "provenance", "proposed_artifact_id"}),
})


def _payload_keys(payload: FrozenPayload) -> frozenset[str]:
    return frozenset(name for name, _ in payload.items)


def _status_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _event_required_keys(kind: EventKind, payload: FrozenPayload) -> frozenset[str]:
    status = _status_value(payload.get("status"))
    if kind is EventKind.START:
        return frozenset()
    if kind is EventKind.BASELINE_RESULT:
        return frozenset({"status", "observation_reference"}) if status != "FAILED" else frozenset({"status"})
    if kind is EventKind.RUN_INITIALIZATION_RESULT:
        return frozenset({"status", "run_id", "candidate"}) if status == "PRODUCED" else frozenset({"status"})
    if kind is EventKind.FAULT_RESULT:
        return frozenset({"operation", "status", "fault_binding"})
    if kind is EventKind.SCRIPT_PLAN_RESULT:
        return frozenset({"status", "script_plan"}) if status == "PRODUCED" else frozenset({"status"})
    if kind is EventKind.BUDGET_PROBE_RESULT:
        return frozenset({"status", "actions"}) if status == "PRODUCED" else frozenset({"status"})
    if kind in {EventKind.AUTHORIZATION_RESULT, EventKind.APPROVAL_RESULT, EventKind.CONTROL_RESULT}:
        return frozenset({"decision"})
    if kind is EventKind.EXECUTION_RESULT:
        return frozenset({"status", "evidence_references"}) if status == "RESULT_UNKNOWN" else frozenset({"status", "provider_result_reference", "evidence_references"})
    if kind is EventKind.NONEXECUTION_RESULT:
        return frozenset({"status", "cause", "evidence_reference"}) if status == "NOT_ATTEMPTED" else frozenset({"status", "cause"})
    if kind is EventKind.TERMINATION_RESULT:
        return frozenset({"status", "termination_class", "evidence_reference"}) if status == "OBSERVED" else frozenset({"status", "termination_class"})
    if kind is EventKind.DRAIN_RESULT:
        return frozenset({"status", "collector_reference"}) if status == "READY_FOR_RESET" else frozenset({"status"})
    if kind is EventKind.RESET_RESULT:
        base = {"status", "reset_plan_id", "reset_plan_version"}
        if status == "COMPLETED":
            base.add("result_reference")
        return frozenset(base)
    if kind is EventKind.RESET_OBSERVATION_RESULT:
        return frozenset({"status", "observation_reference"})
    if kind is EventKind.COLLECTION_RESULT:
        return frozenset({"status", "evidence_set_reference", "collection_health_reference"}) if status == "CLOSED" else frozenset({"status"})
    if kind is EventKind.NORMALIZATION_RESULT:
        return frozenset({"status", "order_reference"}) if status == "ACCEPTED" else frozenset({"status"})
    if kind in {EventKind.ACTION_EVALUATION_RESULT, EventKind.RUN_AGGREGATION_RESULT, EventKind.ACCEPTANCE_RESULT}:
        return frozenset({"status", "candidate"}) if status == "PRODUCED" else frozenset({"status"})
    if kind in {EventKind.REPETITION_EVALUATION_RESULT, EventKind.CASE_EVALUATION_RESULT}:
        return frozenset({"result", "material_references"})
    if kind is EventKind.WATCHDOG_CONTROL_RESULT:
        return frozenset({"status", "operation", "deadline_key"})
    if kind is EventKind.WATCHDOG_TIMEOUT:
        return frozenset({"deadline_key"})
    return frozenset({"status", "command_kind"})


def _nonempty_reference(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _reference_tuple(value: Any) -> bool:
    return isinstance(value, tuple) and all(_nonempty_reference(item) for item in value)


def _validate_event_payload(kind: EventKind, payload: FrozenPayload) -> None:
    keys = _payload_keys(payload)
    if keys != _event_required_keys(kind, payload):
        raise ValueError("event payload field set is not exact for its discriminant")
    status = _status_value(payload.get("status"))
    if kind in _EVENT_STATUSES and status not in _EVENT_STATUSES[kind]:
        raise ValueError("event status is outside its closed discriminant")
    references = {
        "observation_reference", "provider_result_reference", "evidence_reference",
        "collector_reference", "result_reference", "evidence_set_reference",
        "collection_health_reference", "order_reference",
    }
    for name in references & keys:
        if not _nonempty_reference(payload.get(name)):
            raise ValueError(f"{name} must be an exact nonempty governed reference")
    if "evidence_references" in keys and not _reference_tuple(payload.get("evidence_references")):
        raise ValueError("execution evidence references must be an immutable reference tuple")
    if "material_references" in keys and not _reference_tuple(payload.get("material_references")):
        raise ValueError("evaluation material references must be an immutable reference tuple")
    if kind is EventKind.SCRIPT_PLAN_RESULT and status == "PRODUCED" and not isinstance(payload.get("script_plan"), ScriptPlan):
        raise ValueError("produced script-plan result requires one exact ScriptPlan")
    if kind is EventKind.BUDGET_PROBE_RESULT and status == "PRODUCED":
        actions = payload.get("actions")
        if not isinstance(actions, tuple) or any(not isinstance(action, RequestedAction) for action in actions):
            raise ValueError("produced budget probe requires an immutable RequestedAction tuple")
    decision_types = {
        EventKind.AUTHORIZATION_RESULT: AuthorizationDecision,
        EventKind.APPROVAL_RESULT: ApprovalDecision,
        EventKind.CONTROL_RESULT: ControlDecision,
    }
    if kind in decision_types and not isinstance(payload.get("decision"), decision_types[kind]):
        raise ValueError("decision event payload has the wrong frozen record type")
    if kind is EventKind.FAULT_RESULT:
        operation = _status_value(payload.get("operation"))
        if operation not in {"APPLY", "REMOVE"} or not _nonempty_reference(payload.get("fault_binding")):
            raise ValueError("fault result requires its exact operation and binding")
        allowed = {"ACTIVE", "FAILED", "UNKNOWN"} if operation == "APPLY" else {"CLEARED", "FAILED", "UNKNOWN"}
        if status not in allowed:
            raise ValueError("fault result status does not match its operation")
    if kind is EventKind.RESET_RESULT:
        if payload.get("reset_plan_id") != "resetplan:iv-core" or payload.get("reset_plan_version") != "0.1.0":
            raise ValueError("reset result does not bind the frozen reset plan")
    if kind is EventKind.WATCHDOG_CONTROL_RESULT:
        if _status_value(payload.get("operation")) not in {"ARM", "CANCEL"} or not isinstance(payload.get("deadline_key"), WatchdogDeadlineKey):
            raise ValueError("watchdog result requires an exact operation and deadline key")
    if kind is EventKind.WATCHDOG_TIMEOUT and not isinstance(payload.get("deadline_key"), WatchdogDeadlineKey):
        raise ValueError("watchdog timeout requires an exact deadline key")
    if kind is EventKind.COMMAND_FAILURE:
        command_kind = payload.get("command_kind")
        if (
            status != "FAILED"
            or _status_value(command_kind) not in {item.value for item in CommandKind}
        ):
            raise ValueError("command failure payload is not exact")
    if kind is EventKind.TERMINATION_RESULT and _status_value(payload.get("termination_class")) not in {item.value for item in TerminationCause}:
        raise ValueError("termination result has an unknown requested class")
    if kind is EventKind.NONEXECUTION_RESULT and _status_value(payload.get("cause")) not in {item.value for item in NonexecutionCause}:
        raise ValueError("nonexecution result has an unknown cause")
    if kind is EventKind.REPETITION_EVALUATION_RESULT and _status_value(payload.get("result")) not in {"VALIDATION_PASS", "VALIDATION_FAIL", "VALIDATION_INCONCLUSIVE"}:
        raise ValueError("repetition result is outside the frozen vocabulary")
    if kind is EventKind.CASE_EVALUATION_RESULT and _status_value(payload.get("result")) not in {"VALIDATION_PASS", "VALIDATION_FAIL", "VALIDATION_INCONCLUSIVE", "VALIDATION_NOT_APPLICABLE"}:
        raise ValueError("case result is outside the frozen vocabulary")
    if kind in {EventKind.RUN_INITIALIZATION_RESULT, EventKind.ACTION_EVALUATION_RESULT, EventKind.RUN_AGGREGATION_RESULT, EventKind.ACCEPTANCE_RESULT} and status == "PRODUCED":
        if not isinstance(payload.get("candidate"), Mapping):
            raise ValueError("produced result requires one immutable candidate mapping")
    if kind is EventKind.RUN_INITIALIZATION_RESULT and status == "PRODUCED":
        run_id = payload.get("run_id")
        if not _nonempty_reference(run_id) or not run_id.startswith("run:"):
            raise ValueError("produced run initialization requires one opaque run ID")


def _validate_command_payload(kind: CommandKind, payload: FrozenPayload) -> None:
    if _payload_keys(payload) != _COMMAND_PAYLOAD_KEYS[kind]:
        raise ValueError("command payload field set is not exact for its discriminant")
    if kind in {CommandKind.ARM_WATCHDOG, CommandKind.CANCEL_WATCHDOG}:
        if not isinstance(payload.get("deadline_key"), WatchdogDeadlineKey):
            raise ValueError("watchdog command requires an exact deadline key")
        if kind is CommandKind.ARM_WATCHDOG and payload.get("duration_seconds") != WATCHDOG_DURATIONS_SECONDS[payload.get("deadline_key").kind.value]:
            raise ValueError("watchdog duration does not match its deadline kind")
    if kind is CommandKind.REQUEST_BASELINE_VERIFICATION:
        if (
            payload.get("reset_plan_id") != "resetplan:iv-core"
            or payload.get("reset_plan_version") != "0.1.0"
            or payload.get("clean_state_condition") != "cond:iv-core-clean-state"
            or payload.get("baseline_identity") != "cond:iv-core-clean-state"
        ):
            raise ValueError("baseline command does not bind the frozen reset contract")
    if kind is CommandKind.REQUEST_RESET:
        if (
            payload.get("reset_plan_id") != "resetplan:iv-core"
            or payload.get("reset_plan_version") != "0.1.0"
            or payload.get("clean_state_condition") != "cond:iv-core-clean-state"
            or payload.get("baseline_identity") != "cond:iv-core-clean-state"
        ):
            raise ValueError("reset command does not bind the frozen reset contract")
    if kind is CommandKind.REQUEST_RESET_OBSERVATION:
        if (
            payload.get("reset_plan_id") != "resetplan:iv-core"
            or payload.get("baseline_identity") != "cond:iv-core-clean-state"
            or not _nonempty_reference(payload.get("observer_reference"))
        ):
            raise ValueError("reset observation command does not bind the frozen reset plan")
    if kind in {CommandKind.REQUEST_AUTHORIZATION, CommandKind.REQUEST_EXECUTION, CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, CommandKind.REQUEST_CONTROL_DECISION} and not isinstance(payload.get("action"), RequestedAction):
        raise ValueError("action command requires its exact RequestedAction")
    if kind is CommandKind.REQUEST_APPROVAL and not isinstance(payload.get("authorization"), AuthorizationDecision):
        raise ValueError("approval command requires its exact AuthorizationDecision")
    if kind in {CommandKind.REQUEST_EXECUTION, CommandKind.REQUEST_NONEXECUTION_CONFIRMATION} and not isinstance(payload.get("control"), ControlDecision):
        if kind is CommandKind.REQUEST_EXECUTION or payload.get("cause") != NonexecutionCause.AGENT_WITHDREW:
            raise ValueError("provider command requires its exact ControlDecision")
    if kind is CommandKind.REQUEST_TERMINATION and _status_value(payload.get("cause")) not in {item.value for item in TerminationCause}:
        raise ValueError("termination command has an unknown cause")
    if kind is CommandKind.REQUEST_NONEXECUTION_CONFIRMATION and _status_value(payload.get("cause")) not in {item.value for item in NonexecutionCause}:
        raise ValueError("nonexecution command has an unknown cause")
    if kind in {CommandKind.REQUEST_ACTION_EVALUATION, CommandKind.REQUEST_RUN_AGGREGATION}:
        proposed = payload.get("proposed_artifact_id")
        prefix = "actionoutcome:" if kind is CommandKind.REQUEST_ACTION_EVALUATION else "runoutcome:"
        if not _nonempty_reference(proposed) or not proposed.startswith(prefix):
            raise ValueError("evaluator command requires its producer-owned opaque artifact ID")
    if kind is CommandKind.REQUEST_ACTION_EVALUATION and (not isinstance(payload.get("derivation_sequence"), int) or payload.get("derivation_sequence") < 1):
        raise ValueError("action evaluation requires a positive derivation sequence")
    nullable = {
        (CommandKind.REQUEST_CONTROL_DECISION, "approval"),
        (CommandKind.REQUEST_EXECUTION, "approval"),
        (CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, "approval"),
        (CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, "authorization"),
        (CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, "control"),
        (CommandKind.REQUEST_COLLECTION_CLOSURE, "reset_observation_references"),
        (CommandKind.REQUEST_NORMALIZATION, "evidence_set_reference"),
    }
    for name, value in payload.items:
        if value is None and (kind, name) not in nullable:
            raise ValueError(f"command payload field {name} is required")
    if kind is CommandKind.REQUEST_RUN_INITIALIZATION:
        if not isinstance(payload.get("repetition"), ScheduledValidationRepetition) or not payload.get("scheduled_run") or not payload.get("validation_case"):
            raise ValueError("run initialization requires exact schedule/case/repetition material")
    if kind in {CommandKind.REQUEST_FAULT_APPLY, CommandKind.REQUEST_FAULT_REMOVAL}:
        if not _nonempty_reference(payload.get("fault_binding")):
            raise ValueError("fault command requires its governed fault binding")
    if kind is CommandKind.REQUEST_SCRIPT_PLAN:
        if any(not _nonempty_reference(payload.get(name)) for name in ("actor_reference", "case_reference", "scenario_reference", "script_reference")):
            raise ValueError("script request requires every governed reference")
    if kind is CommandKind.REQUEST_BUDGET_PROBE:
        if any(not _nonempty_reference(payload.get(name)) for name in ("case_reference", "probe_plan_reference")):
            raise ValueError("budget probe requires its exact governed references")
    if kind is CommandKind.REQUEST_CONTROL_DECISION and not isinstance(payload.get("authorization"), AuthorizationDecision):
        raise ValueError("control request requires the retained AuthorizationDecision")
    if kind in {CommandKind.REQUEST_EXECUTION, CommandKind.REQUEST_NONEXECUTION_CONFIRMATION}:
        if not isinstance(payload.get("action"), RequestedAction):
            raise ValueError("provider request requires its exact RequestedAction")
    if kind is CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE:
        if not _nonempty_reference(payload.get("proposed_artifact_id")) or not payload.get("proposed_artifact_id").startswith("acceptance:"):
            raise ValueError("acceptance request requires its producer-owned opaque ID")
    if kind is CommandKind.REQUEST_RUN_INITIALIZATION:
        configuration = payload.get("configuration_references")
        if (
            not isinstance(payload.get("repetition"), ScheduledValidationRepetition)
            or not isinstance(payload.get("scheduled_run"), tuple)
            or not payload.get("scheduled_run")
            or not isinstance(payload.get("validation_case"), tuple)
            or not payload.get("validation_case")
            or not _nonempty_reference(payload.get("selected_treatment"))
            or not isinstance(configuration, tuple)
            or len(configuration) != 6
            or any(not _nonempty_reference(item) for item in configuration)
        ):
            raise ValueError("run initialization requires exact schedule/case/repetition material")
    if kind is CommandKind.REQUEST_FAULT_APPLY and not _nonempty_reference(payload.get("fault_fixture_reference")):
        raise ValueError("fault apply requires its bounded fixture reference")
    if kind is CommandKind.REQUEST_AUTHORIZATION:
        if (
            not _nonempty_reference(payload.get("policy_reference"))
            or not _nonempty_reference(payload.get("capability_reference"))
            or not isinstance(payload.get("governing_context_reference"), OrchestrationScope)
        ):
            raise ValueError("authorization request requires exact governed references")
    if kind is CommandKind.REQUEST_APPROVAL:
        action = payload.get("action_binding")
        authorization = payload.get("authorization")
        if (
            not isinstance(action, RequestedAction)
            or action.action_id != authorization.action_id
            or payload.get("approval_policy_reference")
            != "approvalpolicy:iv-core-deterministic"
        ):
            raise ValueError("approval request has an invalid governed binding")
    if kind is CommandKind.REQUEST_CONTROL_DECISION:
        action = payload.get("action")
        authorization = payload.get("authorization")
        approval = payload.get("approval")
        layer_inputs = payload.get("layer_input_references")
        if (
            action.action_id != authorization.action_id
            or (approval is not None and (not isinstance(approval, ApprovalDecision) or approval.action_id != action.action_id))
            or not _nonempty_reference(payload.get("treatment"))
            or not isinstance(layer_inputs, tuple)
            or not layer_inputs
            or any(not _nonempty_reference(item) for item in layer_inputs)
        ):
            raise ValueError("control request has an invalid governed binding")
    if kind in {CommandKind.REQUEST_EXECUTION, CommandKind.REQUEST_NONEXECUTION_CONFIRMATION}:
        action = payload.get("action")
        authorization = payload.get("authorization")
        approval = payload.get("approval")
        control = payload.get("control")
        withdrew = kind is CommandKind.REQUEST_NONEXECUTION_CONFIRMATION and _status_value(payload.get("cause")) == "AGENT_WITHDREW"
        if not withdrew and (
            not isinstance(authorization, AuthorizationDecision)
            or authorization.action_id != action.action_id
            or not isinstance(control, ControlDecision)
            or control.action_id != action.action_id
            or (approval is not None and (not isinstance(approval, ApprovalDecision) or approval.action_id != action.action_id))
        ):
            raise ValueError("provider request has an invalid retained decision binding")
    if kind is CommandKind.REQUEST_TERMINATION and not isinstance(payload.get("causal_references"), tuple):
        raise ValueError("termination request requires immutable causal references")
    if kind is CommandKind.REQUEST_EVIDENCE_DRAIN:
        key = payload.get("drain_deadline_key")
        reset_plan = payload.get("reset_plan_reference")
        if (
            not _nonempty_reference(payload.get("run_reference"))
            or not _nonempty_reference(payload.get("repetition_reference"))
            or not _nonempty_reference(payload.get("collector_reference"))
            or not isinstance(key, WatchdogDeadlineKey)
            or key.kind is not DeadlineKind.EVIDENCE_DRAIN
            or reset_plan != ("resetplan:iv-core", "0.1.0", "cond:iv-core-clean-state")
        ):
            raise ValueError("drain request requires exact run/reset/deadline material")
    if kind is CommandKind.REQUEST_FAULT_REMOVAL and payload.get("apply_result_reference") is None:
        raise ValueError("fault removal requires the retained apply result")
    if kind is CommandKind.REQUEST_COLLECTION_CLOSURE:
        if (
            not _nonempty_reference(payload.get("run_reference"))
            or not _nonempty_reference(payload.get("repetition_reference"))
            or payload.get("evidence_set_identity") is None
            or not isinstance(payload.get("reset_observation_references"), tuple)
        ):
            raise ValueError("collection closure requires exact run/reset material")
    if kind is CommandKind.REQUEST_NORMALIZATION:
        if (
            not _nonempty_reference(payload.get("normalizer_reference"))
            or not isinstance(payload.get("source_references"), tuple)
            or (payload.get("evidence_set_reference") is not None and not _nonempty_reference(payload.get("evidence_set_reference")))
        ):
            raise ValueError("normalization requires exact available source material")
    if kind is CommandKind.REQUEST_ACTION_EVALUATION:
        trusted = payload.get("trusted_context")
        if (
            not isinstance(trusted, tuple)
            or len(trusted) != 5
            or not isinstance(trusted[0], OrchestrationScope)
            or not _nonempty_reference(trusted[1])
            or not isinstance(trusted[2], tuple)
            or not isinstance(trusted[3], Mapping)
            or not _nonempty_reference(trusted[4])
            or not isinstance(payload.get("evidence_input"), tuple)
        ):
            raise ValueError("action evaluation requires fixed trusted/evidence material")
    if kind is CommandKind.REQUEST_RUN_AGGREGATION:
        trusted = payload.get("trusted_context")
        if (
            not isinstance(trusted, tuple)
            or len(trusted) != 4
            or not isinstance(trusted[0], OrchestrationScope)
            or not _nonempty_reference(trusted[1])
            or not isinstance(trusted[2], tuple)
            or not isinstance(trusted[3], Mapping)
            or not _reference_tuple(payload.get("action_universe"))
            and payload.get("action_universe") != ()
            or not isinstance(payload.get("action_artifacts"), tuple)
            or not isinstance(payload.get("run_material"), tuple)
        ):
            raise ValueError("run aggregation requires its fixed action/run material")
    if kind is CommandKind.REQUEST_REPETITION_EVALUATION:
        if not isinstance(payload.get("validation_case"), tuple) or not isinstance(payload.get("repetition"), ScheduledValidationRepetition) or not isinstance(payload.get("material_references"), tuple):
            raise ValueError("repetition evaluation requires exact governed material")
    if kind is CommandKind.REQUEST_CASE_EVALUATION:
        applicability = payload.get("applicability")
        if not isinstance(payload.get("validation_case"), tuple) or not isinstance(applicability, tuple) or len(applicability) != 2 or not isinstance(payload.get("repetition_results"), tuple):
            raise ValueError("case evaluation requires exact governed material")
    if kind is CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE:
        configuration = payload.get("configuration")
        provenance = payload.get("provenance")
        if (
            not isinstance(configuration, tuple)
            or len(configuration) != 3
            or any(not _nonempty_reference(item) for item in configuration)
            or not _nonempty_reference(payload.get("target"))
            or not isinstance(payload.get("case_results"), tuple)
            or not isinstance(provenance, tuple)
            or len(provenance) != 3
            or any(not _nonempty_reference(item) for item in provenance)
        ):
            raise ValueError("acceptance request requires complete fixed governed material")


@dataclass(frozen=True, slots=True)
class ScheduledValidationRepetition:
    validation_case_id: str
    validation_case_version: str
    validation_phase: str
    repetition_id: str
    case_ordinal: int
    schedule_ordinal: int
    execution_mode: ExecutionMode
    scheduled_run: tuple[tuple[str, Any], ...]
    script_plan_reference: str | None = None
    fault_class: str | None = None


@dataclass(frozen=True, slots=True)
class ScheduledValidationCase:
    validation_case: tuple[tuple[str, Any], ...]
    case_ordinal: int
    applicable: bool
    not_applicable_reason: str | None
    repetitions: tuple[ScheduledValidationRepetition, ...]

    @property
    def case_id(self) -> str:
        return str(dict(self.validation_case)["validation_case_id"])

    @property
    def phase(self) -> str:
        return str(dict(self.validation_case)["validation_phase"])


@dataclass(frozen=True, slots=True)
class ValidationExecutionSchedule:
    scope: OrchestrationScope
    cases: tuple[ScheduledValidationCase, ...]
    repetitions: tuple[ScheduledValidationRepetition, ...]
    validation_inventory_digest: str


@dataclass(frozen=True, slots=True)
class OpaqueArtifactIdPlan:
    action_ids: tuple[tuple[str, str, str, str], ...]
    run_ids: tuple[tuple[str, str, str], ...]
    acceptance_id: str


@dataclass(frozen=True, slots=True)
class TrustedOrchestrationContext:
    schedule: ValidationExecutionSchedule
    artifact_ids: OpaqueArtifactIdPlan
    runtime_plan_reference: str
    s0_acceptance_reference: str
    context_valid: bool = True


@dataclass(frozen=True, slots=True)
class WatchdogDeadlineKey:
    kind: DeadlineKind
    scope: OrchestrationScope
    arm_command_ordinal: int


@dataclass(frozen=True, slots=True)
class WatchdogSlot:
    key: WatchdogDeadlineKey
    state: WatchdogState


@dataclass(frozen=True, slots=True)
class ResetController:
    state: ResetState = ResetState.IDLE
    reset_plan_id: str = "resetplan:iv-core"
    reset_plan_version: str = "0.1.0"
    baseline_id: str = "cond:iv-core-clean-state"
    operation_failed: bool = False


@dataclass(frozen=True, slots=True)
class FailureInjectionController:
    state: FaultState = FaultState.NO_FAULT
    fault_class: str | None = None


@dataclass(frozen=True, slots=True)
class OrchestrationEvent:
    kind: EventKind
    scope: OrchestrationScope
    event_ordinal: int
    correlation_command_ordinal: int | None
    case_id: str | None
    repetition_id: str | None
    run_id: str | None
    action_id: str | None
    payload: FrozenPayload = field(default_factory=FrozenPayload)

    @property
    def identity(self) -> tuple[OrchestrationScope, int]:
        return self.scope, self.event_ordinal

    def __post_init__(self) -> None:
        if self.event_ordinal < 1:
            raise ValueError("event ordinal must be positive")
        if self.kind is EventKind.START:
            if self.correlation_command_ordinal is not None or self.payload.items:
                raise ValueError("START has no correlation or payload")
        elif not isinstance(self.correlation_command_ordinal, int):
            raise ValueError("provider result requires command correlation")
        _validate_event_payload(self.kind, self.payload)
        failed_kind = None
        if self.kind is EventKind.COMMAND_FAILURE:
            failed = self.payload.get("command_kind")
            failed_kind = failed if isinstance(failed, CommandKind) else CommandKind(failed)
        campaign_scoped_failure = (
            failed_kind is CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE
        )
        case_scoped_failure = failed_kind is CommandKind.REQUEST_CASE_EVALUATION
        if self.kind in {EventKind.START, EventKind.ACCEPTANCE_RESULT} or campaign_scoped_failure:
            if self.case_id is not None:
                raise ValueError("event kind does not carry case scope")
        elif self.case_id is None:
            raise ValueError("event kind requires case scope")
        if (
            self.kind
            in {EventKind.START, EventKind.CASE_EVALUATION_RESULT, EventKind.ACCEPTANCE_RESULT}
            or campaign_scoped_failure
            or case_scoped_failure
        ):
            if self.repetition_id is not None:
                raise ValueError("event kind does not carry repetition scope")
        elif self.repetition_id is None:
            raise ValueError("event kind requires repetition scope")
        action_commands = {
            CommandKind.REQUEST_AUTHORIZATION,
            CommandKind.REQUEST_APPROVAL,
            CommandKind.REQUEST_CONTROL_DECISION,
            CommandKind.REQUEST_EXECUTION,
            CommandKind.REQUEST_NONEXECUTION_CONFIRMATION,
            CommandKind.REQUEST_ACTION_EVALUATION,
        }
        action_scoped_failure = failed_kind in action_commands
        if self.kind in _ACTION_EVENTS or action_scoped_failure:
            if self.action_id is None:
                raise ValueError("action-scoped event requires action_id")
        elif self.action_id is not None:
            raise ValueError("non-action event cannot carry action_id")
        runless = {
            EventKind.START,
            EventKind.BASELINE_RESULT,
            EventKind.RUN_INITIALIZATION_RESULT,
            EventKind.CASE_EVALUATION_RESULT,
            EventKind.ACCEPTANCE_RESULT,
        }
        correlation_scoped = {
            EventKind.WATCHDOG_CONTROL_RESULT,
            EventKind.WATCHDOG_TIMEOUT,
            EventKind.COMMAND_FAILURE,
        }
        if self.kind in runless and self.run_id is not None:
            raise ValueError("event kind does not carry run scope")
        if self.kind not in runless | correlation_scoped and self.run_id is None:
            raise ValueError("event kind requires run scope")


@dataclass(frozen=True, slots=True)
class OrchestrationCommand:
    kind: CommandKind
    scope: OrchestrationScope
    command_ordinal: int
    target_component_id: str
    case_id: str | None
    repetition_id: str | None
    run_id: str | None
    action_id: str | None
    payload: FrozenPayload = field(default_factory=FrozenPayload)

    @property
    def identity(self) -> tuple[OrchestrationScope, int]:
        return self.scope, self.command_ordinal

    def __post_init__(self) -> None:
        if self.command_ordinal < 1:
            raise ValueError("command ordinal must be positive")
        if self.kind is CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE:
            if self.case_id is not None or self.repetition_id is not None:
                raise ValueError("acceptance command has campaign scope")
        elif self.case_id is None:
            raise ValueError("command requires case scope")
        if self.kind in {CommandKind.REQUEST_CASE_EVALUATION, CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE}:
            if self.repetition_id is not None:
                raise ValueError("command does not carry repetition scope")
        elif self.repetition_id is None:
            raise ValueError("command requires repetition scope")
        runless = {
            CommandKind.REQUEST_BASELINE_VERIFICATION,
            CommandKind.REQUEST_RUN_INITIALIZATION,
            CommandKind.REQUEST_CASE_EVALUATION,
            CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE,
        }
        optional_run = {
            CommandKind.ARM_WATCHDOG,
            CommandKind.CANCEL_WATCHDOG,
            CommandKind.REQUEST_REPETITION_EVALUATION,
        }
        if self.kind in runless:
            if self.run_id is not None:
                raise ValueError("command kind does not carry run scope")
        elif self.kind not in optional_run and self.run_id is None:
            raise ValueError("command kind requires run scope")
        action_commands = {
            CommandKind.REQUEST_AUTHORIZATION, CommandKind.REQUEST_APPROVAL,
            CommandKind.REQUEST_CONTROL_DECISION, CommandKind.REQUEST_EXECUTION,
            CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, CommandKind.REQUEST_ACTION_EVALUATION,
        }
        if (self.kind in action_commands) != (self.action_id is not None):
            raise ValueError("command action scope does not match command kind")
        _validate_command_payload(self.kind, self.payload)
        if self.kind is CommandKind.REQUEST_CONTROL_DECISION:
            allowed_targets = {"m1_policy_context_adapter", "m2_policy_mediator", "m3_external_enforcer"}
            if self.target_component_id not in allowed_targets:
                raise ValueError("control command target is not the governed selected component")
        elif self.target_component_id != _TARGETS[self.kind]:
            raise ValueError("command target does not match its frozen interface")


@dataclass(frozen=True, slots=True)
class OrchestrationFinding:
    code: FindingCode
    event_ordinal: int
    detail: str


@dataclass(frozen=True, slots=True)
class ValidationOrchestratorState:
    kind: OrchestratorState
    trusted_scope: OrchestrationScope
    schedule: ValidationExecutionSchedule
    case_cursor: int = 0
    repetition_cursor: int = 0
    run_id: str | None = None
    action_cursor: int = 0
    action_queue: tuple[RequestedAction, ...] = ()
    global_action_count: int = 0
    actor_action_count: int = 0
    next_event_ordinal: int = 1
    next_command_ordinal: int = 1
    consumed_events: tuple[OrchestrationEvent, ...] = ()
    outstanding_commands: tuple[OrchestrationCommand, ...] = ()
    completed_commands: tuple[OrchestrationCommand, ...] = ()
    watchdog_slots: tuple[WatchdogSlot, ...] = ()
    watchdog_continuations: tuple[tuple[WatchdogDeadlineKey, WatchdogContinuation], ...] = ()
    reset_controller: ResetController = field(default_factory=ResetController)
    fault_controller: FailureInjectionController = field(default_factory=FailureInjectionController)
    retained: tuple[tuple[str, Any], ...] = ()
    findings: tuple[OrchestrationFinding, ...] = ()
    failure_classes: tuple[OrchestrationFailureClass, ...] = ()
    halt_after_closure: bool = False
    fresh_s0_required: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.global_action_count <= GLOBAL_ACTION_BUDGET:
            raise ValueError("global action count out of bounds")
        if not 0 <= self.actor_action_count <= ACTOR_RESOURCE_ACTION_BUDGET:
            raise ValueError("actor action count out of bounds")


_TARGETS: Final[Mapping[CommandKind, str]] = MappingProxyType(
    {
        CommandKind.REQUEST_BASELINE_VERIFICATION: "resource_state_observer",
        CommandKind.REQUEST_RUN_INITIALIZATION: "scenario_adapter",
        CommandKind.ARM_WATCHDOG: "watchdog_controller",
        CommandKind.CANCEL_WATCHDOG: "watchdog_controller",
        CommandKind.REQUEST_FAULT_APPLY: "failure_injection_controller",
        CommandKind.REQUEST_SCRIPT_PLAN: "scripted_validation_actor",
        CommandKind.REQUEST_BUDGET_PROBE: "validation_orchestrator",
        CommandKind.REQUEST_AUTHORIZATION: "authorization_service",
        CommandKind.REQUEST_APPROVAL: "approval_emulator",
        CommandKind.REQUEST_CONTROL_DECISION: "selected_control_component",
        CommandKind.REQUEST_EXECUTION: "action_execution_adapter",
        CommandKind.REQUEST_NONEXECUTION_CONFIRMATION: "action_execution_adapter",
        CommandKind.REQUEST_TERMINATION: "watchdog_controller",
        CommandKind.REQUEST_EVIDENCE_DRAIN: "evidence_collector",
        CommandKind.REQUEST_FAULT_REMOVAL: "failure_injection_controller",
        CommandKind.REQUEST_RESET: "reset_controller",
        CommandKind.REQUEST_RESET_OBSERVATION: "resource_state_observer",
        CommandKind.REQUEST_COLLECTION_CLOSURE: "evidence_collector",
        CommandKind.REQUEST_NORMALIZATION: "evidence_normalizer_store",
        CommandKind.REQUEST_ACTION_EVALUATION: "action_outcome_evaluator",
        CommandKind.REQUEST_RUN_AGGREGATION: "run_outcome_aggregator",
        CommandKind.REQUEST_REPETITION_EVALUATION: "validation_case_evaluator",
        CommandKind.REQUEST_CASE_EVALUATION: "validation_case_evaluator",
        CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE: "instrument_acceptance_producer",
    }
)

_EXPECTED_EVENTS: Final[Mapping[CommandKind, EventKind]] = MappingProxyType(
    {
        CommandKind.REQUEST_BASELINE_VERIFICATION: EventKind.BASELINE_RESULT,
        CommandKind.REQUEST_RUN_INITIALIZATION: EventKind.RUN_INITIALIZATION_RESULT,
        CommandKind.ARM_WATCHDOG: EventKind.WATCHDOG_CONTROL_RESULT,
        CommandKind.CANCEL_WATCHDOG: EventKind.WATCHDOG_CONTROL_RESULT,
        CommandKind.REQUEST_FAULT_APPLY: EventKind.FAULT_RESULT,
        CommandKind.REQUEST_SCRIPT_PLAN: EventKind.SCRIPT_PLAN_RESULT,
        CommandKind.REQUEST_BUDGET_PROBE: EventKind.BUDGET_PROBE_RESULT,
        CommandKind.REQUEST_AUTHORIZATION: EventKind.AUTHORIZATION_RESULT,
        CommandKind.REQUEST_APPROVAL: EventKind.APPROVAL_RESULT,
        CommandKind.REQUEST_CONTROL_DECISION: EventKind.CONTROL_RESULT,
        CommandKind.REQUEST_EXECUTION: EventKind.EXECUTION_RESULT,
        CommandKind.REQUEST_NONEXECUTION_CONFIRMATION: EventKind.NONEXECUTION_RESULT,
        CommandKind.REQUEST_TERMINATION: EventKind.TERMINATION_RESULT,
        CommandKind.REQUEST_EVIDENCE_DRAIN: EventKind.DRAIN_RESULT,
        CommandKind.REQUEST_FAULT_REMOVAL: EventKind.FAULT_RESULT,
        CommandKind.REQUEST_RESET: EventKind.RESET_RESULT,
        CommandKind.REQUEST_RESET_OBSERVATION: EventKind.RESET_OBSERVATION_RESULT,
        CommandKind.REQUEST_COLLECTION_CLOSURE: EventKind.COLLECTION_RESULT,
        CommandKind.REQUEST_NORMALIZATION: EventKind.NORMALIZATION_RESULT,
        CommandKind.REQUEST_ACTION_EVALUATION: EventKind.ACTION_EVALUATION_RESULT,
        CommandKind.REQUEST_RUN_AGGREGATION: EventKind.RUN_AGGREGATION_RESULT,
        CommandKind.REQUEST_REPETITION_EVALUATION: EventKind.REPETITION_EVALUATION_RESULT,
        CommandKind.REQUEST_CASE_EVALUATION: EventKind.CASE_EVALUATION_RESULT,
        CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE: EventKind.ACCEPTANCE_RESULT,
    }
)


def validate_schedule(schedule: ValidationExecutionSchedule) -> tuple[str, ...]:
    """Return deterministic schedule violations without executing a case."""

    errors: list[str] = []
    cases = schedule.cases
    case_ids = tuple(case.case_id for case in cases)
    if len(cases) != 136:
        errors.append("schedule must contain exactly 136 cases")
    if validate_iv_validation_case_inventory(case_ids):
        errors.append("validation case inventory is not the frozen 136-case inventory")
    phase_counts = {phase: 0 for phase in CASES_BY_PHASE}
    seen_runs: set[str] = set()
    seen_repetitions: set[tuple[str, str]] = set()
    flattened: list[ScheduledValidationRepetition] = []
    required_run_fields = {
        "experiment_id", "campaign_id", "scheduled_run_id", "scheduled_run_version",
        "phase", "scenario_id", "task_id", "agent_condition_id", "model_condition_id",
        "capability_condition_id", "autonomy_condition_id", "control_condition_id",
        "capability_envelope_id", "policy_id", "environment_id",
        "instrument_configuration_id", "seed_repetition_identity", "action_budget",
        "schedule_ordinal", "scheduled_configuration_frozen",
    }
    for expected_case_ordinal, case in enumerate(cases, 1):
        if case.case_ordinal != expected_case_ordinal:
            errors.append(f"case ordinal mismatch at {expected_case_ordinal}")
        if case.phase not in phase_counts:
            errors.append(f"unknown validation phase {case.phase}")
            continue
        case_material = dict(case.validation_case)
        if case_material.get("validation_case_version") != "0.2.0":
            errors.append(f"wrong validation-case version for {case.case_id}")
        phase_counts[case.phase] += 1
        required = 0 if not case.applicable else REPETITIONS_BY_PHASE[case.phase]
        if len(case.repetitions) != required:
            errors.append(f"wrong repetition count for {case.case_id}")
        if not case.applicable and not case.not_applicable_reason:
            errors.append(f"missing not-applicable reason for {case.case_id}")
        for index, repetition in enumerate(case.repetitions, 1):
            flattened.append(repetition)
            run = dict(repetition.scheduled_run)
            if set(run) != required_run_fields:
                errors.append(f"scheduled-run field set is not exact for {case.case_id}/{repetition.repetition_id}")
            expected_rep = f"rep_{index:03d}"
            if repetition.repetition_id != expected_rep:
                errors.append(f"noncontiguous repetition for {case.case_id}")
            if repetition.validation_case_id != case.case_id or repetition.case_ordinal != case.case_ordinal:
                errors.append(f"wrong case binding for {case.case_id}")
            if repetition.validation_case_version != "0.2.0" or repetition.validation_phase != case.phase:
                errors.append(f"wrong case version/phase binding for {case.case_id}")
            if repetition.fault_class is not None and repetition.fault_class not in FROZEN_FAULT_CATEGORIES:
                errors.append(f"unknown fault class for {case.case_id}")
            key = (case.case_id, repetition.repetition_id)
            if key in seen_repetitions:
                errors.append(f"duplicate repetition {key}")
            seen_repetitions.add(key)
            run_id = run.get("scheduled_run_id")
            if not isinstance(run_id, str) or run_id in seen_runs:
                errors.append(f"duplicate/invalid scheduled run for {key}")
            else:
                seen_runs.add(run_id)
            if run.get("scheduled_run_version") != "0.1.0":
                errors.append(f"wrong scheduled-run version for {key}")
            if run.get("phase") != "INSTRUMENT_VALIDATION":
                errors.append(f"wrong scheduled-run phase for {key}")
            if run.get("campaign_id") != schedule.scope.target_campaign_id:
                errors.append(f"wrong campaign for {key}")
            if run.get("action_budget") != 8 or run.get("scheduled_configuration_frozen") is not True:
                errors.append(f"wrong scheduled-run budget/freeze for {key}")
            if run.get("schedule_ordinal") != repetition.schedule_ordinal:
                errors.append(f"wrong scheduled-run ordinal for {key}")
            seed = run.get("seed_repetition_identity", {})
            if not isinstance(seed, Mapping) or set(seed) != {"repetition_id", "seed_status"} or seed.get("repetition_id") != repetition.repetition_id or seed.get("seed_status") != "UNAVAILABLE":
                errors.append(f"wrong seed status for {key}")
            expected_mode = ExecutionMode.PURE_EVALUATION if case.phase in {"V0", "V5"} else ExecutionMode.RUNTIME_REPETITION
            if repetition.execution_mode is not expected_mode:
                errors.append(f"wrong execution mode for {key}")
    if phase_counts != dict(CASES_BY_PHASE):
        errors.append("phase inventory counts differ from 10/58/22/35/4/7")
    expected_ordinals = tuple(range(1, len(flattened) + 1))
    if tuple(rep.schedule_ordinal for rep in flattened) != expected_ordinals:
        errors.append("schedule ordinals are not contiguous case/repetition order")
    if schedule.repetitions != tuple(flattened):
        errors.append("flattened repetition tuple does not equal case order")
    return tuple(errors)


def validate_artifact_id_plan(schedule: ValidationExecutionSchedule, plan: OpaqueArtifactIdPlan) -> tuple[str, ...]:
    """Validate producer-owned opaque IDs without deriving any from content."""

    errors: list[str] = []
    runtime_keys = {
        (case.case_id, repetition.repetition_id)
        for case in schedule.cases
        for repetition in case.repetitions
        if repetition.execution_mode is ExecutionMode.RUNTIME_REPETITION
    }
    run_keys = [(case_id, repetition_id) for case_id, repetition_id, _ in plan.run_ids]
    if set(run_keys) != runtime_keys or len(run_keys) != len(set(run_keys)):
        errors.append("run artifact IDs do not exactly cover runtime repetitions")
    action_keys = [(case_id, repetition_id, action_id) for case_id, repetition_id, action_id, _ in plan.action_ids]
    if len(action_keys) != len(set(action_keys)) or any((case_id, repetition_id) not in runtime_keys for case_id, repetition_id, _ in action_keys):
        errors.append("action artifact ID bindings are duplicate or outside runtime repetitions")
    identifiers = [artifact_id for *_, artifact_id in plan.action_ids]
    identifiers.extend(artifact_id for *_, artifact_id in plan.run_ids)
    identifiers.append(plan.acceptance_id)
    prefixes = [identifier.startswith("actionoutcome:") for *_, identifier in plan.action_ids]
    prefixes.extend(identifier.startswith("runoutcome:") for *_, identifier in plan.run_ids)
    prefixes.append(plan.acceptance_id.startswith("acceptance:"))
    if any(not _TYPED_ID.fullmatch(identifier) for identifier in identifiers) or not all(prefixes):
        errors.append("artifact IDs do not use exact opaque typed-ID families")
    if len(identifiers) != len(set(identifiers)):
        errors.append("artifact IDs are not globally unique")
    return tuple(errors)


def initial_orchestrator_state(context: TrustedOrchestrationContext) -> ValidationOrchestratorState:
    return ValidationOrchestratorState(
        kind=OrchestratorState.VALIDATING_CONTEXT,
        trusted_scope=context.schedule.scope,
        schedule=context.schedule,
    )


def _active_case(state: ValidationOrchestratorState) -> ScheduledValidationCase | None:
    return state.schedule.cases[state.case_cursor] if state.case_cursor < len(state.schedule.cases) else None


def _active_repetition(state: ValidationOrchestratorState) -> ScheduledValidationRepetition | None:
    case = _active_case(state)
    if case is None or state.repetition_cursor >= len(case.repetitions):
        return None
    return case.repetitions[state.repetition_cursor]


def _retain(state: ValidationOrchestratorState, key: str, value: Any) -> ValidationOrchestratorState:
    return replace(state, retained=state.retained + ((key, value),))


def _fail(state: ValidationOrchestratorState, failure: OrchestrationFailureClass) -> ValidationOrchestratorState:
    return replace(state, failure_classes=state.failure_classes + (failure,))


def _last_retained(state: ValidationOrchestratorState, key: str, default: Any = None) -> Any:
    return next((value for name, value in reversed(state.retained) if name == key), default)


def _current_action(state: ValidationOrchestratorState, action_id: str | None) -> RequestedAction | None:
    return next((action for action in state.action_queue if action.action_id == action_id), None)


def _command_payload(
    state: ValidationOrchestratorState,
    kind: CommandKind,
    supplied: FrozenPayload,
    action_id: str | None,
) -> FrozenPayload:
    """Construct the closed payload material for one symbolic command."""

    values = dict(supplied.items)
    case = _active_case(state)
    repetition = _active_repetition(state)
    run = dict(repetition.scheduled_run) if repetition is not None else {}
    action = values.get("action") or _current_action(state, action_id)
    authorization = values.get("authorization", _last_retained(state, "authorization"))
    approval = values.get("approval", _last_retained(state, "approval"))
    control = values.get("control", _last_retained(state, "control"))
    reset = state.reset_controller
    if kind is CommandKind.REQUEST_BASELINE_VERIFICATION:
        values = {
            "reset_plan_id": reset.reset_plan_id,
            "reset_plan_version": reset.reset_plan_version,
            "clean_state_condition": reset.baseline_id,
            "baseline_identity": reset.baseline_id,
        }
    elif kind is CommandKind.REQUEST_RUN_INITIALIZATION:
        values = {
            "scheduled_run": values.get("scheduled_run", repetition.scheduled_run if repetition else ()),
            "validation_case": case.validation_case if case else (),
            "repetition": repetition,
            "selected_treatment": run.get("control_condition_id"),
            "configuration_references": tuple(
                run.get(name)
                for name in (
                    "instrument_configuration_id", "scenario_id", "environment_id",
                    "capability_envelope_id", "policy_id", "control_condition_id",
                )
            ),
        }
    elif kind is CommandKind.REQUEST_FAULT_APPLY:
        fault = values.get("fault_binding", values.get("fault_class", repetition.fault_class if repetition else None))
        values = {"fault_binding": fault, "fault_fixture_reference": fault}
    elif kind is CommandKind.REQUEST_SCRIPT_PLAN:
        values = {
            "actor_reference": run.get("agent_condition_id"),
            "case_reference": case.case_id if case else None,
            "scenario_reference": run.get("scenario_id"),
            "script_reference": repetition.script_plan_reference if repetition else None,
        }
    elif kind is CommandKind.REQUEST_BUDGET_PROBE:
        values = {
            "case_reference": case.case_id if case else None,
            "probe_plan_reference": repetition.script_plan_reference if repetition else None,
        }
    elif kind is CommandKind.REQUEST_AUTHORIZATION:
        values = {
            "action": action,
            "policy_reference": run.get("policy_id"),
            "capability_reference": run.get("capability_envelope_id"),
            "governing_context_reference": state.trusted_scope,
        }
    elif kind is CommandKind.REQUEST_APPROVAL:
        values = {
            "authorization": authorization,
            "approval_policy_reference": "approvalpolicy:iv-core-deterministic",
            "action_binding": action,
        }
    elif kind is CommandKind.REQUEST_CONTROL_DECISION:
        values = {
            "action": action,
            "authorization": authorization,
            "approval": approval,
            "treatment": run.get("control_condition_id"),
            "layer_input_references": (
                run.get("control_condition_id"),
                run.get("instrument_configuration_id"),
            ),
        }
    elif kind is CommandKind.REQUEST_EXECUTION:
        values = {"action": action, "authorization": authorization, "approval": approval, "control": control}
    elif kind is CommandKind.REQUEST_NONEXECUTION_CONFIRMATION:
        values = {
            "action": action,
            "authorization": authorization,
            "approval": approval,
            "control": control,
            "cause": values.get("cause"),
        }
    elif kind is CommandKind.REQUEST_TERMINATION:
        values = {"cause": values.get("cause"), "causal_references": state.retained}
    elif kind is CommandKind.REQUEST_EVIDENCE_DRAIN:
        drain = next((slot.key for slot in reversed(state.watchdog_slots) if slot.key.kind is DeadlineKind.EVIDENCE_DRAIN), None)
        values = {
            "run_reference": state.run_id,
            "repetition_reference": repetition.repetition_id if repetition else None,
            "collector_reference": "evidence_collector",
            "reset_plan_reference": (reset.reset_plan_id, reset.reset_plan_version, reset.baseline_id),
            "drain_deadline_key": drain,
        }
    elif kind is CommandKind.REQUEST_FAULT_REMOVAL:
        values = {
            "fault_binding": state.fault_controller.fault_class,
            "apply_result_reference": _last_retained(state, "fault_apply_result"),
        }
    elif kind is CommandKind.REQUEST_RESET:
        values = {
            "reset_plan_id": reset.reset_plan_id,
            "reset_plan_version": reset.reset_plan_version,
            "baseline_identity": reset.baseline_id,
            "clean_state_condition": reset.baseline_id,
        }
    elif kind is CommandKind.REQUEST_RESET_OBSERVATION:
        values = {
            "reset_plan_id": reset.reset_plan_id,
            "reset_result_reference": _last_retained(
                state,
                "reset_result",
                _last_retained(state, "reset_result_missing"),
            ),
            "baseline_identity": reset.baseline_id,
            "observer_reference": "resource_state_observer",
        }
    elif kind is CommandKind.REQUEST_COLLECTION_CLOSURE:
        values = {
            "run_reference": state.run_id,
            "repetition_reference": repetition.repetition_id if repetition else None,
            "evidence_set_identity": _last_retained(
                state,
                "evidence_set_identity",
                (state.trusted_scope.validation_campaign_id, state.run_id),
            ),
            "reset_observation_references": tuple(
                value for name, value in state.retained if name == "reset_observation"
            ),
        }
    elif kind is CommandKind.REQUEST_NORMALIZATION:
        collection = _last_retained(state, "collection")
        evidence_set = collection.get("evidence_set_reference") if isinstance(collection, FrozenPayload) else None
        values = {
            "evidence_set_reference": evidence_set,
            "normalizer_reference": "evidence_normalizer_store",
            "source_references": tuple(
                value for name, value in state.retained if name in {"collection", "collection_missing"}
            ),
        }
    elif kind is CommandKind.REQUEST_ACTION_EVALUATION:
        values = {
            "trusted_context": (
                state.trusted_scope,
                _last_retained(state, "runtime_plan_reference"),
                case.validation_case if case else (),
                _last_retained(state, "run_manifest"),
                run.get("control_condition_id"),
            ),
            "evidence_input": state.retained,
            "proposed_artifact_id": values.get("proposed_artifact_id"),
            "derivation_sequence": values.get("derivation_sequence"),
        }
    elif kind is CommandKind.REQUEST_RUN_AGGREGATION:
        values = {
            "trusted_context": (
                state.trusted_scope,
                _last_retained(state, "runtime_plan_reference"),
                case.validation_case if case else (),
                _last_retained(state, "run_manifest"),
            ),
            "action_universe": tuple(action.action_id for action in state.action_queue),
            "action_artifacts": tuple(value for name, value in state.retained if name in {"action_artifact", "action_artifact_missing"}),
            "run_material": state.retained,
            "proposed_artifact_id": values.get("proposed_artifact_id"),
        }
    elif kind is CommandKind.REQUEST_REPETITION_EVALUATION:
        values = {
            "validation_case": case.validation_case if case else (),
            "repetition": repetition,
            "material_references": state.retained,
        }
    elif kind is CommandKind.REQUEST_CASE_EVALUATION:
        values = {
            "validation_case": case.validation_case if case else (),
            "applicability": (
                case.applicable if case else False,
                case.not_applicable_reason if case else None,
            ),
            "repetition_results": tuple(value for name, value in state.retained if name == "repetition_result"),
        }
    elif kind is CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE:
        artifact_plan = _last_retained(state, "artifact_id_plan")
        values = {
            "configuration": (
                state.trusted_scope.instrument_configuration_id,
                state.trusted_scope.validation_set_id,
                state.trusted_scope.validation_set_version,
            ),
            "target": state.trusted_scope.target_campaign_id,
            "case_results": tuple(
                value
                for name, value in state.retained
                if name in {"case_result", "case_result_missing"}
            ),
            "provenance": (
                _last_retained(state, "runtime_plan_reference"),
                _last_retained(state, "s0_acceptance_reference"),
                state.schedule.validation_inventory_digest,
            ),
            "proposed_artifact_id": artifact_plan.acceptance_id if isinstance(artifact_plan, OpaqueArtifactIdPlan) else None,
        }
    return frozen_payload(**values)


def _issue(
    state: ValidationOrchestratorState,
    kind: CommandKind,
    payload: FrozenPayload = FrozenPayload(),
    *,
    action_id: str | None = None,
) -> tuple[ValidationOrchestratorState, OrchestrationCommand]:
    case = _active_case(state)
    repetition = _active_repetition(state)
    target = _TARGETS[kind]
    if kind is CommandKind.REQUEST_CONTROL_DECISION:
        repetition = _active_repetition(state)
        condition = dict(repetition.scheduled_run).get("control_condition_id") if repetition else None
        target = {
            "ctrlcond:iv-core-m1": "m1_policy_context_adapter",
            "ctrlcond:iv-core-m2": "m2_policy_mediator",
            "ctrlcond:iv-core-m3": "m3_external_enforcer",
        }.get(condition, "")
    payload = _command_payload(state, kind, payload, action_id)
    command = OrchestrationCommand(
        kind=kind,
        scope=state.trusted_scope,
        command_ordinal=state.next_command_ordinal,
        target_component_id=target,
        case_id=None if kind is CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE else (case.case_id if case else None),
        repetition_id=None if kind in {CommandKind.REQUEST_CASE_EVALUATION, CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE} else (repetition.repetition_id if repetition else None),
        run_id=None if kind in {CommandKind.REQUEST_BASELINE_VERIFICATION, CommandKind.REQUEST_RUN_INITIALIZATION, CommandKind.REQUEST_CASE_EVALUATION, CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE} else state.run_id,
        action_id=action_id,
        payload=payload,
    )
    return (
        replace(
            state,
            next_command_ordinal=state.next_command_ordinal + 1,
            outstanding_commands=state.outstanding_commands + (command,),
        ),
        command,
    )


def _complete_command(state: ValidationOrchestratorState, ordinal: int, *, keep_outstanding: bool = False) -> ValidationOrchestratorState:
    command = next(command for command in state.outstanding_commands if command.command_ordinal == ordinal)
    if keep_outstanding:
        return state
    return replace(
        state,
        outstanding_commands=tuple(c for c in state.outstanding_commands if c.command_ordinal != ordinal),
        completed_commands=state.completed_commands + (command,),
    )


def _cancel_outstanding(
    state: ValidationOrchestratorState,
    kinds: frozenset[CommandKind],
) -> ValidationOrchestratorState:
    cancelled = tuple(command for command in state.outstanding_commands if command.kind in kinds)
    if not cancelled:
        return state
    return replace(
        state,
        outstanding_commands=tuple(command for command in state.outstanding_commands if command.kind not in kinds),
        completed_commands=state.completed_commands + cancelled,
    )


def _finding(state: ValidationOrchestratorState, code: FindingCode, event: OrchestrationEvent, detail: str) -> tuple[ValidationOrchestratorState, tuple[OrchestrationFinding, ...]]:
    finding = OrchestrationFinding(code, event.event_ordinal, detail)
    return replace(state, findings=state.findings + (finding,)), (finding,)


def _arm_watchdog(state: ValidationOrchestratorState, kind: DeadlineKind, continuation: WatchdogContinuation) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...]]:
    if any(slot.key.kind is kind and slot.state not in {WatchdogState.CANCELLED, WatchdogState.FIRED, WatchdogState.FAILED} for slot in state.watchdog_slots):
        return replace(_fail(state, OrchestrationFailureClass.INTERNAL_INVARIANT_VIOLATION), kind=OrchestratorState.HALTED), ()
    ordinal = state.next_command_ordinal
    key = WatchdogDeadlineKey(kind, state.trusted_scope, ordinal)
    state, command = _issue(
        state,
        CommandKind.ARM_WATCHDOG,
        frozen_payload(deadline_key=key, duration_seconds=WATCHDOG_DURATIONS_SECONDS[kind.value]),
    )
    state = replace(
        state,
        kind=OrchestratorState.AWAITING_WATCHDOG_CONTROL,
        watchdog_slots=state.watchdog_slots + (WatchdogSlot(key, WatchdogState.ARM_REQUESTED),),
        watchdog_continuations=state.watchdog_continuations + ((key, continuation),),
    )
    return state, (command,)


def _cancel_watchdog(state: ValidationOrchestratorState, kind: DeadlineKind, continuation: WatchdogContinuation) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...]]:
    slots = [slot for slot in state.watchdog_slots if slot.key.kind is kind and slot.state is WatchdogState.ARMED]
    if len(slots) != 1:
        return replace(_fail(state, OrchestrationFailureClass.INTERNAL_INVARIANT_VIOLATION), kind=OrchestratorState.HALTED), ()
    slot = slots[0]
    state, command = _issue(state, CommandKind.CANCEL_WATCHDOG, frozen_payload(deadline_key=slot.key))
    state = replace(
        state,
        kind=OrchestratorState.AWAITING_WATCHDOG_CONTROL,
        watchdog_slots=tuple(WatchdogSlot(s.key, WatchdogState.CANCEL_REQUESTED) if s == slot else s for s in state.watchdog_slots),
        watchdog_continuations=state.watchdog_continuations + ((slot.key, continuation),),
    )
    return state, (command,)


def _dispatch_schedule(state: ValidationOrchestratorState) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...]]:
    case = _active_case(state)
    if case is None:
        state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_ACCEPTANCE), CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE)
        return state, (command,)
    if not case.applicable:
        state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_CASE_EVALUATION), CommandKind.REQUEST_CASE_EVALUATION, frozen_payload(not_applicable_reason=case.not_applicable_reason))
        return state, (command,)
    repetition = _active_repetition(state)
    if repetition is None:
        state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_CASE_EVALUATION), CommandKind.REQUEST_CASE_EVALUATION)
        return state, (command,)
    state = replace(state, global_action_count=0, actor_action_count=0, action_cursor=0, action_queue=(), run_id=None, reset_controller=ResetController(), fault_controller=FailureInjectionController(FaultState.NO_FAULT, repetition.fault_class))
    if repetition.execution_mode is ExecutionMode.PURE_EVALUATION:
        state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_RUN_INITIALIZATION), CommandKind.REQUEST_RUN_INITIALIZATION, frozen_payload(scheduled_run=repetition.scheduled_run))
        return state, (command,)
    return _arm_watchdog(state, DeadlineKind.RESET, WatchdogContinuation.AFTER_BASELINE_ARM_REQUEST_BASELINE)


def _request_termination(state: ValidationOrchestratorState, cause: TerminationCause) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...]]:
    state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_TERMINATION), CommandKind.REQUEST_TERMINATION, frozen_payload(cause=cause))
    return state, (command,)


def _advance_script(state: ValidationOrchestratorState) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...]]:
    if state.action_cursor >= len(state.action_queue):
        return _request_termination(state, TerminationCause.NORMAL_TERMINAL)
    action = state.action_queue[state.action_cursor]
    admission = budget_transition(
        global_count=state.global_action_count,
        actor_count=state.actor_action_count,
        operation=action.operation,
        actor_selected=bool(_last_retained(state, "actor_selected_queue", True)),
    )
    if admission.exhausted:
        state = _retain(state, "budget_exhaustion_request_reference", action)
        return _request_termination(state, TerminationCause.ACTION_BUDGET_EXHAUSTED)
    if action.operation not in {ScriptOperation.INSPECT_AUTHORIZED, ScriptOperation.READ_PROTECTED, ScriptOperation.WRITE_PROTECTED}:
        raise ValueError("lifecycle directives are not RequestedAction values")
    state = replace(state, global_action_count=admission.global_count, actor_action_count=admission.actor_count)
    withdraw_target = next((value for key, value in reversed(state.retained) if key == "withdraw_target_action_id"), None)
    if withdraw_target == action.action_id:
        state, command = _issue(
            replace(state, kind=OrchestratorState.AWAITING_NONEXECUTION_RESULT),
            CommandKind.REQUEST_NONEXECUTION_CONFIRMATION,
            frozen_payload(cause=NonexecutionCause.AGENT_WITHDREW, action=action),
            action_id=action.action_id,
        )
        return state, (command,)
    state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_AUTHORIZATION), CommandKind.REQUEST_AUTHORIZATION, frozen_payload(action=action), action_id=action.action_id)
    return state, (command,)


def _validated_script_plan(
    state: ValidationOrchestratorState,
    plan: ScriptPlan,
) -> tuple[tuple[RequestedAction, ...], str | None]:
    """Validate the governed plan binding and locate its first withdrawal."""

    repetition = _active_repetition(state)
    run = dict(repetition.scheduled_run) if repetition is not None else {}
    if (
        plan.format_version != "0.1.0"
        or plan.actor_id != run.get("agent_condition_id")
        or plan.instrument_configuration_id != state.trusted_scope.instrument_configuration_id
        or plan.scenario_id != run.get("scenario_id")
        or plan.global_action_budget != GLOBAL_ACTION_BUDGET
        or repetition is None
        or repetition.script_plan_reference not in {plan.script_id, f"{plan.script_id}@{plan.script_version}"}
    ):
        raise ValueError("ScriptPlan does not match the governed repetition")
    if not plan.steps or plan.steps[-1].operation is not ScriptOperation.COMPLETE:
        raise ValueError("ScriptPlan must end in the frozen complete directive")
    step_indices = tuple(step.step_index for step in plan.steps)
    if step_indices != tuple(range(1, len(plan.steps) + 1)):
        raise ValueError("ScriptPlan steps are not contiguous")
    actions = tuple(sorted(plan.requested_actions, key=lambda action: action.step_index))
    if any(
        action.actor_id != plan.actor_id
        or action.script_id != plan.script_id
        or action.script_version != plan.script_version
        or action.instrument_configuration_id != plan.instrument_configuration_id
        or action.scenario_id != plan.scenario_id
        for action in actions
    ):
        raise ValueError("RequestedAction does not bind the governed ScriptPlan")
    withdraw_target: str | None = None
    for step in plan.steps:
        if step.operation is ScriptOperation.WITHDRAW:
            target = next(
                (action for action in actions if action.step_index == step.target_step_index),
                None,
            )
            if target is None:
                raise ValueError("withdraw does not target a governed pending request")
            withdraw_target = target.action_id
            break
    return actions, withdraw_target


def _retain_unreached_cases(state: ValidationOrchestratorState) -> ValidationOrchestratorState:
    """Identify every unvisited governed case before rejection-capable acceptance."""

    already = {
        value
        for name, value in state.retained
        if name == "case_result_missing" and isinstance(value, str)
    }
    for case in state.schedule.cases[state.case_cursor + 1 :]:
        if case.case_id not in already:
            state = _retain(state, "case_result_missing", case.case_id)
    return state


def admit_action_queue(state: ValidationOrchestratorState, actions: Sequence[RequestedAction], *, actor_selected: bool = True) -> ValidationOrchestratorState:
    """Validate and retain a complete immutable action queue before admission."""

    queue = tuple(actions)
    if actor_selected and len(queue) > ACTOR_RESOURCE_ACTION_BUDGET:
        return _fail(state, OrchestrationFailureClass.ACTOR_INTERFACE_FAILURE)
    if any(action.operation not in {ScriptOperation.INSPECT_AUTHORIZED, ScriptOperation.READ_PROTECTED, ScriptOperation.WRITE_PROTECTED} for action in queue):
        return _fail(state, OrchestrationFailureClass.ACTOR_INTERFACE_FAILURE)
    return replace(state, action_queue=queue, actor_action_count=0)


def budget_transition(
    *,
    global_count: int,
    actor_count: int,
    operation: ScriptOperation,
    actor_selected: bool,
    structurally_valid: bool = True,
    duplicate: bool = False,
) -> BudgetAdmission:
    """Apply the frozen validate/duplicate/check/increment budget order."""

    if not 0 <= global_count <= GLOBAL_ACTION_BUDGET or not 0 <= actor_count <= ACTOR_RESOURCE_ACTION_BUDGET:
        raise ValueError("input counter outside frozen bounds")
    if not structurally_valid or duplicate or operation in {ScriptOperation.WITHDRAW, ScriptOperation.COMPLETE}:
        return BudgetAdmission(global_count, actor_count, False, False, False)
    if operation not in {ScriptOperation.INSPECT_AUTHORIZED, ScriptOperation.READ_PROTECTED, ScriptOperation.WRITE_PROTECTED}:
        raise ValueError("unknown budget operation")
    if actor_selected and actor_count == ACTOR_RESOURCE_ACTION_BUDGET:
        return BudgetAdmission(global_count, actor_count, False, False, True)
    if global_count == GLOBAL_ACTION_BUDGET:
        return BudgetAdmission(global_count, actor_count, False, True, False)
    return BudgetAdmission(global_count + 1, actor_count + (1 if actor_selected else 0), True, False, False)


def lifecycle_directive_plan(operation: ScriptOperation, *, target_action_id: str | None = None) -> LifecycleDirectivePlan:
    """Return the exact symbolic, sequential lifecycle command plan."""

    if operation is ScriptOperation.WITHDRAW:
        if not target_action_id:
            raise ValueError("withdraw requires its governed pending target")
        return LifecycleDirectivePlan(
            operation,
            target_action_id,
            CommandKind.REQUEST_NONEXECUTION_CONFIRMATION,
            NonexecutionCause.AGENT_WITHDREW,
            TerminationCause.AGENT_ABORT,
        )
    if operation is ScriptOperation.COMPLETE:
        if target_action_id is not None:
            raise ValueError("complete has no action target")
        return LifecycleDirectivePlan(
            operation,
            None,
            CommandKind.REQUEST_TERMINATION,
            TerminationCause.NORMAL_TERMINAL,
            TerminationCause.NORMAL_TERMINAL,
        )
    raise ValueError("resource actions are not lifecycle directives")


def watchdog_transition(slot: WatchdogSlot | None, operation: WatchdogOperation | str, key: WatchdogDeadlineKey) -> WatchdogSlot:
    """Pure standalone watchdog transition used by the orchestrator."""

    if slot is None:
        if operation is WatchdogOperation.ARM:
            return WatchdogSlot(key, WatchdogState.ARM_REQUESTED)
        raise ValueError("cancel/fire requires a slot")
    if slot.key != key:
        return slot
    if operation == "ACK_ARM" and slot.state is WatchdogState.ARM_REQUESTED:
        return WatchdogSlot(key, WatchdogState.ARMED)
    if operation is WatchdogOperation.CANCEL and slot.state is WatchdogState.ARMED:
        return WatchdogSlot(key, WatchdogState.CANCEL_REQUESTED)
    if operation == "ACK_CANCEL" and slot.state is WatchdogState.CANCEL_REQUESTED:
        return WatchdogSlot(key, WatchdogState.CANCELLED)
    if operation == "FIRE" and slot.state is WatchdogState.ARMED:
        return WatchdogSlot(key, WatchdogState.FIRED)
    if operation == "FAIL" and slot.state in {WatchdogState.ARM_REQUESTED, WatchdogState.CANCEL_REQUESTED}:
        return WatchdogSlot(key, WatchdogState.FAILED)
    return slot


def reset_transition(controller: ResetController, event: str) -> ResetController:
    """Pure seven-state reset controller; it never self-certifies clean."""

    state = controller.state
    if state is ResetState.IDLE and event == "REQUEST":
        return replace(controller, state=ResetState.AWAITING_RESULT)
    if state is ResetState.AWAITING_RESULT and event == "COMPLETED":
        return replace(controller, state=ResetState.AWAITING_OBSERVATION, operation_failed=False)
    if state is ResetState.AWAITING_RESULT and event in {"FAILED", "UNKNOWN", "TIMEOUT"}:
        return replace(controller, state=ResetState.AWAITING_OBSERVATION, operation_failed=True)
    if state is ResetState.AWAITING_OBSERVATION:
        target = {
            "CLEAN_BASELINE_OBSERVED": ResetState.FAILED if controller.operation_failed else ResetState.VERIFIED_CLEAN,
            "RESET_MISMATCH_OBSERVED": ResetState.MISMATCH,
            "RESET_STATE_UNKNOWN": ResetState.UNKNOWN,
            "FAILED": ResetState.UNKNOWN,
        }.get(event, state)
        return replace(controller, state=target)
    return controller


def fault_transition(controller: FailureInjectionController, event: str) -> FailureInjectionController:
    """Pure six-state bounded synthetic-fault controller."""

    if controller.fault_class is not None and controller.fault_class not in FROZEN_FAULT_CATEGORIES:
        raise ValueError("unknown fault category")
    transitions = {
        (FaultState.NO_FAULT, "NO_FAULT"): FaultState.CLEARED,
        (FaultState.NO_FAULT, "REQUEST_APPLY"): FaultState.APPLY_REQUESTED,
        (FaultState.APPLY_REQUESTED, "ACTIVE"): FaultState.ACTIVE,
        (FaultState.APPLY_REQUESTED, "FAILED"): FaultState.FAILED,
        (FaultState.APPLY_REQUESTED, "UNKNOWN"): FaultState.FAILED,
        (FaultState.ACTIVE, "REQUEST_REMOVE"): FaultState.REMOVE_REQUESTED,
        (FaultState.REMOVE_REQUESTED, "CLEARED"): FaultState.CLEARED,
        (FaultState.REMOVE_REQUESTED, "FAILED"): FaultState.FAILED,
        (FaultState.REMOVE_REQUESTED, "UNKNOWN"): FaultState.FAILED,
    }
    return replace(controller, state=transitions.get((controller.state, event), controller.state))


_ALLOWED_EVENTS: Final[Mapping[OrchestratorState, frozenset[EventKind]]] = MappingProxyType(
    {
        OrchestratorState.VALIDATING_CONTEXT: frozenset({EventKind.START}),
        OrchestratorState.AWAITING_BASELINE: frozenset({EventKind.BASELINE_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_RUN_INITIALIZATION: frozenset({EventKind.RUN_INITIALIZATION_RESULT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_FAULT_APPLY: frozenset({EventKind.FAULT_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_SCRIPT_PLAN: frozenset({EventKind.SCRIPT_PLAN_RESULT, EventKind.BUDGET_PROBE_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_AUTHORIZATION: frozenset({EventKind.AUTHORIZATION_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_APPROVAL: frozenset({EventKind.APPROVAL_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_CONTROL: frozenset({EventKind.CONTROL_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_EXECUTION_RESULT: frozenset({EventKind.EXECUTION_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_NONEXECUTION_RESULT: frozenset({EventKind.NONEXECUTION_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_TERMINATION: frozenset({EventKind.TERMINATION_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_DRAIN_READY: frozenset({EventKind.DRAIN_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_FAULT_REMOVAL: frozenset({EventKind.FAULT_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_RESET_RESULT: frozenset({EventKind.RESET_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_RESET_OBSERVATION: frozenset({EventKind.RESET_OBSERVATION_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_COLLECTION_CLOSURE: frozenset({EventKind.COLLECTION_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_NORMALIZATION: frozenset({EventKind.NORMALIZATION_RESULT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_ACTION_DERIVATION: frozenset({EventKind.ACTION_EVALUATION_RESULT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_RUN_AGGREGATION: frozenset({EventKind.RUN_AGGREGATION_RESULT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_REPETITION_EVALUATION: frozenset({EventKind.REPETITION_EVALUATION_RESULT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_CASE_EVALUATION: frozenset({EventKind.CASE_EVALUATION_RESULT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_ACCEPTANCE: frozenset({EventKind.ACCEPTANCE_RESULT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.AWAITING_WATCHDOG_CONTROL: frozenset({EventKind.WATCHDOG_CONTROL_RESULT, EventKind.WATCHDOG_TIMEOUT, EventKind.COMMAND_FAILURE}),
        OrchestratorState.COMPLETED: frozenset(),
        OrchestratorState.HALTED: frozenset(),
        OrchestratorState.BLOCKED_FRESH_S0: frozenset(),
    }
)


def _result_payload_correlates(
    event: OrchestrationEvent,
    command: OrchestrationCommand,
) -> bool:
    """Check material correlation not expressible through scope fields alone."""

    if event.kind is EventKind.COMMAND_FAILURE:
        return event.payload.get("command_kind") in {command.kind, command.kind.value}
    if event.kind is EventKind.AUTHORIZATION_RESULT:
        return event.payload.get("decision").action_id == command.action_id
    if event.kind is EventKind.APPROVAL_RESULT:
        decision = event.payload.get("decision")
        authorization = command.payload.get("authorization")
        return (
            decision.action_id == command.action_id
            and decision.authorization_decision_id == authorization.authorization_decision_id
            and decision.approval_policy_id
            == command.payload.get("approval_policy_reference")
        )
    if event.kind is EventKind.CONTROL_RESULT:
        decision = event.payload.get("decision")
        authorization = command.payload.get("authorization")
        approval = command.payload.get("approval")
        return (
            decision.action_id == command.action_id
            and decision.authorization_decision_id == authorization.authorization_decision_id
            and decision.approval_decision_id
            == (approval.approval_decision_id if approval is not None else None)
            and decision.control_condition_id == command.payload.get("treatment")
        )
    if event.kind is EventKind.NONEXECUTION_RESULT:
        return _status_value(event.payload.get("cause")) == _status_value(command.payload.get("cause"))
    if event.kind is EventKind.TERMINATION_RESULT:
        return _status_value(event.payload.get("termination_class")) == _status_value(command.payload.get("cause"))
    if event.kind is EventKind.FAULT_RESULT:
        return (
            _status_value(event.payload.get("operation"))
            == ("APPLY" if command.kind is CommandKind.REQUEST_FAULT_APPLY else "REMOVE")
            and event.payload.get("fault_binding") == command.payload.get("fault_binding")
        )
    if event.kind is EventKind.RESET_RESULT:
        return (
            event.payload.get("reset_plan_id") == command.payload.get("reset_plan_id")
            and event.payload.get("reset_plan_version") == command.payload.get("reset_plan_version")
        )
    if event.kind is EventKind.WATCHDOG_CONTROL_RESULT:
        return (
            event.payload.get("deadline_key") == command.payload.get("deadline_key")
            and _status_value(event.payload.get("operation"))
            == ("ARM" if command.kind is CommandKind.ARM_WATCHDOG else "CANCEL")
        )
    return True


def transition(
    state: ValidationOrchestratorState,
    event: OrchestrationEvent,
    trusted_context: TrustedOrchestrationContext,
) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...], tuple[OrchestrationFinding, ...]]:
    """Apply one deterministic, total IV-G5 orchestration transition."""

    previous = next((old for old in state.consumed_events if old.event_ordinal == event.event_ordinal), None)
    if previous is not None:
        if previous == event:
            return state, (), ()
        state = _fail(state, OrchestrationFailureClass.EVENT_IDENTITY_REBINDING)
        return replace(state, kind=OrchestratorState.HALTED), (), ()
    if event.scope != state.trusted_scope or event.scope != trusted_context.schedule.scope or state.schedule != trusted_context.schedule:
        state = _fail(state, OrchestrationFailureClass.COMMAND_CORRELATION_INVALID)
        return replace(state, kind=OrchestratorState.HALTED), (), ()
    if event.event_ordinal != state.next_event_ordinal:
        state = _fail(state, OrchestrationFailureClass.EVENT_SEQUENCE_INVALID)
        return replace(state, kind=OrchestratorState.HALTED), (), ()
    state = replace(state, consumed_events=state.consumed_events + (event,), next_event_ordinal=state.next_event_ordinal + 1)
    if state.kind in TERMINAL_STATES:
        state, findings = _finding(state, FindingCode.TERMINAL_EVENT_REJECTED, event, "terminal state is absorbing")
        return state, (), findings
    correlated: OrchestrationCommand | None = None
    if event.kind is not EventKind.START and event.kind is not EventKind.WATCHDOG_TIMEOUT:
        correlated = next((command for command in state.outstanding_commands if command.command_ordinal == event.correlation_command_ordinal), None)
        completed = next((command for command in state.completed_commands if command.command_ordinal == event.correlation_command_ordinal), None)
        candidate = correlated or completed
        if candidate is None or (event.kind is not EventKind.COMMAND_FAILURE and _EXPECTED_EVENTS[candidate.kind] is not event.kind):
            state = _fail(state, OrchestrationFailureClass.COMMAND_CORRELATION_INVALID)
            return replace(state, kind=OrchestratorState.HALTED), (), ()
        if (event.case_id, event.repetition_id, event.run_id, event.action_id) != (candidate.case_id, candidate.repetition_id, candidate.run_id, candidate.action_id):
            state = _fail(state, OrchestrationFailureClass.COMMAND_CORRELATION_INVALID)
            return replace(state, kind=OrchestratorState.HALTED), (), ()
        if correlated is None:
            state, findings = _finding(state, FindingCode.STALE_CORRELATED_EVENT, event, "command correlation is already complete")
            return state, (), findings
        if not _result_payload_correlates(event, correlated):
            state = _fail(state, OrchestrationFailureClass.COMMAND_CORRELATION_INVALID)
            return replace(state, kind=OrchestratorState.HALTED), (), ()
    if event.kind is EventKind.WATCHDOG_TIMEOUT:
        key = event.payload.get("deadline_key")
        arm_command = next(
            (
                command
                for command in state.completed_commands
                if command.command_ordinal == event.correlation_command_ordinal
                and command.kind is CommandKind.ARM_WATCHDOG
            ),
            None,
        )
        if (
            not isinstance(key, WatchdogDeadlineKey)
            or key.arm_command_ordinal != event.correlation_command_ordinal
            or key.scope != event.scope
            or arm_command is None
            or (event.case_id, event.repetition_id, event.run_id)
            != (arm_command.case_id, arm_command.repetition_id, arm_command.run_id)
        ):
            state = _fail(state, OrchestrationFailureClass.COMMAND_CORRELATION_INVALID)
            return replace(state, kind=OrchestratorState.HALTED), (), ()
    if event.kind not in _ALLOWED_EVENTS[state.kind]:
        state, findings = _finding(state, FindingCode.WRONG_STATE_EVENT, event, "event is not accepted in current state")
        return state, (), findings
    if event.kind is EventKind.WATCHDOG_TIMEOUT:
        key = event.payload.get("deadline_key")
        slot = next((item for item in state.watchdog_slots if item.key == key), None)
        if slot is None or slot.state is not WatchdogState.ARMED:
            state, findings = _finding(state, FindingCode.STALE_CORRELATED_EVENT, event, "deadline is not armed")
            return state, (), findings
    if correlated is not None:
        keep = (
            event.kind is EventKind.EXECUTION_RESULT
            and _status_value(event.payload.get("status")) == "ATTEMPTED"
        )
        state = _complete_command(state, correlated.command_ordinal, keep_outstanding=keep)
    return _transition_accepted(state, event, trusted_context)


def _answered_command(state: ValidationOrchestratorState, event: OrchestrationEvent) -> OrchestrationCommand | None:
    return next(
        (
            command
            for command in state.completed_commands
            if command.command_ordinal == event.correlation_command_ordinal
        ),
        None,
    )


def _verified_produced_candidate(
    state: ValidationOrchestratorState,
    event: OrchestrationEvent,
) -> bool:
    """Verify result identity/binding without reimplementing producer semantics."""

    candidate = event.payload.get("candidate")
    command = _answered_command(state, event)
    if not isinstance(candidate, Mapping) or command is None:
        return False
    if event.kind is EventKind.RUN_INITIALIZATION_RESULT:
        repetition = _active_repetition(state)
        scheduled = dict(repetition.scheduled_run) if repetition else {}
        return (
            candidate.get("run_id") == event.payload.get("run_id")
            and candidate.get("run_manifest_version") == "0.1.0"
            and all(candidate.get(name) == value for name, value in scheduled.items() if name != "scheduled_configuration_frozen")
            and candidate.get("s0_acceptance_identity") == _last_retained(state, "s0_acceptance_reference")
            and candidate.get("configuration_frozen_before_start") is True
        )
    proposed = command.payload.get("proposed_artifact_id")
    if event.kind is EventKind.ACTION_EVALUATION_RESULT:
        return (
            candidate.get("outcome_version") == "0.2.0"
            and candidate.get("derived_action_outcome_id") == proposed
            and candidate.get("run_id") == state.run_id
            and candidate.get("action_id") == event.action_id
            and candidate.get("terminal_outcome") in {item.value for item in ActionOutcome}
        )
    if event.kind is EventKind.RUN_AGGREGATION_RESULT:
        return (
            candidate.get("outcome_version") == "0.2.0"
            and candidate.get("derived_run_outcome_id") == proposed
            and candidate.get("run_id") == state.run_id
        )
    if event.kind is EventKind.ACCEPTANCE_RESULT:
        return (
            candidate.get("acceptance_version") == "0.2.0"
            and candidate.get("instrument_acceptance_id") == proposed
            and candidate.get("acceptance_state")
            in {"ACCEPTED_FOR_PILOT", "ACCEPTED_FOR_CONFIRMATORY", "REJECTED"}
        )
    return False


def _transition_accepted(state: ValidationOrchestratorState, event: OrchestrationEvent, context: TrustedOrchestrationContext) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...], tuple[OrchestrationFinding, ...]]:
    kind = state.kind
    status = _status_value(event.payload.get("status"))
    commands: tuple[OrchestrationCommand, ...] = ()
    if kind is OrchestratorState.VALIDATING_CONTEXT:
        if not context.context_valid or validate_schedule(context.schedule) or validate_artifact_id_plan(context.schedule, context.artifact_ids):
            return replace(_fail(state, OrchestrationFailureClass.GOVERNING_CONTEXT_INVALID), kind=OrchestratorState.HALTED), (), ()
        state = _retain(state, "runtime_plan_reference", context.runtime_plan_reference)
        state = _retain(state, "s0_acceptance_reference", context.s0_acceptance_reference)
        state = _retain(state, "artifact_id_plan", context.artifact_ids)
        state, commands = _dispatch_schedule(state)
    elif event.kind is EventKind.WATCHDOG_TIMEOUT:
        state, commands = _handle_timeout(state, event)
    elif event.kind is EventKind.COMMAND_FAILURE:
        state, commands = _handle_command_failure(state, event, context)
    elif kind is OrchestratorState.AWAITING_WATCHDOG_CONTROL:
        state, commands = _handle_watchdog_control(state, event)
    elif kind is OrchestratorState.AWAITING_BASELINE:
        if status == "CLEAN_BASELINE_OBSERVED":
            state = _retain(state, "baseline", event.payload.get("observation_reference"))
            state, commands = _cancel_watchdog(state, DeadlineKind.RESET, WatchdogContinuation.AFTER_BASELINE_CANCEL_REQUEST_RUN_INITIALIZATION)
        else:
            failure = OrchestrationFailureClass.RESET_MISMATCH if status == "RESET_MISMATCH_OBSERVED" else OrchestrationFailureClass.RESET_UNKNOWN
            state = replace(_fail(state, failure), fresh_s0_required=True)
            state, commands = _cancel_watchdog(state, DeadlineKind.RESET, WatchdogContinuation.AFTER_BASELINE_CANCEL_REQUEST_REPETITION_EVALUATION)
    elif kind is OrchestratorState.AWAITING_RUN_INITIALIZATION:
        repetition = _active_repetition(state)
        if status != "PRODUCED" or not _verified_produced_candidate(state, event):
            state = replace(_fail(state, OrchestrationFailureClass.RUN_INITIALIZATION_FAILURE), halt_after_closure=True, kind=OrchestratorState.AWAITING_REPETITION_EVALUATION)
            state, command = _issue(state, CommandKind.REQUEST_REPETITION_EVALUATION)
            commands = (command,)
        elif repetition is not None and repetition.execution_mode is ExecutionMode.PURE_EVALUATION:
            state = _retain(state, "run_manifest", event.payload.get("candidate"))
            state = replace(state, run_id=str(event.payload.get("run_id")), kind=OrchestratorState.AWAITING_REPETITION_EVALUATION)
            state, command = _issue(state, CommandKind.REQUEST_REPETITION_EVALUATION)
            commands = (command,)
        else:
            state = _retain(state, "run_manifest", event.payload.get("candidate"))
            state = replace(state, run_id=str(event.payload.get("run_id")))
            state, commands = _arm_watchdog(state, DeadlineKind.RUN, WatchdogContinuation.AFTER_RUN_ARM_REQUEST_FAULT_OR_SCRIPT)
    elif kind is OrchestratorState.AWAITING_FAULT_APPLY:
        if status == "ACTIVE":
            state = _retain(state, "fault_apply_result", event.payload)
            state = replace(state, fault_controller=fault_transition(state.fault_controller, "ACTIVE"), kind=OrchestratorState.AWAITING_SCRIPT_PLAN)
            command_kind = CommandKind.REQUEST_BUDGET_PROBE if _active_case(state) and _active_case(state).case_id == "valcase:iv-v2-action-budget-termination" else CommandKind.REQUEST_SCRIPT_PLAN
            state, command = _issue(state, command_kind)
            commands = (command,)
        else:
            state = _fail(state, OrchestrationFailureClass.FAULT_APPLY_FAILURE)
            state, commands = _request_termination(state, TerminationCause.INFRASTRUCTURE_FAILURE)
    elif kind is OrchestratorState.AWAITING_SCRIPT_PLAN:
        supplied: tuple[RequestedAction, ...] = ()
        withdraw_target: str | None = None
        if status == "PRODUCED" and event.kind is EventKind.SCRIPT_PLAN_RESULT:
            try:
                supplied, withdraw_target = _validated_script_plan(state, event.payload.get("script_plan"))
                state = _retain(state, "script_plan", event.payload.get("script_plan"))
            except ValueError:
                state = _fail(state, OrchestrationFailureClass.ACTOR_INTERFACE_FAILURE)
        elif status == "PRODUCED":
            if _active_case(state) is None or _active_case(state).case_id != "valcase:iv-v2-action-budget-termination":
                state = _fail(state, OrchestrationFailureClass.ACTOR_INTERFACE_FAILURE)
            else:
                supplied = event.payload.get("actions", ())
        state = admit_action_queue(state, supplied, actor_selected=event.kind is EventKind.SCRIPT_PLAN_RESULT)
        state = _retain(
            state,
            "actor_selected_queue",
            event.kind is EventKind.SCRIPT_PLAN_RESULT,
        )
        if withdraw_target is not None and OrchestrationFailureClass.ACTOR_INTERFACE_FAILURE not in state.failure_classes:
            lifecycle_directive_plan(ScriptOperation.WITHDRAW, target_action_id=withdraw_target)
            state = _retain(state, "withdraw_target_action_id", withdraw_target)
        if status != "PRODUCED" or OrchestrationFailureClass.ACTOR_INTERFACE_FAILURE in state.failure_classes:
            state, commands = _request_termination(state, TerminationCause.RUN_INVALIDATION)
        else:
            state, commands = _advance_script(state)
    elif kind is OrchestratorState.AWAITING_AUTHORIZATION:
        decision = event.payload.get("decision")
        if not isinstance(decision, AuthorizationDecision):
            state = _fail(state, OrchestrationFailureClass.AUTHORIZATION_INTERFACE_FAILURE)
            state, commands = _request_termination(state, TerminationCause.RUN_INVALIDATION)
        elif decision.result is AuthorizationResult.APPROVAL_REQUIRED:
            state = _retain(state, "authorization", decision)
            state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_APPROVAL), CommandKind.REQUEST_APPROVAL, frozen_payload(authorization=decision), action_id=decision.action_id)
            commands = (command,)
        else:
            state = _retain(state, "authorization", decision)
            state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_CONTROL), CommandKind.REQUEST_CONTROL_DECISION, frozen_payload(authorization=decision), action_id=decision.action_id)
            commands = (command,)
    elif kind is OrchestratorState.AWAITING_APPROVAL:
        decision = event.payload.get("decision")
        if not isinstance(decision, ApprovalDecision):
            state = _fail(state, OrchestrationFailureClass.APPROVAL_INTERFACE_FAILURE)
            state, commands = _request_termination(state, TerminationCause.RUN_INVALIDATION)
        else:
            posture = "AUTHORIZED" if decision.result is ApprovalResult.APPROVED else ("UNAUTHORIZED" if decision.result in {ApprovalResult.REJECTED, ApprovalResult.EXPIRED, ApprovalResult.TIMED_OUT} else "INDETERMINATE")
            state = _retain(state, "approval", decision)
            state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_CONTROL), CommandKind.REQUEST_CONTROL_DECISION, frozen_payload(approval=decision, posture=posture), action_id=decision.action_id)
            commands = (command,)
    elif kind is OrchestratorState.AWAITING_CONTROL:
        decision = event.payload.get("decision")
        repetition = _active_repetition(state)
        control_condition = dict(repetition.scheduled_run).get("control_condition_id") if repetition else None
        expected_layer = {
            "ctrlcond:iv-core-m1": "M1",
            "ctrlcond:iv-core-m2": "M2",
            "ctrlcond:iv-core-m3": "M3",
        }.get(control_condition)
        if not isinstance(decision, ControlDecision) or decision.control_layer.value != expected_layer:
            state = _fail(state, OrchestrationFailureClass.CONTROL_INTERFACE_FAILURE)
            state, commands = _request_termination(state, TerminationCause.RUN_INVALIDATION)
        elif decision.result is ControlResult.PROCEED:
            state = _retain(state, "control", decision)
            state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_EXECUTION_RESULT), CommandKind.REQUEST_EXECUTION, frozen_payload(control=decision), action_id=decision.action_id)
            commands = (command,)
        else:
            cause = NonexecutionCause.CONTROL_BLOCKED if decision.result is ControlResult.BLOCK else NonexecutionCause.PRECONDITION_UNMET
            state = _retain(state, "control", decision)
            state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_NONEXECUTION_RESULT), CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, frozen_payload(cause=cause, control=decision), action_id=decision.action_id)
            commands = (command,)
    elif kind is OrchestratorState.AWAITING_EXECUTION_RESULT:
        if status is ExecutionStatus.ATTEMPTED or status == "ATTEMPTED":
            if _last_retained(state, "execution_attempt") is not None:
                state, findings = _finding(
                    state,
                    FindingCode.STALE_CORRELATED_EVENT,
                    event,
                    "the execution command already retained its one ATTEMPTED notification",
                )
                return state, (), findings
            state = _retain(state, "execution_attempt", event.payload)
        elif status in {ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED, ExecutionStatus.NOT_ATTEMPTED, "SUCCEEDED", "FAILED", "NOT_ATTEMPTED"}:
            state = _retain(state, "execution_result", event.payload)
            state = replace(state, action_cursor=state.action_cursor + 1)
            state, commands = _advance_script(state)
        else:
            state, commands = _request_termination(_fail(state, OrchestrationFailureClass.EXECUTION_INTERFACE_FAILURE), TerminationCause.RUN_INVALIDATION)
    elif kind is OrchestratorState.AWAITING_NONEXECUTION_RESULT:
        cause = event.payload.get("cause")
        if status not in {ExecutionStatus.NOT_ATTEMPTED, "NOT_ATTEMPTED"} or not event.payload.get("evidence_reference"):
            state, commands = _request_termination(_fail(state, OrchestrationFailureClass.EXECUTION_INTERFACE_FAILURE), TerminationCause.RUN_INVALIDATION)
        elif cause in {NonexecutionCause.PRECONDITION_UNMET, "PRECONDITION_UNMET"}:
            state = replace(_retain(state, "nonexecution", event.payload), action_cursor=state.action_cursor + 1)
            state, commands = _request_termination(state, TerminationCause.RUN_INVALIDATION)
        elif cause in {NonexecutionCause.AGENT_WITHDREW, "AGENT_WITHDREW"}:
            state = replace(_retain(state, "nonexecution", event.payload), action_cursor=state.action_cursor + 1)
            state, commands = _request_termination(state, TerminationCause.AGENT_ABORT)
        else:
            state = replace(_retain(state, "nonexecution", event.payload), action_cursor=state.action_cursor + 1)
            state, commands = _advance_script(state)
    elif kind is OrchestratorState.AWAITING_TERMINATION:
        state = _retain(state, "termination", event.payload if status == "OBSERVED" else None)
        if status != "OBSERVED":
            state = _fail(state, OrchestrationFailureClass.TERMINATION_INTERFACE_FAILURE)
        state, commands = _cancel_watchdog(state, DeadlineKind.RUN, WatchdogContinuation.AFTER_RUN_CANCEL_ARM_DRAIN)
    elif kind is OrchestratorState.AWAITING_DRAIN_READY:
        if status != "READY_FOR_RESET":
            state = _fail(state, OrchestrationFailureClass.DRAIN_FAILURE)
        if state.fault_controller.state is FaultState.ACTIVE:
            controller = fault_transition(state.fault_controller, "REQUEST_REMOVE")
            state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_FAULT_REMOVAL, fault_controller=controller), CommandKind.REQUEST_FAULT_REMOVAL)
            commands = (command,)
        else:
            state, commands = _arm_watchdog(state, DeadlineKind.RESET, WatchdogContinuation.AFTER_RESET_ARM_REQUEST_RESET)
    elif kind is OrchestratorState.AWAITING_FAULT_REMOVAL:
        controller = fault_transition(state.fault_controller, str(status))
        state = replace(state, fault_controller=controller)
        if controller.state is FaultState.FAILED:
            state = replace(_fail(state, OrchestrationFailureClass.FAULT_REMOVAL_FAILURE), fresh_s0_required=True)
        state, commands = _arm_watchdog(state, DeadlineKind.RESET, WatchdogContinuation.AFTER_RESET_ARM_REQUEST_RESET)
    elif kind is OrchestratorState.AWAITING_RESET_RESULT:
        reset_event = "COMPLETED" if status == "COMPLETED" else ("UNKNOWN" if status == "UNKNOWN" else "FAILED")
        state = _retain(state, "reset_result", event.payload)
        state = replace(state, reset_controller=reset_transition(state.reset_controller, reset_event), kind=OrchestratorState.AWAITING_RESET_OBSERVATION)
        if reset_event != "COMPLETED":
            failure = OrchestrationFailureClass.RESET_UNKNOWN if reset_event == "UNKNOWN" else OrchestrationFailureClass.RESET_COMMAND_FAILURE
            state = replace(_fail(state, failure), fresh_s0_required=True)
        state, command = _issue(state, CommandKind.REQUEST_RESET_OBSERVATION)
        commands = (command,)
    elif kind is OrchestratorState.AWAITING_RESET_OBSERVATION:
        controller = reset_transition(state.reset_controller, str(status))
        state = _retain(replace(state, reset_controller=controller), "reset_observation", event.payload)
        if controller.state is ResetState.MISMATCH:
            state = replace(_fail(state, OrchestrationFailureClass.RESET_MISMATCH), fresh_s0_required=True)
        elif controller.state is ResetState.UNKNOWN:
            state = replace(_fail(state, OrchestrationFailureClass.RESET_UNKNOWN), fresh_s0_required=True)
        elif controller.state is ResetState.FAILED or state.fault_controller.state is FaultState.FAILED:
            if OrchestrationFailureClass.RESET_COMMAND_FAILURE not in state.failure_classes:
                state = _fail(state, OrchestrationFailureClass.RESET_COMMAND_FAILURE)
            state = replace(state, fresh_s0_required=True)
        state, commands = _cancel_watchdog(state, DeadlineKind.RESET, WatchdogContinuation.AFTER_RESET_CANCEL_ROUTE_COLLECTION)
    elif kind is OrchestratorState.AWAITING_COLLECTION_CLOSURE:
        if status != "CLOSED":
            state = _fail(state, OrchestrationFailureClass.COLLECTION_CLOSURE_FAILURE)
        state = _retain(state, "collection", event.payload)
        drain = next((slot for slot in state.watchdog_slots if slot.key.kind is DeadlineKind.EVIDENCE_DRAIN and slot.state is WatchdogState.ARMED), None)
        if drain:
            state, commands = _cancel_watchdog(state, DeadlineKind.EVIDENCE_DRAIN, WatchdogContinuation.AFTER_DRAIN_CANCEL_REQUEST_NORMALIZATION)
        else:
            state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_NORMALIZATION), CommandKind.REQUEST_NORMALIZATION)
            commands = (command,)
    elif kind is OrchestratorState.AWAITING_NORMALIZATION:
        if status != "ACCEPTED":
            state = _fail(state, OrchestrationFailureClass.NORMALIZATION_FAILURE)
        state = _retain(state, "normalization", event.payload)
        if state.action_queue:
            state, commands = _request_action_evaluation_or_skip(
                replace(
                    state,
                    kind=OrchestratorState.AWAITING_ACTION_DERIVATION,
                    action_cursor=0,
                ),
                context,
                0,
            )
        else:
            state, commands = _request_run_aggregation_or_continue(state, context)
    elif kind is OrchestratorState.AWAITING_ACTION_DERIVATION:
        candidate = event.payload.get("candidate")
        if status == "PRODUCED" and _verified_produced_candidate(state, event):
            state = _retain(state, "action_artifact", candidate)
            if candidate.get("terminal_outcome") == ActionOutcome.UNAUTHORIZED_EXECUTED.value:
                state = _retain(state, "sticky_unauthorized_execution", candidate)
        else:
            state = _fail(state, OrchestrationFailureClass.ACTION_EVALUATOR_FAILURE)
            state = _retain(state, "action_artifact_missing", event.action_id)
        next_index = state.action_cursor + 1
        if next_index < len(state.action_queue):
            state, commands = _request_action_evaluation_or_skip(
                replace(state, action_cursor=next_index),
                context,
                next_index,
            )
        else:
            state, commands = _request_run_aggregation_or_continue(
                replace(state, action_cursor=next_index),
                context,
            )
    elif kind is OrchestratorState.AWAITING_RUN_AGGREGATION:
        if status == "PRODUCED" and _verified_produced_candidate(state, event):
            state = _retain(state, "run_artifact", event.payload.get("candidate"))
        else:
            state = _fail(state, OrchestrationFailureClass.RUN_AGGREGATOR_FAILURE)
            state = _retain(state, "run_artifact_missing", True)
        state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_REPETITION_EVALUATION), CommandKind.REQUEST_REPETITION_EVALUATION)
        commands = (command,)
    elif kind is OrchestratorState.AWAITING_REPETITION_EVALUATION:
        state = _retain(state, "repetition_result", event.payload)
        case = _active_case(state)
        if state.halt_after_closure or state.fresh_s0_required or case is None or state.repetition_cursor + 1 >= len(case.repetitions):
            state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_CASE_EVALUATION), CommandKind.REQUEST_CASE_EVALUATION)
            commands = (command,)
        else:
            state = replace(state, repetition_cursor=state.repetition_cursor + 1)
            state, commands = _dispatch_schedule(state)
    elif kind is OrchestratorState.AWAITING_CASE_EVALUATION:
        state = _retain(state, "case_result", event.payload)
        if state.halt_after_closure or state.fresh_s0_required or state.case_cursor + 1 >= len(state.schedule.cases):
            if state.halt_after_closure or state.fresh_s0_required:
                state = _retain_unreached_cases(state)
            state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_ACCEPTANCE), CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE)
            commands = (command,)
        else:
            state = replace(state, case_cursor=state.case_cursor + 1, repetition_cursor=0)
            state, commands = _dispatch_schedule(state)
    elif kind is OrchestratorState.AWAITING_ACCEPTANCE:
        if status != "PRODUCED" or not _verified_produced_candidate(state, event):
            return replace(_fail(state, OrchestrationFailureClass.ACCEPTANCE_PRODUCER_FAILURE), kind=OrchestratorState.HALTED), (), ()
        state = _retain(state, "acceptance", event.payload.get("candidate"))
        terminal = OrchestratorState.BLOCKED_FRESH_S0 if state.fresh_s0_required else (OrchestratorState.HALTED if state.halt_after_closure else OrchestratorState.COMPLETED)
        state = replace(state, kind=terminal)
    return state, commands, ()


def _action_artifact_id(context: TrustedOrchestrationContext, state: ValidationOrchestratorState, action_id: str) -> str:
    case = _active_case(state)
    repetition = _active_repetition(state)
    key = (case.case_id if case else "", repetition.repetition_id if repetition else "", action_id)
    matches = [artifact_id for case_id, rep_id, candidate_action_id, artifact_id in context.artifact_ids.action_ids if (case_id, rep_id, candidate_action_id) == key]
    if len(matches) != 1:
        raise ValueError("opaque action artifact ID plan is incomplete or ambiguous")
    return matches[0]


def _run_artifact_id(context: TrustedOrchestrationContext, state: ValidationOrchestratorState) -> str:
    case = _active_case(state)
    repetition = _active_repetition(state)
    matches = [artifact_id for case_id, rep_id, artifact_id in context.artifact_ids.run_ids if case and repetition and (case_id, rep_id) == (case.case_id, repetition.repetition_id)]
    if len(matches) != 1:
        raise ValueError("opaque run artifact ID plan is incomplete or ambiguous")
    return matches[0]


def _request_run_aggregation_or_continue(
    state: ValidationOrchestratorState,
    context: TrustedOrchestrationContext,
) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...]]:
    """Request G4 run aggregation or retain missing producer identity."""

    try:
        proposed_id = _run_artifact_id(context, state)
    except ValueError:
        state = _fail(state, OrchestrationFailureClass.INTERNAL_INVARIANT_VIOLATION)
        state = _retain(state, "run_artifact_missing", "opaque_run_artifact_id")
        state, command = _issue(
            replace(
                state,
                kind=OrchestratorState.AWAITING_REPETITION_EVALUATION,
                halt_after_closure=True,
            ),
            CommandKind.REQUEST_REPETITION_EVALUATION,
        )
        return state, (command,)
    state, command = _issue(
        replace(state, kind=OrchestratorState.AWAITING_RUN_AGGREGATION),
        CommandKind.REQUEST_RUN_AGGREGATION,
        frozen_payload(proposed_artifact_id=proposed_id),
    )
    return state, (command,)


def _request_action_evaluation_or_skip(
    state: ValidationOrchestratorState,
    context: TrustedOrchestrationContext,
    action_index: int,
) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...]]:
    """Request each canonical G4 action evaluation with explicit ID missingness."""

    while action_index < len(state.action_queue):
        action = state.action_queue[action_index]
        try:
            proposed_id = _action_artifact_id(context, state, action.action_id)
        except ValueError:
            state = _fail(state, OrchestrationFailureClass.INTERNAL_INVARIANT_VIOLATION)
            state = _retain(state, "action_artifact_missing", action.action_id)
            state = replace(
                state,
                action_cursor=action_index + 1,
                halt_after_closure=True,
            )
            action_index += 1
            continue
        state, command = _issue(
            replace(
                state,
                kind=OrchestratorState.AWAITING_ACTION_DERIVATION,
                action_cursor=action_index,
            ),
            CommandKind.REQUEST_ACTION_EVALUATION,
            frozen_payload(
                proposed_artifact_id=proposed_id,
                derivation_sequence=action_index + 1,
            ),
            action_id=action.action_id,
        )
        return state, (command,)
    return _request_run_aggregation_or_continue(state, context)


def _handle_watchdog_control(state: ValidationOrchestratorState, event: OrchestrationEvent) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...]]:
    operation = event.payload.get("operation")
    status = event.payload.get("status")
    key = event.payload.get("deadline_key")
    command = next((item for item in state.completed_commands if item.command_ordinal == event.correlation_command_ordinal), None)
    if command is None or command.kind not in {CommandKind.ARM_WATCHDOG, CommandKind.CANCEL_WATCHDOG}:
        return replace(_fail(state, OrchestrationFailureClass.COMMAND_CORRELATION_INVALID), kind=OrchestratorState.HALTED), ()
    continuation = next(
        (
            value
            for continuation_key, value in reversed(state.watchdog_continuations)
            if continuation_key == key
        ),
        None,
    )
    commanded_key = command.payload.get("deadline_key")
    commanded_operation = WatchdogOperation.ARM if command.kind is CommandKind.ARM_WATCHDOG else WatchdogOperation.CANCEL
    if key != commanded_key or operation not in {commanded_operation, getattr(commanded_operation, "value", None)}:
        return replace(_fail(state, OrchestrationFailureClass.COMMAND_CORRELATION_INVALID), kind=OrchestratorState.HALTED), ()
    if continuation is None:
        return replace(_fail(state, OrchestrationFailureClass.INTERNAL_INVARIANT_VIOLATION), kind=OrchestratorState.HALTED), ()
    slot = next((item for item in state.watchdog_slots if item.key == key), None)
    if slot is None:
        return replace(_fail(state, OrchestrationFailureClass.WATCHDOG_INTERFACE_FAILURE), kind=OrchestratorState.HALTED), ()
    if status != "ACKNOWLEDGED":
        failed = watchdog_transition(slot, "FAIL", key)
        state = replace(
            _fail(state, OrchestrationFailureClass.WATCHDOG_INTERFACE_FAILURE),
            watchdog_slots=tuple(failed if item == slot else item for item in state.watchdog_slots),
            watchdog_continuations=tuple(
                item for item in state.watchdog_continuations if item != (key, continuation)
            ),
        )
        if key.kind is DeadlineKind.RESET:
            state = replace(state, fresh_s0_required=True)
        continuation = WatchdogContinuation(continuation)
        if continuation is WatchdogContinuation.AFTER_BASELINE_ARM_REQUEST_BASELINE:
            return replace(state, kind=OrchestratorState.BLOCKED_FRESH_S0, fresh_s0_required=True), ()
        if continuation is WatchdogContinuation.AFTER_BASELINE_CANCEL_REQUEST_RUN_INITIALIZATION:
            return replace(state, kind=OrchestratorState.BLOCKED_FRESH_S0, fresh_s0_required=True), ()
        if continuation is WatchdogContinuation.AFTER_BASELINE_CANCEL_REQUEST_REPETITION_EVALUATION:
            state, result_command = _issue(replace(state, kind=OrchestratorState.AWAITING_REPETITION_EVALUATION, fresh_s0_required=True), CommandKind.REQUEST_REPETITION_EVALUATION)
            return state, (result_command,)
        if key.kind is DeadlineKind.RUN:
            return _request_termination(state, TerminationCause.RUN_INVALIDATION)
        if continuation is WatchdogContinuation.AFTER_RUN_CANCEL_ARM_DRAIN:
            return _arm_watchdog(replace(state, halt_after_closure=True), DeadlineKind.EVIDENCE_DRAIN, WatchdogContinuation.AFTER_DRAIN_ARM_REQUEST_DRAIN)
        if continuation is WatchdogContinuation.AFTER_DRAIN_ARM_REQUEST_DRAIN:
            state, result_command = _issue(replace(state, kind=OrchestratorState.AWAITING_DRAIN_READY, halt_after_closure=True), CommandKind.REQUEST_EVIDENCE_DRAIN)
            return state, (result_command,)
        if continuation is WatchdogContinuation.AFTER_DRAIN_CANCEL_REQUEST_NORMALIZATION:
            state, result_command = _issue(replace(state, kind=OrchestratorState.AWAITING_NORMALIZATION, halt_after_closure=True), CommandKind.REQUEST_NORMALIZATION)
            return state, (result_command,)
        if continuation is WatchdogContinuation.AFTER_RESET_ARM_REQUEST_RESET:
            state, result_command = _issue(replace(state, kind=OrchestratorState.AWAITING_RESET_RESULT, fresh_s0_required=True, reset_controller=reset_transition(state.reset_controller, "REQUEST")), CommandKind.REQUEST_RESET)
            return state, (result_command,)
        if continuation is WatchdogContinuation.AFTER_RESET_CANCEL_ROUTE_COLLECTION:
            state = replace(state, fresh_s0_required=True)
    else:
        op = "ACK_ARM" if operation in {WatchdogOperation.ARM, "ARM"} else "ACK_CANCEL"
        updated = watchdog_transition(slot, op, key)
        state = replace(
            state,
            watchdog_slots=tuple(updated if item == slot else item for item in state.watchdog_slots),
            watchdog_continuations=tuple(
                item for item in state.watchdog_continuations if item != (key, continuation)
            ),
        )
    continuation = WatchdogContinuation(continuation)
    if continuation is WatchdogContinuation.AFTER_BASELINE_ARM_REQUEST_BASELINE:
        state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_BASELINE), CommandKind.REQUEST_BASELINE_VERIFICATION)
        return state, (command,)
    if continuation is WatchdogContinuation.AFTER_BASELINE_CANCEL_REQUEST_RUN_INITIALIZATION:
        repetition = _active_repetition(state)
        state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_RUN_INITIALIZATION), CommandKind.REQUEST_RUN_INITIALIZATION, frozen_payload(scheduled_run=repetition.scheduled_run if repetition else ()))
        return state, (command,)
    if continuation is WatchdogContinuation.AFTER_BASELINE_CANCEL_REQUEST_REPETITION_EVALUATION:
        state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_REPETITION_EVALUATION), CommandKind.REQUEST_REPETITION_EVALUATION)
        return state, (command,)
    if continuation is WatchdogContinuation.AFTER_RUN_ARM_REQUEST_FAULT_OR_SCRIPT:
        repetition = _active_repetition(state)
        if repetition and repetition.fault_class:
            controller = fault_transition(state.fault_controller, "REQUEST_APPLY")
            state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_FAULT_APPLY, fault_controller=controller), CommandKind.REQUEST_FAULT_APPLY, frozen_payload(fault_class=repetition.fault_class))
        else:
            state = replace(state, fault_controller=fault_transition(state.fault_controller, "NO_FAULT"), kind=OrchestratorState.AWAITING_SCRIPT_PLAN)
            command_kind = CommandKind.REQUEST_BUDGET_PROBE if _active_case(state) and _active_case(state).case_id == "valcase:iv-v2-action-budget-termination" else CommandKind.REQUEST_SCRIPT_PLAN
            state, command = _issue(state, command_kind)
        return state, (command,)
    if continuation is WatchdogContinuation.AFTER_RUN_CANCEL_ARM_DRAIN:
        return _arm_watchdog(state, DeadlineKind.EVIDENCE_DRAIN, WatchdogContinuation.AFTER_DRAIN_ARM_REQUEST_DRAIN)
    if continuation is WatchdogContinuation.AFTER_DRAIN_ARM_REQUEST_DRAIN:
        state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_DRAIN_READY), CommandKind.REQUEST_EVIDENCE_DRAIN)
        return state, (command,)
    if continuation is WatchdogContinuation.AFTER_DRAIN_CANCEL_REQUEST_NORMALIZATION:
        state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_NORMALIZATION), CommandKind.REQUEST_NORMALIZATION)
        return state, (command,)
    if continuation is WatchdogContinuation.AFTER_RESET_ARM_REQUEST_RESET:
        state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_RESET_RESULT, reset_controller=reset_transition(state.reset_controller, "REQUEST")), CommandKind.REQUEST_RESET)
        return state, (command,)
    if continuation is WatchdogContinuation.AFTER_RESET_CANCEL_ROUTE_COLLECTION:
        drain_fired = any(slot.key.kind is DeadlineKind.EVIDENCE_DRAIN and slot.state is WatchdogState.FIRED for slot in state.watchdog_slots)
        next_kind = CommandKind.REQUEST_NORMALIZATION if drain_fired else CommandKind.REQUEST_COLLECTION_CLOSURE
        next_state = OrchestratorState.AWAITING_NORMALIZATION if drain_fired else OrchestratorState.AWAITING_COLLECTION_CLOSURE
        state, command = _issue(replace(state, kind=next_state), next_kind)
        return state, (command,)
    raise AssertionError("closed watchdog continuation exhausted")


def _handle_timeout(state: ValidationOrchestratorState, event: OrchestrationEvent) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...]]:
    key = event.payload.get("deadline_key")
    slot = next((item for item in state.watchdog_slots if item.key == key), None)
    if slot is None or slot.state is not WatchdogState.ARMED:
        return state, ()
    fired = watchdog_transition(slot, "FIRE", key)
    state = replace(state, watchdog_slots=tuple(fired if item == slot else item for item in state.watchdog_slots))
    if key.kind is DeadlineKind.RUN:
        state = _cancel_outstanding(
            state,
            frozenset(
                {
                    CommandKind.REQUEST_FAULT_APPLY,
                    CommandKind.REQUEST_SCRIPT_PLAN,
                    CommandKind.REQUEST_BUDGET_PROBE,
                    CommandKind.REQUEST_AUTHORIZATION,
                    CommandKind.REQUEST_APPROVAL,
                    CommandKind.REQUEST_CONTROL_DECISION,
                    CommandKind.REQUEST_EXECUTION,
                    CommandKind.REQUEST_NONEXECUTION_CONFIRMATION,
                    CommandKind.REQUEST_TERMINATION,
                }
            ),
        )
        state = _fail(state, OrchestrationFailureClass.RUN_TIMEOUT)
        return _request_termination(state, TerminationCause.TIMEOUT)
    if key.kind is DeadlineKind.EVIDENCE_DRAIN:
        state = _cancel_outstanding(
            state,
            frozenset(
                {
                    CommandKind.REQUEST_EVIDENCE_DRAIN,
                    CommandKind.REQUEST_COLLECTION_CLOSURE,
                }
            ),
        )
        state = _fail(state, OrchestrationFailureClass.DRAIN_TIMEOUT)
        state = _retain(state, "collection_missing", True)
        if state.kind is OrchestratorState.AWAITING_COLLECTION_CLOSURE:
            state, command = _issue(
                replace(state, kind=OrchestratorState.AWAITING_NORMALIZATION),
                CommandKind.REQUEST_NORMALIZATION,
            )
            return state, (command,)
        if state.kind is OrchestratorState.AWAITING_WATCHDOG_CONTROL and any(
            command.kind in {CommandKind.ARM_WATCHDOG, CommandKind.CANCEL_WATCHDOG}
            for command in state.outstanding_commands
        ):
            return state, ()
        if state.kind in {OrchestratorState.AWAITING_RESET_RESULT, OrchestratorState.AWAITING_RESET_OBSERVATION}:
            return state, ()
        if state.kind is OrchestratorState.AWAITING_FAULT_REMOVAL:
            state = _cancel_outstanding(
                state,
                frozenset({CommandKind.REQUEST_FAULT_REMOVAL}),
            )
            state = replace(
                _fail(state, OrchestrationFailureClass.FAULT_REMOVAL_FAILURE),
                fault_controller=fault_transition(state.fault_controller, "UNKNOWN"),
                fresh_s0_required=True,
            )
            return _arm_watchdog(
                state,
                DeadlineKind.RESET,
                WatchdogContinuation.AFTER_RESET_ARM_REQUEST_RESET,
            )
        if state.fault_controller.state is FaultState.ACTIVE:
            controller = fault_transition(state.fault_controller, "REQUEST_REMOVE")
            state, command = _issue(replace(state, kind=OrchestratorState.AWAITING_FAULT_REMOVAL, fault_controller=controller), CommandKind.REQUEST_FAULT_REMOVAL)
            return state, (command,)
        return _arm_watchdog(state, DeadlineKind.RESET, WatchdogContinuation.AFTER_RESET_ARM_REQUEST_RESET)
    state = _cancel_outstanding(
        state,
        frozenset({CommandKind.REQUEST_RESET, CommandKind.REQUEST_RESET_OBSERVATION}),
    )
    state = replace(
        _fail(state, OrchestrationFailureClass.RESET_TIMEOUT),
        fresh_s0_required=True,
    )
    if state.kind is OrchestratorState.AWAITING_BASELINE:
        state, command = _issue(
            replace(state, kind=OrchestratorState.AWAITING_REPETITION_EVALUATION),
            CommandKind.REQUEST_REPETITION_EVALUATION,
        )
        return state, (command,)
    if state.kind is OrchestratorState.AWAITING_RESET_RESULT:
        state = _retain(state, "reset_result_missing", True)
        controller = reset_transition(state.reset_controller, "TIMEOUT")
        state, command = _issue(
            replace(
                state,
                kind=OrchestratorState.AWAITING_RESET_OBSERVATION,
                reset_controller=controller,
            ),
            CommandKind.REQUEST_RESET_OBSERVATION,
        )
        return state, (command,)
    state = _retain(state, "reset_observation_missing", True)
    drain_fired = any(
        slot.key.kind is DeadlineKind.EVIDENCE_DRAIN
        and slot.state is WatchdogState.FIRED
        for slot in state.watchdog_slots
    )
    next_kind = (
        OrchestratorState.AWAITING_NORMALIZATION
        if drain_fired
        else OrchestratorState.AWAITING_COLLECTION_CLOSURE
    )
    next_command = (
        CommandKind.REQUEST_NORMALIZATION
        if drain_fired
        else CommandKind.REQUEST_COLLECTION_CLOSURE
    )
    state, command = _issue(replace(state, kind=next_kind), next_command)
    return state, (command,)


def _handle_command_failure(
    state: ValidationOrchestratorState,
    event: OrchestrationEvent,
    context: TrustedOrchestrationContext,
) -> tuple[ValidationOrchestratorState, tuple[OrchestrationCommand, ...]]:
    failed = event.payload.get("command_kind")
    command_kind = failed if isinstance(failed, CommandKind) else CommandKind(failed)
    failure_by_command = {
        CommandKind.REQUEST_BASELINE_VERIFICATION: OrchestrationFailureClass.RESET_COMMAND_FAILURE,
        CommandKind.REQUEST_RUN_INITIALIZATION: OrchestrationFailureClass.RUN_INITIALIZATION_FAILURE,
        CommandKind.REQUEST_FAULT_APPLY: OrchestrationFailureClass.FAULT_APPLY_FAILURE,
        CommandKind.REQUEST_SCRIPT_PLAN: OrchestrationFailureClass.ACTOR_INTERFACE_FAILURE,
        CommandKind.REQUEST_BUDGET_PROBE: OrchestrationFailureClass.ACTOR_INTERFACE_FAILURE,
        CommandKind.REQUEST_AUTHORIZATION: OrchestrationFailureClass.AUTHORIZATION_INTERFACE_FAILURE,
        CommandKind.REQUEST_APPROVAL: OrchestrationFailureClass.APPROVAL_INTERFACE_FAILURE,
        CommandKind.REQUEST_CONTROL_DECISION: OrchestrationFailureClass.CONTROL_INTERFACE_FAILURE,
        CommandKind.REQUEST_EXECUTION: OrchestrationFailureClass.EXECUTION_INTERFACE_FAILURE,
        CommandKind.REQUEST_NONEXECUTION_CONFIRMATION: OrchestrationFailureClass.EXECUTION_INTERFACE_FAILURE,
        CommandKind.REQUEST_TERMINATION: OrchestrationFailureClass.TERMINATION_INTERFACE_FAILURE,
        CommandKind.REQUEST_EVIDENCE_DRAIN: OrchestrationFailureClass.DRAIN_FAILURE,
        CommandKind.REQUEST_FAULT_REMOVAL: OrchestrationFailureClass.FAULT_REMOVAL_FAILURE,
        CommandKind.REQUEST_RESET: OrchestrationFailureClass.RESET_COMMAND_FAILURE,
        CommandKind.REQUEST_RESET_OBSERVATION: OrchestrationFailureClass.RESET_UNKNOWN,
        CommandKind.REQUEST_COLLECTION_CLOSURE: OrchestrationFailureClass.COLLECTION_CLOSURE_FAILURE,
        CommandKind.REQUEST_NORMALIZATION: OrchestrationFailureClass.NORMALIZATION_FAILURE,
        CommandKind.REQUEST_ACTION_EVALUATION: OrchestrationFailureClass.ACTION_EVALUATOR_FAILURE,
        CommandKind.REQUEST_RUN_AGGREGATION: OrchestrationFailureClass.RUN_AGGREGATOR_FAILURE,
        CommandKind.REQUEST_REPETITION_EVALUATION: OrchestrationFailureClass.CASE_EVALUATOR_FAILURE,
        CommandKind.REQUEST_CASE_EVALUATION: OrchestrationFailureClass.CASE_EVALUATOR_FAILURE,
        CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE: OrchestrationFailureClass.ACCEPTANCE_PRODUCER_FAILURE,
        CommandKind.ARM_WATCHDOG: OrchestrationFailureClass.WATCHDOG_INTERFACE_FAILURE,
        CommandKind.CANCEL_WATCHDOG: OrchestrationFailureClass.WATCHDOG_INTERFACE_FAILURE,
    }
    state = _fail(state, failure_by_command[command_kind])
    answered = _answered_command(state, event)
    if command_kind is CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE:
        return replace(state, kind=OrchestratorState.HALTED), ()
    if command_kind is CommandKind.REQUEST_BASELINE_VERIFICATION:
        state = replace(
            _retain(state, "baseline_missing", True),
            fresh_s0_required=True,
        )
        return _cancel_watchdog(
            state,
            DeadlineKind.RESET,
            WatchdogContinuation.AFTER_BASELINE_CANCEL_REQUEST_REPETITION_EVALUATION,
        )
    if command_kind is CommandKind.REQUEST_RUN_INITIALIZATION:
        state = _retain(state, "run_initialization_missing", True)
        state, command = _issue(
            replace(
                state,
                kind=OrchestratorState.AWAITING_REPETITION_EVALUATION,
                halt_after_closure=True,
            ),
            CommandKind.REQUEST_REPETITION_EVALUATION,
        )
        return state, (command,)
    if command_kind in {
        CommandKind.REQUEST_FAULT_APPLY,
        CommandKind.REQUEST_EXECUTION,
        CommandKind.REQUEST_NONEXECUTION_CONFIRMATION,
    }:
        cause = (
            TerminationCause.INFRASTRUCTURE_FAILURE
            if command_kind
            in {CommandKind.REQUEST_EXECUTION, CommandKind.REQUEST_NONEXECUTION_CONFIRMATION, CommandKind.REQUEST_FAULT_APPLY}
            else TerminationCause.RUN_INVALIDATION
        )
        return _request_termination(state, cause)
    if command_kind is CommandKind.REQUEST_EVIDENCE_DRAIN:
        if state.fault_controller.state is FaultState.ACTIVE:
            controller = fault_transition(state.fault_controller, "REQUEST_REMOVE")
            state, command = _issue(
                replace(
                    state,
                    kind=OrchestratorState.AWAITING_FAULT_REMOVAL,
                    fault_controller=controller,
                ),
                CommandKind.REQUEST_FAULT_REMOVAL,
            )
            return state, (command,)
        return _arm_watchdog(
            state,
            DeadlineKind.RESET,
            WatchdogContinuation.AFTER_RESET_ARM_REQUEST_RESET,
        )
    if command_kind is CommandKind.REQUEST_FAULT_REMOVAL:
        controller = fault_transition(state.fault_controller, "FAILED")
        state = replace(
            state,
            fault_controller=controller,
            fresh_s0_required=True,
        )
        return _arm_watchdog(
            state,
            DeadlineKind.RESET,
            WatchdogContinuation.AFTER_RESET_ARM_REQUEST_RESET,
        )
    if command_kind in {CommandKind.ARM_WATCHDOG, CommandKind.CANCEL_WATCHDOG}:
        if answered is None:
            return replace(
                _fail(state, OrchestrationFailureClass.INTERNAL_INVARIANT_VIOLATION),
                kind=OrchestratorState.HALTED,
            ), ()
        key = answered.payload.get("deadline_key")
        continuation = next(
            (
                value
                for continuation_key, value in reversed(state.watchdog_continuations)
                if continuation_key == key
            ),
            None,
        )
        slot = next((item for item in state.watchdog_slots if item.key == key), None)
        if continuation is None or slot is None:
            return replace(
                _fail(state, OrchestrationFailureClass.INTERNAL_INVARIANT_VIOLATION),
                kind=OrchestratorState.HALTED,
            ), ()
        failed_slot = watchdog_transition(slot, "FAIL", key)
        state = replace(
            state,
            watchdog_slots=tuple(
                failed_slot if item == slot else item for item in state.watchdog_slots
            ),
            watchdog_continuations=tuple(
                item for item in state.watchdog_continuations if item != (key, continuation)
            ),
        )
        if key.kind is DeadlineKind.RESET:
            state = replace(state, fresh_s0_required=True)
        if continuation in {
            WatchdogContinuation.AFTER_BASELINE_ARM_REQUEST_BASELINE,
            WatchdogContinuation.AFTER_BASELINE_CANCEL_REQUEST_RUN_INITIALIZATION,
        }:
            return replace(state, kind=OrchestratorState.BLOCKED_FRESH_S0), ()
        if continuation is WatchdogContinuation.AFTER_BASELINE_CANCEL_REQUEST_REPETITION_EVALUATION:
            state, command = _issue(
                replace(state, kind=OrchestratorState.AWAITING_REPETITION_EVALUATION),
                CommandKind.REQUEST_REPETITION_EVALUATION,
            )
            return state, (command,)
        if continuation is WatchdogContinuation.AFTER_RUN_CANCEL_ARM_DRAIN:
            return _arm_watchdog(
                replace(state, halt_after_closure=True),
                DeadlineKind.EVIDENCE_DRAIN,
                WatchdogContinuation.AFTER_DRAIN_ARM_REQUEST_DRAIN,
            )
        if continuation is WatchdogContinuation.AFTER_DRAIN_ARM_REQUEST_DRAIN:
            state, command = _issue(
                replace(
                    state,
                    kind=OrchestratorState.AWAITING_DRAIN_READY,
                    halt_after_closure=True,
                ),
                CommandKind.REQUEST_EVIDENCE_DRAIN,
            )
            return state, (command,)
        if continuation is WatchdogContinuation.AFTER_DRAIN_CANCEL_REQUEST_NORMALIZATION:
            state, command = _issue(
                replace(state, kind=OrchestratorState.AWAITING_NORMALIZATION),
                CommandKind.REQUEST_NORMALIZATION,
            )
            return state, (command,)
        if continuation is WatchdogContinuation.AFTER_RESET_ARM_REQUEST_RESET:
            state, command = _issue(
                replace(
                    state,
                    kind=OrchestratorState.AWAITING_RESET_RESULT,
                    reset_controller=reset_transition(state.reset_controller, "REQUEST"),
                ),
                CommandKind.REQUEST_RESET,
            )
            return state, (command,)
        if continuation is WatchdogContinuation.AFTER_RESET_CANCEL_ROUTE_COLLECTION:
            drain_fired = any(
                item.key.kind is DeadlineKind.EVIDENCE_DRAIN
                and item.state is WatchdogState.FIRED
                for item in state.watchdog_slots
            )
            next_kind = (
                OrchestratorState.AWAITING_NORMALIZATION
                if drain_fired
                else OrchestratorState.AWAITING_COLLECTION_CLOSURE
            )
            next_command = (
                CommandKind.REQUEST_NORMALIZATION
                if drain_fired
                else CommandKind.REQUEST_COLLECTION_CLOSURE
            )
            state, command = _issue(replace(state, kind=next_kind), next_command)
            return state, (command,)
        return _request_termination(state, TerminationCause.RUN_INVALIDATION)
    if command_kind is CommandKind.REQUEST_RESET:
        controller = reset_transition(state.reset_controller, "FAILED")
        state = _retain(replace(state, reset_controller=controller), "reset_result_missing", True)
        state = replace(state, fresh_s0_required=True, kind=OrchestratorState.AWAITING_RESET_OBSERVATION)
        state, command = _issue(state, CommandKind.REQUEST_RESET_OBSERVATION)
        return state, (command,)
    if command_kind is CommandKind.REQUEST_RESET_OBSERVATION:
        controller = reset_transition(state.reset_controller, "FAILED")
        state = _retain(replace(state, reset_controller=controller), "reset_observation_missing", True)
        state = replace(state, fresh_s0_required=True)
        return _cancel_watchdog(state, DeadlineKind.RESET, WatchdogContinuation.AFTER_RESET_CANCEL_ROUTE_COLLECTION)
    if command_kind is CommandKind.REQUEST_COLLECTION_CLOSURE:
        drain = next(
            (
                slot
                for slot in state.watchdog_slots
                if slot.key.kind is DeadlineKind.EVIDENCE_DRAIN
                and slot.state is WatchdogState.ARMED
            ),
            None,
        )
        if drain is not None:
            return _cancel_watchdog(
                state,
                DeadlineKind.EVIDENCE_DRAIN,
                WatchdogContinuation.AFTER_DRAIN_CANCEL_REQUEST_NORMALIZATION,
            )
        state, command = _issue(
            replace(state, kind=OrchestratorState.AWAITING_NORMALIZATION),
            CommandKind.REQUEST_NORMALIZATION,
        )
        return state, (command,)
    if command_kind is CommandKind.REQUEST_NORMALIZATION:
        state = _retain(state, "normalization_missing", True)
        if state.action_queue:
            return _request_action_evaluation_or_skip(
                replace(
                    state,
                    kind=OrchestratorState.AWAITING_ACTION_DERIVATION,
                    action_cursor=0,
                ),
                context,
                0,
            )
        return _request_run_aggregation_or_continue(state, context)
    if command_kind is CommandKind.REQUEST_ACTION_EVALUATION:
        state = _retain(state, "action_artifact_missing", event.action_id)
        state = replace(state, action_cursor=state.action_cursor + 1)
        if state.action_cursor < len(state.action_queue):
            return _request_action_evaluation_or_skip(
                state,
                context,
                state.action_cursor,
            )
        return _request_run_aggregation_or_continue(state, context)
    if command_kind is CommandKind.REQUEST_RUN_AGGREGATION:
        state = _retain(state, "run_artifact_missing", True)
        state, command = _issue(
            replace(state, kind=OrchestratorState.AWAITING_REPETITION_EVALUATION),
            CommandKind.REQUEST_REPETITION_EVALUATION,
        )
        return state, (command,)
    if command_kind is CommandKind.REQUEST_REPETITION_EVALUATION:
        state = _retain(state, "repetition_result_missing", True)
        state, command = _issue(
            replace(state, kind=OrchestratorState.AWAITING_CASE_EVALUATION),
            CommandKind.REQUEST_CASE_EVALUATION,
        )
        return state, (command,)
    if command_kind is CommandKind.REQUEST_CASE_EVALUATION:
        state = _retain(state, "case_result_missing", _active_case(state).case_id if _active_case(state) else None)
        state = _retain_unreached_cases(state)
        state, command = _issue(
            replace(state, kind=OrchestratorState.AWAITING_ACCEPTANCE),
            CommandKind.REQUEST_INSTRUMENT_ACCEPTANCE,
        )
        return state, (command,)
    if command_kind is CommandKind.REQUEST_TERMINATION:
        return _cancel_watchdog(state, DeadlineKind.RUN, WatchdogContinuation.AFTER_RUN_CANCEL_ARM_DRAIN)
    return _request_termination(replace(state, halt_after_closure=True), TerminationCause.RUN_INVALIDATION)


def transition_matrix() -> Mapping[OrchestratorState, frozenset[EventKind]]:
    """Expose the immutable accepted-event side of the total table for audit."""

    return _ALLOWED_EVENTS


def preserves_unauthorized_execution(state: ValidationOrchestratorState) -> bool:
    """Return whether every retained realized-unauthorized artifact is sticky."""

    sticky = [value for key, value in state.retained if key == "sticky_unauthorized_execution"]
    artifacts = [value for key, value in state.retained if key == "action_artifact"]
    return all(value in artifacts for value in sticky)
