"""Finite multi-step structural mutations for discovering a hidden dynamical state."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from scientific_parallax.core.reproducibility import content_hash
from scientific_parallax.worlds.latent_gray_scott import LatentLaw


@dataclass(frozen=True, slots=True)
class LatentMutation:
    operator: str
    parent_model_hash: str
    child_model_hash: str


@dataclass(frozen=True, slots=True)
class LatentCandidate:
    candidate_id: str
    law: LatentLaw
    generation: int
    parent_id: str | None
    mutation: LatentMutation | None

    def __post_init__(self) -> None:
        self.law.validate()
        if self.generation < 0:
            raise ValueError("candidate generation cannot be negative")
        if (self.parent_id is None) != (self.mutation is None):
            raise ValueError("only founders may omit mutation provenance")

    @property
    def model_hash(self) -> str:
        return content_hash(asdict(self.law))

    @property
    def structural_stage(self) -> int:
        return self.law.structural_stage


def two_state_founders() -> tuple[LatentCandidate, ...]:
    """All initial candidates are intentionally structurally misspecified."""

    founders = []
    for index, scale in enumerate((0.70, 0.85, 1.00, 1.15, 1.30)):
        law = LatentLaw(
            has_latent_state=False,
            observed_drive_connected=False,
            reaction_feedback_connected=False,
            reaction_scale=scale,
        )
        founders.append(LatentCandidate(f"two-state-{index}", law, 0, None, None))
    return tuple(founders)


class LatentStructureMutator:
    """A complete latent feedback loop requires three separately recorded mutations."""

    OPERATORS = (
        "add_latent_state",
        "connect_observed_drive",
        "connect_reaction_feedback",
        "reaction_scale_low",
        "reaction_scale_high",
        "latent_timescale_fast",
        "latent_timescale_slow",
        "latent_feedback_low",
        "latent_feedback_high",
    )

    def generate(self, parent: LatentCandidate) -> tuple[LatentCandidate, ...]:
        children: list[LatentCandidate] = []
        for operator in self.OPERATORS:
            child_law = _mutate_law(parent.law, operator)
            if child_law is None or child_law == parent.law:
                continue
            child_hash = content_hash(asdict(child_law))
            mutation = LatentMutation(operator, parent.model_hash, child_hash)
            children.append(
                LatentCandidate(
                    f"latent-g{parent.generation + 1}-{child_hash[:12]}",
                    child_law,
                    parent.generation + 1,
                    parent.candidate_id,
                    mutation,
                )
            )
        return tuple(children)


def _mutate_law(law: LatentLaw, operator: str) -> LatentLaw | None:
    if operator == "add_latent_state" and not law.has_latent_state:
        return replace(law, has_latent_state=True)
    if (
        operator == "connect_observed_drive"
        and law.has_latent_state
        and not law.observed_drive_connected
    ):
        return replace(law, observed_drive_connected=True)
    if (
        operator == "connect_reaction_feedback"
        and law.observed_drive_connected
        and not law.reaction_feedback_connected
    ):
        return replace(law, reaction_feedback_connected=True)
    if operator == "reaction_scale_low":
        return replace(law, reaction_scale=max(0.4, law.reaction_scale * 0.85))
    if operator == "reaction_scale_high":
        return replace(law, reaction_scale=min(1.6, law.reaction_scale * 1.15))
    if operator == "latent_timescale_fast" and law.has_latent_state:
        return replace(
            law,
            latent_drive=min(0.16, law.latent_drive * 1.25),
            latent_decay=min(0.10, law.latent_decay * 1.25),
        )
    if operator == "latent_timescale_slow" and law.has_latent_state:
        return replace(
            law,
            latent_drive=max(0.03, law.latent_drive * 0.8),
            latent_decay=max(0.015, law.latent_decay * 0.8),
        )
    if operator == "latent_feedback_low" and law.reaction_feedback_connected:
        return replace(law, latent_feedback=max(0.5, law.latent_feedback * 0.75))
    if operator == "latent_feedback_high" and law.reaction_feedback_connected:
        return replace(law, latent_feedback=min(5.0, law.latent_feedback * 1.25))
    return None


def lineage_to_root(
    candidate_id: str, candidates: dict[str, LatentCandidate]
) -> tuple[LatentCandidate, ...]:
    lineage: list[LatentCandidate] = []
    current = candidates[candidate_id]
    while True:
        lineage.append(current)
        if current.parent_id is None:
            break
        current = candidates[current.parent_id]
    return tuple(reversed(lineage))
