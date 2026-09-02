"""Build and score a counterfactual test of evidence-grounded research direction choice.

The model sees anonymous numerical evidence, not the synthetic generator.  A paired
counterfactual packet removes one late unexplained response while preserving the
experiment, the reference model, and all earlier measurements.  Stable proposals on
the full packet must be operationally different from proposals on the counterfactual;
otherwise a plausible proposal may simply reflect the model's scientific prior.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from scientific_parallax.worlds.gray_scott import MeasurementSpec
from scientific_parallax.worlds.latent_gray_scott import (
    LatentGrayScottExperiment,
    LatentGrayScottWorld,
    LatentLaw,
    LatentPulse,
)

_FIELDS = ("field_a", "field_b")
_FEATURES = ("mean", "standard_deviation", "high_fraction", "gradient_energy")
_DESIGN_LEVELS: dict[str, tuple[float, ...]] = {
    "pulse_radius_at_fixed_total_dose": (1.0, 2.0, 3.0, 4.0),
    "second_pulse_amplitude": (0.0, 0.08, 0.17, 0.24, 0.32),
    "pulse_lag": (12.0, 24.0, 30.0, 36.0),
    "control_feed": (0.02, 0.035, 0.046),
    "control_kill": (0.052, 0.06, 0.064),
}
_RELATIONS = ("a_greater_than_b", "a_less_than_b", "approximately_equal")
_FEATURE_SCALES = dict(zip(_FEATURES, (0.05, 0.05, 0.05, 0.01), strict=True))
_PROMPT = """Read evidence.json and propose exactly one research question.

