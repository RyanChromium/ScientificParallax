"""A queryable synthetic world with separable anomaly sources."""

from __future__ import annotations

import hashlib
import random

from scientific_parallax.step0.domain import Observation, Question
from scientific_parallax.step0.paradigms import (
    baseline,
    measurement_term,
    numerical_term,
    theory_term,
)


class MisleadingScienceWorld:
    """Known ground truth hidden behind channel-specific systematic effects."""

    is_simulated = True
    has_sealed_ground_truth = True
    supports_novel_conditions = False
    supports_intervention = True
    supports_new_measurement = True

    def __init__(self, seed: int) -> None:
        self._seed = seed

    @staticmethod
    def expected_value(question: Question) -> float:
        value = baseline(question.x) + theory_term(question.x)
        if question.instrument == "primary":
            value += measurement_term(question.x)
        if question.solver == "primary":
            value += numerical_term(question.x)
        return value

    def observe(self, question: Question) -> Observation:
        # A question-specific stream gives every strategy the same potential
        # outcome for the same question, independent of query order.
        seed_material = f"{self._seed}:{question.question_id}".encode()
        local_seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
        rng = random.Random(local_seed)
        value = rng.gauss(self.expected_value(question), question.noise_std)
        return Observation(question.question_id, value, question.noise_std)


def finite_question_pool() -> tuple[Question, ...]:
    """Build the protocol-frozen pool of 32 executable questions.

    Extreme conditions have larger raw model disagreement but much noisier
    measurements. This creates a deliberate trap for pure disagreement search.
    """
    questions: list[Question] = []
    for x in (-2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0):
        noise_std = 0.10 + 0.20 * abs(x) ** 3
        for instrument in ("primary", "reference"):
            for solver in ("primary", "reference"):
                instrument_code = "p" if instrument == "primary" else "r"
                solver_code = "p" if solver == "primary" else "r"
                question_id = f"x{x:+.1f}_i{instrument_code}_s{solver_code}"
                questions.append(
                    Question(question_id, x, instrument, solver, noise_std)  # type: ignore[arg-type]
                )
    return tuple(questions)
