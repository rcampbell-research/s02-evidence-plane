"""Stage 10 tests for deterministic confirmatory-gating semantics."""

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
from tests.schema.test_stage7_contracts import (
    valid_acceptance,
    valid_validation_case,
)
from tests.schema.test_stage8_contracts import (
    valid_capability_evaluation,
    valid_campaign,
    valid_draft_analysis,
    valid_frozen_analysis,
)
from tests.semantic.test_stage9_semantic_validation import (
    agent_condition,
    autonomy,
    control,
    control_condition,
    environment,
    instrument,
    scenario,
    scheduled_run,
    valid_artifact_set,
)


ROOT = Path(__file__).resolve().parents[2]


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


def _acceptance_for(
    phase: str,
    campaign_id: str,
    instrument_artifact: dict[str, Any],
) -> dict[str, Any]:
    state = (
        "ACCEPTED_FOR_PILOT"
        if phase == "PILOT"
        else "ACCEPTED_FOR_CONFIRMATORY"
    )
    acceptance = valid_acceptance(state)
    acceptance["instrument_configuration_id"] = instrument_artifact[
        "instrument_configuration_id"
    ]
    acceptance["instrument_configuration_version"] = instrument_artifact[
        "configuration_version"
    ]
    acceptance["environment_id"] = instrument_artifact["environment_id"]
    acceptance["campaign_id"] = campaign_id
    acceptance["component_versions"] = [
        {
            "component_id": component["component_id"],
            "component_version": component["component_version"],
        }
        for component in instrument_artifact["component_manifest"]
    ]
    return acceptance


def _validation_case_for(instrument_id: str) -> dict[str, Any]:
    case = valid_validation_case("V0")
    case["instrument_configuration_id"] = instrument_id
    return case


def _capability_evaluation(
    state: str = "FROZEN_FOR_CONFIRMATORY_USE",
) -> dict[str, Any]:
    evaluation = valid_capability_evaluation(state, "CATEGORICAL")
    evaluation["evaluated_capability_conditions"] = ["capcond:baseline"]
    evaluation["observed_scores"] = [
        {
            "capability_condition_id": "capcond:baseline",
            "capability_task_id": "structured_reasoning",
            "observed_score": 0.75,
        }
    ]
    return evaluation


def gating_artifact_set(
    phase: str = "CONFIRMATORY",
) -> dict[str, list[dict[str, Any]]]:
    artifacts = valid_artifact_set()
    artifacts["run_manifest"] = []

    m1 = control("control:m1-primary", "M1")
    m3 = control("control:m3-primary", "M3")
    m1_condition = control_condition(
        [m1], condition_id="ctrlcond:m1-primary"
    )
    m3_condition = control_condition(
        [m3], condition_id="ctrlcond:m3-primary"
    )
    artifacts["control"] = [m1, m3]
    artifacts["control_condition"] = [m1_condition, m3_condition]

    campaign = valid_campaign(phase)
    campaign_id = campaign["campaign_id"]
    campaign["scenario_ids"] = ["scenario:protected-access"]
    campaign["agent_condition_ids"] = ["agentcond:baseline"]
    campaign["autonomy_condition_ids"] = ["autonomy:bounded"]
    campaign["environment_id"] = "env:synthetic-lab"
    campaign["instrument_configuration_id"] = "instrument:baseline"

    run_count = 2 if phase == "CONFIRMATORY" else 1
    scheduled: list[dict[str, Any]] = []
    for index in range(run_count):
        run = scheduled_run(f"scheduledrun:unit-{index + 1:03d}")
        run["campaign_id"] = campaign_id
        run["phase"] = phase
        run["schedule_ordinal"] = index + 1
        run["scheduled_configuration_frozen"] = True
        run["control_condition_id"] = (
            "ctrlcond:m1-primary" if index == 0 else "ctrlcond:m3-primary"
        )
        scheduled.append(run)
    campaign["scheduled_run_ids"] = [run["scheduled_run_id"] for run in scheduled]
    campaign["control_condition_ids"] = sorted(
        {run["control_condition_id"] for run in scheduled}
    )

    instrument_artifact = artifacts["instrument_configuration"][0]
    validation_case = _validation_case_for(
        instrument_artifact["instrument_configuration_id"]
    )
    acceptance = _acceptance_for(phase, campaign_id, instrument_artifact)

    artifacts["scheduled_run"] = scheduled
    artifacts["campaign"] = [campaign]
    artifacts["validation_case"] = [validation_case]
    artifacts["instrument_acceptance"] = [acceptance]
    artifacts["capability_evaluation"] = []
    artifacts["analysis_manifest"] = []

    if phase == "CONFIRMATORY":
        evaluation = _capability_evaluation()
        analysis = valid_frozen_analysis("CATEGORICAL")
        analysis["scenario_subset"] = ["scenario:protected-access"]
        analysis["agent_condition_subset"] = ["agentcond:baseline"]
        analysis["sample_size"] = len(scheduled)
        artifacts["capability_evaluation"] = [evaluation]
        artifacts["analysis_manifest"] = [analysis]
    return artifacts


