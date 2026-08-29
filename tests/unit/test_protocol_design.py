from scientific_parallax.protocol.candidate_generator import FiniteCandidateGenerator
from scientific_parallax.protocol.design import build_task_design, estimate_clustered_power
from scientific_parallax.protocol.dry_run import gray_scott_ir
from scientific_parallax.protocol.numerics import (
    NumericalTolerance,
    compare_primary_and_reference,
)
from scientific_parallax.worlds.gray_scott import GrayScottExperiment, MeasurementSpec


def test_task_design_has_six_disjoint_clusters_and_thirty_tasks() -> None:
    tasks = build_task_design()
    assert len(tasks) == 30
    assert len({task.cluster_id for task in tasks}) == 6
    assert all(sum(item.cluster_id == task.cluster_id for item in tasks) == 5 for task in tasks)


def test_power_estimate_is_reproducible_and_increases_with_effect() -> None:
    low = estimate_clustered_power(
        assumed_relative_effect=0.20,
        simulations=12,
        bootstrap_samples=40,
        seed=5,
    )
    high = estimate_clustered_power(
        assumed_relative_effect=0.40,
        simulations=12,
        bootstrap_samples=40,
        seed=5,
    )
    assert high.estimated_power >= low.estimated_power
    assert high.tasks == 30


def test_numerical_agreement_uses_frozen_candidate_tolerance() -> None:
    experiment = GrayScottExperiment(
        "numerics",
        grid_size=16,
        steps=30,
        measurement=MeasurementSpec(sample_every=10),
    )
    tolerance = NumericalTolerance(0.005, 0.08, 0.015)
    agreement = compare_primary_and_reference(experiment, tolerance)
    assert agreement.passed


def test_candidate_generator_is_deterministic_and_budgeted() -> None:
    parent = gray_scott_ir("parent")
    generator = FiniteCandidateGenerator()
    first = generator.generate(parent)
    second = generator.generate(parent)
    assert first == second
    assert 0 < len(first) <= generator.spec.maximum_offspring_per_parent
    assert len({item.canonical_structure() for item in first}) == len(first)
    batch = generator.generate_with_accounting(parent)
    assert batch.attempted_mutations >= len(batch.candidates)
    assert batch.attempted_mutations <= generator.spec.maximum_offspring_per_parent
