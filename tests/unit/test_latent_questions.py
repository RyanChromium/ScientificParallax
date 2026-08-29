from scientific_parallax.discovery.latent_questions import (
    ALLOWED_LATENT_QUESTION_MUTATIONS,
    LatentQuestionMutator,
    seed_questions,
    validation_questions,
)


def test_question_grammar_is_executable_and_semantically_distinct() -> None:
    seeds = seed_questions(
        task_token="unit", initial_seed=4, grid_size=12, steps=36, sample_every=12
    )
    mutator = LatentQuestionMutator(ALLOWED_LATENT_QUESTION_MUTATIONS)
    children = mutator.generate(seeds[0], 1)
    assert len(children) == len(ALLOWED_LATENT_QUESTION_MUTATIONS)
    assert len({item.content_hash for item in children}) == len(children)


def test_validation_questions_are_disjoint_from_development_seeds() -> None:
    kwargs = dict(task_token="unit", initial_seed=4, grid_size=12, steps=36, sample_every=12)
    seeds = seed_questions(**kwargs)
    held_out = validation_questions(**kwargs)
    assert {item.content_hash for item in seeds}.isdisjoint(
        {item.content_hash for item in held_out}
    )