def ordered_capability_set() -> dict[str, list[dict[str, Any]]]:
    artifacts = valid_artifact_set()
    artifacts["agent_model_condition"].append(
        agent_condition("agentcond:advanced", "modelcond:advanced", "capcond:advanced")
    )
    artifacts["capability_evaluation"] = [
        valid_capability_evaluation("FROZEN_FOR_CONFIRMATORY_USE", "ORDERED")
    ]
    return artifacts


def replace_control_layer(
    artifacts: dict[str, list[dict[str, Any]]], control_id: str, layer: str
) -> None:
    replacement = control(control_id, layer)
    artifacts["control"] = [
        replacement if item["control_id"] == control_id else item
        for item in artifacts["control"]
    ]
    for condition in artifacts["control_condition"]:
        for constituent in condition["constituents"]:
            if constituent["control_id"] == control_id:
                constituent["control_version"] = replacement["control_version"]
                constituent["configuration_id"] = replacement["configuration_id"]


def test_stage10_supported_family_set_is_explicit() -> None:
    for family in (
        "capability_evaluation",
        "campaign",
        "validation_case",
        "instrument_acceptance",
        "analysis_manifest",
    ):
        assert family in SUPPORTED_ARTIFACT_FAMILIES
    for family in (
        "evidence_event",
        "derived_action_outcome",
        "derived_run_outcome",
    ):
        assert family in SUPPORTED_ARTIFACT_FAMILIES
    assert "unknown_artifact_family" not in SUPPORTED_ARTIFACT_FAMILIES


@pytest.mark.parametrize("phase", ["PILOT", "CONFIRMATORY"])
def test_minimal_valid_gating_sets_have_no_findings(
    phase: str, schema_store: dict[str, Any]
) -> None:
    assert validate(gating_artifact_set(phase), schema_store) == ()


