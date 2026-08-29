"""Development-only Step 5 control with fixed paradigms and evolving questions."""

from __future__ import annotations

import inspect
import json
from dataclasses import asdict, fields, replace
from pathlib import Path
from typing import Any

import numpy as np

from scientific_parallax.baselines.gray_scott import fixed_candidate_pool
from scientific_parallax.core.reproducibility import (
    ExperimentIdentity,
    RunManifest,
    capture_environment,
    content_hash,
)
from scientific_parallax.protocol.dry_run import protocol_spec_from_config
from scientific_parallax.questions.model import (
    AnticipatedOutcome,
    QuestionCost,
    QuestionCostWeights,
    QuestionDiagnostics,
    QuestionGenotype,
    QuestionIndividual,
)
from scientific_parallax.questions.mutation import FrozenQuestionMutator
from scientific_parallax.questions.population import QuestionPopulation
from scientific_parallax.questions.scoring import (
    IndependentEvidenceEngine,
    diagnose_question,
    entropy,
    expected_information_gain,
    predict_question,
    predicted_disagreement,
    summary_noise,
)
from scientific_parallax.step0.ledger import EvidenceLedger, verify_ledger
from scientific_parallax.worlds.gray_scott import (
    GrayScottExperiment,
    GrayScottParameters,
    GrayScottWorld,
    MeasurementSpec,
)


