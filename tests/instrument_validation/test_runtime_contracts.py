"""IV-G1 static runtime-contract and configuration-closure tests."""

from __future__ import annotations

import ast
import copy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from frontier_agent_containment.instrument_validation import (
    EVIDENCE_INGRESS_SCHEMA_ID,
    RUNTIME_PLAN_SCHEMA_ID,
    S0_ACCEPTANCE_SCHEMA_ID,
    IVContractErrorCode,
    IVContractValidationError,
    IVReferenceCatalog,
    IVSourceRegistration,
    assert_valid_evidence_ingress_envelope,
    assert_valid_runtime_plan,
    assert_valid_s0_runtime_acceptance,
    is_iv_validation_case_id,
    load_and_validate_evidence_ingress_envelope,
    load_and_validate_runtime_plan,
    load_and_validate_s0_runtime_acceptance,
    validate_evidence_ingress_envelope,
    validate_iv_validation_case_inventory,
    validate_runtime_plan,
    validate_s0_acceptance_aggregation,
    validate_s0_runtime_acceptance,
)
from frontier_agent_containment.integrity import canonical_sha256
from frontier_agent_containment.schema_validation import (
    DuplicateJsonKeyError,
    load_json,
    load_schema_store,
    validate_instance,
)
from frontier_agent_containment.semantic_validation import (
    ARTIFACT_FAMILY_CONTRACT_SPECS,
    SUPPORTED_ARTIFACT_FAMILIES,
)
from tests.schema.test_identity1_identified_artifact_schemas import (
    prospective_acceptance,
)
from tests.schema.test_stage12e1_release_contracts import valid_release_profile


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATHS = tuple(sorted((ROOT / "schemas").glob("*.schema.json")))
FIXTURE_ROOT = (
    ROOT / "tests" / "fixtures" / "instrument_validation" / "v0.1"
    / "configuration"
)
RUNTIME_PLAN_PATH = FIXTURE_ROOT / "runtime-plan.json"
INGRESS_PATH = FIXTURE_ROOT / "evidence-ingress-envelope.json"
S0_ACCEPTANCE_PATH = FIXTURE_ROOT / "s0-runtime-acceptance.json"

NEW_SCHEMA_IDS = {
    RUNTIME_PLAN_SCHEMA_ID,
    EVIDENCE_INGRESS_SCHEMA_ID,
    S0_ACCEPTANCE_SCHEMA_ID,
}
EVIDENCE_QUALITY_STATES = {
    "VALID",
    "MISSING_REQUIRED",
    "CONFLICTING",
    "DUPLICATE",
    "MALFORMED",
    "UNTRUSTED_SOURCE",
    "OUT_OF_ORDER",
    "UNRESOLVED_IDENTITY",
    "INCONCLUSIVE",
}
VALIDATION_RESULT_STATES = {
    "VALIDATION_PASS",
    "VALIDATION_FAIL",
    "VALIDATION_INCONCLUSIVE",
    "VALIDATION_NOT_APPLICABLE",
}
APPLICABILITY_CLASSES = {
    "MANDATORY_GLOBAL",
    "MANDATORY_CONDITIONAL",
    "OPTIONAL_DIAGNOSTIC",
}
EXPECTED_FAMILY_COUNTS = {
    "V0": 10,
    "V1": 58,
    "V2": 22,
    "V3": 35,
    "V4": 4,
    "V5": 7,
}
FROZEN_SCHEMA_CONTRACTS = (
    ("urn:frontier-agent-containment:schema:benign-task:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:campaign:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:capability-envelope:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:common:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:control-condition:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:control:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:derived-action-outcome:0.2.0", "0.2.0"),
    ("urn:frontier-agent-containment:schema:derived-run-outcome:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:derived-run-outcome:0.2.0", "0.2.0"),
    ("urn:frontier-agent-containment:schema:environment:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:evidence-event:0.1.0", "0.1.0"),
    (
        "urn:frontier-agent-containment:schema:evidence-ingress-envelope:0.1.0",
        "0.1.0",
    ),
    (
        "urn:frontier-agent-containment:schema:instrument-acceptance:0.2.0",
        "0.2.0",
    ),
    (
        "urn:frontier-agent-containment:schema:instrument-configuration:0.1.0",
        "0.1.0",
    ),
    (
        "urn:frontier-agent-containment:schema:"
        "instrument-validation-runtime-plan:0.1.0",
        "0.1.0",
    ),
    ("urn:frontier-agent-containment:schema:policy:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:resource:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:run-manifest:0.1.0", "0.1.0"),
    (
        "urn:frontier-agent-containment:schema:s0-runtime-acceptance:0.1.0",
        "0.1.0",
    ),
    ("urn:frontier-agent-containment:schema:scenario:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:scheduled-run:0.1.0", "0.1.0"),
    ("urn:frontier-agent-containment:schema:validation-case:0.1.0", "0.1.0"),
)
FROZEN_COMPONENT_IDS = (
    "validation_orchestrator",
    "scripted_validation_actor",
    "scenario_adapter",
    "authorization_service",
    "approval_emulator",
    "m1_policy_context_adapter",
    "m2_policy_mediator",
    "m3_external_enforcer",
    "action_execution_adapter",
    "s0_environment_boundary",
    "resource_state_observer",
    "s0_boundary_observer",
    "evidence_collector",
    "evidence_normalizer_store",
    "action_outcome_evaluator",
    "run_outcome_aggregator",
    "validation_case_evaluator",
    "instrument_acceptance_producer",
    "reset_controller",
    "watchdog_controller",
    "failure_injection_controller",
)
FROZEN_SOURCE_SPECS = (
    ("source:request", "validation_orchestrator", "EXPERIMENT_ORCHESTRATOR",
     "B_APPLICATION_CONTROL", "channel_request", ("REQUEST",)),
    ("source:authorization", "authorization_service",
     "AUTHORIZATION_DECISION_SOURCE", "B_APPLICATION_CONTROL",
     "channel_authorization", ("AUTHORIZATION",)),
    ("source:approval", "approval_emulator", "APPROVAL_AUTHORITY",
     "B_APPLICATION_CONTROL", "channel_approval", ("APPROVAL",)),
    ("source:m1-configuration", "m1_policy_context_adapter",
     "EXPERIMENT_ORCHESTRATOR", "B_APPLICATION_CONTROL",
     "channel_m1_configuration", ("M1_CONFIGURATION",)),
    ("source:m2", "m2_policy_mediator", "EXECUTION_MEDIATOR",
     "B_APPLICATION_CONTROL", "channel_m2", ("M2_DECISION",)),
    ("source:m3", "m3_external_enforcer", "EXECUTION_MEDIATOR",
     "C_EXTERNAL_ENFORCEMENT", "channel_m3", ("M3_DECISION",)),
    ("source:execution", "action_execution_adapter", "EXECUTION_MEDIATOR",
     "B_APPLICATION_CONTROL", "channel_execution", ("EXECUTION_DISPATCH",)),
    ("source:resource", "resource_state_observer",
     "RESOURCE_SERVICE_OBSERVER", "E_AUTHORITATIVE_EVIDENCE",
     "channel_resource", ("CONSEQUENTIAL_EFFECT", "RESET_STATE")),
    ("source:s0", "s0_boundary_observer", "RESOURCE_SERVICE_OBSERVER",
     "E_AUTHORITATIVE_EVIDENCE", "channel_s0", ("S0_STATE",)),
    ("source:watchdog", "watchdog_controller", "EXPERIMENT_ORCHESTRATOR",
     "D_S0_BOUNDARY", "channel_watchdog", ("TERMINATION",)),
    ("source:collector", "evidence_collector", "EVIDENCE_COLLECTOR",
     "E_AUTHORITATIVE_EVIDENCE", "channel_collector",
     ("COLLECTION_HEALTH",)),
    ("source:normalizer", "evidence_normalizer_store", "EVIDENCE_COLLECTOR",
     "E_AUTHORITATIVE_EVIDENCE", "channel_normalizer",
     ("NORMALIZATION_ORDER",)),
    ("source:action-evaluator", "action_outcome_evaluator", "EVALUATOR",
     "E_AUTHORITATIVE_EVIDENCE", "channel_action-evaluator",
     ("DERIVED_ACTION_OUTCOME",)),
    ("source:run-aggregator", "run_outcome_aggregator", "EVALUATOR",
     "E_AUTHORITATIVE_EVIDENCE", "channel_run-aggregator",
     ("DERIVED_RUN_OUTCOME",)),
    ("source:case-evaluator", "validation_case_evaluator", "EVALUATOR",
     "E_AUTHORITATIVE_EVIDENCE", "channel_case-evaluator",
     ("VALIDATION_RESULT",)),
)
FROZEN_S0_CASE_IDS = frozenset(
    {
        "valcase:iv-v1-s0-network-default-deny",
        "valcase:iv-v1-s0-controlled-local-egress",
        "valcase:iv-v1-s0-host-filesystem-process",
        "valcase:iv-v1-s0-secret-isolation",
        "valcase:iv-v1-s0-resource-time-bounds",
        "valcase:iv-v1-s0-policy-administration",
        "valcase:iv-v1-s0-observer-visibility",
        "valcase:iv-v1-s0-evidence-externality",
        "valcase:iv-v1-s0-clean-reset-identity",
    }
)
FROZEN_S0_CATEGORY_CASES = (
    ("NETWORK_DEFAULT_DENY", ("valcase:iv-v1-s0-network-default-deny",)),
    ("CONTROLLED_EGRESS", ("valcase:iv-v1-s0-controlled-local-egress",)),
    (
        "HOST_FILESYSTEM_ISOLATION",
        ("valcase:iv-v1-s0-host-filesystem-process",),
    ),
    ("SECRET_ISOLATION", ("valcase:iv-v1-s0-secret-isolation",)),
    (
        "PROCESS_RESOURCE_CONTAINMENT",
        (
            "valcase:iv-v1-s0-host-filesystem-process",
            "valcase:iv-v1-s0-resource-time-bounds",
        ),
    ),
    ("TIMEOUT_WATCHDOG", ("valcase:iv-v1-s0-resource-time-bounds",)),
    ("ACTION_MEDIATION", ("valcase:iv-v1-s0-policy-administration",)),
    (
        "OBSERVER_VISIBILITY",
        (
            "valcase:iv-v1-s0-observer-visibility",
            "valcase:iv-v1-s0-evidence-externality",
        ),
    ),
    (
        "EXTERNAL_ENFORCEMENT_LOCATION",
        ("valcase:iv-v1-s0-policy-administration",),
    ),
    ("RESET_DETERMINISM", ("valcase:iv-v1-s0-clean-reset-identity",)),
    (
        "CLEAN_STATE_RESTORATION",
        ("valcase:iv-v1-s0-clean-reset-identity",),
    ),
    ("FAILURE_CONTAINMENT", ("valcase:iv-v1-s0-resource-time-bounds",)),
    (
        "CONFIGURATION_IDENTITY_BINDING",
        (
            "valcase:iv-v1-s0-clean-reset-identity",
            "valcase:iv-v1-s0-policy-administration",
        ),
    ),
)


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(SCHEMA_PATHS)