The question must be causally motivated by the strongest unexplained numerical pattern,
not by a generic wish to fit better. Cite exact cell_id values. Give two live explanations
with mutually inconsistent predictions under one experiment chosen from the supplied
executable design families. Do not add parameters as evidence, do not assume a hidden
benchmark answer, and do not name or infer a familiar simulator family. A null outcome
must change the research decision. Return only JSON matching response-schema.json.
"""


def build_grounding_packets(
    design_path: Path,
    result_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Create full and late-anomaly-ablated anonymous evidence packets."""

    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite grounding packets: {output_dir}")
    design = _read_json(design_path)
    result = _read_json(result_path)
    if result.get("design_commitment_sha256") != _file_sha256(design_path):
        raise ValueError("result is not bound to the supplied design commitment")
    if result.get("selected_experiment") != design.get("selected_experiment"):
        raise ValueError("design and result refer to different experiments")

    prediction = np.asarray(
        design["committed_predictions"]["saturating-v-removal"], dtype=float
    )
    observed = np.asarray(result["observed_summary"], dtype=float)
    scales = np.asarray(design["feature_scales"], dtype=float)
    if prediction.shape != observed.shape or prediction.size % (len(_FIELDS) * len(_FEATURES)):
        raise ValueError("unexpected evidence-vector shape")
    if scales.shape != (len(_FEATURES),) or np.any(scales <= 0):
        raise ValueError("unexpected feature scales")

    experiment = design["selected_experiment"]
    sample_every = int(experiment["sample_every"])
    steps = int(experiment["steps"])
    times = tuple(float(value) for value in range(sample_every, steps + 1, sample_every))
    expected_size = len(_FIELDS) * len(times) * len(_FEATURES)
    if prediction.size != expected_size:
        raise ValueError("evidence-vector length does not match experiment sampling")
    pulses = experiment["pulses"]
    if len(pulses) < 2:
        raise ValueError("grounding ablation requires a second pulse")
    second_pulse_time = float(pulses[1]["at_step"])

    full_rows = _evidence_rows(observed, prediction, scales, times)
    ablated_observed = observed.copy()
    for field_index in range(len(_FIELDS)):
        for time_index, time in enumerate(times):
            if time <= second_pulse_time:
                continue
            start = (field_index * len(times) + time_index) * len(_FEATURES)
            ablated_observed[start : start + len(_FEATURES)] = prediction[
                start : start + len(_FEATURES)
            ]
    ablated_rows = _evidence_rows(ablated_observed, prediction, scales, times)

    shared = {
        "schema_version": 1,
        "system": "anonymous_two_field_spatial_dynamics",
        "reference": "best previously tested state-free explanation; parameters frozen",
        "experiment": _public_experiment(experiment),
        "executable_design_families": [
            {"design_family": name, "allowed_levels": list(levels)}
            for name, levels in _DESIGN_LEVELS.items()
        ],
        "response_options": {
            "fields": list(_FIELDS),
            "features": list(_FEATURES),
            "times": [time for time in times if time > second_pulse_time],
            "relations": list(_RELATIONS),
        },
        "constraints": [
            "one local CPU experiment",
            "no parameter fitting after observation",
            "one design family with two distinct allowed levels",
            "negative outcome must kill or redirect the question",
        ],
    }
    packets = {}
    for role, rows in (("full", full_rows), ("ablated", ablated_rows)):
        evidence_hash = _content_hash(rows)
        packet = {
            **shared,
            "case_id": f"case-{evidence_hash[:12]}",
            "evidence_cells": rows,
        }
        role_dir = output_dir / role
        role_dir.mkdir(parents=True)
        _write_json(role_dir / "evidence.json", packet)
        _write_json(role_dir / "response-schema.json", response_json_schema(packet["case_id"]))
        (role_dir / "prompt.txt").write_text(_PROMPT, encoding="utf-8")
        packets[role] = packet

    manifest = {
        "schema_version": 1,
        "status": "counterfactual_packets_created",
        "source_design_sha256": _file_sha256(design_path),
        "source_result_sha256": _file_sha256(result_path),
        "full_case_id": packets["full"]["case_id"],
        "ablated_case_id": packets["ablated"]["case_id"],
        "ablation_rule": (
            "Replace all observed summaries strictly after the second pulse with the frozen "
            "reference prediction; preserve earlier measurements and experiment metadata."
        ),
        "model_visible_role_labels": False,
    }
    output_dir.mkdir(exist_ok=True)
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def response_json_schema(case_id: str) -> dict[str, Any]:
    """Return the strict schema for one executable research direction."""

    prediction = {
        "type": "object",
        "additionalProperties": False,
        "required": ["explanation_id", "relation", "rationale"],
        "properties": {
            "explanation_id": {"enum": ["explanation-1", "explanation-2"]},
            "relation": {"enum": list(_RELATIONS)},
            "rationale": {"type": "string", "minLength": 1, "maxLength": 500},
        },
    }
    explanation = {
        "type": "object",
        "additionalProperties": False,
        "required": ["explanation_id", "statement"],
        "properties": {
            "explanation_id": {"enum": ["explanation-1", "explanation-2"]},
            "statement": {"type": "string", "minLength": 1, "maxLength": 500},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "case_id",
            "research_question",
            "empirical_surprise",
            "evidence_cell_ids",
            "competing_explanations",
            "decisive_experiment",
            "stop_rule",
            "scientific_payoff",
            "prior_art_risk",
            "literature_queries",
        ],
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "case_id": {"type": "string", "const": case_id},
            "research_question": {"type": "string", "minLength": 1, "maxLength": 500},
            "empirical_surprise": {"type": "string", "minLength": 1, "maxLength": 800},
            "evidence_cell_ids": {
                "type": "array",
                "minItems": 2,
                "maxItems": 8,
                "items": {"type": "string", "pattern": "^field_[ab]-t[0-9]+-[a-z_]+$"},
            },
            "competing_explanations": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": explanation,
            },
            "decisive_experiment": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "design_family",
                    "level_a",
                    "level_b",
                    "controlled_variables",
                    "response_field",
                    "response_feature",
                    "response_time",
                    "opposing_predictions",
                ],
                "properties": {
                    "design_family": {"enum": list(_DESIGN_LEVELS)},
                    "level_a": {"type": "number"},
                    "level_b": {"type": "number"},
                    "controlled_variables": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 600,
                    },
                    "response_field": {"enum": list(_FIELDS)},
                    "response_feature": {"enum": list(_FEATURES)},
                    "response_time": {"enum": [48.0, 60.0]},
                    "opposing_predictions": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": prediction,
                    },
                },
            },
            "stop_rule": {"type": "string", "minLength": 1, "maxLength": 600},
            "scientific_payoff": {"type": "string", "minLength": 1, "maxLength": 600},
            "prior_art_risk": {"type": "string", "minLength": 1, "maxLength": 500},
            "literature_queries": {
                "type": "array",
                "minItems": 2,
                "maxItems": 4,
                "items": {"type": "string", "minLength": 1, "maxLength": 180},
            },
        },
    }


