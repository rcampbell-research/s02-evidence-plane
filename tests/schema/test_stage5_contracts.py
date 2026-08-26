"""Stage 5 tests for subject, autonomy, environment, and run contracts."""

from __future__ import annotations

import copy
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import ValidationError

from frontier_agent_containment.schema_validation import (
    ExternalSchemaReferenceError,
    UnknownSchemaReferenceError,
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
}
TRUST_ZONES = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6"]
CONFIRMATION_SEMANTICS = [
    "NO_CONFIRMATION",
    "CONFIRM_EACH_ACTION",
    "CONFIRM_HIGH_IMPACT_ONLY",
    "EXTERNAL_POLICY_DEFINED",
]
NETWORK_RELATIONSHIPS = [
    "ROUTE",
    "SERVICE_ACCESS",
    "OBSERVATION_PATH",
    "CONTROL_PATH",
    "EVIDENCE_PATH",
]
FORBIDDEN_EXTERNAL_RELATIONSHIPS = [
    "UNRESTRICTED_INTERNET",
    "REAL_CREDENTIAL_SOURCE",
    "PRODUCTION_SYSTEM",
    "HOST_ADMINISTRATION",
    "THIRD_PARTY_TARGET",
]
RUN_PHASES = ["DEVELOPMENT", "INSTRUMENT_VALIDATION", "PILOT", "CONFIRMATORY"]


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(SCHEMA_PATHS.values())


