import json
from pathlib import Path

from scientific_parallax.step0.experiment import ExperimentConfig, run_experiment
from scientific_parallax.step0.ledger import verify_ledger
from scientific_parallax.step0.paradigms import TRUE_PARADIGM_ID


def test_full_bayesian_run_is_reproducible(tmp_path: Path) -> None:
    config = ExperimentConfig(max_queries=12)
    first = run_experiment(config, "bayesian_design", tmp_path / "first", seed=44)
    second = run_experiment(config, "bayesian_design", tmp_path / "second", seed=44)

    assert first.winner_id == TRUE_PARADIGM_ID
    assert first.final_true_posterior == second.final_true_posterior
    assert first.sustained_identification_query == second.sustained_identification_query
    verify_ledger(Path(first.ledger_path))

    first_lines = Path(first.ledger_path).read_text(encoding="utf-8").splitlines()
    second_lines = Path(second.ledger_path).read_text(encoding="utf-8").splitlines()
    first_events = [json.loads(line) for line in first_lines]
    second_events = [json.loads(line) for line in second_lines]
    assert first_events == second_events
