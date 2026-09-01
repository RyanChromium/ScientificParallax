from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scientific_parallax.discovery.llm_discrimination import _intervention_pool
from scientific_parallax.discovery.llm_hypothesis import (
    compile_hypothesis,
    evaluate_blind_response,
    parse_hypothesis_response,
    prepare_blind_screen,
    simulate_hypothesis,
)
from scientific_parallax.worlds.gray_scott import MeasurementSpec
from scientific_parallax.worlds.latent_gray_scott import LatentGrayScottExperiment


def _candidate(
    identifier: str,
    *,
    rhs: list[dict[str, str]],
    states: list[dict[str, float]] | None = None,
    parameters: list[dict[str, float | str]] | None = None,
) -> dict[str, object]:
    return {
        "hypothesis_id": identifier,
        "summary": f"Executable candidate {identifier}",
        "additional_states": states or [],
        "parameters": parameters or [],
        "rhs": rhs,
        "falsification_test": "Use a held-out pulse timing.",
    }


def _response() -> dict[str, object]:
    return {
        "schema_version": 1,
        "hypotheses": [
            _candidate(
                "two-field-scale",
                parameters=[{"name": "p0", "lower": 0.4, "upper": 1.6, "initial": 1.0}],
                rhs=[
                    {
                        "state": "u",
                        "expression": "0.16*lap(u)-p0*u*v**2+feed*(1-u)",
                    },
                    {
                        "state": "v",
                        "expression": "0.08*lap(v)+p0*u*v**2-(feed+kill)*v",
                    },
                ],
            ),
            _candidate(
                "two-field-cubic",
                parameters=[{"name": "p0", "lower": 0.0, "upper": 2.0, "initial": 0.5}],
                rhs=[
                    {
                        "state": "u",
                        "expression": "0.16*lap(u)-reaction_scale*u*v**2-p0*u*v**3+feed*(1-u)",
                    },
                    {
                        "state": "v",
                        "expression": "0.08*lap(v)+reaction_scale*u*v**2+p0*u*v**3-(feed+kill)*v",
                    },
                ],
            ),
            _candidate(
                "one-memory-field",
                states=[{"name": "w", "initial": 0.0}],
                parameters=[
                    {"name": "p0", "lower": 0.01, "upper": 0.2, "initial": 0.08},
                    {"name": "p1", "lower": 0.01, "upper": 0.1, "initial": 0.04},
                    {"name": "p2", "lower": 0.0, "upper": 5.0, "initial": 2.5},
                ],
                rhs=[
                    {
                        "state": "u",
                        "expression": "0.16*lap(u)-(1+p2*w)*u*v**2+feed*(1-u)",
                    },
                    {
                        "state": "v",
                        "expression": "0.08*lap(v)+(1+p2*w)*u*v**2-(feed+kill)*v",
                    },
                    {"state": "w", "expression": "0.035*lap(w)+p0*v-p1*w"},
                ],
            ),
        ],
    }


def test_response_parses_and_compiled_candidate_runs() -> None:
    hypotheses = parse_hypothesis_response(_response())
    compiled = compile_hypothesis(hypotheses[-1])
    experiment = LatentGrayScottExperiment(
        "compiler-test",
        grid_size=8,
        steps=4,
        sample_every=2,
        measurement=MeasurementSpec(sample_every=2),
    )
    parameters = {"p0": 0.08, "p1": 0.04, "p2": 2.5}
    times, fields = simulate_hypothesis(compiled, parameters, experiment, 1.0)
    assert np.array_equal(times, np.asarray([2.0, 4.0]))
    assert fields.shape == (2, 2, 8, 8)
    assert np.all(np.isfinite(fields))


def test_parser_rejects_code_and_forced_extra_states() -> None:
    unsafe = _response()
    unsafe["hypotheses"][0]["rhs"][0]["expression"] = "__import__('os').system('id')"
    with pytest.raises(ValueError, match="unsupported syntax|unknown name"):
        parse_hypothesis_response(unsafe)

    forced = _response()
    memory = forced["hypotheses"][-1]
    forced["hypotheses"] = [
        memory | {"hypothesis_id": "memory-one"},
        memory | {"hypothesis_id": "memory-two"},
        memory | {"hypothesis_id": "memory-three"},
    ]
    with pytest.raises(ValueError, match="no additional state"):
        parse_hypothesis_response(forced)


