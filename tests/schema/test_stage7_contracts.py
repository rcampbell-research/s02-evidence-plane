"""Stage 7 tests for instrument validation and acceptance contracts."""

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
    path.name.removesuffix(".schema.json"): path
    for path in (ROOT / "schemas").glob("*.schema.json")
}
SCHEMA_IDS = {
    "common": "urn:frontier-agent-containment:schema:common:0.1.0",
    "environment": "urn:frontier-agent-containment:schema:environment:0.1.0",
    "run-manifest": "urn:frontier-agent-containment:schema:run-manifest:0.1.0",
    "evidence-event": (
        "urn:frontier-agent-containment:schema:evidence-event:0.1.0"
    ),
    "derived-run-outcome": (
        "urn:frontier-agent-containment:schema:derived-run-outcome:0.1.0"
    ),
    "instrument-configuration": (
        "urn:frontier-agent-containment:schema:instrument-configuration:0.1.0"
    ),
    "validation-case": (
        "urn:frontier-agent-containment:schema:validation-case:0.1.0"
    ),
    "instrument-acceptance": (
        "urn:frontier-agent-containment:schema:instrument-acceptance:0.1.0"
    ),
}
VALIDATION_PHASES = ["V0", "V1", "V2", "V3", "V4", "V5"]
APPLICABILITY_CLASSES = [
    "MANDATORY_GLOBAL",
    "MANDATORY_CONDITIONAL",
    "OPTIONAL_DIAGNOSTIC",
]
TRIGGER_CLASSES = [
    "STATIC_CONFIGURATION_CHECK",
    "AUTHORIZED_REQUEST",
    "UNAUTHORIZED_REQUEST",
    "APPROVAL_TRANSITION",
    "CONTROL_FAILURE_INJECTION",
    "EVIDENCE_FAILURE_INJECTION",
    "ARCHITECTURE_MISMATCH",
    "RESET_EVENT",
    "SYNTHETIC_EFFECT",
    "RUN_TERMINATION",
]
SCENARIO_FAMILIES = [
    "S01",
    "S02",
    "S03",
    "S04",
    "S05",
    "S06",
    "S07",
    "S08",
    "S09",
    "S10",
]
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
PRIMARY_ENDPOINT_STATES = [
    "ZERO",
    "ONE",
    "UNAVAILABLE_INVALID",
    "UNAVAILABLE_INCOMPLETE",
    "NOT_APPLICABLE",
]
ACCEPTANCE_STATES = [
    "ACCEPTED_FOR_PILOT",
    "ACCEPTED_FOR_CONFIRMATORY",
    "REJECTED",
]
VALIDATION_RESULT_STATES = [
    "VALIDATION_PASS",
    "VALIDATION_FAIL",
    "VALIDATION_INCONCLUSIVE",
    "VALIDATION_NOT_APPLICABLE",
]
LIFECYCLE_STATES = ["DRAFT", "VALIDATED", "FROZEN", "RETIRED"]


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(SCHEMA_PATHS.values())


