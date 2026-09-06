"""Stage 1A tests for the generic evidence-admission seam."""

from __future__ import annotations

import copy
import inspect
from pathlib import Path
from typing import Any, Mapping

import pytest

from frontier_agent_containment.integrity import canonical_sha256, canonicalize_json
from frontier_agent_containment.instrument_validation import evidence_outcomes
from frontier_agent_containment.instrument_validation.evidence_outcomes import (
    EvidenceQuality,
    SuppliedEvidence,
    TrustedEvaluatorContext,
    evaluate_evidence_set,
    evaluate_supplied_evidence,
)
from frontier_agent_containment.schema_validation import load_schema_store


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "schemas"
EVENT_SCHEMA_ID = "urn:frontier-agent-containment:schema:evidence-event:0.2.0"


@pytest.fixture(scope="module")
def schema_store() -> dict[str, Any]:
    return load_schema_store(sorted(SCHEMA_ROOT.glob("*.schema.json")))


@pytest.fixture()
def trusted_context() -> TrustedEvaluatorContext:
    return TrustedEvaluatorContext(
        runtime_plan_id="ivplan:generic-admission",
        validation_case_id="ivcase:generic-admission",
        instrument_configuration_id="instrument:generic-admission",
        experiment_id="exp:generic-admission",
        run_id="run:generic-admission",
        scenario_id="scenario:generic-admission",
        agent_condition_id="agentcond:generic-admission",
        capability_envelope_id="envelope:generic-admission",
        policy_id="policy:generic-admission",
        environment_id="env:generic-admission",
        selected_treatments=(),
        runtime_plan_digest="sha256:" + "1" * 64,
        validation_case_digest="sha256:" + "2" * 64,
        run_manifest_digest="sha256:" + "3" * 64,
    )


@pytest.fixture()
def source_registrations() -> dict[str, dict[str, Any]]:
    return {
        "source:request": {
            "source_registration_id": "source:request",
            "source_component_id": "validation_orchestrator",
            "source_role": "EXPERIMENT_ORCHESTRATOR",
            "source_version": "0.1.0",
            "source_build_id": "build:generic-request",
            "instrument_configuration_id": "instrument:generic-admission",
            "dedicated_local_channel_id": "channel_request",
            "authoritative_properties": ["REQUEST"],
        },
        "source:s0": {
            "source_registration_id": "source:s0",
            "source_component_id": "s0_boundary_observer",
            "source_role": "RESOURCE_SERVICE_OBSERVER",
            "source_version": "0.1.0",
            "source_build_id": "build:generic-s0",
            "instrument_configuration_id": "instrument:generic-admission",
            "dedicated_local_channel_id": "channel_s0",
            "authoritative_properties": ["S0_STATE"],
        },
        "source:other": {
            "source_registration_id": "source:other",
            "source_component_id": "other_orchestrator",
            "source_role": "EXPERIMENT_ORCHESTRATOR",
            "source_version": "0.1.0",
            "source_build_id": "build:generic-other",
            "instrument_configuration_id": "instrument:generic-admission",
            "dedicated_local_channel_id": "channel_other",
            "authoritative_properties": [],
        },
    }


def _event_data(event_class: str) -> dict[str, Any]:
    if event_class == "RUN_INITIALIZED":
        return {
            "run_state": "INITIALIZED",
            "phase": "INSTRUMENT_VALIDATION",
            "state_description": "Synthetic generic run initialized.",
            "starting_state_identity": "clean_state",
            "s0_configuration_id": "cond:generic-s0",
            "s0_acceptance_identity": "generic_s0_acceptance",
            "s0_acceptance_passed": True,
        }
    if event_class == "S0_STATE_OBSERVED":
        return {
            "s0_configuration_id": "cond:generic-s0",
            "s0_acceptance_identity": "generic_s0_acceptance",
            "s0_state": "S0_ACCEPTED",
        }
    raise AssertionError(f"unsupported synthetic event class: {event_class}")


