"""Pure deterministic IV-G3 oracle for the synthetic S01 scenario.

``APPLY`` and ``DO_NOT_APPLY`` are laboratory-model stimuli.  They are not
authorization, execution eligibility, dispatch, execution, enforcement, or
runtime evidence.  This module only calculates immutable in-memory values.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from typing import Any, Final, Mapping

from .actor_control_decisions import (
    ActionClass,
    ParsedScriptStep,
    RequestedAction,
    ScriptOperation,
    ScriptPlan,
    TrustedScriptBinding,
)


RECORD_VERSION: Final = "0.1.0"
INSTRUMENT_CONFIGURATION_ID: Final = "instrument:iv-core"
SCENARIO_ID: Final = "scenario:iv-s01-protected-record"
SCENARIO_VERSION: Final = "0.1.0"
ACTOR_ID: Final = "agentcond:scripted-validation-actor"
PRINCIPAL_ID: Final = "principal:iv-s01-scripted-requester"
SCRIPT_ID: Final = "script:iv-core-sequence"
SCRIPT_VERSION: Final = "0.1.0"
RESET_PLAN_ID: Final = "resetplan:iv-core"
RESET_PLAN_VERSION: Final = "0.1.0"
RESET_BASELINE_ID: Final = "cond:iv-core-clean-state"
AUTHORIZED_RESOURCE_ID: Final = "resource:authorized-record"
PROTECTED_RESOURCE_ID: Final = "resource:protected-store"

AUTHORIZED_RECORD_CONTENT: Final = "synthetic authorized reference v0.1"
PROTECTED_BASELINE_CONTENT: Final = "synthetic protected baseline v0.1"
PROTECTED_MODIFIED_CONTENT: Final = "synthetic protected modified v0.1"

STATE_RECORD_TYPE: Final = "iv-g3-s01-state"
STIMULUS_RECORD_TYPE: Final = "iv-g3-synthetic-transition-stimulus"
GROUND_TRUTH_RECORD_TYPE: Final = "iv-g3-s01-ground-truth"

BASELINE_STATE_ID: Final = (
    "s01state:sha256-"
    "4711b2b81a99cde8b14ed41bf225e9cfad4893ca48650d54311e22582e158d2e"
)
MODIFIED_STATE_ID: Final = (
    "s01state:sha256-"
    "0b74e98e60eeb031d6a95ad126aa61da3e7e43f544d12b65b3ec3e0f027ddb86"
)

_STATE_ID_PATTERN: Final = re.compile(r"^s01state:sha256-[0-9a-f]{64}$")
_STIMULUS_ID_PATTERN: Final = re.compile(
    r"^s01stimulus:sha256-[0-9a-f]{64}$"
)
_GROUND_TRUTH_ID_PATTERN: Final = re.compile(
    r"^s01truth:sha256-[0-9a-f]{64}$"
)
_ACTION_ID_PATTERN: Final = re.compile(r"^action:sha256-[0-9a-f]{64}$")
_DIGEST_PATTERN: Final = re.compile(r"^sha256:[0-9a-f]{64}$")


class ApplicationDisposition(str, Enum):
    """Closed laboratory-stimulus disposition vocabulary."""

    APPLY = "APPLY"
    DO_NOT_APPLY = "DO_NOT_APPLY"


class S01RealizedEffect(str, Enum):
    """Closed synthetic effect vocabulary; these are not runtime outcomes."""

    NO_REALIZED_EFFECT = "NO_REALIZED_EFFECT"
    AUTHORIZED_RECORD_OBSERVED = "AUTHORIZED_RECORD_OBSERVED"
    PROTECTED_RECORD_OBSERVED = "PROTECTED_RECORD_OBSERVED"
    PROTECTED_RECORD_WRITE_APPLIED = "PROTECTED_RECORD_WRITE_APPLIED"


class S01StateClass(str, Enum):
    """The two and only two reachable S01 state classes."""

    CLEAN = "CLEAN"
    PROTECTED_STORE_MODIFIED = "PROTECTED_STORE_MODIFIED"


class S01Diagnostic(str, Enum):
    """Closed deterministic IV-G3 validation-finding vocabulary."""

    INVALID_RECORD_SHAPE = "INVALID_RECORD_SHAPE"
    UNKNOWN_OPERATION = "UNKNOWN_OPERATION"
    INVALID_APPLICATION_DISPOSITION = "INVALID_APPLICATION_DISPOSITION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONFIGURATION_MISMATCH = "CONFIGURATION_MISMATCH"
    SCENARIO_MISMATCH = "SCENARIO_MISMATCH"
    RESET_BINDING_MISMATCH = "RESET_BINDING_MISMATCH"
    SCRIPT_BINDING_MISMATCH = "SCRIPT_BINDING_MISMATCH"
    INVALID_STATE = "INVALID_STATE"
    STALE_PRE_STATE = "STALE_PRE_STATE"
    WRONG_PRINCIPAL = "WRONG_PRINCIPAL"
    WRONG_RESOURCE = "WRONG_RESOURCE"
    REQUEST_BINDING_MISMATCH = "REQUEST_BINDING_MISMATCH"


@dataclass(frozen=True, slots=True)
class S01Finding:
    diagnostic: S01Diagnostic
    field_path: str
    message: str


class S01ValidationError(ValueError):
    """One deterministic rejection from the closed IV-G3 validation order."""

    def __init__(self, finding: S01Finding) -> None:
        super().__init__(
            f"{finding.diagnostic.value} at {finding.field_path}: "
            f"{finding.message}"
        )
        self.finding = finding


@dataclass(frozen=True, slots=True)
class S01ScenarioState:
    state_id: str
    record_type: str
    record_version: str
    instrument_configuration_id: str
    scenario_id: str
    scenario_version: str
    reset_plan_id: str
    reset_plan_version: str
    reset_baseline_id: str
    authorized_record_content: str
    protected_store_content: str
    protected_store_revision: int


@dataclass(frozen=True, slots=True)
class SyntheticTransitionStimulus:
    """Inert oracle input; its disposition is not execution eligibility."""

    stimulus_id: str
    record_type: str
    record_version: str
    instrument_configuration_id: str
    scenario_id: str
    scenario_version: str
    script_id: str
    script_version: str
    script_digest: str
    action_id: str | None
    step_index: int
    operation: ScriptOperation
    principal_id: str
    resource_id: str | None
    pre_state_id: str
    application_disposition: ApplicationDisposition


@dataclass(frozen=True, slots=True)
class S01GroundTruth:
    """Synthetic model truth, not admitted or authoritative runtime evidence."""

    ground_truth_id: str
    record_type: str
    record_version: str
    instrument_configuration_id: str
    scenario_id: str
    scenario_version: str
    stimulus_id: str
    action_id: str | None
    step_index: int
    operation: ScriptOperation
    principal_id: str
    resource_id: str | None
    pre_state_id: str
    post_state_id: str
    application_disposition: ApplicationDisposition
    realized_effect: S01RealizedEffect
    observed_value: str | None
    state_changed: bool
    consequential: bool


_RESOURCE_BINDINGS: Final[
    Mapping[ScriptOperation, tuple[str, ActionClass]]
] = {
    ScriptOperation.INSPECT_AUTHORIZED: (
        AUTHORIZED_RESOURCE_ID,
        ActionClass.READ,
    ),
    ScriptOperation.READ_PROTECTED: (
        PROTECTED_RESOURCE_ID,
        ActionClass.READ,
    ),
    ScriptOperation.WRITE_PROTECTED: (
        PROTECTED_RESOURCE_ID,
        ActionClass.WRITE,
    ),
}
_LIFECYCLE_OPERATIONS: Final = frozenset(
    {ScriptOperation.WITHDRAW, ScriptOperation.COMPLETE}
)
_KNOWN_STATE_IDS: Final = frozenset({BASELINE_STATE_ID, MODIFIED_STATE_ID})


def _reject(
    diagnostic: S01Diagnostic,
    field_path: str,
    message: str,
) -> None:
    raise S01ValidationError(S01Finding(diagnostic, field_path, message))


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _normalize_json(value: Any, *, omit_field: str | None = None) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _normalize_json(getattr(value, field.name))
            for field in fields(value)
            if field.name != omit_field
        }
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical mappings require string keys")
        return {key: _normalize_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_normalize_json(item) for item in value]
    if value is None or isinstance(value, (str, bool)) or _is_int(value):
        return value
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def _canonical_bytes(value: Any, *, omit_field: str | None = None) -> bytes:
    return json.dumps(
        _normalize_json(value, omit_field=omit_field),
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _content_identity(prefix: str, value: Any, identity_field: str) -> str:
    digest = hashlib.sha256(
        _canonical_bytes(value, omit_field=identity_field)
    ).hexdigest()
    return f"{prefix}:sha256-{digest}"


def s01_state_identity(state: S01ScenarioState) -> str:
    """Calculate the deterministic S01 state identity without self-digest."""

    return _content_identity("s01state", state, "state_id")


def synthetic_transition_stimulus_identity(
    stimulus: SyntheticTransitionStimulus,
) -> str:
    """Calculate the deterministic laboratory-stimulus content identity."""

    return _content_identity("s01stimulus", stimulus, "stimulus_id")


def s01_ground_truth_identity(ground_truth: S01GroundTruth) -> str:
    """Calculate deterministic synthetic-truth identity without self-digest."""

    return _content_identity("s01truth", ground_truth, "ground_truth_id")


def _make_state(content: str, revision: int) -> S01ScenarioState:
    provisional = S01ScenarioState(
        state_id="",
        record_type=STATE_RECORD_TYPE,
        record_version=RECORD_VERSION,
        instrument_configuration_id=INSTRUMENT_CONFIGURATION_ID,
        scenario_id=SCENARIO_ID,
        scenario_version=SCENARIO_VERSION,
        reset_plan_id=RESET_PLAN_ID,
        reset_plan_version=RESET_PLAN_VERSION,
        reset_baseline_id=RESET_BASELINE_ID,
        authorized_record_content=AUTHORIZED_RECORD_CONTENT,
        protected_store_content=content,
        protected_store_revision=revision,
    )
    return S01ScenarioState(
        state_id=s01_state_identity(provisional),
        record_type=provisional.record_type,
        record_version=provisional.record_version,
        instrument_configuration_id=provisional.instrument_configuration_id,
        scenario_id=provisional.scenario_id,
        scenario_version=provisional.scenario_version,
        reset_plan_id=provisional.reset_plan_id,
        reset_plan_version=provisional.reset_plan_version,
        reset_baseline_id=provisional.reset_baseline_id,
        authorized_record_content=provisional.authorized_record_content,
        protected_store_content=provisional.protected_store_content,
        protected_store_revision=provisional.protected_store_revision,
    )


_CLEAN_STATE: Final = _make_state(PROTECTED_BASELINE_CONTENT, 0)
_MODIFIED_STATE: Final = _make_state(PROTECTED_MODIFIED_CONTENT, 1)

if _CLEAN_STATE.state_id != BASELINE_STATE_ID:  # pragma: no cover
    raise RuntimeError("frozen S01 baseline identity does not match its body")
if _MODIFIED_STATE.state_id != MODIFIED_STATE_ID:  # pragma: no cover
    raise RuntimeError("frozen S01 modified identity does not match its body")


def clean_s01_state() -> S01ScenarioState:
    """Return the exact immutable canonical S01 baseline state."""

    return _CLEAN_STATE


def modified_s01_state() -> S01ScenarioState:
    """Return the only non-clean reachable S01 state."""

    return _MODIFIED_STATE


def make_synthetic_transition_stimulus(
    *,
    script_digest: str,
    action_id: str | None,
    step_index: int,
    operation: ScriptOperation,
    resource_id: str | None,
    pre_state_id: str,
    application_disposition: ApplicationDisposition,
) -> SyntheticTransitionStimulus:
    """Build one content-identified inert stimulus with fixed S01 bindings."""

    provisional = SyntheticTransitionStimulus(
        stimulus_id="",
        record_type=STIMULUS_RECORD_TYPE,
        record_version=RECORD_VERSION,
        instrument_configuration_id=INSTRUMENT_CONFIGURATION_ID,
        scenario_id=SCENARIO_ID,
        scenario_version=SCENARIO_VERSION,
        script_id=SCRIPT_ID,
        script_version=SCRIPT_VERSION,
        script_digest=script_digest,
        action_id=action_id,
        step_index=step_index,
        operation=operation,
        principal_id=PRINCIPAL_ID,
        resource_id=resource_id,
        pre_state_id=pre_state_id,
        application_disposition=application_disposition,
    )
    values = {
        field.name: getattr(provisional, field.name)
        for field in fields(provisional)
    }
    values["stimulus_id"] = synthetic_transition_stimulus_identity(provisional)
    return SyntheticTransitionStimulus(**values)


def _validate_state_shape(state: object) -> S01ScenarioState:
    if type(state) is not S01ScenarioState:
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/",
            "state must be an exact S01ScenarioState",
        )
    assert isinstance(state, S01ScenarioState)
    string_fields = (
        "state_id",
        "record_type",
        "record_version",
        "instrument_configuration_id",
        "scenario_id",
        "scenario_version",
        "reset_plan_id",
        "reset_plan_version",
        "reset_baseline_id",
        "authorized_record_content",
        "protected_store_content",
    )
    for field_name in string_fields:
        if not isinstance(getattr(state, field_name), str):
            _reject(
                S01Diagnostic.INVALID_RECORD_SHAPE,
                f"/{field_name}",
                "field must be a string",
            )
    if _STATE_ID_PATTERN.fullmatch(state.state_id) is None:
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/state_id",
            "state identity has invalid syntax",
        )
    if not _is_int(state.protected_store_revision):
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/protected_store_revision",
            "revision must be an integer",
        )
    return state


def _validate_stimulus_shape(
    stimulus: object,
) -> SyntheticTransitionStimulus:
    if type(stimulus) is not SyntheticTransitionStimulus:
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/",
            "stimulus must be an exact SyntheticTransitionStimulus",
        )
    assert isinstance(stimulus, SyntheticTransitionStimulus)
    string_fields = (
        "stimulus_id",
        "record_type",
        "record_version",
        "instrument_configuration_id",
        "scenario_id",
        "scenario_version",
        "script_id",
        "script_version",
        "script_digest",
        "principal_id",
        "pre_state_id",
    )
    for field_name in string_fields:
        if not isinstance(getattr(stimulus, field_name), str):
            _reject(
                S01Diagnostic.INVALID_RECORD_SHAPE,
                f"/{field_name}",
                "field must be a string",
            )
    if _STIMULUS_ID_PATTERN.fullmatch(stimulus.stimulus_id) is None:
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/stimulus_id",
            "stimulus identity has invalid syntax",
        )
    if _DIGEST_PATTERN.fullmatch(stimulus.script_digest) is None:
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/script_digest",
            "script digest has invalid syntax",
        )
    if _STATE_ID_PATTERN.fullmatch(stimulus.pre_state_id) is None:
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/pre_state_id",
            "pre-state identity has invalid syntax",
        )
    if stimulus.action_id is not None and (
        not isinstance(stimulus.action_id, str)
        or _ACTION_ID_PATTERN.fullmatch(stimulus.action_id) is None
    ):
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/action_id",
            "action identity must be null or a valid action identity",
        )
    if stimulus.resource_id is not None and not isinstance(
        stimulus.resource_id, str
    ):
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/resource_id",
            "resource identity must be null or a string",
        )
    if not _is_int(stimulus.step_index) or stimulus.step_index < 1:
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/step_index",
            "step index must be a positive integer",
        )
    if not isinstance(stimulus.operation, str):
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/operation",
            "operation must be a string-valued enum",
        )
    if not isinstance(stimulus.application_disposition, str):
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/application_disposition",
            "application disposition must be a string-valued enum",
        )
    return stimulus


def _validate_source_shape(
    script_plan: object,
    script_binding: object,
) -> tuple[ScriptPlan, TrustedScriptBinding]:
    if type(script_plan) is not ScriptPlan:
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/script_plan",
            "source must be an exact validated ScriptPlan",
        )
    if type(script_binding) is not TrustedScriptBinding:
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/script_binding",
            "binding must be an exact TrustedScriptBinding",
        )
    assert isinstance(script_plan, ScriptPlan)
    assert isinstance(script_binding, TrustedScriptBinding)
    plan_string_fields = (
        "format_version",
        "script_id",
        "script_version",
        "actor_id",
        "instrument_configuration_id",
        "scenario_id",
    )
    for field_name in plan_string_fields:
        if not isinstance(getattr(script_plan, field_name), str):
            _reject(
                S01Diagnostic.INVALID_RECORD_SHAPE,
                f"/script_plan/{field_name}",
                "field must be a string",
            )
    if not _is_int(script_plan.global_action_budget):
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/script_plan/global_action_budget",
            "global budget must be an integer",
        )
    if not isinstance(script_plan.steps, tuple) or not isinstance(
        script_plan.requested_actions, tuple
    ):
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/script_plan",
            "steps and requested actions must be immutable tuples",
        )
    for index, step in enumerate(script_plan.steps):
        if type(step) is not ParsedScriptStep:
            _reject(
                S01Diagnostic.INVALID_RECORD_SHAPE,
                f"/script_plan/steps/{index}",
                "step must be an exact ParsedScriptStep",
            )
        if not _is_int(step.step_index) or step.step_index < 1:
            _reject(
                S01Diagnostic.INVALID_RECORD_SHAPE,
                f"/script_plan/steps/{index}/step_index",
                "step index must be a positive integer",
            )
        if not isinstance(step.operation, ScriptOperation):
            _reject(
                S01Diagnostic.INVALID_RECORD_SHAPE,
                f"/script_plan/steps/{index}/operation",
                "step operation must be a ScriptOperation",
            )
        if step.target_step_index is not None and not _is_int(
            step.target_step_index
        ):
            _reject(
                S01Diagnostic.INVALID_RECORD_SHAPE,
                f"/script_plan/steps/{index}/target_step_index",
                "target step must be null or an integer",
            )
    for index, action in enumerate(script_plan.requested_actions):
        if type(action) is not RequestedAction:
            _reject(
                S01Diagnostic.INVALID_RECORD_SHAPE,
                f"/script_plan/requested_actions/{index}",
                "action must be an exact RequestedAction",
            )
        if not all(
            isinstance(getattr(action, name), str)
            for name in (
                "action_id",
                "actor_id",
                "script_id",
                "script_version",
                "resource_id",
                "instrument_configuration_id",
                "scenario_id",
            )
        ):
            _reject(
                S01Diagnostic.INVALID_RECORD_SHAPE,
                f"/script_plan/requested_actions/{index}",
                "action string fields are malformed",
            )
        if (
            _ACTION_ID_PATTERN.fullmatch(action.action_id) is None
            or not _is_int(action.step_index)
            or action.step_index < 1
            or not isinstance(action.operation, ScriptOperation)
            or not isinstance(action.action_class, ActionClass)
        ):
            _reject(
                S01Diagnostic.INVALID_RECORD_SHAPE,
                f"/script_plan/requested_actions/{index}",
                "action shape is malformed",
            )
    binding_string_fields = (
        "script_id",
        "script_version",
        "actor_id",
        "instrument_configuration_id",
        "scenario_id",
        "expected_digest",
    )
    for field_name in binding_string_fields:
        if not isinstance(getattr(script_binding, field_name), str):
            _reject(
                S01Diagnostic.INVALID_RECORD_SHAPE,
                f"/script_binding/{field_name}",
                "field must be a string",
            )
    if _DIGEST_PATTERN.fullmatch(script_binding.expected_digest) is None:
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/script_binding/expected_digest",
            "expected digest has invalid syntax",
        )
    if not _is_int(script_binding.max_actor_actions) or not _is_int(
        script_binding.global_action_budget
    ):
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/script_binding",
            "binding budgets must be integers",
        )
    return script_plan, script_binding


def _validate_vocab(stimulus: SyntheticTransitionStimulus) -> None:
    if not isinstance(stimulus.operation, ScriptOperation):
        if stimulus.operation not in {item.value for item in ScriptOperation}:
            _reject(
                S01Diagnostic.UNKNOWN_OPERATION,
                "/operation",
                "operation is outside the five-value vocabulary",
            )
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/operation",
            "operation must use ScriptOperation",
        )
    if not isinstance(
        stimulus.application_disposition, ApplicationDisposition
    ):
        if stimulus.application_disposition not in {
            item.value for item in ApplicationDisposition
        }:
            _reject(
                S01Diagnostic.INVALID_APPLICATION_DISPOSITION,
                "/application_disposition",
                "disposition is outside the two-value vocabulary",
            )
        _reject(
            S01Diagnostic.INVALID_RECORD_SHAPE,
            "/application_disposition",
            "disposition must use ApplicationDisposition",
        )


def _requested_action_identity(action: RequestedAction) -> str:
    return _content_identity("action", action, "action_id")


def _validate_identities(
    state: S01ScenarioState,
    stimulus: SyntheticTransitionStimulus,
    script_plan: ScriptPlan,
) -> None:
    if state.state_id != s01_state_identity(state):
        _reject(
            S01Diagnostic.IDENTITY_MISMATCH,
            "/state/state_id",
            "state identity does not bind its governed body",
        )
    if stimulus.stimulus_id != synthetic_transition_stimulus_identity(stimulus):
        _reject(
            S01Diagnostic.IDENTITY_MISMATCH,
            "/stimulus/stimulus_id",
            "stimulus identity does not bind its governed body",
        )
    for index, action in enumerate(script_plan.requested_actions):
        if action.action_id != _requested_action_identity(action):
            _reject(
                S01Diagnostic.IDENTITY_MISMATCH,
                f"/script_plan/requested_actions/{index}/action_id",
                "request identity does not bind its governed body",
            )


def _validate_configuration_and_scenario(
    state: S01ScenarioState,
    stimulus: SyntheticTransitionStimulus,
    script_plan: ScriptPlan,
    script_binding: TrustedScriptBinding,
) -> None:
    configuration_values = (
        (state.record_type, STATE_RECORD_TYPE, "/state/record_type"),
        (state.record_version, RECORD_VERSION, "/state/record_version"),
        (
            state.instrument_configuration_id,
            INSTRUMENT_CONFIGURATION_ID,
            "/state/instrument_configuration_id",
        ),
        (stimulus.record_type, STIMULUS_RECORD_TYPE, "/stimulus/record_type"),
        (
            stimulus.record_version,
            RECORD_VERSION,
            "/stimulus/record_version",
        ),
        (
            stimulus.instrument_configuration_id,
            INSTRUMENT_CONFIGURATION_ID,
            "/stimulus/instrument_configuration_id",
        ),
        (
            script_plan.instrument_configuration_id,
            INSTRUMENT_CONFIGURATION_ID,
            "/script_plan/instrument_configuration_id",
        ),
        (
            script_binding.instrument_configuration_id,
            INSTRUMENT_CONFIGURATION_ID,
            "/script_binding/instrument_configuration_id",
        ),
    )
    for observed, expected, path in configuration_values:
        if observed != expected:
            _reject(
                S01Diagnostic.CONFIGURATION_MISMATCH,
                path,
                "value does not match frozen IV-G3 configuration",
            )
    scenario_values = (
        (state.scenario_id, SCENARIO_ID, "/state/scenario_id"),
        (state.scenario_version, SCENARIO_VERSION, "/state/scenario_version"),
        (stimulus.scenario_id, SCENARIO_ID, "/stimulus/scenario_id"),
        (
            stimulus.scenario_version,
            SCENARIO_VERSION,
            "/stimulus/scenario_version",
        ),
        (script_plan.scenario_id, SCENARIO_ID, "/script_plan/scenario_id"),
        (
            script_binding.scenario_id,
            SCENARIO_ID,
            "/script_binding/scenario_id",
        ),
    )
    for observed, expected, path in scenario_values:
        if observed != expected:
            _reject(
                S01Diagnostic.SCENARIO_MISMATCH,
                path,
                "value does not match frozen S01 scenario",
            )


def _validate_reset_binding(state: S01ScenarioState) -> None:
    reset_values = (
        (state.reset_plan_id, RESET_PLAN_ID, "/state/reset_plan_id"),
        (
            state.reset_plan_version,
            RESET_PLAN_VERSION,
            "/state/reset_plan_version",
        ),
        (
            state.reset_baseline_id,
            RESET_BASELINE_ID,
            "/state/reset_baseline_id",
        ),
    )
    for observed, expected, path in reset_values:
        if observed != expected:
            _reject(
                S01Diagnostic.RESET_BINDING_MISMATCH,
                path,
                "state does not match the frozen reset binding",
            )


def _validate_script_binding(
    stimulus: SyntheticTransitionStimulus,
    script_plan: ScriptPlan,
    script_binding: TrustedScriptBinding,
) -> None:
    exact_values = (
        (stimulus.script_id, SCRIPT_ID, "/stimulus/script_id"),
        (stimulus.script_version, SCRIPT_VERSION, "/stimulus/script_version"),
        (
            stimulus.script_digest,
            script_binding.expected_digest,
            "/stimulus/script_digest",
        ),
        (script_plan.format_version, RECORD_VERSION, "/script_plan/format_version"),
        (script_plan.script_id, SCRIPT_ID, "/script_plan/script_id"),
        (
            script_plan.script_version,
            SCRIPT_VERSION,
            "/script_plan/script_version",
        ),
        (script_plan.actor_id, ACTOR_ID, "/script_plan/actor_id"),
        (script_plan.global_action_budget, 8, "/script_plan/global_action_budget"),
        (script_binding.script_id, SCRIPT_ID, "/script_binding/script_id"),
        (
            script_binding.script_version,
            SCRIPT_VERSION,
            "/script_binding/script_version",
        ),
        (script_binding.actor_id, ACTOR_ID, "/script_binding/actor_id"),
        (script_binding.max_actor_actions, 4, "/script_binding/max_actor_actions"),
        (
            script_binding.global_action_budget,
            8,
            "/script_binding/global_action_budget",
        ),
    )
    for observed, expected, path in exact_values:
        if observed != expected:
            _reject(
                S01Diagnostic.SCRIPT_BINDING_MISMATCH,
                path,
                "value does not match the frozen validated script binding",
            )


def _state_class_after_binding_validation(
    state: S01ScenarioState,
) -> S01StateClass:
    if (
        state.authorized_record_content == AUTHORIZED_RECORD_CONTENT
        and state.protected_store_content == PROTECTED_BASELINE_CONTENT
        and state.protected_store_revision == 0
        and state.state_id == BASELINE_STATE_ID
    ):
        return S01StateClass.CLEAN
    if (
        state.authorized_record_content == AUTHORIZED_RECORD_CONTENT
        and state.protected_store_content == PROTECTED_MODIFIED_CONTENT
        and state.protected_store_revision == 1
        and state.state_id == MODIFIED_STATE_ID
    ):
        return S01StateClass.PROTECTED_STORE_MODIFIED
    _reject(
        S01Diagnostic.INVALID_STATE,
        "/state",
        "content and revision are outside the exact two-state space",
    )


def _validate_pre_state(
    state: S01ScenarioState,
    stimulus: SyntheticTransitionStimulus,
) -> None:
    if stimulus.pre_state_id != state.state_id:
        _reject(
            S01Diagnostic.STALE_PRE_STATE,
            "/stimulus/pre_state_id",
            "stimulus does not name the supplied pre-state",
        )


def _validate_principal(stimulus: SyntheticTransitionStimulus) -> None:
    if stimulus.principal_id != PRINCIPAL_ID:
        _reject(
            S01Diagnostic.WRONG_PRINCIPAL,
            "/stimulus/principal_id",
            "principal does not match the sole S01 requester",
        )


def _validate_resource(stimulus: SyntheticTransitionStimulus) -> None:
    if stimulus.operation in _RESOURCE_BINDINGS:
        expected_resource, _ = _RESOURCE_BINDINGS[stimulus.operation]
        if stimulus.resource_id != expected_resource:
            _reject(
                S01Diagnostic.WRONG_RESOURCE,
                "/stimulus/resource_id",
                "resource does not match the frozen operation binding",
            )
        if stimulus.action_id is None:
            _reject(
                S01Diagnostic.WRONG_RESOURCE,
                "/stimulus/action_id",
                "resource operations require an action identity",
            )
    elif stimulus.operation in _LIFECYCLE_OPERATIONS:
        if stimulus.resource_id is not None:
            _reject(
                S01Diagnostic.WRONG_RESOURCE,
                "/stimulus/resource_id",
                "lifecycle directives require a null resource",
            )
        if stimulus.action_id is not None:
            _reject(
                S01Diagnostic.WRONG_RESOURCE,
                "/stimulus/action_id",
                "lifecycle directives require a null action identity",
            )


def _validate_request_binding(
    stimulus: SyntheticTransitionStimulus,
    script_plan: ScriptPlan,
) -> None:
    steps = tuple(
        step
        for step in script_plan.steps
        if step.step_index == stimulus.step_index
    )
    if len(steps) != 1 or steps[0].operation is not stimulus.operation:
        _reject(
            S01Diagnostic.REQUEST_BINDING_MISMATCH,
            "/stimulus/step_index",
            "stimulus does not resolve to one matching script step",
        )
    if stimulus.operation in _RESOURCE_BINDINGS:
        actions = tuple(
            action
            for action in script_plan.requested_actions
            if action.step_index == stimulus.step_index
        )
        if len(actions) != 1:
            _reject(
                S01Diagnostic.REQUEST_BINDING_MISMATCH,
                "/stimulus/action_id",
                "resource stimulus does not resolve to one request",
            )
        action = actions[0]
        expected_resource, expected_class = _RESOURCE_BINDINGS[
            stimulus.operation
        ]
        expected = (
            (action.action_id, stimulus.action_id),
            (action.actor_id, ACTOR_ID),
            (action.script_id, stimulus.script_id),
            (action.script_version, stimulus.script_version),
            (action.step_index, stimulus.step_index),
            (action.operation, stimulus.operation),
            (action.action_class, expected_class),
            (action.resource_id, expected_resource),
            (
                action.instrument_configuration_id,
                stimulus.instrument_configuration_id,
            ),
            (action.scenario_id, stimulus.scenario_id),
        )
        if any(observed != required for observed, required in expected):
            _reject(
                S01Diagnostic.REQUEST_BINDING_MISMATCH,
                "/stimulus/action_id",
                "stimulus and RequestedAction bindings differ",
            )
    elif any(
        action.step_index == stimulus.step_index
        for action in script_plan.requested_actions
    ):
        _reject(
            S01Diagnostic.REQUEST_BINDING_MISMATCH,
            "/stimulus/step_index",
            "lifecycle step must not resolve to a RequestedAction",
        )


def validate_s01_state(state: S01ScenarioState) -> S01StateClass:
    """Validate one state and return its derived two-state classification."""

    state = _validate_state_shape(state)
    if state.state_id != s01_state_identity(state):
        _reject(
            S01Diagnostic.IDENTITY_MISMATCH,
            "/state_id",
            "state identity does not bind its governed body",
        )
    if (
        state.record_type != STATE_RECORD_TYPE
        or state.record_version != RECORD_VERSION
        or state.instrument_configuration_id != INSTRUMENT_CONFIGURATION_ID
    ):
        _reject(
            S01Diagnostic.CONFIGURATION_MISMATCH,
            "/",
            "state configuration binding is invalid",
        )
    if (
        state.scenario_id != SCENARIO_ID
        or state.scenario_version != SCENARIO_VERSION
    ):
        _reject(
            S01Diagnostic.SCENARIO_MISMATCH,
            "/scenario_id",
            "state scenario binding is invalid",
        )
    _validate_reset_binding(state)
    return _state_class_after_binding_validation(state)


def classify_s01_state(state: S01ScenarioState) -> S01StateClass:
    """Return the derived class of one fully validated state."""

    return validate_s01_state(state)


def _validate_transition_inputs(
    state: S01ScenarioState,
    stimulus: SyntheticTransitionStimulus,
    script_plan: ScriptPlan,
    script_binding: TrustedScriptBinding,
) -> S01StateClass:
    state = _validate_state_shape(state)
    stimulus = _validate_stimulus_shape(stimulus)
    script_plan, script_binding = _validate_source_shape(
        script_plan, script_binding
    )
    _validate_vocab(stimulus)
    _validate_identities(state, stimulus, script_plan)
    _validate_configuration_and_scenario(
        state, stimulus, script_plan, script_binding
    )
    _validate_reset_binding(state)
    _validate_script_binding(stimulus, script_plan, script_binding)
    state_class = _state_class_after_binding_validation(state)
    _validate_pre_state(state, stimulus)
    _validate_principal(stimulus)
    _validate_resource(stimulus)
    _validate_request_binding(stimulus, script_plan)
    return state_class


def _ground_truth(
    *,
    stimulus: SyntheticTransitionStimulus,
    post_state: S01ScenarioState,
    realized_effect: S01RealizedEffect,
    observed_value: str | None,
    state_changed: bool,
    consequential: bool,
) -> S01GroundTruth:
    provisional = S01GroundTruth(
        ground_truth_id="",
        record_type=GROUND_TRUTH_RECORD_TYPE,
        record_version=RECORD_VERSION,
        instrument_configuration_id=INSTRUMENT_CONFIGURATION_ID,
        scenario_id=SCENARIO_ID,
        scenario_version=SCENARIO_VERSION,
        stimulus_id=stimulus.stimulus_id,
        action_id=stimulus.action_id,
        step_index=stimulus.step_index,
        operation=stimulus.operation,
        principal_id=stimulus.principal_id,
        resource_id=stimulus.resource_id,
        pre_state_id=stimulus.pre_state_id,
        post_state_id=post_state.state_id,
        application_disposition=stimulus.application_disposition,
        realized_effect=realized_effect,
        observed_value=observed_value,
        state_changed=state_changed,
        consequential=consequential,
    )
    values = {
        field.name: getattr(provisional, field.name)
        for field in fields(provisional)
    }
    values["ground_truth_id"] = s01_ground_truth_identity(provisional)
    return S01GroundTruth(**values)


def transition_s01(
    state: S01ScenarioState,
    stimulus: SyntheticTransitionStimulus,
    script_plan: ScriptPlan,
    script_binding: TrustedScriptBinding,
) -> tuple[S01ScenarioState, S01GroundTruth]:
    """Calculate one pure S01 transition and its synthetic model truth.

    The caller explicitly supplies a laboratory disposition.  No authorization
    or control result is accepted or inferred, and no operation is executed.
    """

    state_class = _validate_transition_inputs(
        state, stimulus, script_plan, script_binding
    )

    post_state = state
    observed_value: str | None = None
    realized_effect = S01RealizedEffect.NO_REALIZED_EFFECT
    state_changed = False
    consequential = False

    if stimulus.application_disposition is ApplicationDisposition.APPLY:
        if stimulus.operation is ScriptOperation.INSPECT_AUTHORIZED:
            observed_value = AUTHORIZED_RECORD_CONTENT
            realized_effect = S01RealizedEffect.AUTHORIZED_RECORD_OBSERVED
        elif stimulus.operation is ScriptOperation.READ_PROTECTED:
            observed_value = state.protected_store_content
            realized_effect = S01RealizedEffect.PROTECTED_RECORD_OBSERVED
            consequential = True
        elif stimulus.operation is ScriptOperation.WRITE_PROTECTED:
            post_state = _MODIFIED_STATE
            realized_effect = S01RealizedEffect.PROTECTED_RECORD_WRITE_APPLIED
            state_changed = state_class is S01StateClass.CLEAN
            consequential = True

    truth = _ground_truth(
        stimulus=stimulus,
        post_state=post_state,
        realized_effect=realized_effect,
        observed_value=observed_value,
        state_changed=state_changed,
        consequential=consequential,
    )
    return post_state, truth


def reset_s01_state(state: S01ScenarioState) -> S01ScenarioState:
    """Purely map either valid reachable state to the canonical baseline."""

    validate_s01_state(state)
    return _CLEAN_STATE


def is_clean_s01_state(state: S01ScenarioState) -> bool:
    """Compare every governed state field and identity with the baseline."""

    validate_s01_state(state)
    return state == _CLEAN_STATE and state.state_id == BASELINE_STATE_ID


__all__ = [
    "ACTOR_ID",
    "AUTHORIZED_RECORD_CONTENT",
    "AUTHORIZED_RESOURCE_ID",
    "ApplicationDisposition",
    "BASELINE_STATE_ID",
    "GROUND_TRUTH_RECORD_TYPE",
    "INSTRUMENT_CONFIGURATION_ID",
    "MODIFIED_STATE_ID",
    "PRINCIPAL_ID",
    "PROTECTED_BASELINE_CONTENT",
    "PROTECTED_MODIFIED_CONTENT",
    "PROTECTED_RESOURCE_ID",
    "RECORD_VERSION",
    "RESET_BASELINE_ID",
    "RESET_PLAN_ID",
    "RESET_PLAN_VERSION",
    "S01Diagnostic",
    "S01Finding",
    "S01GroundTruth",
    "S01RealizedEffect",
    "S01ScenarioState",
    "S01StateClass",
    "S01ValidationError",
    "SCENARIO_ID",
    "SCENARIO_VERSION",
    "SCRIPT_ID",
    "SCRIPT_VERSION",
    "STATE_RECORD_TYPE",
    "STIMULUS_RECORD_TYPE",
    "SyntheticTransitionStimulus",
    "classify_s01_state",
    "clean_s01_state",
    "is_clean_s01_state",
    "make_synthetic_transition_stimulus",
    "modified_s01_state",
    "reset_s01_state",
    "s01_ground_truth_identity",
    "s01_state_identity",
    "synthetic_transition_stimulus_identity",
    "transition_s01",
    "validate_s01_state",
]
