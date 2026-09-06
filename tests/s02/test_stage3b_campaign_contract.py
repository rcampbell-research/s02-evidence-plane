"""Stage 3B campaign orchestration tests using synthetic dependencies only."""

from __future__ import annotations

import inspect
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import pytest

import frontier_agent_containment.s02_campaign as campaign_module
from frontier_agent_containment.s02_campaign import (
    ATTACKS,
    BASELINES,
    CAMPAIGN_VERSION,
    FROZEN_FILES,
    FROZEN_PREDECESSORS,
    PLANNED_B_EVALUATIONS,
    PLANNED_CASES,
    PLANNED_LOCALIZATION_ELIGIBLE_B3,
    RESEARCH_PROGRAM_ID,
    CampaignExclusion,
    CampaignInvariantError,
    CampaignPlanEntry,
    FrozenFileIdentity,
    build_campaign_plan,
    run_campaign,
    serialize_campaign_result,
    verify_frozen_predecessors,
)
from frontier_agent_containment.s02_evidence_plane import (
    BClaimResult,
    ClaimDisposition,
    S02EvaluationResult,
)
from frontier_agent_containment.s02_scoring import (
    ARTIFACT_3_SHA256,
    INVOCATION_PREVENTED_BOUNDARY,
    ClaimProfile,
    ClaimScope,
    ClaimScore,
    FrozenOracle,
    SafetyClassification,
    ScopeLevel,
    ScoringInputError,
    load_frozen_s02_oracle,
)


FORBIDDEN_EVALUATOR_KEYS = {
    "D",
    "X",
    "E",
    "case_id",
    "attack_id",
    "baseline_id",
    "baseline_label",
    "ground_truth",
    "mutation_provenance",
    "provenance",
    "oracle",
    "oracle_claim",
    "expected_results",
    "safety_classifications",
}


@pytest.fixture(scope="module")
def plan() -> tuple[CampaignPlanEntry, ...]:
    return build_campaign_plan()


@pytest.fixture(scope="module")
def oracle() -> FrozenOracle:
    return load_frozen_s02_oracle()


@pytest.fixture()
def baseline_inputs() -> dict[str, dict[str, str]]:
    return {
        baseline: {"visible_evidence": f"synthetic-pristine-{baseline}"}
        for baseline in BASELINES
    }


@dataclass(frozen=True, slots=True)
class _SyntheticMutationResult:
    case_id: str
    attack_id: str
    evaluator_input: Mapping[str, Any]
    provenance: tuple[tuple[str, str | tuple[str, ...]], ...]


def _synthetic_claim(question: str) -> BClaimResult:
    return BClaimResult(
        disposition=ClaimDisposition.INCONCLUSIVE,
        bounded_proposition=f"Synthetic {question} result; not an adversarial output.",
        evidence_basis=("synthetic:evidence",),
        scope_qualifier="Synthetic scope; not scored semantically.",
    )


class _TrackingOracle:
    def __init__(self, oracle: FrozenOracle, events: list[tuple[str, str]]) -> None:
        self.artifact_path = oracle.artifact_path
        self.artifact_sha256 = oracle.artifact_sha256
        self.claims = oracle.claims
        self._oracle = oracle
        self._events = events

    def claim(self, case_id: str, question: str):
        self._events.append((f"oracle:{question}", case_id))
        return self._oracle.claim(case_id, question)