def validate_proposal(proposal: dict[str, Any], packet: dict[str, Any]) -> None:
    """Apply cross-field checks that JSON Schema cannot express."""

    if proposal.get("schema_version") != 1 or proposal.get("case_id") != packet.get("case_id"):
        raise ValueError("proposal is not bound to its evidence packet")
    cell_ids = {row["cell_id"] for row in packet["evidence_cells"]}
    cited = proposal.get("evidence_cell_ids", [])
    if (
        not isinstance(cited, list)
        or len(cited) < 2
        or len(cited) != len(set(cited))
        or not set(cited) <= cell_ids
    ):
        raise ValueError("proposal cites missing or insufficient evidence cells")
    explanations = proposal.get("competing_explanations", [])
    explanation_ids = [item.get("explanation_id") for item in explanations]
    if sorted(explanation_ids) != ["explanation-1", "explanation-2"]:
        raise ValueError("proposal must contain the two unique explanation identifiers")
    experiment = proposal.get("decisive_experiment", {})
    family = experiment.get("design_family")
    if family not in _DESIGN_LEVELS:
        raise ValueError("unknown experiment design family")
    level_a = float(experiment.get("level_a"))
    level_b = float(experiment.get("level_b"))
    if (
        level_a == level_b
        or level_a not in _DESIGN_LEVELS[family]
        or level_b not in _DESIGN_LEVELS[family]
    ):
        raise ValueError("experiment levels must be distinct allowed values")
    predictions = experiment.get("opposing_predictions", [])
    prediction_ids = [item.get("explanation_id") for item in predictions]
    relations = [item.get("relation") for item in predictions]
    if sorted(prediction_ids) != ["explanation-1", "explanation-2"]:
        raise ValueError("predictions must cover both explanations exactly once")
    if len(set(relations)) != 2 or not set(relations) <= set(_RELATIONS):
        raise ValueError("the two explanations must make different allowed predictions")