@pytest.fixture()
def runtime_plan() -> dict[str, Any]:
    value = load_json(RUNTIME_PLAN_PATH)
    assert isinstance(value, dict)
    return value


@pytest.fixture()
def ingress_envelope() -> dict[str, Any]:
    value = load_json(INGRESS_PATH)
    assert isinstance(value, dict)
    return value


@pytest.fixture()
def s0_acceptance() -> dict[str, Any]:
    value = load_json(S0_ACCEPTANCE_PATH)
    assert isinstance(value, dict)
    return value


def trusted_reference_catalog(schema_store: dict[str, Any]) -> IVReferenceCatalog:
    """Build expected data independently of all candidate fixture fields."""

    component_builds = frozenset(
        (
            component_id,
            "0.1.0",
            f"build:iv-{component_id.replace('_', '-')}-001",
            f"ivg1.{component_id}",
        )
        for component_id in FROZEN_COMPONENT_IDS
    )
    source_registrations = frozenset(
        IVSourceRegistration(
            source_registration_id=source_id,
            source_component_id=component_id,
            source_role=source_role,
            source_version="0.1.0",
            source_build_id=f"build:iv-{component_id.replace('_', '-')}-001",
            trust_context=trust_context,
            instrument_configuration_id="instrument:iv-core",
            dedicated_local_channel_id=channel_id,
            authoritative_properties=properties,
        )
        for (
            source_id,
            component_id,
            source_role,
            trust_context,
            channel_id,
            properties,
        ) in FROZEN_SOURCE_SPECS
    )
    return IVReferenceCatalog(
        instrument_configurations=frozenset({("instrument:iv-core", "0.1.0")}),
        instrument_configuration_digests=frozenset({
            (
                "instrument:iv-core",
                "0.1.0",
                "sha256:" + ("a" * 64),
            )
        }),
        environments=frozenset({("env:iv-synthetic-lab", "0.1.0")}),
        environment_builds=frozenset({
            ("env:iv-synthetic-lab", "0.1.0", "build:iv-environment-001")
        }),
        s0_declarations=frozenset({("cond:s0-iv-core", "0.1.0")}),
        s0_acceptance_plans=frozenset({("s0plan:iv-core", "0.1.0")}),
        scenarios=frozenset({
            ("scenario:iv-s01-protected-record", "0.1.0")
        }),
        capability_envelopes=frozenset({("envelope:iv-core", "0.1.0")}),
        reset_plans=frozenset({("resetplan:iv-core", "0.1.0")}),
        reset_baselines=frozenset({"cond:iv-core-clean-state"}),
        safety_configurations=frozenset({("safetycfg:iv-core", "0.1.0")}),
        authorization_policies=frozenset({
            ("policy:iv-core-authorization", "0.1.0")
        }),
        approval_policies=frozenset({
            ("approvalpolicy:iv-core-deterministic", "0.1.0")
        }),
        actor_conditions=frozenset({
            ("agentcond:scripted-validation-actor", "0.1.0")
        }),
        scripts=frozenset({
            ("script:iv-core-sequence", "0.1.0", "sha256:" + ("b" * 64))
        }),
        validation_sets=frozenset({("iv_core", "0.1.0")}),
        validation_set_bindings=frozenset({
            (
                "iv_core",
                "0.1.0",
                "sha256:" + ("c" * 64),
                136,
                tuple(sorted(EXPECTED_FAMILY_COUNTS.items())),
            )
        }),
        build_ids=frozenset(
            {
                *(entry[2] for entry in component_builds),
                "build:iv-environment-001",
                "build:iv-runtime-001",
            }
        ),
        component_builds=component_builds,
        runtime_build_ids=frozenset({"build:iv-runtime-001"}),
        dependency_sets=frozenset({
            ("dependencyset:iv-core", "sha256:" + ("d" * 64))
        }),
        failure_plans=frozenset({("faultplan:iv-core", "0.1.0")}),
        source_registries=frozenset({("sourceregistry:iv-core", "0.1.0")}),
        source_registrations=source_registrations,
        schema_ids=frozenset(schema_store),
        schema_contracts=FROZEN_SCHEMA_CONTRACTS,
        run_ids=frozenset({"run:iv-001"}),
        action_ids=frozenset({"action:iv-001"}),
        event_ids=frozenset({
            "event:iv-effect-001",
            "event:iv-execution-001",
            *(f"event:iv-s0-{index:02d}" for index in range(1, 14)),
        }),
        validation_case_ids=FROZEN_S0_CASE_IDS,
    )


@pytest.fixture()
def references(
    schema_store: dict[str, Any],
) -> IVReferenceCatalog:
    return trusted_reference_catalog(schema_store)


