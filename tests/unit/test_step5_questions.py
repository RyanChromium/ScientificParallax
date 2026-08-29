import inspect
from dataclasses import fields, replace

import numpy as np
import pytest

from scientific_parallax.baselines.gray_scott import fixed_candidate_pool
from scientific_parallax.questions.model import (
    QuestionCost,
    QuestionCostWeights,
    QuestionDiagnostics,
    QuestionGenotype,
    QuestionIndividual,
)
from scientific_parallax.questions.mutation import (
    ALLOWED_QUESTION_MUTATIONS,
    FrozenQuestionMutator,
)
from scientific_parallax.questions.population import QuestionPopulation
from scientific_parallax.questions.scoring import (
    IndependentEvidenceEngine,
    diagnose_question,
    expected_information_gain,
    predicted_disagreement,
    summary_noise,
)
from scientific_parallax.worlds.gray_scott import (
    GrayScottExperiment,
    GrayScottWorld,
    MeasurementSpec,
)


def _question(identifier: str = "q", label: str = "plain") -> QuestionGenotype:
    ids = tuple(item.candidate_id for item in fixed_candidate_pool())
    return QuestionGenotype(
        identifier,
        GrayScottExperiment(
            identifier,
            grid_size=12,
            steps=8,
            measurement=MeasurementSpec(sample_every=8, noise_std=0.006),
        ),
        ids,
        label,
    )


def _individual(question: QuestionGenotype) -> QuestionIndividual:
    paradigms = fixed_candidate_pool()
    posterior = {item.candidate_id: 1.0 / len(paradigms) for item in paradigms}
    diagnostics = diagnose_question(
        question,
        paradigms,
        posterior,
        GrayScottWorld(1),
        QuestionCostWeights(),
        eig_samples=16,
        seed=2,
    )
    return QuestionIndividual(question, diagnostics, 0)


def test_question_identity_ignores_prose_and_display_identifier() -> None:
    first = _question("first", "ordinary")
    second = replace(
        first,
        question_id="second",
        experiment=replace(first.experiment, experiment_id="second"),
        novelty_label="revolutionary language",
    )
    assert first.semantic_hash == second.semantic_hash
    population = QuestionPopulation(4)
    result = population.select(
        (_individual(first), _individual(second)),
        GrayScottWorld(),
        set(first.target_paradigm_ids),
    )
    assert sum(item.reason == "semantic_duplicate" for item in result.rejected) == 1


def test_mutations_are_finite_traceable_and_executable() -> None:
    parent = _question()
    generated = FrozenQuestionMutator().generate(parent, generation=1)
    assert {mutation.operator for _, mutation in generated} == set(ALLOWED_QUESTION_MUTATIONS)
    assert len(generated) == len(ALLOWED_QUESTION_MUTATIONS)
    for child, mutation in generated:
        GrayScottWorld().validate_experiment(child.experiment)
        assert mutation.parent_semantic_hash == parent.semantic_hash
        assert mutation.child_semantic_hash == child.semantic_hash


def test_cost_counts_simulation_measurement_and_intervention_separately() -> None:
    parent = _question()
    pulse = next(
        child
        for child, mutation in FrozenQuestionMutator().generate(parent, 1)
        if mutation.operator == "toggle_pulse"
    )
    base_cost = QuestionCost.estimate(parent, GrayScottWorld(), QuestionCostWeights())
    pulse_cost = QuestionCost.estimate(pulse, GrayScottWorld(), QuestionCostWeights())
    assert base_cost.simulation_work == pulse_cost.simulation_work
    assert base_cost.interventions == 0
    assert pulse_cost.interventions == 1
    assert pulse_cost.weighted_total > base_cost.weighted_total


def test_known_disagreement_has_information_and_updates_independently() -> None:
    noise = summary_noise(8)
    posterior = {"a": 0.5, "b": 0.5}
    neutral = {"a": np.zeros(8), "b": np.zeros(8)}
    separating = {"a": np.zeros(8), "b": 4.0 * noise}
    assert predicted_disagreement(posterior, separating) > predicted_disagreement(
        posterior, neutral
    )
    assert expected_information_gain(
        posterior, separating, samples=64, seed=1
    ) > expected_information_gain(posterior, neutral, samples=64, seed=1)
    engine = IndependentEvidenceEngine(("a", "b"))
    updated = engine.update(separating, separating["a"])
    assert updated["a"] > 0.99
    assert set(inspect.signature(IndependentEvidenceEngine.update).parameters) == {
        "self",
        "predictions",
        "observation",
    }


def test_question_cannot_carry_hidden_truth_or_evidence_update() -> None:
    names = {item.name for item in fields(QuestionGenotype)}
    assert not names & {"hidden_label", "true_paradigm", "observation", "update_rule"}


def test_invalid_and_prediction_free_questions_receive_no_resource() -> None:
    valid = _individual(_question())
    invalid_question = replace(
        valid.genotype,
        question_id="invalid",
        experiment=replace(valid.genotype.experiment, experiment_id="invalid", grid_size=7),
    )
    invalid = replace(valid, genotype=invalid_question)
    no_difference = replace(
        valid,
        genotype=replace(valid.genotype, novelty_label="high linguistic novelty"),
        diagnostics=QuestionDiagnostics(
            valid.diagnostics.anticipated_outcomes,
            0.0,
            0.0,
            valid.diagnostics.cost,
        ),
    )
    population = QuestionPopulation(4)
    invalid_result = population.select(
        (invalid,), GrayScottWorld(), set(valid.genotype.target_paradigm_ids)
    )
    empty_result = population.select(
        (no_difference,), GrayScottWorld(), set(valid.genotype.target_paradigm_ids)
    )
    assert not invalid_result.selected
    assert invalid_result.rejected[0].reason.startswith("invalid:")
    assert not empty_result.selected
    assert empty_result.rejected[0].reason == "no_predictive_difference"


def test_unknown_mutation_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        FrozenQuestionMutator(("invent_a_story",))


def test_cost_weights_cannot_reward_expensive_questions() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        QuestionCostWeights(simulation=-1.0)
    with pytest.raises(ValueError, match="finite"):
        QuestionCostWeights(simulation=float("nan"))


def test_evidence_engine_rejects_malformed_inputs() -> None:
    engine = IndependentEvidenceEngine(("a", "b"))
    with pytest.raises(ValueError, match="shape"):
        engine.update({"a": np.zeros(4), "b": np.zeros(8)}, np.zeros(8))
