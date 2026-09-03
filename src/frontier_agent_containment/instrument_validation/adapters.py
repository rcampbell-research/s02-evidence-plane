"""Pure IV-G6 inert runtime-adapter contracts.

This module validates frozen IV-G5 commands, constructs immutable provider
request data, validates explicitly supplied provider-result data, and
translates that data into IV-G5 orchestration events.  It never invokes a
provider and performs no runtime, observation, collection, or evidence work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Final, Mapping

from .actor_control_decisions import (
    ApprovalDecision,
    AuthorizationDecision,
    ControlDecision,
    ControlLayer,
    RequestedAction,
)
from .orchestration import (
    CommandKind,
    EventKind,
    FROZEN_FAULT_CATEGORIES,
    FrozenPayload,
    OrchestrationCommand,
    OrchestrationEvent,
    OrchestrationScope,
    ScheduledValidationRepetition,
    WatchdogDeadlineKey,
    frozen_payload,
)


_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_NONEMPTY = re.compile(r"^.+$")


class AdapterFamily(str, Enum):
    BASELINE_OBSERVER = "BASELINE_OBSERVER"
    SCENARIO_INITIALIZATION = "SCENARIO_INITIALIZATION"
    WATCHDOG = "WATCHDOG"
    FAULT_CONTROL = "FAULT_CONTROL"
    EXECUTION = "EXECUTION"
    NONEXECUTION_CONFIRMATION = "NONEXECUTION_CONFIRMATION"
    TERMINATION = "TERMINATION"
    EVIDENCE_DRAIN = "EVIDENCE_DRAIN"
    RESET_PROVIDER = "RESET_PROVIDER"
    RESET_OBSERVER = "RESET_OBSERVER"
    COLLECTION_CLOSURE = "COLLECTION_CLOSURE"


class ComponentOwnership(str, Enum):
    G6_INERT_SURFACE = "G6_INERT_SURFACE"
    NON_G6 = "NON_G6"


class CommandOwnership(str, Enum):
    INTERNAL_PURE = "INTERNAL_PURE"
    G6_ADAPTED = "G6_ADAPTED"
    DEFERRED_RED = "DEFERRED_RED"
    INVALID_FOR_G6 = "INVALID_FOR_G6"


class EventOwnership(str, Enum):
    INTERNAL_PURE = "INTERNAL_PURE"
    G6_TRANSLATED_PROVIDER_RESULT = "G6_TRANSLATED_PROVIDER_RESULT"
    G5_LIFECYCLE_DELIVERY = "G5_LIFECYCLE_DELIVERY"
    DEFERRED_RED = "DEFERRED_RED"
    NOT_G6_OWNED = "NOT_G6_OWNED"


class ProviderResultStatus(str, Enum):
    CLEAN_BASELINE_OBSERVED = "CLEAN_BASELINE_OBSERVED"
    RESET_MISMATCH_OBSERVED = "RESET_MISMATCH_OBSERVED"
    RESET_STATE_UNKNOWN = "RESET_STATE_UNKNOWN"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    PRODUCED = "PRODUCED"
    UNKNOWN = "UNKNOWN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    TIMEOUT = "TIMEOUT"
    ACTIVE = "ACTIVE"
    CLEARED = "CLEARED"
    ATTEMPTED = "ATTEMPTED"
    SUCCEEDED = "SUCCEEDED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    RESULT_UNKNOWN = "RESULT_UNKNOWN"
    OBSERVED = "OBSERVED"
    READY_FOR_RESET = "READY_FOR_RESET"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class AdapterErrorCode(str, Enum):
    COMMAND_NOT_ADAPTED = "COMMAND_NOT_ADAPTED"
    COMMAND_FAMILY_MISMATCH = "COMMAND_FAMILY_MISMATCH"
    REQUEST_CONTRACT_INVALID = "REQUEST_CONTRACT_INVALID"
    RESULT_CONTRACT_INVALID = "RESULT_CONTRACT_INVALID"
    PROVIDER_IDENTITY_INVALID = "PROVIDER_IDENTITY_INVALID"
    PROVIDER_BUILD_INVALID = "PROVIDER_BUILD_INVALID"
    PROVIDER_CHANNEL_INVALID = "PROVIDER_CHANNEL_INVALID"
    COMMAND_CORRELATION_INVALID = "COMMAND_CORRELATION_INVALID"
    SCOPE_BINDING_INVALID = "SCOPE_BINDING_INVALID"
    RESULT_IDENTITY_INVALID = "RESULT_IDENTITY_INVALID"
    STATUS_INVALID = "STATUS_INVALID"
    PAYLOAD_INVALID = "PAYLOAD_INVALID"
    EVENT_IDENTITY_INVALID = "EVENT_IDENTITY_INVALID"


class AdapterContractError(ValueError):
    """Deterministic G6 contract rejection; never a runtime result."""

    def __init__(self, code: AdapterErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class InstrumentConfigurationBinding:
    configuration_id: str
    configuration_version: str
    configuration_digest: str

    def __post_init__(self) -> None:
        if (
            self.configuration_id != "instrument:iv-core"
            or self.configuration_version != "0.1.0"
            or not isinstance(self.configuration_digest, str)
            or not _DIGEST.fullmatch(self.configuration_digest)
        ):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "invalid instrument configuration binding")


@dataclass(frozen=True, slots=True)
class EnvironmentBinding:
    environment_id: str
    environment_version: str
    environment_build_id: str

    def __post_init__(self) -> None:
        _require_nonempty_strings(self.environment_id, self.environment_version, self.environment_build_id)


@dataclass(frozen=True, slots=True)
class S0DeclarationBinding:
    declaration_id: str
    declaration_version: str
    component_id: str
    expected_acceptance_plan_id: str
    runtime_accepted: bool

    def __post_init__(self) -> None:
        if (
            self.declaration_id != "cond:s0-iv-core"
            or self.declaration_version != "0.1.0"
            or self.component_id != "s0_environment_boundary"
            or self.expected_acceptance_plan_id != "s0plan:iv-core"
            or self.runtime_accepted is not False
        ):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "invalid inert S0 declaration binding")


@dataclass(frozen=True, slots=True)
class ScenarioBinding:
    scenario_id: str
    scenario_version: str
    scenario_family: str
    scenario_adapter_component_id: str
    ground_truth_adapter_component_id: str
    reset_controller_component_id: str
    safety_configuration_id: str
    safety_configuration_version: str
    z6_endpoint_declared: bool
    synthetic: bool
    public_target: bool
    real_credentials: bool

    def __post_init__(self) -> None:
        if (
            self.scenario_id != "scenario:iv-s01-protected-record"
            or self.scenario_version != "0.1.0"
            or self.scenario_family != "S01"
            or self.scenario_adapter_component_id != "scenario_adapter"
            or self.ground_truth_adapter_component_id != "resource_state_observer"
            or self.reset_controller_component_id != "reset_controller"
            or self.safety_configuration_id != "safetycfg:iv-core"
            or self.safety_configuration_version != "0.1.0"
            or self.z6_endpoint_declared is not False
            or self.synthetic is not True
            or self.public_target is not False
            or self.real_credentials is not False
        ):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "invalid scenario binding")


@dataclass(frozen=True, slots=True)
class CapabilityEnvelopeBinding:
    capability_envelope_id: str
    capability_envelope_version: str

    def __post_init__(self) -> None:
        if (self.capability_envelope_id, self.capability_envelope_version) != (
            "envelope:iv-core",
            "0.1.0",
        ):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "invalid capability-envelope binding")


@dataclass(frozen=True, slots=True)
class ResetBinding:
    reset_plan_id: str
    reset_plan_version: str
    baseline_id: str
    reset_controller_component_id: str

    def __post_init__(self) -> None:
        if (
            self.reset_plan_id,
            self.reset_plan_version,
            self.baseline_id,
            self.reset_controller_component_id,
        ) != (
            "resetplan:iv-core",
            "0.1.0",
            "cond:iv-core-clean-state",
            "reset_controller",
        ):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "invalid reset binding")


@dataclass(frozen=True, slots=True)
class ControlBindings:
    m1_component_id: str
    m2_component_id: str
    m3_component_id: str
    authorization_component_id: str
    authorization_policy_id: str
    authorization_policy_version: str
    approval_component_id: str
    approval_policy_id: str
    approval_policy_version: str
    execution_adapter_component_id: str

    def __post_init__(self) -> None:
        if (
            self.m1_component_id,
            self.m2_component_id,
            self.m3_component_id,
            self.authorization_component_id,
            self.authorization_policy_id,
            self.authorization_policy_version,
            self.approval_component_id,
            self.approval_policy_id,
            self.approval_policy_version,
            self.execution_adapter_component_id,
        ) != (
            "m1_policy_context_adapter",
            "m2_policy_mediator",
            "m3_external_enforcer",
            "authorization_service",
            "policy:iv-core-authorization",
            "0.1.0",
            "approval_emulator",
            "approvalpolicy:iv-core-deterministic",
            "0.1.0",
            "action_execution_adapter",
        ):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "invalid control bindings")


@dataclass(frozen=True, slots=True)
class SourceRegistryBinding:
    registry_id: str
    registry_version: str

    def __post_init__(self) -> None:
        if (self.registry_id, self.registry_version) != ("sourceregistry:iv-core", "0.1.0"):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "invalid source-registry binding")


@dataclass(frozen=True, slots=True)
class ComponentBinding:
    component_id: str
    component_role: str
    component_version: str
    build_id: str
    implementation_reference: str
    trust_context: str
    frozen_zones: tuple[str, ...]
    dependency_component_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_nonempty_strings(
            self.component_id,
            self.component_role,
            self.component_version,
            self.build_id,
            self.implementation_reference,
            self.trust_context,
        )
        if not isinstance(self.frozen_zones, tuple) or not isinstance(
            self.dependency_component_ids, tuple
        ):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "component collections must be tuples")
        _require_nonempty_strings(*self.frozen_zones, *self.dependency_component_ids)


@dataclass(frozen=True, slots=True)
class LocalSourceChannelBinding:
    source_registration_id: str
    source_component_id: str
    source_version: str
    source_build_id: str
    instrument_configuration_id: str
    dedicated_local_channel_id: str
    authoritative_properties: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_nonempty_strings(
            self.source_registration_id,
            self.source_component_id,
            self.source_version,
            self.source_build_id,
            self.instrument_configuration_id,
            self.dedicated_local_channel_id,
            *self.authoritative_properties,
        )
        if not isinstance(self.authoritative_properties, tuple) or not self.authoritative_properties:
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "source properties must be a nonempty tuple")


@dataclass(frozen=True, slots=True)
class ProviderBinding:
    component_id: str
    component_version: str
    build_id: str
    source_registration_id: str | None
    dedicated_local_channel_id: str | None

    def __post_init__(self) -> None:
        _require_nonempty_strings(self.component_id, self.component_version, self.build_id)
        if (self.source_registration_id is None) != (self.dedicated_local_channel_id is None):
            _reject(AdapterErrorCode.PROVIDER_CHANNEL_INVALID, "provider source and channel must be jointly present")
        if self.source_registration_id is not None:
            _require_nonempty_strings(self.source_registration_id, self.dedicated_local_channel_id)


@dataclass(frozen=True, slots=True)
class M3EnforcementIntent:
    control_decision_id: str
    authorization_decision_id: str
    approval_decision_id: str | None
    m3_provider_binding: ProviderBinding
    m3_source_channel_binding: LocalSourceChannelBinding

    def __post_init__(self) -> None:
        _require_nonempty_strings(self.control_decision_id, self.authorization_decision_id)
        if self.approval_decision_id is not None:
            _require_nonempty_strings(self.approval_decision_id)
        if self.m3_provider_binding.component_id != "m3_external_enforcer":
            _reject(AdapterErrorCode.PROVIDER_IDENTITY_INVALID, "M3 intent targets the wrong provider")
        if (
            self.m3_source_channel_binding.source_registration_id != "source:m3"
            or self.m3_source_channel_binding.dedicated_local_channel_id != "channel_m3"
        ):
            _reject(AdapterErrorCode.PROVIDER_CHANNEL_INVALID, "M3 intent uses the wrong source channel")


@dataclass(frozen=True, slots=True)
class AdapterContext:
    scope: OrchestrationScope
    instrument_configuration_binding: InstrumentConfigurationBinding
    environment_binding: EnvironmentBinding
    s0_declaration_binding: S0DeclarationBinding
    scenario_binding: ScenarioBinding
    capability_envelope_binding: CapabilityEnvelopeBinding
    reset_binding: ResetBinding
    control_bindings: ControlBindings
    source_registry_binding: SourceRegistryBinding
    component_bindings: tuple[ComponentBinding, ...]
    source_channel_bindings: tuple[LocalSourceChannelBinding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.scope, OrchestrationScope):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "context requires an orchestration scope")
        if self.scope.runtime_plan_id != "ivplan:iv-core-001" or self.scope.runtime_plan_version != "0.2.0":
            _reject(AdapterErrorCode.SCOPE_BINDING_INVALID, "context requires Runtime Plan 0.2.0")
        if (
            self.scope.instrument_configuration_id
            != self.instrument_configuration_binding.configuration_id
            or self.scope.validation_set_id != "iv_core"
            or self.scope.validation_set_version != "0.1.0"
        ):
            _reject(AdapterErrorCode.SCOPE_BINDING_INVALID, "context scope does not bind the frozen configuration")
        if tuple(item.component_id for item in self.component_bindings) != _COMPONENT_IDS:
            _reject(AdapterErrorCode.PROVIDER_IDENTITY_INVALID, "context component inventory is not exact")
        if tuple(item.source_registration_id for item in self.source_channel_bindings) != _SOURCE_IDS:
            _reject(AdapterErrorCode.PROVIDER_CHANNEL_INVALID, "context source/channel inventory is not exact")
        component_by_id = {item.component_id: item for item in self.component_bindings}
        if len(component_by_id) != 21:
            _reject(AdapterErrorCode.PROVIDER_IDENTITY_INVALID, "component identities are not unique")
        for component in self.component_bindings:
            if any(dependency not in component_by_id for dependency in component.dependency_component_ids):
                _reject(AdapterErrorCode.PROVIDER_IDENTITY_INVALID, "component dependency is unknown")
        source_by_id = {item.source_registration_id: item for item in self.source_channel_bindings}
        if len(source_by_id) != 15:
            _reject(AdapterErrorCode.PROVIDER_CHANNEL_INVALID, "source identities are not unique")
        for source in self.source_channel_bindings:
            component = component_by_id.get(source.source_component_id)
            if (
                component is None
                or source.source_version != component.component_version
                or source.source_build_id != component.build_id
                or source.instrument_configuration_id
                != self.instrument_configuration_binding.configuration_id
            ):
                _reject(AdapterErrorCode.PROVIDER_CHANNEL_INVALID, "source binding disagrees with component/context")


@dataclass(frozen=True, slots=True)
class ProviderResultIdentity:
    provider_component_id: str
    command_identity: tuple[OrchestrationScope, int]
    result_ordinal: int

    def __post_init__(self) -> None:
        _require_nonempty_strings(self.provider_component_id)
        if (
            not isinstance(self.command_identity, tuple)
            or len(self.command_identity) != 2
            or not isinstance(self.command_identity[0], OrchestrationScope)
            or not isinstance(self.command_identity[1], int)
            or self.command_identity[1] < 1
            or not isinstance(self.result_ordinal, int)
            or isinstance(self.result_ordinal, bool)
            or self.result_ordinal < 1
        ):
            _reject(AdapterErrorCode.RESULT_IDENTITY_INVALID, "invalid provider-result identity")


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    adapter_family: AdapterFamily
    provider_binding: ProviderBinding
    command_identity: tuple[OrchestrationScope, int]
    scope: OrchestrationScope
    instrument_configuration_binding: InstrumentConfigurationBinding
    case_id: str | None
    repetition_id: str | None
    run_id: str | None
    action_id: str | None
    payload: FrozenPayload

    def __post_init__(self) -> None:
        if not isinstance(self.adapter_family, AdapterFamily):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "request family is not frozen")
        _validate_envelope_scope(
            self.command_identity,
            self.scope,
            self.instrument_configuration_binding,
            self.case_id,
            self.repetition_id,
            self.run_id,
            self.action_id,
            AdapterErrorCode.REQUEST_CONTRACT_INVALID,
        )
        if not isinstance(self.provider_binding, ProviderBinding) or not isinstance(self.payload, FrozenPayload):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "request envelope type is invalid")
        _validate_request_payload(self.adapter_family, self.payload)


@dataclass(frozen=True, slots=True)
class ProviderResult:
    result_identity: ProviderResultIdentity
    adapter_family: AdapterFamily
    provider_binding: ProviderBinding
    command_identity: tuple[OrchestrationScope, int]
    scope: OrchestrationScope
    instrument_configuration_binding: InstrumentConfigurationBinding
    case_id: str | None
    repetition_id: str | None
    run_id: str | None
    action_id: str | None
    status: ProviderResultStatus
    payload: FrozenPayload

    def __post_init__(self) -> None:
        if not isinstance(self.result_identity, ProviderResultIdentity):
            _reject(AdapterErrorCode.RESULT_CONTRACT_INVALID, "result identity is absent or invalid")
        if not isinstance(self.adapter_family, AdapterFamily):
            _reject(AdapterErrorCode.RESULT_CONTRACT_INVALID, "result family is not frozen")
        if not isinstance(self.provider_binding, ProviderBinding):
            _reject(AdapterErrorCode.RESULT_CONTRACT_INVALID, "provider binding is absent or invalid")
        if not isinstance(self.status, ProviderResultStatus):
            _reject(AdapterErrorCode.STATUS_INVALID, "result status is absent or invalid")
        if not isinstance(self.payload, FrozenPayload):
            _reject(AdapterErrorCode.RESULT_CONTRACT_INVALID, "result payload is absent or invalid")
        _validate_envelope_scope(
            self.command_identity,
            self.scope,
            self.instrument_configuration_binding,
            self.case_id,
            self.repetition_id,
            self.run_id,
            self.action_id,
            AdapterErrorCode.RESULT_CONTRACT_INVALID,
        )
        if self.result_identity.provider_component_id != self.provider_binding.component_id:
            _reject(AdapterErrorCode.RESULT_IDENTITY_INVALID, "result identity provider differs from envelope")
        if self.result_identity.command_identity != self.command_identity:
            _reject(AdapterErrorCode.RESULT_IDENTITY_INVALID, "result identity command differs from envelope")
        _validate_result_payload(self.adapter_family, self.status, self.payload)
        expected_ordinal = _result_ordinal(self.adapter_family, self.status)
        if self.result_identity.result_ordinal != expected_ordinal:
            _reject(AdapterErrorCode.RESULT_IDENTITY_INVALID, "result ordinal is not the frozen lifecycle slot")

    @classmethod
    def from_mapping(cls, fields: Mapping[str, Any]) -> ProviderResult:
        """Strictly construct a supplied result from an exact field mapping."""

        required = {
            "result_identity",
            "adapter_family",
            "provider_binding",
            "command_identity",
            "scope",
            "instrument_configuration_binding",
            "case_id",
            "repetition_id",
            "run_id",
            "action_id",
            "status",
            "payload",
        }
        if not isinstance(fields, Mapping) or set(fields) != required:
            _reject(AdapterErrorCode.RESULT_CONTRACT_INVALID, "ProviderResult field set is not exact")
        try:
            return cls(**dict(fields))
        except AdapterContractError:
            raise
        except (TypeError, ValueError) as exc:
            raise AdapterContractError(
                AdapterErrorCode.RESULT_CONTRACT_INVALID,
                "ProviderResult fields are invalid",
            ) from exc


_COMPONENT_IDS: Final = (
    "validation_orchestrator",
    "scripted_validation_actor",
    "scenario_adapter",
    "authorization_service",
    "approval_emulator",
    "m1_policy_context_adapter",
    "m2_policy_mediator",
    "m3_external_enforcer",
    "action_execution_adapter",
    "s0_environment_boundary",
    "resource_state_observer",
    "s0_boundary_observer",
    "evidence_collector",
    "evidence_normalizer_store",
    "action_outcome_evaluator",
    "run_outcome_aggregator",
    "validation_case_evaluator",
    "instrument_acceptance_producer",
    "reset_controller",
    "watchdog_controller",
    "failure_injection_controller",
)

_G6_COMPONENTS: Final = frozenset(
    {
        "scenario_adapter",
        "m3_external_enforcer",
        "action_execution_adapter",
        "s0_environment_boundary",
        "resource_state_observer",
        "s0_boundary_observer",
        "evidence_collector",
        "reset_controller",
        "watchdog_controller",
        "failure_injection_controller",
    }
)

COMPONENT_OWNERSHIP: Final[Mapping[str, ComponentOwnership]] = MappingProxyType(
    {
        component: (
            ComponentOwnership.G6_INERT_SURFACE
            if component in _G6_COMPONENTS
            else ComponentOwnership.NON_G6
        )
        for component in _COMPONENT_IDS
    }
)

_ADAPTED: Final[Mapping[CommandKind, tuple[AdapterFamily, str]]] = MappingProxyType(
    {
        CommandKind.REQUEST_BASELINE_VERIFICATION: (
            AdapterFamily.BASELINE_OBSERVER,
            "resource_state_observer",
        ),
        CommandKind.REQUEST_RUN_INITIALIZATION: (
            AdapterFamily.SCENARIO_INITIALIZATION,
            "scenario_adapter",
        ),
        CommandKind.ARM_WATCHDOG: (AdapterFamily.WATCHDOG, "watchdog_controller"),
        CommandKind.CANCEL_WATCHDOG: (AdapterFamily.WATCHDOG, "watchdog_controller"),
        CommandKind.REQUEST_FAULT_APPLY: (
            AdapterFamily.FAULT_CONTROL,
            "failure_injection_controller",
        ),
        CommandKind.REQUEST_EXECUTION: (AdapterFamily.EXECUTION, "action_execution_adapter"),
        CommandKind.REQUEST_NONEXECUTION_CONFIRMATION: (
            AdapterFamily.NONEXECUTION_CONFIRMATION,
            "action_execution_adapter",
        ),
        CommandKind.REQUEST_TERMINATION: (AdapterFamily.TERMINATION, "watchdog_controller"),
        CommandKind.REQUEST_EVIDENCE_DRAIN: (
            AdapterFamily.EVIDENCE_DRAIN,
            "evidence_collector",
        ),
        CommandKind.REQUEST_FAULT_REMOVAL: (
            AdapterFamily.FAULT_CONTROL,
            "failure_injection_controller",
        ),
        CommandKind.REQUEST_RESET: (AdapterFamily.RESET_PROVIDER, "reset_controller"),
        CommandKind.REQUEST_RESET_OBSERVATION: (
            AdapterFamily.RESET_OBSERVER,
            "resource_state_observer",
        ),
        CommandKind.REQUEST_COLLECTION_CLOSURE: (
            AdapterFamily.COLLECTION_CLOSURE,
            "evidence_collector",
        ),
    }
)

COMMAND_OWNERSHIP: Final[Mapping[CommandKind, CommandOwnership]] = MappingProxyType(
    {
        kind: CommandOwnership.G6_ADAPTED if kind in _ADAPTED else CommandOwnership.INTERNAL_PURE
        for kind in CommandKind
    }
)

_TRANSLATED_EVENTS: Final = frozenset(
    {
        EventKind.BASELINE_RESULT,
        EventKind.RUN_INITIALIZATION_RESULT,
        EventKind.FAULT_RESULT,
        EventKind.EXECUTION_RESULT,
        EventKind.NONEXECUTION_RESULT,
        EventKind.TERMINATION_RESULT,
        EventKind.DRAIN_RESULT,
        EventKind.RESET_RESULT,
        EventKind.RESET_OBSERVATION_RESULT,
        EventKind.COLLECTION_RESULT,
        EventKind.WATCHDOG_CONTROL_RESULT,
        EventKind.WATCHDOG_TIMEOUT,
    }
)

_LIFECYCLE_EVENTS: Final = frozenset({EventKind.START, EventKind.COMMAND_FAILURE})

EVENT_OWNERSHIP: Final[Mapping[EventKind, EventOwnership]] = MappingProxyType(
    {
        kind: (
            EventOwnership.G6_TRANSLATED_PROVIDER_RESULT
            if kind in _TRANSLATED_EVENTS
            else EventOwnership.G5_LIFECYCLE_DELIVERY
            if kind in _LIFECYCLE_EVENTS
            else EventOwnership.INTERNAL_PURE
        )
        for kind in EventKind
    }
)

_SOURCE_IDS: Final = (
    "source:request",
    "source:authorization",
    "source:approval",
    "source:m1-configuration",
    "source:m2",
    "source:m3",
    "source:execution",
    "source:resource",
    "source:s0",
    "source:watchdog",
    "source:collector",
    "source:normalizer",
    "source:action-evaluator",
    "source:run-aggregator",
    "source:case-evaluator",
)

_COMPONENT_SOURCE: Final[Mapping[str, tuple[str, str]]] = MappingProxyType(
    {
        "m3_external_enforcer": ("source:m3", "channel_m3"),
        "action_execution_adapter": ("source:execution", "channel_execution"),
        "resource_state_observer": ("source:resource", "channel_resource"),
        "s0_boundary_observer": ("source:s0", "channel_s0"),
        "watchdog_controller": ("source:watchdog", "channel_watchdog"),
        "evidence_collector": ("source:collector", "channel_collector"),
    }
)

_REQUEST_KEYS: Final[Mapping[CommandKind, frozenset[str]]] = MappingProxyType(
    {
        CommandKind.REQUEST_BASELINE_VERIFICATION: frozenset(
            {"reset_plan_id", "reset_plan_version", "clean_state_condition", "baseline_identity"}
        ),
        CommandKind.REQUEST_RUN_INITIALIZATION: frozenset(
            {"scheduled_run", "validation_case", "repetition", "selected_treatment", "configuration_references"}
        ),
        CommandKind.ARM_WATCHDOG: frozenset({"deadline_key", "duration_seconds"}),
        CommandKind.CANCEL_WATCHDOG: frozenset({"deadline_key"}),
        CommandKind.REQUEST_FAULT_APPLY: frozenset({"fault_binding", "fault_fixture_reference"}),
        CommandKind.REQUEST_EXECUTION: frozenset(
            {"action", "authorization", "approval", "control", "m3_enforcement_intent"}
        ),
        CommandKind.REQUEST_NONEXECUTION_CONFIRMATION: frozenset(
            {"action", "authorization", "approval", "control", "cause", "m3_enforcement_intent"}
        ),
        CommandKind.REQUEST_TERMINATION: frozenset({"cause", "causal_references"}),
        CommandKind.REQUEST_EVIDENCE_DRAIN: frozenset(
            {"run_reference", "repetition_reference", "collector_reference", "reset_plan_reference", "drain_deadline_key"}
        ),
        CommandKind.REQUEST_FAULT_REMOVAL: frozenset({"fault_binding", "apply_result_reference"}),
        CommandKind.REQUEST_RESET: frozenset(
            {"reset_plan_id", "reset_plan_version", "baseline_identity", "clean_state_condition"}
        ),
        CommandKind.REQUEST_RESET_OBSERVATION: frozenset(
            {"reset_plan_id", "reset_result_reference", "baseline_identity", "observer_reference"}
        ),
        CommandKind.REQUEST_COLLECTION_CLOSURE: frozenset(
            {"run_reference", "repetition_reference", "evidence_set_identity", "reset_observation_references"}
        ),
    }
)

_REQUEST_FAMILY_KEYS: Final[Mapping[AdapterFamily, frozenset[frozenset[str]]]] = MappingProxyType(
    {
        AdapterFamily.BASELINE_OBSERVER: frozenset({_REQUEST_KEYS[CommandKind.REQUEST_BASELINE_VERIFICATION]}),
        AdapterFamily.SCENARIO_INITIALIZATION: frozenset({_REQUEST_KEYS[CommandKind.REQUEST_RUN_INITIALIZATION]}),
        AdapterFamily.WATCHDOG: frozenset(
            {_REQUEST_KEYS[CommandKind.ARM_WATCHDOG], _REQUEST_KEYS[CommandKind.CANCEL_WATCHDOG]}
        ),
        AdapterFamily.FAULT_CONTROL: frozenset(
            {_REQUEST_KEYS[CommandKind.REQUEST_FAULT_APPLY], _REQUEST_KEYS[CommandKind.REQUEST_FAULT_REMOVAL]}
        ),
        AdapterFamily.EXECUTION: frozenset({_REQUEST_KEYS[CommandKind.REQUEST_EXECUTION]}),
        AdapterFamily.NONEXECUTION_CONFIRMATION: frozenset(
            {_REQUEST_KEYS[CommandKind.REQUEST_NONEXECUTION_CONFIRMATION]}
        ),
        AdapterFamily.TERMINATION: frozenset({_REQUEST_KEYS[CommandKind.REQUEST_TERMINATION]}),
        AdapterFamily.EVIDENCE_DRAIN: frozenset({_REQUEST_KEYS[CommandKind.REQUEST_EVIDENCE_DRAIN]}),
        AdapterFamily.RESET_PROVIDER: frozenset({_REQUEST_KEYS[CommandKind.REQUEST_RESET]}),
        AdapterFamily.RESET_OBSERVER: frozenset({_REQUEST_KEYS[CommandKind.REQUEST_RESET_OBSERVATION]}),
        AdapterFamily.COLLECTION_CLOSURE: frozenset({_REQUEST_KEYS[CommandKind.REQUEST_COLLECTION_CLOSURE]}),
    }
)

_RESULT_KEYS: Final[Mapping[tuple[AdapterFamily, ProviderResultStatus], frozenset[str]]] = MappingProxyType(
    {
        (AdapterFamily.BASELINE_OBSERVER, ProviderResultStatus.CLEAN_BASELINE_OBSERVED): frozenset({"observation_reference"}),
        (AdapterFamily.BASELINE_OBSERVER, ProviderResultStatus.RESET_MISMATCH_OBSERVED): frozenset({"observation_reference"}),
        (AdapterFamily.BASELINE_OBSERVER, ProviderResultStatus.RESET_STATE_UNKNOWN): frozenset({"observation_reference"}),
        (AdapterFamily.BASELINE_OBSERVER, ProviderResultStatus.FAILED): frozenset(),
        (AdapterFamily.BASELINE_OBSERVER, ProviderResultStatus.UNAVAILABLE): frozenset(),
        (AdapterFamily.SCENARIO_INITIALIZATION, ProviderResultStatus.PRODUCED): frozenset({"run_id", "candidate"}),
        (AdapterFamily.SCENARIO_INITIALIZATION, ProviderResultStatus.FAILED): frozenset(),
        (AdapterFamily.SCENARIO_INITIALIZATION, ProviderResultStatus.UNKNOWN): frozenset(),
        (AdapterFamily.SCENARIO_INITIALIZATION, ProviderResultStatus.UNAVAILABLE): frozenset(),
        (AdapterFamily.WATCHDOG, ProviderResultStatus.ACKNOWLEDGED): frozenset({"operation", "deadline_key"}),
        (AdapterFamily.WATCHDOG, ProviderResultStatus.FAILED): frozenset({"operation", "deadline_key"}),
        (AdapterFamily.WATCHDOG, ProviderResultStatus.UNKNOWN): frozenset({"operation", "deadline_key"}),
        (AdapterFamily.WATCHDOG, ProviderResultStatus.UNAVAILABLE): frozenset({"operation", "deadline_key"}),
        (AdapterFamily.WATCHDOG, ProviderResultStatus.TIMEOUT): frozenset({"deadline_key"}),
        (AdapterFamily.FAULT_CONTROL, ProviderResultStatus.ACTIVE): frozenset({"operation", "fault_binding"}),
        (AdapterFamily.FAULT_CONTROL, ProviderResultStatus.CLEARED): frozenset({"operation", "fault_binding"}),
        (AdapterFamily.FAULT_CONTROL, ProviderResultStatus.FAILED): frozenset({"operation", "fault_binding"}),
        (AdapterFamily.FAULT_CONTROL, ProviderResultStatus.UNKNOWN): frozenset({"operation", "fault_binding"}),
        (AdapterFamily.FAULT_CONTROL, ProviderResultStatus.UNAVAILABLE): frozenset({"operation", "fault_binding"}),
        (AdapterFamily.EXECUTION, ProviderResultStatus.ATTEMPTED): frozenset({"provider_result_reference", "evidence_references"}),
        (AdapterFamily.EXECUTION, ProviderResultStatus.SUCCEEDED): frozenset({"provider_result_reference", "evidence_references"}),
        (AdapterFamily.EXECUTION, ProviderResultStatus.FAILED): frozenset({"provider_result_reference", "evidence_references"}),
        (AdapterFamily.EXECUTION, ProviderResultStatus.NOT_ATTEMPTED): frozenset({"provider_result_reference", "evidence_references"}),
        (AdapterFamily.EXECUTION, ProviderResultStatus.RESULT_UNKNOWN): frozenset({"evidence_references"}),
        (AdapterFamily.EXECUTION, ProviderResultStatus.UNAVAILABLE): frozenset({"evidence_references"}),
        (AdapterFamily.NONEXECUTION_CONFIRMATION, ProviderResultStatus.NOT_ATTEMPTED): frozenset({"cause", "evidence_reference"}),
        (AdapterFamily.NONEXECUTION_CONFIRMATION, ProviderResultStatus.FAILED): frozenset({"cause"}),
        (AdapterFamily.NONEXECUTION_CONFIRMATION, ProviderResultStatus.UNKNOWN): frozenset({"cause"}),
        (AdapterFamily.NONEXECUTION_CONFIRMATION, ProviderResultStatus.UNAVAILABLE): frozenset({"cause"}),
        (AdapterFamily.TERMINATION, ProviderResultStatus.OBSERVED): frozenset({"termination_class", "evidence_reference"}),
        (AdapterFamily.TERMINATION, ProviderResultStatus.FAILED): frozenset({"termination_class"}),
        (AdapterFamily.TERMINATION, ProviderResultStatus.UNKNOWN): frozenset({"termination_class"}),
        (AdapterFamily.TERMINATION, ProviderResultStatus.UNAVAILABLE): frozenset({"termination_class"}),
        (AdapterFamily.EVIDENCE_DRAIN, ProviderResultStatus.READY_FOR_RESET): frozenset({"collector_reference"}),
        (AdapterFamily.EVIDENCE_DRAIN, ProviderResultStatus.FAILED): frozenset(),
        (AdapterFamily.EVIDENCE_DRAIN, ProviderResultStatus.UNKNOWN): frozenset(),
        (AdapterFamily.EVIDENCE_DRAIN, ProviderResultStatus.UNAVAILABLE): frozenset(),
        (AdapterFamily.RESET_PROVIDER, ProviderResultStatus.COMPLETED): frozenset({"reset_plan_id", "reset_plan_version", "result_reference"}),
        (AdapterFamily.RESET_PROVIDER, ProviderResultStatus.FAILED): frozenset({"reset_plan_id", "reset_plan_version"}),
        (AdapterFamily.RESET_PROVIDER, ProviderResultStatus.UNKNOWN): frozenset({"reset_plan_id", "reset_plan_version"}),
        (AdapterFamily.RESET_PROVIDER, ProviderResultStatus.UNAVAILABLE): frozenset({"reset_plan_id", "reset_plan_version"}),
        (AdapterFamily.RESET_OBSERVER, ProviderResultStatus.CLEAN_BASELINE_OBSERVED): frozenset({"observation_reference"}),
        (AdapterFamily.RESET_OBSERVER, ProviderResultStatus.RESET_MISMATCH_OBSERVED): frozenset({"observation_reference"}),
        (AdapterFamily.RESET_OBSERVER, ProviderResultStatus.RESET_STATE_UNKNOWN): frozenset({"observation_reference"}),
        (AdapterFamily.COLLECTION_CLOSURE, ProviderResultStatus.CLOSED): frozenset({"evidence_set_reference", "collection_health_reference"}),
        (AdapterFamily.COLLECTION_CLOSURE, ProviderResultStatus.FAILED): frozenset(),
        (AdapterFamily.COLLECTION_CLOSURE, ProviderResultStatus.UNKNOWN): frozenset(),
        (AdapterFamily.COLLECTION_CLOSURE, ProviderResultStatus.UNAVAILABLE): frozenset(),
    }
)


def adapter_context_from_validated_runtime_plan(
    scope: OrchestrationScope,
    runtime_plan: Mapping[str, Any],
) -> AdapterContext:
    """Project an already G1-validated Runtime Plan 0.2.0 into G6 data."""

    try:
        if (
            runtime_plan["runtime_plan_id"] != "ivplan:iv-core-001"
            or runtime_plan["runtime_plan_version"] != "0.2.0"
            or runtime_plan["instrument_configuration_id"] != "instrument:iv-core"
            or runtime_plan["instrument_configuration_version"] != "0.1.0"
        ):
            _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "runtime-plan identity is not frozen")
        configuration = InstrumentConfigurationBinding(
            runtime_plan["instrument_configuration_id"],
            runtime_plan["instrument_configuration_version"],
            runtime_plan["instrument_configuration_digest"],
        )
        environment = runtime_plan["environment_binding"]
        s0 = runtime_plan["s0_declaration_binding"]
        scenario = runtime_plan["scenario_selection"]
        capability = runtime_plan["capability_envelope_binding"]
        reset = runtime_plan["reset_plan_binding"]
        controls = runtime_plan["control_bindings"]
        evidence = runtime_plan["evidence_configuration"]
        component_bindings = tuple(
            ComponentBinding(
                item["component_id"],
                item["component_role"],
                item["component_version"],
                item["build_id"],
                item["implementation_reference"],
                item["trust_context"],
                tuple(item["frozen_zones"]),
                tuple(item["dependency_component_ids"]),
            )
            for item in runtime_plan["component_manifest"]
        )
        source_bindings = tuple(
            LocalSourceChannelBinding(
                item["source_registration_id"],
                item["source_component_id"],
                item["source_version"],
                item["source_build_id"],
                item["instrument_configuration_id"],
                item["dedicated_local_channel_id"],
                tuple(item["authoritative_properties"]),
            )
            for item in evidence["source_registry"]
        )
        return AdapterContext(
            scope=scope,
            instrument_configuration_binding=configuration,
            environment_binding=EnvironmentBinding(
                environment["environment_id"],
                environment["environment_version"],
                environment["environment_build_id"],
            ),
            s0_declaration_binding=S0DeclarationBinding(
                s0["s0_declaration_id"],
                s0["s0_declaration_version"],
                s0["s0_component_id"],
                s0["expected_acceptance_plan_id"],
                s0["runtime_accepted"],
            ),
            scenario_binding=ScenarioBinding(
                scenario["scenario_id"],
                scenario["scenario_version"],
                scenario["scenario_family"],
                scenario["scenario_adapter_component_id"],
                scenario["ground_truth_adapter_component_id"],
                scenario["reset_controller_component_id"],
                scenario["safety_configuration_id"],
                scenario["safety_configuration_version"],
                scenario["z6_endpoint_declared"],
                scenario["synthetic"],
                scenario["public_target"],
                scenario["real_credentials"],
            ),
            capability_envelope_binding=CapabilityEnvelopeBinding(
                capability["capability_envelope_id"],
                capability["capability_envelope_version"],
            ),
            reset_binding=ResetBinding(
                reset["reset_plan_id"],
                reset["reset_plan_version"],
                reset["reset_baseline_id"],
                reset["reset_controller_component_id"],
            ),
            control_bindings=ControlBindings(
                controls["m1_component_id"],
                controls["m2_component_id"],
                controls["m3_component_id"],
                controls["authorization_component_id"],
                controls["authorization_policy_id"],
                controls["authorization_policy_version"],
                controls["approval_component_id"],
                controls["approval_policy_id"],
                controls["approval_policy_version"],
                controls["execution_adapter_component_id"],
            ),
            source_registry_binding=SourceRegistryBinding(
                evidence["source_registry_id"], evidence["source_registry_version"]
            ),
            component_bindings=component_bindings,
            source_channel_bindings=source_bindings,
        )
    except AdapterContractError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise AdapterContractError(
            AdapterErrorCode.REQUEST_CONTRACT_INVALID,
            "validated Runtime Plan projection is incomplete",
        ) from exc


def resolve_provider_binding(context: AdapterContext, component_id: str) -> ProviderBinding:
    """Resolve an exact provider/build/channel binding from explicit context."""

    if not isinstance(context, AdapterContext):
        _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "adapter context is invalid")
    components = {item.component_id: item for item in context.component_bindings}
    component = components.get(component_id)
    if component is None:
        _reject(AdapterErrorCode.PROVIDER_IDENTITY_INVALID, "provider component is not registered")
    expected_source = _COMPONENT_SOURCE.get(component_id)
    if expected_source is None:
        return ProviderBinding(component_id, component.component_version, component.build_id, None, None)
    source_id, channel_id = expected_source
    sources = {item.source_registration_id: item for item in context.source_channel_bindings}
    source = sources.get(source_id)
    if (
        source is None
        or source.source_component_id != component_id
        or source.source_version != component.component_version
        or source.source_build_id != component.build_id
        or source.dedicated_local_channel_id != channel_id
    ):
        _reject(AdapterErrorCode.PROVIDER_CHANNEL_INVALID, "provider source/channel binding is not exact")
    return ProviderBinding(
        component_id,
        component.component_version,
        component.build_id,
        source_id,
        channel_id,
    )


def resolve_source_channel_binding(
    context: AdapterContext,
    source_registration_id: str,
) -> LocalSourceChannelBinding:
    """Resolve an existing inert local source/channel declaration."""

    for binding in context.source_channel_bindings:
        if binding.source_registration_id == source_registration_id:
            return binding
    _reject(AdapterErrorCode.PROVIDER_CHANNEL_INVALID, "source registration is not in context")


def build_provider_request(
    command: OrchestrationCommand,
    context: AdapterContext,
) -> ProviderRequest:
    """Translate one frozen G5 command into inert provider request data."""

    if not isinstance(command, OrchestrationCommand):
        _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "command is not an OrchestrationCommand")
    if not isinstance(context, AdapterContext):
        _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "context is not an AdapterContext")
    adapted = _ADAPTED.get(command.kind)
    if adapted is None:
        _reject(AdapterErrorCode.COMMAND_NOT_ADAPTED, "G5 command is internal and has no G6 request")
    family, component_id = adapted
    if command.scope != context.scope:
        _reject(AdapterErrorCode.SCOPE_BINDING_INVALID, "command scope differs from AdapterContext")
    if command.target_component_id != component_id:
        _reject(AdapterErrorCode.PROVIDER_IDENTITY_INVALID, "command target differs from adapter owner")
    provider = resolve_provider_binding(context, component_id)
    values = dict(command.payload.items)
    if command.kind in {
        CommandKind.REQUEST_EXECUTION,
        CommandKind.REQUEST_NONEXECUTION_CONFIRMATION,
    }:
        values["m3_enforcement_intent"] = _m3_intent(command, context)
    payload = frozen_payload(**values)
    if frozenset(name for name, _ in payload.items) != _REQUEST_KEYS[command.kind]:
        _reject(AdapterErrorCode.PAYLOAD_INVALID, "request payload field set is not exact")
    return ProviderRequest(
        adapter_family=family,
        provider_binding=provider,
        command_identity=command.identity,
        scope=command.scope,
        instrument_configuration_binding=context.instrument_configuration_binding,
        case_id=command.case_id,
        repetition_id=command.repetition_id,
        run_id=command.run_id,
        action_id=command.action_id,
        payload=payload,
    )


def translate_provider_result(
    command: OrchestrationCommand,
    request: ProviderRequest,
    supplied_result: ProviderResult,
    context: AdapterContext,
    g5_event_ordinal: int,
) -> OrchestrationEvent:
    """Purely translate validated supplied data into an undelivered G5 event."""

    if not isinstance(g5_event_ordinal, int) or isinstance(g5_event_ordinal, bool) or g5_event_ordinal < 1:
        _reject(AdapterErrorCode.EVENT_IDENTITY_INVALID, "G5 event ordinal must be positive")
    expected_request = build_provider_request(command, context)
    _compare_request(request, expected_request)
    if not isinstance(supplied_result, ProviderResult):
        _reject(AdapterErrorCode.RESULT_CONTRACT_INVALID, "supplied result is not ProviderResult data")
    _compare_result_envelope(supplied_result, expected_request)
    _validate_result_command_bindings(command, request, supplied_result)
    kind, payload = _event_material(command, supplied_result)
    try:
        return OrchestrationEvent(
            kind=kind,
            scope=command.scope,
            event_ordinal=g5_event_ordinal,
            correlation_command_ordinal=command.command_ordinal,
            case_id=command.case_id,
            repetition_id=command.repetition_id,
            run_id=command.run_id,
            action_id=command.action_id,
            payload=payload,
        )
    except ValueError as exc:
        raise AdapterContractError(
            AdapterErrorCode.RESULT_CONTRACT_INVALID,
            "translated event violates the frozen G5 contract",
        ) from exc


def _reject(code: AdapterErrorCode, message: str) -> None:
    raise AdapterContractError(code, message)


def _require_nonempty_strings(*values: Any) -> None:
    if any(not isinstance(value, str) or not _NONEMPTY.fullmatch(value) for value in values):
        _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "binding fields must be nonempty strings")


def _validate_envelope_scope(
    command_identity: tuple[OrchestrationScope, int],
    scope: OrchestrationScope,
    configuration: InstrumentConfigurationBinding,
    case_id: str | None,
    repetition_id: str | None,
    run_id: str | None,
    action_id: str | None,
    error_code: AdapterErrorCode,
) -> None:
    if (
        not isinstance(command_identity, tuple)
        or len(command_identity) != 2
        or not isinstance(command_identity[0], OrchestrationScope)
        or not isinstance(command_identity[1], int)
        or isinstance(command_identity[1], bool)
        or command_identity[1] < 1
        or command_identity[0] != scope
        or not isinstance(configuration, InstrumentConfigurationBinding)
        or configuration.configuration_id != scope.instrument_configuration_id
        or configuration.configuration_version != scope.validation_set_version
    ):
        _reject(error_code, "envelope identity/scope/configuration is invalid")
    for value in (case_id, repetition_id, run_id, action_id):
        if value is not None and (not isinstance(value, str) or not value):
            _reject(error_code, "scope field must be absent or a nonempty string")


def _m3_intent(
    command: OrchestrationCommand,
    context: AdapterContext,
) -> M3EnforcementIntent | None:
    control = command.payload.get("control")
    if control is None:
        return None
    if not isinstance(control, ControlDecision):
        _reject(AdapterErrorCode.PAYLOAD_INVALID, "provider command control is invalid")
    if control.control_layer is not ControlLayer.M3:
        return None
    authorization = command.payload.get("authorization")
    approval = command.payload.get("approval")
    if not isinstance(authorization, AuthorizationDecision):
        _reject(AdapterErrorCode.PAYLOAD_INVALID, "M3 intent requires retained authorization")
    if approval is not None and not isinstance(approval, ApprovalDecision):
        _reject(AdapterErrorCode.PAYLOAD_INVALID, "M3 intent approval is invalid")
    if (
        control.authorization_decision_id != authorization.authorization_decision_id
        or control.approval_decision_id
        != (approval.approval_decision_id if approval is not None else None)
    ):
        _reject(AdapterErrorCode.PAYLOAD_INVALID, "M3 retained decisions do not correlate")
    return M3EnforcementIntent(
        control.control_decision_id,
        authorization.authorization_decision_id,
        approval.approval_decision_id if approval is not None else None,
        resolve_provider_binding(context, "m3_external_enforcer"),
        resolve_source_channel_binding(context, "source:m3"),
    )


def _payload_keys(payload: FrozenPayload) -> frozenset[str]:
    return frozenset(name for name, _ in payload.items)


def _reference(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _references(value: Any) -> bool:
    return isinstance(value, tuple) and all(_reference(item) for item in value)


def _validate_result_payload(
    family: AdapterFamily,
    status: ProviderResultStatus,
    payload: FrozenPayload,
) -> None:
    expected = _RESULT_KEYS.get((family, status))
    if expected is None:
        _reject(AdapterErrorCode.STATUS_INVALID, "status is not permitted for adapter family")
    if _payload_keys(payload) != expected:
        _reject(AdapterErrorCode.PAYLOAD_INVALID, "result payload field set is not exact")
    for name in (
        "observation_reference",
        "provider_result_reference",
        "evidence_reference",
        "collector_reference",
        "result_reference",
        "evidence_set_reference",
        "collection_health_reference",
    ):
        if name in expected and not _reference(payload.get(name)):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, f"{name} is not a governed opaque reference")
    if "evidence_references" in expected and not _references(payload.get("evidence_references")):
        _reject(AdapterErrorCode.PAYLOAD_INVALID, "evidence references must be an immutable string tuple")
    if family is AdapterFamily.SCENARIO_INITIALIZATION and status is ProviderResultStatus.PRODUCED:
        if (
            not _reference(payload.get("run_id"))
            or not payload.get("run_id").startswith("run:")
            or not isinstance(payload.get("candidate"), Mapping)
        ):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "produced run result is invalid")
    if family is AdapterFamily.WATCHDOG:
        if not isinstance(payload.get("deadline_key"), WatchdogDeadlineKey):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "watchdog result requires its exact deadline key")
        if status is not ProviderResultStatus.TIMEOUT and payload.get("operation") not in {"ARM", "CANCEL"}:
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "watchdog control operation is invalid")
    if family is AdapterFamily.FAULT_CONTROL:
        operation = payload.get("operation")
        if operation not in {"APPLY", "REMOVE"} or not _reference(payload.get("fault_binding")):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "fault result operation/binding is invalid")
        if status is ProviderResultStatus.ACTIVE and operation != "APPLY":
            _reject(AdapterErrorCode.STATUS_INVALID, "ACTIVE is valid only for fault apply")
        if status is ProviderResultStatus.CLEARED and operation != "REMOVE":
            _reject(AdapterErrorCode.STATUS_INVALID, "CLEARED is valid only for fault removal")
    if family is AdapterFamily.NONEXECUTION_CONFIRMATION:
        if payload.get("cause") not in {"CONTROL_BLOCKED", "PRECONDITION_UNMET", "AGENT_WITHDREW"}:
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "nonexecution cause is invalid")
    if family is AdapterFamily.TERMINATION:
        if payload.get("termination_class") not in {
            "NORMAL_TERMINAL",
            "AGENT_ABORT",
            "ACTION_BUDGET_EXHAUSTED",
            "RUN_INVALIDATION",
            "INFRASTRUCTURE_FAILURE",
            "TIMEOUT",
        }:
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "termination class is invalid")
    if family is AdapterFamily.RESET_PROVIDER:
        if (
            payload.get("reset_plan_id") != "resetplan:iv-core"
            or payload.get("reset_plan_version") != "0.1.0"
        ):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "reset result does not bind the frozen plan")


def _validate_request_payload(family: AdapterFamily, payload: FrozenPayload) -> None:
    keys = _payload_keys(payload)
    if keys not in _REQUEST_FAMILY_KEYS[family]:
        _reject(AdapterErrorCode.PAYLOAD_INVALID, "request payload field set is not exact")
    if family is AdapterFamily.BASELINE_OBSERVER:
        if (
            payload.get("reset_plan_id") != "resetplan:iv-core"
            or payload.get("reset_plan_version") != "0.1.0"
            or payload.get("clean_state_condition") != "cond:iv-core-clean-state"
            or payload.get("baseline_identity") != "cond:iv-core-clean-state"
        ):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "baseline request does not bind the frozen contract")
    if family is AdapterFamily.SCENARIO_INITIALIZATION:
        if (
            not isinstance(payload.get("scheduled_run"), tuple)
            or not payload.get("scheduled_run")
            or not isinstance(payload.get("validation_case"), tuple)
            or not payload.get("validation_case")
            or not isinstance(payload.get("repetition"), ScheduledValidationRepetition)
            or not _reference(payload.get("selected_treatment"))
            or not isinstance(payload.get("configuration_references"), tuple)
            or len(payload.get("configuration_references")) != 6
            or not _references(payload.get("configuration_references"))
        ):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "scenario initialization request is invalid")
    if family is AdapterFamily.WATCHDOG:
        key = payload.get("deadline_key")
        if not isinstance(key, WatchdogDeadlineKey):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "watchdog request requires a deadline key")
        if "duration_seconds" in keys:
            expected = {"RUN": 30, "EVIDENCE_DRAIN": 5, "RESET": 15}[key.kind.value]
            if payload.get("duration_seconds") != expected:
                _reject(AdapterErrorCode.PAYLOAD_INVALID, "watchdog duration differs from its deadline")
    if family is AdapterFamily.FAULT_CONTROL:
        if (
            not _reference(payload.get("fault_binding"))
            or payload.get("fault_binding") not in FROZEN_FAULT_CATEGORIES
        ):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "fault request lacks its frozen binding")
        if "fault_fixture_reference" in keys and not _reference(payload.get("fault_fixture_reference")):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "fault apply lacks its fixture reference")
        if "apply_result_reference" in keys and payload.get("apply_result_reference") is None:
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "fault removal lacks its apply result")
    if family in {AdapterFamily.EXECUTION, AdapterFamily.NONEXECUTION_CONFIRMATION}:
        action = payload.get("action")
        if not isinstance(action, RequestedAction):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "provider request action is invalid")
        control = payload.get("control")
        intent = payload.get("m3_enforcement_intent")
        authorization = payload.get("authorization")
        cause = payload.get("cause")
        withdrew = (
            family is AdapterFamily.NONEXECUTION_CONFIRMATION
            and isinstance(cause, Enum)
            and cause.value == "AGENT_WITHDREW"
        )
        if not isinstance(authorization, AuthorizationDecision) and not (
            withdrew and authorization is None
        ):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "provider request authorization is invalid")
        if control is not None and not isinstance(control, ControlDecision):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "provider request control is invalid")
        approval = payload.get("approval")
        if approval is not None and not isinstance(approval, ApprovalDecision):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "provider request approval is invalid")
        if not withdrew and (
            authorization.action_id != action.action_id
            or control is None
            or control.action_id != action.action_id
            or (approval is not None and approval.action_id != action.action_id)
        ):
            _reject(
                AdapterErrorCode.PAYLOAD_INVALID,
                "provider request decisions do not bind the action",
            )
        if isinstance(control, ControlDecision) and control.control_layer is ControlLayer.M3:
            if not isinstance(intent, M3EnforcementIntent):
                _reject(AdapterErrorCode.PAYLOAD_INVALID, "M3 request requires an enforcement intent")
        elif intent is not None:
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "non-M3 request must not carry M3 intent")
    if family is AdapterFamily.NONEXECUTION_CONFIRMATION:
        cause = payload.get("cause")
        if not isinstance(cause, Enum) or cause.value not in {
            "CONTROL_BLOCKED",
            "PRECONDITION_UNMET",
            "AGENT_WITHDREW",
        }:
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "nonexecution request cause is invalid")
    if family is AdapterFamily.TERMINATION:
        cause = payload.get("cause")
        if (
            not isinstance(cause, Enum)
            or cause.value not in {
                "NORMAL_TERMINAL",
                "AGENT_ABORT",
                "ACTION_BUDGET_EXHAUSTED",
                "RUN_INVALIDATION",
                "INFRASTRUCTURE_FAILURE",
                "TIMEOUT",
            }
            or not isinstance(payload.get("causal_references"), tuple)
        ):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "termination request is invalid")
    if family is AdapterFamily.EVIDENCE_DRAIN:
        if (
            not _reference(payload.get("run_reference"))
            or not _reference(payload.get("repetition_reference"))
            or not _reference(payload.get("collector_reference"))
            or payload.get("reset_plan_reference")
            != ("resetplan:iv-core", "0.1.0", "cond:iv-core-clean-state")
            or not isinstance(payload.get("drain_deadline_key"), WatchdogDeadlineKey)
        ):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "evidence-drain request is invalid")
    if family is AdapterFamily.RESET_PROVIDER:
        if (
            payload.get("reset_plan_id") != "resetplan:iv-core"
            or payload.get("reset_plan_version") != "0.1.0"
            or payload.get("baseline_identity") != "cond:iv-core-clean-state"
            or payload.get("clean_state_condition") != "cond:iv-core-clean-state"
        ):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "reset request is invalid")
    if family is AdapterFamily.RESET_OBSERVER:
        if (
            payload.get("reset_plan_id") != "resetplan:iv-core"
            or payload.get("baseline_identity") != "cond:iv-core-clean-state"
            or payload.get("reset_result_reference") is None
            or not _reference(payload.get("observer_reference"))
        ):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "reset-observer request is invalid")
    if family is AdapterFamily.COLLECTION_CLOSURE:
        if (
            not _reference(payload.get("run_reference"))
            or not _reference(payload.get("repetition_reference"))
            or payload.get("evidence_set_identity") is None
            or not isinstance(payload.get("reset_observation_references"), tuple)
        ):
            _reject(AdapterErrorCode.PAYLOAD_INVALID, "collection-closure request is invalid")

def _result_ordinal(family: AdapterFamily, status: ProviderResultStatus) -> int:
    if family is AdapterFamily.EXECUTION:
        return 1 if status is ProviderResultStatus.ATTEMPTED else 2
    if family is AdapterFamily.WATCHDOG and status is ProviderResultStatus.TIMEOUT:
        return 2
    return 1


def _compare_provider(actual: ProviderBinding, expected: ProviderBinding) -> None:
    if actual.component_id != expected.component_id:
        _reject(AdapterErrorCode.PROVIDER_IDENTITY_INVALID, "provider component differs from request")
    if (
        actual.component_version != expected.component_version
        or actual.build_id != expected.build_id
    ):
        _reject(AdapterErrorCode.PROVIDER_BUILD_INVALID, "provider version/build differs from context")
    if (
        actual.source_registration_id != expected.source_registration_id
        or actual.dedicated_local_channel_id != expected.dedicated_local_channel_id
    ):
        _reject(AdapterErrorCode.PROVIDER_CHANNEL_INVALID, "provider source/channel differs from context")


def _compare_request(actual: ProviderRequest, expected: ProviderRequest) -> None:
    if not isinstance(actual, ProviderRequest):
        _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "request is not ProviderRequest data")
    if actual.adapter_family is not expected.adapter_family:
        _reject(AdapterErrorCode.COMMAND_FAMILY_MISMATCH, "request family differs from command")
    _compare_provider(actual.provider_binding, expected.provider_binding)
    if actual.command_identity != expected.command_identity:
        _reject(AdapterErrorCode.COMMAND_CORRELATION_INVALID, "request command identity differs")
    if (
        actual.scope != expected.scope
        or actual.instrument_configuration_binding
        != expected.instrument_configuration_binding
        or actual.case_id != expected.case_id
        or actual.repetition_id != expected.repetition_id
        or actual.run_id != expected.run_id
        or actual.action_id != expected.action_id
    ):
        _reject(AdapterErrorCode.SCOPE_BINDING_INVALID, "request scope differs from command/context")
    if actual.payload != expected.payload:
        _reject(AdapterErrorCode.REQUEST_CONTRACT_INVALID, "request payload differs from command")


def _compare_result_envelope(result: ProviderResult, request: ProviderRequest) -> None:
    if result.adapter_family is not request.adapter_family:
        _reject(AdapterErrorCode.COMMAND_FAMILY_MISMATCH, "result family differs from request")
    _compare_provider(result.provider_binding, request.provider_binding)
    if result.command_identity != request.command_identity:
        _reject(AdapterErrorCode.COMMAND_CORRELATION_INVALID, "result command identity differs")
    if (
        result.scope != request.scope
        or result.instrument_configuration_binding
        != request.instrument_configuration_binding
        or result.case_id != request.case_id
        or result.repetition_id != request.repetition_id
        or result.run_id != request.run_id
        or result.action_id != request.action_id
    ):
        _reject(AdapterErrorCode.SCOPE_BINDING_INVALID, "result scope differs from request")
    if result.result_identity.provider_component_id != request.provider_binding.component_id:
        _reject(AdapterErrorCode.RESULT_IDENTITY_INVALID, "result identity provider differs from request")
    if result.result_identity.command_identity != request.command_identity:
        _reject(AdapterErrorCode.RESULT_IDENTITY_INVALID, "result identity command differs from request")


def _validate_result_command_bindings(
    command: OrchestrationCommand,
    request: ProviderRequest,
    result: ProviderResult,
) -> None:
    payload = result.payload
    request_payload = request.payload
    if request.adapter_family is AdapterFamily.WATCHDOG:
        if result.status is ProviderResultStatus.TIMEOUT:
            if command.kind is not CommandKind.ARM_WATCHDOG:
                _reject(AdapterErrorCode.STATUS_INVALID, "watchdog timeout is valid only for ARM")
        else:
            expected_operation = "ARM" if command.kind is CommandKind.ARM_WATCHDOG else "CANCEL"
            if payload.get("operation") != expected_operation:
                _reject(AdapterErrorCode.PAYLOAD_INVALID, "watchdog operation differs from command")
        if payload.get("deadline_key") != request_payload.get("deadline_key"):
            _reject(AdapterErrorCode.SCOPE_BINDING_INVALID, "watchdog deadline differs from request")
    if request.adapter_family is AdapterFamily.FAULT_CONTROL:
        expected_operation = "APPLY" if command.kind is CommandKind.REQUEST_FAULT_APPLY else "REMOVE"
        if (
            payload.get("operation") != expected_operation
            or payload.get("fault_binding") != request_payload.get("fault_binding")
        ):
            _reject(AdapterErrorCode.SCOPE_BINDING_INVALID, "fault result differs from request")
    if request.adapter_family is AdapterFamily.NONEXECUTION_CONFIRMATION:
        cause = request_payload.get("cause")
        expected = cause.value if isinstance(cause, Enum) else cause
        if payload.get("cause") != expected:
            _reject(AdapterErrorCode.SCOPE_BINDING_INVALID, "nonexecution cause differs from request")
    if request.adapter_family is AdapterFamily.TERMINATION:
        cause = request_payload.get("cause")
        expected = cause.value if isinstance(cause, Enum) else cause
        if payload.get("termination_class") != expected:
            _reject(AdapterErrorCode.SCOPE_BINDING_INVALID, "termination class differs from request")
    if request.adapter_family is AdapterFamily.RESET_PROVIDER:
        if (
            payload.get("reset_plan_id") != request_payload.get("reset_plan_id")
            or payload.get("reset_plan_version") != request_payload.get("reset_plan_version")
        ):
            _reject(AdapterErrorCode.SCOPE_BINDING_INVALID, "reset result differs from request")


def _event_material(
    command: OrchestrationCommand,
    result: ProviderResult,
) -> tuple[EventKind, FrozenPayload]:
    family = result.adapter_family
    status = result.status
    values = dict(result.payload.items)
    output_status = status.value
    if status is ProviderResultStatus.UNAVAILABLE:
        output_status = (
            "FAILED" if family is AdapterFamily.BASELINE_OBSERVER else "RESULT_UNKNOWN"
            if family is AdapterFamily.EXECUTION
            else "UNKNOWN"
        )
    if family is AdapterFamily.BASELINE_OBSERVER:
        values["status"] = output_status
        return EventKind.BASELINE_RESULT, frozen_payload(**values)
    if family is AdapterFamily.SCENARIO_INITIALIZATION:
        values["status"] = output_status
        return EventKind.RUN_INITIALIZATION_RESULT, frozen_payload(**values)
    if family is AdapterFamily.WATCHDOG:
        if status is ProviderResultStatus.TIMEOUT:
            return EventKind.WATCHDOG_TIMEOUT, frozen_payload(**values)
        values["status"] = output_status
        return EventKind.WATCHDOG_CONTROL_RESULT, frozen_payload(**values)
    if family is AdapterFamily.FAULT_CONTROL:
        values["status"] = output_status
        return EventKind.FAULT_RESULT, frozen_payload(**values)
    if family is AdapterFamily.EXECUTION:
        values["status"] = output_status
        return EventKind.EXECUTION_RESULT, frozen_payload(**values)
    if family is AdapterFamily.NONEXECUTION_CONFIRMATION:
        values["status"] = output_status
        return EventKind.NONEXECUTION_RESULT, frozen_payload(**values)
    if family is AdapterFamily.TERMINATION:
        values["status"] = output_status
        return EventKind.TERMINATION_RESULT, frozen_payload(**values)
    if family is AdapterFamily.EVIDENCE_DRAIN:
        values["status"] = output_status
        return EventKind.DRAIN_RESULT, frozen_payload(**values)
    if family is AdapterFamily.RESET_PROVIDER:
        values["status"] = output_status
        return EventKind.RESET_RESULT, frozen_payload(**values)
    if family is AdapterFamily.RESET_OBSERVER:
        values["status"] = output_status
        return EventKind.RESET_OBSERVATION_RESULT, frozen_payload(**values)
    if family is AdapterFamily.COLLECTION_CLOSURE:
        values["status"] = output_status
        return EventKind.COLLECTION_RESULT, frozen_payload(**values)
    _reject(AdapterErrorCode.COMMAND_FAMILY_MISMATCH, "result family has no G5 event mapping")


__all__ = [
    "AdapterContext",
    "AdapterContractError",
    "AdapterErrorCode",
    "AdapterFamily",
    "CapabilityEnvelopeBinding",
    "CommandOwnership",
    "ComponentBinding",
    "ComponentOwnership",
    "ControlBindings",
    "EnvironmentBinding",
    "EventOwnership",
    "InstrumentConfigurationBinding",
    "LocalSourceChannelBinding",
    "M3EnforcementIntent",
    "ProviderBinding",
    "ProviderRequest",
    "ProviderResult",
    "ProviderResultIdentity",
    "ProviderResultStatus",
    "ResetBinding",
    "S0DeclarationBinding",
    "ScenarioBinding",
    "SourceRegistryBinding",
    "COMPONENT_OWNERSHIP",
    "COMMAND_OWNERSHIP",
    "EVENT_OWNERSHIP",
    "adapter_context_from_validated_runtime_plan",
    "build_provider_request",
    "resolve_provider_binding",
    "resolve_source_channel_binding",
    "translate_provider_result",
]