def _event(
    trusted_context: TrustedEvaluatorContext,
    source_registrations: Mapping[str, Mapping[str, Any]],
    event_class: str,
    *,
    sequence: int = 1,
    prior: tuple[str, ...] = (),
    event_id: str | None = None,
    source_registration_id: str | None = None,
) -> dict[str, Any]:
    default_sources = {
        "RUN_INITIALIZED": "source:request",
        "S0_STATE_OBSERVED": "source:s0",
    }
    registration_id = source_registration_id or default_sources[event_class]
    registration = source_registrations[registration_id]
    return {
        "event_id": event_id
        or f"event:generic-{event_class.lower().replace('_', '-')}-{sequence}",
        "event_version": "0.2.0",
        "experiment_id": trusted_context.experiment_id,
        "run_id": trusted_context.run_id,
        "scenario_id": trusted_context.scenario_id,
        "condition_id": "cond:generic-admission",
        "event_class": event_class,
        "event_class_rank": 10,
        "source_registration_id": registration_id,
        "source_local_sequence": sequence,
        "authoritative_source": {
            "source_id": registration["source_component_id"],
            "source_role": registration["source_role"],
            "source_version": registration["source_version"],
            "build_id": registration["source_build_id"],
        },
        "instrument_configuration_id": trusted_context.instrument_configuration_id,
        "environment_id": trusted_context.environment_id,
        "evidence_quality_state": "VALID",
        "event_data": _event_data(event_class),
        "prior_event_ids": list(prior),
    }


def _envelope(
    event: Mapping[str, Any],
    source_registrations: Mapping[str, Mapping[str, Any]],
    *,
    receipt_id: str,
) -> dict[str, Any]:
    registration = source_registrations[event["source_registration_id"]]
    return {
        "schema_version": "0.2.0",
        "envelope_version": "0.2.0",
        "receipt_id": receipt_id,
        "instrument_configuration_id": event["instrument_configuration_id"],
        "source_registry_id": "sourceregistry:generic-admission",
        "source_registry_version": "0.1.0",
        "run_id": event["run_id"],
        "event_id": event["event_id"],
        "source_registration_id": event["source_registration_id"],
        "source_component_id": registration["source_component_id"],
        "source_version": registration["source_version"],
        "source_build_id": registration["source_build_id"],
        "dedicated_local_channel_id": registration["dedicated_local_channel_id"],
        "source_local_sequence": event["source_local_sequence"],
        "collector_receipt_sequence": 1,
        "prior_event_ids": list(event["prior_event_ids"]),
        "event_class": event["event_class"],
        "event_class_rank": event["event_class_rank"],
        "normalized_event_schema_id": EVENT_SCHEMA_ID,
        "normalized_event_version": "0.2.0",
        "payload": {
            "content_reference": event["event_id"],
            "media_type": "application/json",
            "byte_length": len(canonicalize_json(event)),
            "content_digest": canonical_sha256(event),
        },
        "evidence_quality_state": "VALID",
        "receipt_state": "RECEIVED",
    }


def _pair(
    event: Mapping[str, Any],
    source_registrations: Mapping[str, Mapping[str, Any]],
    *,
    receipt_id: str,
) -> SuppliedEvidence:
    return SuppliedEvidence(
        _envelope(event, source_registrations, receipt_id=receipt_id),
        event,
    )


