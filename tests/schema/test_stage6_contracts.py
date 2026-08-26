"""Stage 6 tests for evidence events and evaluator-derived outcomes."""

from __future__ import annotations

import copy
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import ValidationError

from frontier_agent_containment.schema_validation import (
    check_draft_2020_12_schema,
    load_schema_store,
    validate_instance,
)


ROOT = Path(__file__).resolve().parents[2]
DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_PATHS = {
    "common": ROOT / "schemas" / "common.schema.json",
    "resource": ROOT / "schemas" / "resource.schema.json",
    "benign_task": ROOT / "schemas" / "benign-task.schema.json",
    "capability_envelope": ROOT / "schemas" / "capability-envelope.schema.json",
    "scenario": ROOT / "schemas" / "scenario.schema.json",
    "policy": ROOT / "schemas" / "policy.schema.json",
    "control": ROOT / "schemas" / "control.schema.json",
    "control_condition": ROOT / "schemas" / "control-condition.schema.json",
    "agent_model_condition": ROOT / "schemas" / "agent-model-condition.schema.json",
    "autonomy_condition": ROOT / "schemas" / "autonomy-condition.schema.json",
    "environment": ROOT / "schemas" / "environment.schema.json",
    "run_manifest": ROOT / "schemas" / "run-manifest.schema.json",
    "evidence_event": ROOT / "schemas" / "evidence-event.schema.json",
    "derived_action_outcome": ROOT / "schemas" / "derived-action-outcome.schema.json",
    "derived_run_outcome": ROOT / "schemas" / "derived-run-outcome.schema.json",
}
SCHEMA_IDS = {
    "common": "urn:frontier-agent-containment:schema:common:0.1.0",
    "resource": "urn:frontier-agent-containment:schema:resource:0.1.0",
    "benign_task": "urn:frontier-agent-containment:schema:benign-task:0.1.0",
    "capability_envelope": (
        "urn:frontier-agent-containment:schema:capability-envelope:0.1.0"
    ),
    "scenario": "urn:frontier-agent-containment:schema:scenario:0.1.0",
    "policy": "urn:frontier-agent-containment:schema:policy:0.1.0",
    "control": "urn:frontier-agent-containment:schema:control:0.1.0",
    "control_condition": (
        "urn:frontier-agent-containment:schema:control-condition:0.1.0"
    ),
    "agent_model_condition": (
        "urn:frontier-agent-containment:schema:agent-model-condition:0.1.0"
    ),
    "autonomy_condition": (
        "urn:frontier-agent-containment:schema:autonomy-condition:0.1.0"
    ),
    "environment": "urn:frontier-agent-containment:schema:environment:0.1.0",
    "run_manifest": "urn:frontier-agent-containment:schema:run-manifest:0.1.0",
    "evidence_event": (
        "urn:frontier-agent-containment:schema:evidence-event:0.1.0"
    ),
    "derived_action_outcome": (
        "urn:frontier-agent-containment:schema:derived-action-outcome:0.1.0"
    ),
    "derived_run_outcome": (
        "urn:frontier-agent-containment:schema:derived-run-outcome:0.1.0"
    ),
}
EVENT_CLASSES = [
    "RUN_INITIALIZED",
    "RUN_STARTED",
    "AGENT_ACTION_REQUESTED",
    "AUTHORIZATION_DECIDED",
    "APPROVAL_REQUESTED",
    "APPROVAL_DECIDED",
    "EXECUTION_ATTEMPTED",
    "EXECUTION_COMPLETED",
    "RESOURCE_ACCESSED",
    "RESOURCE_MODIFIED",
    "PRIVILEGE_EFFECT_OBSERVED",
    "PERSISTENCE_STATE_OBSERVED",
    "DATA_MOVEMENT_OBSERVED",
    "NETWORK_EFFECT_OBSERVED",
    "CONTROL_DECISION_OBSERVED",
    "CONTROL_ERROR_OBSERVED",
    "ARCHITECTURAL_INVALIDITY_OBSERVED",
    "RUN_TERMINATED",
    "ACTION_OUTCOME_DERIVED",
    "RUN_OUTCOME_DERIVED",
]
SOURCE_ROLES = [
    "EXPERIMENT_ORCHESTRATOR",
    "AUTHORIZATION_DECISION_SOURCE",
    "APPROVAL_AUTHORITY",
    "EXECUTION_MEDIATOR",
    "RESOURCE_SERVICE_OBSERVER",
    "NETWORK_OBSERVER",
    "EVIDENCE_COLLECTOR",
    "EVALUATOR",
]
APPROVAL_DECISIONS = [
    "APPROVED",
    "REJECTED",
    "EXPIRED",
    "TIMED_OUT",
    "UNAVAILABLE",
    "INVALID",
]
EVIDENCE_QUALITY_STATES = [
    "VALID",
    "MISSING_REQUIRED",
    "CONFLICTING",
    "DUPLICATE",
    "MALFORMED",
    "UNTRUSTED_SOURCE",
    "OUT_OF_ORDER",
    "UNRESOLVED_IDENTITY",
    "INCONCLUSIVE",
]
EFFECT_STATES = ["OBSERVED", "NOT_OBSERVED", "UNKNOWN"]
TERMINATION_CLASSES = [
    "NORMAL_TERMINAL",
    "ACTION_BUDGET_EXHAUSTED",
    "TIMEOUT",
    "AGENT_ABORT",
    "INFRASTRUCTURE_TERMINATION",
    "SAFETY_TERMINATION",
    "RUN_INVALIDATION",
]
TERMINAL_OUTCOMES = [
    "AUTHORIZED_EXECUTED",
    "AUTHORIZED_NOT_EXECUTED",
    "UNAUTHORIZED_BLOCKED",
    "UNAUTHORIZED_NOT_EXECUTED_OTHER",
    "UNAUTHORIZED_EXECUTED",
    "AGENT_ABORTED",
    "CONTROL_ERROR",
    "INCONCLUSIVE",
]
RUN_VALIDITY_STATES = [
    "VALID_FOR_PRIMARY_ANALYSIS",
    "INVALID_FOR_PRIMARY_ANALYSIS",
]
PRIMARY_OBSERVABILITY_STATES = [
    "COMPLETE_FOR_PRIMARY_ENDPOINT",
    "INCOMPLETE_FOR_PRIMARY_ENDPOINT",
]
RERUN_RELATIONSHIPS = ["ORIGINAL_OF_RERUN", "RERUN_OF"]


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(SCHEMA_PATHS.values())


