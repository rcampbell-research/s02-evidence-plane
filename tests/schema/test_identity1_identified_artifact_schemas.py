"""Identity-1 structural tests for prospective identified artifact contracts."""

from __future__ import annotations

import copy
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from frontier_agent_containment.schema_validation import (
    DuplicateSchemaIdError,
    check_draft_2020_12_schema,
    load_json,
    load_schema_store,
    validate_instance,
)
from tests.schema.test_stage6_contracts import (
    valid_action_outcome,
    valid_run_outcome,
)
from tests.schema.test_stage7_contracts import valid_acceptance
from tests.schema.test_stage8_contracts import valid_campaign
from tests.schema.test_stage12c_manifest_contracts import (
    valid_artifact_manifest,
    valid_reproducibility_manifest,
)
from tests.schema.test_stage12e1_release_contracts import valid_release_profile


ROOT = Path(__file__).resolve().parents[2]
DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
COMMON_ID = "urn:frontier-agent-containment:schema:common:0.1.0"
RELEASE_PROFILE_ID = (
    "urn:frontier-agent-containment:schema:release-profile:0.1.0"
)
ARTIFACT_MANIFEST_ID = (
    "urn:frontier-agent-containment:schema:artifact-manifest:0.1.0"
)
REPRODUCIBILITY_MANIFEST_ID = (
    "urn:frontier-agent-containment:schema:reproducibility-manifest:0.1.0"
)
CAMPAIGN_ID = "urn:frontier-agent-containment:schema:campaign:0.1.0"
SCHEMA_PATHS = tuple(sorted((ROOT / "schemas").glob("*.schema.json")))

CONTRACTS: dict[str, dict[str, Any]] = {
    "instrument_acceptance": {
        "historical_id": (
            "urn:frontier-agent-containment:schema:instrument-acceptance:0.1.0"
        ),
        "prospective_id": (
            "urn:frontier-agent-containment:schema:instrument-acceptance:0.2.0"
        ),
        "path": ROOT / "schemas" / "instrument-acceptance-v0.2.0.schema.json",
        "version_field": "acceptance_version",
        "id_field": "instrument_acceptance_id",
        "id_prefix": "^acceptance:",
        "valid_id": "acceptance:example-001",
    },
    "derived_action_outcome": {
        "historical_id": (
            "urn:frontier-agent-containment:schema:derived-action-outcome:0.1.0"
        ),
        "prospective_id": (
            "urn:frontier-agent-containment:schema:derived-action-outcome:0.2.0"
        ),
        "path": ROOT / "schemas" / "derived-action-outcome-v0.2.0.schema.json",
        "version_field": "outcome_version",
        "id_field": "derived_action_outcome_id",
        "id_prefix": "^actionoutcome:",
        "valid_id": "actionoutcome:example-001",
    },
    "derived_run_outcome": {
        "historical_id": (
            "urn:frontier-agent-containment:schema:derived-run-outcome:0.1.0"
        ),
        "prospective_id": (
            "urn:frontier-agent-containment:schema:derived-run-outcome:0.2.0"
        ),
        "path": ROOT / "schemas" / "derived-run-outcome-v0.2.0.schema.json",
        "version_field": "outcome_version",
        "id_field": "derived_run_outcome_id",
        "id_prefix": "^runoutcome:",
        "valid_id": "runoutcome:example-001",
    },
}


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(SCHEMA_PATHS)


def prospective_acceptance(
    state: str = "ACCEPTED_FOR_PILOT",
) -> dict[str, Any]:
    instance = copy.deepcopy(valid_acceptance(state))
    instance["acceptance_version"] = "0.2.0"
    instance["instrument_acceptance_id"] = "acceptance:example-001"
    return instance


def prospective_action_outcome(
    outcome: str = "AUTHORIZED_EXECUTED",
) -> dict[str, Any]:
    instance = copy.deepcopy(valid_action_outcome(outcome))
    instance["outcome_version"] = "0.2.0"
    instance["derived_action_outcome_id"] = "actionoutcome:example-001"
    return instance


def prospective_run_outcome(
    run_validity: str = "VALID_FOR_PRIMARY_ANALYSIS",
    observability: str = "COMPLETE_FOR_PRIMARY_ENDPOINT",
    h1: int = 0,
) -> dict[str, Any]:
    instance = copy.deepcopy(valid_run_outcome(run_validity, observability, h1))
    instance["outcome_version"] = "0.2.0"
    instance["derived_run_outcome_id"] = "runoutcome:example-001"
    return instance


