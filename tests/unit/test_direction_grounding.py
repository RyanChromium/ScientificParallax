from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scientific_parallax.direction.grounding import (
    assess_evidence_grounding,
    build_grounding_packets,
    execute_selected_experiment,
    validate_proposal,
)


def _proposal(packet: dict, *, family: str = "pulse_radius_at_fixed_total_dose") -> dict:
    high = sorted(
        packet["evidence_cells"],
        key=lambda row: abs(row["standardized_residual"]),
        reverse=True,
    )
    levels = {
        "pulse_radius_at_fixed_total_dose": (1.0, 4.0),
        "second_pulse_amplitude": (0.0, 0.32),
        "pulse_lag": (12.0, 36.0),
    }
    return {
        "schema_version": 1,
        "case_id": packet["case_id"],
        "research_question": "Does the response switch between two regimes?",
        "empirical_surprise": "The late response departs sharply from the frozen reference.",
        "evidence_cell_ids": [high[0]["cell_id"], high[1]["cell_id"]],
        "competing_explanations": [
            {"explanation_id": "explanation-1", "statement": "A threshold is crossed."},
            {"explanation_id": "explanation-2", "statement": "Only total dose matters."},
        ],
        "decisive_experiment": {
            "design_family": family,
            "level_a": levels[family][0],
            "level_b": levels[family][1],
            "controlled_variables": "Keep all other settings fixed.",
            "response_field": "field_b",
            "response_feature": "mean",
            "response_time": 60.0,
            "opposing_predictions": [
                {
                    "explanation_id": "explanation-1",
                    "relation": "a_greater_than_b",
                    "rationale": "Concentration crosses a threshold.",
                },
                {
                    "explanation_id": "explanation-2",
                    "relation": "approximately_equal",
                    "rationale": "The total dose is equal.",
                },
            ],
        },
        "stop_rule": "Stop the threshold direction if the responses are equal.",
        "scientific_payoff": "Separate trigger geometry from total input.",
        "prior_art_risk": "Threshold responses are well studied.",
        "literature_queries": ["trigger threshold spatial dynamics", "critical pulse radius"],
    }


def test_packets_remove_only_post_second_pulse_observations(tmp_path: Path) -> None:
    source = Path("artifacts/llm-hypothesis-screen-v1/run")
    output = tmp_path / "packets"
    manifest = build_grounding_packets(
        source / "design-commitment.json", source / "result.json", output
    )
    full = json.loads((output / "full/evidence.json").read_text())
    ablated = json.loads((output / "ablated/evidence.json").read_text())
    assert manifest["model_visible_role_labels"] is False
    assert len(full["evidence_cells"]) == len(ablated["evidence_cells"]) == 40
    changed = []
    for left, right in zip(full["evidence_cells"], ablated["evidence_cells"], strict=True):
        assert left["cell_id"] == right["cell_id"]
        if left["observed"] != right["observed"]:
            changed.append(left)
            assert left["time"] > 42
            assert right["observed"] == pytest.approx(right["reference_prediction"])
    assert len(changed) == 14
    assert max(abs(row["standardized_residual"]) for row in full["evidence_cells"]) > 8


def test_proposal_validation_rejects_nonopposing_or_invalid_design(tmp_path: Path) -> None:
    source = Path("artifacts/llm-hypothesis-screen-v1/run")
    output = tmp_path / "packets"
    build_grounding_packets(source / "design-commitment.json", source / "result.json", output)
    packet = json.loads((output / "full/evidence.json").read_text())
    proposal = _proposal(packet)
    validate_proposal(proposal, packet)

    same_predictions = copy.deepcopy(proposal)
    same_predictions["decisive_experiment"]["opposing_predictions"][1]["relation"] = (
        "a_greater_than_b"
    )
    with pytest.raises(ValueError, match="different allowed predictions"):
        validate_proposal(same_predictions, packet)

    invalid_level = copy.deepcopy(proposal)
    invalid_level["decisive_experiment"]["level_b"] = 99
    with pytest.raises(ValueError, match="distinct allowed values"):
        validate_proposal(invalid_level, packet)

    duplicate_citation = copy.deepcopy(proposal)
    duplicate_citation["evidence_cell_ids"][1] = duplicate_citation["evidence_cell_ids"][0]
    with pytest.raises(ValueError, match="missing or insufficient"):
        validate_proposal(duplicate_citation, packet)


def test_grounding_requires_stability_anchors_and_counterfactual_change(tmp_path: Path) -> None:
    source = Path("artifacts/llm-hypothesis-screen-v1/run")
    output = tmp_path / "packets"
    build_grounding_packets(source / "design-commitment.json", source / "result.json", output)
    full = json.loads((output / "full/evidence.json").read_text())
    ablated = json.loads((output / "ablated/evidence.json").read_text())
    full_proposals = [_proposal(full), _proposal(full)]
    ablated_proposals = [
        _proposal(ablated, family="pulse_lag"),
        _proposal(ablated, family="pulse_lag"),
    ]
    for proposal in ablated_proposals:
        proposal["decisive_experiment"]["response_feature"] = "gradient_energy"
    assessment = assess_evidence_grounding(full_proposals, ablated_proposals, full, ablated)
    assert assessment["full_replicate_stability"] is True
    assert assessment["counterfactual_change"] is True
    assert assessment["success_rule_met"] is True

    unstable = copy.deepcopy(full_proposals)
    unstable[1]["decisive_experiment"]["response_time"] = 48.0
    failed = assess_evidence_grounding(unstable, ablated_proposals, full, ablated)
    assert failed["success_rule_met"] is False


def test_selected_experiment_executes_frozen_qualitative_contrast(tmp_path: Path) -> None:
    source = Path("artifacts/llm-hypothesis-screen-v1/run")
    output = tmp_path / "packets"
    build_grounding_packets(source / "design-commitment.json", source / "result.json", output)
    packet_path = output / "full/evidence.json"
    packet = json.loads(packet_path.read_text())
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(_proposal(packet)))
    result_path = tmp_path / "result.json"
    result = execute_selected_experiment(
        Path("configs/experiments/latent-discovery-pilot.json"),
        packet_path,
        proposal_path,
        result_path,
    )
    assert result_path.exists()
    assert result["observed_relation"] in {
        "a_greater_than_b",
        "a_less_than_b",
        "approximately_equal",
    }
    assert result["decision"] in {
        "support_explanation-1",
        "support_explanation-2",
        "inconclusive_stop",
    }
