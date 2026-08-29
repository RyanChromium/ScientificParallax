"""Gray–Scott fixed-candidate and fixed-representation Step 3 baselines."""

from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from scientific_parallax.baselines.surrogate import BootstrapEnsemble, FixedFeatureRegressor
from scientific_parallax.core.reproducibility import (
    ExperimentIdentity,
    RunManifest,
    capture_environment,
    content_hash,
)
from scientific_parallax.step0.ledger import EvidenceLedger, verify_ledger
from scientific_parallax.worlds.gray_scott import (
    GrayScottExperiment,
    GrayScottParameters,
    GrayScottWorld,
    LocalPulse,
    MeasurementSpec,
    ReactionLaw,
)

StrategyName = Literal[
    "random",
    "coverage",
    "active_learning",
    "max_disagreement",
    "bayesian_design",
]


@dataclass(frozen=True, slots=True)
class GrayScottBaselineConfig:
    schema_version: int = 1
    protocol_id: str = "gray-scott-baseline-v1"
    seed: int = 31415
    grid_size: int = 24
    steps: int = 60
    max_queries: int = 16
    posterior_threshold: float = 0.95
    replicates: int = 12
    bed_samples: int = 48

    @classmethod
    def from_json(cls, path: Path) -> GrayScottBaselineConfig:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(**{name: payload[name] for name in cls.__dataclass_fields__ if name in payload})

    def validate(self) -> None:
        if self.schema_version != 1 or self.grid_size < 16 or self.steps < 20:
            raise ValueError("invalid baseline schema or simulation size")
        if self.max_queries < 1 or self.replicates < 1 or self.bed_samples < 8:
            raise ValueError("query, replicate, and BED sample counts must be positive")


@dataclass(frozen=True, slots=True)
class FixedParadigmCandidate:
    candidate_id: str
    law: ReactionLaw
    description: str


def fixed_candidate_pool() -> tuple[FixedParadigmCandidate, ...]:
    return (
        FixedParadigmCandidate("standard", ReactionLaw(), "standard Gray–Scott law"),
        FixedParadigmCandidate("reaction_p1.95", ReactionLaw(reaction_power=1.95), "v^1.95"),
        FixedParadigmCandidate("reaction_p2.05", ReactionLaw(reaction_power=2.05), "v^2.05"),
        FixedParadigmCandidate("reaction_low", ReactionLaw(reaction_scale=0.95), "weak reaction"),
        FixedParadigmCandidate(
            "reaction_high", ReactionLaw(reaction_scale=1.05), "strong reaction"
        ),
        FixedParadigmCandidate("feed_low", ReactionLaw(feed_scale=0.96), "weak feed"),
        FixedParadigmCandidate("kill_high", ReactionLaw(kill_offset=0.002), "extra kill"),
        FixedParadigmCandidate(
            "diffusion_ratio",
            ReactionLaw(diffusion_u_scale=0.92, diffusion_v_scale=1.08),
            "changed diffusion ratio",
        ),
    )


TRUE_CANDIDATE_ID = "standard"


def baseline_question_pool(config: GrayScottBaselineConfig) -> list[GrayScottExperiment]:
    questions: list[GrayScottExperiment] = []
    index = 0
    measurement = MeasurementSpec(sample_every=config.steps, noise_std=0.006)
    for feed, kill in ((0.025, 0.055), (0.035, 0.060), (0.045, 0.063), (0.055, 0.062)):
        for family in ("center_square", "two_spots"):
            for pulse_delta in (0.0, 0.18):
                intervention = None
                if pulse_delta:
                    center = config.grid_size // 2
                    intervention = LocalPulse(
                        config.steps // 2, center, center, delta_v=pulse_delta
                    )
                questions.append(
                    GrayScottExperiment(
                        f"gs-q{index:02d}",
                        parameters=GrayScottParameters(feed=feed, kill=kill),
                        initial_family=family,
                        initial_seed=100 + index,
                        grid_size=config.grid_size,
                        steps=config.steps,
                        intervention=intervention,
                        measurement=measurement,
                    )
                )
                index += 1
    return questions


