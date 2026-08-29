"""Reproducible orchestration for the fixed-candidate Step 0 experiment."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scientific_parallax.step0.evidence import EvidenceEngine
from scientific_parallax.step0.ledger import EvidenceLedger, canonical_json, verify_ledger
from scientific_parallax.step0.paradigms import TRUE_PARADIGM_ID, fixed_paradigms
from scientific_parallax.step0.strategies import SELECTORS
from scientific_parallax.step0.world import MisleadingScienceWorld, finite_question_pool


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    schema_version: int = 1
    protocol_id: str = "step0-v1"
    noise_seed: int = 1729
    max_queries: int = 32
    posterior_threshold: float = 0.95
    quadrature_points: int = 41

    @classmethod
    def from_json(cls, path: Path) -> ExperimentConfig:
        raw = json.loads(path.read_text(encoding="utf-8"))
        fields = cls.__dataclass_fields__
        return cls(**{key: raw[key] for key in fields if key in raw})

    @property
    def config_hash(self) -> str:
        return hashlib.sha256(canonical_json(asdict(self)).encode()).hexdigest()

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported experiment schema version")
        if not 1 <= self.max_queries <= len(finite_question_pool()):
            raise ValueError("max_queries must fit within the finite question pool")
        if not 0.5 < self.posterior_threshold < 1.0:
            raise ValueError("posterior_threshold must be between 0.5 and 1")
        if self.quadrature_points < 9 or self.quadrature_points % 2 == 0:
            raise ValueError("quadrature_points must be odd and at least 9")


@dataclass(frozen=True, slots=True)
class RunResult:
    strategy: str
    seed: int
    queries_executed: int
    sustained_identification_query: int | None
    final_true_posterior: float
    winner_id: str
    config_hash: str
    ledger_path: str
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sustained_threshold(values: list[float], threshold: float) -> int | None:
    """First 1-based query after which all remaining values stay above threshold."""
    suffix_all_above = True
    earliest: int | None = None
    for index in range(len(values) - 1, -1, -1):
        suffix_all_above = suffix_all_above and values[index] >= threshold
        if suffix_all_above:
            earliest = index + 1
    return earliest


def run_experiment(
    config: ExperimentConfig,
    strategy: str,
    output_dir: Path,
    *,
    seed: int | None = None,
) -> RunResult:
    """Run all budgeted queries, preserving a complete evidence trail."""
    config.validate()
    if strategy not in SELECTORS:
        raise ValueError(f"unknown strategy: {strategy}")
    run_seed = config.noise_seed if seed is None else seed
    paradigms = fixed_paradigms()
    evidence = EvidenceEngine([paradigm.paradigm_id for paradigm in paradigms])
    world = MisleadingScienceWorld(run_seed)
    remaining = list(finite_question_pool())
    strategy_rng = random.Random(f"{config.protocol_id}:{strategy}:{run_seed}")

    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = EvidenceLedger(output_dir / "ledger.jsonl")
    ledger.append(
        "run_started",
        {
            "config": asdict(config),
            "config_hash": config.config_hash,
            "strategy": strategy,
            "seed": run_seed,
            "candidate_ids": [paradigm.paradigm_id for paradigm in paradigms],
            "true_candidate_id": TRUE_PARADIGM_ID,
        },
    )

    true_posterior_history: list[float] = []
    selector = SELECTORS[strategy]
    for query_index in range(1, config.max_queries + 1):
        posterior_before = evidence.posterior
        question = selector(
            remaining,
            paradigms,
            posterior_before,
            strategy_rng,
            config.quadrature_points,
        )
        predictions = {paradigm.paradigm_id: paradigm.predict(question) for paradigm in paradigms}
        prediction_hash = ledger.preregister(
            {
                "query_index": query_index,
                "question": question.to_dict(),
                "posterior_before": posterior_before,
                "predictions": {
                    key: prediction.to_dict() for key, prediction in predictions.items()
                },
            }
        )
        observation = world.observe(question)
        posterior_after = evidence.update(predictions, observation)
        ledger.record_observation(
            {
                "query_index": query_index,
                "observation": observation.to_dict(),
                "posterior_after": posterior_after,
            },
            prediction_hash,
        )
        true_posterior_history.append(posterior_after[TRUE_PARADIGM_ID])
        remaining.remove(question)

    posterior = evidence.posterior
    winner_id = max(posterior, key=posterior.__getitem__)
    sustained_query = _sustained_threshold(
        true_posterior_history,
        config.posterior_threshold,
    )
    ledger.append(
        "run_completed",
        {
            "winner_id": winner_id,
            "final_posterior": posterior,
            "sustained_identification_query": sustained_query,
        },
    )
    verify_ledger(ledger.path)
    result = RunResult(
        strategy=strategy,
        seed=run_seed,
        queries_executed=config.max_queries,
        sustained_identification_query=sustained_query,
        final_true_posterior=posterior[TRUE_PARADIGM_ID],
        winner_id=winner_id,
        config_hash=config.config_hash,
        ledger_path=str(ledger.path),
    )
    (output_dir / "result.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
