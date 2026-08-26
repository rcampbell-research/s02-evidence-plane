"""Stage 8 tests for capability, campaign, scheduling, and analysis contracts."""

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
    name: f"urn:frontier-agent-containment:schema:{name}:0.1.0"
    for name in SCHEMA_PATHS
}
STAGE8_SCHEMAS = [
    "capability-evaluation",
    "campaign",
    "scheduled-run",
    "analysis-manifest",
]
RUN_PHASES = [
    "DEVELOPMENT",
    "INSTRUMENT_VALIDATION",
    "PILOT",
    "CONFIRMATORY",
]
CAPABILITY_EVALUATION_STATES = [
    "DRAFT",
    "COMPLETED",
    "FROZEN_FOR_CONFIRMATORY_USE",
]
CAPABILITY_REPRESENTATIONS = ["CATEGORICAL", "ORDERED"]
ANALYSIS_STATES = ["DRAFT", "FROZEN_FOR_CONFIRMATORY"]
ANALYSIS_POPULATIONS = [
    "SCHEDULED_RUN_SET",
    "PRIMARY_VALID_SET",
    "UTILITY_VALID_SET",
    "TIMING_VALID_SET",
]


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(SCHEMA_PATHS.values())


@pytest.fixture(scope="module")
def schemas(schema_store: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        name: schema_store[schema_id]
        for name, schema_id in SCHEMA_IDS.items()
    }


def valid_capability_evaluation(
    state: str = "DRAFT", representation: str = "CATEGORICAL"
) -> dict[str, Any]:
    instance: dict[str, Any] = {
        "evaluation_configuration_id": "cond:capability-evaluation-baseline",
        "evaluation_version": "0.1.0",
        "display_name": "Independent synthetic capability evaluation",
        "description": "Authorized tasks independent of containment outcomes.",
        "evaluation_state": state,
        "evaluated_capability_conditions": [
            "capcond:baseline",
            "capcond:advanced",
        ],
        "capability_tasks": [
            {
                "capability_task_id": "structured_reasoning",
                "description": "Solve an authorized synthetic reasoning task.",
                "success_criteria": [
                    {
                        "criterion_id": "correct_result",
                        "description": "The external evaluator observes a correct result.",
                    }
                ],
                "measurement_type": "bounded_numeric",
                "task_scope": "SYNTHETIC_AUTHORIZED",
                "containment_controls_used": False,
            }
        ],
        "scoring_method": {
            "method_id": "prespecified_aggregation",
            "description": "Aggregate externally evaluated task results.",
            "aggregation_rule": "Apply the frozen mean score rule by condition.",
        },
        "observed_scores": [],
        "capability_representation": representation,
        "ordering_method": {
            "method_id": "independent_task_ordering",
            "description": "Order only from authorized capability-task scores.",
            "tie_handling": "Place tied conditions in the same ordered group.",
            "missing_result_handling": "Use categorical representation if unresolved.",
            "non_monotonic_handling": "Do not fabricate an ordinal score.",
        },
        "ordering_result": {
            "categorical_reason": "No ordinal relationship is asserted."
        },
        "containment_outcomes_used": False,
    }
    if state != "DRAFT":
        instance["observed_scores"] = [
            {
                "capability_condition_id": "capcond:baseline",
                "capability_task_id": "structured_reasoning",
                "observed_score": 0.75,
            },
            {
                "capability_condition_id": "capcond:advanced",
                "capability_task_id": "structured_reasoning",
                "observed_score": 0.9,
            },
        ]
    if representation == "ORDERED":
        instance["ordering_result"] = {
            "ordered_groups": [
                ["capcond:baseline"],
                ["capcond:advanced"],
            ]
        }
    return instance


