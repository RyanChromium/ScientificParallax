"""Exact, auditable accounting for frozen protocol resources."""

from __future__ import annotations

from dataclasses import asdict, dataclass


class BudgetExceeded(RuntimeError):
    """Raised before an operation would exceed a frozen resource ceiling."""


@dataclass(frozen=True, slots=True)
class BudgetLimits:
    world_queries: int
    candidate_generations: int
    candidate_evaluations: int

    def __post_init__(self) -> None:
        if min(asdict(self).values()) < 1:
            raise ValueError("all budget limits must be positive")


@dataclass(frozen=True, slots=True)
class BudgetSnapshot:
    world_queries: int
    candidate_generations: int
    candidate_evaluations: int
    candidate_evaluation_cache_hits: int


class BudgetLedger:
    """Charge protocol operations using rules fixed before evaluation."""

    def __init__(self, limits: BudgetLimits) -> None:
        self.limits = limits
        self._world_queries = 0
        self._candidate_generations = 0
        self._candidate_evaluations = 0
        self._candidate_evaluation_cache_hits = 0

    @classmethod
    def resume(cls, limits: BudgetLimits, snapshot: BudgetSnapshot) -> BudgetLedger:
        values = asdict(snapshot)
        if min(values.values()) < 0:
            raise ValueError("budget snapshot counts cannot be negative")
        if (
            snapshot.world_queries > limits.world_queries
            or snapshot.candidate_generations > limits.candidate_generations
            or snapshot.candidate_evaluations > limits.candidate_evaluations
        ):
            raise ValueError("budget snapshot exceeds its declared limits")
        ledger = cls(limits)
        ledger._world_queries = snapshot.world_queries
        ledger._candidate_generations = snapshot.candidate_generations
        ledger._candidate_evaluations = snapshot.candidate_evaluations
        ledger._candidate_evaluation_cache_hits = snapshot.candidate_evaluation_cache_hits
        return ledger

    @property
    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(
            self._world_queries,
            self._candidate_generations,
            self._candidate_evaluations,
            self._candidate_evaluation_cache_hits,
        )

    def _charge(self, resource: str, amount: int, limit: int) -> None:
        if amount < 1:
            raise ValueError("charges must be positive integers")
        attribute = f"_{resource}"
        next_value = getattr(self, attribute) + amount
        if next_value > limit:
            raise BudgetExceeded(f"{resource} budget exceeded: {next_value} > {limit}")
        setattr(self, attribute, next_value)

    def charge_world_query(self, amount: int = 1) -> None:
        self._charge("world_queries", amount, self.limits.world_queries)

    def charge_candidate_generation(self, amount: int = 1) -> None:
        self._charge(
            "candidate_generations",
            amount,
            self.limits.candidate_generations,
        )

    def charge_candidate_evaluation(self, *, cache_hit: bool = False) -> None:
        if cache_hit:
            self._candidate_evaluation_cache_hits += 1
            return
        self._charge(
            "candidate_evaluations",
            1,
            self.limits.candidate_evaluations,
        )
