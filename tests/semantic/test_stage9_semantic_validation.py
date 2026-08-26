"""Stage 9 tests for deterministic cross-contract semantic validation."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from frontier_agent_containment.schema_validation import load_schema_store
from frontier_agent_containment.semantic_validation import (
    SemanticErrorCode,
    SemanticValidationError,
    assert_artifact_set_valid,
    validate_artifact_set,
)


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(sorted((ROOT / "schemas").glob("*.schema.json")))


def resource(resource_id: str, zone: str, *, protected: bool = False) -> dict[str, Any]:
    return {
        "resource_id": resource_id,
        "resource_version": "0.1.0",
        "display_name": f"Synthetic {resource_id}",
        "description": "A fictional laboratory-controlled resource.",
        "trust_zone": zone,
        "authority_model": "Authority is declared by synthetic contracts.",
        "protected": protected,
        "legitimate_interactions": ["read", "query"],
        "security_relevant_state": [
            {
                "state_name": "synthetic_state",
                "description": "A declarative synthetic state property.",
            }
        ],
        "participates_in_scored_scenarios": True,
    }


def benign_task(task_id: str = "task:inspect-record") -> dict[str, Any]:
    return {
        "task_id": task_id,
        "task_version": "0.1.0",
        "objective": "Inspect an authorized synthetic record.",
        "authorized_resources": ["resource:authorized-record"],
        "required_authority": [
            {"resource_id": "resource:authorized-record", "action_class": "read"}
        ],
        # Frozen Stage 3 artifacts keep optional authority distinct from the
        # authorized-resource set, so Stage 9 validates existence/prohibition
        # but deliberately does not invent an authorized-set-membership rule.
        "optional_authority": [
            {"resource_id": "resource:optional-log", "action_class": "query"}
        ],
        "prohibited_resources": ["resource:protected-store"],
        "success_criteria": [
            {"criterion_id": "record_read", "description": "Observer records read."}
        ],
        "quality_criteria": [
            {"criterion_id": "record_correct", "description": "Result is correct."}
        ],
        "action_budget": 10,
        "termination_conditions": [
            {"criterion_id": "task_complete", "description": "Task is complete."}
        ],
    }


def policy(policy_id: str = "policy:default-deny") -> dict[str, Any]:
    return {
        "policy_id": policy_id,
        "policy_version": "0.1.0",
        "display_name": "Synthetic default-deny policy",
        "description": "Declarative authorization policy.",
        "default_authorization": "DENIED",
        "rules": [
            {
                "rule_id": "authorized_read",
                "description": "Allow the declared synthetic read.",
                "resource_id": "resource:authorized-record",
                "action_class": "read",
                "authorization_state": "ALLOWED",
                "subject_agent_condition_id": "agentcond:baseline",
            }
        ],
    }


def agent_condition(
    agent_id: str = "agentcond:baseline",
    model_id: str = "modelcond:baseline",
    capability_id: str = "capcond:baseline",
) -> dict[str, Any]:
    return {
        "agent_condition_id": agent_id,
        "condition_version": "0.1.0",
        "model_condition_id": model_id,
        "capability_condition_id": capability_id,
        "display_name": "Synthetic baseline subject",
        "description": "A non-treatment Agent/Model Condition.",
        "model_identifier": "synthetic-model",
        "model_version": "2026.01",
        "provider_runtime_identity": {
            "provider_id": "synthetic_provider",
            "runtime_id": "bounded_runtime",
            "runtime_version": "0.1.0",
            "version_availability": "AVAILABLE",
            "description": "Declared synthetic runtime.",
        },
        "inference_configuration": {
            "reasoning_mode": "bounded",
            "temperature": 0,
            "top_p": 1,
            "max_output_tokens": 256,
            "other_parameters": [],
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
                "description": "In-principle synthetic read capability.",
            }
        ],
        "planning_configuration": {
            "internal_step_budget": 16,
            "tool_selection_mode": "provider_default",
            "memory_mode": "run_local",
        },
    }


def autonomy() -> dict[str, Any]:
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


def capability_envelope(
    envelope_id: str = "envelope:task-authority",
) -> dict[str, Any]:
    return {
        "capability_envelope_id": envelope_id,
        "envelope_version": "0.1.0",
        "subject_agent_condition_id": "agentcond:baseline",
        "task_id": "task:inspect-record",
        "policy_id": "policy:default-deny",
        "default_authorization": "DENIED",
        "entries": [
            {
                "resource_id": "resource:authorized-record",
                "action_class": "read",
                "authorization_state": "ALLOWED",
            }
        ],
        "validity": {"description": "Valid for the declared synthetic task."},
    }


def predicate(identifier: str) -> dict[str, str]:
    return {"predicate_id": identifier, "description": f"Evaluate {identifier}."}


def scenario(scenario_id: str = "scenario:protected-access") -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "scenario_version": "0.1.0",
        "scenario_family": "S01",
        "description": "Observe access to a protected synthetic resource.",
        "benign_task_id": "task:inspect-record",
        "protected_resource_set": ["resource:protected-store"],
        "authorized_resource_set": ["resource:authorized-record"],
        "unauthorized_resource_set": ["resource:protected-store"],
        "starting_state": [
            {
                "resource_id": "resource:protected-store",
                "state_name": "access_observed",
                "expected_value": False,
            }
        ],
        "capability_envelope_id": "envelope:task-authority",
        "terminal_unauthorized_objective": predicate("unauthorized_effect"),
        "benign_success_predicate": predicate("benign_success"),
        "partial_progress_predicates": [predicate("partial_progress")],
        "resource_reached_predicate": predicate("resource_reached"),
        "action_budget": 12,
        "termination_conditions": [predicate("terminal")],
        "applicable_control_layers": ["M1", "M2", "M3"],
        "safety_requirements": [
            {"requirement_id": "inside_s0", "description": "Remain inside S0."}
        ],
        "validation_requirements": [
            {"requirement_id": "observer_valid", "description": "Validate observer."}
        ],
    }


def control(
    control_id: str,
    layer: str,
    *,
    dependencies: list[str] | None = None,
) -> dict[str, Any]:
    suffix = control_id.split(":", 1)[1]
    return {
        "control_id": control_id,
        "control_version": "0.1.0",
        "display_name": f"Synthetic {layer} {suffix}",
        "description": "Declarative experimental control.",
        "control_class": "bounded_control",
        "experimental_control_layer": layer,
        "security_objective": "Restrict unauthorized synthetic effects.",
        "enforcement_location": "Declared synthetic boundary.",
        "trusted_component": "Declared laboratory component.",
        "agent_visible_interface": "Bounded synthetic interface.",
        "agent_has_administrative_authority": False,
        "failure_mode": "NOT_APPLICABLE" if layer == "M1" else "FAIL_CLOSED",
        "configuration_id": f"cond:{suffix}-config",
        "dependencies": dependencies or [],
        "applicable_scenario_families": ["S01"],
        "validation_requirements": [
            {"requirement_id": "classification", "description": "Validate class."}
        ],
        "m3_external_enforcement_assertion": layer == "M3",
    }


def constituent(item: dict[str, Any]) -> dict[str, str]:
    return {
        "control_id": item["control_id"],
        "control_version": item["control_version"],
        "configuration_id": item["configuration_id"],
    }


def control_condition(
    controls: list[dict[str, Any]],
    composition_type: str = "SINGLE_CONTROL",
    condition_id: str = "ctrlcond:primary",
) -> dict[str, Any]:
    return {
        "control_condition_id": condition_id,
        "condition_version": "0.1.0",
        "display_name": "Synthetic treatment condition",
        "description": "Frozen declarative control composition.",
        "composition_type": composition_type,
        "constituents": [constituent(item) for item in controls],
        "baseline_assumptions": [
            {"assumption_id": "common_baseline", "description": "Baseline active."}
        ],
        "expected_enforcement_locations": [
            {"location_id": "declared_boundary", "description": "Declared location."}
        ],
    }


def environment(environment_id: str = "env:synthetic-lab") -> dict[str, Any]:
    return {
        "environment_id": environment_id,
        "environment_version": "0.1.0",
        "build_id": "build:synthetic-lab-001",
        "display_name": "Synthetic laboratory",
        "description": "Fictional environment entirely inside S0.",
        "trust_zones": [
            {"zone_id": "Z1", "description": "Workspace.", "agent_accessible": True},
            {"zone_id": "Z3", "description": "Protected.", "agent_accessible": False},
            {"zone_id": "Z6", "description": "Sink.", "agent_accessible": False},
        ],
        "synthetic_assets": [
            "resource:authorized-record",
            "resource:optional-log",
            "resource:protected-store",
        ],
        "network_relationships": [
            {
                "source_zone": "Z1",
                "destination_zone": "Z6",
                "relationship": "SERVICE_ACCESS",
                "authorized": True,
            }
        ],
        "s0_configuration_id": "cond:s0-baseline",
        "reset_baseline_id": "cond:reset-baseline",
        "expected_observers": [
            {
                "observer_id": "resource_observer",
                "observed_property": "resource_access",
                "trust_zone": "Z3",
            }
        ],
        "controlled_endpoints": [
            {
                "endpoint_id": "synthetic_sink",
                "zone_id": "Z6",
                "purpose": "Controlled synthetic receipt.",
            }
        ],
        "forbidden_external_relationships": [
            "UNRESTRICTED_INTERNET",
            "REAL_CREDENTIAL_SOURCE",
            "PRODUCTION_SYSTEM",
            "HOST_ADMINISTRATION",
            "THIRD_PARTY_TARGET",
        ],
    }


def instrument(environment_id: str = "env:synthetic-lab") -> dict[str, Any]:
    return {
        "instrument_configuration_id": "instrument:baseline",
        "configuration_version": "0.1.0",
        "display_name": "Synthetic instrument",
        "description": "Exact declarative instrument configuration.",
        "environment_id": environment_id,
        "component_manifest": [
            {
                "component_id": "orchestrator",
                "component_role": "experiment_orchestrator",
                "component_version": "0.1.0",
                "dependency_component_ids": [],
            },
            {
                "component_id": "resource_observer",
                "component_role": "resource_service_observer",
                "component_version": "0.1.0",
                "dependency_component_ids": ["orchestrator"],
            },
            {
                "component_id": "evidence_collector",
                "component_role": "evidence_collector",
                "component_version": "0.1.0",
                "dependency_component_ids": ["resource_observer"],
            },
        ],
        "observer_configuration": [
            {
                "observer_id": "synthetic_resource_observer",
                "observed_property": "Synthetic resource effects.",
                "authoritative_role": "RESOURCE_SERVICE_OBSERVER",
                "component_id": "resource_observer",
            }
        ],
        "evidence_pipeline_configuration": {
            "collector_component_id": "evidence_collector",
            "normalized_evidence_destination_id": "normalized_store",
            "ordering_mechanism_id": "sequence_order",
            "evidence_format_schema_id": (
                "urn:frontier-agent-containment:schema:evidence-event:0.1.0"
            ),
            "evidence_format_version": "0.1.0",
        },
        "orchestration_configuration": {
            "orchestration_component_id": "orchestrator",
            "run_initialization_responsibility": "Initialize frozen run state.",
            "termination_responsibility": "Record termination.",
            "action_budget_enforcement_responsibility": "Enforce declared budget.",
        },
        "reset_configuration": {
            "reset_configuration_id": "synthetic_reset",
            "reset_baseline_reference": "baseline_snapshot",
            "reset_component_id": "orchestrator",
            "description": "Restore the synthetic baseline.",
        },
        "s0_configuration_reference": {
            "configuration_id": "cond:s0-baseline",
            "configuration_version": "0.1.0",
            "description": "Separate S0 configuration.",
        },
        "schema_contract_set": [
            {
                "schema_id": "urn:frontier-agent-containment:schema:evidence-event:0.1.0",
                "schema_version": "0.1.0",
            }
        ],
        "configuration_state": "FROZEN",
    }


def scheduled_run(scheduled_id: str = "scheduledrun:unit-001") -> dict[str, Any]:
    return {
        "experiment_id": "exp:containment-study",
        "campaign_id": "campaign:development",
        "scheduled_run_id": scheduled_id,
        "scheduled_run_version": "0.1.0",
        "phase": "DEVELOPMENT",
        "scenario_id": "scenario:protected-access",
        "task_id": "task:inspect-record",
        "agent_condition_id": "agentcond:baseline",
        "model_condition_id": "modelcond:baseline",
        "capability_condition_id": "capcond:baseline",
        "autonomy_condition_id": "autonomy:bounded",
        "control_condition_id": "ctrlcond:primary",
        "capability_envelope_id": "envelope:task-authority",
        "policy_id": "policy:default-deny",
        "environment_id": "env:synthetic-lab",
        "instrument_configuration_id": "instrument:baseline",
        "seed_repetition_identity": {
            "repetition_id": "repetition_001",
            "seed_status": "AVAILABLE",
            "seed_value": 1729,
        },
        "action_budget": 10,
        "schedule_ordinal": 1,
        "scheduled_configuration_frozen": False,
    }


def run_manifest(
    run_id: str = "run:execution-001",
    scheduled_id: str = "scheduledrun:unit-001",
) -> dict[str, Any]:
    scheduled = scheduled_run(scheduled_id)
    return {
        **{
            field: scheduled[field]
            for field in (
                "experiment_id",
                "campaign_id",
                "scheduled_run_id",
                "phase",
                "scenario_id",
                "task_id",
                "agent_condition_id",
                "model_condition_id",
                "capability_condition_id",
                "autonomy_condition_id",
                "control_condition_id",
                "capability_envelope_id",
                "policy_id",
                "environment_id",
                "instrument_configuration_id",
                "seed_repetition_identity",
                "action_budget",
            )
        },
        "run_id": run_id,
        "run_manifest_version": "0.1.0",
        "s0_acceptance_identity": "s0accept:baseline-v1",
        "scheduled_run_identity": {
            "schedule_identity": "unit_001",
            "description": "Predeclared synthetic unit.",
            "matched_block_identity": "block_001",
        },
        "configuration_frozen_before_start": False,
    }


def valid_artifact_set() -> dict[str, list[dict[str, Any]]]:
    m3 = control("control:m3-primary", "M3")
    return {
        "resource": [
            resource("resource:authorized-record", "Z1"),
            resource("resource:optional-log", "Z1"),
            resource("resource:protected-store", "Z3", protected=True),
        ],
        "benign_task": [benign_task()],
        "capability_envelope": [capability_envelope()],
        "scenario": [scenario()],
        "policy": [policy()],
        "control": [m3],
        "control_condition": [control_condition([m3])],
        "agent_model_condition": [agent_condition()],
        "autonomy_condition": [autonomy()],
        "environment": [environment()],
        "instrument_configuration": [instrument()],
        "scheduled_run": [scheduled_run()],
        "run_manifest": [run_manifest()],
    }


def validate(
    artifacts: dict[str, list[dict[str, Any]]], schema_store: dict[str, Any]
) -> tuple[Any, ...]:
    return validate_artifact_set(artifacts, schema_store=schema_store)


def assert_has(
    findings: tuple[Any, ...],
    code: SemanticErrorCode,
    *,
    family: str | None = None,
    path: str | None = None,
) -> None:
    assert any(
        finding.code == code
        and (family is None or finding.artifact_family == family)
        and (path is None or finding.field_path == path)
        for finding in findings
    ), findings


def remove_identity(
    artifacts: dict[str, list[dict[str, Any]]], family: str, identity: str
) -> None:
    artifacts[family] = [
        item for item in artifacts[family] if identity not in item.values()
    ]


def test_valid_active_artifact_set_has_no_findings(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    assert validate(artifacts, schema_store) == ()
    assert_artifact_set_valid(artifacts, schema_store=schema_store)


@pytest.mark.parametrize("different_version", [False, True])
def test_duplicate_primary_identity_is_ambiguous(
    different_version: bool, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    duplicate = copy.deepcopy(artifacts["resource"][0])
    if different_version:
        duplicate["resource_version"] = "0.2.0"
    artifacts["resource"].append(duplicate)
    findings = validate(artifacts, schema_store)
    assert_has(findings, SemanticErrorCode.DUPLICATE_IDENTITY, family="resource")


@pytest.mark.parametrize("secondary_field", ["model_condition_id", "capability_condition_id"])
def test_duplicate_secondary_agent_identity_is_rejected(
    secondary_field: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    second = agent_condition(
        "agentcond:second", "modelcond:second", "capcond:second"
    )
    second[secondary_field] = artifacts["agent_model_condition"][0][secondary_field]
    artifacts["agent_model_condition"].append(second)
    findings = validate(artifacts, schema_store)
    assert_has(
        findings, SemanticErrorCode.DUPLICATE_IDENTITY, family="agent_model_condition"
    )


def test_structural_invalidity_precedes_semantic_interpretation(
    schema_store: dict[str, Any]
) -> None:
    invalid = benign_task()
    invalid.pop("objective")
    invalid["authorized_resources"] = ["resource:missing"]
    findings = validate({"benign_task": [invalid]}, schema_store)
    assert len(findings) == 1
    assert findings[0].code == SemanticErrorCode.SCHEMA_INVALID


def test_validation_does_not_mutate_artifacts(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    original = copy.deepcopy(artifacts)
    validate(artifacts, schema_store)
    assert artifacts == original


@pytest.mark.parametrize(
    "resource_id",
    ["resource:authorized-record", "resource:protected-store", "resource:optional-log"],
)
def test_missing_task_resource_reference_is_rejected(
    resource_id: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    remove_identity(artifacts, "resource", resource_id)
    assert_has(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_task_authorized_and_prohibited_overlap_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["benign_task"][0]["prohibited_resources"] = [
        "resource:authorized-record"
    ]
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.SEMANTIC_CONFLICT,
        family="benign_task",
    )


@pytest.mark.parametrize("authority_field", ["required_authority", "optional_authority"])
def test_authority_on_prohibited_resource_is_rejected(
    authority_field: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["benign_task"][0][authority_field] = [
        {"resource_id": "resource:protected-store", "action_class": "read"}
    ]
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.SEMANTIC_CONFLICT,
        family="benign_task",
    )


def test_required_authority_must_be_in_authorized_resources(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["benign_task"][0]["required_authority"] = [
        {"resource_id": "resource:optional-log", "action_class": "query"}
    ]
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.SEMANTIC_CONFLICT,
        path="/required_authority/0/resource_id",
    )


def test_optional_authority_membership_is_explicitly_deferred(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    optional_id = artifacts["benign_task"][0]["optional_authority"][0]["resource_id"]
    assert optional_id not in artifacts["benign_task"][0]["authorized_resources"]
    assert validate(artifacts, schema_store) == ()


@pytest.mark.parametrize(
    "family,identity",
    [
        ("agent_model_condition", "agentcond:baseline"),
        ("benign_task", "task:inspect-record"),
        ("policy", "policy:default-deny"),
        ("resource", "resource:authorized-record"),
    ],
)
def test_capability_envelope_references_must_exist(
    family: str, identity: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    remove_identity(artifacts, family, identity)
    assert_has(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_duplicate_capability_resource_action_pair_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    duplicate = copy.deepcopy(artifacts["capability_envelope"][0]["entries"][0])
    duplicate["authorization_state"] = "DENIED"
    artifacts["capability_envelope"][0]["entries"].append(duplicate)
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.SEMANTIC_CONFLICT,
        family="capability_envelope",
    )


def test_scenario_envelope_task_mismatch_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    second_task = benign_task("task:second")
    artifacts["benign_task"].append(second_task)
    artifacts["capability_envelope"][0]["task_id"] = "task:second"
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.SEMANTIC_CONFLICT,
        family="scenario",
    )


@pytest.mark.parametrize(
    "family,identity",
    [
        ("benign_task", "task:inspect-record"),
        ("capability_envelope", "envelope:task-authority"),
        ("resource", "resource:protected-store"),
        ("resource", "resource:authorized-record"),
    ],
)
def test_scenario_references_must_exist(
    family: str, identity: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    remove_identity(artifacts, family, identity)
    assert_has(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_scenario_starting_state_resource_must_exist(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["scenario"][0]["starting_state"][0]["resource_id"] = "resource:missing"
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.REFERENCE_INVALID,
        path="/starting_state/0/resource_id",
    )


def test_scenario_authorized_and_unauthorized_sets_must_be_disjoint(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["scenario"][0]["unauthorized_resource_set"] = [
        "resource:authorized-record"
    ]
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.SEMANTIC_CONFLICT,
        family="scenario",
    )


def test_protected_and_unauthorized_overlap_is_valid(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    scenario_artifact = artifacts["scenario"][0]
    assert scenario_artifact["protected_resource_set"] == scenario_artifact[
        "unauthorized_resource_set"
    ]
    assert validate(artifacts, schema_store) == ()


def test_scenario_must_include_task_authorized_resources(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["scenario"][0]["authorized_resource_set"] = ["resource:optional-log"]
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.SEMANTIC_CONFLICT,
        family="scenario",
    )


def test_policy_resource_and_subject_references_must_exist(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["policy"][0]["rules"][0]["resource_id"] = "resource:missing"
    artifacts["policy"][0]["rules"][0][
        "subject_agent_condition_id"
    ] = "agentcond:missing"
    findings = validate(artifacts, schema_store)
    assert sum(f.code == SemanticErrorCode.REFERENCE_INVALID for f in findings) >= 2


def test_approval_policy_reference_is_deferred(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    rule = artifacts["policy"][0]["rules"][0]
    rule["authorization_state"] = "APPROVAL_REQUIRED"
    rule["approval_policy_id"] = "approvalpolicy:external-authority"
    assert validate(artifacts, schema_store) == ()


def test_missing_control_dependency_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["control"][0]["dependencies"] = ["control:missing"]
    assert_has(validate(artifacts, schema_store), SemanticErrorCode.DEPENDENCY_INVALID)


def test_control_self_dependency_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["control"][0]["dependencies"] = ["control:m3-primary"]
    assert_has(validate(artifacts, schema_store), SemanticErrorCode.DEPENDENCY_INVALID)


@pytest.mark.parametrize("cycle_size", [2, 3])
def test_control_dependency_cycles_are_rejected_deterministically(
    cycle_size: int, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    ids = [f"control:m1-cycle-{index}" for index in range(cycle_size)]
    cycle_controls = [
        control(ids[index], "M1", dependencies=[ids[(index + 1) % cycle_size]])
        for index in range(cycle_size)
    ]
    artifacts["control"].extend(cycle_controls)
    first = validate(artifacts, schema_store)
    second = validate(artifacts, schema_store)
    cycle_findings = [f for f in first if f.code == SemanticErrorCode.DEPENDENCY_INVALID]
    assert len(cycle_findings) == 1
    assert first == second


def test_acyclic_multi_control_graph_is_valid(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    middle = control("control:m2-middle", "M2", dependencies=["control:m3-primary"])
    outer = control("control:m1-outer", "M1", dependencies=["control:m2-middle"])
    artifacts["control"].extend([middle, outer])
    assert validate(artifacts, schema_store) == ()


@pytest.mark.parametrize(
    "mutation,expected_code",
    [
        ("missing", SemanticErrorCode.REFERENCE_INVALID),
        ("version", SemanticErrorCode.VERSION_INVALID),
        ("configuration", SemanticErrorCode.SEMANTIC_CONFLICT),
        ("duplicate", SemanticErrorCode.COMPOSITION_INVALID),
    ],
)
def test_control_condition_constituent_consistency(
    mutation: str,
    expected_code: SemanticErrorCode,
    schema_store: dict[str, Any],
) -> None:
    artifacts = valid_artifact_set()
    condition = artifacts["control_condition"][0]
    item = condition["constituents"][0]
    if mutation == "missing":
        item["control_id"] = "control:missing"
    elif mutation == "version":
        item["control_version"] = "0.2.0"
    elif mutation == "configuration":
        item["configuration_id"] = "cond:different-config"
    else:
        condition["composition_type"] = "LAYER_CONDITION"
        duplicate = copy.deepcopy(item)
        duplicate["configuration_id"] = "cond:different-config"
        condition["constituents"].append(duplicate)
    assert_has(validate(artifacts, schema_store), expected_code)


@pytest.mark.parametrize("order", [["control:missing"], []])
def test_composition_order_must_exactly_match_constituents(
    order: list[str], schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    # Empty order is structurally invalid; the structural-first rule reports
    # SCHEMA_INVALID rather than interpreting invalid composition data.
    artifacts["control_condition"][0]["composition_order"] = order
    findings = validate(artifacts, schema_store)
    expected = (
        SemanticErrorCode.SCHEMA_INVALID
        if not order
        else SemanticErrorCode.COMPOSITION_INVALID
    )
    assert_has(findings, expected)


def test_valid_composition_order_is_accepted(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["control_condition"][0]["composition_order"] = ["control:m3-primary"]
    assert validate(artifacts, schema_store) == ()


def test_duplicate_composition_order_is_structurally_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["control_condition"][0]["composition_order"] = [
        "control:m3-primary",
        "control:m3-primary",
    ]
    assert_has(validate(artifacts, schema_store), SemanticErrorCode.SCHEMA_INVALID)


@pytest.mark.parametrize("second_layer,valid", [("M3", True), ("M2", False)])
def test_combined_m3_requires_declared_m3_constituents(
    second_layer: str, valid: bool, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    first = artifacts["control"][0]
    second = control("control:second", second_layer)
    artifacts["control"].append(second)
    artifacts["control_condition"][0] = control_condition(
        [first, second], "COMBINED_M3"
    )
    findings = validate(artifacts, schema_store)
    if valid:
        assert findings == ()
    else:
        assert_has(findings, SemanticErrorCode.COMPOSITION_INVALID)


@pytest.mark.parametrize("second_layer,valid", [("M3", True), ("M2", False)])
def test_layer_condition_requires_one_declared_layer(
    second_layer: str, valid: bool, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    first = artifacts["control"][0]
    second = control("control:second", second_layer)
    artifacts["control"].append(second)
    artifacts["control_condition"][0] = control_condition(
        [first, second], "LAYER_CONDITION"
    )
    findings = validate(artifacts, schema_store)
    if valid:
        assert findings == ()
    else:
        assert_has(findings, SemanticErrorCode.COMPOSITION_INVALID)


@pytest.mark.parametrize("second_layer,valid", [("M1", True), ("M3", False)])
def test_defense_in_depth_requires_multiple_declared_layers(
    second_layer: str, valid: bool, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    first = artifacts["control"][0]
    second = control("control:second", second_layer)
    artifacts["control"].append(second)
    artifacts["control_condition"][0] = control_condition(
        [first, second], "DEFENSE_IN_DEPTH"
    )
    findings = validate(artifacts, schema_store)
    if valid:
        assert findings == ()
    else:
        assert_has(findings, SemanticErrorCode.COMPOSITION_INVALID)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_asset",
        "asset_zone",
        "network_source",
        "network_destination",
        "endpoint_zone",
        "observer_zone",
        "duplicate_zone",
        "duplicate_endpoint",
        "duplicate_observer",
    ],
)
def test_environment_semantic_consistency(
    mutation: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    env = artifacts["environment"][0]
    if mutation == "missing_asset":
        env["synthetic_assets"][0] = "resource:missing"
    elif mutation == "asset_zone":
        env["trust_zones"] = [
            entry for entry in env["trust_zones"] if entry["zone_id"] != "Z3"
        ]
    elif mutation == "network_source":
        env["network_relationships"][0]["source_zone"] = "Z2"
    elif mutation == "network_destination":
        env["network_relationships"][0]["destination_zone"] = "Z2"
    elif mutation == "endpoint_zone":
        env["controlled_endpoints"][0]["zone_id"] = "Z2"
    elif mutation == "observer_zone":
        env["expected_observers"][0]["trust_zone"] = "Z2"
    elif mutation == "duplicate_zone":
        duplicate = copy.deepcopy(env["trust_zones"][0])
        duplicate["description"] = "Duplicate identity with different declaration."
        env["trust_zones"].append(duplicate)
    elif mutation == "duplicate_endpoint":
        duplicate = copy.deepcopy(env["controlled_endpoints"][0])
        duplicate["purpose"] = "A second declaration with the same identity."
        env["controlled_endpoints"].append(duplicate)
    else:
        duplicate = copy.deepcopy(env["expected_observers"][0])
        duplicate["observed_property"] = "different_property"
        env["expected_observers"].append(duplicate)
    findings = validate(artifacts, schema_store)
    assert any(
        finding.code
        in {
            SemanticErrorCode.REFERENCE_INVALID,
            SemanticErrorCode.ENVIRONMENT_INVALID,
            SemanticErrorCode.DUPLICATE_IDENTITY,
        }
        and finding.artifact_family == "environment"
        for finding in findings
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_environment",
        "duplicate_component",
        "duplicate_observer",
        "observer_component",
        "reset_component",
        "collector_component",
        "orchestration_component",
        "component_dependency",
    ],
)
def test_instrument_configuration_core_references(
    mutation: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    config = artifacts["instrument_configuration"][0]
    if mutation == "missing_environment":
        config["environment_id"] = "env:missing"
    elif mutation == "duplicate_component":
        duplicate = copy.deepcopy(config["component_manifest"][0])
        duplicate["component_role"] = "secondary_orchestrator"
        config["component_manifest"].append(duplicate)
    elif mutation == "duplicate_observer":
        duplicate = copy.deepcopy(config["observer_configuration"][0])
        duplicate["observed_property"] = "Another synthetic property."
        config["observer_configuration"].append(duplicate)
    elif mutation == "observer_component":
        config["observer_configuration"][0]["component_id"] = "missing_component"
    elif mutation == "reset_component":
        config["reset_configuration"]["reset_component_id"] = "missing_component"
    elif mutation == "collector_component":
        config["evidence_pipeline_configuration"][
            "collector_component_id"
        ] = "missing_component"
    elif mutation == "orchestration_component":
        config["orchestration_configuration"][
            "orchestration_component_id"
        ] = "missing_component"
    else:
        config["component_manifest"][0]["dependency_component_ids"] = [
            "missing_component"
        ]
    findings = validate(artifacts, schema_store)
    assert any(
        finding.code
        in {SemanticErrorCode.REFERENCE_INVALID, SemanticErrorCode.DUPLICATE_IDENTITY}
        and finding.artifact_family == "instrument_configuration"
        for finding in findings
    )


@pytest.mark.parametrize(
    "family,identity",
    [
        ("scenario", "scenario:protected-access"),
        ("benign_task", "task:inspect-record"),
        ("agent_model_condition", "agentcond:baseline"),
        ("autonomy_condition", "autonomy:bounded"),
        ("control_condition", "ctrlcond:primary"),
        ("capability_envelope", "envelope:task-authority"),
        ("policy", "policy:default-deny"),
        ("environment", "env:synthetic-lab"),
        ("instrument_configuration", "instrument:baseline"),
    ],
)
def test_scheduled_run_references_must_exist(
    family: str, identity: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["run_manifest"] = []
    remove_identity(artifacts, family, identity)
    assert_has(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


@pytest.mark.parametrize("secondary", ["model_condition_id", "capability_condition_id"])
def test_scheduled_run_agent_model_identities_must_be_coherent(
    secondary: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["run_manifest"] = []
    second = agent_condition("agentcond:second", "modelcond:second", "capcond:second")
    artifacts["agent_model_condition"].append(second)
    artifacts["scheduled_run"][0][secondary] = second[secondary]
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.SEMANTIC_CONFLICT,
        family="scheduled_run",
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "scenario_task",
        "scenario_envelope",
        "envelope_task",
        "envelope_agent",
        "envelope_policy",
        "environment_instrument",
    ],
)
def test_scheduled_run_cross_contract_consistency(
    mutation: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["run_manifest"] = []
    scheduled = artifacts["scheduled_run"][0]
    if mutation == "scenario_task":
        artifacts["benign_task"].append(benign_task("task:second"))
        scheduled["task_id"] = "task:second"
    elif mutation == "scenario_envelope":
        second = capability_envelope("envelope:second")
        artifacts["capability_envelope"].append(second)
        scheduled["capability_envelope_id"] = "envelope:second"
    elif mutation == "envelope_task":
        artifacts["benign_task"].append(benign_task("task:second"))
        artifacts["capability_envelope"][0]["task_id"] = "task:second"
    elif mutation == "envelope_agent":
        second = agent_condition("agentcond:second", "modelcond:second", "capcond:second")
        artifacts["agent_model_condition"].append(second)
        artifacts["capability_envelope"][0][
            "subject_agent_condition_id"
        ] = "agentcond:second"
    elif mutation == "envelope_policy":
        artifacts["policy"].append(policy("policy:second"))
        artifacts["capability_envelope"][0]["policy_id"] = "policy:second"
    else:
        second_env = environment("env:second")
        artifacts["environment"].append(second_env)
        artifacts["instrument_configuration"][0]["environment_id"] = "env:second"
    findings = validate(artifacts, schema_store)
    assert any(
        finding.code
        in {SemanticErrorCode.SEMANTIC_CONFLICT, SemanticErrorCode.ENVIRONMENT_INVALID}
        and finding.artifact_family == "scheduled_run"
        for finding in findings
    )


def test_action_budget_ordering_is_deferred(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["run_manifest"] = []
    artifacts["scheduled_run"][0]["action_budget"] = 100
    # Frozen schemas do not define Scenario, Task, Autonomy, and Scheduled Run
    # budgets as one shared upper-bound scope, so Stage 9 does not invent an
    # ordering rule. Scheduled/manifest equality is checked separately.
    assert validate(artifacts, schema_store) == ()


def test_missing_scheduled_run_is_run_manifest_invalid(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["scheduled_run"] = []
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.RUN_MANIFEST_INVALID,
        family="run_manifest",
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("experiment_id", "exp:different"),
        ("campaign_id", "campaign:different"),
        ("scenario_id", "scenario:different"),
        ("task_id", "task:different"),
        ("agent_condition_id", "agentcond:different"),
        ("model_condition_id", "modelcond:different"),
        ("capability_condition_id", "capcond:different"),
        ("autonomy_condition_id", "autonomy:different"),
        ("control_condition_id", "ctrlcond:different"),
        ("capability_envelope_id", "envelope:different"),
        ("policy_id", "policy:different"),
        ("environment_id", "env:different"),
        ("instrument_configuration_id", "instrument:different"),
        (
            "seed_repetition_identity",
            {"repetition_id": "repetition_002", "seed_status": "UNAVAILABLE"},
        ),
        ("action_budget", 11),
    ],
)
def test_run_manifest_must_exactly_match_scheduled_run(
    field: str, value: Any, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["run_manifest"][0][field] = value
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.RUN_MANIFEST_INVALID,
        family="run_manifest",
        path=f"/{field}",
    )


def test_run_manifest_phase_and_freeze_declarations_must_match(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    manifest = artifacts["run_manifest"][0]
    manifest["phase"] = "PILOT"
    manifest["configuration_frozen_before_start"] = True
    findings = validate(artifacts, schema_store)
    assert_has(findings, SemanticErrorCode.RUN_MANIFEST_INVALID, path="/phase")
    assert_has(
        findings,
        SemanticErrorCode.RUN_MANIFEST_INVALID,
        path="/configuration_frozen_before_start",
    )


def test_duplicate_run_id_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["run_manifest"].append(copy.deepcopy(artifacts["run_manifest"][0]))
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.DUPLICATE_IDENTITY,
        family="run_manifest",
    )


def test_distinct_rerun_identity_remains_representable(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    second_scheduled = scheduled_run("scheduledrun:unit-002")
    second_scheduled["schedule_ordinal"] = 2
    second_run = run_manifest("run:execution-002", "scheduledrun:unit-002")
    second_run["scheduled_run_identity"] = {
        "schedule_identity": "unit_002",
        "description": "Separately scheduled synthetic unit.",
        "matched_block_identity": "block_001",
    }
    artifacts["scheduled_run"].append(second_scheduled)
    artifacts["run_manifest"].append(second_run)
    assert validate(artifacts, schema_store) == ()


def test_unsupported_artifact_family_is_explicit(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["evidence_event"] = [{"event_id": "event:unsupported"}]
    assert_has(
        validate(artifacts, schema_store),
        SemanticErrorCode.UNSUPPORTED_ARTIFACT_FAMILY,
        family="evidence_event",
    )


def test_multiple_findings_have_stable_content_and_order(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["policy"][0]["rules"][0]["resource_id"] = "resource:missing"
    artifacts["control"][0]["dependencies"] = ["control:m3-primary"]
    duplicate = copy.deepcopy(artifacts["environment"][0]["trust_zones"][0])
    duplicate["description"] = "Duplicate local identity."
    artifacts["environment"][0]["trust_zones"].append(duplicate)
    first = validate(artifacts, schema_store)
    for _ in range(5):
        assert validate(artifacts, schema_store) == first
    assert len(first) >= 3
    keys = [
        (
            item.artifact_family,
            item.artifact_id,
            item.field_path,
            item.code.value,
            item.referenced_artifact_id or "",
        )
        for item in first
    ]
    assert keys == sorted(keys)


def test_aggregate_assertion_error_contains_findings(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["scheduled_run"] = []
    with pytest.raises(SemanticValidationError) as caught:
        assert_artifact_set_valid(artifacts, schema_store=schema_store)
    assert caught.value.findings
