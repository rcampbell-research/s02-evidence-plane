"""Deterministic orchestration for the frozen S02 adversarial campaign.

This module freezes the Stage 3B dataflow but does not load baselines, choose
runtime dependencies, execute a campaign, or write a result artifact.
"""

from __future__ import annotations

import dataclasses
import hashlib
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias

import yaml

from frontier_agent_containment.integrity import canonicalize_json
from frontier_agent_containment.s02_evidence_plane import (
    BClaimResult,
    S02EvaluationResult,
)
from frontier_agent_containment.s02_scoring import (
    ARTIFACT_3_PATH,
    ARTIFACT_3_SHA256,
    QUESTIONS,
    FrozenOracle,
    OracleReference,
    SafetyClassification,
    localization_correct,
)


RESEARCH_PROGRAM_ID = "s02-evidence-plane"
CAMPAIGN_VERSION = "s02-authoritative-campaign-v0.1"
BASELINES = ("A", "B", "C")
ATTACKS = tuple(f"A{index}" for index in range(1, 15))
PLANNED_CASES = 42
PLANNED_B_EVALUATIONS = 126
PLANNED_LOCALIZATION_ELIGIBLE_B3 = 33


@dataclass(frozen=True, slots=True)
class FrozenPredecessorIdentity:
    stage: str
    tag: str
    peeled_commit: str


@dataclass(frozen=True, slots=True)
class FrozenFileIdentity:
    stage: str
    path: str
    sha256: str


FROZEN_PREDECESSORS = (
    FrozenPredecessorIdentity(
        "Stage 0", "s02-stage0-v0.1", "8f8751ede9fcb2f4f476e4cc63ef037dcd0fc8fa"
    ),
    FrozenPredecessorIdentity(
        "Stage 1", "s02-stage1-v0.1", "4c8c645bd759a5c9f009cd86017be0eaeca72ecb"
    ),
    FrozenPredecessorIdentity(
        "Stage 2", "s02-stage2-v0.1", "09b297f3e9d9d70e7774fe653ad73f2d5dd3c1e4"
    ),
    FrozenPredecessorIdentity(
        "Stage 3A", "s02-stage3a-v0.1", "87603959da2b02165337e48c8dcdd34f2fa603b6"
    ),
)

FROZEN_FILES = (
    FrozenFileIdentity(
        "Stage 0",
        "docs/s02-research-and-analysis-contract-v0.1.md",
        "6ce9d4f6a820cfae1489827ee38a0b51c7d451001028025d6edbe08559b5546f",
    ),
    FrozenFileIdentity(
        "Stage 0",
        "docs/s02-baseline-and-claim-oracle-v0.1.yaml",
        "506b45ea30070664ee79f45006555aeaa2eb4f7d1bc0c8e8ff68adb96f753149",
    ),
    FrozenFileIdentity("Stage 0", ARTIFACT_3_PATH, ARTIFACT_3_SHA256),
    FrozenFileIdentity(
        "Stage 0",
        "docs/s02-stage0-freeze-manifest-v0.1.json",
        "8f741052840059f0058a49b0d1e0e95168667af1ddf03f73513237152c178720",
    ),
    FrozenFileIdentity(
        "Stage 1",
        "src/frontier_agent_containment/instrument_validation/evidence_outcomes.py",
        "a2d0ff7113b8437d1c27016f00b82f2db0c9502e079206c1ff4a5dae3d75c368",
    ),
    FrozenFileIdentity(
        "Stage 1",
        "src/frontier_agent_containment/s02_evidence_plane.py",
        "ae8a81bbcd209ba258cb23917ec723613afe626ae7176a1ababc2083d24d8ed0",
    ),
    FrozenFileIdentity(
        "Stage 1",
        "tests/fixtures/s02/stage1/pristine-baselines.json",
        "df1ebae1b14a451ae4e1aeb7cb5f8e1a890cba1165ad9702f9ac7fb3cb7e1d19",
    ),
    FrozenFileIdentity(
        "Stage 1",
        "tests/s02/test_stage1_minimum.py",
        "a742553b6faa7794061ed332664060de1594496013452ca2634c19a6534903c3",
    ),
    FrozenFileIdentity(
        "Stage 2",
        "src/frontier_agent_containment/s02_mutations.py",
        "4f0c261dcdc69baace0dcb8ddc0a95d24362415a13236c24c111ef15bd4102da",
    ),
    FrozenFileIdentity(
        "Stage 2",
        "tests/s02/test_stage2_mutations.py",
        "5a4e900d9027f90dca136f0de324114302ab3d22813f02b535b529a6ec3a2f94",
    ),
    FrozenFileIdentity(
        "Stage 3A",
        "src/frontier_agent_containment/s02_scoring.py",
        "238c8f4e2ff50c5ee28201ad58e39a0dc197f6e61fd0fa4f4ae3d6a5895d873d",
    ),
    FrozenFileIdentity(
        "Stage 3A",
        "tests/s02/test_stage3_scoring_contract.py",
        "208a0647420f1dee4d7ee21c6c85193778e8f89c689c773eb2e9e3ef888ea3ab",
    ),
)