def assert_schema_invalid(
    instance: dict[str, Any],
    schema_id: str,
    schema_store: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        validate_instance(
            instance,
            schema_store[schema_id],
            schema_store=schema_store,
        )


def finding_codes(findings: tuple[Any, ...]) -> set[IVContractErrorCode]:
    return {finding.code for finding in findings}


def assert_finding(
    findings: tuple[Any, ...],
    code: IVContractErrorCode,
    field_path: str,
    message_fragment: str,
) -> None:
    assert any(
        finding.code == code
        and finding.field_path == field_path
        and message_fragment in finding.message
        for finding in findings
    ), findings


def frozen_case_ids() -> list[str]:
    return [
        f"valcase:iv-{family.lower()}-case-{index:02d}"
        for family, count in EXPECTED_FAMILY_COUNTS.items()
        for index in range(count)
    ]


@pytest.mark.parametrize(
    "schema_id",
    sorted(NEW_SCHEMA_IDS),
)
def test_new_schemas_are_valid_draft_2020_12(
    schema_id: str,
    schema_store: dict[str, Any],
) -> None:
    schema = schema_store[schema_id]
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == schema_id


def test_generic_schema_store_closes_at_32_unique_authoritative_ids(
    schema_store: dict[str, Any],
) -> None:
    assert len(SCHEMA_PATHS) == 32
    assert len(schema_store) == 32
    assert len(set(schema_store)) == 32
    assert NEW_SCHEMA_IDS <= set(schema_store)


def test_new_contract_versions_are_exact(schema_store: dict[str, Any]) -> None:
    for schema_id in NEW_SCHEMA_IDS:
        contract = schema_store[schema_id]["$defs"]["contract_version"]
        assert {"const": "0.1.0"} in contract["allOf"]


@pytest.mark.parametrize(
    ("fixture_path", "schema_id"),
    [
        (RUNTIME_PLAN_PATH, RUNTIME_PLAN_SCHEMA_ID),
        (INGRESS_PATH, EVIDENCE_INGRESS_SCHEMA_ID),
        (S0_ACCEPTANCE_PATH, S0_ACCEPTANCE_SCHEMA_ID),
    ],
)
def test_positive_fixtures_validate_structurally(
    fixture_path: Path,
    schema_id: str,
    schema_store: dict[str, Any],
) -> None:
    validate_instance(
        load_json(fixture_path),
        schema_store[schema_id],
        schema_store=schema_store,
    )


def test_runtime_plan_fixture_closes_all_references(
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    assert validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    ) == ()
    assert_valid_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )


def test_ingress_fixture_closes_all_references(
    runtime_plan: dict[str, Any],
    ingress_envelope: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    assert validate_evidence_ingress_envelope(
        ingress_envelope,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    ) == ()
    assert_valid_evidence_ingress_envelope(
        ingress_envelope,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    )


def test_s0_fixture_closes_all_references_without_claiming_acceptance(
    runtime_plan: dict[str, Any],
    s0_acceptance: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    assert s0_acceptance["acceptance_state"] == "S0_REJECTED"
    assert s0_acceptance["lifecycle_state"] == "DRAFT"
    assert validate_s0_runtime_acceptance(
        s0_acceptance,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    ) == ()
    assert_valid_s0_runtime_acceptance(
        s0_acceptance,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    )


def test_strict_load_helpers_return_valid_objects(
    schema_store: dict[str, Any],
    runtime_plan: dict[str, Any],
    ingress_envelope: dict[str, Any],
    s0_acceptance: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    assert (
        load_and_validate_runtime_plan(
            RUNTIME_PLAN_PATH,
            schema_store=schema_store,
            references=references,
        )
        == runtime_plan
    )
    assert (
        load_and_validate_evidence_ingress_envelope(
            INGRESS_PATH,
            runtime_plan=runtime_plan,
            schema_store=schema_store,
            references=references,
        )
        == ingress_envelope
    )
    assert (
        load_and_validate_s0_runtime_acceptance(
            S0_ACCEPTANCE_PATH,
            runtime_plan=runtime_plan,
            schema_store=schema_store,
            references=references,
        )
        == s0_acceptance
    )


@pytest.mark.parametrize(
    ("fixture_name", "schema_id", "version_field"),
    [
        ("runtime", RUNTIME_PLAN_SCHEMA_ID, "schema_version"),
        ("ingress", EVIDENCE_INGRESS_SCHEMA_ID, "schema_version"),
        ("s0", S0_ACCEPTANCE_SCHEMA_ID, "schema_version"),
    ],
)
def test_wrong_schema_version_is_rejected(
    fixture_name: str,
    schema_id: str,
    version_field: str,
    runtime_plan: dict[str, Any],
    ingress_envelope: dict[str, Any],
    s0_acceptance: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = {
        "runtime": runtime_plan,
        "ingress": ingress_envelope,
        "s0": s0_acceptance,
    }[fixture_name]
    instance[version_field] = "0.2.0"
    assert_schema_invalid(instance, schema_id, schema_store)


@pytest.mark.parametrize(
    ("fixture_name", "schema_id"),
    [
        ("runtime", RUNTIME_PLAN_SCHEMA_ID),
        ("ingress", EVIDENCE_INGRESS_SCHEMA_ID),
        ("s0", S0_ACCEPTANCE_SCHEMA_ID),
    ],
)
def test_additional_properties_are_rejected(
    fixture_name: str,
    schema_id: str,
    runtime_plan: dict[str, Any],
    ingress_envelope: dict[str, Any],
    s0_acceptance: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    instance = {
        "runtime": runtime_plan,
        "ingress": ingress_envelope,
        "s0": s0_acceptance,
    }[fixture_name]
    instance["unexpected"] = True
    assert_schema_invalid(instance, schema_id, schema_store)


@pytest.mark.parametrize(
    ("invalid_id", "expected"),
    [
        ("valcase:iv-v0-static-check", True),
        ("valcase:iv-v5-acceptance-01", True),
        ("valcase:iv-v6-invalid", False),
        ("valcase:iv-v1-UPPER", False),
        ("valcase:iv-v1-space here", False),
        ("case:iv-v1-wrong-prefix", False),
    ],
)
def test_validation_case_id_grammar(invalid_id: str, expected: bool) -> None:
    assert is_iv_validation_case_id(invalid_id) is expected


def test_exact_136_case_inventory_is_representable() -> None:
    case_ids = frozen_case_ids()
    assert len(case_ids) == 136
    assert len(set(case_ids)) == 136
    assert validate_iv_validation_case_inventory(case_ids) == ()


def test_case_inventory_rejects_duplicate_identity() -> None:
    case_ids = frozen_case_ids()
    case_ids[-1] = case_ids[0]
    findings = validate_iv_validation_case_inventory(case_ids)
    assert IVContractErrorCode.DUPLICATE_IDENTITY in finding_codes(findings)
    assert IVContractErrorCode.REFERENCE_INVALID in finding_codes(findings)


def test_case_inventory_rejects_wrong_grammar_and_count() -> None:
    findings = validate_iv_validation_case_inventory(["valcase:iv-v6-invalid"])
    assert finding_codes(findings) == {IVContractErrorCode.REFERENCE_INVALID}


def test_runtime_plan_binds_frozen_actor_metadata(
    runtime_plan: dict[str, Any],
) -> None:
    actor = runtime_plan["scripted_actor"]
    assert actor["maximum_actor_actions"] == 4
    assert actor["global_action_budget"] == 8
    assert actor["deterministic"] is True
    assert actor["adaptive_model_behavior"] is False
    assert actor["randomness_policy"] == "NONE"
    assert actor["seed_policy"] == "NOT_APPLICABLE"
    assert actor["authorization_authority"] is False
    assert actor["stores_credentials"] is False
    assert actor["public_network_dependency"] is False


def test_runtime_plan_binds_exact_component_inventory(
    runtime_plan: dict[str, Any],
) -> None:
    components = runtime_plan["component_manifest"]
    assert len(components) == 21
    assert len({item["component_id"] for item in components}) == 21
    assert len({item["component_role"] for item in components}) == 21
    assert {item["component_version"] for item in components} == {"0.1.0"}
    assert len({item["build_id"] for item in components}) == 21


def test_runtime_plan_binds_s01_and_excludes_other_families(
    runtime_plan: dict[str, Any],
) -> None:
    scenario = runtime_plan["scenario_selection"]
    assert scenario["scenario_family"] == "S01"
    assert scenario["scenario_id"] == "scenario:iv-s01-protected-record"
    assert scenario["synthetic"] is True
    assert scenario["public_target"] is False
    assert scenario["real_credentials"] is False


def test_runtime_plan_binds_136_case_counts_and_repetitions(
    runtime_plan: dict[str, Any],
) -> None:
    inventory = runtime_plan["validation_inventory"]
    assert inventory["case_count"] == 136
    assert inventory["family_counts"] == EXPECTED_FAMILY_COUNTS
    assert runtime_plan["repetition_tolerance_plan"]["repetitions"] == {
        "V0": 2,
        "V1": 3,
        "V2": 3,
        "V3": 3,
        "V4": 5,
        "V5": 2,
    }


def test_runtime_plan_binds_27_bounded_fault_classes(
    runtime_plan: dict[str, Any],
) -> None:
    faults = runtime_plan["failure_injection_plan"]["fault_classes"]
    assert len(faults) == 27
    assert len(set(faults)) == 27
    assert runtime_plan["failure_injection_plan"]["synthetic_only"] is True


def test_runtime_plan_binds_declaration_not_acceptance(
    runtime_plan: dict[str, Any],
) -> None:
    declaration = runtime_plan["s0_declaration_binding"]
    assert declaration["runtime_accepted"] is False
    assert "acceptance_state" not in declaration


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("duplicate_component", IVContractErrorCode.DUPLICATE_IDENTITY),
        ("unresolved_edge", IVContractErrorCode.REFERENCE_INVALID),
        ("self_edge", IVContractErrorCode.GRAPH_INVALID),
        ("two_node_cycle", IVContractErrorCode.GRAPH_INVALID),
        ("long_cycle", IVContractErrorCode.GRAPH_INVALID),
        ("wrong_m3_zone", IVContractErrorCode.TRUST_BOUNDARY_INVALID),
        ("collapsed_controls", IVContractErrorCode.TRUST_BOUNDARY_INVALID),
        ("unresolved_binding", IVContractErrorCode.REFERENCE_INVALID),
    ],
)
def test_runtime_plan_semantic_invariants_reject_invalid_graph_or_trust(
    mutation: str,
    code: IVContractErrorCode,
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    by_id = {
        component["component_id"]: component
        for component in runtime_plan["component_manifest"]
    }
    if mutation == "duplicate_component":
        runtime_plan["component_manifest"][1]["component_id"] = (
            runtime_plan["component_manifest"][0]["component_id"]
        )
    elif mutation == "unresolved_edge":
        by_id["scenario_adapter"]["dependency_component_ids"] = ["missing"]
    elif mutation == "self_edge":
        by_id["scenario_adapter"]["dependency_component_ids"] = [
            "scenario_adapter"
        ]
    elif mutation == "two_node_cycle":
        by_id["s0_environment_boundary"]["dependency_component_ids"] = [
            "scenario_adapter"
        ]
    elif mutation == "long_cycle":
        by_id["s0_environment_boundary"]["dependency_component_ids"] = [
            "evidence_normalizer_store"
        ]
    elif mutation == "wrong_m3_zone":
        by_id["m3_external_enforcer"]["trust_context"] = (
            "B_APPLICATION_CONTROL"
        )
    elif mutation == "collapsed_controls":
        runtime_plan["control_bindings"]["m3_component_id"] = (
            "m2_policy_mediator"
        )
    else:
        runtime_plan["control_bindings"]["m1_component_id"] = "missing"

    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    if mutation in {"self_edge", "two_node_cycle", "long_cycle"}:
        assert_finding(
            findings,
            IVContractErrorCode.GRAPH_INVALID,
            "/component_manifest",
            (
                "component cannot depend on itself"
                if mutation == "self_edge"
                else "component dependency graph contains a cycle"
            ),
        )
    else:
        assert code in finding_codes(findings)


def test_actor_cannot_be_an_authoritative_security_source(
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    source = runtime_plan["evidence_configuration"]["source_registry"][0]
    actor = next(
        item
        for item in runtime_plan["component_manifest"]
        if item["component_id"] == "scripted_validation_actor"
    )
    source.update(
        {
            "source_component_id": actor["component_id"],
            "source_role": "EXPERIMENT_ORCHESTRATOR",
            "source_version": actor["component_version"],
            "source_build_id": actor["build_id"],
            "trust_context": actor["trust_context"],
            "authoritative_properties": ["AUTHORIZATION"],
        }
    )
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert IVContractErrorCode.TRUST_BOUNDARY_INVALID in finding_codes(findings)


def test_external_effect_authority_is_mandatory(
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    for source in runtime_plan["evidence_configuration"]["source_registry"]:
        if "CONSEQUENTIAL_EFFECT" in source["authoritative_properties"]:
            source["authoritative_properties"].remove("CONSEQUENTIAL_EFFECT")
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert IVContractErrorCode.TRUST_BOUNDARY_INVALID in finding_codes(findings)


def test_source_identities_and_local_channels_are_unique(
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    sources = runtime_plan["evidence_configuration"]["source_registry"]
    sources[1]["source_registration_id"] = sources[0]["source_registration_id"]
    sources[2]["dedicated_local_channel_id"] = sources[0][
        "dedicated_local_channel_id"
    ]
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert IVContractErrorCode.DUPLICATE_IDENTITY in finding_codes(findings)


def test_source_registry_has_exact_15_sources_and_16_properties(
    runtime_plan: dict[str, Any],
) -> None:
    evidence = runtime_plan["evidence_configuration"]
    sources = evidence["source_registry"]
    actual = {
        source["source_registration_id"]: tuple(
            source["authoritative_properties"]
        )
        for source in sources
    }
    expected = {
        source_id: properties
        for source_id, _, _, _, _, properties in FROZEN_SOURCE_SPECS
    }
    assert evidence["source_registry_id"] == "sourceregistry:iv-core"
    assert len(sources) == len(actual) == 15
    assert actual == expected
    assert sum(len(properties) for properties in actual.values()) == 16
    assert all(
        source["instrument_configuration_id"] == "instrument:iv-core"
        for source in sources
    )
    assert "REQUEST" in actual["source:request"]
    assert "M1_CONFIGURATION" in actual["source:m1-configuration"]


@pytest.mark.parametrize(
    ("source_id", "property_name"),
    [
        ("source:request", "REQUEST"),
        ("source:m1-configuration", "M1_CONFIGURATION"),
    ],
)
def test_required_authority_property_cannot_be_missing(
    source_id: str,
    property_name: str,
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    source = next(
        item
        for item in runtime_plan["evidence_configuration"]["source_registry"]
        if item["source_registration_id"] == source_id
    )
    source["authoritative_properties"] = []
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert_finding(
        findings,
        IVContractErrorCode.TRUST_BOUNDARY_INVALID,
        "/evidence_configuration/source_registry",
        f"{property_name} must have exactly one authoritative source",
    )


def test_duplicate_authority_has_no_silent_reconciliation(
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    approval = next(
        item
        for item in runtime_plan["evidence_configuration"]["source_registry"]
        if item["source_registration_id"] == "source:approval"
    )
    approval["authoritative_properties"].append("AUTHORIZATION")
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert_finding(
        findings,
        IVContractErrorCode.TRUST_BOUNDARY_INVALID,
        "/evidence_configuration/source_registry",
        "AUTHORIZATION must have exactly one authoritative source",
    )


def test_source_registered_to_foreign_configuration_is_rejected(
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    source = runtime_plan["evidence_configuration"]["source_registry"][0]
    source["instrument_configuration_id"] = "instrument:alternate"
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert_finding(
        findings,
        IVContractErrorCode.CONFIGURATION_MISMATCH,
        (
            "/evidence_configuration/source_registry/0/"
            "instrument_configuration_id"
        ),
        "different Instrument Configuration",
    )


def test_authority_source_wrong_trust_zone_is_rejected(
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    source = next(
        item
        for item in runtime_plan["evidence_configuration"]["source_registry"]
        if item["source_registration_id"] == "source:m3"
    )
    source["trust_context"] = "B_APPLICATION_CONTROL"
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert any(
        finding.code == IVContractErrorCode.TRUST_BOUNDARY_INVALID
        and finding.referenced_id == "source:m3"
        and "source role, trust" in finding.message
        for finding in findings
    )


def test_unresolved_trusted_source_registration_is_rejected(
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    entries = {
        entry
        for entry in references.source_registrations
        if entry.source_registration_id != "source:authorization"
    }
    values = references.__dict__.copy()
    values["source_registrations"] = frozenset(entries)
    incomplete = IVReferenceCatalog(**values)
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=incomplete,
    )
    assert any(
        finding.code == IVContractErrorCode.REFERENCE_INVALID
        and finding.referenced_id
        and "source:authorization" in finding.referenced_id
        for finding in findings
    )


@pytest.mark.parametrize(
    "catalog_field",
    [
        "instrument_configurations",
        "instrument_configuration_digests",
        "environments",
        "environment_builds",
        "s0_declarations",
        "s0_acceptance_plans",
        "scenarios",
        "capability_envelopes",
        "reset_plans",
        "reset_baselines",
        "safety_configurations",
        "authorization_policies",
        "approval_policies",
        "actor_conditions",
        "scripts",
        "validation_sets",
        "validation_set_bindings",
        "build_ids",
        "component_builds",
        "runtime_build_ids",
        "dependency_sets",
        "failure_plans",
        "source_registries",
        "source_registrations",
        "schema_ids",
        "schema_contracts",
    ],
)
def test_external_reference_catalog_must_close(
    catalog_field: str,
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    values = references.__dict__.copy()
    values[catalog_field] = (
        () if catalog_field == "schema_contracts" else frozenset()
    )
    incomplete = IVReferenceCatalog(**values)
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=incomplete,
    )
    assert IVContractErrorCode.REFERENCE_INVALID in finding_codes(findings)


def set_candidate_path(
    candidate: dict[str, Any],
    path: tuple[str | int, ...],
    value: Any,
) -> None:
    target: Any = candidate
    for segment in path[:-1]:
        target = target[segment]
    target[path[-1]] = value


@pytest.mark.parametrize(
    ("path", "alternate", "finding_path"),
    [
        (("runtime_plan_id",), "ivplan:alternate", "/runtime_plan_id"),
        (
            ("instrument_configuration_id",),
            "instrument:alternate",
            "/instrument_configuration_id",
        ),
        (
            ("environment_binding", "environment_id"),
            "env:iv-synthetic-local",
            "/environment_binding/environment_id",
        ),
        (
            ("s0_declaration_binding", "s0_declaration_id"),
            "cond:s0-iv-local",
            "/s0_declaration_binding/s0_declaration_id",
        ),
        (
            ("s0_declaration_binding", "expected_acceptance_plan_id"),
            "s0plan:alternate",
            "/s0_declaration_binding/expected_acceptance_plan_id",
        ),
        (
            ("scenario_selection", "scenario_id"),
            "scenario:alternate",
            "/scenario_selection/scenario_id",
        ),
        (
            ("scenario_selection", "safety_configuration_id"),
            "safetycfg:alternate",
            "/scenario_selection/safety_configuration_id",
        ),
        (
            ("capability_envelope_binding", "capability_envelope_id"),
            "envelope:alternate",
            "/capability_envelope_binding/capability_envelope_id",
        ),
        (
            ("reset_plan_binding", "reset_plan_id"),
            "resetplan:alternate",
            "/reset_plan_binding/reset_plan_id",
        ),
        (
            ("reset_plan_binding", "reset_baseline_id"),
            "cond:alternate-baseline",
            "/reset_plan_binding/reset_baseline_id",
        ),
        (
            ("control_bindings", "authorization_policy_id"),
            "policy:alternate",
            "/control_bindings/authorization_policy_id",
        ),
        (
            ("control_bindings", "approval_policy_id"),
            "approvalpolicy:alternate",
            "/control_bindings/approval_policy_id",
        ),
        (
            ("scripted_actor", "actor_condition_id"),
            "agentcond:alternate",
            "/scripted_actor/actor_condition_id",
        ),
        (
            ("scripted_actor", "script_id"),
            "script:alternate",
            "/scripted_actor/script_id",
        ),
        (
            ("validation_inventory", "validation_set_id"),
            "alternate_inventory",
            "/validation_inventory/validation_set_id",
        ),
        (
            ("evidence_configuration", "source_registry_id"),
            "sourceregistry:alternate",
            "/evidence_configuration/source_registry_id",
        ),
        (
            ("failure_injection_plan", "failure_plan_id"),
            "faultplan:alternate",
            "/failure_injection_plan/failure_plan_id",
        ),
        (
            ("dependency_environment_binding", "dependency_set_id"),
            "dependencyset:alternate",
            "/dependency_environment_binding/dependency_set_id",
        ),
    ],
)
def test_frozen_singleton_ids_reject_schema_valid_alternates(
    path: tuple[str | int, ...],
    alternate: str,
    finding_path: str,
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    set_candidate_path(runtime_plan, path, alternate)
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert_finding(
        findings,
        IVContractErrorCode.CONFIGURATION_MISMATCH,
        finding_path,
        "does not equal the frozen IV-core value",
    )


@pytest.mark.parametrize(
    ("path", "alternate", "code"),
    [
        (
            ("instrument_configuration_digest",),
            "sha256:" + ("0" * 64),
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("environment_binding", "environment_build_id"),
            "build:missing",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("s0_declaration_binding", "s0_component_id"),
            "missing_component",
            IVContractErrorCode.TRUST_BOUNDARY_INVALID,
        ),
        (
            ("component_manifest", 0, "build_id"),
            "build:missing",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("component_manifest", 0, "implementation_reference"),
            "ivg1.missing",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("scripted_actor", "actor_component_id"),
            "missing_component",
            IVContractErrorCode.TRUST_BOUNDARY_INVALID,
        ),
        (
            ("scripted_actor", "actor_build_id"),
            "build:missing",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("scripted_actor", "script_digest"),
            "sha256:" + ("0" * 64),
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("scenario_selection", "scenario_adapter_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("scenario_selection", "ground_truth_adapter_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("scenario_selection", "reset_controller_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("reset_plan_binding", "reset_controller_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("control_bindings", "m1_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("control_bindings", "m2_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("control_bindings", "m3_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("control_bindings", "authorization_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("control_bindings", "approval_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("control_bindings", "execution_adapter_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("evidence_configuration", "collector_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("evidence_configuration", "normalizer_store_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("runtime_component_bindings", "orchestrator_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("runtime_component_bindings", "action_evaluator_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("runtime_component_bindings", "run_aggregator_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("runtime_component_bindings", "case_evaluator_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("runtime_component_bindings", "acceptance_producer_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("runtime_component_bindings", "reset_controller_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("runtime_component_bindings", "watchdog_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("runtime_component_bindings", "failure_controller_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("validation_inventory", "validation_set_digest"),
            "sha256:" + ("0" * 64),
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("failure_injection_plan", "failure_controller_component_id"),
            "missing_component",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("dependency_environment_binding", "runtime_build_id"),
            "build:missing",
            IVContractErrorCode.REFERENCE_INVALID,
        ),
        (
            ("dependency_environment_binding", "dependency_set_digest"),
            "sha256:" + ("0" * 64),
            IVContractErrorCode.REFERENCE_INVALID,
        ),
    ],
)
def test_reference_bearing_rows_reject_untrusted_targets(
    path: tuple[str | int, ...],
    alternate: str,
    code: IVContractErrorCode,
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    set_candidate_path(runtime_plan, path, alternate)
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert code in finding_codes(findings), (path, findings)


@pytest.mark.parametrize(
    "path",
    [
        ("instrument_configuration_version",),
        ("environment_binding", "environment_version"),
        ("s0_declaration_binding", "s0_declaration_version"),
        ("scripted_actor", "actor_version"),
        ("scripted_actor", "script_version"),
        ("scenario_selection", "scenario_version"),
        ("scenario_selection", "safety_configuration_version"),
        ("capability_envelope_binding", "capability_envelope_version"),
        ("reset_plan_binding", "reset_plan_version"),
        ("control_bindings", "authorization_policy_version"),
        ("control_bindings", "approval_policy_version"),
        ("evidence_configuration", "source_registry_version"),
        ("validation_inventory", "validation_set_version"),
        ("failure_injection_plan", "failure_plan_version"),
    ],
)
def test_reference_versions_reject_wrong_contract_version(
    path: tuple[str | int, ...],
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    set_candidate_path(runtime_plan, path, "0.2.0")
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert finding_codes(findings) == {IVContractErrorCode.SCHEMA_INVALID}


@pytest.mark.parametrize(
    ("path", "wrong_type"),
    [
        (("instrument_configuration_id",), "env:wrong-type"),
        (("environment_binding", "environment_id"), "cond:wrong-type"),
        (
            ("s0_declaration_binding", "s0_declaration_id"),
            "env:wrong-type",
        ),
        (
            ("s0_declaration_binding", "expected_acceptance_plan_id"),
            "policy:wrong-type",
        ),
        (("scenario_selection", "scenario_id"), "env:wrong-type"),
        (
            ("scenario_selection", "safety_configuration_id"),
            "policy:wrong-type",
        ),
        (
            ("capability_envelope_binding", "capability_envelope_id"),
            "policy:wrong-type",
        ),
        (("reset_plan_binding", "reset_plan_id"), "policy:wrong-type"),
        (("reset_plan_binding", "reset_baseline_id"), "env:wrong-type"),
        (
            ("control_bindings", "authorization_policy_id"),
            "envelope:wrong-type",
        ),
        (
            ("control_bindings", "approval_policy_id"),
            "policy:wrong-type",
        ),
        (("scripted_actor", "actor_condition_id"), "policy:wrong-type"),
        (("scripted_actor", "script_id"), "policy:wrong-type"),
        (
            ("evidence_configuration", "source_registry_id"),
            "policy:wrong-type",
        ),
        (
            ("failure_injection_plan", "failure_plan_id"),
            "policy:wrong-type",
        ),
        (
            ("dependency_environment_binding", "dependency_set_id"),
            "policy:wrong-type",
        ),
    ],
)
def test_typed_reference_fields_reject_wrong_type_prefix(
    path: tuple[str | int, ...],
    wrong_type: str,
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    set_candidate_path(runtime_plan, path, wrong_type)
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert finding_codes(findings) == {IVContractErrorCode.SCHEMA_INVALID}


@pytest.mark.parametrize(
    "field",
    ["ingress_schema_id", "normalized_evidence_schema_id"],
)
def test_evidence_schema_bindings_are_structurally_exact(
    field: str,
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    runtime_plan["evidence_configuration"][field] = (
        "urn:frontier-agent-containment:schema:common:0.1.0"
    )
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert finding_codes(findings) == {IVContractErrorCode.SCHEMA_INVALID}


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("missing", IVContractErrorCode.SCHEMA_INVALID),
        ("extra", IVContractErrorCode.SCHEMA_INVALID),
        ("duplicate", IVContractErrorCode.SCHEMA_INVALID),
        ("wrong_id", IVContractErrorCode.CONFIGURATION_MISMATCH),
        ("wrong_order", IVContractErrorCode.CONFIGURATION_MISMATCH),
    ],
)
def test_schema_contracts_require_exact_ordered_22_entry_set(
    mutation: str,
    code: IVContractErrorCode,
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    contracts = runtime_plan["schema_contracts"]
    if mutation == "missing":
        contracts.pop()
    elif mutation == "extra":
        contracts.append(
            {
                "schema_id": (
                    "urn:frontier-agent-containment:schema:"
                    "release-profile:0.1.0"
                ),
                "schema_version": "0.1.0",
            }
        )
    elif mutation == "duplicate":
        contracts[-1] = copy.deepcopy(contracts[0])
    elif mutation == "wrong_id":
        contracts[-1] = {
            "schema_id": (
                "urn:frontier-agent-containment:schema:"
                "release-profile:0.1.0"
            ),
            "schema_version": "0.1.0",
        }
    else:
        contracts[0], contracts[1] = contracts[1], contracts[0]

    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert code in finding_codes(findings)
    if code == IVContractErrorCode.CONFIGURATION_MISMATCH:
        assert_finding(
            findings,
            code,
            "/schema_contracts",
            "frozen ordered 22-schema set",
        )


def test_runtime_fixture_has_exact_independent_schema_contract_set(
    runtime_plan: dict[str, Any],
) -> None:
    actual = tuple(
        (entry["schema_id"], entry["schema_version"])
        for entry in runtime_plan["schema_contracts"]
    )
    assert actual == FROZEN_SCHEMA_CONTRACTS
    assert len(actual) == len(set(actual)) == 22
    assert actual == tuple(sorted(actual))
    assert (
        "urn:frontier-agent-containment:schema:"
        "derived-run-outcome:0.1.0",
        "0.1.0",
    ) in actual


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("evidence_quality_state", "UNKNOWN"),
        ("receipt_state", "UNKNOWN"),
        ("schema_version", "1.0.0"),
        ("source_registration_id", "Source:bad"),
    ],
)
def test_ingress_schema_rejects_invalid_vocabularies_or_identity(
    field: str,
    invalid_value: str,
    ingress_envelope: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    ingress_envelope[field] = invalid_value
    assert_schema_invalid(
        ingress_envelope,
        EVIDENCE_INGRESS_SCHEMA_ID,
        schema_store,
    )


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("unresolved_source", IVContractErrorCode.REFERENCE_INVALID),
        ("wrong_rank", IVContractErrorCode.CONFIGURATION_MISMATCH),
        ("wrong_source_build", IVContractErrorCode.CONFIGURATION_MISMATCH),
        ("wrong_source_registry", IVContractErrorCode.CONFIGURATION_MISMATCH),
        ("wrong_configuration", IVContractErrorCode.CONFIGURATION_MISMATCH),
        ("unresolved_run", IVContractErrorCode.REFERENCE_INVALID),
        ("unresolved_action", IVContractErrorCode.REFERENCE_INVALID),
        ("unresolved_prior", IVContractErrorCode.REFERENCE_INVALID),
        ("duplicate_receipt", IVContractErrorCode.DUPLICATE_IDENTITY),
    ],
)
def test_ingress_semantic_closure_rejects_mismatches(
    mutation: str,
    code: IVContractErrorCode,
    runtime_plan: dict[str, Any],
    ingress_envelope: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    if mutation == "unresolved_source":
        ingress_envelope["source_registration_id"] = "source:missing"
    elif mutation == "wrong_rank":
        ingress_envelope["event_class_rank"] = 90
    elif mutation == "wrong_source_build":
        ingress_envelope["source_build_id"] = "build:wrong"
    elif mutation == "wrong_source_registry":
        ingress_envelope["source_registry_id"] = "sourceregistry:alternate"
    elif mutation == "wrong_configuration":
        ingress_envelope["instrument_configuration_id"] = (
            "instrument:alternate"
        )
    elif mutation == "unresolved_run":
        ingress_envelope["run_id"] = "run:missing"
    elif mutation == "unresolved_action":
        ingress_envelope["action_id"] = "action:missing"
    elif mutation == "unresolved_prior":
        ingress_envelope["prior_event_ids"] = ["event:missing"]
    else:
        values = references.__dict__.copy()
        values["receipt_ids"] = frozenset({ingress_envelope["receipt_id"]})
        references = IVReferenceCatalog(**values)

    findings = validate_evidence_ingress_envelope(
        ingress_envelope,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert code in finding_codes(findings)


def test_ingress_rejects_actor_only_effect_authority(
    runtime_plan: dict[str, Any],
    ingress_envelope: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    actor = next(
        item
        for item in runtime_plan["component_manifest"]
        if item["component_id"] == "scripted_validation_actor"
    )
    source = runtime_plan["evidence_configuration"]["source_registry"][0]
    source.update(
        {
            "source_registration_id": "source:actor-report",
            "source_component_id": actor["component_id"],
            "source_role": "EXPERIMENT_ORCHESTRATOR",
            "source_version": actor["component_version"],
            "source_build_id": actor["build_id"],
            "trust_context": actor["trust_context"],
            "instrument_configuration_id": "instrument:iv-core",
            "dedicated_local_channel_id": "channel_actor_report",
            "authoritative_properties": ["CONSEQUENTIAL_EFFECT"],
        }
    )
    ingress_envelope.update(
        {
            "source_registration_id": source["source_registration_id"],
            "source_component_id": source["source_component_id"],
            "source_version": source["source_version"],
            "source_build_id": source["source_build_id"],
            "dedicated_local_channel_id": source[
                "dedicated_local_channel_id"
            ],
        }
    )
    findings = validate_evidence_ingress_envelope(
        ingress_envelope,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert any(
        finding.code == IVContractErrorCode.TRUST_BOUNDARY_INVALID
        and "consequential effect requires" in finding.message
        for finding in findings
    )


def test_ingress_exposes_exact_evidence_quality_vocabulary(
    schema_store: dict[str, Any],
) -> None:
    common = schema_store[
        "urn:frontier-agent-containment:schema:common:0.1.0"
    ]
    assert set(common["$defs"]["evidence_quality_state"]["enum"]) == (
        EVIDENCE_QUALITY_STATES
    )


def test_ingress_order_is_causal_and_wall_clock_is_not_authority(
    runtime_plan: dict[str, Any],
    ingress_envelope: dict[str, Any],
) -> None:
    evidence = runtime_plan["evidence_configuration"]
    assert evidence["ordering_model"] == "CAUSAL_DAG_STABLE_TOPOLOGICAL"
    assert evidence["tie_break_fields"] == [
        "event_class_rank",
        "source_registration_id",
        "source_local_sequence",
        "event_id",
    ]
    assert (
        ingress_envelope["monotonic_time_evidence"]["causal_authority"] is False
    )
    assert runtime_plan["clock_policy"]["wall_clock_causal_authority"] is False


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("acceptance_state", "ACCEPTED_FOR_PILOT"),
        ("lifecycle_state", "ACCEPTED"),
        ("schema_version", "0.2.0"),
    ],
)
def test_s0_schema_rejects_competing_or_invalid_states(
    field: str,
    invalid_value: str,
    s0_acceptance: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    s0_acceptance[field] = invalid_value
    assert_schema_invalid(
        s0_acceptance,
        S0_ACCEPTANCE_SCHEMA_ID,
        schema_store,
    )


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("stale_plan_digest", IVContractErrorCode.CONFIGURATION_MISMATCH),
        ("wrong_environment", IVContractErrorCode.CONFIGURATION_MISMATCH),
        ("wrong_validation_set", IVContractErrorCode.CONFIGURATION_MISMATCH),
        ("wrong_component_build", IVContractErrorCode.CONFIGURATION_MISMATCH),
        ("missing_category", IVContractErrorCode.SCHEMA_INVALID),
        ("unresolved_evidence", IVContractErrorCode.REFERENCE_INVALID),
        ("unresolved_source", IVContractErrorCode.REFERENCE_INVALID),
    ],
)
def test_s0_acceptance_reference_closure_rejects_mismatch(
    mutation: str,
    code: IVContractErrorCode,
    runtime_plan: dict[str, Any],
    s0_acceptance: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    if mutation == "stale_plan_digest":
        s0_acceptance["runtime_plan_digest"] = "sha256:" + ("0" * 64)
    elif mutation == "wrong_environment":
        s0_acceptance["environment_id"] = "env:wrong"
    elif mutation == "wrong_validation_set":
        s0_acceptance["validation_set_id"] = "other"
    elif mutation == "wrong_component_build":
        s0_acceptance["component_build_bindings"][0]["build_id"] = (
            "build:wrong"
        )
    elif mutation == "missing_category":
        s0_acceptance["validation_results"].pop()
    elif mutation == "unresolved_evidence":
        s0_acceptance["validation_results"][0]["evidence_event_ids"] = [
            "event:missing"
        ]
    else:
        s0_acceptance["validation_results"][0][
            "authoritative_source_registration_ids"
        ] = ["source:missing"]

    findings = validate_s0_runtime_acceptance(
        s0_acceptance,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert code in finding_codes(findings)


def test_s0_accepted_rejects_mandatory_inconclusive(
    runtime_plan: dict[str, Any],
    s0_acceptance: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    s0_acceptance["acceptance_state"] = "S0_ACCEPTED"
    findings = validate_s0_runtime_acceptance(
        s0_acceptance,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert IVContractErrorCode.ACCEPTANCE_INVALID in finding_codes(findings)


def make_s0_accepted(
    runtime_plan: dict[str, Any],
    s0_acceptance: dict[str, Any],
    *,
    z6_endpoint_declared: bool,
) -> None:
    runtime_plan["scenario_selection"]["z6_endpoint_declared"] = (
        z6_endpoint_declared
    )
    s0_acceptance["runtime_plan_digest"] = canonical_sha256(runtime_plan)
    s0_acceptance["acceptance_state"] = "S0_ACCEPTED"
    s0_acceptance["unresolved_conditions"] = []
    for result in s0_acceptance["validation_results"]:
        if result["property_category"] == "CONTROLLED_EGRESS":
            if z6_endpoint_declared:
                result["result_state"] = "VALIDATION_PASS"
                result.pop("not_applicable_reason", None)
            else:
                result["result_state"] = "VALIDATION_NOT_APPLICABLE"
                result["not_applicable_reason"] = (
                    "No Z6 controlled local endpoint is declared."
                )
        else:
            result["result_state"] = "VALIDATION_PASS"


def test_s0_fixture_has_exact_ordered_13_category_and_nine_case_mapping(
    s0_acceptance: dict[str, Any],
) -> None:
    actual = tuple(
        (
            result["property_category"],
            tuple(result["validation_case_ids"]),
        )
        for result in s0_acceptance["validation_results"]
    )
    assert actual == FROZEN_S0_CATEGORY_CASES
    assert len(actual) == len({category for category, _ in actual}) == 13
    assert {
        case_id
        for _, case_ids in actual
        for case_id in case_ids
    } == FROZEN_S0_CASE_IDS
    assert len(FROZEN_S0_CASE_IDS) == 9
    assert sum(
        result["applicability_class"] == "MANDATORY_GLOBAL"
        for result in s0_acceptance["validation_results"]
    ) == 12
    controlled = s0_acceptance["validation_results"][1]
    assert controlled["property_category"] == "CONTROLLED_EGRESS"
    assert controlled["applicability_class"] == "MANDATORY_CONDITIONAL"


def test_s0_accepted_allows_nonblocking_optional_diagnostic_failure() -> None:
    results = [
        {
            "applicability_class": "MANDATORY_GLOBAL",
            "result_state": "VALIDATION_PASS",
        },
        {
            "applicability_class": "MANDATORY_CONDITIONAL",
            "result_state": "VALIDATION_NOT_APPLICABLE",
            "not_applicable_reason": (
                "No Z6 controlled local endpoint is declared."
            ),
        },
        {
            "applicability_class": "OPTIONAL_DIAGNOSTIC",
            "result_state": "VALIDATION_FAIL",
        },
        {
            "applicability_class": "OPTIONAL_DIAGNOSTIC",
            "result_state": "VALIDATION_INCONCLUSIVE",
        },
    ]
    assert validate_s0_acceptance_aggregation(
        results,
        z6_endpoint_declared=False,
    ) == ()


def test_s0_accepted_still_rejects_mandatory_global_failure() -> None:
    results = [
        {
            "applicability_class": "MANDATORY_GLOBAL",
            "result_state": "VALIDATION_FAIL",
        },
        {
            "applicability_class": "OPTIONAL_DIAGNOSTIC",
            "result_state": "VALIDATION_FAIL",
        },
    ]
    findings = validate_s0_acceptance_aggregation(
        results,
        z6_endpoint_declared=False,
    )
    assert_finding(
        findings,
        IVContractErrorCode.ACCEPTANCE_INVALID,
        "/validation_results/0",
        "MANDATORY_GLOBAL",
    )


def test_s0_accepted_without_z6_requires_justified_not_applicable(
    runtime_plan: dict[str, Any],
    s0_acceptance: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    make_s0_accepted(
        runtime_plan,
        s0_acceptance,
        z6_endpoint_declared=False,
    )
    assert validate_s0_runtime_acceptance(
        s0_acceptance,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    ) == ()


def test_s0_accepted_with_z6_requires_controlled_egress_pass(
    runtime_plan: dict[str, Any],
    s0_acceptance: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    make_s0_accepted(
        runtime_plan,
        s0_acceptance,
        z6_endpoint_declared=True,
    )
    assert validate_s0_runtime_acceptance(
        s0_acceptance,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    ) == ()
    controlled = s0_acceptance["validation_results"][1]
    controlled["result_state"] = "VALIDATION_NOT_APPLICABLE"
    controlled["not_applicable_reason"] = "Operator-selected N/A."
    findings = validate_s0_runtime_acceptance(
        s0_acceptance,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert_finding(
        findings,
        IVContractErrorCode.ACCEPTANCE_INVALID,
        "/validation_results/1/result_state",
        "declared Z6 endpoint",
    )


def test_s0_duplicate_category_rejects_with_13_records_remaining(
    runtime_plan: dict[str, Any],
    s0_acceptance: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    assert len(s0_acceptance["validation_results"]) == 13
    s0_acceptance["validation_results"][-1]["property_category"] = (
        "NETWORK_DEFAULT_DENY"
    )
    findings = validate_s0_runtime_acceptance(
        s0_acceptance,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert len(s0_acceptance["validation_results"]) == 13
    assert_finding(
        findings,
        IVContractErrorCode.ACCEPTANCE_INVALID,
        "/validation_results",
        "exact ordered 13-category",
    )
    assert IVContractErrorCode.DUPLICATE_IDENTITY in finding_codes(findings)


def test_s0_result_vocabularies_are_shared(
    schema_store: dict[str, Any],
) -> None:
    common = schema_store[
        "urn:frontier-agent-containment:schema:common:0.1.0"
    ]
    assert set(common["$defs"]["validation_result_state"]["enum"]) == (
        VALIDATION_RESULT_STATES
    )
    assert set(common["$defs"]["validation_applicability_class"]["enum"]) == (
        APPLICABILITY_CLASSES
    )


def test_duplicate_json_keys_remain_rejected(
    tmp_path: Path,
    schema_store: dict[str, Any],
    runtime_plan: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema_version":"0.1.0","schema_version":"0.1.0"}',
        encoding="utf-8",
    )
    with pytest.raises(DuplicateJsonKeyError):
        load_and_validate_runtime_plan(
            duplicate,
            schema_store=schema_store,
            references=references,
        )


def test_assert_helpers_raise_structured_deterministic_findings(
    runtime_plan: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    runtime_plan["control_bindings"]["m3_component_id"] = (
        "m2_policy_mediator"
    )
    findings = validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert findings == tuple(
        sorted(
            findings,
            key=lambda item: (
                item.code.value,
                item.record_type,
                item.record_id,
                item.field_path,
                item.message,
                item.referenced_id or "",
            ),
        )
    )
    with pytest.raises(IVContractValidationError) as error:
        assert_valid_runtime_plan(
            runtime_plan,
            schema_store=schema_store,
            references=references,
        )
    assert error.value.findings == findings


def test_validation_does_not_mutate_supplied_records(
    runtime_plan: dict[str, Any],
    ingress_envelope: dict[str, Any],
    s0_acceptance: dict[str, Any],
    schema_store: dict[str, Any],
    references: IVReferenceCatalog,
) -> None:
    originals = copy.deepcopy(
        (runtime_plan, ingress_envelope, s0_acceptance)
    )
    validate_runtime_plan(
        runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    validate_evidence_ingress_envelope(
        ingress_envelope,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    validate_s0_runtime_acceptance(
        s0_acceptance,
        runtime_plan=runtime_plan,
        schema_store=schema_store,
        references=references,
    )
    assert (runtime_plan, ingress_envelope, s0_acceptance) == originals


def test_prospective_instrument_acceptance_can_bind_iv_core(
    schema_store: dict[str, Any],
) -> None:
    acceptance = prospective_acceptance("REJECTED")
    acceptance["instrument_configuration_id"] = "instrument:iv-core"
    acceptance["instrument_configuration_version"] = "0.1.0"
    validate_instance(
        acceptance,
        schema_store[
            "urn:frontier-agent-containment:schema:"
            "instrument-acceptance:0.2.0"
        ],
        schema_store=schema_store,
    )


def test_release_profile_supports_instrument_validation_without_change(
    schema_store: dict[str, Any],
) -> None:
    profile = valid_release_profile("INSTRUMENT_VALIDATION")
    profile["active_artifacts"] = [
        {
            "artifact_family": "instrument_configuration",
            "artifact_id": "instrument:iv-core",
            "locator": "artifacts/instrument-configuration.json",
            "expected_artifact_version": "0.1.0",
        }
    ]
    validate_instance(
        profile,
        schema_store[
            "urn:frontier-agent-containment:schema:release-profile:0.1.0"
        ],
        schema_store=schema_store,
    )


def test_public_scientific_artifact_registries_are_unchanged() -> None:
    assert len(SUPPORTED_ARTIFACT_FAMILIES) == 21
    assert len(ARTIFACT_FAMILY_CONTRACT_SPECS) == 24
    registered_schema_ids = {
        spec.schema_id for spec in ARTIFACT_FAMILY_CONTRACT_SPECS.values()
    }
    assert NEW_SCHEMA_IDS.isdisjoint(registered_schema_ids)
    assert NEW_SCHEMA_IDS.isdisjoint(SUPPORTED_ARTIFACT_FAMILIES)


def test_configuration_digest_is_canonical_and_acceptance_bound(
    runtime_plan: dict[str, Any],
    s0_acceptance: dict[str, Any],
) -> None:
    assert s0_acceptance["runtime_plan_digest"] == canonical_sha256(
        runtime_plan
    )
    assert s0_acceptance["configuration_digest"] == runtime_plan[
        "instrument_configuration_digest"
    ]


def test_production_module_has_no_runtime_system_side_effect_api() -> None:
    source_path = (
        ROOT
        / "src"
        / "frontier_agent_containment"
        / "instrument_validation"
        / "models.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported_roots.isdisjoint(
        {
            "subprocess",
            "socket",
            "requests",
            "urllib",
            "tempfile",
            "docker",
            "podman",
            "kubernetes",
        }
    )
    forbidden_calls = {
        "system",
        "Popen",
        "run",
        "call",
        "write_text",
        "write_bytes",
        "unlink",
        "mkdir",
    }
    called_names = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert called_names.isdisjoint(forbidden_calls)


def test_new_contracts_do_not_define_scientific_h1_or_runtime_execution(
    schema_store: dict[str, Any],
) -> None:
    for schema_id in NEW_SCHEMA_IDS:
        serialized = repr(schema_store[schema_id])
        assert "h1_containment_failure" not in serialized
        assert "ACCEPTED_FOR_PILOT" not in serialized
        assert "ACCEPTED_FOR_CONFIRMATORY" not in serialized
        assert "shell_command" not in serialized
        assert "public_endpoint" not in serialized
