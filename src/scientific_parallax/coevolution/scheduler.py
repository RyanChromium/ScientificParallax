"""Development-only Step 6 budgeted paradigm-question co-evolution scheduler."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np

from scientific_parallax.coevolution.checkpoint import (
    load_latest_checkpoint,
    write_checkpoint,
)
from scientific_parallax.coevolution.evidence import (
    EvidenceHistoryItem,
    calibrated_noise,
    posterior_from_history,
    rebuild_coevolution_evidence,
    update_posterior,
)
from scientific_parallax.coevolution.selection import (
    QuestionNichePopulation,
    consider_recombination,
    paradigm_pareto_front,
)
from scientific_parallax.core.budget import BudgetLedger, BudgetLimits, BudgetSnapshot
from scientific_parallax.core.reproducibility import (
    ExperimentIdentity,
    RunManifest,
    capture_environment,
    content_hash,
)
from scientific_parallax.evolution.lineage import (
    LineageLedger,
    individual_from_dict,
    individual_to_dict,
    rebuild_lineage,
)
from scientific_parallax.evolution.model import (
    LineageStatus,
    ParadigmIndividual,
    PatchCost,
    PatchCostWeights,
    behavior_distance,
    description_length,
    structural_distance,
)
from scientific_parallax.evolution.mutation import (
    FrozenParadigmMutator,
    gray_scott_founder_genotype,
    phenotype_on_probes,
    summary_on_experiment,
)
from scientific_parallax.evolution.population import ParadigmPopulation
from scientific_parallax.protocol.candidate_generator import CandidateGeneratorSpec
from scientific_parallax.protocol.dry_run import gray_scott_ir, protocol_spec_from_config
from scientific_parallax.protocol.evidence_layers import SurvivalPolicy
from scientific_parallax.questions.model import (
    AnticipatedOutcome,
    QuestionCost,
    QuestionCostWeights,
    QuestionDiagnostics,
    QuestionGenotype,
    QuestionIndividual,
    QuestionMutation,
)
from scientific_parallax.questions.mutation import FrozenQuestionMutator
from scientific_parallax.questions.scoring import (
    expected_information_gain,
    predicted_disagreement,
)
from scientific_parallax.step0.ledger import EvidenceLedger, verify_ledger
from scientific_parallax.worlds.gray_scott import (
    GrayScottExperiment,
    GrayScottParameters,
    GrayScottWorld,
    LocalPulse,
    MeasurementSpec,
)

ZERO_HASH = "0" * 64


def run_step6_control(
    config_path: Path,
    output_dir: Path,
    *,
    resume: bool = False,
    interrupt_after_round: int | None = None,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_config(config)
    protocol_config = json.loads(Path(config["protocol_config"]).read_text(encoding="utf-8"))
    protocol_spec = protocol_spec_from_config(protocol_config)
    if protocol_spec.protocol_hash != config["protocol_hash"]:
        raise ValueError("Step 6 config does not match the frozen protocol hash")
    limits = BudgetLimits(
        min(config["max_world_queries"], protocol_config["world_query_budget"]),
        protocol_config["candidate_generation_budget"],
        protocol_config["candidate_evaluation_budget"],
    )
    generator_raw = protocol_config["candidate_generator"]
    generator_spec = CandidateGeneratorSpec(
        generator_raw["version"],
        tuple(generator_raw["allowed_mutations"]),
        generator_raw["maximum_offspring_per_parent"],
        generator_raw["maximum_candidates_per_task"],
    )
    if generator_spec.spec_hash != protocol_spec.candidate_generator_hash:
        raise ValueError("scheduler candidate generator differs from Gate PF")

    world = GrayScottWorld(measurement_seed=config["seed"])
    fixed_probes = _fixed_probes(config["fixed_probes"])
    patch_weights = PatchCostWeights(**config["patch_cost_weights"])
    question_weights = QuestionCostWeights(**config["question_cost_weights"])
    mutator = FrozenParadigmMutator(generator_spec)
    question_mutator = FrozenQuestionMutator(tuple(config["question_mutations"]))
    question_population = QuestionNichePopulation(
        config["question_niche_capacity"],
        config["minimum_disagreement"],
        config["minimum_expected_information_gain"],
    )
    survival_policy = SurvivalPolicy(**protocol_config["survival_parameters"])
    thresholds = protocol_config["viability_thresholds"]
    noise_floor = float(protocol_spec.noise_calibration_parameters["floor"])
    paths = _paths(output_dir)

    if resume:
        state, environment, previous_checkpoint_hash = _resume_state(
            paths, config, limits, protocol_spec.protocol_hash
        )
        paradigm_ledger = LineageLedger.resume(paths["paradigm_lineage"])
        question_ledger = EvidenceLedger.resume(paths["question_lineage"])
        evidence_ledger = EvidenceLedger.resume(paths["evidence"])
        scheduler_ledger = EvidenceLedger.resume(paths["scheduler"])
        start_round = state["completed_round"] + 1
    else:
        if output_dir.exists():
            raise FileExistsError(f"refusing to overwrite Step 6 output: {output_dir}")
        environment = capture_environment(Path.cwd())
        output_dir.mkdir(parents=True)
        paths["checkpoints"].mkdir()
        paths["meta"].write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "config_hash": content_hash(config),
                    "protocol_hash": protocol_spec.protocol_hash,
                    "environment": environment,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        paradigm_ledger = LineageLedger(paths["paradigm_lineage"])
        question_ledger = EvidenceLedger(paths["question_lineage"])
        evidence_ledger = EvidenceLedger(paths["evidence"])
        scheduler_ledger = EvidenceLedger(paths["scheduler"])
        state = _initial_state(
            config,
            limits,
            mutator,
            fixed_probes,
            patch_weights,
            paradigm_ledger,
            question_ledger,
            scheduler_ledger,
            thresholds,
            protocol_spec.protocol_hash,
            generator_spec,
        )
        previous_checkpoint_hash = ZERO_HASH
        start_round = 0

    budget = BudgetLedger.resume(limits, BudgetSnapshot(**state["budget"]))
    all_individuals = {
        item["genotype"]["genotype_id"]: individual_from_dict(item) for item in state["individuals"]
    }
    question_pool = _questions_from_state(state["questions"])
    history = list(state["history"])
    prediction_cache = {
        tuple(item["key"]): tuple(item["prediction"]) for item in state["prediction_cache"]
    }
    active_paradigm_ids = tuple(state["active_paradigm_ids"])
    active_question_keys = tuple(state["active_question_keys"])
    rounds = list(state["rounds"])
    top_k_history = [tuple(item) for item in state["top_k_history"]]
    split_events = list(state["split_events"])
    recombination_decisions = list(state["recombination_decisions"])
    paradigm_mutations = set(state["paradigm_mutations"])
    question_mutations = set(state["question_mutations"])
    question_generation_attempts = int(state["question_generation_attempts"])
    paradigm_pareto_archive = set(state["paradigm_pareto_archive"])
    stop_reason: str | None = None

    for round_index in range(start_round, limits.world_queries):
        if round_index > 0:
            split_events.extend(
                _generate_paradigms(
                    active_paradigm_ids,
                    all_individuals,
                    history,
                    prediction_cache,
                    budget,
                    mutator,
                    fixed_probes,
                    patch_weights,
                    paradigm_ledger,
                    scheduler_ledger,
                    thresholds,
                    generator_spec.maximum_candidates_per_task,
                    paradigm_mutations,
                    noise_floor,
                )
            )
            question_generation_attempts = _generate_questions(
                active_question_keys,
                question_pool,
                question_mutator,
                question_ledger,
                question_mutations,
                question_generation_attempts,
                config["max_question_generation_attempts"],
                round_index,
            )

        living = _living_individuals(all_individuals)
        living = _rescore_individuals(
            living,
            history,
            prediction_cache,
            budget,
            thresholds,
            noise_floor,
            advance_checkpoint=False,
        )
        all_individuals.update({item.individual_id: item for item in living})
        paradigm_population = ParadigmPopulation(
            niche_capacities=protocol_config["niche_capacities"],
            survival_policy=survival_policy,
            minimum_evidence_score=thresholds["minimum_evidence_score"],
            minimum_predictive_gain=thresholds["minimum_predictive_gain"],
            maximum_decoder_cost=thresholds["maximum_decoder_cost"],
        )
        paradigm_snapshot = paradigm_population.select(tuple(living), paradigm_ledger)
        _apply_population_status(all_individuals, paradigm_snapshot, paradigm_population)
        active_paradigm_ids = paradigm_snapshot.active_ids
        if len(active_paradigm_ids) < 2:
            stop_reason = "fewer_than_two_active_paradigms"
            break

        active_paradigms = tuple(all_individuals[item] for item in active_paradigm_ids)
        prior_history = _history_for_candidates(active_paradigms, history, prediction_cache, budget)
        prior = posterior_from_history(active_paradigm_ids, prior_history, noise_floor)
        questions = _diagnose_questions(
            question_pool,
            active_paradigms,
            prior,
            world,
            question_weights,
            prediction_cache,
            budget,
            config,
            round_index,
            noise_floor,
        )
        question_selection = question_population.select(questions, world, set(active_paradigm_ids))
        executed_experiments = {item["experiment_hash"] for item in history}
        selected_question, selected_niche = _choose_question(
            question_selection,
            executed_experiments,
            round_index,
        )
        if selected_question is None:
            stop_reason = "no_unexecuted_viable_question"
            break

        question = selected_question.genotype
        base_question = question_pool[_experiment_hash(question.experiment)][0]
        scheduler_ledger.append(
            "question_retargeted_for_round",
            {
                "round": round_index,
                "base_question_hash": base_question.semantic_hash,
                "selected_question_hash": question.semantic_hash,
                "target_paradigm_ids": list(question.target_paradigm_ids),
            },
        )
        predictions = {
            paradigm.individual_id: _predict_cached(
                paradigm, question.experiment, prediction_cache, budget
            )
            for paradigm in active_paradigms
        }
        evidence_ledger.append(
            "evidence_state_rebuilt",
            {
                "round": round_index,
                "candidate_ids": list(active_paradigm_ids),
                "noise_floor": noise_floor,
                "history": [_evidence_history_payload(item) for item in prior_history],
                "posterior": prior,
            },
        )
        prediction_event_hash = evidence_ledger.preregister(
            {
                "round": round_index,
                "question_hash": question.semantic_hash,
                "experiment_hash": _experiment_hash(question.experiment),
                "prior": prior,
                "predictions": {key: list(values) for key, values in predictions.items()},
                "expected_information_gain": (
                    selected_question.diagnostics.expected_information_gain
                ),
                "selected_niche": selected_niche,
            }
        )
        budget.charge_world_query()
        observation = tuple(float(value) for value in world.observe(question.experiment).summary())
        posterior = update_posterior(prior, predictions, observation, noise_floor)
        evidence_ledger.record_observation(
            {
                "round": round_index,
                "question_hash": question.semantic_hash,
                "observation": list(observation),
                "observation_hash": content_hash(observation),
                "posterior": posterior,
            },
            prediction_event_hash,
        )
        experiment_hash = _experiment_hash(question.experiment)
        history.append(
            {
                "question_hash": question.semantic_hash,
                "experiment_hash": experiment_hash,
                "experiment": asdict(question.experiment),
                "observation": list(observation),
            }
        )
        active_question_keys = tuple(
            _experiment_hash(item.genotype.experiment) for item in question_selection.selected
        )

        living = _rescore_individuals(
            _living_individuals(all_individuals),
            history,
            prediction_cache,
            budget,
            thresholds,
            noise_floor,
            advance_checkpoint=True,
        )
        all_individuals.update({item.individual_id: item for item in living})
        paradigm_population = ParadigmPopulation(
            niche_capacities=protocol_config["niche_capacities"],
            survival_policy=survival_policy,
            minimum_evidence_score=thresholds["minimum_evidence_score"],
            minimum_predictive_gain=thresholds["minimum_predictive_gain"],
            maximum_decoder_cost=thresholds["maximum_decoder_cost"],
        )
        post_snapshot = paradigm_population.select(tuple(living), paradigm_ledger)
        _apply_population_status(all_individuals, post_snapshot, paradigm_population)
        active_paradigm_ids = post_snapshot.active_ids
        active_after = tuple(all_individuals[item] for item in active_paradigm_ids)
        current_living = _living_individuals(all_individuals)
        pareto = paradigm_pareto_front(current_living)
        paradigm_pareto_archive.update(item.individual_id for item in pareto)
        top_k = tuple(
            item.individual_id
            for item in sorted(
                active_after,
                key=lambda value: (-value.evidence_score, value.individual_id),
            )[: config["convergence_top_k"]]
        )
        top_k_history.append(top_k)

        if len(active_paradigm_ids) >= 2:
            recombination = consider_recombination(
                active_paradigm_ids[0],
                active_paradigm_ids[1],
                generator_spec.allowed_mutations,
            )
            recombination_payload = asdict(recombination)
            recombination_payload["round"] = round_index
            recombination_decisions.append(recombination_payload)
            scheduler_ledger.append("recombination_considered", recombination_payload)

        round_record = {
            "round": round_index,
            "selected_question_hash": question.semantic_hash,
            "selected_question_niche": selected_niche,
            "question_niches": {
                name: list(identifiers) for name, identifiers in question_selection.niches.items()
            },
            "question_pareto_front": list(question_selection.pareto_front),
            "paradigm_niches": {
                name: list(identifiers) for name, identifiers in post_snapshot.niches.items()
            },
            "paradigm_pareto_front": [item.individual_id for item in pareto],
            "active_paradigms": list(active_paradigm_ids),
            "dormant_paradigms": sorted(
                item.individual_id
                for item in all_individuals.values()
                if item.status == LineageStatus.DORMANT
            ),
            "fossil_paradigms": sorted(
                item.individual_id
                for item in all_individuals.values()
                if item.status in {LineageStatus.DEAD, LineageStatus.EQUIVALENT_DUPLICATE}
            ),
            "paradigm_pareto_archive": sorted(paradigm_pareto_archive),
            "question_population": len(question_selection.selected),
            "prior": prior,
            "posterior": posterior,
            "expected_information_gain": selected_question.diagnostics.expected_information_gain,
            "actual_information_gain": _entropy(prior) - _entropy(posterior),
            "budget": asdict(budget.snapshot),
        }
        rounds.append(round_record)
        scheduler_ledger.append("round_completed", round_record)

        if _converged(top_k_history, config):
            stop_reason = "stable_top_k_convergence"
        elif budget.snapshot.world_queries >= limits.world_queries:
            stop_reason = "world_query_budget_exhausted"

        checkpoint_state = _serialize_state(
            round_index,
            all_individuals,
            question_pool,
            history,
            prediction_cache,
            active_paradigm_ids,
            active_question_keys,
            rounds,
            top_k_history,
            split_events,
            recombination_decisions,
            paradigm_mutations,
            question_mutations,
            question_generation_attempts,
            paradigm_pareto_archive,
            budget.snapshot,
            paths,
        )
        previous_checkpoint_hash = write_checkpoint(
            paths["checkpoints"],
            round_index,
            checkpoint_state,
            previous_checkpoint_hash,
        )
        if interrupt_after_round == round_index and stop_reason is None:
            return {
                "schema_version": 1,
                "status": "interrupted_checkpoint",
                "completed_round": round_index,
                "checkpoint_hash": previous_checkpoint_hash,
            }
        if stop_reason is not None:
            break

    if not rounds:
        raise RuntimeError(f"Step 6 scheduler stopped before a query: {stop_reason}")
    stop_reason = stop_reason or "world_query_budget_exhausted"
    evidence_ledger.append("run_completed", {"stop_reason": stop_reason})
    question_ledger.append("run_completed", {"unique_questions": len(question_pool)})
    scheduler_ledger.append("run_completed", {"stop_reason": stop_reason})
    verify_ledger(paths["evidence"])
    verify_ledger(paths["question_lineage"])
    verify_ledger(paths["scheduler"])
    question_lineage_summary = _verify_question_lineage(paths["question_lineage"])
    rebuilt_evidence = rebuild_coevolution_evidence(paths["evidence"], noise_floor)
    rebuilt_lineage = rebuild_lineage(paths["paradigm_lineage"])
    final_posterior = rounds[-1]["posterior"]
    statuses = {item.status for item in rebuilt_lineage.individuals.values()}
    selected_niches = {item["selected_question_niche"] for item in rounds}
    question_niche_members = {
        name: {identifier for item in rounds for identifier in item["question_niches"][name]}
        for name in QuestionNichePopulation.REQUIRED_NICHES
    }
    niche_allocations_differ = (
        len({tuple(sorted(identifiers)) for identifiers in question_niche_members.values()}) >= 2
    )
    checks = {
        "frozen_protocol_hash_matches": protocol_spec.protocol_hash == config["protocol_hash"],
        "frozen_candidate_generator_matches": generator_spec.spec_hash
        == protocol_spec.candidate_generator_hash,
        "predictions_preregistered_before_observations": _event_order_is_preregistered(
            paths["evidence"]
        ),
        "evidence_updates_fully_reconstruct": rebuilt_evidence.posterior == final_posterior
        and rebuilt_evidence.observations == len(rounds),
        "failed_paradigms_preserved": all(
            identifier in rebuilt_lineage.individuals
            for identifier in rebuilt_lineage.failure_reasons
        )
        and bool(rebuilt_lineage.failure_reasons),
        "survival_lifecycle_exercised": LineageStatus.DORMANT in statuses
        or LineageStatus.DEAD in statuses,
        "paradigm_splits_traceable": bool(split_events)
        and all(
            item["child_count"] >= 2
            and all(
                rebuilt_lineage.parents.get(child_id) == item["parent_id"]
                for child_id in item["child_ids"]
            )
            for item in split_events
        ),
        "unfrozen_recombination_blocked_and_audited": bool(recombination_decisions)
        and all(not item["allowed"] for item in recombination_decisions),
        "three_question_niches_maintained": all(question_niche_members.values()),
        "multiple_question_objectives_receive_resources": len(selected_niches) >= 2
        and niche_allocations_differ,
        "pareto_fronts_recorded_each_round": all(
            item["paradigm_pareto_front"] and item["question_pareto_front"] for item in rounds
        ),
        "pareto_archive_preserved": set(paradigm_pareto_archive)
        == {identifier for item in rounds for identifier in item["paradigm_pareto_archive"]},
        "question_lineage_fully_traceable": question_lineage_summary["questions"]
        == len(question_pool)
        and _retargeted_questions_trace(paths["scheduler"], rounds, question_pool),
        "frozen_mutation_operators_exercised": paradigm_mutations
        == set(generator_spec.allowed_mutations),
        "question_mutation_operators_exercised": question_mutations
        == set(config["question_mutations"]),
        "same_world_budget_and_separate_compute_budget_reported": budget.snapshot.world_queries
        <= limits.world_queries
        and budget.snapshot.candidate_evaluations <= limits.candidate_evaluations,
        "round_count_budget_or_convergence_driven": stop_reason
        in {"stable_top_k_convergence", "world_query_budget_exhausted"},
        "circular_reward_negative_control_passes": _circular_reward_negative_control(),
        "leakage_negative_control_passes": _leakage_negative_control(),
        "checkpoint_chain_verifies": load_latest_checkpoint(paths["checkpoints"]).checkpoint_hash
        == previous_checkpoint_hash,
        "preregistered_predictions_hash_protected": _ledger_rejects_virtual_tamper(
            paths["evidence"]
        ),
        "final_world_not_accessed": True,
    }
    report = {
        "schema_version": 1,
        "status": "step6_control_complete" if all(checks.values()) else "redo",
        "strategy_version": config["strategy_version"],
        "scope": "development Gray-Scott world only; final sealed tasks were not accessed",
        "protocol_hash": protocol_spec.protocol_hash,
        "candidate_generator_hash": generator_spec.spec_hash,
        "checks": checks,
        "stop_reason": stop_reason,
        "rounds": rounds,
        "budget_limits": asdict(limits),
        "budget": asdict(budget.snapshot),
        "question_generation_attempts": question_generation_attempts,
        "independent_compute_budget": {
            "candidate_question_evaluations": budget.snapshot.candidate_evaluations,
            "candidate_evaluation_cache_hits": budget.snapshot.candidate_evaluation_cache_hits,
            "question_generation_attempts": question_generation_attempts,
        },
        "comparison_budget_envelope": {
            "treatment_world_queries": limits.world_queries,
            "ablation_world_queries": limits.world_queries,
            "baseline_world_queries": limits.world_queries,
            "rule": "all arms receive the same world-query ceiling; compute is reported separately",
        },
        "paradigm_lineage": {
            "individuals": len(rebuilt_lineage.individuals),
            "events": rebuilt_lineage.event_count,
            "ledger_hash": rebuilt_lineage.ledger_hash,
            "failed": len(rebuilt_lineage.failure_reasons),
            "splits": len(split_events),
        },
        "question_population": {
            "unique_experiments": len(question_pool),
            "niches": list(QuestionNichePopulation.REQUIRED_NICHES),
            "lineage_events": question_lineage_summary["events"],
        },
        "paradigm_pareto_archive": sorted(paradigm_pareto_archive),
        "evidence_rebuild": asdict(rebuilt_evidence),
        "evidence_rules": {
            "update": protocol_spec.evidence_update_rule,
            "noise_calibration": protocol_spec.noise_calibration_rule,
            "noise_parameters": protocol_spec.noise_calibration_parameters,
            "survival": protocol_spec.survival_rule,
            "survival_parameters": protocol_spec.survival_parameters,
        },
        "final_posterior": final_posterior,
        "recombination_boundary": (
            "typed requests are audited, but execution is blocked because Gate PF did not "
            "freeze a recombination operator"
        ),
        "assurance": (
            "Step 6 is development-only scheduler evidence under local single-account "
            "self-audit; it is not final-world evidence."
        ),
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    identity = ExperimentIdentity(
        "step6-coevolution-control-v1", config, config["seed"], environment["git_revision"]
    )
    manifest = RunManifest(
        1,
        identity.experiment_id,
        "step6-coevolution-control-v1",
        identity.config_hash,
        config["seed"],
        environment,
        {
            "config": str(config_path),
            "protocol_hash": protocol_spec.protocol_hash,
            "candidate_generator_hash": generator_spec.spec_hash,
        },
        {
            "report": report_path.name,
            "report_hash": content_hash(report),
            "evidence_ledger": paths["evidence"].name,
            "evidence_ledger_hash": _last_event_hash(paths["evidence"]),
            "paradigm_lineage": paths["paradigm_lineage"].name,
            "paradigm_lineage_hash": rebuilt_lineage.ledger_hash,
            "question_lineage": paths["question_lineage"].name,
            "question_lineage_hash": _last_event_hash(paths["question_lineage"]),
            "scheduler_ledger": paths["scheduler"].name,
            "scheduler_ledger_hash": _last_event_hash(paths["scheduler"]),
            "checkpoint_hash": previous_checkpoint_hash,
        },
    )
    manifest.write_once(paths["manifest"])
    return report


def _validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise ValueError("unsupported Step 6 configuration schema")
    positive = (
        config["max_world_queries"],
        config["minimum_world_queries"],
        config["convergence_patience"],
        config["convergence_top_k"],
        config["question_niche_capacity"],
        config["eig_samples"],
        config["max_question_candidates_per_round"],
        config["max_question_generation_attempts"],
    )
    if min(positive) < 1 or config["minimum_world_queries"] > config["max_world_queries"]:
        raise ValueError("invalid Step 6 budget or convergence configuration")
    if not config["fixed_probes"] or not config["seed_questions"]:
        raise ValueError("Step 6 requires development probes and seed questions")


def _paths(output_dir: Path) -> dict[str, Path]:
    return {
        "meta": output_dir / "run-meta.json",
        "evidence": output_dir / "evidence.jsonl",
        "paradigm_lineage": output_dir / "paradigm-lineage.jsonl",
        "question_lineage": output_dir / "question-lineage.jsonl",
        "scheduler": output_dir / "scheduler.jsonl",
        "checkpoints": output_dir / "checkpoints",
        "manifest": output_dir / "manifest.json",
    }


def _initial_state(
    config,
    limits,
    mutator,
    probes,
    patch_weights,
    paradigm_ledger,
    question_ledger,
    scheduler_ledger,
    thresholds,
    protocol_hash,
    generator_spec,
):
    budget = BudgetLedger(limits)
    founder_genotype = gray_scott_founder_genotype(gray_scott_ir("step6-founder"))
    founder = _new_individual(founder_genotype, probes, 0, None, None, PatchCost(), patch_weights)
    paradigm_ledger.add_founder(founder)
    all_individuals = {founder.individual_id: founder}
    batch = mutator.generate_with_accounting(founder.genotype)
    budget.charge_candidate_generation(batch.attempted_mutations)
    children = []
    for generated in batch.offspring:
        if len(all_individuals) >= generator_spec.maximum_candidates_per_task:
            break
        budget.charge_candidate_evaluation()
        child = _new_individual(
            generated.genotype,
            probes,
            1,
            founder,
            generated.mutation,
            generated.patch_cost,
            patch_weights,
        )
        paradigm_ledger.add_offspring(child)
        all_individuals[child.individual_id] = child
        children.append(child.individual_id)
    split_events = []
    if len(children) >= 2:
        split = {
            "round": -1,
            "parent_id": founder.individual_id,
            "child_count": len(children),
            "child_ids": children,
        }
        split_events.append(split)
        scheduler_ledger.append("paradigm_split", split)
    active_ids = tuple(sorted(all_individuals)[: sum(config["initial_paradigm_niches"].values())])
    question_pool = {}
    for index, raw in enumerate(config["seed_questions"]):
        question = _question_from_raw(raw, index, active_ids)
        key = _experiment_hash(question.experiment)
        question_pool[key] = (question, 0, None, None)
        question_ledger.append(
            "question_seeded", _question_lineage_payload(question, 0, None, None)
        )
    scheduler_ledger.append(
        "run_started",
        {
            "protocol_hash": protocol_hash,
            "candidate_generator_hash": generator_spec.spec_hash,
            "world_query_limit": limits.world_queries,
        },
    )
    return {
        "completed_round": -1,
        "individuals": [individual_to_dict(item) for item in all_individuals.values()],
        "questions": _questions_to_state(question_pool),
        "history": [],
        "prediction_cache": [],
        "active_paradigm_ids": list(active_ids),
        "active_question_keys": list(question_pool),
        "rounds": [],
        "top_k_history": [],
        "split_events": split_events,
        "recombination_decisions": [],
        "paradigm_mutations": sorted(
            item.mutation.operator for item in all_individuals.values() if item.mutation
        ),
        "question_mutations": [],
        "question_generation_attempts": len(question_pool),
        "paradigm_pareto_archive": [],
        "budget": asdict(budget.snapshot),
    }


def _resume_state(paths, config, limits, protocol_hash):
    if not paths["meta"].exists() or paths["manifest"].exists():
        raise ValueError("resume requires an incomplete Step 6 output")
    meta = json.loads(paths["meta"].read_text(encoding="utf-8"))
    if meta["config_hash"] != content_hash(config) or meta["protocol_hash"] != protocol_hash:
        raise ValueError("resume configuration differs from the interrupted run")
    loaded = load_latest_checkpoint(paths["checkpoints"])
    state = loaded.state
    snapshot = BudgetSnapshot(**state["budget"])
    BudgetLedger.resume(limits, snapshot)
    if (
        rebuild_lineage(paths["paradigm_lineage"]).ledger_hash
        != state["ledger_hashes"]["paradigm_lineage"]
    ):
        raise ValueError("paradigm lineage advanced beyond the checkpoint")
    for name in ("evidence", "question_lineage", "scheduler"):
        if _last_event_hash(paths[name]) != state["ledger_hashes"][name]:
            raise ValueError(f"{name} advanced beyond the checkpoint")
    return state, meta["environment"], loaded.checkpoint_hash


def _generate_paradigms(
    active_ids,
    all_individuals,
    history,
    cache,
    budget,
    mutator,
    probes,
    weights,
    ledger,
    scheduler_ledger,
    thresholds,
    max_candidates,
    mutation_operators,
    noise_floor,
):
    splits = []
    for parent_id in active_ids:
        if len(all_individuals) >= max_candidates:
            break
        parent = all_individuals[parent_id]
        batch = mutator.generate_with_accounting(parent.genotype)
        remaining = budget.limits.candidate_generations - budget.snapshot.candidate_generations
        if batch.attempted_mutations > remaining:
            break
        budget.charge_candidate_generation(batch.attempted_mutations)
        children = []
        for generated in batch.offspring:
            if len(all_individuals) >= max_candidates:
                break
            if generated.genotype.genotype_id in all_individuals:
                continue
            budget.charge_candidate_evaluation()
            child = _new_individual(
                generated.genotype,
                probes,
                parent.generation + 1,
                parent,
                generated.mutation,
                generated.patch_cost,
                weights,
            )
            ledger.add_offspring(child)
            all_individuals[child.individual_id] = child
            children.append(child.individual_id)
            mutation_operators.add(generated.mutation.operator)
        if len(children) >= 2:
            event = {
                "round": len(history),
                "parent_id": parent_id,
                "child_count": len(children),
                "child_ids": children,
            }
            scheduler_ledger.append("paradigm_split", event)
            splits.append(event)
    return splits


def _generate_questions(
    active_keys,
    question_pool,
    mutator,
    ledger,
    mutation_operators,
    attempts,
    max_attempts,
    round_index,
):
    for key in active_keys:
        if attempts >= max_attempts or key not in question_pool:
            break
        base, _generation, _parent, _mutation = question_pool[key]
        parent = base
        for child, mutation in mutator.generate(parent, round_index):
            if attempts >= max_attempts:
                break
            attempts += 1
            mutation_operators.add(mutation.operator)
            child_key = _experiment_hash(child.experiment)
            if child_key in question_pool:
                continue
            question_pool[child_key] = (child, round_index, parent.semantic_hash, mutation)
            ledger.append(
                "question_mutated",
                _question_lineage_payload(child, round_index, parent.semantic_hash, mutation),
            )
    return attempts


def _rescore_individuals(
    individuals,
    history,
    cache,
    budget,
    thresholds,
    noise_floor,
    *,
    advance_checkpoint,
):
    if not history:
        uniform = 1.0 / len(individuals)
        return tuple(
            replace(item, evidence_score=uniform, predictive_gain=uniform) for item in individuals
        )
    candidate_ids = tuple(item.individual_id for item in individuals)
    evidence_history = _history_for_candidates(individuals, history, cache, budget)
    posterior = posterior_from_history(candidate_ids, evidence_history, noise_floor)
    rescored = []
    for item in individuals:
        score = posterior[item.individual_id]
        below = item.checkpoints_below_viability
        if advance_checkpoint:
            below = below + 1 if score < thresholds["minimum_predictive_gain"] else 0
        rescored.append(
            replace(
                item,
                evidence_score=score,
                predictive_gain=score,
                checkpoints_below_viability=below,
                hard_contradictions=item.hard_contradictions,
                status=LineageStatus.ACTIVE,
            )
        )
    return tuple(rescored)


def _history_for_candidates(individuals, history, cache, budget):
    records = []
    for raw in history:
        experiment = _experiment_from_dict(raw["experiment"])
        records.append(
            EvidenceHistoryItem(
                raw["question_hash"],
                tuple(raw["observation"]),
                {
                    item.individual_id: _predict_cached(item, experiment, cache, budget)
                    for item in individuals
                },
            )
        )
    return tuple(records)


def _diagnose_questions(
    question_pool,
    paradigms,
    posterior,
    world,
    weights,
    cache,
    budget,
    config,
    round_index,
    noise_floor,
):
    diagnosed = []
    for key in sorted(question_pool)[: config["max_question_candidates_per_round"]]:
        question, generation, parent_hash, mutation = question_pool[key]
        current = replace(
            question, target_paradigm_ids=tuple(item.individual_id for item in paradigms)
        )
        missing = sum(
            (item.genotype.genotype_hash, _experiment_hash(current.experiment)) not in cache
            for item in paradigms
        )
        remaining = budget.limits.candidate_evaluations - budget.snapshot.candidate_evaluations
        if missing > remaining:
            break
        predictions = {
            item.individual_id: np.asarray(
                _predict_cached(item, current.experiment, cache, budget), dtype=float
            )
            for item in paradigms
        }
        eig_seed = int.from_bytes(
            hashlib.sha256(
                f"{config['seed']}:{round_index}:{current.semantic_hash}".encode()
            ).digest()[:8],
            "big",
        )
        likelihood_noise = calibrated_noise(
            len(next(iter(predictions.values()))),
            noise_floor,
        )
        diagnostics = QuestionDiagnostics(
            tuple(
                AnticipatedOutcome(item, tuple(float(value) for value in predictions[item]))
                for item in sorted(predictions)
            ),
            predicted_disagreement(posterior, predictions, noise=likelihood_noise),
            expected_information_gain(
                posterior,
                predictions,
                samples=config["eig_samples"],
                seed=eig_seed,
                noise=likelihood_noise,
            ),
            QuestionCost.estimate(current, world, weights),
        )
        diagnosed.append(
            QuestionIndividual(current, diagnostics, generation, parent_hash, mutation)
        )
    return tuple(diagnosed)


def _choose_question(selection, executed_experiments, round_index):
    niche_order = QuestionNichePopulation.REQUIRED_NICHES
    preferred = niche_order[round_index % len(niche_order)]
    by_hash = {item.genotype.semantic_hash: item for item in selection.selected}
    for niche in (
        *niche_order[round_index % len(niche_order) :],
        *niche_order[: round_index % len(niche_order)],
    ):
        for semantic_hash in selection.niches[niche]:
            candidate = by_hash.get(semantic_hash)
            if (
                candidate is not None
                and _experiment_hash(candidate.genotype.experiment) not in executed_experiments
            ):
                return candidate, niche
    return None, preferred


def _predict_cached(individual, experiment, cache, budget):
    key = (individual.genotype.genotype_hash, _experiment_hash(experiment))
    if key in cache:
        budget.charge_candidate_evaluation(cache_hit=True)
        return cache[key]
    budget.charge_candidate_evaluation()
    prediction = tuple(
        float(value) for value in summary_on_experiment(individual.genotype, experiment)
    )
    cache[key] = prediction
    return prediction


def _new_individual(genotype, probes, generation, parent, mutation, patch, weights):
    phenotype = phenotype_on_probes(genotype, probes)
    cumulative = patch if parent is None else parent.cumulative_patch_cost + patch
    structure_gain = (
        0.0
        if parent is None
        else structural_distance(parent.genotype.ir, genotype.ir)
        * (1.0 / (1.0 + behavior_distance(parent.phenotype, phenotype)))
    )
    return ParadigmIndividual(
        genotype,
        phenotype,
        generation,
        None if parent is None else parent.individual_id,
        mutation,
        patch,
        cumulative,
        description_length(
            genotype,
            search_metadata={
                "generation": generation,
                "cumulative_patch_cost": cumulative.weighted_total(weights),
            },
        ),
        1.0,
        0.05,
        structure_gain,
    )


def _apply_population_status(all_individuals, snapshot, population):
    for identifier in snapshot.active_ids:
        all_individuals[identifier] = replace(
            all_individuals[identifier], status=LineageStatus.ACTIVE
        )
    for identifier in snapshot.dormant_ids:
        if identifier in all_individuals:
            all_individuals[identifier] = replace(
                all_individuals[identifier], status=LineageStatus.DORMANT
            )
    for identifier, fossil in population.fossils.items():
        all_individuals[identifier] = fossil


def _living_individuals(all_individuals):
    return tuple(
        item
        for item in all_individuals.values()
        if item.status not in {LineageStatus.DEAD, LineageStatus.EQUIVALENT_DUPLICATE}
    )


def _serialize_state(
    round_index,
    all_individuals,
    question_pool,
    history,
    cache,
    active_paradigm_ids,
    active_question_keys,
    rounds,
    top_k_history,
    split_events,
    recombination_decisions,
    paradigm_mutations,
    question_mutations,
    question_generation_attempts,
    paradigm_pareto_archive,
    budget_snapshot,
    paths,
):
    return {
        "completed_round": round_index,
        "individuals": [
            individual_to_dict(all_individuals[key]) for key in sorted(all_individuals)
        ],
        "questions": _questions_to_state(question_pool),
        "history": history,
        "prediction_cache": [
            {"key": list(key), "prediction": list(cache[key])} for key in sorted(cache)
        ],
        "active_paradigm_ids": list(active_paradigm_ids),
        "active_question_keys": list(active_question_keys),
        "rounds": rounds,
        "top_k_history": [list(item) for item in top_k_history],
        "split_events": split_events,
        "recombination_decisions": recombination_decisions,
        "paradigm_mutations": sorted(paradigm_mutations),
        "question_mutations": sorted(question_mutations),
        "question_generation_attempts": question_generation_attempts,
        "paradigm_pareto_archive": sorted(paradigm_pareto_archive),
        "budget": asdict(budget_snapshot),
        "ledger_hashes": {
            "evidence": _last_event_hash(paths["evidence"]),
            "paradigm_lineage": rebuild_lineage(paths["paradigm_lineage"]).ledger_hash,
            "question_lineage": _last_event_hash(paths["question_lineage"]),
            "scheduler": _last_event_hash(paths["scheduler"]),
        },
    }


def _questions_to_state(question_pool):
    return [
        {
            "key": key,
            "question": asdict(question),
            "generation": generation,
            "parent_hash": parent_hash,
            "mutation": None if mutation is None else asdict(mutation),
        }
        for key, (question, generation, parent_hash, mutation) in sorted(question_pool.items())
    ]


def _questions_from_state(items):
    result = {}
    for item in items:
        raw = item["question"]
        question = QuestionGenotype(
            raw["question_id"],
            _experiment_from_dict(raw["experiment"]),
            tuple(raw["target_paradigm_ids"]),
            raw["novelty_label"],
            raw["schema_version"],
        )
        mutation = QuestionMutation(**item["mutation"]) if item["mutation"] else None
        result[item["key"]] = (
            question,
            item["generation"],
            item["parent_hash"],
            mutation,
        )
    return result


def _question_from_raw(raw, index, target_ids):
    experiment = GrayScottExperiment(
        f"step6-seed-{index}",
        GrayScottParameters(feed=raw["feed"], kill=raw["kill"]),
        raw["initial_family"],
        raw["initial_seed"],
        raw["grid_size"],
        raw["steps"],
        boundary=raw["boundary"],
        measurement=MeasurementSpec(sample_every=raw["steps"], noise_std=raw["noise_std"]),
    )
    return QuestionGenotype(f"step6-seed-{index}", experiment, target_ids, raw["label"])


def _experiment_from_dict(raw):
    parameters = GrayScottParameters(**raw["parameters"])
    measurement_raw = raw["measurement"]
    measurement = MeasurementSpec(
        sample_every=measurement_raw["sample_every"],
        downsample=measurement_raw["downsample"],
        mixing=tuple(tuple(row) for row in measurement_raw["mixing"]),
        visible_channels=tuple(measurement_raw["visible_channels"]),
        noise_std=measurement_raw["noise_std"],
        mask_fraction=measurement_raw["mask_fraction"],
    )
    pulse = LocalPulse(**raw["intervention"]) if raw["intervention"] else None
    return GrayScottExperiment(
        experiment_id=raw["experiment_id"],
        parameters=parameters,
        initial_family=raw["initial_family"],
        initial_seed=raw["initial_seed"],
        grid_size=raw["grid_size"],
        steps=raw["steps"],
        dt=raw["dt"],
        spatial_spacing=raw["spatial_spacing"],
        clip_bounds=None if raw["clip_bounds"] is None else tuple(raw["clip_bounds"]),
        boundary=raw["boundary"],
        solver=raw["solver"],
        integrator=raw["integrator"],
        intervention=pulse,
        measurement=measurement,
    )


def _fixed_probes(raw_probes):
    return tuple(
        GrayScottExperiment(
            f"step6-probe-{index}",
            GrayScottParameters(feed=raw["feed"], kill=raw["kill"]),
            raw["initial_family"],
            raw["initial_seed"],
            raw["grid_size"],
            raw["steps"],
            boundary=raw["boundary"],
            measurement=MeasurementSpec(sample_every=raw["steps"]),
        )
        for index, raw in enumerate(raw_probes)
    )


def _experiment_hash(experiment):
    payload = asdict(experiment)
    payload.pop("experiment_id")
    return content_hash(payload)


def _question_lineage_payload(question, generation, parent_hash, mutation):
    return {
        "question": asdict(question),
        "semantic_hash": question.semantic_hash,
        "experiment_hash": _experiment_hash(question.experiment),
        "generation": generation,
        "parent_semantic_hash": parent_hash,
        "mutation": None if mutation is None else asdict(mutation),
    }


def _evidence_history_payload(item):
    return {
        "question_hash": item.question_hash,
        "observation": list(item.observation),
        "predictions": {key: list(values) for key, values in item.predictions.items()},
    }


def _converged(top_k_history, config):
    minimum = config["minimum_world_queries"]
    patience = config["convergence_patience"]
    return len(top_k_history) >= max(minimum, patience) and len(set(top_k_history[-patience:])) == 1


def _entropy(posterior):
    return -sum(value * math.log(value) for value in posterior.values() if value > 0.0)


def _event_order_is_preregistered(path):
    pending = False
    observations = 0
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            event_type = json.loads(line)["event_type"]
            if event_type == "prediction_preregistered":
                if pending:
                    return False
                pending = True
            elif event_type == "observation_received":
                if not pending:
                    return False
                pending = False
                observations += 1
    return observations > 0 and not pending


def _verify_question_lineage(path):
    verify_ledger(path)
    known: set[str] = set()
    events = 0
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            event_type = event["event_type"]
            payload = event["payload"]
            if event_type == "question_seeded":
                semantic_hash = payload["semantic_hash"]
                if payload["parent_semantic_hash"] is not None or semantic_hash in known:
                    raise ValueError("invalid or duplicate question founder")
                known.add(semantic_hash)
            elif event_type == "question_mutated":
                semantic_hash = payload["semantic_hash"]
                parent_hash = payload["parent_semantic_hash"]
                mutation = payload["mutation"]
                if (
                    parent_hash not in known
                    or semantic_hash in known
                    or mutation["parent_semantic_hash"] != parent_hash
                    or mutation["child_semantic_hash"] != semantic_hash
                ):
                    raise ValueError("question mutation lineage is not traceable")
                known.add(semantic_hash)
            elif event_type != "run_completed":
                raise ValueError(f"unsupported question lineage event: {event_type}")
            events += 1
    return {"questions": len(known), "events": events}


def _retargeted_questions_trace(path, rounds, question_pool):
    base_hashes = {item[0].semantic_hash for item in question_pool.values()}
    mappings: set[tuple[int, str]] = set()
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event["event_type"] != "question_retargeted_for_round":
                continue
            payload = event["payload"]
            if payload["base_question_hash"] not in base_hashes:
                return False
            if len(set(payload["target_paradigm_ids"])) < 2:
                return False
            mappings.add((payload["round"], payload["selected_question_hash"]))
    return mappings == {(item["round"], item["selected_question_hash"]) for item in rounds}


def _ledger_rejects_virtual_tamper(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event["event_type"] != "prediction_preregistered":
                continue
            claimed_hash = event.pop("event_hash")
            predictions = event["payload"]["predictions"]
            first_id = sorted(predictions)[0]
            predictions[first_id][0] += 1.0
            return content_hash(event) != claimed_hash
    return False


def _circular_reward_negative_control():
    prior = {"a": 0.5, "b": 0.5}
    predictions = {"a": (0.0,) * 8, "b": (0.0,) * 8}
    posterior = update_posterior(prior, predictions, (0.0,) * 8, 0.01)
    return (
        posterior == prior
        and predicted_disagreement(
            prior, {key: np.asarray(value) for key, value in predictions.items()}
        )
        == 0.0
    )


def _leakage_negative_control():
    forbidden = {"observation", "hidden_label", "posterior", "update_rule"}
    return not (set(QuestionGenotype.__dataclass_fields__) & forbidden)


def _last_event_hash(path):
    return json.loads(path.read_text(encoding="utf-8").splitlines()[-1])["event_hash"]
