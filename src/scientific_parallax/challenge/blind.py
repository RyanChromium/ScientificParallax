"""Semantic-hiding boundary for the Step 7 development challenge."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from scientific_parallax.worlds.base import WorldCapabilities
from scientific_parallax.worlds.gray_scott import GrayScottExperiment


@dataclass(frozen=True, slots=True)
class BlindTaskView:
    """The complete task information available to a selection strategy."""

    task_token: str
    capabilities: WorldCapabilities
    summary_dimension: int


@dataclass(frozen=True, slots=True)
class DevelopmentBlindTask:
    """Evaluator-owned task state; cluster coordinates and seeds stay behind this boundary."""

    task_token: str
    cluster_id: str
    cluster_task_index: int
    measurement_seed: int
    experiment: GrayScottExperiment

    @property
    def view(self) -> BlindTaskView:
        return BlindTaskView(
            self.task_token,
            WorldCapabilities(True, True, True, True, True),
            4 * len(self.experiment.measurement.visible_channels),
        )


def anonymous_task_token(seed: int, cluster_index: int, task_index: int) -> str:
    payload = f"step7-development\0{seed}\0{cluster_index}\0{task_index}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]