class _SyntheticDependencies:
    def __init__(
        self,
        *,
        classifications: Mapping[
            tuple[str, str], SafetyClassification
        ] | None = None,
        excluded_case: str | None = None,
        exclusion_reason: str = "synthetic predeclared infrastructure failure",
    ) -> None:
        self.classifications = dict(classifications or {})
        self.excluded_case = excluded_case
        self.exclusion_reason = exclusion_reason
        self.events: list[tuple[str, str]] = []
        self.mutation_calls: list[str] = []
        self.evaluator_calls: list[str] = []
        self.score_calls: list[tuple[str, str]] = []
        self.evaluator_inputs: list[dict[str, Any]] = []
        self._current_case: str | None = None

    def mutate(
        self, *, case_id: str, attack_id: str, evaluator_input: Mapping[str, Any]
    ) -> _SyntheticMutationResult:
        self._current_case = case_id
        self.mutation_calls.append(case_id)
        self.events.append(("mutate", case_id))
        if case_id == self.excluded_case:
            raise CampaignExclusion(self.exclusion_reason)
        return _SyntheticMutationResult(
            case_id=case_id,
            attack_id=attack_id,
            evaluator_input={"visible_evidence": evaluator_input["visible_evidence"]},
            provenance=(("synthetic_operator", attack_id),),
        )

    def evaluate(self, **evaluator_input: Any) -> S02EvaluationResult:
        assert self._current_case is not None
        case_id = self._current_case
        self.evaluator_calls.append(case_id)
        self.evaluator_inputs.append(evaluator_input)
        self.events.append(("evaluate", case_id))
        return S02EvaluationResult(
            B1=_synthetic_claim("B1"),
            B2=_synthetic_claim("B2"),
            B3=_synthetic_claim("B3"),
        )

    def score(self, *, question: str, evaluator_result, oracle_claim) -> ClaimScore:
        case_id = oracle_claim.reference.case_id
        self.score_calls.append((case_id, question))
        self.events.append((f"score:{question}", case_id))
        classification = self.classifications.get(
            (case_id, question), SafetyClassification.EXACT_SAFE
        )
        scope = ClaimScope(ScopeLevel.LOCAL_BOUNDARY, frozenset())
        boundaries = (
            frozenset({INVOCATION_PREVENTED_BOUNDARY})
            if question == "B3" and oracle_claim.localization_eligible is True
            else frozenset()
        )
        evaluator_profile = ClaimProfile(
            question, frozenset(), frozenset(), scope, boundaries
        )
        oracle_profile = ClaimProfile(
            question, frozenset(), frozenset(), scope, boundaries
        )
        return ClaimScore(
            question,
            classification,
            evaluator_profile,
            oracle_profile,
            oracle_claim.reference,
        )


def _run(
    plan: tuple[CampaignPlanEntry, ...],
    baseline_inputs: Mapping[str, Mapping[str, Any]],
    oracle: FrozenOracle,
    dependencies: _SyntheticDependencies,
):
    tracking_oracle = _TrackingOracle(oracle, dependencies.events)
    return run_campaign(
        plan=plan,
        baseline_inputs=baseline_inputs,
        mutate=dependencies.mutate,
        evaluate=dependencies.evaluate,
        score=dependencies.score,
        frozen_oracle=tracking_oracle,  # type: ignore[arg-type]
    )


def _mapping_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        return set(value).union(
            *(_mapping_keys(item) for item in value.values()), set()
        )
    if isinstance(value, (list, tuple)):
        return set().union(*(_mapping_keys(item) for item in value), set())
    return set()


def test_frozen_plan_loads_without_execution_and_preserves_matrix_order(
    plan: tuple[CampaignPlanEntry, ...],
) -> None:
    evaluator_calls = 0

    def evaluator_that_must_not_run(**_: Any) -> None:
        nonlocal evaluator_calls
        evaluator_calls += 1

    assert evaluator_calls == 0
    assert len(plan) == PLANNED_CASES
    assert len({entry.case_id for entry in plan}) == PLANNED_CASES
    assert Counter(entry.baseline_id for entry in plan) == {
        baseline: 14 for baseline in BASELINES
    }
    assert {entry.attack_id for entry in plan} == set(ATTACKS)
    assert tuple((entry.baseline_id, entry.attack_id) for entry in plan) == tuple(
        (baseline, attack) for baseline in BASELINES for attack in ATTACKS
    )
    assert len(plan) * 3 == PLANNED_B_EVALUATIONS
    assert evaluator_calls == 0
    assert evaluator_that_must_not_run is not None


