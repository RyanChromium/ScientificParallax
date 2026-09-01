"""One-step development experiment for discriminating two LLM proposals."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from scientific_parallax.discovery.llm_hypothesis import (
    _baseline_hypothesis,
    _content_hash,
    _file_sha256,
    _frames_vector,
    _simulated_vector,
    _summary_frames,
    _validate_development_config,
    compile_hypothesis,
    parse_hypothesis_response,
)
from scientific_parallax.worlds.gray_scott import MeasurementSpec
from scientific_parallax.worlds.latent_gray_scott import (
    LatentGrayScottExperiment,
    LatentGrayScottWorld,
    LatentLaw,
    LatentPulse,
)

_MEMORY_ID = "latent-activation-memory"
_STATE_FREE_ID = "saturating-v-removal"
_SECONDARY_ID = "superquadratic-autocatalysis"
_FEATURE_SCALES = np.asarray((0.05, 0.05, 0.05, 0.01), dtype=float)
_MINIMUM_RELATIVE_GAIN = 0.10


def run_memory_discrimination(
    config_path: Path,
    response_path: Path,
    evaluation_path: Path,
    protocol_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Commit a candidate-only design, then query one synthetic development world."""

    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite discrimination output: {output_dir}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_development_config(config)
    response = json.loads(response_path.read_text(encoding="utf-8"))
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    hypotheses = {
        item.hypothesis_id: compile_hypothesis(item) for item in parse_hypothesis_response(response)
    }
    expected_ids = {_MEMORY_ID, _STATE_FREE_ID, _SECONDARY_ID}
    if set(hypotheses) != expected_ids:
        raise ValueError("response does not contain the frozen v0 proposal set")
    if evaluation.get("response_sha256") != _file_sha256(response_path):
        raise ValueError("evaluation is not bound to the supplied response")
    rows = {item["hypothesis_id"]: item for item in evaluation["hypotheses"]}
    if set(rows) != expected_ids:
        raise ValueError("evaluation does not contain the frozen v0 proposal set")
    parameters = {name: rows[name]["positive_fit_parameters"] for name in expected_ids}
    reaction_scale = float(evaluation["baseline"]["positive_parameters"]["reaction_scale"])

    pool = _intervention_pool()
    scored = []
    memory = hypotheses[_MEMORY_ID]
    state_free = hypotheses[_STATE_FREE_ID]
    for experiment in pool:
        memory_prediction = _simulated_vector(
            memory, parameters[_MEMORY_ID], experiment, reaction_scale
        )
        state_free_prediction = _simulated_vector(
            state_free, parameters[_STATE_FREE_ID], experiment, reaction_scale
        )
        scale = np.tile(_FEATURE_SCALES, memory_prediction.size // _FEATURE_SCALES.size)
        disagreement = float(
            np.sqrt(np.mean(((memory_prediction - state_free_prediction) / scale) ** 2))
        )
        scored.append(
            (
                disagreement,
                experiment.experiment_id,
                experiment,
                memory_prediction,
                state_free_prediction,
            )
        )
    _, _, selected, memory_prediction, state_free_prediction = sorted(
        scored, key=lambda item: (-item[0], item[1])
    )[0]
    selected_score = next(item[0] for item in scored if item[2] == selected)

    output_dir.mkdir(parents=True)
    design = {
        "schema_version": 1,
        "status": "design_committed_before_observation",
        "protocol_sha256": _file_sha256(protocol_path),
        "config_sha256": _file_sha256(config_path),
        "response_sha256": _file_sha256(response_path),
        "evaluation_sha256": _file_sha256(evaluation_path),
        "pool_size": len(pool),
        "feature_scales": _FEATURE_SCALES.tolist(),
        "primary_contrast": [_MEMORY_ID, _STATE_FREE_ID],
        "fitted_parameter_hashes": {
            name: _content_hash(parameters[name]) for name in sorted(parameters)
        },
        "selected_experiment": _experiment_record(selected),
        "standardized_disagreement": selected_score,
        "committed_predictions": {
            _MEMORY_ID: memory_prediction.tolist(),
            _STATE_FREE_ID: state_free_prediction.tolist(),
        },
        "prediction_hashes": {
            _MEMORY_ID: _array_hash(memory_prediction),
            _STATE_FREE_ID: _array_hash(state_free_prediction),
        },
    }
    design_path = output_dir / "design-commitment.json"
    design_path.write_text(json.dumps(design, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    world = _positive_world(config)
    observed_experiment = replace(
        selected,
        measurement=MeasurementSpec(sample_every=12, noise_std=0.004),
    )
    observation = world.observe(observed_experiment)
    observed_vector = _frames_vector(_summary_frames(observation.times, observation.fields))
    candidate_errors = {}
    candidate_predictions = {}
    for name in sorted(expected_ids):
        prediction = _simulated_vector(hypotheses[name], parameters[name], selected, reaction_scale)
        candidate_predictions[name] = prediction
        candidate_errors[name] = _rmse(prediction, observed_vector)
    baseline = compile_hypothesis(_baseline_hypothesis(reaction_scale))
    baseline_prediction = _simulated_vector(baseline, {}, selected, reaction_scale)
    candidate_predictions["two-field-baseline"] = baseline_prediction
    candidate_errors["two-field-baseline"] = _rmse(baseline_prediction, observed_vector)

    memory_error = candidate_errors[_MEMORY_ID]
    state_free_error = candidate_errors[_STATE_FREE_ID]
    baseline_error = candidate_errors["two-field-baseline"]
    gain_vs_state_free = _relative_gain(memory_error, state_free_error)
    gain_vs_baseline = _relative_gain(memory_error, baseline_error)
    continue_recovery = (
        gain_vs_state_free >= _MINIMUM_RELATIVE_GAIN and gain_vs_baseline >= _MINIMUM_RELATIVE_GAIN
    )
    report = {
        "schema_version": 1,
        "status": "development_discrimination_complete",
        "design_commitment_sha256": _file_sha256(design_path),
        "selected_experiment": _experiment_record(selected),
        "observed_summary": observed_vector.tolist(),
        "observed_summary_sha256": _array_hash(observed_vector),
        "candidate_prediction_hashes": {
            name: _array_hash(value) for name, value in sorted(candidate_predictions.items())
        },
        "candidate_rmse": candidate_errors,
        "memory_relative_gain_vs_state_free": gain_vs_state_free,
        "memory_relative_gain_vs_baseline": gain_vs_baseline,
        "minimum_required_gain": _MINIMUM_RELATIVE_GAIN,
        "decision": (
            "continue_multi_case_memory_recovery"
            if continue_recovery
            else "stop_llm_recovered_z_route"
        ),
        "claim_boundary": (
            "One locally selected development intervention; no mechanism identity, novelty, "
            "or confirmatory error guarantee."
        ),
    }
    (output_dir / "result.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def _intervention_pool() -> tuple[LatentGrayScottExperiment, ...]:
    grid_size = 12
    center = grid_size // 2
    schedules = (
        (),
        (LatentPulse(12, center, center, radius=2, delta_v=0.24),),
        (LatentPulse(36, center, center, radius=2, delta_v=0.24),),
        (
            LatentPulse(12, center, center, radius=2, delta_v=0.17),
            LatentPulse(24, center, center, radius=2, delta_v=0.17),
        ),
        (
            LatentPulse(12, center, center, radius=2, delta_v=0.17),
            LatentPulse(42, center, center, radius=2, delta_v=0.17),
        ),
        (LatentPulse(12, center, center, radius=3, delta_v=0.12),),
    )
    items = []
    index = 0
    for initial_family in ("center_square", "two_spots", "stripe"):
        for boundary in ("periodic", "reflecting"):
            for feed, kill in ((0.020, 0.052), (0.035, 0.060), (0.046, 0.064)):
                for pulses in schedules:
                    items.append(
                        LatentGrayScottExperiment(
                            f"design-{index:03d}",
                            feed=feed,
                            kill=kill,
                            initial_family=initial_family,
                            initial_seed=940000,
                            grid_size=grid_size,
                            steps=60,
                            sample_every=12,
                            boundary=boundary,
                            pulses=pulses,
                            measurement=MeasurementSpec(sample_every=12),
                        )
                    )
                    index += 1
    return tuple(items)


def _positive_world(config: dict[str, Any]) -> LatentGrayScottWorld:
    cluster = config["truth_clusters"][0]
    return LatentGrayScottWorld(
        int(config["measurement_seed_base"]),
        LatentLaw(
            latent_drive=float(cluster["latent_drive"]),
            latent_decay=float(cluster["latent_decay"]),
            latent_feedback=float(cluster["latent_feedback"]),
        ),
    )


def _experiment_record(experiment: LatentGrayScottExperiment) -> dict[str, Any]:
    raw = asdict(experiment)
    raw.pop("measurement")
    return raw


def _relative_gain(candidate_error: float, reference_error: float) -> float:
    if reference_error <= 0:
        return float("-inf")
    return (reference_error - candidate_error) / reference_error


def _rmse(predicted: NDArray[np.float64], observed: NDArray[np.float64]) -> float:
    difference = predicted - observed
    return float(np.sqrt(np.mean(difference * difference)))


def _array_hash(value: NDArray[np.float64]) -> str:
    contiguous = np.ascontiguousarray(value, dtype="<f8")
    return hashlib.sha256(contiguous.tobytes()).hexdigest()