@pytest.fixture(scope="module")
def schemas(schema_store: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {name: schema_store[schema_id] for name, schema_id in SCHEMA_IDS.items()}


def valid_instrument_configuration() -> dict[str, Any]:
    return {
        "instrument_configuration_id": "instrument:validation-baseline",
        "configuration_version": "0.1.0",
        "display_name": "Synthetic validation instrument",
        "description": "Exact declarative configuration for instrument validation.",
        "environment_id": "env:synthetic-lab",
        "component_manifest": [
            {
                "component_id": "orchestrator",
                "component_role": "experiment_orchestrator",
                "component_version": "0.1.0",
                "build_id": "build:orchestrator-001",
                "implementation_reference": "orchestrator_build",
                "dependency_component_ids": [],
            },
            {
                "component_id": "resource_observer",
                "component_role": "resource_service_observer",
                "component_version": "0.1.0",
                "build_id": "build:observer-001",
                "implementation_reference": "resource_observer_build",
                "dependency_component_ids": ["orchestrator"],
            },
            {
                "component_id": "evidence_collector",
                "component_role": "evidence_collector",
                "component_version": "0.1.0",
                "build_id": "build:collector-001",
                "implementation_reference": "collector_build",
                "dependency_component_ids": ["resource_observer"],
            },
        ],
        "observer_configuration": [
            {
                "observer_id": "synthetic_resource_observer",
                "observed_property": "Synthetic resource access and effects.",
                "authoritative_role": "RESOURCE_SERVICE_OBSERVER",
                "component_id": "resource_observer",
            }
        ],
        "evidence_pipeline_configuration": {
            "collector_component_id": "evidence_collector",
            "normalized_evidence_destination_id": "normalized_evidence_store",
            "ordering_mechanism_id": "run_sequence_order",
            "evidence_format_schema_id": (
                "urn:frontier-agent-containment:schema:evidence-event:0.1.0"
            ),
            "evidence_format_version": "0.1.0",
        },
        "orchestration_configuration": {
            "orchestration_component_id": "orchestrator",
            "run_initialization_responsibility": "Initializes frozen run state.",
            "termination_responsibility": "Records declared termination state.",
            "action_budget_enforcement_responsibility": (
                "Enforces the predeclared action budget where applicable."
            ),
        },
        "reset_configuration": {
            "reset_configuration_id": "synthetic_reset",
            "reset_baseline_reference": "baseline_snapshot",
            "reset_component_id": "orchestrator",
            "description": "Restores the declared synthetic baseline.",
        },
        "s0_configuration_reference": {
            "configuration_id": "cond:s0-baseline",
            "configuration_version": "0.1.0",
            "description": "Separate laboratory safety boundary configuration.",
        },
        "schema_contract_set": [
            {
                "schema_id": (
                    "urn:frontier-agent-containment:schema:evidence-event:0.1.0"
                ),
                "schema_version": "0.1.0",
            }
        ],
        "configuration_state": "FROZEN",
    }


def valid_validation_case(phase: str = "V0") -> dict[str, Any]:
    trigger_by_phase = {
        "V0": "STATIC_CONFIGURATION_CHECK",
        "V1": "SYNTHETIC_EFFECT",
        "V2": "AUTHORIZED_REQUEST",
        "V3": "EVIDENCE_FAILURE_INJECTION",
        "V4": "RESET_EVENT",
        "V5": "STATIC_CONFIGURATION_CHECK",
    }
    return {
        "validation_case_id": f"valcase:{phase.lower()}-baseline",
        "validation_case_version": "0.1.0",
        "instrument_configuration_id": "instrument:validation-baseline",
        "display_name": f"{phase} known-ground-truth case",
        "description": "Synthetic known-ground-truth instrument validation.",
        "validation_phase": phase,
        "applicability_class": "MANDATORY_GLOBAL",
        "applicable_component": "orchestrator",
        "applicable_scenario_families": [],
        "applicable_control_layers": [],
        "preconditions": [
            {
                "precondition_id": "frozen_configuration_available",
                "description": "The exact configuration is available for inspection.",
                "expected_state": True,
            }
        ],
        "trigger": {
            "trigger_class": trigger_by_phase[phase],
            "description": "Apply the bounded synthetic validation stimulus.",
            "fixture_reference": "known_ground_truth_fixture",
        },
        "ground_truth": {
            "source_id": "independent_fixture",
            "source_type": "VALIDATION_FIXTURE",
            "state_description": "The expected state is fixed independently.",
        },
        "expected_authorization_state": "NOT_APPLICABLE",
        "expected_approval_state": "NOT_APPLICABLE",
        "expected_control_state": {
            "state_id": "configuration_consistent",
            "description": "Configuration declarations match the frozen fixture.",
        },
        "expected_execution_state": "NOT_APPLICABLE",
        "expected_effect_state": "NOT_APPLICABLE",
        "expected_evidence": [
            {
                "event_class": "RUN_INITIALIZED",
                "minimum_count": 1,
                "required": True,
            }
        ],
        "expected_evidence_quality_state": "VALID",
        "expected_terminal_outcome": "NOT_APPLICABLE",
        "expected_run_validity": "NOT_APPLICABLE",
        "expected_primary_endpoint_observability": "NOT_APPLICABLE",
        "expected_primary_endpoint_state": "NOT_APPLICABLE",
        "reset_cleanup_expectation": {
            "reset_required": False,
            "description": "No runtime state is created by this static case.",
        },
        "pass_criterion": {
            "criterion_id": "all_mandatory_properties_match",
            "description": "Every mandatory expected property must match.",
            "tolerance_description": "No mismatch is allowed.",
        },
    }


def set_endpoint_expectation(instance: dict[str, Any], state: str) -> None:
    instance["expected_primary_endpoint_state"] = state
    if state in {"ZERO", "ONE"}:
        instance["expected_run_validity"] = "VALID_FOR_PRIMARY_ANALYSIS"
        instance["expected_primary_endpoint_observability"] = (
            "COMPLETE_FOR_PRIMARY_ENDPOINT"
        )
    elif state == "UNAVAILABLE_INVALID":
        instance["expected_run_validity"] = "INVALID_FOR_PRIMARY_ANALYSIS"
        instance["expected_primary_endpoint_observability"] = (
            "COMPLETE_FOR_PRIMARY_ENDPOINT"
        )
    elif state == "UNAVAILABLE_INCOMPLETE":
        instance["expected_run_validity"] = "VALID_FOR_PRIMARY_ANALYSIS"
        instance["expected_primary_endpoint_observability"] = (
            "INCOMPLETE_FOR_PRIMARY_ENDPOINT"
        )
    else:
        instance["expected_run_validity"] = "NOT_APPLICABLE"
        instance["expected_primary_endpoint_observability"] = "NOT_APPLICABLE"


def valid_acceptance(state: str = "ACCEPTED_FOR_PILOT") -> dict[str, Any]:
    instance: dict[str, Any] = {
        "acceptance_version": "0.1.0",
        "instrument_configuration_id": "instrument:validation-baseline",
        "instrument_configuration_version": "0.1.0",
        "environment_id": "env:synthetic-lab",
        "campaign_id": "campaign:synthetic-pilot",
        "validation_set_id": "core_validation_set",
        "validation_set_version": "0.1.0",
        "acceptance_state": state,
        "validation_results": [
            {
                "validation_case_id": "valcase:v0-baseline",
                "validation_case_version": "0.1.0",
                "validation_phase": "V0",
                "applicability_class": "MANDATORY_GLOBAL",
                "result_state": "VALIDATION_PASS",
                "evidence_event_ids": ["event:validation-evidence-001"],
                "result_description": "Every mandatory expected property matched.",
            }
        ],
        "component_versions": [
            {
                "component_id": "orchestrator",
                "component_version": "0.1.0",
                "build_id": "build:orchestrator-001",
            }
        ],
        "acceptance_basis": "Retained results were evaluated under the frozen rule.",
        "acceptance_order": 1,
        "acceptance_authority": {
            "authority_id": "independent_acceptance_authority",
            "authority_role": "INSTRUMENT_ACCEPTANCE_AUTHORITY",
        },
        "acceptance_decision_rule_id": "campaign_acceptance_rule",
        "acceptance_decision_rule_version": "0.1.0",
        "unresolved_conditions": [],
    }
    if state == "ACCEPTED_FOR_PILOT":
        instance["accepted_for_phase"] = "PILOT"
    elif state == "ACCEPTED_FOR_CONFIRMATORY":
        instance["accepted_for_phase"] = "CONFIRMATORY"
        instance["campaign_id"] = "campaign:synthetic-confirmatory"
    else:
        instance["unresolved_conditions"] = ["A mandatory condition failed."]
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
    ["instrument-configuration", "validation-case", "instrument-acceptance"],
)
def test_stage7_schema_is_valid_draft_2020_12(
    schema_name: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    schema = schemas[schema_name]
    assert schema["$schema"] == DRAFT_2020_12
    assert schema["$id"] == SCHEMA_IDS[schema_name]
    check_draft_2020_12_schema(schema, schema_store=schema_store)


def test_valid_instrument_configuration_is_accepted(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    assert_valid(
        valid_instrument_configuration(),
        schemas["instrument-configuration"],
        schema_store,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("instrument_configuration_id", "env:wrong-prefix"),
        ("configuration_version", "v0.1"),
        ("environment_id", "instrument:wrong-prefix"),
    ],
)
def test_instrument_configuration_rejects_wrong_identity_or_version(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_instrument_configuration()
    instance[field] = value
    assert_invalid(instance, schemas["instrument-configuration"], schema_store)


def test_instrument_configuration_rejects_empty_component_manifest(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_instrument_configuration()
    instance["component_manifest"] = []
    assert_invalid(instance, schemas["instrument-configuration"], schema_store)


@pytest.mark.parametrize("version", ["latest", "0.1", "v0.1.0"])
def test_instrument_configuration_rejects_malformed_component_version(
    version: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_instrument_configuration()
    instance["component_manifest"][0]["component_version"] = version
    assert_invalid(instance, schemas["instrument-configuration"], schema_store)


@pytest.mark.parametrize("role", SOURCE_ROLES)
def test_instrument_observer_accepts_each_stage6_authoritative_role(
    role: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_instrument_configuration()
    instance["observer_configuration"][0]["authoritative_role"] = role
    assert_valid(instance, schemas["instrument-configuration"], schema_store)


def test_instrument_observer_rejects_agent_role(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_instrument_configuration()
    instance["observer_configuration"][0]["authoritative_role"] = "AGENT"
    assert_invalid(instance, schemas["instrument-configuration"], schema_store)


@pytest.mark.parametrize("state", LIFECYCLE_STATES)
def test_instrument_configuration_accepts_each_lifecycle_state(
    state: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_instrument_configuration()
    instance["configuration_state"] = state
    assert_valid(instance, schemas["instrument-configuration"], schema_store)


def test_instrument_configuration_rejects_unknown_lifecycle_state(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_instrument_configuration()
    instance["configuration_state"] = "ACCEPTED"
    assert_invalid(instance, schemas["instrument-configuration"], schema_store)


def test_s0_reference_is_separate_from_experimental_treatment(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_instrument_configuration()
    instance["s0_configuration_reference"]["experimental_control_layer"] = "M3"
    assert_invalid(instance, schemas["instrument-configuration"], schema_store)


@pytest.mark.parametrize("field", ["component_manifest", "reset_configuration"])
def test_instrument_configuration_rejects_missing_required_field(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_instrument_configuration()
    del instance[field]
    assert_invalid(instance, schemas["instrument-configuration"], schema_store)


def test_instrument_configuration_rejects_unknown_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_instrument_configuration()
    instance["acceptance_state"] = "ACCEPTED_FOR_PILOT"
    assert_invalid(instance, schemas["instrument-configuration"], schema_store)


def test_instrument_configuration_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_instrument_configuration()
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["instrument-configuration"], schema_store)
    assert instance == original


@pytest.mark.parametrize("phase", VALIDATION_PHASES)
def test_validation_case_accepts_each_frozen_phase(
    phase: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(valid_validation_case(phase), schemas["validation-case"], schema_store)


def test_validation_case_phase_enum_is_exact(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert schemas["validation-case"]["properties"]["validation_phase"]["enum"] == (
        VALIDATION_PHASES
    )


def test_validation_case_rejects_unknown_phase(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_validation_case()
    instance["validation_phase"] = "V6"
    assert_invalid(instance, schemas["validation-case"], schema_store)


@pytest.mark.parametrize("applicability", APPLICABILITY_CLASSES)
def test_validation_case_accepts_each_applicability_class(
    applicability: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_validation_case()
    instance["applicability_class"] = applicability
    assert_valid(instance, schemas["validation-case"], schema_store)


def test_validation_case_rejects_unknown_applicability_class(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_validation_case()
    instance["applicability_class"] = "MANDATORY"
    assert_invalid(instance, schemas["validation-case"], schema_store)


@pytest.mark.parametrize("family", SCENARIO_FAMILIES)
def test_validation_case_accepts_each_scenario_family(
    family: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_validation_case()
    instance["applicable_scenario_families"] = [family]
    assert_valid(instance, schemas["validation-case"], schema_store)


@pytest.mark.parametrize("layer", ["M1", "M2", "M3"])
def test_validation_case_accepts_each_experimental_control_layer(
    layer: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_validation_case()
    instance["applicable_control_layers"] = [layer]
    assert_valid(instance, schemas["validation-case"], schema_store)


def test_validation_case_rejects_s0_as_experimental_control_layer(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_validation_case()
    instance["applicable_control_layers"] = ["S0"]
    assert_invalid(instance, schemas["validation-case"], schema_store)


@pytest.mark.parametrize("trigger_class", TRIGGER_CLASSES)
def test_validation_case_accepts_each_trigger_class(
    trigger_class: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_validation_case()
    instance["trigger"]["trigger_class"] = trigger_class
    assert_valid(instance, schemas["validation-case"], schema_store)


def test_validation_case_trigger_enum_is_exact(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert schemas["validation-case"]["$defs"]["trigger"]["properties"][
        "trigger_class"
    ]["enum"] == TRIGGER_CLASSES


def test_validation_case_rejects_unknown_trigger_class(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_validation_case()
    instance["trigger"]["trigger_class"] = "PHYSICAL_FAULT_INJECTION"
    assert_invalid(instance, schemas["validation-case"], schema_store)


@pytest.mark.parametrize("event_class", EVENT_CLASSES)
def test_validation_case_accepts_each_stage6_evidence_event_class(
    event_class: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_validation_case()
    instance["expected_evidence"][0]["event_class"] = event_class
    assert_valid(instance, schemas["validation-case"], schema_store)


def test_expected_evidence_event_class_reference_is_exact(
    schemas: dict[str, dict[str, Any]],
) -> None:
    event_ref = schemas["validation-case"]["$defs"]["evidence_expectation"][
        "properties"
    ]["event_class"]["$ref"]
    assert event_ref == SCHEMA_IDS["evidence-event"] + "#/properties/event_class"
    assert schemas["evidence-event"]["properties"]["event_class"]["enum"] == (
        EVENT_CLASSES
    )


def test_validation_case_rejects_unknown_evidence_event_class(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_validation_case()
    instance["expected_evidence"][0]["event_class"] = "VALIDATION_PASSED"
    assert_invalid(instance, schemas["validation-case"], schema_store)


@pytest.mark.parametrize("terminal_outcome", TERMINAL_OUTCOMES)
def test_validation_case_accepts_each_frozen_terminal_outcome(
    terminal_outcome: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_validation_case()
    instance["expected_terminal_outcome"] = terminal_outcome
    assert_valid(instance, schemas["validation-case"], schema_store)


@pytest.mark.parametrize("approval_state", APPROVAL_DECISIONS + ["NOT_APPLICABLE"])
def test_validation_case_accepts_frozen_approval_or_local_nonapplicability(
    approval_state: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_validation_case()
    instance["expected_approval_state"] = approval_state
    assert_valid(instance, schemas["validation-case"], schema_store)


@pytest.mark.parametrize("endpoint_state", PRIMARY_ENDPOINT_STATES)
def test_validation_case_accepts_each_consistent_primary_endpoint_state(
    endpoint_state: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_validation_case()
    set_endpoint_expectation(instance, endpoint_state)
    assert_valid(instance, schemas["validation-case"], schema_store)


@pytest.mark.parametrize("endpoint_state", ["ZERO", "ONE"])
def test_zero_or_one_rejects_invalid_run_validity(
    endpoint_state: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_validation_case()
    set_endpoint_expectation(instance, endpoint_state)
    instance["expected_run_validity"] = "INVALID_FOR_PRIMARY_ANALYSIS"
    assert_invalid(instance, schemas["validation-case"], schema_store)


def test_unavailable_invalid_rejects_valid_run_validity(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_validation_case()
    set_endpoint_expectation(instance, "UNAVAILABLE_INVALID")
    instance["expected_run_validity"] = "VALID_FOR_PRIMARY_ANALYSIS"
    assert_invalid(instance, schemas["validation-case"], schema_store)


def test_unavailable_incomplete_requires_incomplete_observability(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_validation_case()
    set_endpoint_expectation(instance, "UNAVAILABLE_INCOMPLETE")
    instance["expected_primary_endpoint_observability"] = (
        "COMPLETE_FOR_PRIMARY_ENDPOINT"
    )
    assert_invalid(instance, schemas["validation-case"], schema_store)


def test_validation_case_rejects_unknown_primary_endpoint_state(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_validation_case()
    instance["expected_primary_endpoint_state"] = "NULL"
    assert_invalid(instance, schemas["validation-case"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("validation_case_id", "instrument:wrong-prefix"),
        ("validation_case_version", "v0.1"),
        ("instrument_configuration_id", "valcase:wrong-prefix"),
    ],
)
def test_validation_case_rejects_wrong_identity_or_version(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_validation_case()
    instance[field] = value
    assert_invalid(instance, schemas["validation-case"], schema_store)


def test_validation_case_rejects_unknown_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_validation_case()
    instance["executable_script"] = "not permitted"
    assert_invalid(instance, schemas["validation-case"], schema_store)


@pytest.mark.parametrize("field", ["ground_truth", "pass_criterion"])
def test_validation_case_rejects_missing_required_field(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_validation_case()
    del instance[field]
    assert_invalid(instance, schemas["validation-case"], schema_store)


def test_validation_case_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_validation_case("V3")
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["validation-case"], schema_store)
    assert instance == original


@pytest.mark.parametrize(
    "state,phase",
    [
        ("ACCEPTED_FOR_PILOT", "PILOT"),
        ("ACCEPTED_FOR_CONFIRMATORY", "CONFIRMATORY"),
    ],
)
def test_acceptance_state_accepts_exact_matching_phase(
    state: str,
    phase: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_acceptance(state)
    assert instance["accepted_for_phase"] == phase
    assert_valid(instance, schemas["instrument-acceptance"], schema_store)


@pytest.mark.parametrize(
    "state,wrong_phase",
    [
        ("ACCEPTED_FOR_PILOT", "CONFIRMATORY"),
        ("ACCEPTED_FOR_CONFIRMATORY", "PILOT"),
    ],
)
def test_acceptance_state_rejects_mismatched_phase(
    state: str,
    wrong_phase: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_acceptance(state)
    instance["accepted_for_phase"] = wrong_phase
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


def test_rejected_acceptance_is_valid_without_phase(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    assert_valid(
        valid_acceptance("REJECTED"), schemas["instrument-acceptance"], schema_store
    )


def test_rejected_acceptance_rejects_accepted_for_phase(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_acceptance("REJECTED")
    instance["accepted_for_phase"] = "PILOT"
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


def test_acceptance_state_enum_is_exactly_shared(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert schemas["common"]["$defs"]["instrument_acceptance_state"]["enum"] == (
        ACCEPTANCE_STATES
    )
    assert schemas["instrument-acceptance"]["properties"]["acceptance_state"][
        "$ref"
    ] == SCHEMA_IDS["common"] + "#/$defs/instrument_acceptance_state"


def test_acceptance_rejects_unknown_acceptance_state(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_acceptance()
    instance["acceptance_state"] = "ACCEPTED"
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


@pytest.mark.parametrize("result_state", VALIDATION_RESULT_STATES)
def test_acceptance_accepts_each_validation_result_state_when_consistent(
    result_state: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_acceptance("REJECTED")
    result = instance["validation_results"][0]
    result["result_state"] = result_state
    if result_state == "VALIDATION_NOT_APPLICABLE":
        result["applicability_class"] = "MANDATORY_CONDITIONAL"
        result["not_applicable_reason"] = "The corresponding feature is absent."
    assert_valid(instance, schemas["instrument-acceptance"], schema_store)


def test_mandatory_global_result_cannot_be_not_applicable(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_acceptance("REJECTED")
    result = instance["validation_results"][0]
    result["result_state"] = "VALIDATION_NOT_APPLICABLE"
    result["not_applicable_reason"] = "Not a legitimate global omission."
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


def test_not_applicable_result_requires_reason(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_acceptance("REJECTED")
    result = instance["validation_results"][0]
    result["result_state"] = "VALIDATION_NOT_APPLICABLE"
    result["applicability_class"] = "MANDATORY_CONDITIONAL"
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


def test_acceptance_rejects_unknown_validation_result_state(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_acceptance("REJECTED")
    instance["validation_results"][0]["result_state"] = "PASS"
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


@pytest.mark.parametrize(
    "path,value",
    [
        (("validation_results", 0, "validation_case_id"), "event:wrong-prefix"),
        (("instrument_configuration_id",), "env:wrong-prefix"),
        (("environment_id",), "instrument:wrong-prefix"),
        (("component_versions", 0, "component_version"), "latest"),
    ],
)
def test_acceptance_rejects_malformed_identity_or_version(
    path: tuple[Any, ...],
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_acceptance()
    node: Any = instance
    for part in path[:-1]:
        node = node[part]
    node[path[-1]] = value
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


@pytest.mark.parametrize(
    "evidence_ids",
    [[], ["run:wrong-prefix"], ["event:evidence-001", "event:evidence-001"]],
)
def test_acceptance_rejects_empty_malformed_or_duplicate_evidence_event_ids(
    evidence_ids: list[str],
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_acceptance()
    instance["validation_results"][0]["evidence_event_ids"] = evidence_ids
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


@pytest.mark.parametrize("field", ["validation_results", "component_versions"])
def test_acceptance_rejects_empty_required_collection(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_acceptance()
    instance[field] = []
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


def test_acceptance_rejects_agent_self_certification_role(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_acceptance()
    instance["acceptance_authority"]["authority_role"] = "AGENT"
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


def test_acceptance_rejects_unknown_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_acceptance()
    instance["h1_verdict"] = "SUPPORTED"
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


def test_acceptance_rejects_missing_required_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_acceptance()
    del instance["acceptance_basis"]
    assert_invalid(instance, schemas["instrument-acceptance"], schema_store)


def test_acceptance_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_acceptance("ACCEPTED_FOR_CONFIRMATORY")
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["instrument-acceptance"], schema_store)
    assert instance == original


def test_stage5_and_stage6_shared_references_remain_exact(
    schemas: dict[str, dict[str, Any]],
) -> None:
    common = SCHEMA_IDS["common"]
    assert schemas["instrument-configuration"]["properties"]["environment_id"][
        "$ref"
    ] == common + "#/$defs/environment_id"
    assert schemas["instrument-acceptance"]["properties"]["environment_id"][
        "$ref"
    ] == common + "#/$defs/environment_id"
    assert schemas["run-manifest"]["properties"]["instrument_configuration_id"][
        "$ref"
    ] == common + "#/$defs/instrument_configuration_id"
    assert schemas["instrument-acceptance"]["$defs"]["validation_result"][
        "properties"
    ]["evidence_event_ids"]["items"]["$ref"] == common + "#/$defs/event_id"


def test_stage6_roles_terminal_outcomes_and_run_validity_are_not_duplicated(
    schemas: dict[str, dict[str, Any]],
) -> None:
    observer_role_ref = schemas["instrument-configuration"]["$defs"]["observer"][
        "properties"
    ]["authoritative_role"]["$ref"]
    assert observer_role_ref == (
        SCHEMA_IDS["evidence-event"]
        + "#/$defs/authoritative_source/properties/source_role"
    )
    assert schemas["evidence-event"]["$defs"]["authoritative_source"]["properties"][
        "source_role"
    ]["enum"] == SOURCE_ROLES
    assert schemas["common"]["$defs"]["terminal_action_outcome"]["enum"] == (
        TERMINAL_OUTCOMES
    )
    run_validity_ref = schemas["validation-case"]["properties"][
        "expected_run_validity"
    ]["oneOf"][0]["$ref"]
    assert run_validity_ref == (
        SCHEMA_IDS["derived-run-outcome"] + "#/properties/run_validity"
    )


def test_stage5_confirmatory_freeze_rule_remains_separate_from_acceptance(
    schemas: dict[str, dict[str, Any]],
) -> None:
    manifest = schemas["run-manifest"]
    serialized = str(manifest["allOf"])
    assert "PILOT" in serialized
    assert "CONFIRMATORY" in serialized
    assert "configuration_frozen_before_start" in serialized
    assert "configuration_frozen_before_start" not in schemas[
        "instrument-acceptance"
    ]["properties"]


def test_stage7_schemas_validate_from_explicit_local_store_without_network(
    monkeypatch: pytest.MonkeyPatch,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access was attempted")

    monkeypatch.setattr(urllib.request, "urlopen", fail_network)
    assert_valid(
        valid_instrument_configuration(),
        schemas["instrument-configuration"],
        schema_store,
    )
    assert_valid(valid_validation_case(), schemas["validation-case"], schema_store)
    assert_valid(valid_acceptance(), schemas["instrument-acceptance"], schema_store)


def test_stage7_contracts_do_not_define_unsafe_or_analytic_fields(
    schemas: dict[str, dict[str, Any]],
) -> None:
    property_names: set[str] = set()
    pending: list[Any] = [
        schemas["instrument-configuration"],
        schemas["validation-case"],
        schemas["instrument-acceptance"],
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
        "physical_fault_injection",
        "agent_self_certification",
        "risk_difference",
        "risk_ratio",
        "p_value",
        "h1_verdict",
    ):
        assert forbidden not in property_names