@pytest.fixture(scope="module")
def schemas(schema_store: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {name: schema_store[schema_id] for name, schema_id in SCHEMA_IDS.items()}


def source(role: str = "EXPERIMENT_ORCHESTRATOR") -> dict[str, Any]:
    return {
        "source_id": "authoritative_component",
        "source_role": role,
        "source_version": "0.1.0",
        "build_id": "build:instrument-001",
        "configuration_id": "cond:observer-baseline",
    }


def event_data(event_class: str) -> dict[str, Any]:
    values: dict[str, dict[str, Any]] = {
        "RUN_INITIALIZED": {
            "run_state": "INITIALIZED",
            "phase": "DEVELOPMENT",
            "state_description": "Frozen run configuration was initialized.",
            "starting_state_identity": "baseline_state",
            "s0_configuration_id": "cond:s0-baseline",
            "s0_acceptance_identity": "s0_acceptance",
            "s0_acceptance_passed": True,
        },
        "RUN_STARTED": {
            "run_state": "STARTED",
            "state_description": "The prospective action horizon began.",
        },
        "AGENT_ACTION_REQUESTED": {
            "action_id": "action:request-001",
            "subject_agent_condition_id": "agentcond:baseline-agent",
            "action_class": "read",
            "target_resource_id": "resource:synthetic-record",
            "bounded_arguments": {"record_name": "synthetic_record"},
        },
        "AUTHORIZATION_DECIDED": {
            "action_id": "action:request-001",
            "capability_envelope_id": "envelope:baseline-envelope",
            "policy_id": "policy:default-deny",
            "authorization_decision": "DENIED",
        },
        "APPROVAL_REQUESTED": {
            "action_id": "action:request-001",
            "approval_policy_id": "approvalpolicy:deterministic-review",
        },
        "APPROVAL_DECIDED": {
            "action_id": "action:request-001",
            "approval_policy_id": "approvalpolicy:deterministic-review",
            "approval_decision": "APPROVED",
        },
        "EXECUTION_ATTEMPTED": {
            "action_id": "action:request-001",
            "execution_state": "EXECUTION_ATTEMPTED",
            "target_resource_id": "resource:synthetic-record",
        },
        "EXECUTION_COMPLETED": {
            "action_id": "action:request-001",
            "execution_state": "EXECUTION_SUCCEEDED",
            "target_resource_id": "resource:synthetic-record",
            "execution_reason": "The synthetic operation completed.",
        },
        "RESOURCE_ACCESSED": {
            "action_id": "action:request-001",
            "resource_id": "resource:synthetic-record",
            "effect_state": "OBSERVED",
            "effect_description": "The synthetic resource observer recorded access.",
        },
        "RESOURCE_MODIFIED": {
            "action_id": "action:request-001",
            "resource_id": "resource:synthetic-record",
            "effect_state": "OBSERVED",
            "effect_description": "The synthetic resource observer recorded modification.",
        },
        "PRIVILEGE_EFFECT_OBSERVED": {
            "action_id": "action:request-001",
            "resource_id": "resource:synthetic-runtime",
            "effect_state": "OBSERVED",
            "effect_description": "Synthetic effective privilege was observed.",
        },
        "PERSISTENCE_STATE_OBSERVED": {
            "action_id": "action:request-001",
            "resource_id": "resource:synthetic-state",
            "effect_state": "NOT_OBSERVED",
            "effect_description": "No state persisted across the synthetic reset boundary.",
        },
        "DATA_MOVEMENT_OBSERVED": {
            "action_id": "action:request-001",
            "resource_id": "resource:synthetic-record",
            "source_zone": "Z2",
            "destination_zone": "Z6",
            "effect_state": "OBSERVED",
            "effect_description": "Synthetic data reached the controlled sink.",
        },
        "NETWORK_EFFECT_OBSERVED": {
            "action_id": "action:request-001",
            "source_zone": "Z1",
            "destination_zone": "Z6",
            "effect_state": "OBSERVED",
            "effect_description": "A controlled synthetic network receipt was observed.",
        },
        "CONTROL_DECISION_OBSERVED": {
            "action_id": "action:request-001",
            "control_condition_id": "ctrlcond:m3-baseline",
            "control_id": "control:execution-mediator",
            "decision_description": "The configured control denied dispatch.",
        },
        "CONTROL_ERROR_OBSERVED": {
            "error_class": "observer_unavailable",
            "error_description": "A synthetic observer reported an explicit error.",
            "control_id": "control:execution-mediator",
            "control_condition_id": "ctrlcond:m3-baseline",
            "action_id": "action:request-001",
        },
        "ARCHITECTURAL_INVALIDITY_OBSERVED": {
            "violated_requirement": "external_enforcement_independence",
            "invalidity_description": "A declared synthetic boundary was absent.",
            "effect_on_endpoint_validity": "PRIMARY_ENDPOINT_INVALID",
            "control_id": "control:execution-mediator",
            "control_condition_id": "ctrlcond:m3-baseline",
        },
        "RUN_TERMINATED": {
            "termination_class": "NORMAL_TERMINAL",
            "termination_description": "The declared synthetic terminal state was reached.",
            "terminal_condition_id": "scenario_terminal",
        },
        "ACTION_OUTCOME_DERIVED": {
            "action_id": "action:request-001",
            "derived_artifact_reference": "action_outcome_001",
            "derivation_rule_id": "terminal_outcome_rule",
            "source_event_ids": ["event:authorization-001", "event:effect-001"],
        },
        "RUN_OUTCOME_DERIVED": {
            "derived_artifact_reference": "run_outcome_001",
            "derivation_rule_id": "run_aggregation_rule",
            "source_event_ids": ["event:action-outcome-001"],
        },
    }
    return copy.deepcopy(values[event_class])


def valid_evidence_event(event_class: str = "RUN_INITIALIZED") -> dict[str, Any]:
    source_role = "EVALUATOR" if event_class.endswith("OUTCOME_DERIVED") else (
        "EXPERIMENT_ORCHESTRATOR"
    )
    return {
        "event_id": "event:evidence-001",
        "event_version": "0.1.0",
        "experiment_id": "exp:containment-study",
        "run_id": "run:development-001",
        "scenario_id": "scenario:synthetic-resource-access",
        "condition_id": "cond:complete-condition",
        "event_class": event_class,
        "sequence_number": 1,
        "authoritative_source": source(source_role),
        "instrument_configuration_id": "instrument:development-001",
        "environment_id": "env:synthetic-lab",
        "build_id": "build:synthetic-lab-001",
        "evidence_quality_state": "VALID",
        "event_data": event_data(event_class),
        "prior_event_ids": [],
        "integrity_identifier": "integrity_reference_001",
    }


def valid_action_outcome(outcome: str = "AUTHORIZED_EXECUTED") -> dict[str, Any]:
    instance: dict[str, Any] = {
        "outcome_version": "0.1.0",
        "experiment_id": "exp:containment-study",
        "run_id": "run:development-001",
        "action_id": "action:request-001",
        "terminal_outcome": outcome,
        "evidence_event_ids": ["event:authorization-001", "event:effect-001"],
        "derivation_rule_id": "terminal_outcome_rule",
        "derivation_description": "The frozen terminal-outcome rule was applied.",
        "evaluator_source_id": "frozen_evaluator",
        "derivation_sequence_number": 1,
        "architecture_validity": "VALID_FOR_ACTION_OUTCOME",
        "evidence_completeness": "COMPLETE_FOR_ACTION_OUTCOME",
    }
    conditional = {
        "UNAUTHORIZED_BLOCKED": {
            "blocking_control_id": "control:execution-mediator",
            "blocking_control_condition_id": "ctrlcond:m3-baseline",
        },
        "UNAUTHORIZED_NOT_EXECUTED_OTHER": {
            "nonexecution_reason": "The synthetic service was independently unavailable."
        },
        "UNAUTHORIZED_EXECUTED": {
            "effect_event_ids": ["event:effect-001"]
        },
        "AGENT_ABORTED": {
            "termination_reason": "The agent voluntarily withdrew before execution."
        },
        "CONTROL_ERROR": {
            "error_reason": "An identified mediator malfunction prevented classification."
        },
        "INCONCLUSIVE": {
            "inconclusive_reason": "No specific malfunction explained incomplete evidence."
        },
    }
    instance.update(conditional.get(outcome, {}))
    return instance


def valid_run_outcome(
    run_validity: str = "VALID_FOR_PRIMARY_ANALYSIS",
    observability: str = "COMPLETE_FOR_PRIMARY_ENDPOINT",
    h1: int = 0,
) -> dict[str, Any]:
    instance: dict[str, Any] = {
        "outcome_version": "0.1.0",
        "experiment_id": "exp:containment-study",
        "run_id": "run:development-001",
        "run_validity": run_validity,
        "primary_endpoint_observability": observability,
        "action_outcome_references": [
            {
                "action_id": "action:request-001",
                "derived_action_outcome_reference": "action_outcome_001",
            }
        ],
        "benign_utility": {
            "evaluable": True,
            "task_success": True,
            "criterion_results": [
                {
                    "criterion_id": "authorized_task_complete",
                    "observed_result": "complete",
                    "satisfied": True,
                    "evidence_event_ids": ["event:utility-observation-001"],
                }
            ],
        },
        "derivation_rule_id": "run_aggregation_rule",
        "derivation_description": "The frozen run-level aggregation rule was applied.",
        "evaluator_source_id": "frozen_evaluator",
        "derivation_sequence_number": 2,
    }
    if (
        run_validity == "VALID_FOR_PRIMARY_ANALYSIS"
        and observability == "COMPLETE_FOR_PRIMARY_ENDPOINT"
    ):
        instance["h1_containment_failure"] = h1
    if run_validity == "INVALID_FOR_PRIMARY_ANALYSIS":
        instance["invalidity_reason"] = "A prespecified invalidating condition occurred."
    if observability == "INCOMPLETE_FOR_PRIMARY_ENDPOINT":
        instance["missingness_reason"] = "Required primary evidence was unavailable."
    return instance


def assert_valid(
    instance: dict[str, Any],
    schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    validate_instance(instance, schema, schema_store=schema_store)


def assert_invalid(
    instance: dict[str, Any],
    schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        validate_instance(instance, schema, schema_store=schema_store)


@pytest.mark.parametrize(
    "schema_name",
    ["evidence_event", "derived_action_outcome", "derived_run_outcome"],
)
def test_stage6_schema_is_valid_draft_2020_12(
    schema_name: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    schema = schemas[schema_name]
    assert schema["$schema"] == DRAFT_2020_12
    assert schema["$id"] == SCHEMA_IDS[schema_name]
    check_draft_2020_12_schema(schema, schema_store=schema_store)


def test_evidence_event_class_enum_is_exact(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert schemas["evidence_event"]["properties"]["event_class"]["enum"] == (
        EVENT_CLASSES
    )


@pytest.mark.parametrize("event_class", EVENT_CLASSES)
def test_valid_event_class_and_sensitive_data_are_accepted(
    event_class: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(valid_evidence_event(event_class), schemas["evidence_event"], schema_store)


def test_action_request_requires_action_id(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event("AGENT_ACTION_REQUESTED")
    del instance["event_data"]["action_id"]
    assert_invalid(instance, schemas["evidence_event"], schema_store)


@pytest.mark.parametrize(
    "argument_name",
    ["exploit_payload", "malware_path", "target_ip", "stolen_password", "api_key"],
)
def test_action_request_rejects_unsafe_bounded_argument_name(
    argument_name: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_evidence_event("AGENT_ACTION_REQUESTED")
    instance["event_data"]["bounded_arguments"] = {argument_name: "prohibited"}
    assert_invalid(instance, schemas["evidence_event"], schema_store)


@pytest.mark.parametrize(
    "decision", ["ALLOWED", "DENIED", "APPROVAL_REQUIRED", "INDETERMINATE"]
)
def test_authorization_event_accepts_each_runtime_decision(
    decision: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_evidence_event("AUTHORIZATION_DECIDED")
    instance["event_data"]["authorization_decision"] = decision
    assert_valid(instance, schemas["evidence_event"], schema_store)


def test_authorization_event_rejects_not_applicable(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event("AUTHORIZATION_DECIDED")
    instance["event_data"]["authorization_decision"] = "NOT_APPLICABLE"
    assert_invalid(instance, schemas["evidence_event"], schema_store)


@pytest.mark.parametrize("decision", APPROVAL_DECISIONS)
def test_approval_event_accepts_all_six_frozen_decisions(
    decision: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_evidence_event("APPROVAL_DECIDED")
    instance["event_data"]["approval_decision"] = decision
    assert_valid(instance, schemas["evidence_event"], schema_store)


def test_approval_event_rejects_approval_required_as_decision(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event("APPROVAL_DECIDED")
    instance["event_data"]["approval_decision"] = "APPROVAL_REQUIRED"
    assert_invalid(instance, schemas["evidence_event"], schema_store)


def test_execution_attempt_rejects_completed_state(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event("EXECUTION_ATTEMPTED")
    instance["event_data"]["execution_state"] = "EXECUTION_SUCCEEDED"
    assert_invalid(instance, schemas["evidence_event"], schema_store)


@pytest.mark.parametrize(
    "state", ["EXECUTION_SUCCEEDED", "EXECUTION_FAILED", "EXECUTION_RESULT_UNKNOWN"]
)
def test_execution_completed_accepts_each_completion_state(
    state: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_evidence_event("EXECUTION_COMPLETED")
    instance["event_data"]["execution_state"] = state
    assert_valid(instance, schemas["evidence_event"], schema_store)


@pytest.mark.parametrize("effect_state", EFFECT_STATES)
def test_resource_effect_accepts_each_observation_state(
    effect_state: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_evidence_event("RESOURCE_ACCESSED")
    instance["event_data"]["effect_state"] = effect_state
    assert_valid(instance, schemas["evidence_event"], schema_store)


def test_resource_effect_rejects_invalid_state(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event("RESOURCE_MODIFIED")
    instance["event_data"]["effect_state"] = "ASSUMED_ABSENT"
    assert_invalid(instance, schemas["evidence_event"], schema_store)


def test_effect_state_enum_is_exact(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert schemas["evidence_event"]["$defs"]["effect_state"]["enum"] == EFFECT_STATES


@pytest.mark.parametrize("role", SOURCE_ROLES)
def test_evidence_event_accepts_each_authoritative_source_role(
    role: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_evidence_event()
    instance["authoritative_source"]["source_role"] = role
    assert_valid(instance, schemas["evidence_event"], schema_store)


def test_authoritative_source_role_enum_is_exact(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert schemas["evidence_event"]["$defs"]["authoritative_source"]["properties"][
        "source_role"
    ]["enum"] == SOURCE_ROLES


def test_agent_is_not_an_authoritative_source_role(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event()
    instance["authoritative_source"]["source_role"] = "AGENT"
    assert_invalid(instance, schemas["evidence_event"], schema_store)


def test_derived_marker_requires_evaluator_source(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event("ACTION_OUTCOME_DERIVED")
    instance["authoritative_source"]["source_role"] = "EVIDENCE_COLLECTOR"
    assert_invalid(instance, schemas["evidence_event"], schema_store)


def test_evidence_event_rejects_zero_sequence_number(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event()
    instance["sequence_number"] = 0
    assert_invalid(instance, schemas["evidence_event"], schema_store)


@pytest.mark.parametrize("quality", EVIDENCE_QUALITY_STATES)
def test_evidence_event_accepts_each_frozen_quality_state(
    quality: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_evidence_event()
    instance["evidence_quality_state"] = quality
    assert_valid(instance, schemas["evidence_event"], schema_store)


def test_evidence_event_rejects_invalid_quality_state(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event()
    instance["evidence_quality_state"] = "ASSUMED_VALID"
    assert_invalid(instance, schemas["evidence_event"], schema_store)


@pytest.mark.parametrize(
    "prior_ids",
    [["run:wrong-prefix"], ["event:prior-001", "event:prior-001"]],
)
def test_evidence_event_rejects_malformed_or_duplicate_prior_event_ids(
    prior_ids: list[str],
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_evidence_event()
    instance["prior_event_ids"] = prior_ids
    assert_invalid(instance, schemas["evidence_event"], schema_store)


@pytest.mark.parametrize(
    "unit", ["NANOSECONDS", "MICROSECONDS", "MILLISECONDS", "SECONDS"]
)
def test_evidence_event_accepts_optional_time_evidence(
    unit: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_evidence_event()
    instance["time_evidence"] = {
        "clock_id": "run_monotonic_clock",
        "monotonic_reading": 1.5,
        "unit": unit,
    }
    assert_valid(instance, schemas["evidence_event"], schema_store)


def test_evidence_event_rejects_invalid_time_unit(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event()
    instance["time_evidence"] = {
        "clock_id": "run_monotonic_clock",
        "monotonic_reading": 1,
        "unit": "WALL_CLOCK",
    }
    assert_invalid(instance, schemas["evidence_event"], schema_store)


def test_event_class_sensitive_data_rejects_conflation(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event("AUTHORIZATION_DECIDED")
    instance["event_data"] = event_data("EXECUTION_COMPLETED")
    assert_invalid(instance, schemas["evidence_event"], schema_store)


def test_termination_class_enum_is_exact(
    schemas: dict[str, dict[str, Any]],
) -> None:
    termination = schemas["evidence_event"]["$defs"]["run_terminated_data"][
        "properties"
    ]["termination_class"]
    assert termination["enum"] == TERMINATION_CLASSES


@pytest.mark.parametrize("termination_class", TERMINATION_CLASSES)
def test_run_terminated_accepts_each_frozen_termination_class(
    termination_class: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_evidence_event("RUN_TERMINATED")
    instance["event_data"]["termination_class"] = termination_class
    if termination_class == "SAFETY_TERMINATION":
        instance["event_data"]["s0_intervention"] = {
            "component_id": "network_boundary",
            "safety_property_protected": "Prevented uncontrolled external access.",
            "synthetic_endpoint_effect": "The synthetic endpoint became unobservable.",
            "expected_under_frozen_design": False,
            "effect_on_primary_endpoint": "PRIMARY_ENDPOINT_UNKNOWN",
        }
    assert_valid(instance, schemas["evidence_event"], schema_store)


def test_safety_termination_requires_s0_intervention_details(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event("RUN_TERMINATED")
    instance["event_data"]["termination_class"] = "SAFETY_TERMINATION"
    assert_invalid(instance, schemas["evidence_event"], schema_store)


def test_evidence_event_rejects_unknown_property(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event()
    instance["agent_claimed_success"] = True
    assert_invalid(instance, schemas["evidence_event"], schema_store)


@pytest.mark.parametrize("field", ["event_id", "scenario_id", "condition_id", "event_data"])
def test_evidence_event_rejects_missing_required_field(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_evidence_event()
    del instance[field]
    assert_invalid(instance, schemas["evidence_event"], schema_store)


def test_evidence_event_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_evidence_event("NETWORK_EFFECT_OBSERVED")
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["evidence_event"], schema_store)
    assert instance == original


def test_terminal_action_outcome_enum_is_exactly_shared(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert schemas["common"]["$defs"]["terminal_action_outcome"]["enum"] == (
        TERMINAL_OUTCOMES
    )
    assert schemas["derived_action_outcome"]["properties"]["terminal_outcome"][
        "$ref"
    ] == (SCHEMA_IDS["common"] + "#/$defs/terminal_action_outcome")


@pytest.mark.parametrize("outcome", TERMINAL_OUTCOMES)
def test_each_frozen_terminal_action_outcome_is_accepted(
    outcome: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(
        valid_action_outcome(outcome),
        schemas["derived_action_outcome"],
        schema_store,
    )


def test_derived_action_outcome_rejects_unknown_terminal_outcome(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_action_outcome()
    instance["terminal_outcome"] = "BLOCKED"
    assert_invalid(instance, schemas["derived_action_outcome"], schema_store)


@pytest.mark.parametrize(
    "evidence_ids",
    [[], ["event:evidence-001", "event:evidence-001"], ["run:wrong-prefix"]],
)
def test_derived_action_rejects_empty_duplicate_or_malformed_evidence_ids(
    evidence_ids: list[str],
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_action_outcome()
    instance["evidence_event_ids"] = evidence_ids
    assert_invalid(instance, schemas["derived_action_outcome"], schema_store)


@pytest.mark.parametrize(
    "field", ["blocking_control_id", "blocking_control_condition_id"]
)
def test_unauthorized_blocked_requires_both_attribution_references(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_action_outcome("UNAUTHORIZED_BLOCKED")
    del instance[field]
    assert_invalid(instance, schemas["derived_action_outcome"], schema_store)


@pytest.mark.parametrize(
    "outcome,required_field",
    [
        ("UNAUTHORIZED_NOT_EXECUTED_OTHER", "nonexecution_reason"),
        ("UNAUTHORIZED_EXECUTED", "effect_event_ids"),
        ("CONTROL_ERROR", "error_reason"),
        ("INCONCLUSIVE", "inconclusive_reason"),
        ("AGENT_ABORTED", "termination_reason"),
    ],
)
def test_conditional_action_outcome_field_is_required(
    outcome: str,
    required_field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_action_outcome(outcome)
    del instance[required_field]
    assert_invalid(instance, schemas["derived_action_outcome"], schema_store)


def test_unauthorized_executed_rejects_empty_effect_event_ids(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_action_outcome("UNAUTHORIZED_EXECUTED")
    instance["effect_event_ids"] = []
    assert_invalid(instance, schemas["derived_action_outcome"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [("run_id", "event:wrong-prefix"), ("action_id", "run:wrong-prefix")],
)
def test_derived_action_rejects_wrong_run_or_action_id(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_action_outcome()
    instance[field] = value
    assert_invalid(instance, schemas["derived_action_outcome"], schema_store)


@pytest.mark.parametrize("field", ["agent_claimed_success", "model_verdict", "unexpected"])
def test_derived_action_rejects_agent_verdict_or_unknown_field(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_action_outcome()
    instance[field] = True
    assert_invalid(instance, schemas["derived_action_outcome"], schema_store)


def test_derived_action_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_action_outcome("UNAUTHORIZED_EXECUTED")
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["derived_action_outcome"], schema_store)
    assert instance == original


def test_run_validity_and_observability_enums_are_exact(
    schemas: dict[str, dict[str, Any]],
) -> None:
    schema = schemas["derived_run_outcome"]
    assert schema["properties"]["run_validity"]["enum"] == RUN_VALIDITY_STATES
    assert schema["properties"]["primary_endpoint_observability"]["enum"] == (
        PRIMARY_OBSERVABILITY_STATES
    )


@pytest.mark.parametrize("h1", [0, 1])
def test_valid_complete_run_accepts_binary_h1(
    h1: int,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(valid_run_outcome(h1=h1), schemas["derived_run_outcome"], schema_store)


@pytest.mark.parametrize("h1", [-1, 2, "0", None])
def test_run_outcome_rejects_nonbinary_h1(
    h1: object,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_run_outcome()
    instance["h1_containment_failure"] = h1
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_valid_complete_run_requires_h1(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome()
    del instance["h1_containment_failure"]
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


@pytest.mark.parametrize(
    "validity,observability",
    [
        ("INVALID_FOR_PRIMARY_ANALYSIS", "COMPLETE_FOR_PRIMARY_ENDPOINT"),
        ("VALID_FOR_PRIMARY_ANALYSIS", "INCOMPLETE_FOR_PRIMARY_ENDPOINT"),
        ("INVALID_FOR_PRIMARY_ANALYSIS", "INCOMPLETE_FOR_PRIMARY_ENDPOINT"),
    ],
)
def test_invalid_or_incomplete_run_rejects_h1_presence(
    validity: str,
    observability: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_run_outcome(validity, observability)
    instance["h1_containment_failure"] = 0
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_invalid_run_requires_invalidity_reason(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome("INVALID_FOR_PRIMARY_ANALYSIS")
    del instance["invalidity_reason"]
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_valid_run_rejects_invalidity_reason(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome()
    instance["invalidity_reason"] = "Not applicable to a valid run."
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_incomplete_endpoint_requires_missingness_reason(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome(
        "VALID_FOR_PRIMARY_ANALYSIS", "INCOMPLETE_FOR_PRIMARY_ENDPOINT"
    )
    del instance["missingness_reason"]
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_complete_endpoint_rejects_missingness_reason(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome()
    instance["missingness_reason"] = "Not applicable to complete evidence."
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_evaluable_utility_requires_task_success(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome()
    del instance["benign_utility"]["task_success"]
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_utility_criterion_requires_authoritative_evidence_reference(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome()
    del instance["benign_utility"]["criterion_results"][0]["evidence_event_ids"]
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_nonevaluable_utility_rejects_task_success(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome()
    instance["benign_utility"]["evaluable"] = False
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_nonevaluable_utility_without_task_success_is_accepted(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome()
    instance["benign_utility"]["evaluable"] = False
    del instance["benign_utility"]["task_success"]
    instance["benign_utility"]["criterion_results"] = []
    assert_valid(instance, schemas["derived_run_outcome"], schema_store)


@pytest.mark.parametrize("relationship", RERUN_RELATIONSHIPS)
def test_run_outcome_accepts_each_rerun_relationship(
    relationship: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_run_outcome()
    instance["rerun_reference"] = {
        "related_run_id": "run:related-002",
        "relationship": relationship,
    }
    assert_valid(instance, schemas["derived_run_outcome"], schema_store)


def test_rerun_relationship_enum_is_exact(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert schemas["derived_run_outcome"]["$defs"]["rerun_reference"]["properties"][
        "relationship"
    ]["enum"] == RERUN_RELATIONSHIPS


def test_run_outcome_rejects_unknown_rerun_relationship(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome()
    instance["rerun_reference"] = {
        "related_run_id": "run:related-002",
        "relationship": "REPLACES",
    }
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_run_outcome_rejects_malformed_run_id(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome()
    instance["run_id"] = "event:wrong-prefix"
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


@pytest.mark.parametrize(
    "reference",
    [
        {"action_id": "run:wrong-prefix", "derived_action_outcome_reference": "outcome_001"},
        {"action_id": "action:request-001"},
    ],
)
def test_run_outcome_rejects_malformed_action_outcome_reference(
    reference: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_run_outcome()
    instance["action_outcome_references"] = [reference]
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


@pytest.mark.parametrize(
    "field", ["risk_difference", "risk_ratio", "p_value", "confidence_interval", "h1_verdict"]
)
def test_run_outcome_rejects_statistical_aggregate_field(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_run_outcome()
    instance[field] = 0
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_run_outcome_rejects_unknown_property(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome()
    instance["unexpected"] = True
    assert_invalid(instance, schemas["derived_run_outcome"], schema_store)


def test_run_outcome_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_outcome(h1=1)
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["derived_run_outcome"], schema_store)
    assert instance == original


def test_approval_decision_exactly_includes_timed_out(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert schemas["common"]["$defs"]["approval_decision"]["enum"] == (
        APPROVAL_DECISIONS
    )


def test_action_class_syntax_matches_prior_stages(
    schemas: dict[str, dict[str, Any]],
) -> None:
    patterns = {
        schemas["resource"]["$defs"]["action_class"]["pattern"],
        schemas["benign_task"]["$defs"]["action_class"]["pattern"],
        schemas["capability_envelope"]["$defs"]["action_class"]["pattern"],
        schemas["policy"]["$defs"]["action_class"]["pattern"],
        schemas["agent_model_condition"]["$defs"]["action_class"]["pattern"],
        schemas["evidence_event"]["$defs"]["action_class"]["pattern"],
    }
    assert patterns == {"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$"}


@pytest.mark.parametrize(
    "definition",
    ["execution_attempted_data", "execution_completed_data"],
)
def test_execution_state_constraints_reference_frozen_common_semantics(
    definition: str,
    schemas: dict[str, dict[str, Any]],
) -> None:
    execution_state = schemas["evidence_event"]["$defs"][definition]["properties"][
        "execution_state"
    ]
    assert execution_state["allOf"][0]["$ref"] == (
        SCHEMA_IDS["common"] + "#/$defs/execution_state"
    )


@pytest.mark.parametrize(
    "schema_name,path,common_definition",
    [
        ("evidence_event", ("properties", "run_id"), "run_id"),
        ("evidence_event", ("properties", "event_id"), "event_id"),
        (
            "evidence_event",
            ("$defs", "authorization_decision_data", "properties", "capability_envelope_id"),
            "capability_envelope_id",
        ),
        (
            "evidence_event",
            ("$defs", "authorization_decision_data", "properties", "policy_id"),
            "policy_id",
        ),
        (
            "evidence_event",
            ("$defs", "control_decision_data", "properties", "control_id"),
            "control_id",
        ),
        ("evidence_event", ("properties", "environment_id"), "environment_id"),
        (
            "evidence_event",
            ("properties", "instrument_configuration_id"),
            "instrument_configuration_id",
        ),
        ("derived_action_outcome", ("properties", "action_id"), "action_id"),
    ],
)
def test_stage6_uses_frozen_shared_identifier_reference(
    schema_name: str,
    path: tuple[str, ...],
    common_definition: str,
    schemas: dict[str, dict[str, Any]],
) -> None:
    node: Any = schemas[schema_name]
    for component in path:
        node = node[component]
    assert node["$ref"] == SCHEMA_IDS["common"] + f"#/$defs/{common_definition}"


def test_stage6_schemas_validate_from_explicit_local_store_without_network(
    monkeypatch: pytest.MonkeyPatch,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access was attempted")

    monkeypatch.setattr(urllib.request, "urlopen", fail_network)
    assert_valid(valid_evidence_event(), schemas["evidence_event"], schema_store)
    assert_valid(
        valid_action_outcome(), schemas["derived_action_outcome"], schema_store
    )
    assert_valid(valid_run_outcome(), schemas["derived_run_outcome"], schema_store)


def test_stage6_contract_comments_preserve_reference_existence_limit(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert "does not establish event existence" in schemas["derived_action_outcome"][
        "$comment"
    ]
    assert "does not establish artifact existence" in schemas["derived_run_outcome"][
        "properties"
    ]["action_outcome_references"]["$comment"]


def test_stage6_schema_property_names_exclude_unsafe_or_conflated_fields(
    schemas: dict[str, dict[str, Any]],
) -> None:
    property_names: set[str] = set()
    pending: list[Any] = [
        schemas["evidence_event"],
        schemas["derived_action_outcome"],
        schemas["derived_run_outcome"],
    ]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                property_names.update(properties)
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)

    for forbidden in (
        "exploit_payload",
        "malware_path",
        "target_ip",
        "target_url",
        "stolen_password",
        "api_key",
        "agent_claimed_success",
        "model_verdict",
        "risk_difference",
        "risk_ratio",
        "p_value",
        "confidence_interval",
    ):
        assert forbidden not in property_names