def test_prepare_packet_is_blind_and_response_can_be_scored(tmp_path: Path) -> None:
    config = Path("configs/experiments/latent-discovery-pilot.json")
    request_dir = tmp_path / "request"
    prepared = prepare_blind_screen(config, request_dir)
    packet_text = (request_dir / "request.json").read_text(encoding="utf-8").lower()
    assert prepared["status"] == "blind_prompt_ready"
    assert "latent" not in packet_text
    assert "screen-test" not in packet_text
    assert "truth_cluster" not in packet_text

    response_path = tmp_path / "response.json"
    response_path.write_text(json.dumps(_response()), encoding="utf-8")
    report_path = tmp_path / "evaluation.json"
    report = evaluate_blind_response(
        config,
        request_dir / "request.json",
        response_path,
        report_path,
        parameter_draws=2,
    )
    assert report["status"] == "blind_response_screened"
    assert len(report["hypotheses"]) == 3
    assert all(np.isfinite(item["held_out_positive_rmse"]) for item in report["hypotheses"])
    assert report_path.exists()


def test_null_packet_is_blind_and_bound_to_its_source_world(tmp_path: Path) -> None:
    config = Path("configs/experiments/latent-discovery-pilot.json")
    positive_dir = tmp_path / "positive"
    null_dir = tmp_path / "null"
    prepare_blind_screen(config, positive_dir)
    prepared = prepare_blind_screen(config, null_dir, source_world="null")
    null_packet = (null_dir / "request.json").read_text(encoding="utf-8").lower()
    assert prepared["source_world"] == "null"
    assert "null" not in null_packet
    assert (
        json.loads((positive_dir / "request.json").read_text())["case_id"]
        != json.loads((null_dir / "request.json").read_text())["case_id"]
    )

    response_path = tmp_path / "response.json"
    response_path.write_text(json.dumps(_response()), encoding="utf-8")
    report = evaluate_blind_response(
        config,
        null_dir / "request.json",
        response_path,
        tmp_path / "null-evaluation.json",
        parameter_draws=2,
        source_world="null",
    )
    assert report["elicitation_world"] == "null"
    with pytest.raises(ValueError, match="does not match"):
        evaluate_blind_response(
            config,
            null_dir / "request.json",
            response_path,
            tmp_path / "wrong-evaluation.json",
            parameter_draws=2,
            source_world="positive",
        )


def test_evaluator_rejects_packet_tampering(tmp_path: Path) -> None:
    config = Path("configs/experiments/latent-discovery-pilot.json")
    request_dir = tmp_path / "request"
    prepare_blind_screen(config, request_dir)
    packet_path = request_dir / "request.json"
    packet = json.loads(packet_path.read_text())
    packet["evidence"]["conditions"][0]["feed"] = 0.999
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    response_path = tmp_path / "response.json"
    response_path.write_text(json.dumps(_response()), encoding="utf-8")
    with pytest.raises(ValueError, match="does not bind"):
        evaluate_blind_response(
            config,
            packet_path,
            response_path,
            tmp_path / "evaluation.json",
            parameter_draws=1,
        )


def test_discrimination_pool_is_the_frozen_candidate_only_design_space() -> None:
    pool = _intervention_pool()
    assert len(pool) == 108
    assert [item.experiment_id for item in pool] == [f"design-{index:03d}" for index in range(108)]
    assert {item.initial_family for item in pool} == {
        "center_square",
        "two_spots",
        "stripe",
    }
    assert {item.boundary for item in pool} == {"periodic", "reflecting"}
    assert {(item.feed, item.kill) for item in pool} == {
        (0.020, 0.052),
        (0.035, 0.060),
        (0.046, 0.064),
    }
    assert {len(item.pulses) for item in pool} == {0, 1, 2}
    assert all(item.grid_size == 12 and item.steps == 60 for item in pool)