def test_missing_evaluated_capability_condition_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    evaluation = _capability_evaluation()
    evaluation["evaluated_capability_conditions"] = ["capcond:missing"]
    evaluation["observed_scores"][0]["capability_condition_id"] = "capcond:missing"
    artifacts["capability_evaluation"] = [evaluation]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_score_condition_must_be_declared(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    evaluation = _capability_evaluation()
    evaluation["observed_scores"][0]["capability_condition_id"] = "capcond:other"
    artifacts["capability_evaluation"] = [evaluation]
    assert_code(
        validate(artifacts, schema_store),
        SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
    )


def test_score_task_must_be_declared(schema_store: dict[str, Any]) -> None:
    artifacts = valid_artifact_set()
    evaluation = _capability_evaluation()
    evaluation["observed_scores"][0]["capability_task_id"] = "undeclared_task"
    artifacts["capability_evaluation"] = [evaluation]
    assert_code(
        validate(artifacts, schema_store),
        SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
    )


def test_duplicate_semantic_score_pair_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    evaluation = _capability_evaluation()
    duplicate = copy.deepcopy(evaluation["observed_scores"][0])
    duplicate["observed_score"] = 0.8
    evaluation["observed_scores"].append(duplicate)
    artifacts["capability_evaluation"] = [evaluation]
    assert_code(
        validate(artifacts, schema_store),
        SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
    )


def test_categorical_capability_representation_is_accepted(
    schema_store: dict[str, Any]
) -> None:
    artifacts = valid_artifact_set()
    artifacts["capability_evaluation"] = [_capability_evaluation()]
    assert validate(artifacts, schema_store) == ()


def test_valid_ordered_capability_representation_is_accepted(
    schema_store: dict[str, Any]
) -> None:
    assert validate(ordered_capability_set(), schema_store) == ()


def test_ordering_with_undeclared_condition_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = ordered_capability_set()
    evaluation = artifacts["capability_evaluation"][0]
    evaluation["ordering_result"]["ordered_groups"][1] = ["capcond:missing"]
    assert_code(
        validate(artifacts, schema_store),
        SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
    )


@pytest.mark.parametrize("state", ["COMPLETED", "DRAFT"])
def test_confirmatory_campaign_requires_frozen_capability_evaluation(
    state: str, schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["capability_evaluation"][0]["evaluation_state"] = state
    assert_code(
        validate(artifacts, schema_store),
        SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
    )


def test_confirmatory_frozen_capability_evaluation_is_accepted(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    assert artifacts["capability_evaluation"][0]["evaluation_state"] == (
        "FROZEN_FOR_CONFIRMATORY_USE"
    )
    assert validate(artifacts, schema_store) == ()


def test_campaign_capability_must_be_evaluated(schema_store: dict[str, Any]) -> None:
    artifacts = gating_artifact_set()
    artifacts["agent_model_condition"].append(
        agent_condition("agentcond:advanced", "modelcond:advanced", "capcond:advanced")
    )
    evaluation = artifacts["capability_evaluation"][0]
    evaluation["evaluated_capability_conditions"] = ["capcond:advanced"]
    evaluation["observed_scores"][0]["capability_condition_id"] = "capcond:advanced"
    assert_code(
        validate(artifacts, schema_store),
        SemanticErrorCode.CAPABILITY_EVALUATION_INVALID,
        family="campaign",
    )


def test_missing_campaign_scheduled_run_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["scheduled_run"].pop()
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.CAMPAIGN_INVALID)


@pytest.mark.parametrize(
    "field,value",
    [
        ("experiment_id", "exp:different"),
        ("campaign_id", "campaign:different"),
        ("phase", "PILOT"),
        ("environment_id", "env:different"),
        ("instrument_configuration_id", "instrument:different"),
    ],
)
def test_campaign_and_scheduled_run_fields_must_match(
    field: str, value: Any, schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["scheduled_run"][0][field] = value
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.CAMPAIGN_INVALID)


@pytest.mark.parametrize(
    "run_field,campaign_field,value",
    [
        ("scenario_id", "scenario_ids", "scenario:other"),
        ("agent_condition_id", "agent_condition_ids", "agentcond:other"),
        ("autonomy_condition_id", "autonomy_condition_ids", "autonomy:other"),
        ("control_condition_id", "control_condition_ids", "ctrlcond:other"),
    ],
)
def test_scheduled_run_factor_must_be_declared_by_campaign(
    run_field: str,
    campaign_field: str,
    value: str,
    schema_store: dict[str, Any],
) -> None:
    artifacts = gating_artifact_set()
    artifacts["scheduled_run"][0][run_field] = value
    assert value not in artifacts["campaign"][0][campaign_field]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.CAMPAIGN_INVALID)


def test_unlisted_active_campaign_run_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = gating_artifact_set()
    extra = copy.deepcopy(artifacts["scheduled_run"][0])
    extra["scheduled_run_id"] = "scheduledrun:unlisted"
    extra["schedule_ordinal"] = 3
    artifacts["scheduled_run"].append(extra)
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.CAMPAIGN_INVALID)