def test_generic_entry_point_has_only_resolved_inputs_and_admits_evidence(
    trusted_context: TrustedEvaluatorContext,
    source_registrations: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    parameters = inspect.signature(evaluate_supplied_evidence).parameters
    assert tuple(parameters) == (
        "supplied_evidence",
        "trusted_context",
        "source_registrations",
        "schema_store",
    )
    assert set(parameters).isdisjoint(
        {
            "attack_id",
            "case_attack_id",
            "hidden_d",
            "hidden_x",
            "hidden_e",
            "case_oracle",
            "oracle_answers",
            "mutation_provenance",
            "baseline_id",
            "expected_result",
        }
    )

    initialized = _event(
        trusted_context, source_registrations, "RUN_INITIALIZED"
    )
    evaluation = evaluate_supplied_evidence(
        [_pair(initialized, source_registrations, receipt_id="receipt:initialized")],
        trusted_context=trusted_context,
        source_registrations=source_registrations,
        schema_store=schema_store,
    )

    assert evaluation.trusted_context == trusted_context
    assert evaluation.admission_results[0].admitted
    assert (
        evaluation.admission_results[0].derived_quality_state
        is EvidenceQuality.VALID
    )


def test_iv_wrapper_and_generic_entry_point_are_equivalent_after_resolution(
    monkeypatch: pytest.MonkeyPatch,
    trusted_context: TrustedEvaluatorContext,
    source_registrations: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    initialized = _event(
        trusted_context, source_registrations, "RUN_INITIALIZED"
    )
    supplied = [
        _pair(initialized, source_registrations, receipt_id="receipt:initialized")
    ]

    monkeypatch.setattr(
        evidence_outcomes,
        "validate_trusted_evaluator_context",
        lambda *args, **kwargs: trusted_context,
    )
    monkeypatch.setattr(
        evidence_outcomes,
        "_trusted_registrations",
        lambda runtime_plan: source_registrations,
    )

    generic = evaluate_supplied_evidence(
        supplied,
        trusted_context=trusted_context,
        source_registrations=source_registrations,
        schema_store=schema_store,
    )
    wrapped = evaluate_evidence_set(
        supplied,
        runtime_plan={},
        validation_case={},
        run_manifest={},
        schema_store=schema_store,
    )

    assert wrapped == generic


def test_generic_entry_point_preserves_dag_validation_and_stable_ordering(
    trusted_context: TrustedEvaluatorContext,
    source_registrations: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    initialized = _event(
        trusted_context, source_registrations, "RUN_INITIALIZED"
    )
    s0 = _event(
        trusted_context,
        source_registrations,
        "S0_STATE_OBSERVED",
        prior=(initialized["event_id"],),
    )
    ordered = evaluate_supplied_evidence(
        [
            _pair(s0, source_registrations, receipt_id="receipt:s0"),
            _pair(initialized, source_registrations, receipt_id="receipt:initialized"),
        ],
        trusted_context=trusted_context,
        source_registrations=source_registrations,
        schema_store=schema_store,
    )
    assert ordered.canonical_event_ids == (initialized["event_id"], s0["event_id"])
    assert all(result.admitted for result in ordered.admission_results)

    missing_predecessor = _event(
        trusted_context, source_registrations, "S0_STATE_OBSERVED"
    )
    invalid = evaluate_supplied_evidence(
        [
            _pair(
                initialized,
                source_registrations,
                receipt_id="receipt:initialized",
            ),
            _pair(
                missing_predecessor,
                source_registrations,
                receipt_id="receipt:s0",
            ),
        ],
        trusted_context=trusted_context,
        source_registrations=source_registrations,
        schema_store=schema_store,
    )
    assert (
        invalid.admission_results[1].derived_quality_state
        is EvidenceQuality.OUT_OF_ORDER
    )
    assert (
        EvidenceQuality.MISSING_REQUIRED
        in invalid.admission_results[1].auxiliary_defects
    )


def test_generic_entry_point_preserves_duplicate_and_replay_classification(
    trusted_context: TrustedEvaluatorContext,
    source_registrations: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    initialized = _event(
        trusted_context, source_registrations, "RUN_INITIALIZED"
    )
    duplicate_results = evaluate_supplied_evidence(
        [
            _pair(initialized, source_registrations, receipt_id="receipt:first"),
            _pair(initialized, source_registrations, receipt_id="receipt:second"),
        ],
        trusted_context=trusted_context,
        source_registrations=source_registrations,
        schema_store=schema_store,
    ).admission_results
    assert [result.derived_quality_state for result in duplicate_results] == [
        EvidenceQuality.VALID,
        EvidenceQuality.DUPLICATE,
    ]
    assert duplicate_results[1].duplicate_of_receipt_id == "receipt:first"

    replay = copy.deepcopy(initialized)
    replay["source_local_sequence"] = 2
    replay_results = evaluate_supplied_evidence(
        [
            _pair(initialized, source_registrations, receipt_id="receipt:first"),
            _pair(replay, source_registrations, receipt_id="receipt:second"),
        ],
        trusted_context=trusted_context,
        source_registrations=source_registrations,
        schema_store=schema_store,
    ).admission_results
    assert replay_results[1].derived_quality_state is EvidenceQuality.DUPLICATE
    assert replay_results[1].replay_of_receipt_id == "receipt:first"


def test_generic_entry_point_preserves_source_authority_resolution(
    trusted_context: TrustedEvaluatorContext,
    source_registrations: dict[str, dict[str, Any]],
    schema_store: dict[str, Any],
) -> None:
    initialized = _event(
        trusted_context,
        source_registrations,
        "RUN_INITIALIZED",
        source_registration_id="source:other",
    )
    result = evaluate_supplied_evidence(
        [_pair(initialized, source_registrations, receipt_id="receipt:initialized")],
        trusted_context=trusted_context,
        source_registrations=source_registrations,
        schema_store=schema_store,
    ).admission_results[0]

    assert result.resolved_source_registration_id == "source:other"
    assert result.derived_quality_state is EvidenceQuality.UNTRUSTED_SOURCE
    assert not result.admitted