ProvenanceValue: TypeAlias = str | tuple[str, ...]
MutationProvenance: TypeAlias = tuple[tuple[str, ProvenanceValue], ...]


class CampaignInvariantError(RuntimeError):
    """The authoritative run cannot continue without violating its freeze."""


class CampaignExclusion(Exception):
    """Explicitly mark a predeclared validity/infrastructure exclusion."""

    def __init__(self, reason: str) -> None:
        if type(reason) is not str or not reason:
            raise CampaignInvariantError(
                "an exclusion reason must be a non-empty exact string"
            )
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class CampaignPlanEntry:
    case_id: str
    baseline_id: str
    attack_id: str


@dataclass(frozen=True, slots=True)
class BScoredResult:
    question: str
    evaluator_result: BClaimResult
    oracle_reference: OracleReference
    classification: SafetyClassification


@dataclass(frozen=True, slots=True)
class ExclusionRecord:
    case_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class CaseCampaignResult:
    case_id: str
    attack_id: str
    mutation_provenance: MutationProvenance
    scored_results: tuple[BScoredResult, ...]
    localization_eligible: bool | None
    localization_correct: bool | None
    exclusion: ExclusionRecord | None = None

    @property
    def status(self) -> str:
        return "EXCLUDED" if self.exclusion is not None else "VALID"


@dataclass(frozen=True, slots=True)
class QuestionAggregate:
    question: str
    valid_evaluations: int
    exact_safe_count: int
    exact_safe_rate: float | None
    safe_conservative_count: int
    safe_conservative_rate: float | None
    unsafe_false_establishment_count: int
    unsafe_false_establishment_rate: float | None


@dataclass(frozen=True, slots=True)
class CampaignAggregate:
    planned_cases: int
    valid_cases: int
    planned_B_evaluations: int
    valid_B_evaluations: int
    unsafe_false_establishment_count: int
    unsafe_false_establishment_rate: float | None
    exact_safe_count: int
    exact_safe_rate: float | None
    safe_conservative_count: int
    safe_conservative_rate: float | None
    by_question: tuple[QuestionAggregate, ...]
    planned_localization_eligible_B3: int
    localization_eligible_denominator: int
    correct_localization_numerator: int
    correct_localization_rate: float | None
    complete_corpus_UFER_zero_target_met: bool


@dataclass(frozen=True, slots=True)
class CampaignResult:
    research_program_id: str
    campaign_version: str
    predecessor_identities: tuple[FrozenPredecessorIdentity, ...]
    frozen_files: tuple[FrozenFileIdentity, ...]
    cases: tuple[CaseCampaignResult, ...]
    aggregate: CampaignAggregate

    @property
    def exclusions(self) -> tuple[ExclusionRecord, ...]:
        return tuple(
            case.exclusion for case in self.cases if case.exclusion is not None
        )


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def verify_frozen_predecessors(root: str | Path | None = None) -> None:
    """Fail closed unless every frozen predecessor file has its recorded bytes."""

    repository_root = _repository_root() if root is None else Path(root)
    for identity in FROZEN_FILES:
        path = repository_root / identity.path
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise CampaignInvariantError(
                f"cannot read frozen predecessor {identity.path!r}"
            ) from exc
        if actual != identity.sha256:
            raise CampaignInvariantError(
                f"frozen SHA-256 mismatch for {identity.path!r}: "
                f"expected {identity.sha256}, got {actual}"
            )


