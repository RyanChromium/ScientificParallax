from pathlib import Path

from scientific_parallax.coevolution.evidence import rebuild_coevolution_evidence
from scientific_parallax.coevolution.scheduler import run_step6_control
from scientific_parallax.evolution.lineage import rebuild_lineage

CONFIG = Path("configs/experiments/step6-coevolution.json")


def test_step6_closes_loop_and_resumes_deterministically(tmp_path: Path) -> None:
    direct = tmp_path / "direct"
    direct_report = run_step6_control(CONFIG, direct)
    assert direct_report["status"] == "step6_control_complete"
    assert all(direct_report["checks"].values())
    assert 3 <= direct_report["budget"]["world_queries"] <= 4
    assert direct_report["paradigm_lineage"]["splits"] > 0
    assert direct_report["paradigm_lineage"]["failed"] > 0
    assert rebuild_lineage(direct / "paradigm-lineage.jsonl").individuals
    rebuilt = rebuild_coevolution_evidence(direct / "evidence.jsonl", 0.01)
    assert rebuilt.posterior == direct_report["final_posterior"]

    resumed = tmp_path / "resumed"
    interrupted = run_step6_control(CONFIG, resumed, interrupt_after_round=0)
    assert interrupted["status"] == "interrupted_checkpoint"
    resumed_report = run_step6_control(CONFIG, resumed, resume=True)
    assert resumed_report == direct_report
    for name in (
        "evidence.jsonl",
        "paradigm-lineage.jsonl",
        "question-lineage.jsonl",
        "scheduler.jsonl",
        "report.json",
    ):
        assert (resumed / name).read_bytes() == (direct / name).read_bytes()
