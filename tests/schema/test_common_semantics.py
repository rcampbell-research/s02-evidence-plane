"""Stage 2 tests for canonical shared schema semantics."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import ValidationError

from frontier_agent_containment.schema_validation import (
    DuplicateJsonKeyError,
    check_draft_2020_12_schema,
    load_json,
    validate_instance,
)


COMMON_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "common.schema.json"
)

IDENTIFIER_PREFIXES = {
    "experiment_id": "exp",
    "run_id": "run",
    "condition_id": "cond",
    "scenario_id": "scenario",
    "task_id": "task",
    "action_id": "action",
    "event_id": "event",
    "agent_condition_id": "agentcond",
    "model_condition_id": "modelcond",
    "capability_condition_id": "capcond",
    "autonomy_condition_id": "autonomy",
    "control_id": "control",
    "control_condition_id": "ctrlcond",
    "capability_envelope_id": "envelope",
    "policy_id": "policy",
    "approval_policy_id": "approvalpolicy",
    "environment_id": "env",
    "build_id": "build",
    "resource_id": "resource",
    "validation_case_id": "valcase",
    "instrument_configuration_id": "instrument",
    "analysis_configuration_id": "analysis",
    "campaign_id": "campaign",
    "scheduled_run_id": "scheduledrun",
}

# These expected values are test oracles traced to the frozen specifications;
# schemas/common.schema.json remains the executable source consumed by code.
EXPECTED_ENUMS = {
    "experimental_control_layer": ["M1", "M2", "M3"],
    "laboratory_safety_layer": ["S0"],
    "capability_authorization_state": [
        "ALLOWED",
        "DENIED",
        "APPROVAL_REQUIRED",
        "NOT_APPLICABLE",
    ],
    "authorization_decision": [
        "ALLOWED",
        "DENIED",
        "APPROVAL_REQUIRED",
        "INDETERMINATE",
    ],
    "approval_decision": [
        "APPROVED",
        "REJECTED",
        "EXPIRED",
        "TIMED_OUT",
        "UNAVAILABLE",
        "INVALID",
    ],
    "terminal_action_outcome": [
        "AUTHORIZED_EXECUTED",
        "AUTHORIZED_NOT_EXECUTED",
        "UNAUTHORIZED_BLOCKED",
        "UNAUTHORIZED_NOT_EXECUTED_OTHER",
        "UNAUTHORIZED_EXECUTED",
        "AGENT_ABORTED",
        "CONTROL_ERROR",
        "INCONCLUSIVE",
    ],
    "run_phase": [
        "DEVELOPMENT",
        "INSTRUMENT_VALIDATION",
        "PILOT",
        "CONFIRMATORY",
    ],
    "evidence_quality_state": [
        "VALID",
        "MISSING_REQUIRED",
        "CONFLICTING",
        "DUPLICATE",
        "MALFORMED",
        "UNTRUSTED_SOURCE",
        "OUT_OF_ORDER",
        "UNRESOLVED_IDENTITY",
        "INCONCLUSIVE",
    ],
    "validation_result_state": [
        "VALIDATION_PASS",
        "VALIDATION_FAIL",
        "VALIDATION_INCONCLUSIVE",
        "VALIDATION_NOT_APPLICABLE",
    ],
    "validation_applicability_class": [
        "MANDATORY_GLOBAL",
        "MANDATORY_CONDITIONAL",
        "OPTIONAL_DIAGNOSTIC",
    ],
    "instrument_acceptance_state": [
        "ACCEPTED_FOR_PILOT",
        "ACCEPTED_FOR_CONFIRMATORY",
        "REJECTED",
    ],
    "artifact_lifecycle_state": ["DRAFT", "VALIDATED", "FROZEN", "RETIRED"],
    "execution_state": [
        "EXECUTION_NOT_ATTEMPTED",
        "EXECUTION_ATTEMPTED",
        "EXECUTION_SUCCEEDED",
        "EXECUTION_FAILED",
        "EXECUTION_RESULT_UNKNOWN",
    ],
}


@pytest.fixture(scope="module")
def common_schema() -> dict[str, Any]:
    schema = load_json(COMMON_SCHEMA_PATH)
    assert isinstance(schema, dict)
    return schema


def definition_schema(common_schema: dict[str, Any], name: str) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": common_schema["$defs"],
        "$ref": f"#/$defs/{name}",
    }


def assert_valid_definition(
    common_schema: dict[str, Any], name: str, value: object
) -> None:
    validate_instance(value, definition_schema(common_schema, name))


def assert_invalid_definition(
    common_schema: dict[str, Any], name: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        validate_instance(value, definition_schema(common_schema, name))


def test_common_schema_is_valid_draft_2020_12(
    common_schema: dict[str, Any],
) -> None:
    assert common_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert common_schema["$id"] == (
        "urn:frontier-agent-containment:schema:common:0.1.0"
    )
    check_draft_2020_12_schema(common_schema)


@pytest.mark.parametrize(
    "version",
    ["0.1.0", "1.0.0", "2.3.4-alpha.1", "1.2.3+build.5", "1.2.3-rc.1+7"],
)
def test_executable_artifact_version_accepts_semver_core_and_extensions(
    common_schema: dict[str, Any], version: str
) -> None:
    assert_valid_definition(common_schema, "executable_artifact_version", version)


@pytest.mark.parametrize(
    "version",
    ["v0.1", "0.1", "01.2.3", "latest", "1.0.0-01", "1.0.0+", "1.0.0\n"],
)
def test_executable_artifact_version_rejects_noncanonical_values(
    common_schema: dict[str, Any], version: str
) -> None:
    assert_invalid_definition(common_schema, "executable_artifact_version", version)


@pytest.mark.parametrize("definition,prefix", IDENTIFIER_PREFIXES.items())
def test_every_typed_identifier_accepts_its_prefix(
    common_schema: dict[str, Any], definition: str, prefix: str
) -> None:
    assert_valid_definition(common_schema, definition, f"{prefix}:alpha-1.test_2")


@pytest.mark.parametrize("definition,prefix", IDENTIFIER_PREFIXES.items())
def test_every_typed_identifier_rejects_wrong_prefix(
    common_schema: dict[str, Any], definition: str, prefix: str
) -> None:
    assert_invalid_definition(common_schema, definition, f"wrong:{prefix}-1")


@pytest.mark.parametrize("definition,prefix", IDENTIFIER_PREFIXES.items())
def test_every_typed_identifier_rejects_whitespace(
    common_schema: dict[str, Any], definition: str, prefix: str
) -> None:
    for token in ("bad token", "token\n"):
        assert_invalid_definition(common_schema, definition, f"{prefix}:{token}")


@pytest.mark.parametrize("value", ["exp:", "exp:/bad", "exp::bad", "Exp:token"])
def test_typed_identifier_rejects_empty_or_malformed_token(
    common_schema: dict[str, Any], value: str
) -> None:
    assert_invalid_definition(common_schema, "experiment_id", value)


@pytest.mark.parametrize("definition,members", EXPECTED_ENUMS.items())
def test_canonical_enumeration_exactly_matches_frozen_members(
    common_schema: dict[str, Any], definition: str, members: list[str]
) -> None:
    assert common_schema["$defs"][definition]["enum"] == members
    for member in members:
        assert_valid_definition(common_schema, definition, member)


@pytest.mark.parametrize("definition", EXPECTED_ENUMS)
def test_each_canonical_enumeration_rejects_unknown_member(
    common_schema: dict[str, Any], definition: str
) -> None:
    assert_invalid_definition(common_schema, definition, "UNKNOWN_MEMBER")


def test_safety_and_experimental_layers_cannot_be_conflated(
    common_schema: dict[str, Any],
) -> None:
    assert_invalid_definition(common_schema, "experimental_control_layer", "S0")
    for member in ("M1", "M2", "M3"):
        assert_invalid_definition(common_schema, "laboratory_safety_layer", member)


def test_capability_state_and_authorization_decision_remain_distinct(
    common_schema: dict[str, Any],
) -> None:
    assert_valid_definition(
        common_schema, "capability_authorization_state", "NOT_APPLICABLE"
    )
    assert_invalid_definition(common_schema, "authorization_decision", "NOT_APPLICABLE")
    assert_valid_definition(common_schema, "authorization_decision", "INDETERMINATE")
    assert_invalid_definition(
        common_schema, "capability_authorization_state", "INDETERMINATE"
    )


def test_approval_decision_exactly_preserves_frozen_six_states(
    common_schema: dict[str, Any],
) -> None:
    expected = [
        "APPROVED",
        "REJECTED",
        "EXPIRED",
        "TIMED_OUT",
        "UNAVAILABLE",
        "INVALID",
    ]
    assert common_schema["$defs"]["approval_decision"]["enum"] == expected
    for member in expected:
        assert_valid_definition(common_schema, "approval_decision", member)
    assert_invalid_definition(common_schema, "approval_decision", "APPROVAL_REQUIRED")
    assert_invalid_definition(common_schema, "approval_decision", "UNKNOWN_APPROVAL")


def test_terminal_action_outcome_is_exactly_the_frozen_eight(
    common_schema: dict[str, Any],
) -> None:
    assert len(common_schema["$defs"]["terminal_action_outcome"]["enum"]) == 8
    assert common_schema["$defs"]["terminal_action_outcome"]["enum"] == (
        EXPECTED_ENUMS["terminal_action_outcome"]
    )


def test_duplicate_top_level_json_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"policy": "DENIED", "policy": "ALLOWED"}', encoding="utf-8")

    with pytest.raises(DuplicateJsonKeyError, match="policy"):
        load_json(path)


def test_duplicate_nested_json_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "nested-duplicate.json"
    path.write_text('{"outer": {"state": 1, "state": 2}}', encoding="utf-8")

    with pytest.raises(DuplicateJsonKeyError, match="state"):
        load_json(path)


def test_ordinary_json_loads_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "valid.json"
    expected = {"state": "VALID", "nested": {"count": 1}, "items": [1, 2]}
    path.write_text(json.dumps(expected), encoding="utf-8")

    loaded = load_json(path)

    assert loaded == expected


def test_repeated_array_values_are_not_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "array.json"
    path.write_text('{"values": ["same", "same"]}', encoding="utf-8")

    assert load_json(path) == {"values": ["same", "same"]}


def test_parse_errors_duplicate_keys_and_schema_failures_are_distinct(
    tmp_path: Path,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"value":', encoding="utf-8")
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"value": 1, "value": 2}', encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_json(malformed)
    with pytest.raises(DuplicateJsonKeyError):
        load_json(duplicate)
    with pytest.raises(ValidationError):
        validate_instance(
            {"value": "1"},
            {
                "type": "object",
                "properties": {"value": {"type": "integer"}},
                "required": ["value"],
            },
        )


def test_loaded_valid_json_is_not_rewritten(tmp_path: Path) -> None:
    path = tmp_path / "preserved.json"
    path.write_text('{"value": "1", "items": [1, 1]}', encoding="utf-8")
    loaded = load_json(path)
    original = copy.deepcopy(loaded)

    validate_instance(
        loaded,
        {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "items": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["value", "items"],
            "additionalProperties": False,
        },
    )

    assert loaded == original
