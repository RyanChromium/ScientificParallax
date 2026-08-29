import json
from pathlib import Path

from scientific_parallax.questions.experiment import run_step5_control
from scientific_parallax.step0.ledger import verify_ledger


def test_step5_fixed_paradigm_control_is_reproducible_and_auditable(tmp_path: Path) -> None:
    output = tmp_path / "step5"
    report = run_step5_control(
        Path("configs/experiments/step5-question-evolution.json"),
        output,
    )
    assert report["status"] == "step5_control_complete"
    assert all(report["checks"].values())
    assert report["budget"]["world_queries"] == 3
    assert report["budget"]["unique_questions"] > 2
    assert report["budget"]["question_generation_attempts"] >= report["budget"]["unique_questions"]
    assert len(report["rounds"]) == 3
    assert all("actual_minus_expected_information_gain" in item for item in report["rounds"])
    assert "final sealed tasks were not accessed" in report["scope"]
    verify_ledger(output / "evidence.jsonl")
    verify_ledger(output / "question-lineage.jsonl")
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["inputs"]["protocol_hash"] == report["protocol_hash"]

    replay = tmp_path / "step5-replay"
    replay_report = run_step5_control(
        Path("configs/experiments/step5-question-evolution.json"), replay
    )
    assert replay_report == report
    assert (replay / "evidence.jsonl").read_bytes() == (output / "evidence.jsonl").read_bytes()
    assert (replay / "question-lineage.jsonl").read_bytes() == (
        output / "question-lineage.jsonl"
    ).read_bytes()