def _validate_plan(plan: Sequence[CampaignPlanEntry]) -> tuple[CampaignPlanEntry, ...]:
    frozen = tuple(plan)
    if len(frozen) != PLANNED_CASES or any(
        not isinstance(entry, CampaignPlanEntry) for entry in frozen
    ):
        raise CampaignInvariantError("campaign plan must contain 42 plan entries")
    if len({entry.case_id for entry in frozen}) != PLANNED_CASES:
        raise CampaignInvariantError("campaign plan case IDs must be unique")
    if Counter(entry.baseline_id for entry in frozen) != Counter(
        {baseline: 14 for baseline in BASELINES}
    ):
        raise CampaignInvariantError("campaign plan must contain 14 cases per baseline")
    if set(entry.attack_id for entry in frozen) != set(ATTACKS):
        raise CampaignInvariantError("campaign plan must contain exactly 14 attacks")
    expected_pairs = {(baseline, attack) for baseline in BASELINES for attack in ATTACKS}
    actual_pairs = {(entry.baseline_id, entry.attack_id) for entry in frozen}
    if actual_pairs != expected_pairs or len(actual_pairs) != PLANNED_CASES:
        raise CampaignInvariantError(
            "campaign plan must contain every baseline x attack pair exactly once"
        )
    if len(frozen) * len(QUESTIONS) != PLANNED_B_EVALUATIONS:
        raise CampaignInvariantError("campaign plan must declare 126 B evaluations")
    return frozen


def build_campaign_plan(path: str | Path | None = None) -> tuple[CampaignPlanEntry, ...]:
    """Load and verify Artifact 3 while retaining its declared case order."""

    artifact_path = (
        _repository_root() / ARTIFACT_3_PATH if path is None else Path(path)
    )
    try:
        raw = artifact_path.read_bytes()
    except OSError as exc:
        raise CampaignInvariantError("cannot read frozen Artifact 3") from exc
    actual_digest = hashlib.sha256(raw).hexdigest()
    if actual_digest != ARTIFACT_3_SHA256:
        raise CampaignInvariantError(
            f"Artifact 3 SHA-256 mismatch: expected {ARTIFACT_3_SHA256}, "
            f"got {actual_digest}"
        )
    document = yaml.safe_load(raw)
    if not isinstance(document, Mapping):
        raise CampaignInvariantError("Artifact 3 must be a mapping")
    if document.get("research_program_id") != RESEARCH_PROGRAM_ID:
        raise CampaignInvariantError("Artifact 3 research program identity mismatch")

    attacks = document.get("attack_classes")
    cases = document.get("cases")
    summary = document.get("matrix_summary")
    if not isinstance(attacks, list) or len(attacks) != len(ATTACKS):
        raise CampaignInvariantError("Artifact 3 must contain exactly 14 attacks")
    attack_ids = tuple(
        item.get("attack_id") if isinstance(item, Mapping) else None
        for item in attacks
    )
    if len(set(attack_ids)) != len(ATTACKS) or set(attack_ids) != set(ATTACKS):
        raise CampaignInvariantError("Artifact 3 attack IDs are not the frozen set")
    if not isinstance(cases, list) or len(cases) != PLANNED_CASES:
        raise CampaignInvariantError("Artifact 3 must contain exactly 42 cases")
    if not isinstance(summary, Mapping) or any(
        summary.get(key) != expected
        for key, expected in {
            "attack_classes": 14,
            "baselines": 3,
            "primary_cases": PLANNED_CASES,
            "co_primary_questions_per_case": 3,
            "primary_B_evaluations": PLANNED_B_EVALUATIONS,
        }.items()
    ):
        raise CampaignInvariantError("Artifact 3 matrix summary is not 42/126")

    entries: list[CampaignPlanEntry] = []
    declared_B_evaluations = 0
    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            raise CampaignInvariantError(f"Artifact 3 case {index} is not a mapping")
        case_id = case.get("case_id")
        baseline_id = case.get("baseline_id")
        attack_id = case.get("attack_id")
        strongest = case.get("strongest_safe_claims")
        if not all(type(item) is str and item for item in (case_id, baseline_id, attack_id)):
            raise CampaignInvariantError(f"Artifact 3 case {index} identifiers are malformed")
        if not isinstance(strongest, Mapping) or set(strongest) != set(QUESTIONS):
            raise CampaignInvariantError(
                f"Artifact 3 case {case_id!r} must declare B1/B2/B3"
            )
        declared_B_evaluations += len(strongest)
        entries.append(CampaignPlanEntry(case_id, baseline_id, attack_id))
    if declared_B_evaluations != PLANNED_B_EVALUATIONS:
        raise CampaignInvariantError("Artifact 3 must declare 126 B evaluations")
    return _validate_plan(entries)