SUMMARY_NOISE = np.asarray([0.035, 0.035, 0.08, 0.008] * 2)


class CandidateEvidence:
    def __init__(self, candidate_ids: list[str]) -> None:
        self._log_weights = {item: -math.log(len(candidate_ids)) for item in candidate_ids}

    @property
    def posterior(self) -> dict[str, float]:
        maximum = max(self._log_weights.values())
        total = sum(math.exp(value - maximum) for value in self._log_weights.values())
        return {key: math.exp(value - maximum) / total for key, value in self._log_weights.items()}

    def update(
        self,
        predictions: dict[str, NDArray[np.float64]],
        observation: NDArray[np.float64],
    ) -> dict[str, float]:
        if set(predictions) != set(self._log_weights):
            raise ValueError("candidate predictions do not match registered evidence state")
        for candidate_id, prediction in predictions.items():
            residual = (observation - prediction) / SUMMARY_NOISE
            self._log_weights[candidate_id] += -0.5 * float(residual @ residual)
        return self.posterior


def _prediction_cache(
    questions: list[GrayScottExperiment],
    candidates: tuple[FixedParadigmCandidate, ...],
) -> dict[str, dict[str, NDArray[np.float64]]]:
    cache: dict[str, dict[str, NDArray[np.float64]]] = {}
    for question in questions:
        expected_question = replace(
            question,
            measurement=replace(question.measurement, noise_std=0.0),
        )
        cache[question.experiment_id] = {
            candidate.candidate_id: GrayScottWorld(0, candidate.law)
            .observe(expected_question)
            .summary()
            for candidate in candidates
        }
    return cache


def _condition_vector(question: GrayScottExperiment) -> NDArray[np.float64]:
    p = question.parameters
    return np.asarray(
        [
            p.feed / 0.06,
            p.kill / 0.07,
            float(question.initial_family == "two_spots"),
            float(question.intervention is not None),
        ]
    )


def _entropy(posterior: dict[str, float]) -> float:
    return -sum(value * math.log(value) for value in posterior.values() if value > 0.0)


def _posterior_for_outcome(
    posterior: dict[str, float],
    predictions: dict[str, NDArray[np.float64]],
    outcome: NDArray[np.float64],
) -> dict[str, float]:
    log_values = {
        key: math.log(max(posterior[key], 1e-300))
        - 0.5
        * float(((outcome - prediction) / SUMMARY_NOISE) @ ((outcome - prediction) / SUMMARY_NOISE))
        for key, prediction in predictions.items()
    }
    maximum = max(log_values.values())
    total = sum(math.exp(value - maximum) for value in log_values.values())
    return {key: math.exp(value - maximum) / total for key, value in log_values.items()}


def expected_information_gain(
    posterior: dict[str, float],
    predictions: dict[str, NDArray[np.float64]],
    samples: int,
    seed: int,
) -> float:
    rng = np.random.default_rng(seed)
    ids = list(predictions)
    probabilities = np.asarray([posterior[item] for item in ids])
    expected_entropy = 0.0
    for _ in range(samples):
        source_index = int(rng.choice(len(ids), p=probabilities))
        outcome = predictions[ids[source_index]] + rng.normal(0.0, SUMMARY_NOISE)
        expected_entropy += _entropy(_posterior_for_outcome(posterior, predictions, outcome))
    return _entropy(posterior) - expected_entropy / samples


