"""Stage 4 tests for declarative policy and control contracts."""

from __future__ import annotations

import copy
import json
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import ValidationError

from frontier_agent_containment.schema_validation import (
    DuplicateSchemaIdError,
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
}
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


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(SCHEMA_PATHS.values())


@pytest.fixture(scope="module")
def schemas(schema_store: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {name: schema_store[schema_id] for name, schema_id in SCHEMA_IDS.items()}


def policy_rule(state: str = "ALLOWED") -> dict[str, Any]:
    return {
        "rule_id": "authorized_read",
        "description": "Authorize a bounded interaction with a synthetic resource.",
        "resource_id": "resource:authorized-record",
        "action_class": "read",
        "authorization_state": state,
    }


def valid_policy() -> dict[str, Any]:
    return {
        "policy_id": "policy:default-deny",
        "policy_version": "0.1.0",
        "display_name": "Synthetic default-deny policy",
        "description": "Declarative policy for synthetic laboratory resources.",
        "default_authorization": "DENIED",
        "rules": [policy_rule()],
    }


def valid_control(layer: str = "M1") -> dict[str, Any]:
    return {
        "control_id": f"control:{layer.lower()}-bounded-control",
        "control_version": "0.1.0",
        "display_name": f"Synthetic {layer} control",
        "description": "A declarative experimental control definition.",
        "control_class": "bounded_control",
        "experimental_control_layer": layer,
        "security_objective": "Restrict unauthorized synthetic effects.",
        "enforcement_location": "Declared synthetic enforcement boundary.",
        "trusted_component": "Declared laboratory component.",
        "agent_visible_interface": "Bounded synthetic action interface.",
        "agent_has_administrative_authority": False,
        "failure_mode": "NOT_APPLICABLE" if layer == "M1" else "FAIL_CLOSED",
        "configuration_id": f"cond:{layer.lower()}-control-config",
        "dependencies": [],
        "applicable_scenario_families": ["S01"],
        "validation_requirements": [
            {
                "requirement_id": "classification_checked",
                "description": "Validate the declared architecture independently.",
            }
        ],
        "m3_external_enforcement_assertion": layer == "M3",
    }


def constituent(number: int = 1) -> dict[str, str]:
    return {
        "control_id": f"control:bounded-control-{number}",
        "control_version": "0.1.0",
        "configuration_id": f"cond:bounded-control-{number}-config",
    }


def valid_condition(composition_type: str = "SINGLE_CONTROL") -> dict[str, Any]:
    constituent_count = 2 if composition_type == "COMBINED_M3" else 1
    return {
        "control_condition_id": "ctrlcond:bounded-treatment",
        "condition_version": "0.1.0",
        "display_name": "Bounded treatment condition",
        "description": "A declarative experimental control composition.",
        "composition_type": composition_type,
        "constituents": [constituent(index) for index in range(1, constituent_count + 1)],
        "baseline_assumptions": [
            {
                "assumption_id": "common_synthetic_baseline",
                "description": "The declared common synthetic baseline is active.",
            }
        ],
        "expected_enforcement_locations": [
            {
                "location_id": "declared_boundary",
                "description": "The instrument must validate this declared location.",
            }
        ],
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


@pytest.mark.parametrize("schema_name", ["policy", "control", "control_condition"])
def test_stage4_schema_is_valid_draft_2020_12(
    schema_name: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    schema = schemas[schema_name]
    assert schema["$schema"] == DRAFT_2020_12
    assert schema["$id"] == SCHEMA_IDS[schema_name]
    check_draft_2020_12_schema(schema, schema_store=schema_store)


def test_valid_policy_is_accepted(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    assert_valid(valid_policy(), schemas["policy"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("policy_id", "control:wrong-prefix"),
        ("policy_version", "v0.1"),
        ("default_authorization", "ALLOWED"),
    ],
)
def test_policy_rejects_invalid_identity_version_or_default(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_policy()
    instance[field] = value
    assert_invalid(instance, schemas["policy"], schema_store)


@pytest.mark.parametrize("state", ["ALLOWED", "DENIED"])
def test_policy_accepts_active_rule_state_without_approval_policy(
    state: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_policy()
    instance["rules"] = [policy_rule(state)]
    assert_valid(instance, schemas["policy"], schema_store)


def test_policy_accepts_approval_required_with_approval_policy(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_policy()
    rule = policy_rule("APPROVAL_REQUIRED")
    rule["approval_policy_id"] = "approvalpolicy:deterministic-approval"
    instance["rules"] = [rule]
    assert_valid(instance, schemas["policy"], schema_store)


def test_policy_rejects_approval_required_without_approval_policy(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_policy()
    instance["rules"] = [policy_rule("APPROVAL_REQUIRED")]
    assert_invalid(instance, schemas["policy"], schema_store)


@pytest.mark.parametrize("state", ["ALLOWED", "DENIED"])
def test_policy_rejects_approval_policy_for_nonapproval_rule(
    state: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_policy()
    rule = policy_rule(state)
    rule["approval_policy_id"] = "approvalpolicy:not-applicable"
    instance["rules"] = [rule]
    assert_invalid(instance, schemas["policy"], schema_store)


@pytest.mark.parametrize("state", ["NOT_APPLICABLE", "INDETERMINATE"])
def test_policy_rejects_nonpolicy_rule_state(
    state: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_policy()
    instance["rules"] = [policy_rule(state)]
    assert_invalid(instance, schemas["policy"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("resource_id", "task:wrong-prefix"),
        ("subject_agent_condition_id", "modelcond:wrong-prefix"),
        ("action_class", "Read protected"),
    ],
)
def test_policy_rejects_invalid_rule_value(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_policy()
    rule = policy_rule()
    rule[field] = value
    instance["rules"] = [rule]
    assert_invalid(instance, schemas["policy"], schema_store)


def test_policy_accepts_valid_subject_agent_condition(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_policy()
    instance["rules"][0]["subject_agent_condition_id"] = "agentcond:baseline-agent"
    assert_valid(instance, schemas["policy"], schema_store)


@pytest.mark.parametrize("mutation", ["unknown", "missing"])
def test_policy_rejects_unknown_or_missing_root_field(
    mutation: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_policy()
    if mutation == "unknown":
        instance["runtime_decision"] = "ALLOWED"
    else:
        del instance["description"]
    assert_invalid(instance, schemas["policy"], schema_store)


def test_policy_validation_does_not_mutate_instance(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_policy()
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["policy"], schema_store)
    assert instance == original


@pytest.mark.parametrize("layer", ["M1", "M2", "M3"])
def test_valid_control_layer_is_accepted(
    layer: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(valid_control(layer), schemas["control"], schema_store)


@pytest.mark.parametrize("layer", ["S0", "M4"])
def test_control_rejects_nonexperimental_layer(
    layer: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_control()
    instance["experimental_control_layer"] = layer
    assert_invalid(instance, schemas["control"], schema_store)


def test_m3_rejects_agent_administrative_authority(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_control("M3")
    instance["agent_has_administrative_authority"] = True
    assert_invalid(instance, schemas["control"], schema_store)


def test_m3_requires_external_enforcement_assertion(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_control("M3")
    instance["m3_external_enforcement_assertion"] = False
    assert_invalid(instance, schemas["control"], schema_store)


@pytest.mark.parametrize("layer", ["M1", "M2"])
def test_non_m3_rejects_external_enforcement_assertion(
    layer: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_control(layer)
    instance["m3_external_enforcement_assertion"] = True
    assert_invalid(instance, schemas["control"], schema_store)


def test_m3_rejects_not_applicable_failure_mode(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_control("M3")
    instance["failure_mode"] = "NOT_APPLICABLE"
    assert_invalid(instance, schemas["control"], schema_store)


@pytest.mark.parametrize("failure_mode", ["FAIL_CLOSED", "FAIL_OPEN"])
def test_m3_accepts_declared_applicable_failure_mode(
    failure_mode: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_control("M3")
    instance["failure_mode"] = failure_mode
    assert_valid(instance, schemas["control"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("control_id", "policy:wrong-prefix"),
        ("control_version", "0.1"),
        ("configuration_id", "control:wrong-prefix"),
        ("failure_mode", "FAIL_SAFE"),
        ("agent_has_administrative_authority", "false"),
        ("m3_external_enforcement_assertion", "false"),
    ],
)
def test_control_rejects_invalid_shared_or_primitive_value(
    field: str,
    value: object,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_control()
    instance[field] = value
    assert_invalid(instance, schemas["control"], schema_store)


def test_control_rejects_malformed_dependency_id(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_control()
    instance["dependencies"] = ["resource:wrong-prefix"]
    assert_invalid(instance, schemas["control"], schema_store)


def test_control_rejects_duplicate_dependency_id(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_control()
    instance["dependencies"] = ["control:dependency", "control:dependency"]
    assert_invalid(instance, schemas["control"], schema_store)


@pytest.mark.parametrize("family", SCENARIO_FAMILIES)
def test_control_accepts_each_frozen_scenario_family(
    family: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_control()
    instance["applicable_scenario_families"] = [family]
    assert_valid(instance, schemas["control"], schema_store)


def test_control_rejects_unknown_scenario_family(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_control()
    instance["applicable_scenario_families"] = ["S11"]
    assert_invalid(instance, schemas["control"], schema_store)


@pytest.mark.parametrize("mutation", ["unknown", "missing"])
def test_control_rejects_unknown_or_missing_root_field(
    mutation: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_control()
    if mutation == "unknown":
        instance["effectiveness"] = "proven"
    else:
        del instance["security_objective"]
    assert_invalid(instance, schemas["control"], schema_store)


def test_control_validation_does_not_mutate_instance(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_control("M3")
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["control"], schema_store)
    assert instance == original


@pytest.mark.parametrize(
    "composition_type",
    ["SINGLE_CONTROL", "LAYER_CONDITION", "COMBINED_M3", "DEFENSE_IN_DEPTH"],
)
def test_valid_control_condition_composition_is_accepted(
    composition_type: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(
        valid_condition(composition_type), schemas["control_condition"], schema_store
    )


@pytest.mark.parametrize("count", [0, 2])
def test_single_control_requires_exactly_one_constituent(
    count: int,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_condition()
    instance["constituents"] = [constituent(index) for index in range(1, count + 1)]
    assert_invalid(instance, schemas["control_condition"], schema_store)


def test_combined_m3_requires_at_least_two_constituents(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_condition("COMBINED_M3")
    instance["constituents"] = [constituent()]
    assert_invalid(instance, schemas["control_condition"], schema_store)


def test_condition_rejects_unknown_composition_type(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_condition()
    instance["composition_type"] = "PROVEN_M3"
    assert_invalid(instance, schemas["control_condition"], schema_store)


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("root", "control_condition_id", "cond:wrong-prefix"),
        ("constituent", "control_id", "policy:wrong-prefix"),
        ("constituent", "control_version", "v0.1"),
        ("constituent", "configuration_id", "ctrlcond:wrong-prefix"),
    ],
)
def test_condition_rejects_invalid_shared_identity_or_version(
    target: str,
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_condition()
    if target == "root":
        instance[field] = value
    else:
        instance["constituents"][0][field] = value
    assert_invalid(instance, schemas["control_condition"], schema_store)


def test_condition_rejects_malformed_baseline_assumption(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_condition()
    instance["baseline_assumptions"] = [{"assumption_id": "Missing description"}]
    assert_invalid(instance, schemas["control_condition"], schema_store)


def test_condition_rejects_malformed_enforcement_location(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_condition()
    instance["expected_enforcement_locations"] = [
        {"location_id": "declared_boundary", "description": ""}
    ]
    assert_invalid(instance, schemas["control_condition"], schema_store)


@pytest.mark.parametrize("mutation", ["unknown", "missing"])
def test_condition_rejects_unknown_or_missing_root_field(
    mutation: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_condition()
    if mutation == "unknown":
        instance["confirmed_effectiveness"] = True
    else:
        del instance["baseline_assumptions"]
    assert_invalid(instance, schemas["control_condition"], schema_store)


def test_condition_accepts_bounded_composition_order(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_condition("DEFENSE_IN_DEPTH")
    instance["composition_order"] = ["control:bounded-control-1"]
    assert_valid(instance, schemas["control_condition"], schema_store)


def test_condition_rejects_duplicate_identical_constituent_objects(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_condition("DEFENSE_IN_DEPTH")
    instance["constituents"] = [constituent(), constituent()]
    assert_invalid(instance, schemas["control_condition"], schema_store)


def test_control_id_only_constituent_uniqueness_is_deferred(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_condition("DEFENSE_IN_DEPTH")
    second = constituent()
    second["configuration_id"] = "cond:alternate-config"
    instance["constituents"] = [constituent(), second]
    assert_valid(instance, schemas["control_condition"], schema_store)


def test_condition_validation_does_not_mutate_instance(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_condition("COMBINED_M3")
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["control_condition"], schema_store)
    assert instance == original


def test_action_class_syntax_exactly_matches_stage3(
    schemas: dict[str, dict[str, Any]],
) -> None:
    expected_pattern = schemas["resource"]["$defs"]["action_class"]["pattern"]
    assert schemas["benign_task"]["$defs"]["action_class"]["pattern"] == expected_pattern
    assert (
        schemas["capability_envelope"]["$defs"]["action_class"]["pattern"]
        == expected_pattern
    )
    assert schemas["policy"]["$defs"]["action_class"]["pattern"] == expected_pattern


def test_scenario_families_exactly_match_stage3(
    schemas: dict[str, dict[str, Any]],
) -> None:
    assert schemas["scenario"]["properties"]["scenario_family"]["enum"] == (
        SCENARIO_FAMILIES
    )
    assert schemas["control"]["$defs"]["scenario_family"]["enum"] == (
        SCENARIO_FAMILIES
    )


@pytest.mark.parametrize(
    "schema_name,reference_path,expected_fragment",
    [
        ("policy", ("properties", "policy_id"), "#/$defs/policy_id"),
        ("policy", ("$defs", "rule", "properties", "resource_id"), "#/$defs/resource_id"),
        (
            "policy",
            ("$defs", "rule", "properties", "subject_agent_condition_id"),
            "#/$defs/agent_condition_id",
        ),
        ("control", ("properties", "control_id"), "#/$defs/control_id"),
        (
            "control_condition",
            ("properties", "control_condition_id"),
            "#/$defs/control_condition_id",
        ),
    ],
)
def test_stage4_shared_identifier_references_use_common_schema(
    schema_name: str,
    reference_path: tuple[str, ...],
    expected_fragment: str,
    schemas: dict[str, dict[str, Any]],
) -> None:
    node: Any = schemas[schema_name]
    for part in reference_path:
        node = node[part]
    assert node["$ref"] == SCHEMA_IDS["common"] + expected_fragment


def test_local_store_resolves_common_and_stage3_without_network(
    monkeypatch: pytest.MonkeyPatch,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access was attempted")

    monkeypatch.setattr(urllib.request, "urlopen", fail_network)
    assert_valid(valid_policy(), schemas["policy"], schema_store)
    check_draft_2020_12_schema(schemas["scenario"], schema_store=schema_store)


def test_unknown_project_reference_fails_explicitly() -> None:
    schema = {
        "$schema": DRAFT_2020_12,
        "$id": "urn:frontier-agent-containment:schema:test:0.1.0",
        "$ref": "urn:frontier-agent-containment:schema:missing:0.1.0",
    }
    with pytest.raises(UnknownSchemaReferenceError):
        validate_instance({}, schema, schema_store={})


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_remote_reference_is_rejected_before_retrieval(
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
        "$id": "urn:frontier-agent-containment:schema:test:0.1.0",
        "$ref": f"{scheme}://example.invalid/schema.json",
    }
    with pytest.raises(ExternalSchemaReferenceError):
        validate_instance({}, schema, schema_store={})
    assert called is False


def test_duplicate_schema_ids_still_fail(
    tmp_path: Path,
    schemas: dict[str, dict[str, Any]],
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    encoded = json.dumps(schemas["common"])
    first.write_text(encoded, encoding="utf-8")
    second.write_text(encoded, encoding="utf-8")
    with pytest.raises(DuplicateSchemaIdError):
        load_schema_store([first, second])