_HARNESS_ONLY_KEYS = frozenset(
    {
        "D",
        "E",
        "X",
        "attack_id",
        "baseline_id",
        "baseline_label",
        "case_id",
        "d",
        "e",
        "expected_evidence_effects",
        "expected_result",
        "expected_results",
        "ground_truth",
        "mutation_provenance",
        "oracle",
        "oracle_claim",
        "oracle_claims",
        "provenance",
        "safety_classification",
        "safety_classifications",
        "strongest_safe_claims",
        "x",
    }
)


def _assert_isolated(value: Any, *, path: str = "$", in_schema_store: bool = False) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                raise CampaignInvariantError(
                    f"evaluator projection key at {path} is not a string"
                )
            if not in_schema_store and key in _HARNESS_ONLY_KEYS:
                raise CampaignInvariantError(
                    f"harness-only metadata {key!r} leaked into evaluator projection"
                )
            _assert_isolated(
                item,
                path=f"{path}.{key}",
                in_schema_store=in_schema_store or (path == "$" and key == "schema_store"),
            )
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _assert_isolated(item, path=f"{path}[{index}]", in_schema_store=in_schema_store)
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            _assert_isolated(
                getattr(value, field.name),
                path=f"{path}.{field.name}",
                in_schema_store=in_schema_store,
            )


def _mutation_field(mutation: Any, name: str) -> Any:
    if isinstance(mutation, Mapping):
        if name not in mutation:
            raise CampaignInvariantError(f"mutation result lacks {name!r}")
        return mutation[name]
    try:
        return getattr(mutation, name)
    except AttributeError as exc:
        raise CampaignInvariantError(f"mutation result lacks {name!r}") from exc


def _provenance(value: Any) -> MutationProvenance:
    if not isinstance(value, tuple):
        raise CampaignInvariantError("mutation provenance must be an immutable tuple")
    normalized: list[tuple[str, ProvenanceValue]] = []
    for item in value:
        if not isinstance(item, tuple) or len(item) != 2 or type(item[0]) is not str:
            raise CampaignInvariantError("mutation provenance entries are malformed")
        name, detail = item
        if type(detail) is str:
            normalized.append((name, detail))
        elif isinstance(detail, tuple) and all(type(part) is str for part in detail):
            normalized.append((name, detail))
        else:
            raise CampaignInvariantError("mutation provenance values are malformed")
    if len({name for name, _ in normalized}) != len(normalized):
        raise CampaignInvariantError("mutation provenance keys must be unique")
    return tuple(normalized)