def _select_question(
    strategy: StrategyName,
    remaining: list[GrayScottExperiment],
    selected: list[GrayScottExperiment],
    observations: list[NDArray[np.float64]],
    posterior: dict[str, float],
    predictions: dict[str, dict[str, NDArray[np.float64]]],
    rng: random.Random,
    bed_samples: int,
) -> GrayScottExperiment:
    if strategy == "random":
        return rng.choice(remaining)

    if strategy == "coverage" or (strategy == "active_learning" and len(selected) < 5):
        selected_vectors = [_condition_vector(item) for item in selected]

        def coverage_score(question: GrayScottExperiment) -> tuple[float, str]:
            vector = _condition_vector(question)
            distance = (
                float(np.linalg.norm(vector))
                if not selected_vectors
                else min(float(np.linalg.norm(vector - seen)) for seen in selected_vectors)
            )
            return distance, question.experiment_id

        return max(remaining, key=coverage_score)

    if strategy == "active_learning":
        ensemble = BootstrapEnsemble(members=8, seed=rng.randrange(2**32)).fit(
            selected,
            np.stack(observations),
        )

        def active_score(question: GrayScottExperiment) -> tuple[float, str]:
            variance = ensemble.predictive_variance([question])[0]
            return float(np.sum(variance / (SUMMARY_NOISE * SUMMARY_NOISE))), question.experiment_id

        return max(remaining, key=active_score)

    if strategy == "max_disagreement":

        def disagreement_score(question: GrayScottExperiment) -> tuple[float, str]:
            question_predictions = predictions[question.experiment_id]
            mean = sum(posterior[key] * value for key, value in question_predictions.items())
            score = sum(
                posterior[key] * float(np.sum(((value - mean) / SUMMARY_NOISE) ** 2))
                for key, value in question_predictions.items()
            )
            return score, question.experiment_id

        return max(remaining, key=disagreement_score)

    if strategy != "bayesian_design":
        raise ValueError(f"unknown strategy: {strategy}")

    def design_score(question: GrayScottExperiment) -> tuple[float, str]:
        question_seed = int.from_bytes(
            hashlib.sha256(question.experiment_id.encode()).digest()[:8], "big"
        )
        score = expected_information_gain(
            posterior,
            predictions[question.experiment_id],
            bed_samples,
            question_seed,
        )
        return score, question.experiment_id

    return max(remaining, key=design_score)


@dataclass(frozen=True, slots=True)
class BaselineRunResult:
    strategy: str
    seed: int
    sustained_identification_query: int | None
    final_true_posterior: float
    final_true_rank: int
    selected_question_ids: tuple[str, ...]
    posterior_history: tuple[dict[str, float], ...]
    observation_summaries: tuple[tuple[float, ...], ...]


def _sustained_query(history: list[float], threshold: float) -> int | None:
    earliest = None
    suffix_valid = True
    for index in range(len(history) - 1, -1, -1):
        suffix_valid = suffix_valid and history[index] >= threshold
        if suffix_valid:
            earliest = index + 1
    return earliest


def run_selection_baseline(
    config: GrayScottBaselineConfig,
    strategy: StrategyName,
    seed: int,
    prediction_cache: dict[str, dict[str, NDArray[np.float64]]] | None = None,
    ledger_path: Path | None = None,
) -> BaselineRunResult:
    config.validate()
    questions = baseline_question_pool(config)
    if config.max_queries > len(questions):
        raise ValueError("query budget exceeds the frozen question pool")
    candidates = fixed_candidate_pool()
    predictions = prediction_cache or _prediction_cache(questions, candidates)
    evidence = CandidateEvidence([item.candidate_id for item in candidates])
    world = GrayScottWorld(seed)
    remaining = questions.copy()
    selected: list[GrayScottExperiment] = []
    observations: list[NDArray[np.float64]] = []
    history: list[float] = []
    posterior_history: list[dict[str, float]] = []
    rng = random.Random(f"{config.protocol_id}:{strategy}:{seed}")
    ledger = EvidenceLedger(ledger_path) if ledger_path is not None else None
    if ledger is not None:
        ledger.append(
            "run_started",
            {
                "protocol_id": config.protocol_id,
                "strategy": strategy,
                "seed": seed,
                "candidate_ids": [item.candidate_id for item in candidates],
            },
        )
    for query_index in range(1, config.max_queries + 1):
        question = _select_question(
            strategy,
            remaining,
            selected,
            observations,
            evidence.posterior,
            predictions,
            rng,
            config.bed_samples,
        )
        question_predictions = predictions[question.experiment_id]
        prediction_event_hash = None
        if ledger is not None:
            prediction_event_hash = ledger.preregister(
                {
                    "query_index": query_index,
                    "question_id": question.experiment_id,
                    "question_hash": question.content_hash,
                    "posterior_before": evidence.posterior,
                    "predictions": {
                        candidate_id: value.tolist()
                        for candidate_id, value in question_predictions.items()
                    },
                    "summary_noise": SUMMARY_NOISE.tolist(),
                }
            )
        observation = world.observe(question).summary()
        selected.append(question)
        observations.append(observation)
        remaining.remove(question)
        posterior = evidence.update(question_predictions, observation)
        if ledger is not None and prediction_event_hash is not None:
            ledger.record_observation(
                {
                    "query_index": query_index,
                    "question_id": question.experiment_id,
                    "observation_summary": observation.tolist(),
                    "posterior_after": posterior,
                },
                prediction_event_hash,
            )
        history.append(posterior[TRUE_CANDIDATE_ID])
        posterior_history.append(posterior)
    final_posterior = evidence.posterior
    ordered = sorted(final_posterior, key=final_posterior.__getitem__, reverse=True)
    if ledger is not None:
        ledger.append(
            "run_completed",
            {
                "final_posterior": final_posterior,
                "true_candidate_rank": ordered.index(TRUE_CANDIDATE_ID) + 1,
            },
        )
        verify_ledger(ledger.path)
    return BaselineRunResult(
        strategy,
        seed,
        _sustained_query(history, config.posterior_threshold),
        final_posterior[TRUE_CANDIDATE_ID],
        ordered.index(TRUE_CANDIDATE_ID) + 1,
        tuple(item.experiment_id for item in selected),
        tuple(posterior_history),
        tuple(tuple(float(value) for value in item) for item in observations),
    )


