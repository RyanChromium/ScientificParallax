import pytest

from scientific_parallax.core.budget import BudgetExceeded, BudgetLedger, BudgetLimits
from scientific_parallax.core.schema import ArtifactKind, MigrationRegistry, validate_schema


def test_budget_accounting_charges_misses_but_not_cache_hits() -> None:
    ledger = BudgetLedger(BudgetLimits(2, 2, 1))
    ledger.charge_world_query(2)
    ledger.charge_candidate_generation(2)
    ledger.charge_candidate_evaluation()
    ledger.charge_candidate_evaluation(cache_hit=True)
    assert ledger.snapshot.candidate_evaluations == 1
    assert ledger.snapshot.candidate_evaluation_cache_hits == 1
    with pytest.raises(BudgetExceeded):
        ledger.charge_candidate_evaluation()


def test_budget_rejects_charge_before_crossing_ceiling() -> None:
    ledger = BudgetLedger(BudgetLimits(1, 1, 1))
    with pytest.raises(BudgetExceeded):
        ledger.charge_world_query(2)
    assert ledger.snapshot.world_queries == 0


def test_schema_rejects_missing_and_future_versions() -> None:
    with pytest.raises(ValueError, match="schema_version"):
        validate_schema(ArtifactKind.REPORT, {})
    with pytest.raises(ValueError, match="future"):
        validate_schema(ArtifactKind.REPORT, {"schema_version": 2})


def test_migration_registry_requires_explicit_transition() -> None:
    registry = MigrationRegistry()
    artifact = {"schema_version": 1, "value": "kept"}
    assert registry.migrate_current(ArtifactKind.REPORT, artifact) == artifact