def _rate(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _question_aggregate(
    question: str, results: Sequence[BScoredResult]
) -> QuestionAggregate:
    counts = Counter(result.classification for result in results)
    denominator = len(results)
    exact = counts[SafetyClassification.EXACT_SAFE]
    conservative = counts[SafetyClassification.SAFE_CONSERVATIVE]
    unsafe = counts[SafetyClassification.UNSAFE_FALSE_ESTABLISHMENT]
    if exact + conservative + unsafe != denominator:
        raise CampaignInvariantError("safety classifications are not exhaustive")
    return QuestionAggregate(
        question,
        denominator,
        exact,
        _rate(exact, denominator),
        conservative,
        _rate(conservative, denominator),
        unsafe,
        _rate(unsafe, denominator),
    )


def _aggregate(cases: Sequence[CaseCampaignResult]) -> CampaignAggregate:
    valid = tuple(case for case in cases if case.exclusion is None)
    by_question = tuple(
        _question_aggregate(
            question,
            tuple(
                scored
                for case in valid
                for scored in case.scored_results
                if scored.question == question
            ),
        )
        for question in QUESTIONS
    )
    all_results = tuple(scored for case in valid for scored in case.scored_results)
    overall = _question_aggregate("ALL", all_results)
    if len(all_results) != len(valid) * len(QUESTIONS):
        raise CampaignInvariantError("a valid case does not have exactly three scores")
    eligible = tuple(case for case in valid if case.localization_eligible is True)
    correct = sum(case.localization_correct is True for case in eligible)
    return CampaignAggregate(
        PLANNED_CASES,
        len(valid),
        PLANNED_B_EVALUATIONS,
        len(all_results),
        overall.unsafe_false_establishment_count,
        overall.unsafe_false_establishment_rate,
        overall.exact_safe_count,
        overall.exact_safe_rate,
        overall.safe_conservative_count,
        overall.safe_conservative_rate,
        by_question,
        PLANNED_LOCALIZATION_ELIGIBLE_B3,
        len(eligible),
        correct,
        _rate(correct, len(eligible)),
        len(valid) == PLANNED_CASES
        and overall.unsafe_false_establishment_count == 0,
    )


def _validate_baselines(baseline_inputs: Mapping[str, Mapping[str, Any]]) -> None:
    if not isinstance(baseline_inputs, Mapping) or set(baseline_inputs) != set(BASELINES):
        raise CampaignInvariantError("baseline inputs must contain exactly A, B, and C")
    if any(not isinstance(baseline_inputs[item], Mapping) for item in BASELINES):
        raise CampaignInvariantError("each pristine baseline input must be a mapping")


def _validate_oracle_summary(frozen_oracle: FrozenOracle) -> None:
    if getattr(frozen_oracle, "artifact_sha256", None) != ARTIFACT_3_SHA256:
        raise CampaignInvariantError("frozen oracle Artifact 3 identity mismatch")
    claims = getattr(frozen_oracle, "claims", None)
    if not isinstance(claims, tuple) or len(claims) != PLANNED_B_EVALUATIONS:
        raise CampaignInvariantError("frozen oracle must contain exactly 126 claims")
    eligible = sum(
        claim.reference.question == "B3" and claim.localization_eligible is True
        for claim in claims
    )
    if eligible != PLANNED_LOCALIZATION_ELIGIBLE_B3:
        raise CampaignInvariantError("frozen oracle localization denominator is not 33")


def run_campaign(
    *,
    plan: Sequence[CampaignPlanEntry],
    baseline_inputs: Mapping[str, Mapping[str, Any]],
    mutate: Callable[..., Any],
    evaluate: Callable[..., S02EvaluationResult],
    score: Callable[..., Any],
    frozen_oracle: FrozenOracle,
) -> CampaignResult:
    """Run the already-frozen plan once through narrowly injected dependencies."""

    verify_frozen_predecessors()
    authoritative_plan = build_campaign_plan()
    supplied_plan = _validate_plan(plan)
    if supplied_plan != authoritative_plan:
        raise CampaignInvariantError(
            "campaign plan must preserve the exact frozen Artifact 3 ordering"
        )
    _validate_baselines(baseline_inputs)
    _validate_oracle_summary(frozen_oracle)

    case_results: list[CaseCampaignResult] = []
    for entry in supplied_plan:
        try:
            mutation = mutate(
                case_id=entry.case_id,
                attack_id=entry.attack_id,
                evaluator_input=baseline_inputs[entry.baseline_id],
            )
        except CampaignExclusion as exc:
            exclusion = ExclusionRecord(entry.case_id, exc.reason)
            case_results.append(
                CaseCampaignResult(
                    entry.case_id, entry.attack_id, (), (), None, None, exclusion
                )
            )
            continue

        if _mutation_field(mutation, "case_id") != entry.case_id:
            raise CampaignInvariantError("mutation result case ID mismatch")
        if _mutation_field(mutation, "attack_id") != entry.attack_id:
            raise CampaignInvariantError("mutation result attack ID mismatch")
        provenance = _provenance(_mutation_field(mutation, "provenance"))
        evaluator_input = _mutation_field(mutation, "evaluator_input")
        if not isinstance(evaluator_input, Mapping):
            raise CampaignInvariantError("mutated evaluator projection must be a mapping")
        _assert_isolated(evaluator_input)

        try:
            evaluated = evaluate(**dict(evaluator_input))
        except CampaignExclusion as exc:
            exclusion = ExclusionRecord(entry.case_id, exc.reason)
            case_results.append(
                CaseCampaignResult(
                    entry.case_id,
                    entry.attack_id,
                    provenance,
                    (),
                    None,
                    None,
                    exclusion,
                )
            )
            continue
        if not isinstance(evaluated, S02EvaluationResult):
            raise CampaignInvariantError(
                "evaluator must return one structured B1/B2/B3 result"
            )

        scored_results: list[BScoredResult] = []
        localization_eligible: bool | None = None
        correct_localization: bool | None = None
        for question in QUESTIONS:
            evaluator_result = getattr(evaluated, question)
            if not isinstance(evaluator_result, BClaimResult):
                raise CampaignInvariantError(
                    f"evaluator {question} result is not a BClaimResult"
                )

            # The case-specific oracle is deliberately retrieved only after the
            # evaluator has produced all three outputs.
            oracle_claim = frozen_oracle.claim(entry.case_id, question)
            if (
                oracle_claim.reference.case_id != entry.case_id
                or oracle_claim.reference.question != question
            ):
                raise CampaignInvariantError("frozen oracle claim/reference mismatch")
            claim_score = score(
                question=question,
                evaluator_result=evaluator_result,
                oracle_claim=oracle_claim,
            )
            if getattr(claim_score, "question", None) != question:
                raise CampaignInvariantError("scorer question mismatch")
            if getattr(claim_score, "oracle_reference", None) != oracle_claim.reference:
                raise CampaignInvariantError("scorer oracle-reference mismatch")
            classification = getattr(claim_score, "classification", None)
            if not isinstance(classification, SafetyClassification):
                raise CampaignInvariantError("scorer returned an invalid classification")
            scored_results.append(
                BScoredResult(
                    question,
                    evaluator_result,
                    oracle_claim.reference,
                    classification,
                )
            )
            if question == "B3":
                localization_eligible = oracle_claim.localization_eligible
                if not isinstance(localization_eligible, bool):
                    raise CampaignInvariantError(
                        "B3 oracle claim lacks localization eligibility"
                    )
                if localization_eligible:
                    correct_localization = localization_correct(
                        claim_score.evaluator_profile, claim_score.oracle_profile
                    )

        case_results.append(
            CaseCampaignResult(
                entry.case_id,
                entry.attack_id,
                provenance,
                tuple(scored_results),
                localization_eligible,
                correct_localization,
            )
        )

    frozen_cases = tuple(case_results)
    if len(frozen_cases) != PLANNED_CASES:
        raise CampaignInvariantError("campaign did not retain all 42 case records")
    return CampaignResult(
        RESEARCH_PROGRAM_ID,
        CAMPAIGN_VERSION,
        FROZEN_PREDECESSORS,
        FROZEN_FILES,
        frozen_cases,
        _aggregate(frozen_cases),
    )


def _claim_document(result: BClaimResult) -> dict[str, Any]:
    return {
        "disposition": result.disposition.value,
        "bounded_proposition": result.bounded_proposition,
        "evidence_basis": list(result.evidence_basis),
        "scope_qualifier": result.scope_qualifier,
        "supported_boundary": (
            None if result.supported_boundary is None else list(result.supported_boundary)
        ),
    }


def _category_document(value: QuestionAggregate) -> dict[str, Any]:
    return {
        "valid_evaluations": value.valid_evaluations,
        "exact_safe_count": value.exact_safe_count,
        "exact_safe_rate": value.exact_safe_rate,
        "safe_conservative_count": value.safe_conservative_count,
        "safe_conservative_rate": value.safe_conservative_rate,
        "unsafe_false_establishment_count": value.unsafe_false_establishment_count,
        "unsafe_false_establishment_rate": value.unsafe_false_establishment_rate,
    }


def serialize_campaign_result(result: CampaignResult) -> bytes:
    """Return RFC 8785 canonical bytes without embedding a self-digest."""

    if not isinstance(result, CampaignResult):
        raise TypeError("result must be a CampaignResult")
    case_documents: list[dict[str, Any]] = []
    for case in result.cases:
        document: dict[str, Any] = {
            "case_id": case.case_id,
            "attack_id": case.attack_id,
            "status": case.status,
            "harness_only_mutation_provenance": [
                {
                    "name": name,
                    "value": list(value) if isinstance(value, tuple) else value,
                }
                for name, value in case.mutation_provenance
            ],
        }
        if case.exclusion is not None:
            document["exclusion_reason"] = case.exclusion.reason
        else:
            document["evaluations"] = {
                scored.question: {
                    "evaluator_result": _claim_document(scored.evaluator_result),
                    "oracle_reference": {
                        "case_id": scored.oracle_reference.case_id,
                        "question": scored.oracle_reference.question,
                        "path": scored.oracle_reference.path,
                        "claim_digest": scored.oracle_reference.claim_digest,
                    },
                    "safety_classification": scored.classification.value,
                }
                for scored in case.scored_results
            }
            document["B3_localization"] = {
                "eligible": case.localization_eligible,
                "correct": case.localization_correct,
            }
        case_documents.append(document)

    aggregate = result.aggregate
    payload = {
        "research_program_id": result.research_program_id,
        "campaign_version": result.campaign_version,
        "predecessor_identities": [
            {
                "stage": item.stage,
                "tag": item.tag,
                "peeled_commit": item.peeled_commit,
            }
            for item in result.predecessor_identities
        ],
        "frozen_sha256": [
            {"stage": item.stage, "path": item.path, "sha256": item.sha256}
            for item in result.frozen_files
        ],
        "exclusions": [
            {"case_id": item.case_id, "reason": item.reason}
            for item in result.exclusions
        ],
        "cases": case_documents,
        "aggregate": {
            "planned_cases": aggregate.planned_cases,
            "valid_cases": aggregate.valid_cases,
            "planned_B_evaluations": aggregate.planned_B_evaluations,
            "valid_B_evaluations": aggregate.valid_B_evaluations,
            "unsafe_false_establishment_count": (
                aggregate.unsafe_false_establishment_count
            ),
            "UNSAFE_FALSE_ESTABLISHMENT_RATE": (
                aggregate.unsafe_false_establishment_rate
            ),
            "exact_safe_count": aggregate.exact_safe_count,
            "exact_safe_rate": aggregate.exact_safe_rate,
            "safe_conservative_count": aggregate.safe_conservative_count,
            "safe_conservative_rate": aggregate.safe_conservative_rate,
            "by_question": {
                item.question: _category_document(item)
                for item in aggregate.by_question
            },
            "localization": {
                "planned_localization_eligible_B3": (
                    aggregate.planned_localization_eligible_B3
                ),
                "localization_eligible_denominator": (
                    aggregate.localization_eligible_denominator
                ),
                "correct_localization_numerator": (
                    aggregate.correct_localization_numerator
                ),
                "correct_localization_rate": aggregate.correct_localization_rate,
            },
            "complete_corpus_UFER_zero_target_met": (
                aggregate.complete_corpus_UFER_zero_target_met
            ),
        },
    }
    return canonicalize_json(payload)


__all__ = [
    "ATTACKS",
    "BASELINES",
    "CAMPAIGN_VERSION",
    "FROZEN_FILES",
    "FROZEN_PREDECESSORS",
    "PLANNED_B_EVALUATIONS",
    "PLANNED_CASES",
    "PLANNED_LOCALIZATION_ELIGIBLE_B3",
    "RESEARCH_PROGRAM_ID",
    "BScoredResult",
    "CampaignAggregate",
    "CampaignExclusion",
    "CampaignInvariantError",
    "CampaignPlanEntry",
    "CampaignResult",
    "CaseCampaignResult",
    "ExclusionRecord",
    "FrozenFileIdentity",
    "FrozenPredecessorIdentity",
    "QuestionAggregate",
    "build_campaign_plan",
    "run_campaign",
    "serialize_campaign_result",
    "verify_frozen_predecessors",
]
