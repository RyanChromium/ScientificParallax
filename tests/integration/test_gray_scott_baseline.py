from pathlib import Path

from scientific_parallax.baselines.gray_scott import (
    TRUE_CANDIDATE_ID,
    CandidateEvidence,
    GrayScottBaselineConfig,
    baseline_question_pool,
    fixed_candidate_pool,
    run_selection_baseline,
)
from scientific_parallax.core.reproducibility import content_hash
from scientific_parallax.step0.ledger import EvidenceLedger, verify_ledger
from scientific_parallax.worlds.gray_scott import GrayScottExperiment, GrayScottWorld


def test_candidate_pool_has_one_declared_truth() -> None:
    candidates = fixed_candidate_pool()
    assert len(candidates) == 8
    assert sum(item.candidate_id == TRUE_CANDIDATE_ID for item in candidates) == 1


def test_bayesian_design_identifies_standard_law_in_small_run(tmp_path: Path) -> None:
    config = GrayScottBaselineConfig(grid_size=16, steps=30, max_queries=8, bed_samples=16)
    ledger_path = tmp_path / "ledger.jsonl"
    result = run_selection_baseline(
        config,
        "bayesian_design",
        seed=55,
        ledger_path=ledger_path,
    )
    assert result.final_true_posterior > 1.0 / len(fixed_candidate_pool())
    assert len(result.observation_summaries) == config.max_queries
    verify_ledger(ledger_path)


def test_evidence_rejects_candidate_mismatch() -> None:
    evidence = CandidateEvidence(["a", "b"])
    question = baseline_question_pool(GrayScottBaselineConfig())[0]
    assert question.experiment_id
    try:
        evidence.update({}, question.parameters.feed)  # type: ignore[arg-type]
    except ValueError as error:
        assert "do not match" in str(error)
    else:
        raise AssertionError("mismatched candidate evidence was accepted")


def test_interrupted_gray_scott_query_recovers_from_preregistered_ledger(
    tmp_path: Path,
) -> None:
    path = tmp_path / "gray-scott-ledger.jsonl"
    experiment = GrayScottExperiment("recovery", grid_size=16, steps=20)
    ledger = EvidenceLedger(path)
    prediction_hash = ledger.preregister(
        {"experiment_hash": experiment.content_hash, "predicted_summary": [0.0] * 8}
    )

    # The world is deterministic, so a restarted process can recompute the pending query.
    observation = GrayScottWorld().observe(experiment)
    resumed = EvidenceLedger.resume(path)
    resumed.record_observation(
        {
            "experiment_hash": observation.experiment_hash,
            "summary_hash": content_hash(observation.summary().tolist()),
        },
        prediction_hash,
    )
    verify_ledger(path)