def test_duplicate_schedule_ordinal_is_rejected(schema_store: dict[str, Any]) -> None:
    artifacts = gating_artifact_set()
    artifacts["scheduled_run"][1]["schedule_ordinal"] = 1
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.CAMPAIGN_INVALID)


def test_valid_campaign_schedule_closure_is_accepted(
    schema_store: dict[str, Any]
) -> None:
    assert validate(gating_artifact_set(), schema_store) == ()


def test_missing_compatible_acceptance_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["instrument_acceptance"] = []
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ACCEPTANCE_INVALID)


def test_multiple_compatible_acceptances_are_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["instrument_acceptance"].append(
        copy.deepcopy(artifacts["instrument_acceptance"][0])
    )
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ACCEPTANCE_INVALID)


@pytest.mark.parametrize(
    "field,value",
    [
        ("instrument_configuration_id", "instrument:wrong"),
        ("environment_id", "env:wrong"),
    ],
)
def test_acceptance_must_match_exact_instrument_environment(
    field: str, value: str, schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["instrument_acceptance"][0][field] = value
    findings = validate(artifacts, schema_store)
    assert any(
        finding.code
        in {SemanticErrorCode.ACCEPTANCE_INVALID, SemanticErrorCode.REFERENCE_INVALID}
        for finding in findings
    )


@pytest.mark.parametrize("state", ["ACCEPTED_FOR_PILOT", "REJECTED"])
def test_nonconfirmatory_acceptance_cannot_gate_confirmatory_campaign(
    state: str, schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    acceptance = artifacts["instrument_acceptance"][0]
    acceptance["acceptance_state"] = state
    if state == "ACCEPTED_FOR_PILOT":
        acceptance["accepted_for_phase"] = "PILOT"
    else:
        acceptance.pop("accepted_for_phase")
        acceptance["unresolved_conditions"] = ["Rejected synthetic condition."]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ACCEPTANCE_INVALID)


def test_valid_confirmatory_acceptance_is_accepted(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    assert artifacts["instrument_acceptance"][0]["acceptance_state"] == (
        "ACCEPTED_FOR_CONFIRMATORY"
    )
    assert validate(artifacts, schema_store) == ()


def test_acceptance_requires_every_configured_component(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["instrument_acceptance"][0]["component_versions"].pop()
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ACCEPTANCE_INVALID)


def test_acceptance_component_version_must_match(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["instrument_acceptance"][0]["component_versions"][0][
        "component_version"
    ] = "0.2.0"
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.VERSION_INVALID)


def test_acceptance_cannot_introduce_component(schema_store: dict[str, Any]) -> None:
    artifacts = gating_artifact_set()
    artifacts["instrument_acceptance"][0]["component_versions"].append(
        {"component_id": "undeclared_component", "component_version": "0.1.0"}
    )
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ACCEPTANCE_INVALID)


def test_validation_result_case_must_exist(schema_store: dict[str, Any]) -> None:
    artifacts = gating_artifact_set()
    artifacts["validation_case"] = []
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.REFERENCE_INVALID)


def test_validation_result_case_version_must_match(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["instrument_acceptance"][0]["validation_results"][0][
        "validation_case_version"
    ] = "0.2.0"
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.VERSION_INVALID)


def test_validation_result_applicability_must_match(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["instrument_acceptance"][0]["validation_results"][0][
        "applicability_class"
    ] = "OPTIONAL_DIAGNOSTIC"
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ACCEPTANCE_INVALID)


def test_omitted_mandatory_global_validation_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    second = valid_validation_case("V1")
    second["instrument_configuration_id"] = "instrument:baseline"
    artifacts["validation_case"].append(second)
    assert_code(
        validate(artifacts, schema_store), SemanticErrorCode.VALIDATION_INCOMPLETE
    )