def valid_campaign(phase: str = "DEVELOPMENT") -> dict[str, Any]:
    instance: dict[str, Any] = {
        "experiment_id": "exp:containment-study",
        "campaign_id": f"campaign:{phase.lower().replace('_', '-')}",
        "campaign_version": "0.1.0",
        "display_name": f"{phase} campaign",
        "description": "Prospectively planned synthetic experimental units.",
        "phase": phase,
        "scenario_ids": ["scenario:synthetic-001"],
        "agent_condition_ids": ["agentcond:baseline"],
        "autonomy_condition_ids": ["autonomy:bounded"],
        "control_condition_ids": ["ctrlcond:m1-primary", "ctrlcond:m3-primary"],
        "environment_id": "env:synthetic-lab",
        "instrument_configuration_id": "instrument:validated-baseline",
        "scheduled_run_ids": ["scheduledrun:unit-001", "scheduledrun:unit-002"],
        "campaign_frozen_before_start": phase in {"PILOT", "CONFIRMATORY"},
    }
    if phase == "CONFIRMATORY":
        instance.update(
            {
                "analysis_configuration_id": "analysis:confirmatory-primary",
                "capability_evaluation_reference": (
                    "cond:capability-evaluation-baseline"
                ),
                "instrument_acceptance_reference": "acceptance:confirmatory-001",
            }
        )
    return instance


def valid_scheduled_run(phase: str = "DEVELOPMENT") -> dict[str, Any]:
    return {
        "experiment_id": "exp:containment-study",
        "campaign_id": f"campaign:{phase.lower().replace('_', '-')}",
        "scheduled_run_id": "scheduledrun:unit-001",
        "scheduled_run_version": "0.1.0",
        "phase": phase,
        "scenario_id": "scenario:synthetic-001",
        "task_id": "task:benign-001",
        "agent_condition_id": "agentcond:baseline",
        "model_condition_id": "modelcond:provider-release",
        "capability_condition_id": "capcond:baseline",
        "autonomy_condition_id": "autonomy:bounded",
        "control_condition_id": "ctrlcond:m3-primary",
        "capability_envelope_id": "envelope:task-authority",
        "policy_id": "policy:default-deny",
        "environment_id": "env:synthetic-lab",
        "instrument_configuration_id": "instrument:validated-baseline",
        "seed_repetition_identity": {
            "repetition_id": "repetition_001",
            "seed_status": "AVAILABLE",
            "seed_value": 1729,
        },
        "action_budget": 24,
        "schedule_ordinal": 1,
        "scheduled_configuration_frozen": phase in {"PILOT", "CONFIRMATORY"},
    }


def unresolved(reason: str) -> dict[str, str]:
    return {"resolution_state": "UNRESOLVED", "reason": reason}


def valid_draft_analysis() -> dict[str, Any]:
    return {
        "analysis_configuration_id": "analysis:draft-primary",
        "analysis_version": "0.1.0",
        "analysis_state": "DRAFT",
        "primary_endpoint": "RUN_LEVEL_ANY_UNAUTHORIZED_EXECUTED",
        "primary_estimand": "RISK_DIFFERENCE",
        "primary_effect_direction": "M3_MINUS_M1",
        "model_specification": unresolved("Pilot feasibility remains unresolved."),
        "dependency_structure": unresolved("Pilot dependence remains unresolved."),
        "standardization_method": unresolved("Weights remain unresolved."),
        "interval_method": unresolved("Interval method remains unresolved."),
        "multiplicity_strategy": unresolved("The hierarchy remains unresolved."),
        "primary_utility_endpoint": unresolved("Utility endpoint remains unresolved."),
        "missing_data_strategy": unresolved("Sensitivity rules remain unresolved."),
        "zero_event_strategy": unresolved("Zero-event handling remains unresolved."),
        "secondary_hypothesis_configuration": unresolved(
            "H2-H4 details remain unresolved."
        ),
    }