def run_surrogate_evaluation(config: GrayScottBaselineConfig) -> dict[str, float | int]:
    metrics, _, _, _ = _surrogate_outputs(config)
    return metrics


def _surrogate_outputs(
    config: GrayScottBaselineConfig,
) -> tuple[
    dict[str, float | int],
    NDArray[np.float64],
    NDArray[np.float64],
    list[str],
]:
    experiments = baseline_question_pool(config)
    world = GrayScottWorld(config.seed)
    targets = np.stack([world.observe(question).summary() for question in experiments])
    train_indices = [index for index, item in enumerate(experiments) if item.parameters.feed < 0.05]
    test_indices = [index for index, item in enumerate(experiments) if item.parameters.feed >= 0.05]
    train = [experiments[index] for index in train_indices]
    test = [experiments[index] for index in test_indices]
    train_targets = targets[train_indices]
    test_targets = targets[test_indices]
    predictor = FixedFeatureRegressor().fit(train, train_targets)
    ensemble = BootstrapEnsemble(seed=config.seed).fit(train, train_targets)
    predictor_rmse = float(np.sqrt(np.mean((predictor.predict(test) - test_targets) ** 2)))
    ensemble_predictions = ensemble.predict(test)
    ensemble_rmse = float(np.sqrt(np.mean((ensemble_predictions - test_targets) ** 2)))
    average_uncertainty = float(np.mean(np.sqrt(ensemble.predictive_variance(test))))
    calibration_ratio = ensemble_rmse / max(average_uncertainty, 1e-12)
    metrics: dict[str, float | int] = {
        "train_tasks": len(train),
        "held_out_parameter_tasks": len(test),
        "fixed_predictor_rmse": predictor_rmse,
        "ensemble_rmse": ensemble_rmse,
        "ensemble_average_std": average_uncertainty,
        "ensemble_rmse_to_predicted_std": calibration_ratio,
        "ensemble_oob_calibration_scale": ensemble.calibration_scale,
    }
    return (
        metrics,
        ensemble.predict_members(test),
        test_targets,
        [item.experiment_id for item in test],
    )


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_gray_scott_benchmark(
    config: GrayScottBaselineConfig,
    output_dir: Path,
    strategies: list[StrategyName],
) -> dict[str, Any]:
    config.validate()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite benchmark directory: {output_dir}")
    output_dir.mkdir(parents=True)
    questions = baseline_question_pool(config)
    predictions = _prediction_cache(questions, fixed_candidate_pool())
    all_results: dict[str, list[BaselineRunResult]] = {}
    for strategy in strategies:
        all_results[strategy] = [
            run_selection_baseline(
                config,
                strategy,
                config.seed + offset,
                predictions,
                output_dir / "ledgers" / strategy / f"seed-{config.seed + offset}.jsonl",
            )
            for offset in range(config.replicates)
        ]
    summaries = {}
    for strategy, results in all_results.items():
        censored = [item.sustained_identification_query or config.max_queries for item in results]
        successes = sum(item.sustained_identification_query is not None for item in results)
        summaries[strategy] = {
            "successes": successes,
            "success_rate": successes / len(results),
            "median_queries_with_censoring": statistics.median(censored),
            "median_final_true_posterior": statistics.median(
                item.final_true_posterior for item in results
            ),
            "median_final_true_rank": statistics.median(item.final_true_rank for item in results),
        }
    candidate_ids = [item.candidate_id for item in fixed_candidate_pool()]
    question_ids = [item.experiment_id for item in questions]
    prediction_array = np.stack(
        [
            np.stack([predictions[question_id][candidate_id] for candidate_id in candidate_ids])
            for question_id in question_ids
        ]
    )
    candidate_distribution_path = output_dir / "candidate-predictive-distributions.npz"
    np.savez_compressed(
        candidate_distribution_path,
        means=prediction_array,
        noise_std=SUMMARY_NOISE,
        question_ids=np.asarray(question_ids),
        candidate_ids=np.asarray(candidate_ids),
    )
    surrogate_metrics, member_predictions, test_targets, test_ids = _surrogate_outputs(config)
    surrogate_distribution_path = output_dir / "surrogate-predictive-distributions.npz"
    np.savez_compressed(
        surrogate_distribution_path,
        member_predictions=member_predictions,
        targets=test_targets,
        experiment_ids=np.asarray(test_ids),
    )
    raw_runs_path = output_dir / "runs.json"
    raw_runs_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "strategies": {
                    strategy: [asdict(result) for result in results]
                    for strategy, results in all_results.items()
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    raw_config = asdict(config)
    candidate_spec = [
        {"candidate_id": item.candidate_id, "law": asdict(item.law)}
        for item in fixed_candidate_pool()
    ]
    question_spec = [asdict(item) for item in questions]
    environment = capture_environment(Path.cwd())
    identity = ExperimentIdentity(
        config.protocol_id,
        raw_config,
        config.seed,
        environment["git_revision"],
    )
    report = {
        "schema_version": 1,
        "protocol_id": config.protocol_id,
        "config_hash": content_hash(raw_config),
        "candidate_count": len(fixed_candidate_pool()),
        "candidate_spec_hash": content_hash(candidate_spec),
        "question_pool_hash": content_hash(question_spec),
        "summary_noise": SUMMARY_NOISE.tolist(),
        "question_pool_size": len(questions),
        "query_budget": config.max_queries,
        "summaries": summaries,
        "surrogate_evaluation": surrogate_metrics,
        "interpretation": "Development-world baseline only; not a sealed confirmation result.",
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = RunManifest(
        1,
        identity.experiment_id,
        config.protocol_id,
        identity.config_hash,
        config.seed,
        environment,
        {
            "candidate_ids": candidate_ids,
            "candidate_spec_hash": content_hash(candidate_spec),
            "question_ids": question_ids,
            "question_pool_hash": content_hash(question_spec),
            "summary_noise": SUMMARY_NOISE.tolist(),
        },
        {
            "report": str(report_path),
            "report_hash": content_hash(report),
            "runs": str(raw_runs_path),
            "runs_hash": _file_hash(raw_runs_path),
            "candidate_distributions": str(candidate_distribution_path),
            "candidate_distributions_hash": _file_hash(candidate_distribution_path),
            "surrogate_distributions": str(surrogate_distribution_path),
            "surrogate_distributions_hash": _file_hash(surrogate_distribution_path),
            "ledger_directory": str(output_dir / "ledgers"),
        },
    )
    manifest.write_once(output_dir / "manifest.json")
    return report