def test_complete_campaign_has_exact_calls_isolation_and_oracle_order(
    plan: tuple[CampaignPlanEntry, ...],
    baseline_inputs: Mapping[str, Mapping[str, Any]],
    oracle: FrozenOracle,
) -> None:
    dependencies = _SyntheticDependencies()
    result = _run(plan, baseline_inputs, oracle, dependencies)

    assert dependencies.mutation_calls == [entry.case_id for entry in plan]
    assert dependencies.evaluator_calls == [entry.case_id for entry in plan]
    assert len(dependencies.score_calls) == PLANNED_B_EVALUATIONS
    assert set(Counter(dependencies.mutation_calls).values()) == {1}
    assert set(Counter(dependencies.evaluator_calls).values()) == {1}
    assert set(Counter(dependencies.score_calls).values()) == {1}
    assert all(set(item) == {"visible_evidence"} for item in dependencies.evaluator_inputs)
    assert all(
        _mapping_keys(item).isdisjoint(FORBIDDEN_EVALUATOR_KEYS)
        for item in dependencies.evaluator_inputs
    )
    for entry in plan:
        case_events = [name for name, case_id in dependencies.events if case_id == entry.case_id]
        assert case_events == [
            "mutate",
            "evaluate",
            "oracle:B1",
            "score:B1",
            "oracle:B2",
            "score:B2",
            "oracle:B3",
            "score:B3",
        ]
    assert tuple(case.case_id for case in result.cases) == tuple(
        entry.case_id for entry in plan
    )
    assert all(len(case.scored_results) == 3 for case in result.cases)


def test_unsafe_result_does_not_stop_or_retry_later_cases(
    plan: tuple[CampaignPlanEntry, ...],
    baseline_inputs: Mapping[str, Mapping[str, Any]],
    oracle: FrozenOracle,
) -> None:
    unsafe_key = (plan[0].case_id, "B1")
    dependencies = _SyntheticDependencies(
        classifications={unsafe_key: SafetyClassification.UNSAFE_FALSE_ESTABLISHMENT}
    )
    result = _run(plan, baseline_inputs, oracle, dependencies)

    assert dependencies.evaluator_calls[-1] == plan[-1].case_id
    assert set(Counter(dependencies.evaluator_calls).values()) == {1}
    assert result.aggregate.unsafe_false_establishment_count == 1
    assert not result.aggregate.complete_corpus_UFER_zero_target_met


def test_exclusion_is_preserved_reduces_denominator_and_blocks_target(
    plan: tuple[CampaignPlanEntry, ...],
    baseline_inputs: Mapping[str, Mapping[str, Any]],
    oracle: FrozenOracle,
) -> None:
    excluded = plan[0].case_id
    reason = "synthetic declared collector outage"
    dependencies = _SyntheticDependencies(
        excluded_case=excluded, exclusion_reason=reason
    )
    result = _run(plan, baseline_inputs, oracle, dependencies)

    assert len(dependencies.mutation_calls) == PLANNED_CASES
    assert len(dependencies.evaluator_calls) == PLANNED_CASES - 1
    assert len(dependencies.score_calls) == PLANNED_B_EVALUATIONS - 3
    assert [(item.case_id, item.reason) for item in result.exclusions] == [
        (excluded, reason)
    ]
    excluded_record = result.cases[0]
    assert excluded_record.status == "EXCLUDED"
    assert excluded_record.scored_results == ()
    assert result.aggregate.planned_cases == 42
    assert result.aggregate.valid_cases == 41
    assert result.aggregate.planned_B_evaluations == 126
    assert result.aggregate.valid_B_evaluations == 123
    assert result.aggregate.unsafe_false_establishment_count == 0
    assert not result.aggregate.complete_corpus_UFER_zero_target_met


