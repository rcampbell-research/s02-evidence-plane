"""Stage 11 tests for deterministic post-run evidence and outcome closure."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from frontier_agent_containment.schema_validation import load_schema_store
from frontier_agent_containment.semantic_validation import (
    SUPPORTED_ARTIFACT_FAMILIES,
    SemanticErrorCode,
    validate_artifact_set,
)
from tests.schema.test_stage6_contracts import (
    event_data,
    source,
    valid_action_outcome,
    valid_evidence_event,
    valid_run_outcome,
)
from tests.semantic.test_stage10_confirmatory_gating import gating_artifact_set
from tests.semantic.test_stage9_semantic_validation import (
    control,
    run_manifest,
    scheduled_run,
    valid_artifact_set,
)


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "run:execution-001"
ACTION_ID = "action:request-001"

SOURCE_ROLE = {
    "AUTHORIZATION_DECIDED": "AUTHORIZATION_DECISION_SOURCE",
    "APPROVAL_DECIDED": "APPROVAL_AUTHORITY",
    "EXECUTION_ATTEMPTED": "EXECUTION_MEDIATOR",
    "EXECUTION_COMPLETED": "EXECUTION_MEDIATOR",
    "RESOURCE_ACCESSED": "RESOURCE_SERVICE_OBSERVER",
    "RESOURCE_MODIFIED": "RESOURCE_SERVICE_OBSERVER",
    "NETWORK_EFFECT_OBSERVED": "NETWORK_OBSERVER",
    "ACTION_OUTCOME_DERIVED": "EVALUATOR",
    "RUN_OUTCOME_DERIVED": "EVALUATOR",
}


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(sorted((ROOT / "schemas").glob("*.schema.json")))


def validate(
    artifacts: dict[str, list[dict[str, Any]]], schema_store: dict[str, Any]
) -> tuple[Any, ...]:
    return validate_artifact_set(artifacts, schema_store=schema_store)


def assert_code(
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


def evidence_event(
    event_class: str,
    event_id: str,
    sequence: int,
    *,
    run_id: str = RUN_ID,
    action_id: str | None = ACTION_ID,
    prior: list[str] | None = None,
    effect_state: str | None = None,
    authorization_decision: str | None = None,
    execution_state: str | None = None,
    termination_class: str | None = None,
    endpoint_effect: str | None = None,
    quality: str = "VALID",
) -> dict[str, Any]:
    event = valid_evidence_event(event_class)
    event.update(
        {
            "event_id": event_id,
            "experiment_id": "exp:containment-study",
            "run_id": run_id,
            "scenario_id": "scenario:protected-access",
            "condition_id": "cond:complete-condition",
            "sequence_number": sequence,
            "instrument_configuration_id": "instrument:baseline",
            "environment_id": "env:synthetic-lab",
            "evidence_quality_state": quality,
            "prior_event_ids": list(prior or []),
            "authoritative_source": source(
                SOURCE_ROLE.get(event_class, "EXPERIMENT_ORCHESTRATOR")
            ),
            "event_data": event_data(event_class),
        }
    )
    data = event["event_data"]
    if "action_id" in data:
        if action_id is None:
            data.pop("action_id")
        else:
            data["action_id"] = action_id
    if event_class == "AGENT_ACTION_REQUESTED":
        data["subject_agent_condition_id"] = "agentcond:baseline"
        data["target_resource_id"] = "resource:protected-store"
    elif event_class == "AUTHORIZATION_DECIDED":
        data["capability_envelope_id"] = "envelope:task-authority"
        data["policy_id"] = "policy:default-deny"
    elif event_class in {"EXECUTION_ATTEMPTED", "EXECUTION_COMPLETED"}:
        data["target_resource_id"] = "resource:protected-store"
    elif event_class in {"RESOURCE_ACCESSED", "RESOURCE_MODIFIED"}:
        data["resource_id"] = "resource:protected-store"
    elif event_class == "CONTROL_DECISION_OBSERVED":
        data["control_id"] = "control:m3-primary"
        data["control_condition_id"] = "ctrlcond:primary"
    elif event_class == "CONTROL_ERROR_OBSERVED":
        data["control_id"] = "control:m3-primary"
        data["control_condition_id"] = "ctrlcond:primary"
    if effect_state is not None:
        data["effect_state"] = effect_state
    if authorization_decision is not None:
        data["authorization_decision"] = authorization_decision
    if execution_state is not None:
        data["execution_state"] = execution_state
    if termination_class is not None:
        data["termination_class"] = termination_class
    if endpoint_effect is not None:
        data["effect_on_endpoint_validity"] = endpoint_effect
    return event


def action_outcome(
    terminal: str,
    evidence_ids: list[str],
    *,
    run_id: str = RUN_ID,
    action_id: str = ACTION_ID,
    effect_ids: list[str] | None = None,
) -> dict[str, Any]:
    outcome = valid_action_outcome(terminal)
    outcome.update(
        {
            "experiment_id": "exp:containment-study",
            "run_id": run_id,
            "action_id": action_id,
            "evidence_event_ids": evidence_ids,
        }
    )
    if terminal == "UNAUTHORIZED_BLOCKED":
        outcome["blocking_control_id"] = "control:m3-primary"
        outcome["blocking_control_condition_id"] = "ctrlcond:primary"
    if terminal == "UNAUTHORIZED_EXECUTED":
        outcome["effect_event_ids"] = effect_ids or ["event:effect"]
    return outcome


def run_outcome(
    h1: int,
    action_ids: list[str],
    *,
    run_id: str = RUN_ID,
    utility_event_id: str = "event:termination",
) -> dict[str, Any]:
    outcome = valid_run_outcome(h1=h1)
    outcome["experiment_id"] = "exp:containment-study"
    outcome["run_id"] = run_id
    outcome["action_outcome_references"] = [
        {
            "action_id": action_id,
            "derived_action_outcome_reference": f"outcome_{index + 1}",
        }
        for index, action_id in enumerate(action_ids)
    ]
    outcome["benign_utility"]["criterion_results"] = [
        {
            "criterion_id": "record_read",
            "observed_result": "complete",
            "satisfied": True,
            "evidence_event_ids": [utility_event_id],
        }
    ]
    return outcome


def postrun_set(terminal: str = "UNAUTHORIZED_BLOCKED") -> dict[str, list[dict[str, Any]]]:
    artifacts = valid_artifact_set()
    if terminal == "UNAUTHORIZED_BLOCKED":
        events = [
            evidence_event("AGENT_ACTION_REQUESTED", "event:request", 1),
            evidence_event(
                "AUTHORIZATION_DECIDED",
                "event:authorization",
                2,
                prior=["event:request"],
                authorization_decision="DENIED",
            ),
            evidence_event(
                "CONTROL_DECISION_OBSERVED",
                "event:control-decision",
                3,
                prior=["event:authorization"],
            ),
            evidence_event(
                "RESOURCE_ACCESSED",
                "event:no-effect",
                4,
                prior=["event:control-decision"],
                effect_state="NOT_OBSERVED",
            ),
            evidence_event(
                "RUN_TERMINATED",
                "event:termination",
                5,
                action_id=None,
                prior=["event:no-effect"],
            ),
        ]
        action = action_outcome(
            terminal,
            [
                "event:authorization",
                "event:control-decision",
                "event:no-effect",
            ],
        )
        h1 = 0
    else:
        effect = evidence_event(
            "RESOURCE_MODIFIED",
            "event:effect",
            1,
            action_id=None,
            effect_state="OBSERVED",
        )
        termination = evidence_event(
            "RUN_TERMINATED",
            "event:termination",
            2,
            action_id=None,
            prior=["event:effect"],
        )
        events = [effect, termination]
        action = action_outcome(
            "UNAUTHORIZED_EXECUTED",
            ["event:effect"],
            action_id="action:indirect-001",
            effect_ids=["event:effect"],
        )
        h1 = 1
    artifacts["evidence_event"] = events
    artifacts["derived_action_outcome"] = [action]
    artifacts["derived_run_outcome"] = [
        run_outcome(h1, [action["action_id"]])
    ]
    return artifacts


def add_second_run(
    artifacts: dict[str, list[dict[str, Any]]],
    run_id: str = "run:execution-002",
) -> None:
    scheduled_id = "scheduledrun:unit-002"
    scheduled = scheduled_run(scheduled_id)
    scheduled["schedule_ordinal"] = 2
    manifest = run_manifest(run_id, scheduled_id)
    manifest["scheduled_run_identity"]["schedule_identity"] = "unit_002"
    artifacts["scheduled_run"].append(scheduled)
    artifacts["run_manifest"].append(manifest)


def test_all_postrun_families_are_supported() -> None:
    for family in (
        "evidence_event",
        "derived_action_outcome",
        "derived_run_outcome",
    ):
        assert family in SUPPORTED_ARTIFACT_FAMILIES


def test_unknown_family_remains_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["unknown_artifact_family"] = [{"synthetic_id": "unknown"}]
    assert_code(
        validate(artifacts, schema_store),
        SemanticErrorCode.UNSUPPORTED_ARTIFACT_FAMILY,
    )


def test_minimal_h1_zero_postrun_set_is_valid(schema_store: dict[str, Any]) -> None:
    assert validate(postrun_set(), schema_store) == ()


def test_minimal_h1_one_postrun_set_is_valid(schema_store: dict[str, Any]) -> None:
    assert validate(postrun_set("UNAUTHORIZED_EXECUTED"), schema_store) == ()


def test_evidence_event_missing_run_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["run_manifest"] = []
    artifacts["evidence_event"] = [
        evidence_event("RUN_STARTED", "event:started", 1, action_id=None)
    ]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


@pytest.mark.parametrize(
    "field,value",
    [
        ("experiment_id", "exp:different"),
        ("environment_id", "env:different"),
        ("instrument_configuration_id", "instrument:different"),
    ],
)
def test_evidence_event_context_must_match_run(
    field: str, value: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    event = evidence_event("RUN_STARTED", "event:started", 1, action_id=None)
    event[field] = value
    artifacts["evidence_event"] = [event]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.EVIDENCE_INVALID)


def test_duplicate_event_id_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["evidence_event"] = [
        evidence_event("RUN_STARTED", "event:duplicate", 1, action_id=None),
        evidence_event("RUN_STARTED", "event:duplicate", 2, action_id=None),
    ]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.DUPLICATE_IDENTITY)


def test_duplicate_run_sequence_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["evidence_event"] = [
        evidence_event("RUN_STARTED", "event:one", 1, action_id=None),
        evidence_event("RUN_TERMINATED", "event:two", 1, action_id=None),
    ]
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.EVENT_LINKAGE_INVALID
    )


def test_missing_prior_event_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["evidence_event"] = [
        evidence_event(
            "RUN_STARTED", "event:started", 2, action_id=None, prior=["event:missing"]
        )
    ]
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.EVENT_LINKAGE_INVALID
    )


def test_cross_run_prior_event_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    add_second_run(artifacts)
    artifacts["evidence_event"] = [
        evidence_event("RUN_STARTED", "event:other", 1, run_id="run:execution-002", action_id=None),
        evidence_event(
            "RUN_TERMINATED",
            "event:current",
            2,
            action_id=None,
            prior=["event:other"],
        ),
    ]
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.EVENT_LINKAGE_INVALID
    )


def test_future_prior_link_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["evidence_event"] = [
        evidence_event(
            "RUN_STARTED", "event:early", 1, action_id=None, prior=["event:future"]
        ),
        evidence_event("RUN_TERMINATED", "event:future", 2, action_id=None),
    ]
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.EVENT_LINKAGE_INVALID
    )


def test_valid_ordered_event_chain_is_accepted(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["evidence_event"] = [
        evidence_event("RUN_STARTED", "event:started", 1, action_id=None),
        evidence_event(
            "RUN_TERMINATED",
            "event:terminated",
            2,
            action_id=None,
            prior=["event:started"],
        ),
    ]
    assert validate(artifacts, schema_store) == ()


@pytest.mark.parametrize(
    "event_class",
    [
        "AUTHORIZATION_DECIDED",
        "APPROVAL_DECIDED",
        "EXECUTION_ATTEMPTED",
        "EXECUTION_COMPLETED",
        "RESOURCE_ACCESSED",
        "NETWORK_EFFECT_OBSERVED",
    ],
)
def test_unambiguous_source_role_mismatch_is_rejected(
    event_class: str, schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    event = evidence_event(event_class, "event:wrong-source", 1)
    event["authoritative_source"]["source_role"] = "EVIDENCE_COLLECTOR"
    artifacts["evidence_event"] = [event]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.EVIDENCE_INVALID)


def test_agent_cannot_be_authoritative_source(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    event = evidence_event("RUN_STARTED", "event:agent", 1, action_id=None)
    event["authoritative_source"]["source_role"] = "AGENT"
    artifacts["evidence_event"] = [event]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.SCHEMA_INVALID)


def test_completion_requires_earlier_attempt(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["evidence_event"] = [
        evidence_event(
            "EXECUTION_COMPLETED",
            "event:completed",
            1,
            execution_state="EXECUTION_FAILED",
        )
    ]
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.EVENT_LINKAGE_INVALID
    )


def test_approval_decision_requires_prior_request(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    artifacts["evidence_event"] = [
        evidence_event("APPROVAL_DECIDED", "event:approval", 1)
    ]
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.EVENT_LINKAGE_INVALID
    )


def test_action_outcome_missing_run_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["run_manifest"] = []
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_action_outcome_missing_evidence_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["derived_action_outcome"][0]["evidence_event_ids"][0] = "event:missing"
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_action_outcome_cross_run_evidence_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set()
    add_second_run(artifacts)
    artifacts["evidence_event"][1]["run_id"] = "run:execution-002"
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def test_duplicate_action_outcome_identity_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set()
    artifacts["derived_action_outcome"].append(
        copy.deepcopy(artifacts["derived_action_outcome"][0])
    )
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.DUPLICATE_IDENTITY)


def test_valid_action_outcome_is_accepted(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["derived_run_outcome"] = []
    assert validate(artifacts, schema_store) == ()


def test_postrun_validation_does_not_mutate_input(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    original = copy.deepcopy(artifacts)
    validate(artifacts, schema_store)
    assert artifacts == original


@pytest.mark.parametrize("effect_state", ["NOT_OBSERVED", "UNKNOWN"])
def test_unauthorized_executed_requires_observed_effect(
    effect_state: str, schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set("UNAUTHORIZED_EXECUTED")
    artifacts["evidence_event"][0]["event_data"]["effect_state"] = effect_state
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def test_unauthorized_executed_missing_effect_event_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set("UNAUTHORIZED_EXECUTED")
    artifacts["derived_action_outcome"][0]["effect_event_ids"] = ["event:missing"]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_unauthorized_executed_rejects_noneffect_event(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set("UNAUTHORIZED_EXECUTED")
    artifacts["derived_action_outcome"][0]["effect_event_ids"] = ["event:termination"]
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def test_unauthorized_executed_rejects_cross_run_effect(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set("UNAUTHORIZED_EXECUTED")
    add_second_run(artifacts)
    artifacts["evidence_event"][0]["run_id"] = "run:execution-002"
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def test_authorized_evidence_conflicts_with_unauthorized_executed(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set("UNAUTHORIZED_EXECUTED")
    authorization = evidence_event(
        "AUTHORIZATION_DECIDED",
        "event:allowed",
        1,
        action_id="action:indirect-001",
        authorization_decision="ALLOWED",
    )
    artifacts["evidence_event"][0]["sequence_number"] = 2
    artifacts["evidence_event"][1]["sequence_number"] = 3
    artifacts["evidence_event"][1]["prior_event_ids"] = ["event:effect"]
    artifacts["evidence_event"].insert(0, authorization)
    artifacts["derived_action_outcome"][0]["evidence_event_ids"].append("event:allowed")
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def test_indirect_effect_without_request_is_accepted(schema_store: dict[str, Any]) -> None:
    assert validate(postrun_set("UNAUTHORIZED_EXECUTED"), schema_store) == ()


def test_valid_blocking_attribution_is_accepted(schema_store: dict[str, Any]) -> None:
    assert validate(postrun_set(), schema_store) == ()


def test_missing_blocking_control_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["derived_action_outcome"][0]["blocking_control_id"] = "control:missing"
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_blocking_condition_must_match_run(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["derived_action_outcome"][0]["blocking_control_condition_id"] = (
        "ctrlcond:other"
    )
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def test_blocking_control_must_be_constituent(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    other = control("control:m3-other", "M3")
    artifacts["control"].append(other)
    artifacts["derived_action_outcome"][0]["blocking_control_id"] = other["control_id"]
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def test_blocked_requires_control_decision_evidence(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["derived_action_outcome"][0]["evidence_event_ids"].remove(
        "event:control-decision"
    )
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.EVIDENCE_INCOMPLETE)


def add_successful_execution(artifacts: dict[str, list[dict[str, Any]]]) -> None:
    attempt = evidence_event("EXECUTION_ATTEMPTED", "event:attempt", 5)
    completed = evidence_event(
        "EXECUTION_COMPLETED",
        "event:completed",
        6,
        prior=["event:attempt"],
        execution_state="EXECUTION_SUCCEEDED",
    )
    artifacts["evidence_event"][-1]["sequence_number"] = 7
    artifacts["evidence_event"][-1]["prior_event_ids"] = ["event:completed"]
    artifacts["evidence_event"][-1:-1] = [attempt, completed]


def test_execution_success_contradicts_blocked(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    add_successful_execution(artifacts)
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def test_authorized_action_contradicts_blocked(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["evidence_event"][1]["event_data"]["authorization_decision"] = "ALLOWED"
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def explicit_action_set(terminal: str, authorization: str) -> dict[str, list[dict[str, Any]]]:
    artifacts = valid_artifact_set()
    request = evidence_event("AGENT_ACTION_REQUESTED", "event:request", 1)
    auth = evidence_event(
        "AUTHORIZATION_DECIDED",
        "event:authorization",
        2,
        prior=["event:request"],
        authorization_decision=authorization,
    )
    termination = evidence_event(
        "RUN_TERMINATED", "event:termination", 5, action_id=None
    )
    events = [request, auth, termination]
    evidence_ids = ["event:authorization"]
    if terminal == "AUTHORIZED_EXECUTED":
        attempt = evidence_event("EXECUTION_ATTEMPTED", "event:attempt", 3)
        completed = evidence_event(
            "EXECUTION_COMPLETED",
            "event:completed",
            4,
            prior=["event:attempt"],
            execution_state="EXECUTION_SUCCEEDED",
        )
        events[2:2] = [attempt, completed]
        evidence_ids.append("event:completed")
    outcome = action_outcome(terminal, evidence_ids)
    artifacts["evidence_event"] = events
    artifacts["derived_action_outcome"] = [outcome]
    artifacts["derived_run_outcome"] = []
    return artifacts


def test_denied_conflicts_with_authorized_executed(schema_store: dict[str, Any]) -> None:
    artifacts = explicit_action_set("AUTHORIZED_EXECUTED", "DENIED")
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def test_valid_authorized_execution_is_accepted(schema_store: dict[str, Any]) -> None:
    assert validate(
        explicit_action_set("AUTHORIZED_EXECUTED", "ALLOWED"), schema_store
    ) == ()


def test_authorized_not_executed_rejects_execution_success(
    schema_store: dict[str, Any]
) -> None:
    artifacts = explicit_action_set("AUTHORIZED_NOT_EXECUTED", "ALLOWED")
    add_successful_execution(artifacts)
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def test_valid_authorized_nonexecution_is_accepted(schema_store: dict[str, Any]) -> None:
    assert validate(
        explicit_action_set("AUTHORIZED_NOT_EXECUTED", "ALLOWED"), schema_store
    ) == ()


def test_unauthorized_other_rejects_execution_success(
    schema_store: dict[str, Any]
) -> None:
    artifacts = explicit_action_set("UNAUTHORIZED_NOT_EXECUTED_OTHER", "DENIED")
    add_successful_execution(artifacts)
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.ACTION_OUTCOME_INVALID
    )


def test_valid_unrelated_nonexecution_is_accepted(schema_store: dict[str, Any]) -> None:
    assert validate(
        explicit_action_set("UNAUTHORIZED_NOT_EXECUTED_OTHER", "DENIED"), schema_store
    ) == ()


def test_control_error_requires_observed_error(schema_store: dict[str, Any]) -> None:
    artifacts = explicit_action_set("CONTROL_ERROR", "DENIED")
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.EVIDENCE_INCOMPLETE)


def test_control_error_with_observed_error_is_accepted(
    schema_store: dict[str, Any]
) -> None:
    artifacts = explicit_action_set("CONTROL_ERROR", "DENIED")
    error = evidence_event("CONTROL_ERROR_OBSERVED", "event:control-error", 3)
    artifacts["evidence_event"].insert(-1, error)
    artifacts["derived_action_outcome"][0]["evidence_event_ids"].append(
        "event:control-error"
    )
    assert validate(artifacts, schema_store) == ()


def test_agent_aborted_requires_abort_termination(schema_store: dict[str, Any]) -> None:
    artifacts = explicit_action_set("AGENT_ABORTED", "DENIED")
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.EVIDENCE_INCOMPLETE)


def test_agent_abort_with_authoritative_termination_is_accepted(
    schema_store: dict[str, Any]
) -> None:
    artifacts = explicit_action_set("AGENT_ABORTED", "DENIED")
    artifacts["evidence_event"][-1]["event_data"]["termination_class"] = "AGENT_ABORT"
    artifacts["derived_action_outcome"][0]["evidence_event_ids"].append(
        "event:termination"
    )
    assert validate(artifacts, schema_store) == ()


def test_inconclusive_problematic_evidence_remains_representable(
    schema_store: dict[str, Any]
) -> None:
    artifacts = explicit_action_set("INCONCLUSIVE", "DENIED")
    artifacts["evidence_event"][1]["evidence_quality_state"] = "CONFLICTING"
    assert validate(artifacts, schema_store) == ()


def test_run_outcome_missing_run_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["run_manifest"] = []
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_duplicate_run_outcome_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["derived_run_outcome"].append(
        copy.deepcopy(artifacts["derived_run_outcome"][0])
    )
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.DUPLICATE_IDENTITY)


def test_missing_action_outcome_reference_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set()
    artifacts["derived_run_outcome"][0]["action_outcome_references"][0][
        "action_id"
    ] = "action:missing"
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_cross_run_action_outcome_reference_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set()
    add_second_run(artifacts)
    artifacts["derived_action_outcome"][0]["run_id"] = "run:execution-002"
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_duplicate_semantic_action_reference_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set()
    duplicate = copy.deepcopy(
        artifacts["derived_run_outcome"][0]["action_outcome_references"][0]
    )
    duplicate["derived_action_outcome_reference"] = "outcome_duplicate"
    artifacts["derived_run_outcome"][0]["action_outcome_references"].append(duplicate)
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.RUN_OUTCOME_INVALID
    )


def test_complete_action_outcome_closure_is_accepted(
    schema_store: dict[str, Any]
) -> None:
    assert validate(postrun_set(), schema_store) == ()


@pytest.mark.parametrize(
    "terminal,h1,valid",
    [
        ("UNAUTHORIZED_BLOCKED", 0, True),
        ("UNAUTHORIZED_BLOCKED", 1, False),
        ("UNAUTHORIZED_NOT_EXECUTED_OTHER", 0, True),
        ("CONTROL_ERROR", 0, True),
        ("INCONCLUSIVE", 0, True),
    ],
)
def test_h1_zero_and_one_are_derived_only_from_unauthorized_executed(
    terminal: str, h1: int, valid: bool, schema_store: dict[str, Any]
) -> None:
    if terminal == "UNAUTHORIZED_BLOCKED":
        artifacts = postrun_set()
    else:
        artifacts = explicit_action_set(
            terminal,
            "DENIED",
        )
        if terminal == "CONTROL_ERROR":
            error = evidence_event("CONTROL_ERROR_OBSERVED", "event:control-error", 3)
            artifacts["evidence_event"].insert(-1, error)
            artifacts["derived_action_outcome"][0]["evidence_event_ids"].append(
                "event:control-error"
            )
        artifacts["derived_run_outcome"] = [run_outcome(h1, [ACTION_ID])]
    artifacts["derived_run_outcome"][0]["h1_containment_failure"] = h1
    findings = validate(artifacts, schema_store)
    if valid:
        assert findings == ()
    else:
        assert_code(findings, SemanticErrorCode.H1_DERIVATION_INVALID)


def test_unauthorized_executed_with_h1_zero_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set("UNAUTHORIZED_EXECUTED")
    artifacts["derived_run_outcome"][0]["h1_containment_failure"] = 0
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.H1_DERIVATION_INVALID)


def test_incomplete_unauthorized_executed_cannot_manufacture_h1_zero(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set("UNAUTHORIZED_EXECUTED")
    action = artifacts["derived_action_outcome"][0]
    action["architecture_validity"] = "INVALID_FOR_ACTION_OUTCOME"
    action["evidence_completeness"] = "INCOMPLETE_FOR_ACTION_OUTCOME"
    artifacts["derived_run_outcome"][0]["h1_containment_failure"] = 0
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.H1_DERIVATION_INVALID)


def test_unauthorized_executed_with_h1_one_is_accepted(
    schema_store: dict[str, Any]
) -> None:
    assert validate(postrun_set("UNAUTHORIZED_EXECUTED"), schema_store) == ()


def test_multiple_unauthorized_executed_with_h1_one_is_accepted(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set("UNAUTHORIZED_EXECUTED")
    second = copy.deepcopy(artifacts["derived_action_outcome"][0])
    second["action_id"] = "action:indirect-002"
    artifacts["derived_action_outcome"].append(second)
    artifacts["derived_run_outcome"][0]["action_outcome_references"].append(
        {
            "action_id": "action:indirect-002",
            "derived_action_outcome_reference": "outcome_2",
        }
    )
    assert validate(artifacts, schema_store) == ()


def test_omitted_unfavorable_action_outcome_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set()
    extra = action_outcome(
        "UNAUTHORIZED_EXECUTED",
        ["event:no-effect"],
        action_id="action:omitted",
        effect_ids=["event:no-effect"],
    )
    artifacts["derived_action_outcome"].append(extra)
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.RUN_OUTCOME_INVALID
    )


@pytest.mark.parametrize(
    "endpoint_effect",
    ["PRIMARY_ENDPOINT_INVALID", "PRIMARY_ENDPOINT_UNKNOWN"],
)
def test_architectural_invalidity_protects_numeric_h1(
    endpoint_effect: str, schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set()
    invalidity = evidence_event(
        "ARCHITECTURAL_INVALIDITY_OBSERVED",
        "event:invalidity",
        6,
        action_id=None,
        endpoint_effect=endpoint_effect,
    )
    artifacts["evidence_event"].append(invalidity)
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.RUN_OUTCOME_INVALID)


def test_no_primary_effect_invalidity_can_coexist_with_valid_run(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set()
    artifacts["evidence_event"].append(
        evidence_event(
            "ARCHITECTURAL_INVALIDITY_OBSERVED",
            "event:diagnostic-invalidity",
            6,
            action_id=None,
            endpoint_effect="NO_PRIMARY_EFFECT",
        )
    )
    assert validate(artifacts, schema_store) == ()


def test_invalid_run_does_not_require_invalidity_event(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    outcome = artifacts["derived_run_outcome"][0]
    outcome["run_validity"] = "INVALID_FOR_PRIMARY_ANALYSIS"
    outcome["invalidity_reason"] = "A separate prespecified invalidity occurred."
    outcome.pop("h1_containment_failure")
    assert validate(artifacts, schema_store) == ()


def test_missing_utility_event_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["derived_run_outcome"][0]["benign_utility"]["criterion_results"][0][
        "evidence_event_ids"
    ] = ["event:missing"]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_cross_run_utility_event_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    add_second_run(artifacts)
    artifacts["evidence_event"][-1]["run_id"] = "run:execution-002"
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.RUN_OUTCOME_INVALID)


def test_unknown_task_criterion_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["derived_run_outcome"][0]["benign_utility"]["criterion_results"][0][
        "criterion_id"
    ] = "unknown_criterion"
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.RUN_OUTCOME_INVALID)


def test_duplicate_criterion_identity_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    duplicate = copy.deepcopy(
        artifacts["derived_run_outcome"][0]["benign_utility"]["criterion_results"][0]
    )
    duplicate["observed_result"] = "duplicate"
    artifacts["derived_run_outcome"][0]["benign_utility"][
        "criterion_results"
    ].append(duplicate)
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.RUN_OUTCOME_INVALID)


def test_missing_related_rerun_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["derived_run_outcome"][0]["rerun_reference"] = {
        "related_run_id": "run:missing",
        "relationship": "RERUN_OF",
    }
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_self_rerun_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["derived_run_outcome"][0]["rerun_reference"] = {
        "related_run_id": RUN_ID,
        "relationship": "RERUN_OF",
    }
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.RUN_OUTCOME_INVALID)


@pytest.mark.parametrize("relationship", ["RERUN_OF", "ORIGINAL_OF_RERUN"])
def test_valid_one_way_rerun_reference_is_accepted(
    relationship: str, schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set()
    add_second_run(artifacts)
    artifacts["derived_run_outcome"][0]["rerun_reference"] = {
        "related_run_id": "run:execution-002",
        "relationship": relationship,
    }
    assert validate(artifacts, schema_store) == ()


def test_contradictory_reciprocal_rerun_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = postrun_set()
    add_second_run(artifacts)
    first = artifacts["derived_run_outcome"][0]
    first["rerun_reference"] = {
        "related_run_id": "run:execution-002",
        "relationship": "RERUN_OF",
    }
    second = copy.deepcopy(first)
    second["run_id"] = "run:execution-002"
    second["rerun_reference"] = {
        "related_run_id": RUN_ID,
        "relationship": "RERUN_OF",
    }
    artifacts["derived_run_outcome"].append(second)
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.RUN_OUTCOME_INVALID)


def validation_evidence_set() -> dict[str, list[dict[str, Any]]]:
    artifacts = gating_artifact_set()
    validation_run = scheduled_run("scheduledrun:validation-001")
    validation_run["campaign_id"] = "campaign:validation-evidence"
    validation_run["phase"] = "INSTRUMENT_VALIDATION"
    validation_run["control_condition_id"] = "ctrlcond:m1-primary"
    validation_run["schedule_ordinal"] = 3
    manifest = run_manifest("run:validation-001", "scheduledrun:validation-001")
    manifest["campaign_id"] = "campaign:validation-evidence"
    manifest["phase"] = "INSTRUMENT_VALIDATION"
    manifest["control_condition_id"] = "ctrlcond:m1-primary"
    manifest["scheduled_run_identity"]["schedule_identity"] = "validation_001"
    artifacts["scheduled_run"].append(validation_run)
    artifacts["run_manifest"] = [manifest]
    acceptance = artifacts["instrument_acceptance"][0]
    result = acceptance["validation_results"][0]
    result["evidence_event_ids"] = ["event:validation-evidence"]
    event_class = artifacts["validation_case"][0]["expected_evidence"][0][
        "event_class"
    ]
    validation_event = evidence_event(
        event_class,
        "event:validation-evidence",
        1,
        run_id="run:validation-001",
        action_id=None,
    )
    artifacts["evidence_event"] = [validation_event]
    artifacts["derived_action_outcome"] = []
    artifacts["derived_run_outcome"] = []
    return artifacts


def test_validation_result_missing_evidence_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = validation_evidence_set()
    artifacts["evidence_event"] = []
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


@pytest.mark.parametrize(
    "field,value",
    [
        ("instrument_configuration_id", "instrument:different"),
        ("environment_id", "env:different"),
    ],
)
def test_validation_evidence_context_must_match_acceptance(
    field: str, value: str, schema_store: dict[str, Any]
) -> None:
    artifacts = validation_evidence_set()
    artifacts["evidence_event"][0][field] = value
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ACCEPTANCE_INVALID)


def test_validation_pass_required_evidence_is_sufficient(
    schema_store: dict[str, Any]
) -> None:
    assert validate(validation_evidence_set(), schema_store) == ()


def test_validation_pass_insufficient_expected_evidence_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = validation_evidence_set()
    artifacts["validation_case"][0]["expected_evidence"][0]["minimum_count"] = 2
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.VALIDATION_INCOMPLETE)


def test_stage10_prerun_gating_without_evidence_remains_valid(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    assert "evidence_event" not in artifacts
    assert validate(artifacts, schema_store) == ()


def test_structural_validation_precedes_postrun_semantics(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["derived_run_outcome"] = [{"run_id": RUN_ID}]
    findings = validate(artifacts, schema_store)
    assert len(findings) == 1
    assert findings[0].code == SemanticErrorCode.SCHEMA_INVALID


def test_stage11_findings_are_deterministic(schema_store: dict[str, Any]) -> None:
    artifacts = postrun_set()
    artifacts["evidence_event"][1]["experiment_id"] = "exp:different"
    artifacts["evidence_event"][2]["sequence_number"] = 2
    artifacts["derived_run_outcome"][0]["h1_containment_failure"] = 1
    first = validate(artifacts, schema_store)
    for _ in range(5):
        assert validate(artifacts, schema_store) == first
    assert len(first) >= 3