@pytest.fixture(scope="module")
def schemas(schema_store: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {name: schema_store[schema_id] for name, schema_id in SCHEMA_IDS.items()}


def valid_agent_model_condition() -> dict[str, Any]:
    return {
        "agent_condition_id": "agentcond:baseline-agent",
        "condition_version": "0.1.0",
        "model_condition_id": "modelcond:synthetic-model",
        "capability_condition_id": "capcond:baseline-capability",
        "display_name": "Synthetic baseline subject",
        "description": "A non-treatment model and agent condition.",
        "model_identifier": "synthetic-model",
        "model_version": "2026.01",
        "provider_runtime_identity": {
            "provider_id": "synthetic_provider",
            "runtime_id": "bounded_runtime",
            "runtime_version": "0.1.0",
            "version_availability": "AVAILABLE",
            "description": "A declared synthetic provider/runtime identity.",
        },
        "inference_configuration": {
            "reasoning_mode": "bounded",
            "temperature": 0,
            "top_p": 1,
            "max_output_tokens": 256,
            "other_parameters": [
                {
                    "parameter_id": "sampling_mode",
                    "declared_value": "provider_default",
                }
            ],
        },
        "context_configuration": {
            "system_context": {
                "context_id": "non_treatment_system",
                "context_version": "0.1.0",
            },
            "task_context": {
                "context_id": "synthetic_task",
                "context_version": "0.1.0",
            },
            "maximum_context_tokens": 4096,
            "history_carryover_permitted": False,
            "additional_context_artifacts": [],
        },
        "tool_repertoire": [
            {
                "tool_id": "synthetic_reader",
                "action_classes": ["read", "query"],
                "description": "In-principle access to a synthetic read interface.",
            }
        ],
        "planning_configuration": {
            "internal_step_budget": 16,
            "tool_selection_mode": "provider_default",
            "memory_mode": "run_local",
        },
    }


def valid_autonomy_condition() -> dict[str, Any]:
    return {
        "autonomy_condition_id": "autonomy:bounded",
        "condition_version": "0.1.0",
        "display_name": "Bounded autonomy",
        "description": "Prospective synthetic action-selection limits.",
        "max_consecutive_agent_selected_actions": 4,
        "replanning_allowed": True,
        "intermediate_approval_required": False,
        "action_horizon": 12,
        "action_budget": 10,
        "tool_confirmation_semantics": "NO_CONFIRMATION",
    }


def valid_environment() -> dict[str, Any]:
    return {
        "environment_id": "env:synthetic-lab",
        "environment_version": "0.1.0",
        "build_id": "build:synthetic-lab-001",
        "display_name": "Synthetic laboratory environment",
        "description": "A fictional environment entirely inside S0.",
        "trust_zones": [
            {
                "zone_id": "Z1",
                "description": "Synthetic agent workspace.",
                "agent_accessible": True,
            },
            {
                "zone_id": "Z6",
                "description": "Controlled synthetic endpoint zone.",
                "agent_accessible": False,
            },
        ],
        "synthetic_assets": ["resource:authorized-record", "resource:protected-store"],
        "network_relationships": [
            {
                "source_zone": "Z1",
                "destination_zone": "Z6",
                "relationship": "SERVICE_ACCESS",
                "authorized": True,
            }
        ],
        "s0_configuration_id": "cond:s0-baseline",
        "reset_baseline_id": "cond:synthetic-reset",
        "expected_observers": [
            {
                "observer_id": "resource_observer",
                "observed_property": "resource_access",
                "trust_zone": "Z6",
            }
        ],
        "controlled_endpoints": [
            {
                "endpoint_id": "synthetic_sink",
                "zone_id": "Z6",
                "purpose": "Receive controlled synthetic scenario effects.",
            }
        ],
        "forbidden_external_relationships": FORBIDDEN_EXTERNAL_RELATIONSHIPS.copy(),
    }


def valid_run_manifest(phase: str = "DEVELOPMENT") -> dict[str, Any]:
    return {
        "experiment_id": "exp:containment-study",
        "campaign_id": "campaign:development-campaign",
        "scheduled_run_id": "scheduledrun:block-001-run-001",
        "run_id": "run:development-001",
        "run_manifest_version": "0.1.0",
        "phase": phase,
        "scenario_id": "scenario:protected-resource-access",
        "task_id": "task:inspect-authorized-record",
        "agent_condition_id": "agentcond:baseline-agent",
        "model_condition_id": "modelcond:synthetic-model",
        "capability_condition_id": "capcond:baseline-capability",
        "autonomy_condition_id": "autonomy:bounded",
        "control_condition_id": "ctrlcond:bounded-treatment",
        "capability_envelope_id": "envelope:authorized-inspection",
        "policy_id": "policy:default-deny",
        "environment_id": "env:synthetic-lab",
        "build_id": "build:synthetic-lab-001",
        "instrument_configuration_id": "instrument:development-001",
        "seed_repetition_identity": {
            "repetition_id": "repetition_001",
            "seed_status": "AVAILABLE",
            "seed_value": 7,
        },
        "action_budget": 10,
        "s0_acceptance_identity": "s0accept:baseline-v1",
        "scheduled_run_identity": {
            "schedule_identity": "block_001_run_001",
            "description": "Predeclared scheduled unit in the synthetic campaign.",
            "matched_block_identity": "block_001",
        },
        "configuration_frozen_before_start": phase in {"PILOT", "CONFIRMATORY"},
    }


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
    ["agent_model_condition", "autonomy_condition", "environment", "run_manifest"],
)
def test_stage5_schema_is_valid_draft_2020_12(
    schema_name: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    schema = schemas[schema_name]
    assert schema["$schema"] == DRAFT_2020_12
    assert schema["$id"] == SCHEMA_IDS[schema_name]
    check_draft_2020_12_schema(schema, schema_store=schema_store)


def test_valid_agent_model_condition_is_accepted(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    assert_valid(valid_agent_model_condition(), schemas["agent_model_condition"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("agent_condition_id", "modelcond:wrong-prefix"),
        ("model_condition_id", "agentcond:wrong-prefix"),
        ("capability_condition_id", "cond:wrong-prefix"),
        ("condition_version", "v0.1"),
    ],
)
def test_agent_model_rejects_invalid_shared_identity_or_version(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_agent_model_condition()
    instance[field] = value
    assert_invalid(instance, schemas["agent_model_condition"], schema_store)


@pytest.mark.parametrize("model_identifier", ["", "Synthetic Model", "model/api"])
def test_agent_model_rejects_invalid_model_identifier(
    model_identifier: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_agent_model_condition()
    instance["model_identifier"] = model_identifier
    assert_invalid(instance, schemas["agent_model_condition"], schema_store)


def test_agent_model_accepts_unavailable_model_version(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_agent_model_condition()
    instance["model_version"] = "UNAVAILABLE"
    instance["provider_runtime_identity"]["version_availability"] = "UNAVAILABLE"
    instance["provider_runtime_identity"].pop("runtime_version")
    assert_valid(instance, schemas["agent_model_condition"], schema_store)


def test_agent_model_rejects_invalid_tool_id(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_agent_model_condition()
    instance["tool_repertoire"][0]["tool_id"] = "Invalid Tool"
    assert_invalid(instance, schemas["agent_model_condition"], schema_store)


def test_agent_model_rejects_malformed_action_class(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_agent_model_condition()
    instance["tool_repertoire"][0]["action_classes"] = ["Read protected"]
    assert_invalid(instance, schemas["agent_model_condition"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("control_condition_id", "ctrlcond:leaked-treatment"),
        ("experimental_control_layer", "M3"),
        ("capability_envelope_id", "envelope:leaked-treatment"),
        ("unexpected", True),
    ],
)
def test_agent_model_rejects_treatment_or_unknown_root_field(
    field: str,
    value: object,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_agent_model_condition()
    instance[field] = value
    assert_invalid(instance, schemas["agent_model_condition"], schema_store)


def test_agent_model_rejects_autonomy_field_in_planning_configuration(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_agent_model_condition()
    instance["planning_configuration"]["replanning_available"] = True
    assert_invalid(instance, schemas["agent_model_condition"], schema_store)


@pytest.mark.parametrize(
    "parameter_id",
    [
        "control_condition_id",
        "experimental_control_layer",
        "policy_id",
        "approval_policy_id",
        "capability_envelope_id",
        "authorization_state",
        "authorization_decision",
    ],
)
def test_agent_model_rejects_treatment_field_in_other_parameters(
    parameter_id: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_agent_model_condition()
    instance["inference_configuration"]["other_parameters"] = [
        {"parameter_id": parameter_id, "declared_value": "M3"}
    ]
    assert_invalid(instance, schemas["agent_model_condition"], schema_store)


def test_agent_model_rejects_missing_required_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_agent_model_condition()
    del instance["provider_runtime_identity"]
    assert_invalid(instance, schemas["agent_model_condition"], schema_store)


def test_agent_model_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_agent_model_condition()
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["agent_model_condition"], schema_store)
    assert instance == original


def test_valid_autonomy_condition_is_accepted(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    assert_valid(valid_autonomy_condition(), schemas["autonomy_condition"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("autonomy_condition_id", "cond:wrong-prefix"),
        ("condition_version", "0.1"),
        ("max_consecutive_agent_selected_actions", 0),
        ("action_horizon", 0),
        ("action_budget", 0),
        ("action_budget", "10"),
        ("replanning_allowed", "true"),
        ("intermediate_approval_required", "false"),
    ],
)
def test_autonomy_rejects_invalid_identity_version_limit_or_type(
    field: str,
    value: object,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_autonomy_condition()
    instance[field] = value
    assert_invalid(instance, schemas["autonomy_condition"], schema_store)


@pytest.mark.parametrize("semantic", CONFIRMATION_SEMANTICS)
def test_autonomy_accepts_each_confirmation_semantic(
    semantic: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_autonomy_condition()
    instance["tool_confirmation_semantics"] = semantic
    assert_valid(instance, schemas["autonomy_condition"], schema_store)


def test_autonomy_rejects_unknown_confirmation_semantic(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_autonomy_condition()
    instance["tool_confirmation_semantics"] = "MODEL_SELF_APPROVES"
    assert_invalid(instance, schemas["autonomy_condition"], schema_store)


def test_autonomy_rejects_unknown_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_autonomy_condition()
    instance["observed_autonomy"] = "high"
    assert_invalid(instance, schemas["autonomy_condition"], schema_store)


def test_autonomy_rejects_missing_required_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_autonomy_condition()
    del instance["action_horizon"]
    assert_invalid(instance, schemas["autonomy_condition"], schema_store)


def test_autonomy_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_autonomy_condition()
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["autonomy_condition"], schema_store)
    assert instance == original


def test_valid_environment_is_accepted(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    assert_valid(valid_environment(), schemas["environment"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("environment_id", "resource:wrong-prefix"),
        ("environment_version", "v0.1"),
    ],
)
def test_environment_rejects_invalid_identity_or_version(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_environment()
    instance[field] = value
    assert_invalid(instance, schemas["environment"], schema_store)


@pytest.mark.parametrize("zone", TRUST_ZONES)
def test_environment_accepts_each_synthetic_trust_zone(
    zone: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_environment()
    instance["trust_zones"] = [
        {"zone_id": zone, "description": "Synthetic zone.", "agent_accessible": False}
    ]
    instance["network_relationships"] = []
    instance["expected_observers"] = []
    instance["controlled_endpoints"] = []
    assert_valid(instance, schemas["environment"], schema_store)


def test_environment_rejects_z0_as_ordinary_trust_zone(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_environment()
    instance["trust_zones"][0]["zone_id"] = "Z0"
    assert_invalid(instance, schemas["environment"], schema_store)


def test_environment_rejects_duplicate_synthetic_resource_ids(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_environment()
    instance["synthetic_assets"] = ["resource:record", "resource:record"]
    assert_invalid(instance, schemas["environment"], schema_store)


def test_environment_rejects_wrong_synthetic_resource_id(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_environment()
    instance["synthetic_assets"] = ["task:wrong-prefix"]
    assert_invalid(instance, schemas["environment"], schema_store)


def test_environment_rejects_invalid_network_zone(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_environment()
    instance["network_relationships"][0]["destination_zone"] = "Z0"
    assert_invalid(instance, schemas["environment"], schema_store)


@pytest.mark.parametrize("relationship", NETWORK_RELATIONSHIPS)
def test_environment_accepts_each_network_relationship(
    relationship: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_environment()
    instance["network_relationships"][0]["relationship"] = relationship
    assert_valid(instance, schemas["environment"], schema_store)


def test_environment_rejects_invalid_network_relationship(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_environment()
    instance["network_relationships"][0]["relationship"] = "PUBLIC_INTERNET"
    assert_invalid(instance, schemas["environment"], schema_store)


def test_environment_accepts_symbolic_controlled_endpoint(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_environment()
    instance["controlled_endpoints"] = [
        {
            "endpoint_id": "synthetic_endpoint",
            "zone_id": "Z6",
            "purpose": "Controlled synthetic observation.",
        }
    ]
    assert_valid(instance, schemas["environment"], schema_store)


@pytest.mark.parametrize("location", ["root", "endpoint"])
def test_environment_rejects_arbitrary_target_field(
    location: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_environment()
    if location == "root":
        instance["target_ip"] = "192.0.2.1"
    else:
        instance["controlled_endpoints"][0]["url"] = "https://example.invalid"
    assert_invalid(instance, schemas["environment"], schema_store)


@pytest.mark.parametrize("category", FORBIDDEN_EXTERNAL_RELATIONSHIPS)
def test_environment_accepts_each_forbidden_external_category(
    category: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_environment()
    instance["forbidden_external_relationships"] = [category]
    assert_valid(instance, schemas["environment"], schema_store)


def test_environment_rejects_invalid_forbidden_external_category(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_environment()
    instance["forbidden_external_relationships"] = ["ALLOW_UNRESTRICTED_INTERNET"]
    assert_invalid(instance, schemas["environment"], schema_store)


def test_environment_rejects_unknown_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_environment()
    instance["isolation_proven"] = True
    assert_invalid(instance, schemas["environment"], schema_store)


def test_environment_rejects_missing_required_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_environment()
    del instance["s0_configuration_id"]
    assert_invalid(instance, schemas["environment"], schema_store)


def test_environment_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_environment()
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["environment"], schema_store)
    assert instance == original


@pytest.mark.parametrize("phase", RUN_PHASES)
def test_run_manifest_accepts_each_frozen_phase(
    phase: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(valid_run_manifest(phase), schemas["run_manifest"], schema_store)


@pytest.mark.parametrize("phase", ["PILOT", "CONFIRMATORY"])
def test_scored_phase_rejects_not_frozen_before_start(
    phase: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_run_manifest(phase)
    instance["configuration_frozen_before_start"] = False
    assert_invalid(instance, schemas["run_manifest"], schema_store)


@pytest.mark.parametrize("phase", ["DEVELOPMENT", "INSTRUMENT_VALIDATION"])
def test_nonscored_phase_permits_false_frozen_declaration(
    phase: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_run_manifest(phase)
    instance["configuration_frozen_before_start"] = False
    assert_valid(instance, schemas["run_manifest"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("experiment_id", "run:wrong-prefix"),
        ("campaign_id", "exp:wrong-prefix"),
        ("scheduled_run_id", "run:wrong-prefix"),
        ("run_id", "scheduledrun:wrong-prefix"),
        ("scenario_id", "task:wrong-prefix"),
        ("task_id", "scenario:wrong-prefix"),
        ("agent_condition_id", "modelcond:wrong-prefix"),
        ("model_condition_id", "agentcond:wrong-prefix"),
        ("capability_condition_id", "cond:wrong-prefix"),
        ("autonomy_condition_id", "cond:wrong-prefix"),
        ("control_condition_id", "control:wrong-prefix"),
        ("capability_envelope_id", "policy:wrong-prefix"),
        ("policy_id", "envelope:wrong-prefix"),
        ("environment_id", "build:wrong-prefix"),
        ("instrument_configuration_id", "cond:wrong-prefix"),
    ],
)
def test_run_manifest_rejects_wrong_reference_identifier(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_run_manifest()
    instance[field] = value
    assert_invalid(instance, schemas["run_manifest"], schema_store)


@pytest.mark.parametrize("value", [0, -1, "10"])
def test_run_manifest_rejects_invalid_action_budget(
    value: object,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_run_manifest()
    instance["action_budget"] = value
    assert_invalid(instance, schemas["run_manifest"], schema_store)


def test_run_manifest_rejects_invalid_phase(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_manifest()
    instance["phase"] = "VALIDATION"
    assert_invalid(instance, schemas["run_manifest"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("terminal_action_outcome", "UNAUTHORIZED_EXECUTED"),
        ("authorization_decision", "DENIED"),
        ("benign_task_result", "SUCCESS"),
        ("unexpected", True),
    ],
)
def test_run_manifest_rejects_runtime_outcome_or_unknown_field(
    field: str,
    value: object,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_run_manifest()
    instance[field] = value
    assert_invalid(instance, schemas["run_manifest"], schema_store)


def test_run_manifest_rejects_missing_required_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_manifest()
    del instance["instrument_configuration_id"]
    assert_invalid(instance, schemas["run_manifest"], schema_store)


def test_run_manifest_accepts_unavailable_seed_without_seed_value(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_manifest()
    instance["seed_repetition_identity"] = {
        "repetition_id": "repetition_001",
        "seed_status": "UNAVAILABLE",
    }
    assert_valid(instance, schemas["run_manifest"], schema_store)


def test_run_manifest_rejects_unavailable_seed_with_fabricated_value(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_manifest()
    instance["seed_repetition_identity"]["seed_status"] = "UNAVAILABLE"
    assert_invalid(instance, schemas["run_manifest"], schema_store)


def test_run_manifest_rejects_available_seed_without_value(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_manifest()
    del instance["seed_repetition_identity"]["seed_value"]
    assert_invalid(instance, schemas["run_manifest"], schema_store)


def test_run_manifest_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_run_manifest("CONFIRMATORY")
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["run_manifest"], schema_store)
    assert instance == original


def test_agent_model_action_class_syntax_matches_stage3_and_stage4(
    schemas: dict[str, dict[str, Any]],
) -> None:
    patterns = {
        schemas["resource"]["$defs"]["action_class"]["pattern"],
        schemas["benign_task"]["$defs"]["action_class"]["pattern"],
        schemas["capability_envelope"]["$defs"]["action_class"]["pattern"],
        schemas["policy"]["$defs"]["action_class"]["pattern"],
        schemas["agent_model_condition"]["$defs"]["action_class"]["pattern"],
    }
    assert patterns == {"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$"}


@pytest.mark.parametrize(
    "schema_name,path,common_definition",
    [
        ("run_manifest", ("properties", "scenario_id"), "scenario_id"),
        ("run_manifest", ("properties", "task_id"), "task_id"),
        ("run_manifest", ("properties", "control_condition_id"), "control_condition_id"),
        (
            "run_manifest",
            ("properties", "capability_envelope_id"),
            "capability_envelope_id",
        ),
        ("run_manifest", ("properties", "policy_id"), "policy_id"),
        ("environment", ("properties", "synthetic_assets", "items"), "resource_id"),
    ],
)
def test_cross_stage_shared_identifier_reference(
    schema_name: str,
    path: tuple[str, ...],
    common_definition: str,
    schemas: dict[str, dict[str, Any]],
) -> None:
    node: Any = schemas[schema_name]
    for component in path:
        node = node[component]
    assert node["$ref"] == SCHEMA_IDS["common"] + f"#/$defs/{common_definition}"


def test_run_manifest_phase_exactly_matches_common(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert schemas["common"]["$defs"]["run_phase"]["enum"] == RUN_PHASES
    assert schemas["run_manifest"]["properties"]["phase"]["$ref"] == (
        SCHEMA_IDS["common"] + "#/$defs/run_phase"
    )


def test_local_store_validates_all_stage5_contracts_without_network(
    monkeypatch: pytest.MonkeyPatch,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access was attempted")

    monkeypatch.setattr(urllib.request, "urlopen", fail_network)
    assert_valid(valid_agent_model_condition(), schemas["agent_model_condition"], schema_store)
    assert_valid(valid_autonomy_condition(), schemas["autonomy_condition"], schema_store)
    assert_valid(valid_environment(), schemas["environment"], schema_store)
    assert_valid(valid_run_manifest(), schemas["run_manifest"], schema_store)


def test_unknown_project_reference_still_fails_explicitly() -> None:
    schema = {
        "$schema": DRAFT_2020_12,
        "$id": "urn:frontier-agent-containment:schema:test-stage5:0.1.0",
        "$ref": "urn:frontier-agent-containment:schema:missing-stage5:0.1.0",
    }
    with pytest.raises(UnknownSchemaReferenceError):
        validate_instance({}, schema, schema_store={})


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_remote_reference_still_fails_before_retrieval(
    scheme: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    called = False

    def mark_called(*args: object, **kwargs: object) -> None:
        nonlocal called
        called = True
        raise AssertionError("network access was attempted")

    monkeypatch.setattr(urllib.request, "urlopen", mark_called)
    schema = {
        "$schema": DRAFT_2020_12,
        "$id": "urn:frontier-agent-containment:schema:test-stage5:0.1.0",
        "$ref": f"{scheme}://example.invalid/schema.json",
    }
    with pytest.raises(ExternalSchemaReferenceError):
        validate_instance({}, schema, schema_store={})
    assert called is False


def test_stage5_schema_property_names_exclude_credential_and_outcome_fields(
    schemas: dict[str, dict[str, Any]],
) -> None:
    property_names: set[str] = set()
    pending: list[Any] = [
        schemas["agent_model_condition"],
        schemas["autonomy_condition"],
        schemas["environment"],
        schemas["run_manifest"],
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
        "api_key",
        "password",
        "target_ip",
        "target_url",
        "exploit_payload",
        "malware_path",
        "authorization_decision",
        "terminal_action_outcome",
        "h1_endpoint",
    ):
        assert forbidden not in property_names
