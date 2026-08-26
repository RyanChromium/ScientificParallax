from scientific_parallax.step0.paradigms import TRUE_PARADIGM_ID, fixed_paradigms
from scientific_parallax.step0.world import MisleadingScienceWorld, finite_question_pool


def test_fixed_pool_contains_eight_unique_combinations() -> None:
    paradigms = fixed_paradigms()
    assert len(paradigms) == 8
    assert len({paradigm.paradigm_id for paradigm in paradigms}) == 8
    assert TRUE_PARADIGM_ID in {paradigm.paradigm_id for paradigm in paradigms}


def test_true_candidate_matches_world_expectation() -> None:
    true_paradigm = next(
        paradigm for paradigm in fixed_paradigms() if paradigm.paradigm_id == TRUE_PARADIGM_ID
    )
    for question in finite_question_pool():
        expected = MisleadingScienceWorld.expected_value(question)
        assert true_paradigm.predict_mean(question) == expected


def test_question_outcomes_are_order_independent() -> None:
    first, second = finite_question_pool()[:2]
    world_a = MisleadingScienceWorld(99)
    observations_a = [world_a.observe(first), world_a.observe(second)]
    world_b = MisleadingScienceWorld(99)
    observations_b = [world_b.observe(second), world_b.observe(first)]
    assert observations_a[0] == observations_b[1]
    assert observations_a[1] == observations_b[0]