def test_scoring_input_and_invariant_failures_abort_without_retry(
    plan: tuple[CampaignPlanEntry, ...],
    baseline_inputs: Mapping[str, Mapping[str, Any]],
    oracle: FrozenOracle,
) -> None:
    dependencies = _SyntheticDependencies()

    def rejected_score(**_: Any) -> None:
        raise ScoringInputError("synthetic unknown semantic form")

    with pytest.raises(ScoringInputError, match="unknown semantic form"):
        run_campaign(
            plan=plan,
            baseline_inputs=baseline_inputs,
            mutate=dependencies.mutate,
            evaluate=dependencies.evaluate,
            score=rejected_score,
            frozen_oracle=oracle,
        )
    assert dependencies.mutation_calls == [plan[0].case_id]
    assert dependencies.evaluator_calls == [plan[0].case_id]

    leaked_dependencies = _SyntheticDependencies()

    def leaking_mutation(**kwargs: Any) -> _SyntheticMutationResult:
        result = leaked_dependencies.mutate(**kwargs)
        return _SyntheticMutationResult(
            result.case_id,
            result.attack_id,
            {"visible_evidence": "synthetic", "oracle": "must-not-cross"},
            result.provenance,
        )

    with pytest.raises(CampaignInvariantError, match="harness-only metadata"):
        run_campaign(
            plan=plan,
            baseline_inputs=baseline_inputs,
            mutate=leaking_mutation,
            evaluate=leaked_dependencies.evaluate,
            score=leaked_dependencies.score,
            frozen_oracle=oracle,
        )
    assert leaked_dependencies.evaluator_calls == []


def test_complete_aggregates_are_exhaustive_and_localization_is_frozen(
    plan: tuple[CampaignPlanEntry, ...],
    baseline_inputs: Mapping[str, Mapping[str, Any]],
    oracle: FrozenOracle,
) -> None:
    classifications = {
        (entry.case_id, question): (
            SafetyClassification.EXACT_SAFE
            if index % 3 == 0
            else SafetyClassification.SAFE_CONSERVATIVE
            if index % 3 == 1
            else SafetyClassification.UNSAFE_FALSE_ESTABLISHMENT
        )
        for index, (entry, question) in enumerate(
            (entry, question) for entry in plan for question in ("B1", "B2", "B3")
        )
    }
    result = _run(
        plan,
        baseline_inputs,
        oracle,
        _SyntheticDependencies(classifications=classifications),
    )
    aggregate = result.aggregate

    assert aggregate.valid_B_evaluations == 126
    assert (
        aggregate.exact_safe_count
        + aggregate.safe_conservative_count
        + aggregate.unsafe_false_establishment_count
        == 126
    )
    assert tuple(item.question for item in aggregate.by_question) == (
        "B1",
        "B2",
        "B3",
    )
    for item in aggregate.by_question:
        assert item.valid_evaluations == 42
        assert (
            item.exact_safe_count
            + item.safe_conservative_count
            + item.unsafe_false_establishment_count
            == 42
        )
    assert aggregate.planned_localization_eligible_B3 == 33
    assert aggregate.localization_eligible_denominator == 33
    assert aggregate.correct_localization_numerator == 33
    assert aggregate.correct_localization_rate == 1.0


def test_localization_eligibility_changes_only_localization_denominator(
    plan: tuple[CampaignPlanEntry, ...],
    baseline_inputs: Mapping[str, Mapping[str, Any]],
    oracle: FrozenOracle,
) -> None:
    eligible_case = next(
        entry.case_id
        for entry in plan
        if oracle.claim(entry.case_id, "B3").localization_eligible is True
    )
    ineligible_case = next(
        entry.case_id
        for entry in plan
        if oracle.claim(entry.case_id, "B3").localization_eligible is False
    )
    eligible_excluded = _run(
        plan,
        baseline_inputs,
        oracle,
        _SyntheticDependencies(excluded_case=eligible_case),
    ).aggregate
    ineligible_excluded = _run(
        plan,
        baseline_inputs,
        oracle,
        _SyntheticDependencies(excluded_case=ineligible_case),
    ).aggregate

    assert eligible_excluded.valid_B_evaluations == 123
    assert ineligible_excluded.valid_B_evaluations == 123
    assert eligible_excluded.exact_safe_count == 123
    assert ineligible_excluded.exact_safe_count == 123
    assert eligible_excluded.localization_eligible_denominator == 32
    assert ineligible_excluded.localization_eligible_denominator == 33


