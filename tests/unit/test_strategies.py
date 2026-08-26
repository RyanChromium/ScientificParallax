import random

from scientific_parallax.step0.evidence import EvidenceEngine
from scientific_parallax.step0.paradigms import fixed_paradigms
from scientific_parallax.step0.strategies import (
    expected_information_gain,
    select_bayesian_design,
    select_max_disagreement,
)
from scientific_parallax.step0.world import finite_question_pool


def test_expected_information_gain_is_nonnegative() -> None:
    paradigms = fixed_paradigms()
    posterior = EvidenceEngine([p.paradigm_id for p in paradigms]).posterior
    for question in finite_question_pool():
        assert expected_information_gain(question, paradigms, posterior) >= -1e-8


def test_bayesian_design_avoids_raw_disagreement_noise_trap() -> None:
    paradigms = fixed_paradigms()
    posterior = EvidenceEngine([p.paradigm_id for p in paradigms]).posterior
    questions = finite_question_pool()
    raw_choice = select_max_disagreement(questions, paradigms, posterior, random.Random(0), 41)
    bayes_choice = select_bayesian_design(questions, paradigms, posterior, random.Random(0), 41)
    assert bayes_choice.noise_std < raw_choice.noise_std
