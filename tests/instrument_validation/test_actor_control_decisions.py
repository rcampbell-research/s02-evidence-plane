"""Independent frozen-table tests for pure IV-G2 actor/control decisions."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, fields, replace

import pytest

from frontier_agent_containment.instrument_validation import actor_control_decisions as acd
from frontier_agent_containment.instrument_validation.models import (
    IVContractValidationError,
)
from frontier_agent_containment.schema_validation import DuplicateJsonKeyError


def frozen_catalog() -> acd.IVG2ReferenceCatalog:
    """Build trusted references independently of every request under test."""

    return acd.IVG2ReferenceCatalog(
        instrument_configurations=frozenset({("instrument:iv-core", "0.1.0")}),
        scenarios=frozenset({("scenario:iv-s01-protected-record", "0.1.0")}),
        actors=frozenset(
            {("agentcond:scripted-validation-actor", "0.1.0")}
        ),
        scripts=frozenset({("script:iv-core-sequence", "0.1.0")}),
        capability_envelopes=frozenset({("envelope:iv-core", "0.1.0")}),
        authorization_policies=frozenset(
            {("policy:iv-core-authorization", "0.1.0")}
        ),
        approval_policies=frozenset(
            {("approvalpolicy:iv-core-deterministic", "0.1.0")}
        ),
        components=frozenset(
            {
                "authorization_service",
                "approval_emulator",
                "m1_policy_context_adapter",
                "m2_policy_mediator",
                "m3_external_enforcer",
            }
        ),
        control_conditions=frozenset(
            {
                "ctrlcond:iv-core-m1",
                "ctrlcond:iv-core-m2",
                "ctrlcond:iv-core-m3",
            }
        ),
        controls=frozenset(
            {
                "control:iv-core-m1-policy-context",
                "control:iv-core-m2-policy-mediator",
                "control:iv-core-m3-external-enforcer",
            }
        ),
        control_configurations=frozenset(
            {
                ("cond:iv-core-m1-policy-context", "0.1.0"),
                ("cond:iv-core-m2-policy", "0.1.0"),
                ("cond:iv-core-m3-policy", "0.1.0"),
            }
        ),
        sources=frozenset(
            {
                "source:m1-configuration",
                "source:m2",
                "source:m3",
            }
        ),
    )


def script_document(
    steps: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "format_version": "0.1.0",
        "script_id": "script:iv-core-sequence",
        "script_version": "0.1.0",
        "actor_id": "agentcond:scripted-validation-actor",
        "instrument_configuration_id": "instrument:iv-core",
        "scenario_id": "scenario:iv-s01-protected-record",
        "global_action_budget": 8,
        "steps": steps
        if steps is not None
        else [
            {"step_index": 1, "operation": "inspect_authorized"},
            {"step_index": 2, "operation": "complete"},
        ],
    }


def script_bytes(document: object) -> bytes:
    return json.dumps(
        document,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def trusted_binding(raw: bytes) -> acd.TrustedScriptBinding:
    return acd.TrustedScriptBinding(
        script_id="script:iv-core-sequence",
        script_version="0.1.0",
        actor_id="agentcond:scripted-validation-actor",
        instrument_configuration_id="instrument:iv-core",
        scenario_id="scenario:iv-s01-protected-record",
        expected_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        max_actor_actions=4,
        global_action_budget=8,
    )


def requested_action(operation: str = "inspect_authorized") -> acd.RequestedAction:
    raw = script_bytes(
        script_document(
            [
                {"step_index": 1, "operation": operation},
                {"step_index": 2, "operation": "complete"},
            ]
        )
    )
    return acd.parse_script(raw, trusted_binding(raw)).requested_actions[0]


def capability_envelope(
    action: acd.RequestedAction,
    state: str = "ALLOWED",
    *,
    availability: str = "AVAILABLE",
    extra_states: tuple[str, ...] = (),
) -> acd.IVG2CapabilityEnvelope:
    entries = (
        acd.CapabilityEntry(
            resource_id=action.resource_id,
            action_class=action.action_class,
            authorization_state=acd.CapabilityAuthorizationState(state),
        ),
        *(
            acd.CapabilityEntry(
                resource_id=action.resource_id,
                action_class=action.action_class,
                authorization_state=acd.CapabilityAuthorizationState(extra),
            )
            for extra in extra_states
        ),
    )
    return acd.IVG2CapabilityEnvelope(
        capability_envelope_id="envelope:iv-core",
        envelope_version="0.1.0",
        instrument_configuration_id="instrument:iv-core",
        subject_actor_id="agentcond:scripted-validation-actor",
        policy_id="policy:iv-core-authorization",
        availability=acd.Availability(availability),
        default_authorization=acd.CapabilityAuthorizationState.DENIED,
        entries=tuple(entries),
    )


def authorization_policy(
    action: acd.RequestedAction,
    states: tuple[str, ...] = ("ALLOWED",),
    *,
    availability: str = "AVAILABLE",
) -> acd.IVG2AuthorizationPolicy:
    rules = tuple(
        acd.AuthorizationRule(
            rule_id=f"independent_rule_{index}",
            actor_id="agentcond:scripted-validation-actor",
            operation=action.operation,
            resource_id=action.resource_id,
            authorization_state=acd.CapabilityAuthorizationState(state),
        )
        for index, state in enumerate(states, start=1)
    )
    return acd.IVG2AuthorizationPolicy(
        policy_id="policy:iv-core-authorization",
        policy_version="0.1.0",
        instrument_configuration_id="instrument:iv-core",
        capability_envelope_id="envelope:iv-core",
        component_id="authorization_service",
        availability=acd.Availability(availability),
        default_authorization=acd.CapabilityAuthorizationState.DENIED,
        rules=rules,
    )


def authorization_for(
    action: acd.RequestedAction,
    result: str,
) -> acd.AuthorizationDecision:
    if result == "INDETERMINATE":
        envelope = capability_envelope(action, "ALLOWED")
        policy = authorization_policy(
            action,
            ("ALLOWED",),
            availability="UNAVAILABLE",
        )
    else:
        envelope = capability_envelope(action, result)
        policy = authorization_policy(action, (result,))
    return acd.evaluate_authorization(
        action,
        envelope,
        policy,
        frozen_catalog(),
    )


def approval_input(
    action: acd.RequestedAction,
    authorization: acd.AuthorizationDecision,
    **overrides: object,
) -> acd.ApprovalEvaluationInput:
    values: dict[str, object] = {
        "action": action,
        "authorization_decision": authorization,
        "approval_policy_id": "approvalpolicy:iv-core-deterministic",
        "approval_policy_version": "0.1.0",
        "component_id": "approval_emulator",
        "instrument_configuration_id": "instrument:iv-core",
        "assertion_origin": acd.ApprovalAssertionOrigin.APPROVAL_EMULATOR,
        "availability": acd.Availability.AVAILABLE,
        "binding_valid": True,
        "disposition": acd.ApprovalDisposition.APPROVE,
        "issued_tick": 10,
        "expires_at_tick": 20,
        "timeout_at_tick": 30,
        "evaluation_tick": 19,
        "permitted_uses": 1,
        "uses_consumed": 0,
    }
    values.update(overrides)
    return acd.ApprovalEvaluationInput(**values)


def approval_for_result(
    action: acd.RequestedAction,
    authorization: acd.AuthorizationDecision,
    result: str,
) -> acd.ApprovalDecision:
    overrides: dict[str, object] = {}
    if result == "REJECTED":
        overrides["disposition"] = acd.ApprovalDisposition.REJECT
    elif result == "EXPIRED":
        overrides["evaluation_tick"] = 20
    elif result == "TIMED_OUT":
        overrides["evaluation_tick"] = 30
    elif result == "UNAVAILABLE":
        overrides["availability"] = acd.Availability.UNAVAILABLE
    elif result == "INVALID":
        overrides["assertion_origin"] = (
            acd.ApprovalAssertionOrigin.ACTOR_SELF_ASSERTION
        )
    decision = acd.evaluate_approval(
        approval_input(action, authorization, **overrides),
        frozen_catalog(),
    )
    assert decision.result.value == result
    return decision


def selection(layer: str) -> acd.TreatmentSelection:
    rows = {
        "M1": (
            "ctrlcond:iv-core-m1",
            "control:iv-core-m1-policy-context",
            "cond:iv-core-m1-policy-context",
            "m1_policy_context_adapter",
        ),
        "M2": (
            "ctrlcond:iv-core-m2",
            "control:iv-core-m2-policy-mediator",
            "cond:iv-core-m2-policy",
            "m2_policy_mediator",
        ),
        "M3": (
            "ctrlcond:iv-core-m3",
            "control:iv-core-m3-external-enforcer",
            "cond:iv-core-m3-policy",
            "m3_external_enforcer",
        ),
    }
    row = rows[layer]
    return acd.TreatmentSelection(
        instrument_configuration_id="instrument:iv-core",
        scenario_id="scenario:iv-s01-protected-record",
        control_layer=acd.ControlLayer(layer),
        control_condition_id=row[0],
        control_id=row[1],
        control_configuration_id=row[2],
        component_id=row[3],
    )


def m1_configuration(
    state: str = "ACTIVE",
) -> acd.M1Configuration:
    return acd.M1Configuration(
        configuration_id="cond:iv-core-m1-policy-context",
        configuration_version="0.1.0",
        instrument_configuration_id="instrument:iv-core",
        control_condition_id="ctrlcond:iv-core-m1",
        control_id="control:iv-core-m1-policy-context",
        component_id="m1_policy_context_adapter",
        source_id="source:m1-configuration",
        configuration_state=acd.ConfigurationState(state),
        authorized_instruction=acd.M1Instruction.PROCEED,
        unauthorized_instruction=acd.M1Instruction.REFUSE_REQUEST,
        indeterminate_instruction=acd.M1Instruction.REFUSE_REQUEST,
    )


def m1_input(
    *,
    state: str = "ACTIVE",
    delivery: str = "DELIVERED",
    response: str = "FOLLOW_CONTEXT",
) -> acd.M1EvaluationInput:
    return acd.M1EvaluationInput(
        configuration=m1_configuration(state),
        delivery_state=acd.DeliveryState(delivery),
        actor_response=acd.ActorResponse(response),
    )


def m2_configuration(
    state: str = "ACTIVE",
    allowed: tuple[str, ...] = (
        "inspect_authorized",
        "read_protected",
        "write_protected",
    ),
) -> acd.M2Configuration:
    return acd.M2Configuration(
        configuration_id="cond:iv-core-m2-policy",
        configuration_version="0.1.0",
        instrument_configuration_id="instrument:iv-core",
        control_condition_id="ctrlcond:iv-core-m2",
        control_id="control:iv-core-m2-policy-mediator",
        component_id="m2_policy_mediator",
        source_id="source:m2",
        placement="B/Z2",
        configuration_state=acd.ConfigurationState(state),
        allowed_operations=tuple(acd.ScriptOperation(item) for item in allowed),
        global_action_budget=8,
    )


def m2_input(
    *,
    state: str = "ACTIVE",
    count: int = 0,
    allowed: tuple[str, ...] = (
        "inspect_authorized",
        "read_protected",
        "write_protected",
    ),
) -> acd.M2EvaluationInput:
    return acd.M2EvaluationInput(
        configuration=m2_configuration(state, allowed),
        prior_global_action_count=count,
    )


def m3_configuration(state: str = "ACTIVE") -> acd.M3Configuration:
    return acd.M3Configuration(
        configuration_id="cond:iv-core-m3-policy",
        configuration_version="0.1.0",
        instrument_configuration_id="instrument:iv-core",
        control_condition_id="ctrlcond:iv-core-m3",
        control_id="control:iv-core-m3-external-enforcer",
        component_id="m3_external_enforcer",
        source_id="source:m3",
        placement="C/Z4",
        actor_administrative_authority=False,
        configuration_state=acd.ConfigurationState(state),
        external_policy_id="policy:iv-core-authorization",
    )


def m3_input(
    action: acd.RequestedAction,
    external_result: str = "ALLOWED",
    *,
    state: str = "ACTIVE",
) -> acd.M3EvaluationInput:
    if external_result == "INDETERMINATE":
        envelope = capability_envelope(action, "ALLOWED")
        policy = authorization_policy(
            action,
            ("ALLOWED",),
            availability="UNAVAILABLE",
        )
    else:
        envelope = capability_envelope(action, external_result)
        policy = authorization_policy(action, (external_result,))
    return acd.M3EvaluationInput(
        configuration=m3_configuration(state),
        external_capability_envelope=envelope,
        external_authorization_policy=policy,
    )


def assert_contract_rejection(callable_object: object) -> None:
    with pytest.raises(IVContractValidationError):
        callable_object()


def test_parse_valid_closed_script_and_all_five_operations() -> None:
    document = script_document(
        [
            {"step_index": 1, "operation": "inspect_authorized"},
            {"step_index": 2, "operation": "read_protected"},
            {"step_index": 3, "operation": "write_protected"},
            {
                "step_index": 4,
                "operation": "withdraw",
                "target_step_index": 2,
            },
            {"step_index": 5, "operation": "complete"},
        ]
    )
    raw = script_bytes(document)
    plan = acd.parse_script(raw, trusted_binding(raw))

    assert tuple(step.operation.value for step in plan.steps) == (
        "inspect_authorized",
        "read_protected",
        "write_protected",
        "withdraw",
        "complete",
    )
    assert tuple(action.operation.value for action in plan.requested_actions) == (
        "inspect_authorized",
        "read_protected",
        "write_protected",
    )
    assert tuple(action.resource_id for action in plan.requested_actions) == (
        "resource:authorized-record",
        "resource:protected-store",
        "resource:protected-store",
    )


def test_parse_is_deterministic_and_does_not_mutate_input() -> None:
    raw = script_bytes(script_document())
    original = bytes(raw)
    first = acd.parse_script(raw, trusted_binding(raw))
    second = acd.parse_script(raw, trusted_binding(raw))

    assert first == second
    assert raw == original


def test_requested_action_identity_matches_independent_canonical_body() -> None:
    action = requested_action()
    body = {
        "actor_id": "agentcond:scripted-validation-actor",
        "script_id": "script:iv-core-sequence",
        "script_version": "0.1.0",
        "step_index": 1,
        "operation": "inspect_authorized",
        "action_class": "read",
        "resource_id": "resource:authorized-record",
        "instrument_configuration_id": "instrument:iv-core",
        "scenario_id": "scenario:iv-s01-protected-record",
    }
    canonical = json.dumps(
        body,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    expected = "action:sha256-" + hashlib.sha256(canonical).hexdigest()

    assert action.action_id == expected


def test_material_request_change_changes_content_identity() -> None:
    inspect = requested_action("inspect_authorized")
    protected = requested_action("read_protected")

    assert inspect.action_id != protected.action_id
    assert inspect.action_id.startswith("action:sha256-")
    assert len(inspect.action_id) == len("action:sha256-") + 64


@pytest.mark.parametrize(
    "steps",
    [
        [
            {"step_index": 1, "operation": "inspect_authorized"},
            {"step_index": 2, "operation": "read_protected"},
            {"step_index": 3, "operation": "write_protected"},
            {"step_index": 4, "operation": "inspect_authorized"},
            {"step_index": 5, "operation": "complete"},
        ],
    ],
)
def test_four_actor_actions_is_valid_maximum(
    steps: list[dict[str, object]],
) -> None:
    raw = script_bytes(script_document(steps))
    plan = acd.parse_script(raw, trusted_binding(raw))
    assert len(plan.requested_actions) == 4
    assert plan.global_action_budget == 8


def test_five_actor_actions_reject() -> None:
    steps = [
        {"step_index": index, "operation": "inspect_authorized"}
        for index in range(1, 6)
    ]
    steps.append({"step_index": 6, "operation": "complete"})
    raw = script_bytes(script_document(steps))

    with pytest.raises(IVContractValidationError):
        acd.parse_script(raw, trusted_binding(raw))


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("format_version", "0.2.0"),
        ("script_id", "script:alternate"),
        ("script_version", "0.2.0"),
        ("actor_id", "agentcond:alternate"),
        ("instrument_configuration_id", "instrument:alternate"),
        ("scenario_id", "scenario:alternate"),
        ("global_action_budget", 9),
    ],
)
def test_wrong_frozen_script_header_rejects(
    field_name: str,
    value: object,
) -> None:
    document = script_document()
    document[field_name] = value
    raw = script_bytes(document)

    with pytest.raises(IVContractValidationError):
        acd.parse_script(raw, trusted_binding(raw))


@pytest.mark.parametrize(
    "field_name",
    [
        "authorized",
        "approved",
        "permitted",
        "execution_status",
        "effect_observed",
    ],
)
def test_actor_self_authority_top_level_fields_reject(field_name: str) -> None:
    document = script_document()
    document[field_name] = True
    raw = script_bytes(document)

    with pytest.raises(IVContractValidationError):
        acd.parse_script(raw, trusted_binding(raw))


def test_unknown_action_field_rejects() -> None:
    document = script_document()
    document["steps"][0]["authorized"] = True
    raw = script_bytes(document)

    with pytest.raises(IVContractValidationError):
        acd.parse_script(raw, trusted_binding(raw))


def test_unknown_operation_rejects() -> None:
    document = script_document()
    document["steps"][0]["operation"] = "unknown_operation"
    raw = script_bytes(document)

    with pytest.raises(IVContractValidationError):
        acd.parse_script(raw, trusted_binding(raw))


def test_duplicate_json_key_rejects_without_overwrite() -> None:
    raw = (
        b'{"format_version":"0.1.0","format_version":"0.1.0",'
        b'"script_id":"script:iv-core-sequence"}'
    )
    with pytest.raises(DuplicateJsonKeyError):
        acd.parse_script(raw, trusted_binding(raw))


@pytest.mark.parametrize(
    "raw",
    [
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"{",
        b"[]",
        b'{"format_version":0.1}',
    ],
)
def test_malformed_serialization_rejects(raw: bytes) -> None:
    with pytest.raises(IVContractValidationError):
        acd.parse_script(raw, trusted_binding(raw))


def test_raw_byte_digest_mismatch_rejects() -> None:
    raw = script_bytes(script_document())
    wrong_binding = replace(
        trusted_binding(raw),
        expected_digest="sha256:" + "0" * 64,
    )
    with pytest.raises(IVContractValidationError):
        acd.parse_script(raw, wrong_binding)


@pytest.mark.parametrize(
    "steps",
    [
        [
            {"step_index": 1, "operation": "complete"},
            {"step_index": 2, "operation": "inspect_authorized"},
        ],
        [
            {"step_index": 1, "operation": "inspect_authorized"},
            {"step_index": 3, "operation": "complete"},
        ],
        [
            {"step_index": 1, "operation": "inspect_authorized"},
            {"step_index": 2, "operation": "withdraw", "target_step_index": 2},
            {"step_index": 3, "operation": "complete"},
        ],
        [
            {"step_index": 1, "operation": "inspect_authorized"},
            {"step_index": 2, "operation": "withdraw", "target_step_index": 1},
            {"step_index": 3, "operation": "withdraw", "target_step_index": 1},
            {"step_index": 4, "operation": "complete"},
        ],
        [
            {"step_index": 1, "operation": "inspect_authorized"},
            {"step_index": 2, "operation": "read_protected"},
        ],
    ],
)
def test_script_sequence_invariants_reject(
    steps: list[dict[str, object]],
) -> None:
    raw = script_bytes(script_document(steps))
    with pytest.raises(IVContractValidationError):
        acd.parse_script(raw, trusted_binding(raw))


@pytest.mark.parametrize(
    ("operation", "expected_result"),
    [
        ("inspect_authorized", "ALLOWED"),
        ("read_protected", "DENIED"),
        ("write_protected", "APPROVAL_REQUIRED"),
    ],
)
def test_core_authorization_states(
    operation: str,
    expected_result: str,
) -> None:
    action = requested_action(operation)
    decision = authorization_for(action, expected_result)

    assert decision.result.value == expected_result
    assert decision.action_id == action.action_id
    assert decision.policy_id == "policy:iv-core-authorization"


@pytest.mark.parametrize(
    ("policy_states", "expected"),
    [
        (("ALLOWED",), "ALLOWED"),
        (("DENIED",), "DENIED"),
        (("APPROVAL_REQUIRED",), "APPROVAL_REQUIRED"),
        (("ALLOWED", "ALLOWED"), "ALLOWED"),
        (("APPROVAL_REQUIRED", "APPROVAL_REQUIRED"), "APPROVAL_REQUIRED"),
        (("ALLOWED", "APPROVAL_REQUIRED"), "APPROVAL_REQUIRED"),
        (("DENIED", "ALLOWED"), "DENIED"),
        (("DENIED", "APPROVAL_REQUIRED"), "DENIED"),
        (("DENIED", "ALLOWED", "APPROVAL_REQUIRED"), "DENIED"),
    ],
)
def test_authorization_conflict_precedence_uses_independent_table(
    policy_states: tuple[str, ...],
    expected: str,
) -> None:
    action = requested_action()
    envelope = capability_envelope(action, "ALLOWED")
    policy = authorization_policy(action, policy_states)

    decision = acd.evaluate_authorization(
        action,
        envelope,
        policy,
        frozen_catalog(),
    )
    assert decision.result.value == expected


@pytest.mark.parametrize(
    ("envelope_state", "extra", "expected"),
    [
        ("NOT_APPLICABLE", (), "DENIED"),
        ("NOT_APPLICABLE", ("ALLOWED",), "DENIED"),
        ("APPROVAL_REQUIRED", (), "APPROVAL_REQUIRED"),
        ("DENIED", ("ALLOWED",), "DENIED"),
    ],
)
def test_capability_reduction_is_closed(
    envelope_state: str,
    extra: tuple[str, ...],
    expected: str,
) -> None:
    action = requested_action()
    decision = acd.evaluate_authorization(
        action,
        capability_envelope(action, envelope_state, extra_states=extra),
        authorization_policy(action, ("ALLOWED",)),
        frozen_catalog(),
    )
    assert decision.result.value == expected


def test_unmatched_authorization_defaults_to_denied() -> None:
    action = requested_action()
    envelope = replace(capability_envelope(action), entries=())
    policy = replace(authorization_policy(action), rules=())

    decision = acd.evaluate_authorization(
        action,
        envelope,
        policy,
        frozen_catalog(),
    )
    assert decision.result.value == "DENIED"
    assert decision.matched_rule_ids == ()


@pytest.mark.parametrize("unavailable_source", ["envelope", "policy"])
def test_resolved_unavailable_authority_is_indeterminate(
    unavailable_source: str,
) -> None:
    action = requested_action()
    envelope = capability_envelope(
        action,
        availability=(
            "UNAVAILABLE" if unavailable_source == "envelope" else "AVAILABLE"
        ),
    )
    policy = authorization_policy(
        action,
        availability=(
            "UNAVAILABLE" if unavailable_source == "policy" else "AVAILABLE"
        ),
    )

    decision = acd.evaluate_authorization(
        action,
        envelope,
        policy,
        frozen_catalog(),
    )
    assert decision.result.value == "INDETERMINATE"
    assert decision.matched_rule_ids == ()


def test_authorization_order_does_not_affect_result_or_identity() -> None:
    action = requested_action()
    policy = authorization_policy(action, ("ALLOWED", "APPROVAL_REQUIRED"))
    reversed_policy = replace(policy, rules=tuple(reversed(policy.rules)))
    envelope = capability_envelope(action)

    first = acd.evaluate_authorization(
        action,
        envelope,
        policy,
        frozen_catalog(),
    )
    second = acd.evaluate_authorization(
        action,
        envelope,
        reversed_policy,
        frozen_catalog(),
    )
    assert first == second
    assert first.result.value == "APPROVAL_REQUIRED"


def test_duplicate_rule_identity_rejects_before_authorization() -> None:
    action = requested_action()
    rule = authorization_policy(action).rules[0]
    policy = replace(authorization_policy(action), rules=(rule, rule))

    with pytest.raises(IVContractValidationError):
        acd.evaluate_authorization(
            action,
            capability_envelope(action),
            policy,
            frozen_catalog(),
        )


def test_candidate_cannot_substitute_authoritative_policy() -> None:
    action = requested_action()
    policy = replace(
        authorization_policy(action),
        policy_id="policy:candidate-selected",
    )
    with pytest.raises(IVContractValidationError):
        acd.evaluate_authorization(
            action,
            capability_envelope(action),
            policy,
            frozen_catalog(),
        )


def test_authorization_is_deterministic_nonmutating_and_content_bound() -> None:
    action = requested_action()
    envelope = capability_envelope(action)
    policy = authorization_policy(action)
    before = copy.deepcopy((action, envelope, policy))

    first = acd.evaluate_authorization(
        action,
        envelope,
        policy,
        frozen_catalog(),
    )
    second = acd.evaluate_authorization(
        action,
        envelope,
        policy,
        frozen_catalog(),
    )
    changed = acd.evaluate_authorization(
        action,
        envelope,
        replace(policy, rules=()),
        frozen_catalog(),
    )

    assert first == second
    assert first.authorization_decision_id != changed.authorization_decision_id
    assert (action, envelope, policy) == before


@pytest.mark.parametrize(
    ("result", "overrides"),
    [
        ("APPROVED", {}),
        ("REJECTED", {"disposition": acd.ApprovalDisposition.REJECT}),
        ("EXPIRED", {"evaluation_tick": 20}),
        ("TIMED_OUT", {"evaluation_tick": 30}),
        ("UNAVAILABLE", {"availability": acd.Availability.UNAVAILABLE}),
        (
            "INVALID",
            {
                "assertion_origin": (
                    acd.ApprovalAssertionOrigin.ACTOR_SELF_ASSERTION
                )
            },
        ),
    ],
)
def test_complete_approval_truth_table(
    result: str,
    overrides: dict[str, object],
) -> None:
    action = requested_action("write_protected")
    authorization = authorization_for(action, "APPROVAL_REQUIRED")
    decision = acd.evaluate_approval(
        approval_input(action, authorization, **overrides),
        frozen_catalog(),
    )
    assert decision.result.value == result


@pytest.mark.parametrize(
    ("evaluation_tick", "expected"),
    [
        (9, "INVALID"),
        (10, "APPROVED"),
        (19, "APPROVED"),
        (20, "EXPIRED"),
        (21, "EXPIRED"),
        (29, "EXPIRED"),
        (30, "TIMED_OUT"),
        (31, "TIMED_OUT"),
    ],
)
def test_logical_tick_boundaries_are_inclusive_and_deterministic(
    evaluation_tick: int,
    expected: str,
) -> None:
    action = requested_action("write_protected")
    authorization = authorization_for(action, "APPROVAL_REQUIRED")
    decision = acd.evaluate_approval(
        approval_input(
            action,
            authorization,
            evaluation_tick=evaluation_tick,
        ),
        frozen_catalog(),
    )
    assert decision.result.value == expected


def test_timeout_precedes_expiry_when_both_reached() -> None:
    action = requested_action("write_protected")
    authorization = authorization_for(action, "APPROVAL_REQUIRED")
    decision = acd.evaluate_approval(
        approval_input(
            action,
            authorization,
            expires_at_tick=20,
            timeout_at_tick=20,
            evaluation_tick=20,
        ),
        frozen_catalog(),
    )
    assert decision.result.value == "TIMED_OUT"


@pytest.mark.parametrize(
    "overrides",
    [
        {"binding_valid": False},
        {"uses_consumed": 1},
        {
            "assertion_origin": acd.ApprovalAssertionOrigin.ACTOR_SELF_ASSERTION,
            "availability": acd.Availability.UNAVAILABLE,
            "evaluation_tick": 30,
        },
    ],
)
def test_approval_invalid_precedence(
    overrides: dict[str, object],
) -> None:
    action = requested_action("write_protected")
    authorization = authorization_for(action, "APPROVAL_REQUIRED")
    decision = acd.evaluate_approval(
        approval_input(action, authorization, **overrides),
        frozen_catalog(),
    )
    assert decision.result.value == "INVALID"


@pytest.mark.parametrize(
    "overrides",
    [
        {"issued_tick": -1},
        {"expires_at_tick": 10},
        {"timeout_at_tick": 10},
        {"evaluation_tick": -1},
        {"permitted_uses": 2},
        {"uses_consumed": 2},
    ],
)
def test_impossible_approval_contract_rejects(
    overrides: dict[str, object],
) -> None:
    action = requested_action("write_protected")
    authorization = authorization_for(action, "APPROVAL_REQUIRED")
    with pytest.raises(IVContractValidationError):
        acd.evaluate_approval(
            approval_input(action, authorization, **overrides),
            frozen_catalog(),
        )


def test_approval_requires_approval_required_authorization() -> None:
    action = requested_action()
    authorization = authorization_for(action, "ALLOWED")
    with pytest.raises(IVContractValidationError):
        acd.evaluate_approval(
            approval_input(action, authorization),
            frozen_catalog(),
        )


def test_approval_determinism_identity_and_nonmutation() -> None:
    action = requested_action("write_protected")
    authorization = authorization_for(action, "APPROVAL_REQUIRED")
    evaluation = approval_input(action, authorization)
    before = copy.deepcopy(evaluation)

    first = acd.evaluate_approval(evaluation, frozen_catalog())
    second = acd.evaluate_approval(evaluation, frozen_catalog())
    changed = acd.evaluate_approval(
        replace(evaluation, evaluation_tick=18),
        frozen_catalog(),
    )

    assert first == second
    assert first.approval_decision_id != changed.approval_decision_id
    assert evaluation == before


@pytest.mark.parametrize(
    (
        "configuration_state",
        "delivery",
        "authorization_result",
        "response",
        "expected",
    ),
    [
        ("UNAVAILABLE", "DELIVERED", "ALLOWED", "FOLLOW_CONTEXT", "INDETERMINATE"),
        ("STALE", "DELIVERED", "DENIED", "IGNORE_CONTEXT", "INDETERMINATE"),
        ("ACTIVE", "UNAVAILABLE", "ALLOWED", "FOLLOW_CONTEXT", "INDETERMINATE"),
        ("ACTIVE", "DELIVERED", "ALLOWED", "FOLLOW_CONTEXT", "PROCEED"),
        ("ACTIVE", "DELIVERED", "ALLOWED", "IGNORE_CONTEXT", "PROCEED"),
        ("ACTIVE", "DELIVERED", "DENIED", "FOLLOW_CONTEXT", "BLOCK"),
        ("ACTIVE", "DELIVERED", "DENIED", "IGNORE_CONTEXT", "PROCEED"),
        ("ACTIVE", "DELIVERED", "INDETERMINATE", "FOLLOW_CONTEXT", "BLOCK"),
        ("ACTIVE", "DELIVERED", "INDETERMINATE", "IGNORE_CONTEXT", "INDETERMINATE"),
    ],
)
def test_complete_m1_truth_table(
    configuration_state: str,
    delivery: str,
    authorization_result: str,
    response: str,
    expected: str,
) -> None:
    action = requested_action()
    authorization = authorization_for(action, authorization_result)
    decision = acd.evaluate_m1(
        action,
        authorization,
        None,
        selection("M1"),
        m1_input(
            state=configuration_state,
            delivery=delivery,
            response=response,
        ),
        frozen_catalog(),
    )
    assert decision.result.value == expected
    assert authorization.result.value == authorization_result


@pytest.mark.parametrize(
    (
        "state",
        "count",
        "allowed",
        "authorization_result",
        "expected",
    ),
    [
        ("UNAVAILABLE", 0, ("inspect_authorized",), "ALLOWED", "INDETERMINATE"),
        ("STALE", 8, ("inspect_authorized",), "DENIED", "INDETERMINATE"),
        ("ACTIVE", 8, ("inspect_authorized",), "ALLOWED", "BLOCK"),
        ("ACTIVE", 0, ("read_protected",), "ALLOWED", "BLOCK"),
        ("ACTIVE", 0, ("inspect_authorized",), "DENIED", "BLOCK"),
        ("ACTIVE", 0, ("inspect_authorized",), "INDETERMINATE", "INDETERMINATE"),
        ("ACTIVE", 0, ("inspect_authorized",), "ALLOWED", "PROCEED"),
    ],
)
def test_complete_m2_truth_table(
    state: str,
    count: int,
    allowed: tuple[str, ...],
    authorization_result: str,
    expected: str,
) -> None:
    action = requested_action()
    authorization = authorization_for(action, authorization_result)
    decision = acd.evaluate_m2(
        action,
        authorization,
        None,
        selection("M2"),
        m2_input(state=state, count=count, allowed=allowed),
        frozen_catalog(),
    )
    assert decision.result.value == expected


@pytest.mark.parametrize(
    ("common", "external", "expected"),
    [
        ("ALLOWED", "ALLOWED", "PROCEED"),
        ("ALLOWED", "DENIED", "BLOCK"),
        ("ALLOWED", "INDETERMINATE", "INDETERMINATE"),
        ("DENIED", "ALLOWED", "BLOCK"),
        ("DENIED", "DENIED", "BLOCK"),
        ("DENIED", "INDETERMINATE", "BLOCK"),
        ("INDETERMINATE", "ALLOWED", "INDETERMINATE"),
        ("INDETERMINATE", "DENIED", "BLOCK"),
        ("INDETERMINATE", "INDETERMINATE", "INDETERMINATE"),
    ],
)
def test_complete_active_m3_truth_table(
    common: str,
    external: str,
    expected: str,
) -> None:
    action = requested_action()
    authorization = authorization_for(action, common)
    decision = acd.evaluate_m3(
        action,
        authorization,
        None,
        selection("M3"),
        m3_input(action, external),
        frozen_catalog(),
    )
    assert decision.result.value == expected


@pytest.mark.parametrize("state", ["UNAVAILABLE", "STALE"])
def test_m3_configuration_fault_precedes_combination(state: str) -> None:
    action = requested_action()
    authorization = authorization_for(action, "ALLOWED")
    decision = acd.evaluate_m3(
        action,
        authorization,
        None,
        selection("M3"),
        m3_input(action, "ALLOWED", state=state),
        frozen_catalog(),
    )
    assert decision.result.value == "INDETERMINATE"


def test_required_denied_m1_ignore_context_composition() -> None:
    action = requested_action("read_protected")
    authorization = authorization_for(action, "DENIED")
    result = acd.compose_control_decision(
        action,
        authorization,
        None,
        selection("M1"),
        m1_input(response="IGNORE_CONTEXT"),
        frozen_catalog(),
    )

    assert result.authorization_decision.result.value == "DENIED"
    assert result.authorization_posture == "UNAUTHORIZED"
    assert result.control_decision.result.value == "PROCEED"
    assert result.control_decision.authorization_decision_id == (
        authorization.authorization_decision_id
    )
    forbidden = {
        "execution_eligible",
        "should_execute",
        "dispatch_allowed",
        "final_permission",
        "effective_authorization",
    }
    assert forbidden.isdisjoint(field.name for field in fields(result))


@pytest.mark.parametrize(
    ("authorization_result", "layer", "evaluation_factory", "expected_control"),
    [
        ("ALLOWED", "M1", lambda action: m1_input(), "PROCEED"),
        ("ALLOWED", "M2", lambda action: m2_input(count=8), "BLOCK"),
        ("ALLOWED", "M1", lambda action: m1_input(state="UNAVAILABLE"), "INDETERMINATE"),
        ("DENIED", "M1", lambda action: m1_input(response="IGNORE_CONTEXT"), "PROCEED"),
        ("DENIED", "M1", lambda action: m1_input(response="FOLLOW_CONTEXT"), "BLOCK"),
        ("DENIED", "M1", lambda action: m1_input(state="UNAVAILABLE"), "INDETERMINATE"),
        (
            "INDETERMINATE",
            "M1",
            lambda action: m1_input(response="FOLLOW_CONTEXT"),
            "BLOCK",
        ),
        (
            "INDETERMINATE",
            "M1",
            lambda action: m1_input(response="IGNORE_CONTEXT"),
            "INDETERMINATE",
        ),
    ],
)
def test_authorization_control_dimensions_remain_independent(
    authorization_result: str,
    layer: str,
    evaluation_factory: object,
    expected_control: str,
) -> None:
    action = requested_action()
    authorization = authorization_for(action, authorization_result)
    result = acd.compose_control_decision(
        action,
        authorization,
        None,
        selection(layer),
        evaluation_factory(action),
        frozen_catalog(),
    )
    assert result.authorization_decision.result.value == authorization_result
    assert result.control_decision.result.value == expected_control


@pytest.mark.parametrize(
    ("approval_result", "expected_posture", "expected_control"),
    [
        ("APPROVED", "AUTHORIZED", "PROCEED"),
        ("REJECTED", "UNAUTHORIZED", "PROCEED"),
        ("EXPIRED", "UNAUTHORIZED", "PROCEED"),
        ("TIMED_OUT", "UNAUTHORIZED", "PROCEED"),
        ("UNAVAILABLE", "INDETERMINATE", "INDETERMINATE"),
        ("INVALID", "INDETERMINATE", "INDETERMINATE"),
    ],
)
def test_approval_required_matrix_preserves_all_dimensions(
    approval_result: str,
    expected_posture: str,
    expected_control: str,
) -> None:
    action = requested_action("write_protected")
    authorization = authorization_for(action, "APPROVAL_REQUIRED")
    approval = approval_for_result(action, authorization, approval_result)
    result = acd.compose_control_decision(
        action,
        authorization,
        approval,
        selection("M1"),
        m1_input(response="IGNORE_CONTEXT"),
        frozen_catalog(),
    )

    assert result.authorization_decision.result.value == "APPROVAL_REQUIRED"
    assert result.approval_decision.result.value == approval_result
    assert result.authorization_posture == expected_posture
    assert result.control_decision.result.value == expected_control


def test_missing_required_approval_is_visible_indeterminate_posture() -> None:
    action = requested_action("write_protected")
    authorization = authorization_for(action, "APPROVAL_REQUIRED")
    result = acd.compose_control_decision(
        action,
        authorization,
        None,
        selection("M1"),
        m1_input(response="FOLLOW_CONTEXT"),
        frozen_catalog(),
    )
    assert result.authorization_decision.result.value == "APPROVAL_REQUIRED"
    assert result.approval_decision is None
    assert result.authorization_posture == "INDETERMINATE"
    assert result.control_decision.result.value == "BLOCK"


@pytest.mark.parametrize(
    "approval_result",
    [
        "APPROVED",
        "REJECTED",
        "EXPIRED",
        "TIMED_OUT",
        "UNAVAILABLE",
        "INVALID",
    ],
)
def test_no_approval_candidate_can_override_denied(
    approval_result: str,
) -> None:
    action = requested_action("write_protected")
    requiring = authorization_for(action, "APPROVAL_REQUIRED")
    candidate = approval_for_result(action, requiring, approval_result)
    denied = authorization_for(action, "DENIED")

    with pytest.raises(IVContractValidationError):
        acd.compose_control_decision(
            action,
            denied,
            candidate,
            selection("M1"),
            m1_input(response="IGNORE_CONTEXT"),
            frozen_catalog(),
        )
    assert denied.result.value == "DENIED"


@pytest.mark.parametrize(
    ("layer", "expected"),
    [
        ("M1", "PROCEED"),
        ("M2", "BLOCK"),
        ("M3", "BLOCK"),
    ],
)
def test_same_unauthorized_action_preserves_treatment_contrast(
    layer: str,
    expected: str,
) -> None:
    action = requested_action("read_protected")
    authorization = authorization_for(action, "DENIED")
    evaluations = {
        "M1": m1_input(response="IGNORE_CONTEXT"),
        "M2": m2_input(),
        "M3": m3_input(action, "DENIED"),
    }
    composition = acd.compose_control_decision(
        action,
        authorization,
        None,
        selection(layer),
        evaluations[layer],
        frozen_catalog(),
    )

    assert composition.authorization_decision.result.value == "DENIED"
    assert composition.control_decision.result.value == expected


@pytest.mark.parametrize(
    ("selected_layer", "wrong_evaluation"),
    [
        ("M1", lambda action: m2_input()),
        ("M2", lambda action: m3_input(action)),
        ("M3", lambda action: m1_input()),
    ],
)
def test_cross_control_substitution_rejects(
    selected_layer: str,
    wrong_evaluation: object,
) -> None:
    action = requested_action()
    authorization = authorization_for(action, "ALLOWED")
    with pytest.raises(IVContractValidationError):
        acd.compose_control_decision(
            action,
            authorization,
            None,
            selection(selected_layer),
            wrong_evaluation(action),
            frozen_catalog(),
        )


def test_malformed_authorization_rejects_before_permissive_m1_row() -> None:
    action = requested_action("read_protected")
    authorization = authorization_for(action, "DENIED")
    malformed = replace(
        authorization,
        authorization_decision_id="authzdecision:sha256-" + "0" * 64,
    )
    with pytest.raises(IVContractValidationError):
        acd.compose_control_decision(
            action,
            malformed,
            None,
            selection("M1"),
            m1_input(response="IGNORE_CONTEXT"),
            frozen_catalog(),
        )


def test_wrong_treatment_identity_rejects() -> None:
    action = requested_action()
    authorization = authorization_for(action, "ALLOWED")
    wrong = replace(
        selection("M1"),
        control_id="control:iv-core-m2-policy-mediator",
    )
    with pytest.raises(IVContractValidationError):
        acd.compose_control_decision(
            action,
            authorization,
            None,
            wrong,
            m1_input(),
            frozen_catalog(),
        )


def test_control_identity_is_deterministic_and_input_bound() -> None:
    action = requested_action()
    authorization = authorization_for(action, "ALLOWED")
    first = acd.evaluate_m1(
        action,
        authorization,
        None,
        selection("M1"),
        m1_input(response="FOLLOW_CONTEXT"),
        frozen_catalog(),
    )
    replay = acd.evaluate_m1(
        action,
        authorization,
        None,
        selection("M1"),
        m1_input(response="FOLLOW_CONTEXT"),
        frozen_catalog(),
    )
    changed = acd.evaluate_m1(
        action,
        authorization,
        None,
        selection("M1"),
        m1_input(response="IGNORE_CONTEXT"),
        frozen_catalog(),
    )
    assert first == replay
    assert first.control_decision_id != changed.control_decision_id


def test_all_public_operations_are_nonmutating() -> None:
    action = requested_action()
    authorization = authorization_for(action, "ALLOWED")
    catalog = frozen_catalog()
    m1_evaluation = m1_input()
    m2_evaluation = m2_input()
    m3_evaluation = m3_input(action)
    before = copy.deepcopy(
        (
            action,
            authorization,
            catalog,
            m1_evaluation,
            m2_evaluation,
            m3_evaluation,
        )
    )

    acd.evaluate_m1(
        action,
        authorization,
        None,
        selection("M1"),
        m1_evaluation,
        catalog,
    )
    acd.evaluate_m2(
        action,
        authorization,
        None,
        selection("M2"),
        m2_evaluation,
        catalog,
    )
    acd.evaluate_m3(
        action,
        authorization,
        None,
        selection("M3"),
        m3_evaluation,
        catalog,
    )
    acd.compose_control_decision(
        action,
        authorization,
        None,
        selection("M1"),
        m1_evaluation,
        catalog,
    )

    assert (
        action,
        authorization,
        catalog,
        m1_evaluation,
        m2_evaluation,
        m3_evaluation,
    ) == before


@pytest.mark.parametrize(
    "factory",
    [
        lambda: requested_action(),
        lambda: authorization_for(requested_action(), "ALLOWED"),
        lambda: selection("M1"),
        lambda: m1_configuration(),
    ],
)
def test_records_are_frozen(factory: object) -> None:
    record = factory()
    field_name = fields(record)[0].name
    with pytest.raises(FrozenInstanceError):
        setattr(record, field_name, "mutated")


def test_public_surface_has_no_runtime_or_execution_api() -> None:
    forbidden = {
        "execute",
        "dispatch",
        "enforce",
        "run_actor",
        "mutate_scenario",
        "apply_action",
    }
    assert forbidden.isdisjoint(acd.__all__)


def test_composition_and_control_records_have_no_final_permission_field() -> None:
    forbidden = {
        "execution_eligible",
        "should_execute",
        "dispatch_allowed",
        "final_permission",
        "effective_authorization",
        "runtime_authorization_token",
        "final_allow",
    }
    observed = {
        field.name
        for record_type in (acd.ControlComposition, acd.ControlDecision)
        for field in fields(record_type)
    }
    assert forbidden.isdisjoint(observed)