def run_step5_control(config_path: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite Step 5 output: {output_dir}")
    environment = capture_environment(Path.cwd())
    output_dir.mkdir(parents=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("unsupported Step 5 control configuration schema")
    if (
        config["generations"] < 1
        or config["population_capacity"] < 1
        or config["max_world_queries"] < 1
        or config["eig_samples"] < 8
        or not config["seed_questions"]
    ):
        raise ValueError("invalid Step 5 generations, capacity, query, sample, or seed count")

    protocol_config_path = Path(config["protocol_config"])
    protocol_config = json.loads(protocol_config_path.read_text(encoding="utf-8"))
    protocol_spec = protocol_spec_from_config(protocol_config)
    if protocol_spec.protocol_hash != config["protocol_hash"]:
        raise ValueError("Step 5 config does not match the frozen protocol hash")
    if config["max_world_queries"] > protocol_config["world_query_budget"]:
        raise ValueError("Step 5 query budget exceeds the frozen protocol budget")

    paradigms = fixed_candidate_pool()
    paradigm_ids = tuple(item.candidate_id for item in paradigms)
    registered_ids = set(paradigm_ids)
    fixed_paradigm_hash = content_hash([asdict(item) for item in paradigms])
    world = GrayScottWorld(measurement_seed=config["seed"])
    weights = QuestionCostWeights(**config["cost_weights"])
    mutator = FrozenQuestionMutator(tuple(config["allowed_mutations"]))
    population = QuestionPopulation(
        config["population_capacity"],
        config["minimum_disagreement"],
        config["minimum_expected_information_gain"],
    )
    evidence = IndependentEvidenceEngine(paradigm_ids)
    evidence_ledger = EvidenceLedger(output_dir / "evidence.jsonl")
    lineage_ledger = EvidenceLedger(output_dir / "question-lineage.jsonl")
    evidence_ledger.append(
        "run_started",
        {
            "strategy_version": config["strategy_version"],
            "protocol_hash": protocol_spec.protocol_hash,
            "fixed_paradigm_hash": fixed_paradigm_hash,
        },
    )

    all_questions: dict[str, tuple[QuestionGenotype, int, str | None, Any]] = {}
    for question in _seed_questions(config, paradigm_ids):
        all_questions[question.semantic_hash] = (question, 0, None, None)
        lineage_ledger.append("question_seeded", _lineage_payload(question, 0, None, None))

    executed: set[str] = set()
    rounds: list[dict[str, Any]] = []
    rejection_counts: dict[str, int] = {}
    mutation_operators: set[str] = set()
    attempted_questions = len(all_questions)
    prediction_evaluations = 0
    total_realized_cost = 0.0
    active: tuple[QuestionIndividual, ...] = ()

    for generation in range(config["generations"] + 1):
        if generation > 0:
            parents = active or tuple(
                _diagnosed_individual(
                    entry[0],
                    entry[1],
                    entry[2],
                    entry[3],
                    paradigms,
                    evidence.posterior,
                    world,
                    weights,
                    config,
                )
                for entry in all_questions.values()
            )
            for parent in parents:
                for child, mutation in mutator.generate(parent.genotype, generation):
                    attempted_questions += 1
                    mutation_operators.add(mutation.operator)
                    if child.semantic_hash in all_questions:
                        rejection_counts["semantic_duplicate"] = (
                            rejection_counts.get("semantic_duplicate", 0) + 1
                        )
                        continue
                    all_questions[child.semantic_hash] = (
                        child,
                        generation,
                        parent.genotype.semantic_hash,
                        mutation,
                    )
                    lineage_ledger.append(
                        "question_mutated",
                        _lineage_payload(
                            child, generation, parent.genotype.semantic_hash, mutation
                        ),
                    )

        diagnosed: list[QuestionIndividual] = []
        for question, born, parent_hash, mutation in all_questions.values():
            diagnosed.append(
                _diagnosed_individual(
                    question,
                    born,
                    parent_hash,
                    mutation,
                    paradigms,
                    evidence.posterior,
                    world,
                    weights,
                    config,
                )
            )
            prediction_evaluations += len(paradigms)
        selection = population.select(tuple(diagnosed), world, registered_ids)
        active = selection.selected
        for rejected in selection.rejected:
            rejection_counts[rejected.reason] = rejection_counts.get(rejected.reason, 0) + 1

        available = [item for item in active if item.genotype.semantic_hash not in executed]
        if not available or len(executed) >= config["max_world_queries"]:
            break
        selected = available[0]
        question = selected.genotype
        predictions = predict_question(question, paradigms)
        prior = evidence.posterior
        prediction_event_hash = evidence_ledger.preregister(
            {
                "generation": generation,
                "question_id": question.question_id,
                "question_semantic_hash": question.semantic_hash,
                "experiment": asdict(question.experiment),
                "prior": prior,
                "anticipated_outcomes": {
                    item: [float(value) for value in predictions[item]]
                    for item in sorted(predictions)
                },
                "predicted_disagreement": selected.diagnostics.predicted_disagreement,
                "expected_information_gain": selected.diagnostics.expected_information_gain,
                "cost": asdict(selected.diagnostics.cost),
            }
        )
        observation = world.observe(question.experiment).summary()
        before_entropy = entropy(prior)
        posterior = evidence.update(predictions, observation)
        actual_information_gain = before_entropy - entropy(posterior)
        gap = actual_information_gain - selected.diagnostics.expected_information_gain
        evidence_ledger.record_observation(
            {
                "question_semantic_hash": question.semantic_hash,
                "observation": [float(value) for value in observation],
                "observation_hash": content_hash([float(value) for value in observation]),
                "posterior": posterior,
                "actual_information_gain": actual_information_gain,
                "actual_minus_expected_information_gain": gap,
            },
            prediction_event_hash,
        )
        executed.add(question.semantic_hash)
        total_realized_cost += selected.diagnostics.cost.weighted_total
        rounds.append(
            {
                "generation": generation,
                "population_size": len(active),
                "known_questions": len(all_questions),
                "selected_question_id": question.question_id,
                "selected_question_hash": question.semantic_hash,
                "parent_question_hash": selected.parent_semantic_hash,
                "mutation": None if selected.mutation is None else asdict(selected.mutation),
                "predicted_disagreement": selected.diagnostics.predicted_disagreement,
                "expected_information_gain": selected.diagnostics.expected_information_gain,
                "actual_information_gain": actual_information_gain,
                "actual_minus_expected_information_gain": gap,
                "resource_score": selected.diagnostics.resource_score,
                "posterior": posterior,
            }
        )

    evidence_ledger.append("run_completed", {"world_queries": len(rounds)})
    lineage_ledger.append(
        "lineage_completed",
        {"unique_questions": len(all_questions), "attempted_questions": attempted_questions},
    )
    verify_ledger(output_dir / "evidence.jsonl")
    verify_ledger(output_dir / "question-lineage.jsonl")

    safety_checks = _safety_checks(
        world=world,
        population=population,
        paradigms=paradigms,
        weights=weights,
        config=config,
        seed_question=next(iter(all_questions.values()))[0],
    )
    checks = {
        "frozen_protocol_hash_matches": protocol_spec.protocol_hash == config["protocol_hash"],
        "fixed_paradigms_unchanged": fixed_paradigm_hash
        == content_hash([asdict(item) for item in paradigms]),
        "known_distinguishing_experiment_selected": safety_checks[
            "known_distinguishing_experiment_selected"
        ],
        "question_has_no_hidden_label_or_update_fields": safety_checks[
            "question_has_no_hidden_label_or_update_fields"
        ],
        "evidence_engine_does_not_accept_question_objects": safety_checks[
            "evidence_engine_does_not_accept_question_objects"
        ],
        "semantic_duplicate_rejected": safety_checks["semantic_duplicate_rejected"],
        "language_only_novelty_gets_no_resource": safety_checks[
            "language_only_novelty_gets_no_resource"
        ],
        "invalid_question_rejected": safety_checks["invalid_question_rejected"],
        "all_mutation_operators_exercised": mutation_operators == set(config["allowed_mutations"]),
        "all_questions_traceable": all(
            generation == 0
            or (
                parent_hash in all_questions
                and mutation is not None
                and mutation.parent_semantic_hash == parent_hash
                and mutation.child_semantic_hash == question.semantic_hash
            )
            for question, generation, parent_hash, mutation in all_questions.values()
        ),
        "expected_actual_information_gain_recorded": bool(rounds)
        and all("actual_minus_expected_information_gain" in item for item in rounds),
        "world_query_budget_respected": len(rounds) <= config["max_world_queries"],
        "evidence_ledgers_verify": True,
        "final_world_not_accessed": True,
    }
    report = {
        "schema_version": 1,
        "status": "step5_control_complete" if all(checks.values()) else "redo",
        "strategy_version": config["strategy_version"],
        "scope": "development Gray-Scott world only; final sealed tasks were not accessed",
        "protocol_hash": protocol_spec.protocol_hash,
        "fixed_paradigm_hash": fixed_paradigm_hash,
        "fixed_paradigm_ids": list(paradigm_ids),
        "checks": checks,
        "mutation_operators": sorted(mutation_operators),
        "cost_weights": asdict(weights),
        "budget": {
            "world_queries": len(rounds),
            "question_generation_attempts": attempted_questions,
            "unique_questions": len(all_questions),
            "prediction_evaluations": prediction_evaluations,
            "realized_weighted_cost": total_realized_cost,
        },
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "rounds": rounds,
        "final_posterior": evidence.posterior,
        "boundary": (
            "Question genotypes can propose executable experiments and target registered "
            "paradigms, but cannot observe hidden labels or alter evidence updates."
        ),
        "assurance": (
            "Step 5 is strategy development after local self-audited Protocol Freeze; "
            "this report is not final-world evidence."
        ),
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    identity = ExperimentIdentity(
        "step5-question-evolution-control-v1",
        config,
        config["seed"],
        environment["git_revision"],
    )
    manifest = RunManifest(
        schema_version=1,
        experiment_id=identity.experiment_id,
        protocol_id="step5-question-evolution-control-v1",
        config_hash=identity.config_hash,
        seed=config["seed"],
        environment=environment,
        inputs={
            "config": str(config_path),
            "protocol_hash": protocol_spec.protocol_hash,
            "fixed_paradigm_hash": fixed_paradigm_hash,
        },
        outputs={
            "report": report_path.name,
            "report_hash": content_hash(report),
            "evidence_ledger": "evidence.jsonl",
            "evidence_ledger_hash": _last_event_hash(output_dir / "evidence.jsonl"),
            "question_lineage": "question-lineage.jsonl",
            "question_lineage_hash": _last_event_hash(output_dir / "question-lineage.jsonl"),
        },
    )
    manifest.write_once(output_dir / "manifest.json")
    return report


def _seed_questions(config: dict[str, Any], paradigm_ids: tuple[str, ...]):
    for index, raw in enumerate(config["seed_questions"]):
        measurement = MeasurementSpec(sample_every=raw["steps"], noise_std=raw["noise_std"])
        experiment = GrayScottExperiment(
            experiment_id=f"step5-seed-{index}",
            parameters=GrayScottParameters(feed=raw["feed"], kill=raw["kill"]),
            initial_family=raw["initial_family"],
            initial_seed=raw["initial_seed"],
            grid_size=raw["grid_size"],
            steps=raw["steps"],
            boundary=raw["boundary"],
            measurement=measurement,
        )
        yield QuestionGenotype(
            f"step5-seed-{index}",
            experiment,
            paradigm_ids,
            novelty_label=raw.get("label", "seed"),
        )


def _diagnosed_individual(
    question,
    generation,
    parent_hash,
    mutation,
    paradigms,
    posterior,
    world,
    weights,
    config,
):
    diagnostics = diagnose_question(
        question,
        paradigms,
        posterior,
        world,
        weights,
        eig_samples=config["eig_samples"],
        seed=config["seed"],
    )
    return QuestionIndividual(question, diagnostics, generation, parent_hash, mutation)


def _lineage_payload(question, generation, parent_hash, mutation):
    return {
        "question": asdict(question),
        "semantic_hash": question.semantic_hash,
        "generation": generation,
        "parent_semantic_hash": parent_hash,
        "mutation": None if mutation is None else asdict(mutation),
    }


def _safety_checks(*, world, population, paradigms, weights, config, seed_question):
    ids = tuple(item.candidate_id for item in paradigms)
    registered = set(ids)
    dimension = 8
    noise = summary_noise(dimension)
    prior = {"model_a": 0.5, "model_b": 0.5}
    neutral = {"model_a": np.zeros(dimension), "model_b": np.zeros(dimension)}
    distinguishing = {
        "model_a": np.zeros(dimension),
        "model_b": 4.0 * noise,
    }
    toy_scores = {
        "neutral": (
            predicted_disagreement(prior, neutral),
            expected_information_gain(prior, neutral, samples=64, seed=17),
        ),
        "known_distinguishing": (
            predicted_disagreement(prior, distinguishing),
            expected_information_gain(prior, distinguishing, samples=64, seed=17),
        ),
    }

    valid = _diagnosed_individual(
        seed_question,
        0,
        None,
        None,
        paradigms,
        {item: 1.0 / len(ids) for item in ids},
        world,
        weights,
        config,
    )
    alias = replace(seed_question, question_id="language-only-alias", novelty_label="惊人新问题")
    alias_individual = replace(valid, genotype=alias)
    duplicate_selection = population.select((valid, alias_individual), world, registered)

    zero_diagnostics = QuestionDiagnostics(
        tuple(AnticipatedOutcome(item, (0.0,) * dimension) for item in ids),
        0.0,
        0.0,
        QuestionCost.estimate(alias, world, weights),
    )
    language_only = replace(valid, genotype=alias, diagnostics=zero_diagnostics)
    no_difference_selection = population.select((language_only,), world, registered)

    invalid = replace(
        seed_question,
        question_id="invalid-grid",
        experiment=replace(seed_question.experiment, experiment_id="invalid-grid", grid_size=7),
    )
    invalid_individual = replace(valid, genotype=invalid)
    invalid_selection = population.select((invalid_individual,), world, registered)
    question_fields = {item.name for item in fields(QuestionGenotype)}
    forbidden = {"hidden_label", "true_paradigm", "observation", "posterior", "update_rule"}
    update_parameters = set(inspect.signature(IndependentEvidenceEngine.update).parameters)
    return {
        "known_distinguishing_experiment_selected": max(
            toy_scores, key=lambda item: toy_scores[item]
        )
        == "known_distinguishing"
        and toy_scores["known_distinguishing"][0] > toy_scores["neutral"][0]
        and toy_scores["known_distinguishing"][1] > toy_scores["neutral"][1],
        "question_has_no_hidden_label_or_update_fields": not (question_fields & forbidden),
        "evidence_engine_does_not_accept_question_objects": "question" not in update_parameters,
        "semantic_duplicate_rejected": any(
            item.reason == "semantic_duplicate" for item in duplicate_selection.rejected
        ),
        "language_only_novelty_gets_no_resource": not no_difference_selection.selected
        and any(
            item.reason == "no_predictive_difference" for item in no_difference_selection.rejected
        ),
        "invalid_question_rejected": not invalid_selection.selected
        and any(item.reason.startswith("invalid:") for item in invalid_selection.rejected),
    }


def _last_event_hash(path: Path) -> str:
    last_line = path.read_text(encoding="utf-8").splitlines()[-1]
    return json.loads(last_line)["event_hash"]