@pytest.mark.parametrize(
    "result_state", ["VALIDATION_FAIL", "VALIDATION_INCONCLUSIVE"]
)
def test_mandatory_global_failure_or_inconclusive_blocks_acceptance(
    result_state: str, schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["instrument_acceptance"][0]["validation_results"][0][
        "result_state"
    ] = result_state
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ACCEPTANCE_INVALID)


def test_mandatory_global_pass_is_accepted(schema_store: dict[str, Any]) -> None:
    artifacts = gating_artifact_set()
    assert artifacts["instrument_acceptance"][0]["validation_results"][0][
        "result_state"
    ] == "VALIDATION_PASS"
    assert validate(artifacts, schema_store) == ()


def test_omitted_conditional_completeness_is_explicitly_deferred(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    conditional = valid_validation_case("V1")
    conditional["instrument_configuration_id"] = "instrument:baseline"
    conditional["applicability_class"] = "MANDATORY_CONDITIONAL"
    conditional["applicable_scenario_families"] = ["S01"]
    conditional["applicable_control_layers"] = ["M3"]
    artifacts["validation_case"].append(conditional)
    assert validate(artifacts, schema_store) == ()


def test_opaque_acceptance_reference_is_not_falsely_content_resolved(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["campaign"][0]["instrument_acceptance_reference"] = (
        "acceptance:opaque-reference-with-no-contract-id"
    )
    assert validate(artifacts, schema_store) == ()


def test_missing_confirmatory_analysis_is_rejected(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["analysis_manifest"] = []
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ANALYSIS_INVALID)


def test_draft_analysis_cannot_gate_confirmatory_campaign(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    draft = valid_draft_analysis()
    draft["analysis_configuration_id"] = "analysis:confirmatory-primary"
    artifacts["analysis_manifest"] = [draft]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ANALYSIS_INVALID)


def test_frozen_analysis_is_accepted(schema_store: dict[str, Any]) -> None:
    assert validate(gating_artifact_set(), schema_store) == ()


@pytest.mark.parametrize(
    "field,condition_id",
    [
        ("primary_m1_control_condition_id", "ctrlcond:m1-primary"),
        ("primary_m3_control_condition_id", "ctrlcond:m3-primary"),
    ],
)
def test_missing_primary_comparator_is_rejected(
    field: str, condition_id: str, schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["control_condition"] = [
        item
        for item in artifacts["control_condition"]
        if item["control_condition_id"] != condition_id
    ]
    findings = validate(artifacts, schema_store)
    assert any(
        finding.code
        in {SemanticErrorCode.REFERENCE_INVALID, SemanticErrorCode.ANALYSIS_INVALID}
        for finding in findings
    )


@pytest.mark.parametrize("layer", ["M2", "M3"])
def test_primary_m1_comparator_must_be_pure_m1(
    layer: str, schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    replace_control_layer(artifacts, "control:m1-primary", layer)
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ANALYSIS_INVALID)


def test_primary_m3_comparator_cannot_be_m1(schema_store: dict[str, Any]) -> None:
    artifacts = gating_artifact_set()
    replace_control_layer(artifacts, "control:m3-primary", "M1")
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ANALYSIS_INVALID)


def test_valid_declarative_m3_comparator_is_accepted(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    assert validate(artifacts, schema_store) == ()


def test_primary_comparator_must_be_in_campaign(schema_store: dict[str, Any]) -> None:
    artifacts = gating_artifact_set()
    alternate = control_condition(
        [artifacts["control"][0]], condition_id="ctrlcond:m1-alternate"
    )
    artifacts["control_condition"].append(alternate)
    artifacts["analysis_manifest"][0]["primary_m1_control_condition_id"] = (
        "ctrlcond:m1-alternate"
    )
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ANALYSIS_INVALID)


def test_analysis_scenario_must_be_in_campaign(schema_store: dict[str, Any]) -> None:
    artifacts = gating_artifact_set()
    artifacts["scenario"].append(scenario("scenario:other"))
    artifacts["analysis_manifest"][0]["scenario_subset"] = ["scenario:other"]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ANALYSIS_INVALID)


def test_analysis_agent_must_be_in_campaign(schema_store: dict[str, Any]) -> None:
    artifacts = gating_artifact_set()
    artifacts["agent_model_condition"].append(
        agent_condition("agentcond:other", "modelcond:other", "capcond:other")
    )
    artifacts["analysis_manifest"][0]["agent_condition_subset"] = [
        "agentcond:other"
    ]
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ANALYSIS_INVALID)