def assess_evidence_grounding(
    full_proposals: list[dict[str, Any]],
    ablated_proposals: list[dict[str, Any]],
    full_packet: dict[str, Any],
    ablated_packet: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate frozen two-by-two proposal samples without semantic judging."""

    if len(full_proposals) != 2 or len(ablated_proposals) != 2:
        raise ValueError("the frozen pilot requires two proposals per evidence condition")
    for proposal in full_proposals:
        validate_proposal(proposal, full_packet)
    for proposal in ablated_proposals:
        validate_proposal(proposal, ablated_packet)

    full_rows = {row["cell_id"]: row for row in full_packet["evidence_cells"]}
    ablated_rows = {row["cell_id"]: row for row in ablated_packet["evidence_cells"]}
    magnitudes = np.asarray(
        [abs(float(row["standardized_residual"])) for row in full_rows.values()], dtype=float
    )
    high_threshold = max(2.0, float(np.quantile(magnitudes, 0.8)))
    high_ids = {
        cell_id
        for cell_id, row in full_rows.items()
        if abs(float(row["standardized_residual"])) >= high_threshold
    }
    changed_ids = {
        cell_id
        for cell_id in full_rows
        if not np.isclose(
            full_rows[cell_id]["observed"], ablated_rows[cell_id]["observed"], atol=1e-12
        )
    }
    anchor_rows = []
    for proposal in full_proposals:
        cited = set(proposal["evidence_cell_ids"])
        anchor_rows.append(
            {
                "case_id": proposal["case_id"],
                "high_anomaly_citation_count": len(cited & high_ids),
                "ablated_cell_citation_count": len(cited & changed_ids),
                "passes": len(cited & high_ids) >= 2 and bool(cited & changed_ids),
            }
        )
    full_signatures = [_signature(item) for item in full_proposals]
    ablated_signatures = [_signature(item) for item in ablated_proposals]
    full_stable = full_signatures[0] == full_signatures[1]
    signature_distances = [
        sum(left != right for left, right in zip(full_signatures[0], signature, strict=True))
        for signature in ablated_signatures
    ]
    counterfactual_change = all(distance >= 2 for distance in signature_distances)
    success = all(item["passes"] for item in anchor_rows) and full_stable and counterfactual_change
    return {
        "schema_version": 1,
        "status": "grounding_passed" if success else "grounding_failed",
        "high_anomaly_threshold": high_threshold,
        "high_anomaly_cell_ids": sorted(high_ids),
        "ablated_cell_ids": sorted(changed_ids),
        "full_anchor_checks": anchor_rows,
        "full_signatures": [list(item) for item in full_signatures],
        "ablated_signatures": [list(item) for item in ablated_signatures],
        "full_replicate_stability": full_stable,
        "full_to_ablated_signature_distances": signature_distances,
        "counterfactual_change": counterfactual_change,
        "success_rule_met": success,
    }


def execute_selected_experiment(
    config_path: Path,
    packet_path: Path,
    proposal_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Execute a grounded proposal's frozen two-level experiment once."""

    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite experiment result: {output_path}")
    config = _read_json(config_path)
    packet = _read_json(packet_path)
    proposal = _read_json(proposal_path)
    validate_proposal(proposal, packet)
    experiment_spec = proposal["decisive_experiment"]
    base = _private_base_experiment(packet)
    experiment_a = _experiment_at_level(
        base, experiment_spec["design_family"], float(experiment_spec["level_a"]), "a"
    )
    experiment_b = _experiment_at_level(
        base, experiment_spec["design_family"], float(experiment_spec["level_b"]), "b"
    )
    world = _world_from_config(config)
    vector_a = world.observe(experiment_a).summary()
    vector_b = world.observe(experiment_b).summary()
    index = _response_index(
        experiment_spec["response_field"],
        experiment_spec["response_feature"],
        float(experiment_spec["response_time"]),
        base.steps,
        base.sample_every,
    )
    value_a = float(vector_a[index])
    value_b = float(vector_b[index])
    tolerance = 0.5 * _FEATURE_SCALES[experiment_spec["response_feature"]]
    observed_relation = _relation(value_a, value_b, tolerance)
    predictions = {
        item["explanation_id"]: item["relation"]
        for item in experiment_spec["opposing_predictions"]
    }
    matches = [name for name, relation in predictions.items() if relation == observed_relation]
    decision = f"support_{matches[0]}" if len(matches) == 1 else "inconclusive_stop"
    report = {
        "schema_version": 1,
        "status": "selected_experiment_complete",
        "proposal_sha256": _file_sha256(proposal_path),
        "packet_sha256": _file_sha256(packet_path),
        "config_sha256": _file_sha256(config_path),
        "design_family": experiment_spec["design_family"],
        "level_a": float(experiment_spec["level_a"]),
        "level_b": float(experiment_spec["level_b"]),
        "response_field": experiment_spec["response_field"],
        "response_feature": experiment_spec["response_feature"],
        "response_time": float(experiment_spec["response_time"]),
        "response_a": value_a,
        "response_b": value_b,
        "equality_tolerance": tolerance,
        "observed_relation": observed_relation,
        "committed_predictions": predictions,
        "decision": decision,
        "research_decision_changed": len(matches) == 1,
        "claim_boundary": (
            "One noiseless local development contrast in the existing synthetic world; no "
            "mechanism identity, generalization rate, or publication-level novelty claim."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output_path, report)
    return report


def _evidence_rows(
    observed: np.ndarray,
    prediction: np.ndarray,
    scales: np.ndarray,
    times: tuple[float, ...],
) -> list[dict[str, Any]]:
    rows = []
    for field_index, field in enumerate(_FIELDS):
        for time_index, time in enumerate(times):
            for feature_index, feature in enumerate(_FEATURES):
                index = (
                    (field_index * len(times) + time_index) * len(_FEATURES) + feature_index
                )
                residual = float(observed[index] - prediction[index])
                rows.append(
                    {
                        "cell_id": f"{field}-t{int(time)}-{feature}",
                        "field": field,
                        "time": time,
                        "feature": feature,
                        "observed": float(observed[index]),
                        "reference_prediction": float(prediction[index]),
                        "residual": residual,
                        "standardized_residual": residual / float(scales[feature_index]),
                    }
                )
    return rows


def _public_experiment(experiment: dict[str, Any]) -> dict[str, Any]:
    return {
        "grid_size": experiment["grid_size"],
        "steps": experiment["steps"],
        "sample_every": experiment["sample_every"],
        "boundary": experiment["boundary"],
        "control_feed": experiment["feed"],
        "control_kill": experiment["kill"],
        "initial_family": "localized_center_seed",
        "pulses": [
            {
                "time": item["at_step"],
                "radius": item["radius"],
                "amplitude": item["delta_v"],
            }
            for item in experiment["pulses"]
        ],
    }


def _signature(proposal: dict[str, Any]) -> tuple[str, ...]:
    experiment = proposal["decisive_experiment"]
    return (
        str(experiment["design_family"]),
        str(experiment["response_field"]),
        str(experiment["response_feature"]),
        str(float(experiment["response_time"])),
    )


def _private_base_experiment(packet: dict[str, Any]) -> LatentGrayScottExperiment:
    public = packet["experiment"]
    grid_size = int(public["grid_size"])
    center = grid_size // 2
    pulses = tuple(
        LatentPulse(
            at_step=int(item["time"]),
            center_y=center,
            center_x=center,
            radius=int(item["radius"]),
            delta_v=float(item["amplitude"]),
        )
        for item in public["pulses"]
    )
    sample_every = int(public["sample_every"])
    return LatentGrayScottExperiment(
        "direction-grounding-base",
        feed=float(public["control_feed"]),
        kill=float(public["control_kill"]),
        initial_family="center_square",
        initial_seed=940000,
        grid_size=grid_size,
        steps=int(public["steps"]),
        sample_every=sample_every,
        boundary=public["boundary"],
        pulses=pulses,
        measurement=MeasurementSpec(sample_every=sample_every),
    )


def _experiment_at_level(
    base: LatentGrayScottExperiment, family: str, level: float, suffix: str
) -> LatentGrayScottExperiment:
    pulses = list(base.pulses)
    if family == "pulse_radius_at_fixed_total_dose":
        radius = int(level)
        reference = pulses[1]
        reference_cells = _pulse_cell_count(base.grid_size, reference.radius)
        level_cells = _pulse_cell_count(base.grid_size, radius)
        pulses[1] = replace(
            reference,
            radius=radius,
            delta_v=reference.delta_v * reference_cells / level_cells,
        )
    elif family == "second_pulse_amplitude":
        pulses[1] = replace(pulses[1], delta_v=level)
    elif family == "pulse_lag":
        pulses[1] = replace(pulses[1], at_step=pulses[0].at_step + int(level))
    elif family == "control_feed":
        return replace(base, experiment_id=f"direction-level-{suffix}", feed=level)
    elif family == "control_kill":
        return replace(base, experiment_id=f"direction-level-{suffix}", kill=level)
    else:  # pragma: no cover - validate_proposal prevents this branch
        raise ValueError(f"unknown design family: {family}")
    return replace(base, experiment_id=f"direction-level-{suffix}", pulses=tuple(pulses))


def _pulse_cell_count(grid_size: int, radius: int) -> int:
    center = grid_size // 2
    yy, xx = np.ogrid[:grid_size, :grid_size]
    return int(np.sum((yy - center) ** 2 + (xx - center) ** 2 <= radius**2))


def _world_from_config(config: dict[str, Any]) -> LatentGrayScottWorld:
    cluster = config["truth_clusters"][0]
    return LatentGrayScottWorld(
        int(config["measurement_seed_base"]),
        LatentLaw(
            latent_drive=float(cluster["latent_drive"]),
            latent_decay=float(cluster["latent_decay"]),
            latent_feedback=float(cluster["latent_feedback"]),
        ),
    )


def _response_index(
    field: str,
    feature: str,
    time: float,
    steps: int,
    sample_every: int,
) -> int:
    times = tuple(float(value) for value in range(sample_every, steps + 1, sample_every))
    return (
        (_FIELDS.index(field) * len(times) + times.index(time)) * len(_FEATURES)
        + _FEATURES.index(feature)
    )


def _relation(value_a: float, value_b: float, tolerance: float) -> str:
    if abs(value_a - value_b) <= tolerance:
        return "approximately_equal"
    return "a_greater_than_b" if value_a > value_b else "a_less_than_b"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _content_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
