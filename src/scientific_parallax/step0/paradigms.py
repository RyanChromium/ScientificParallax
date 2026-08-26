"""The eight preregistered paradigm candidates and diagnostic controls."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from scientific_parallax.step0.domain import Prediction, Question


def baseline(x: float) -> float:
    """The shared, locally successful theory."""
    return 0.5 + 0.8 * x


def theory_term(x: float) -> float:
    """A physical term missing from the shared baseline."""
    return 0.55 * x * x


def measurement_term(x: float) -> float:
    """Bias present only in the primary instrument."""
    return 0.70 * x if x >= 0.0 else -0.25 * x


def numerical_term(x: float) -> float:
    """Artifact present only in the primary numerical implementation."""
    return 0.45 * x * x * x


@dataclass(frozen=True, slots=True)
class Paradigm:
    """A deliberately small executable model family member."""

    paradigm_id: str
    includes_theory_term: bool
    includes_measurement_bias: bool
    includes_numerical_artifact: bool
    description: str

    def predict_mean(self, question: Question) -> float:
        value = baseline(question.x)
        if self.includes_theory_term:
            value += theory_term(question.x)
        if self.includes_measurement_bias and question.instrument == "primary":
            value += measurement_term(question.x)
        if self.includes_numerical_artifact and question.solver == "primary":
            value += numerical_term(question.x)
        return value

    def predict(self, question: Question) -> Prediction:
        return Prediction(self.paradigm_id, self.predict_mean(question), question.noise_std)


@dataclass(frozen=True, slots=True)
class ContradictoryControl:
    """A deterministic nonsense model that creates large but unsupported disagreement."""

    paradigm_id: str = "negative_control_contradictory"
    description: str = "Hash-derived sign flips unrelated to the world's causal structure."

    def predict_mean(self, question: Question) -> float:
        digest = sha256(question.question_id.encode("utf-8")).digest()
        sign = 1.0 if digest[0] % 2 == 0 else -1.0
        return baseline(question.x) + sign * (3.0 + abs(question.x))

    def predict(self, question: Question) -> Prediction:
        return Prediction(self.paradigm_id, self.predict_mean(question), question.noise_std)


def fixed_paradigms() -> tuple[Paradigm, ...]:
    """Return all 2^3 preregistered explanations in stable order."""
    paradigms: list[Paradigm] = []
    for theory in (False, True):
        for measurement in (False, True):
            for numerical in (False, True):
                bits = f"{int(theory)}{int(measurement)}{int(numerical)}"
                included = [
                    name
                    for enabled, name in (
                        (theory, "physical term"),
                        (measurement, "measurement bias"),
                        (numerical, "numerical artifact"),
                    )
                    if enabled
                ]
                description = (
                    "baseline only" if not included else "baseline + " + " + ".join(included)
                )
                paradigms.append(Paradigm(f"p_{bits}", theory, measurement, numerical, description))
    return tuple(paradigms)


TRUE_PARADIGM_ID = "p_111"