def test_analysis_capability_representation_must_match_evaluation(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["analysis_manifest"][0]["capability_representation"] = {
        "representation": "ORDERED",
        "capability_evaluation_reference": "cond:capability-evaluation-baseline",
        "contrast_definition": "Use the independently frozen ordering.",
        "containment_outcomes_used": False,
    }
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ANALYSIS_INVALID)


@pytest.mark.parametrize(
    "missing_condition", ["ctrlcond:m1-primary", "ctrlcond:m3-primary"]
)
def test_primary_comparators_must_appear_in_scheduled_runs(
    missing_condition: str, schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    replacement = (
        "ctrlcond:m3-primary"
        if missing_condition == "ctrlcond:m1-primary"
        else "ctrlcond:m1-primary"
    )
    for run in artifacts["scheduled_run"]:
        if run["control_condition_id"] == missing_condition:
            run["control_condition_id"] = replacement
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.ANALYSIS_INVALID)


def test_frozen_sample_size_must_equal_campaign_schedule(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["analysis_manifest"][0]["sample_size"] = 3
    assert_code(
        validate(artifacts, schema_store),
        SemanticErrorCode.ANALYSIS_INVALID,
        path="/sample_size",
    )


def test_structured_sample_size_count_is_supported(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["analysis_manifest"][0]["sample_size"] = {
        "scheduled_run_count": 2,
        "determination_reference": "frozen_sample_size",
        "assumption_summary": "Two synthetic scheduled units for this fixture.",
    }
    assert validate(artifacts, schema_store) == ()


@pytest.mark.parametrize(
    "campaign_phase,scheduled_phase",
    [("PILOT", "CONFIRMATORY"), ("CONFIRMATORY", "PILOT")],
)
def test_pilot_confirmatory_phase_separation(
    campaign_phase: str,
    scheduled_phase: str,
    schema_store: dict[str, Any],
) -> None:
    artifacts = gating_artifact_set(campaign_phase)
    artifacts["scheduled_run"][0]["phase"] = scheduled_phase
    assert_code(validate(artifacts, schema_store), SemanticErrorCode.CAMPAIGN_INVALID)


def test_unknown_family_remains_explicitly_unsupported(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    artifacts["unknown_artifact_family"] = [{"synthetic_id": "unsupported"}]
    assert_code(
        validate(artifacts, schema_store),
        SemanticErrorCode.UNSUPPORTED_ARTIFACT_FAMILY,
        family="unknown_artifact_family",
    )


def test_structural_validation_precedes_stage10_semantics(
    schema_store: dict[str, Any]
) -> None:
    artifacts = {"campaign": [{"campaign_id": "campaign:malformed"}]}
    findings = validate(artifacts, schema_store)
    assert len(findings) == 1
    assert findings[0].code == SemanticErrorCode.SCHEMA_INVALID


def test_stage10_validation_does_not_mutate_input(
    schema_store: dict[str, Any]
) -> None:
    artifacts = gating_artifact_set()
    original = copy.deepcopy(artifacts)
    validate(artifacts, schema_store)
    assert artifacts == original


def test_stage10_findings_are_deterministic(schema_store: dict[str, Any]) -> None:
    artifacts = gating_artifact_set()
    artifacts["capability_evaluation"][0]["evaluation_state"] = "COMPLETED"
    artifacts["scheduled_run"][1]["schedule_ordinal"] = 1
    artifacts["analysis_manifest"][0]["sample_size"] = 3
    first = validate(artifacts, schema_store)
    for _ in range(5):
        assert validate(artifacts, schema_store) == first
    assert len(first) >= 3