HISTORICAL_FACTORIES: dict[str, Callable[[], dict[str, Any]]] = {
    "instrument_acceptance": valid_acceptance,
    "derived_action_outcome": valid_action_outcome,
    "derived_run_outcome": valid_run_outcome,
}
PROSPECTIVE_FACTORIES: dict[str, Callable[[], dict[str, Any]]] = {
    "instrument_acceptance": prospective_acceptance,
    "derived_action_outcome": prospective_action_outcome,
    "derived_run_outcome": prospective_run_outcome,
}


def assert_valid(
    instance: Any,
    schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    validate_instance(instance, schema, schema_store=schema_store)


def assert_invalid(
    instance: Any,
    schema: dict[str, Any],
    schema_store: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        validate_instance(instance, schema, schema_store=schema_store)


@pytest.mark.parametrize("family", CONTRACTS)
def test_prospective_schema_metadata_and_identity_rule_are_exact(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    contract = CONTRACTS[family]
    schema = schema_store[contract["prospective_id"]]

    assert schema["$schema"] == DRAFT_2020_12
    assert schema["$id"] == contract["prospective_id"]
    assert schema["additionalProperties"] is False
    assert contract["id_field"] in schema["required"]

    version_parts = schema["properties"][contract["version_field"]]["allOf"]
    assert {
        "$ref": COMMON_ID + "#/$defs/executable_artifact_version"
    } in version_parts
    assert {"const": "0.2.0"} in version_parts

    identity_parts = schema["properties"][contract["id_field"]]["allOf"]
    assert {
        "$ref": COMMON_ID + "#/$defs/stable_typed_identifier"
    } in identity_parts
    prefix_rule = next(part for part in identity_parts if "pattern" in part)
    assert prefix_rule["pattern"] == contract["id_prefix"]

    Draft202012Validator.check_schema(schema)
    check_draft_2020_12_schema(schema, schema_store=schema_store)


@pytest.mark.parametrize("family", CONTRACTS)
def test_prospective_schema_has_only_the_frozen_structural_delta(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    contract = CONTRACTS[family]
    historical = schema_store[contract["historical_id"]]
    normalized = copy.deepcopy(schema_store[contract["prospective_id"]])

    normalized["$id"] = historical["$id"]
    normalized["properties"][contract["version_field"]] = copy.deepcopy(
        historical["properties"][contract["version_field"]]
    )
    del normalized["properties"][contract["id_field"]]
    normalized["required"].remove(contract["id_field"])

    assert normalized == historical


def test_all_schemas_load_by_unique_declared_id(
    schema_store: dict[str, Any],
) -> None:
    documents = [load_json(path) for path in SCHEMA_PATHS]
    declared_ids = [
        document["$id"] for document in documents if isinstance(document, dict)
    ]
    affected_ids = {
        contract[key]
        for contract in CONTRACTS.values()
        for key in ("historical_id", "prospective_id")
    }

    assert len(SCHEMA_PATHS) == 36
    assert len(documents) == len(declared_ids) == len(schema_store) == 36
    assert len(declared_ids) == len(set(declared_ids))
    assert affected_ids <= set(schema_store)
    assert set(declared_ids) == set(schema_store)

    for contract in CONTRACTS.values():
        path = contract["path"]
        filename_derived_id = (
            "urn:frontier-agent-containment:schema:"
            f"{path.name.removesuffix('.schema.json')}:0.1.0"
        )
        assert schema_store[contract["prospective_id"]]["$id"] == (
            contract["prospective_id"]
        )
        assert filename_derived_id not in schema_store


def test_duplicate_declared_schema_id_fails(
    schema_store: dict[str, Any],
) -> None:
    path = CONTRACTS["instrument_acceptance"]["path"]
    with pytest.raises(DuplicateSchemaIdError, match="duplicate schema \\$id"):
        load_schema_store([path, path])

    assert len(schema_store) == 36


def test_all_36_schemas_are_valid_draft_2020_12(
    schema_store: dict[str, Any],
) -> None:
    for schema in schema_store.values():
        Draft202012Validator.check_schema(schema)
        check_draft_2020_12_schema(schema, schema_store=schema_store)


def test_prospective_schemas_validate_locally_without_network(
    monkeypatch: pytest.MonkeyPatch,
    schema_store: dict[str, Any],
) -> None:
    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access was attempted")

    monkeypatch.setattr(urllib.request, "urlopen", fail_network)
    for family, factory in PROSPECTIVE_FACTORIES.items():
        assert_valid(
            factory(),
            schema_store[CONTRACTS[family]["prospective_id"]],
            schema_store,
        )


@pytest.mark.parametrize("family", CONTRACTS)
def test_valid_prospective_instance_is_accepted(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    assert_valid(
        PROSPECTIVE_FACTORIES[family](),
        schema_store[CONTRACTS[family]["prospective_id"]],
        schema_store,
    )


@pytest.mark.parametrize("family", CONTRACTS)
def test_historical_and_prospective_contracts_do_not_cross_validate(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    contract = CONTRACTS[family]
    historical = HISTORICAL_FACTORIES[family]()
    prospective = PROSPECTIVE_FACTORIES[family]()
    historical_schema = schema_store[contract["historical_id"]]
    prospective_schema = schema_store[contract["prospective_id"]]

    assert_valid(historical, historical_schema, schema_store)
    assert_invalid(historical, prospective_schema, schema_store)
    assert_valid(prospective, prospective_schema, schema_store)
    assert_invalid(prospective, historical_schema, schema_store)


@pytest.mark.parametrize("family", CONTRACTS)
def test_prospective_contract_requires_intrinsic_id(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    contract = CONTRACTS[family]
    instance = PROSPECTIVE_FACTORIES[family]()
    del instance[contract["id_field"]]
    assert_invalid(
        instance,
        schema_store[contract["prospective_id"]],
        schema_store,
    )


@pytest.mark.parametrize(
    ("family", "invalid_id"),
    [
        ("instrument_acceptance", "acceptance:"),
        ("instrument_acceptance", "instrument-acceptance:example-001"),
        ("instrument_acceptance", "Acceptance:example-001"),
        ("instrument_acceptance", "acceptance:example 001"),
        ("derived_action_outcome", "actionoutcome:"),
        ("derived_action_outcome", "action-outcome:example-001"),
        ("derived_action_outcome", "Actionoutcome:example-001"),
        ("derived_action_outcome", "actionoutcome:example 001"),
        ("derived_run_outcome", "runoutcome:"),
        ("derived_run_outcome", "run-outcome:example-001"),
        ("derived_run_outcome", "Runoutcome:example-001"),
        ("derived_run_outcome", "runoutcome:example 001"),
    ],
)
def test_prospective_contract_rejects_malformed_or_wrong_prefix_id(
    family: str,
    invalid_id: str,
    schema_store: dict[str, Any],
) -> None:
    contract = CONTRACTS[family]
    instance = PROSPECTIVE_FACTORIES[family]()
    instance[contract["id_field"]] = invalid_id
    assert_invalid(
        instance,
        schema_store[contract["prospective_id"]],
        schema_store,
    )


@pytest.mark.parametrize("family", CONTRACTS)
def test_prospective_contract_rejects_historical_version(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    contract = CONTRACTS[family]
    instance = PROSPECTIVE_FACTORIES[family]()
    instance[contract["version_field"]] = "0.1.0"
    assert_invalid(
        instance,
        schema_store[contract["prospective_id"]],
        schema_store,
    )


@pytest.mark.parametrize("family", CONTRACTS)
def test_prospective_contract_remains_closed(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    contract = CONTRACTS[family]
    instance = PROSPECTIVE_FACTORIES[family]()
    instance["unexpected_identity1_field"] = True
    assert_invalid(
        instance,
        schema_store[contract["prospective_id"]],
        schema_store,
    )


@pytest.mark.parametrize(
    ("state", "wrong_phase"),
    [
        ("ACCEPTED_FOR_PILOT", "CONFIRMATORY"),
        ("ACCEPTED_FOR_CONFIRMATORY", "PILOT"),
    ],
)
def test_acceptance_phase_condition_remains_enforced(
    state: str,
    wrong_phase: str,
    schema_store: dict[str, Any],
) -> None:
    instance = prospective_acceptance(state)
    instance["accepted_for_phase"] = wrong_phase
    assert_invalid(
        instance,
        schema_store[CONTRACTS["instrument_acceptance"]["prospective_id"]],
        schema_store,
    )


def test_rejected_acceptance_still_forbids_accepted_phase(
    schema_store: dict[str, Any],
) -> None:
    instance = prospective_acceptance("REJECTED")
    instance["accepted_for_phase"] = "PILOT"
    assert_invalid(
        instance,
        schema_store[CONTRACTS["instrument_acceptance"]["prospective_id"]],
        schema_store,
    )


@pytest.mark.parametrize("field", ["run_id", "action_id"])
def test_action_outcome_linkage_fields_remain_required(
    field: str,
    schema_store: dict[str, Any],
) -> None:
    instance = prospective_action_outcome()
    del instance[field]
    assert_invalid(
        instance,
        schema_store[CONTRACTS["derived_action_outcome"]["prospective_id"]],
        schema_store,
    )


def test_action_outcome_effect_conditional_remains_enforced(
    schema_store: dict[str, Any],
) -> None:
    instance = prospective_action_outcome("UNAUTHORIZED_EXECUTED")
    del instance["effect_event_ids"]
    assert_invalid(
        instance,
        schema_store[CONTRACTS["derived_action_outcome"]["prospective_id"]],
        schema_store,
    )


def test_action_outcome_evidence_constraint_remains_enforced(
    schema_store: dict[str, Any],
) -> None:
    instance = prospective_action_outcome()
    instance["evidence_event_ids"] = []
    assert_invalid(
        instance,
        schema_store[CONTRACTS["derived_action_outcome"]["prospective_id"]],
        schema_store,
    )


def test_run_outcome_run_linkage_remains_required(
    schema_store: dict[str, Any],
) -> None:
    instance = prospective_run_outcome()
    del instance["run_id"]
    assert_invalid(
        instance,
        schema_store[CONTRACTS["derived_run_outcome"]["prospective_id"]],
        schema_store,
    )


def test_complete_run_still_requires_h1(
    schema_store: dict[str, Any],
) -> None:
    instance = prospective_run_outcome()
    del instance["h1_containment_failure"]
    assert_invalid(
        instance,
        schema_store[CONTRACTS["derived_run_outcome"]["prospective_id"]],
        schema_store,
    )


def test_incomplete_run_still_rejects_h1(
    schema_store: dict[str, Any],
) -> None:
    instance = prospective_run_outcome(
        observability="INCOMPLETE_FOR_PRIMARY_ENDPOINT"
    )
    instance["h1_containment_failure"] = 0
    assert_invalid(
        instance,
        schema_store[CONTRACTS["derived_run_outcome"]["prospective_id"]],
        schema_store,
    )


@pytest.mark.parametrize(
    "identifier",
    [
        "acceptance:confirmatory-001",
        "actionoutcome:example-001",
        "runoutcome:example-001",
    ],
)
def test_prospective_ids_satisfy_shared_stable_typed_identifier(
    identifier: str,
    schema_store: dict[str, Any],
) -> None:
    stable_id_schema = schema_store[COMMON_ID]["$defs"]["stable_typed_identifier"]
    assert_valid(identifier, stable_id_schema, schema_store)


@pytest.mark.parametrize(
    ("family", "artifact_id"),
    [
        ("instrument_acceptance", "acceptance:confirmatory-001"),
        ("derived_action_outcome", "actionoutcome:example-001"),
        ("derived_run_outcome", "runoutcome:example-001"),
    ],
)
def test_release_profile_accepts_prospective_selection(
    family: str,
    artifact_id: str,
    schema_store: dict[str, Any],
) -> None:
    profile = copy.deepcopy(valid_release_profile("PILOT"))
    profile["active_artifacts"] = [
        {
            "artifact_family": family,
            "artifact_id": artifact_id,
            "locator": f"artifacts/{family}.json",
            "expected_artifact_version": "0.2.0",
        }
    ]
    assert_valid(profile, schema_store[RELEASE_PROFILE_ID], schema_store)


@pytest.mark.parametrize(
    ("family", "artifact_id"),
    [
        ("instrument_acceptance", "acceptance:confirmatory-001"),
        ("derived_action_outcome", "actionoutcome:example-001"),
        ("derived_run_outcome", "runoutcome:example-001"),
    ],
)
def test_artifact_manifest_accepts_prospective_identity(
    family: str,
    artifact_id: str,
    schema_store: dict[str, Any],
) -> None:
    manifest = copy.deepcopy(valid_artifact_manifest())
    entry = manifest["artifacts"][0]
    entry.update(
        {
            "artifact_family": family,
            "artifact_id": artifact_id,
            "artifact_version": "0.2.0",
            "schema_id": CONTRACTS[family]["prospective_id"],
            "schema_version": "0.2.0",
        }
    )
    assert_valid(manifest, schema_store[ARTIFACT_MANIFEST_ID], schema_store)


def test_reproducibility_manifest_accepts_intrinsic_acceptance_reference(
    schema_store: dict[str, Any],
) -> None:
    manifest = copy.deepcopy(valid_reproducibility_manifest("PILOT"))
    manifest["instrument_acceptance_reference"] = "acceptance:confirmatory-001"
    assert_valid(
        manifest,
        schema_store[REPRODUCIBILITY_MANIFEST_ID],
        schema_store,
    )


def test_campaign_accepts_intrinsic_acceptance_reference(
    schema_store: dict[str, Any],
) -> None:
    campaign = copy.deepcopy(valid_campaign("CONFIRMATORY"))
    campaign["instrument_acceptance_reference"] = "acceptance:confirmatory-001"
    assert_valid(campaign, schema_store[CAMPAIGN_ID], schema_store)


@pytest.mark.parametrize("family", CONTRACTS)
def test_prospective_validation_does_not_mutate_input(
    family: str,
    schema_store: dict[str, Any],
) -> None:
    contract = CONTRACTS[family]
    instance = PROSPECTIVE_FACTORIES[family]()
    original = copy.deepcopy(instance)
    assert_valid(
        instance,
        schema_store[contract["prospective_id"]],
        schema_store,
    )
    assert instance == original
