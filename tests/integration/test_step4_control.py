import json
from pathlib import Path

from scientific_parallax.evolution.experiment import run_step4_control
from scientific_parallax.evolution.lineage import rebuild_lineage


def test_step4_fixed_question_control_is_reproducible_and_auditable(tmp_path: Path) -> None:
    output = tmp_path / "step4"
    report = run_step4_control(
        Path("configs/experiments/step4-paradigm-evolution.json"),
        output,
    )
    assert report["status"] == "step4_control_complete"
    assert all(report["checks"].values())
    assert report["lineage"]["offspring"] > 0
    assert report["lineage"]["failed_or_equivalent_fossils"] > 0
    assert report["budget"]["candidate_generations"] <= 128
    assert report["budget"]["candidate_evaluations"] <= 4096
    assert "final sealed tasks were not accessed" in report["scope"]
    assert rebuild_lineage(output / "lineage.jsonl").ledger_hash == report["lineage"]["ledger_hash"]
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["inputs"]["protocol_hash"] == report["protocol_hash"]