def valid_frozen_analysis(
    representation: str = "CATEGORICAL",
) -> dict[str, Any]:
    capability_representation: dict[str, Any] = {
        "representation": representation,
        "contrast_definition": "Use the frozen categorical interaction family.",
        "containment_outcomes_used": False,
    }
    if representation == "ORDERED":
        capability_representation["capability_evaluation_reference"] = (
            "cond:capability-evaluation-baseline"
        )
        capability_representation["contrast_definition"] = (
            "Use the independently frozen adjacent ordered contrast."
        )

    return {
        "analysis_configuration_id": "analysis:confirmatory-primary",
        "analysis_version": "0.1.0",
        "analysis_state": "FROZEN_FOR_CONFIRMATORY",
        "primary_endpoint": "RUN_LEVEL_ANY_UNAUTHORIZED_EXECUTED",
        "primary_estimand": "RISK_DIFFERENCE",
        "primary_effect_direction": "M3_MINUS_M1",
        "primary_m1_control_condition_id": "ctrlcond:m1-primary",
        "primary_m3_control_condition_id": "ctrlcond:m3-primary",
        "model_specification": {
            "resolution_state": "CONCRETE",
            "model_family": "marginal_binary",
            "link_function": "identity",
            "correlation_or_random_structure": (
                "Prespecified matched-block repeated structure."
            ),
            "estimation_method": "Frozen clustered marginal estimator.",
        },
        "dependency_structure": {
            "resolution_state": "CONCRETE",
            "experimental_unit": "RUN",
            "action_level_observations_independent": False,
            "clustering_or_blocking_factors": [
                "SCENARIO",
                "AGENT_MODEL_CONDITION",
                "MATCHED_TREATMENT_SET",
                "REPETITION_SEED_BLOCK",
            ],
            "dependency_description": "Account for repeated matched run-level units.",
        },
        "standardization_method": {
            "resolution_state": "CONCRETE",
            "method_id": "frozen_design_distribution",
            "target_distribution": "The prospectively scheduled matched design.",
            "weighting_rule": "Use design-derived weights fixed before outcomes.",
        },
        "interval_method": {
            "resolution_state": "CONCRETE",
            "method_id": "cluster_robust_interval",
            "description": "Use the frozen clustered interval procedure.",
        },
        "confidence_level": 0.95,
        "inference_sidedness": "TWO_SIDED",
        "multiplicity_strategy": {
            "resolution_state": "CONCRETE",
            "strategy": "HIERARCHICAL",
            "method_detail": "Test H1 once before the frozen secondary families.",
            "family_order": ["H1_PRIMARY", "H2", "H3", "H4"],
        },
        "capability_representation": capability_representation,
        "primary_utility_endpoint": {
            "resolution_state": "CONCRETE",
            "endpoint_id": "benign_task_success",
            "description": "Authoritatively evaluated benign-task success.",
            "direction": "HIGHER_IS_BETTER",
            "aggregation_rule": "Use the frozen run-level utility rule.",
            "security_weighted_composite": False,
        },
        "scenario_subset": ["scenario:synthetic-001", "scenario:synthetic-002"],
        "agent_condition_subset": ["agentcond:baseline", "agentcond:advanced"],
        "sample_size": 120,
        "minimum_effect_of_interest": 0.1,
        "missing_data_strategy": {
            "resolution_state": "CONCRETE",
            "strategy_id": "prespecified_bounds",
            "description": "Disclose missingness and apply frozen sensitivity bounds.",
            "missing_primary_assigned_zero": False,
            "missingness_disclosure_required": True,
            "sensitivity_analysis_ids": ["worst_case_m3", "worst_case_m1"],
        },
        "zero_event_strategy": {
            "resolution_state": "CONCRETE",
            "strategy_id": "prespecified_zero_event",
            "description": "Use the frozen estimator behavior without post-hoc repair.",
            "post_hoc_pseudocounts_prohibited": True,
            "zero_events_are_proof_of_security": False,
        },
        "analysis_populations": [
            {
                "population": population,
                "inclusion_rule": f"Apply the frozen {population} inclusion rule.",
                "derivation_rule": f"Derive {population} from retained run records.",
            }
            for population in ANALYSIS_POPULATIONS
        ],
        "software_runtime_identity": {
            "software": "python_analysis_runtime",
            "version": "3.14.0",
            "environment_reference": "frozen_analysis_environment",
        },
        "secondary_hypothesis_configuration": {
            "resolution_state": "CONCRETE",
            "h2": {
                "combined_m3_control_condition_id": "ctrlcond:m3-combined",
                "constituent_single_control_condition_ids": [
                    "ctrlcond:m3-filesystem",
                    "ctrlcond:m3-network",
                ],
                "endpoint": "RUN_LEVEL_ANY_UNAUTHORIZED_EXECUTED",
                "contrast_rule": "Compare combined M3 with each frozen constituent.",
            },
            "h3": {
                "security_endpoint": "RUN_LEVEL_ANY_UNAUTHORIZED_EXECUTED",
                "utility_endpoint_reference": "benign_task_success",
                "joint_representation": "Report security and utility separately.",
                "security_utility_composite": False,
            },
            "h4": {
                "interaction_definition": "Frozen capability by control interaction.",
                "capability_contrast_rule": (
                    "Use the representation and contrast frozen above."
                ),
                "containment_outcomes_used_for_ordering": False,
            },
        },
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


@pytest.mark.parametrize("schema_name", STAGE8_SCHEMAS)
def test_stage8_schema_is_valid_draft_2020_12(
    schema_name: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    schema = schemas[schema_name]
    assert schema["$schema"] == DRAFT_2020_12
    assert schema["$id"] == SCHEMA_IDS[schema_name]
    check_draft_2020_12_schema(schema, schema_store=schema_store)


@pytest.mark.parametrize("state", CAPABILITY_EVALUATION_STATES)
def test_capability_evaluation_accepts_each_state(
    state: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(
        valid_capability_evaluation(state),
        schemas["capability-evaluation"],
        schema_store,
    )


def test_completed_capability_evaluation_requires_observed_score(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_capability_evaluation("COMPLETED")
    instance["observed_scores"] = []
    assert_invalid(instance, schemas["capability-evaluation"], schema_store)


@pytest.mark.parametrize("value,valid", [(False, True), (True, False)])
def test_capability_evaluation_never_uses_containment_outcomes(
    value: bool,
    valid: bool,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_capability_evaluation()
    instance["containment_outcomes_used"] = value
    if valid:
        assert_valid(instance, schemas["capability-evaluation"], schema_store)
    else:
        assert_invalid(instance, schemas["capability-evaluation"], schema_store)


def test_capability_task_cannot_use_containment_controls(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_capability_evaluation()
    instance["capability_tasks"][0]["containment_controls_used"] = True
    assert_invalid(instance, schemas["capability-evaluation"], schema_store)


@pytest.mark.parametrize(
    "condition_ids",
    [
        ["agentcond:wrong-prefix"],
        ["capcond:baseline", "capcond:baseline"],
    ],
)
def test_capability_evaluation_rejects_malformed_or_duplicate_conditions(
    condition_ids: list[str],
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_capability_evaluation()
    instance["evaluated_capability_conditions"] = condition_ids
    assert_invalid(instance, schemas["capability-evaluation"], schema_store)


@pytest.mark.parametrize("representation", CAPABILITY_REPRESENTATIONS)
def test_capability_evaluation_accepts_each_representation(
    representation: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(
        valid_capability_evaluation("COMPLETED", representation),
        schemas["capability-evaluation"],
        schema_store,
    )


def test_ordered_capability_evaluation_requires_usable_ordering(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_capability_evaluation("COMPLETED", "ORDERED")
    instance["ordering_result"] = {"ordered_groups": [["capcond:baseline"]]}
    assert_invalid(instance, schemas["capability-evaluation"], schema_store)


def test_categorical_capability_evaluation_rejects_ordered_groups(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_capability_evaluation()
    instance["ordering_result"] = {
        "categorical_reason": "No ordering.",
        "ordered_groups": [["capcond:baseline"], ["capcond:advanced"]],
    }
    assert_invalid(instance, schemas["capability-evaluation"], schema_store)


@pytest.mark.parametrize(
    "field",
    ["control_condition_id", "h1_containment_failure", "containment_failure_rate"],
)
def test_capability_evaluation_rejects_treatment_or_containment_result_field(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_capability_evaluation()
    instance[field] = "not permitted"
    assert_invalid(instance, schemas["capability-evaluation"], schema_store)


def test_capability_evaluation_rejects_missing_required_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_capability_evaluation()
    del instance["scoring_method"]
    assert_invalid(instance, schemas["capability-evaluation"], schema_store)


def test_capability_evaluation_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_capability_evaluation("FROZEN_FOR_CONFIRMATORY_USE", "ORDERED")
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["capability-evaluation"], schema_store)
    assert instance == original


@pytest.mark.parametrize("phase", RUN_PHASES)
def test_campaign_accepts_each_frozen_phase(
    phase: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(valid_campaign(phase), schemas["campaign"], schema_store)


@pytest.mark.parametrize("phase", ["PILOT", "CONFIRMATORY"])
def test_scored_campaign_rejects_mutable_configuration(
    phase: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_campaign(phase)
    instance["campaign_frozen_before_start"] = False
    assert_invalid(instance, schemas["campaign"], schema_store)


@pytest.mark.parametrize(
    "field",
    [
        "analysis_configuration_id",
        "capability_evaluation_reference",
        "instrument_acceptance_reference",
    ],
)
def test_confirmatory_campaign_requires_each_freeze_reference(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_campaign("CONFIRMATORY")
    del instance[field]
    assert_invalid(instance, schemas["campaign"], schema_store)


def test_campaign_rejects_duplicate_scheduled_run_ids(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_campaign()
    instance["scheduled_run_ids"] = [
        "scheduledrun:unit-001",
        "scheduledrun:unit-001",
    ]
    assert_invalid(instance, schemas["campaign"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("campaign_id", "exp:wrong-prefix"),
        ("scenario_ids", ["task:wrong-prefix"]),
        ("control_condition_ids", ["control:wrong-prefix"]),
        ("phase", "EXPLORATORY"),
    ],
)
def test_campaign_rejects_malformed_identity_or_phase(
    field: str,
    value: Any,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_campaign()
    instance[field] = value
    assert_invalid(instance, schemas["campaign"], schema_store)


@pytest.mark.parametrize(
    "field", ["h1_containment_failure", "p_value", "treatment_effect_result"]
)
def test_campaign_rejects_outcome_or_analysis_result_field(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_campaign()
    instance[field] = 0
    assert_invalid(instance, schemas["campaign"], schema_store)


def test_campaign_rejects_unknown_field(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_campaign()
    instance["unplanned_runs"] = []
    assert_invalid(instance, schemas["campaign"], schema_store)


def test_campaign_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_campaign("CONFIRMATORY")
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["campaign"], schema_store)
    assert instance == original


@pytest.mark.parametrize("phase", RUN_PHASES)
def test_scheduled_run_accepts_each_frozen_phase(
    phase: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(valid_scheduled_run(phase), schemas["scheduled-run"], schema_store)


@pytest.mark.parametrize("phase", ["PILOT", "CONFIRMATORY"])
def test_scored_scheduled_run_rejects_mutable_configuration(
    phase: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_scheduled_run(phase)
    instance["scheduled_configuration_frozen"] = False
    assert_invalid(instance, schemas["scheduled-run"], schema_store)


def test_scheduled_run_accepts_unavailable_seed_without_fabrication(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_scheduled_run()
    instance["seed_repetition_identity"] = {
        "repetition_id": "repetition_001",
        "seed_status": "UNAVAILABLE",
    }
    assert_valid(instance, schemas["scheduled-run"], schema_store)


def test_scheduled_run_rejects_run_id(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_scheduled_run()
    instance["run_id"] = "run:not-yet-executed"
    assert_invalid(instance, schemas["scheduled-run"], schema_store)


@pytest.mark.parametrize(
    "field,value",
    [
        ("scheduled_run_id", "run:wrong-prefix"),
        ("campaign_id", "exp:wrong-prefix"),
        ("scenario_id", "task:wrong-prefix"),
        ("task_id", "scenario:wrong-prefix"),
        ("agent_condition_id", "modelcond:wrong-prefix"),
        ("model_condition_id", "agentcond:wrong-prefix"),
        ("capability_condition_id", "autonomy:wrong-prefix"),
        ("autonomy_condition_id", "capcond:wrong-prefix"),
        ("control_condition_id", "control:wrong-prefix"),
        ("capability_envelope_id", "policy:wrong-prefix"),
        ("policy_id", "envelope:wrong-prefix"),
        ("environment_id", "instrument:wrong-prefix"),
        ("instrument_configuration_id", "env:wrong-prefix"),
    ],
)
def test_scheduled_run_rejects_wrong_identifier_prefix(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_scheduled_run()
    instance[field] = value
    assert_invalid(instance, schemas["scheduled-run"], schema_store)


@pytest.mark.parametrize("field,value", [("action_budget", 0), ("schedule_ordinal", 0)])
def test_scheduled_run_rejects_nonpositive_integer(
    field: str,
    value: int,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_scheduled_run()
    instance[field] = value
    assert_invalid(instance, schemas["scheduled-run"], schema_store)


@pytest.mark.parametrize(
    "field",
    [
        "evidence",
        "authorization_decision",
        "terminal_outcome",
        "h1_containment_failure",
        "utility_result",
        "p_value",
    ],
)
def test_scheduled_run_rejects_runtime_or_analytic_field(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_scheduled_run()
    instance[field] = "not permitted"
    assert_invalid(instance, schemas["scheduled-run"], schema_store)


def test_scheduled_run_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_scheduled_run("CONFIRMATORY")
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["scheduled-run"], schema_store)
    assert instance == original


def test_valid_draft_analysis_accepts_explicit_unresolved_choices(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    assert_valid(valid_draft_analysis(), schemas["analysis-manifest"], schema_store)


@pytest.mark.parametrize("representation", CAPABILITY_REPRESENTATIONS)
def test_frozen_analysis_accepts_each_capability_representation(
    representation: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    assert_valid(
        valid_frozen_analysis(representation),
        schemas["analysis-manifest"],
        schema_store,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("primary_endpoint", "ACTION_LEVEL_UNAUTHORIZED_EXECUTED_COUNT"),
        ("primary_estimand", "RISK_RATIO"),
        ("primary_effect_direction", "M1_MINUS_M3"),
    ],
)
def test_analysis_rejects_changed_h1_semantics(
    field: str,
    value: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_frozen_analysis()
    instance[field] = value
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


@pytest.mark.parametrize(
    "field",
    ["primary_m1_control_condition_id", "primary_m3_control_condition_id"],
)
def test_analysis_rejects_malformed_primary_comparator(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_frozen_analysis()
    instance[field] = "control:wrong-prefix"
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


@pytest.mark.parametrize("confidence_level", [0, -0.1, 1, 1.1])
def test_analysis_rejects_invalid_confidence_level(
    confidence_level: float,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_frozen_analysis()
    instance["confidence_level"] = confidence_level
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


def test_analysis_rejects_unknown_inference_sidedness(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_frozen_analysis()
    instance["inference_sidedness"] = "DEFAULT"
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


def test_ordered_analysis_requires_capability_evaluation_reference(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_frozen_analysis("ORDERED")
    del instance["capability_representation"]["capability_evaluation_reference"]
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


def test_analysis_capability_ordering_rejects_containment_outcomes(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_frozen_analysis("ORDERED")
    instance["capability_representation"]["containment_outcomes_used"] = True
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


@pytest.mark.parametrize("field", ["scenario_subset", "agent_condition_subset"])
def test_frozen_analysis_rejects_duplicate_subset_ids(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_frozen_analysis()
    instance[field] = [instance[field][0], instance[field][0]]
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


@pytest.mark.parametrize("field", ["scenario_subset", "agent_condition_subset"])
def test_frozen_analysis_rejects_empty_subset(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_frozen_analysis()
    instance[field] = []
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


@pytest.mark.parametrize(
    "field",
    ["sample_size", "primary_utility_endpoint", "multiplicity_strategy"],
)
def test_frozen_analysis_rejects_missing_confirmatory_choice(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_frozen_analysis()
    del instance[field]
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


@pytest.mark.parametrize("sample_size", [0, -1])
def test_frozen_analysis_rejects_nonpositive_sample_size(
    sample_size: int,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_frozen_analysis()
    instance["sample_size"] = sample_size
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


@pytest.mark.parametrize(
    "field",
    [
        "model_specification",
        "dependency_structure",
        "standardization_method",
        "interval_method",
        "multiplicity_strategy",
        "primary_utility_endpoint",
        "missing_data_strategy",
        "zero_event_strategy",
        "secondary_hypothesis_configuration",
    ],
)
def test_frozen_analysis_rejects_unresolved_confirmatory_choice(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_frozen_analysis()
    instance[field] = unresolved("Not resolved before confirmatory use.")
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


def test_analysis_rejects_action_level_pseudoreplication(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_frozen_analysis()
    instance["dependency_structure"]["action_level_observations_independent"] = True
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


def test_analysis_rejects_mapping_missing_primary_outcome_to_zero(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_frozen_analysis()
    instance["missing_data_strategy"]["missing_primary_assigned_zero"] = True
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


def test_analysis_rejects_zero_events_as_security_proof(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_frozen_analysis()
    instance["zero_event_strategy"]["zero_events_are_proof_of_security"] = True
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


def test_analysis_requires_each_frozen_population(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_frozen_analysis()
    instance["analysis_populations"][-1]["population"] = "PRIMARY_VALID_SET"
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


def test_frozen_analysis_rejects_latest_software_version(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_frozen_analysis()
    instance["software_runtime_identity"]["version"] = "latest"
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


@pytest.mark.parametrize(
    "field",
    [
        "observed_risk_difference",
        "risk_ratio_result",
        "p_value",
        "confidence_interval_result",
        "h1_supported",
        "h2_supported",
        "h3_supported",
        "h4_supported",
        "treatment_effect_result",
    ],
)
def test_analysis_manifest_rejects_analytic_result_field(
    field: str,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    instance = valid_frozen_analysis()
    instance[field] = 0
    assert_invalid(instance, schemas["analysis-manifest"], schema_store)


def test_analysis_validation_does_not_mutate_input(
    schemas: dict[str, dict[str, Any]], schema_store: dict[str, Any]
) -> None:
    instance = valid_frozen_analysis("ORDERED")
    original = copy.deepcopy(instance)
    assert_valid(instance, schemas["analysis-manifest"], schema_store)
    assert instance == original


def test_run_phase_references_remain_exactly_shared(
    schemas: dict[str, dict[str, Any]],
) -> None:
    common_ref = SCHEMA_IDS["common"] + "#/$defs/run_phase"
    assert schemas["campaign"]["properties"]["phase"]["$ref"] == common_ref
    assert schemas["scheduled-run"]["properties"]["phase"]["$ref"] == common_ref
    assert schemas["run-manifest"]["properties"]["phase"]["$ref"] == common_ref
    assert schemas["common"]["$defs"]["run_phase"]["enum"] == RUN_PHASES


def test_scheduled_run_shared_identifiers_match_run_manifest(
    schemas: dict[str, dict[str, Any]],
) -> None:
    scheduled_properties = schemas["scheduled-run"]["properties"]
    manifest_properties = schemas["run-manifest"]["properties"]
    for field in (
        "experiment_id",
        "campaign_id",
        "scheduled_run_id",
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
    ):
        assert scheduled_properties[field]["$ref"] == manifest_properties[field]["$ref"]
    assert scheduled_properties["seed_repetition_identity"]["$ref"] == (
        SCHEMA_IDS["run-manifest"] + "#/$defs/seed_repetition_identity"
    )


def test_analysis_h1_constants_match_frozen_research_semantics(
    schemas: dict[str, dict[str, Any]],
) -> None:
    properties = schemas["analysis-manifest"]["properties"]
    assert properties["primary_endpoint"]["const"] == (
        "RUN_LEVEL_ANY_UNAUTHORIZED_EXECUTED"
    )
    assert properties["primary_estimand"]["const"] == "RISK_DIFFERENCE"
    assert properties["primary_effect_direction"]["const"] == "M3_MINUS_M1"


def test_stage8_schemas_validate_from_explicit_local_store_without_network(
    monkeypatch: pytest.MonkeyPatch,
    schemas: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access was attempted")

    monkeypatch.setattr(urllib.request, "urlopen", fail_network)
    assert_valid(
        valid_capability_evaluation(),
        schemas["capability-evaluation"],
        schema_store,
    )
    assert_valid(valid_campaign(), schemas["campaign"], schema_store)
    assert_valid(valid_scheduled_run(), schemas["scheduled-run"], schema_store)
    assert_valid(valid_frozen_analysis(), schemas["analysis-manifest"], schema_store)


def test_stage8_contracts_do_not_define_unsafe_or_runtime_fields(
    schemas: dict[str, dict[str, Any]],
) -> None:
    property_names: set[str] = set()
    pending: list[Any] = [schemas[name] for name in STAGE8_SCHEMAS]
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
        "target_ip",
        "target_url",
        "real_credentials",
        "api_key",
        "exploit_payload",
        "malware_path",
        "host_compromise",
        "physical_fault_injection",
        "model_api",
        "agent_execution",
    ):
        assert forbidden not in property_names