def test_serialization_is_canonical_repeatable_and_auditable(
    plan: tuple[CampaignPlanEntry, ...],
    baseline_inputs: Mapping[str, Mapping[str, Any]],
    oracle: FrozenOracle,
) -> None:
    result = _run(plan, baseline_inputs, oracle, _SyntheticDependencies())
    first = serialize_campaign_result(result)
    second = serialize_campaign_result(result)
    document = json.loads(first)

    assert first == second
    assert document["research_program_id"] == RESEARCH_PROGRAM_ID
    assert document["campaign_version"] == CAMPAIGN_VERSION
    assert document["predecessor_identities"] == [
        {
            "stage": item.stage,
            "tag": item.tag,
            "peeled_commit": item.peeled_commit,
        }
        for item in FROZEN_PREDECESSORS
    ]
    assert document["frozen_sha256"] == [
        {"stage": item.stage, "path": item.path, "sha256": item.sha256}
        for item in FROZEN_FILES
    ]
    assert len(document["cases"]) == 42
    assert set(document["cases"][0]["evaluations"]) == {"B1", "B2", "B3"}
    assert "result_sha256" not in _mapping_keys(document)
    assert "D" not in _mapping_keys(document["cases"][0]["evaluations"])
    assert "X" not in _mapping_keys(document["cases"][0]["evaluations"])
    assert "E" not in _mapping_keys(document["cases"][0]["evaluations"])


def test_frozen_hashes_and_mismatch_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verify_frozen_predecessors()
    assert tuple(item.sha256 for item in FROZEN_FILES) == (
        "6ce9d4f6a820cfae1489827ee38a0b51c7d451001028025d6edbe08559b5546f",
        "506b45ea30070664ee79f45006555aeaa2eb4f7d1bc0c8e8ff68adb96f753149",
        "58f05ad3103b99143aecb6b424d1939bc657032c773262b9916e1b84b6f15645",
        "8f741052840059f0058a49b0d1e0e95168667af1ddf03f73513237152c178720",
        "a2d0ff7113b8437d1c27016f00b82f2db0c9502e079206c1ff4a5dae3d75c368",
        "ae8a81bbcd209ba258cb23917ec723613afe626ae7176a1ababc2083d24d8ed0",
        "df1ebae1b14a451ae4e1aeb7cb5f8e1a890cba1165ad9702f9ac7fb3cb7e1d19",
        "a742553b6faa7794061ed332664060de1594496013452ca2634c19a6534903c3",
        "4f0c261dcdc69baace0dcb8ddc0a95d24362415a13236c24c111ef15bd4102da",
        "5a4e900d9027f90dca136f0de324114302ab3d22813f02b535b529a6ec3a2f94",
        "238c8f4e2ff50c5ee28201ad58e39a0dc197f6e61fd0fa4f4ae3d6a5895d873d",
        "208a0647420f1dee4d7ee21c6c85193778e8f89c689c773eb2e9e3ef888ea3ab",
    )
    (tmp_path / "changed").write_bytes(b"changed")
    monkeypatch.setattr(
        campaign_module,
        "FROZEN_FILES",
        (FrozenFileIdentity("synthetic", "changed", "0" * 64),),
    )
    with pytest.raises(CampaignInvariantError, match="frozen SHA-256 mismatch"):
        verify_frozen_predecessors(tmp_path)


def test_runner_has_no_authoritative_execution_dependency() -> None:
    source = inspect.getsource(campaign_module)
    assert "mutate_s02_case" not in source
    assert "evaluate_s02_evidence" not in source
    assert "write_bytes" not in source
    assert ARTIFACT_3_SHA256 in {item.sha256 for item in FROZEN_FILES}
