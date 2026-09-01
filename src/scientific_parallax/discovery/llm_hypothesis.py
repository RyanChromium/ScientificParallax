"""Blind, auditable hypothesis proposals for the development Gray--Scott screen.

The trusted side of this module creates anonymous evidence from a synthetic
development world.  An external language model receives only that evidence and
the public two-field baseline.  It returns equations in a deliberately small
AST language; no model-generated Python is executed.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from scientific_parallax.worlds.gray_scott import (
    MeasurementSpec,
    _initial_state,
    _laplacian_periodic,
    _laplacian_reflecting,
)
from scientific_parallax.worlds.latent_gray_scott import (
    LatentGrayScottExperiment,
    LatentGrayScottWorld,
    LatentLaw,
    LatentPulse,
)

_FEATURE_NAMES = ("mean", "standard_deviation", "high_fraction", "gradient_energy")
_PUBLIC_FIELDS = ("u", "v")
_FIXED_NAMES = frozenset({"feed", "kill", "reaction_scale"})
_MAX_AUXILIARY_STATES = 2
_MAX_PARAMETERS = 8
_MAX_EXPRESSION_NODES = 80
_HYPOTHESIS_COUNT = 3


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    name: str
    lower: float
    upper: float
    initial: float


@dataclass(frozen=True, slots=True)
class StateSpec:
    name: str
    initial: float


@dataclass(frozen=True, slots=True)
class HypothesisSpec:
    hypothesis_id: str
    summary: str
    additional_states: tuple[StateSpec, ...]
    parameters: tuple[ParameterSpec, ...]
    rhs: dict[str, str]
    falsification_test: str

    @property
    def state_names(self) -> tuple[str, ...]:
        return _PUBLIC_FIELDS + tuple(item.name for item in self.additional_states)


@dataclass(frozen=True, slots=True)
class CompiledHypothesis:
    spec: HypothesisSpec
    expressions: dict[str, ast.Expression]


def prepare_blind_screen(
    config_path: Path,
    output_dir: Path,
    *,
    source_world: str = "positive",
) -> dict[str, Any]:
    """Write a prompt packet without exposing the generator or held-out conditions."""

    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite blind-screen output: {output_dir}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_development_config(config)
    _validate_source_world(source_world)
    training, _, positive_world = _screen_cases(config)
    world = _select_source_world(config, positive_world, source_world)
    baseline_scale = _fit_two_field_scale(world, training)
    evidence = _evidence_payload(world, training, baseline_scale)
    schema = response_json_schema()
    prompt = _proposal_prompt(evidence, baseline_scale)
    packet = {
        "schema_version": 1,
        "scope": "anonymous_development_screen",
        "case_id": _content_hash(evidence)[:16],
        "baseline_fit": {"reaction_scale": baseline_scale},
        "evidence": evidence,
        "prompt": prompt,
        "response_schema": schema,
        "assurance": {
            "generator_source_in_prompt": False,
            "held_out_conditions_in_prompt": False,
            "candidate_code_execution": False,
        },
    }
    _assert_blind_packet(packet, config)
    output_dir.mkdir(parents=True)
    (output_dir / "request.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    (output_dir / "response-schema.json").write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = {
        "status": "blind_prompt_ready",
        "source_world": source_world,
        "case_id": packet["case_id"],
        "training_condition_count": len(training),
        "baseline_reaction_scale": baseline_scale,
        "request_sha256": _file_sha256(output_dir / "request.json"),
        "next_step": "obtain one schema-valid response without repository access",
    }
    (output_dir / "prepare-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def evaluate_blind_response(
    config_path: Path,
    request_path: Path,
    response_path: Path,
    output_path: Path,
    *,
    parameter_draws: int = 64,
    source_world: str = "positive",
) -> dict[str, Any]:
    """Fit proposed equations on prompt data and score untouched development conditions."""

    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite blind-screen report: {output_path}")
    if parameter_draws < 1 or parameter_draws > 2048:
        raise ValueError("parameter_draws must lie between 1 and 2048")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_development_config(config)
    _validate_source_world(source_world)
    packet = json.loads(request_path.read_text(encoding="utf-8"))
    _assert_blind_packet(packet, config)
    hypotheses = parse_hypothesis_response(json.loads(response_path.read_text(encoding="utf-8")))
    training, held_out, positive_world = _screen_cases(config)
    elicitation_scale = float(packet["baseline_fit"]["reaction_scale"])
    source = _select_source_world(config, positive_world, source_world)
    expected_evidence = _evidence_payload(source, training, elicitation_scale)
    if packet.get("case_id") != _content_hash(expected_evidence)[:16]:
        raise ValueError("request packet does not match the configured development case")

    null_world = LatentGrayScottWorld(
        measurement_seed=int(config["measurement_seed_base"]) + 8000,
        law=LatentLaw(False, False, False),
    )
    positive_baseline_scale = _fit_two_field_scale(positive_world, training)
    null_baseline_scale = _fit_two_field_scale(null_world, training)
    rng_seed = int(hashlib.sha256(packet["case_id"].encode()).hexdigest()[:16], 16)
    rows = []
    for index, hypothesis in enumerate(hypotheses):
        compiled = compile_hypothesis(hypothesis)
        parameters, training_rmse = _fit_hypothesis(
            compiled,
            positive_world,
            training,
            parameter_draws,
            rng_seed + index,
            positive_baseline_scale,
        )
        null_parameters, null_training_rmse = _fit_hypothesis(
            compiled,
            null_world,
            training,
            parameter_draws,
            rng_seed + 1000 + index,
            null_baseline_scale,
        )
        positive_rmse = _hypothesis_rmse(
            compiled, parameters, positive_world, held_out, positive_baseline_scale
        )
        null_rmse = _hypothesis_rmse(
            compiled,
            null_parameters,
            null_world,
            held_out,
            null_baseline_scale,
        )
        rows.append(
            {
                "hypothesis_id": hypothesis.hypothesis_id,
                "summary": hypothesis.summary,
                "additional_state_count": len(hypothesis.additional_states),
                "parameter_count": len(hypothesis.parameters),
                "positive_fit_parameters": parameters,
                "positive_training_rmse": training_rmse,
                "held_out_positive_rmse": positive_rmse,
                "null_fit_parameters": null_parameters,
                "null_training_rmse": null_training_rmse,
                "held_out_null_rmse": null_rmse,
                "falsification_test": hypothesis.falsification_test,
            }
        )

    baseline = compile_hypothesis(_baseline_hypothesis(positive_baseline_scale))
    null_baseline = compile_hypothesis(_baseline_hypothesis(null_baseline_scale))
    baseline_positive = _hypothesis_rmse(
        baseline, {}, positive_world, held_out, positive_baseline_scale
    )
    baseline_null = _hypothesis_rmse(null_baseline, {}, null_world, held_out, null_baseline_scale)
    report = {
        "schema_version": 1,
        "status": "blind_response_screened",
        "scope": "development_only_not_confirmatory",
        "elicitation_world": source_world,
        "case_id": packet["case_id"],
        "request_sha256": _file_sha256(request_path),
        "response_sha256": _file_sha256(response_path),
        "config_sha256": _file_sha256(config_path),
        "implementation_sha256": _file_sha256(Path(__file__)),
        "parameter_draws_per_hypothesis": parameter_draws,
        "baseline": {
            "positive_parameters": {"reaction_scale": positive_baseline_scale},
            "null_parameters": {"reaction_scale": null_baseline_scale},
            "held_out_positive_rmse": baseline_positive,
            "held_out_null_rmse": baseline_null,
        },
        "hypotheses": rows,
        "interpretation_boundary": _interpretation_boundary(source_world),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def response_json_schema() -> dict[str, Any]:
    state = {
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "initial"],
        "properties": {
            "name": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,15}$"},
            "initial": {"type": "number", "minimum": -1.5, "maximum": 1.5},
        },
    }
    parameter = {
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "lower", "upper", "initial"],
        "properties": {
            "name": {"type": "string", "pattern": "^p[0-9]+$"},
            "lower": {"type": "number", "minimum": -10.0, "maximum": 10.0},
            "upper": {"type": "number", "minimum": -10.0, "maximum": 10.0},
            "initial": {"type": "number", "minimum": -10.0, "maximum": 10.0},
        },
    }
    hypothesis = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "hypothesis_id",
            "summary",
            "additional_states",
            "parameters",
            "rhs",
            "falsification_test",
        ],
        "properties": {
            "hypothesis_id": {"type": "string", "pattern": "^[a-z][a-z0-9-]{0,39}$"},
            "summary": {"type": "string", "minLength": 1, "maxLength": 240},
            "additional_states": {
                "type": "array",
                "maxItems": _MAX_AUXILIARY_STATES,
                "items": state,
            },
            "parameters": {
                "type": "array",
                "maxItems": _MAX_PARAMETERS,
                "items": parameter,
            },
            "rhs": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2 + _MAX_AUXILIARY_STATES,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["state", "expression"],
                    "properties": {
                        "state": {
                            "type": "string",
                            "pattern": "^[a-z][a-z0-9_]{0,15}$",
                        },
                        "expression": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 500,
                        },
                    },
                },
            },
            "falsification_test": {"type": "string", "minLength": 1, "maxLength": 300},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "hypotheses"],
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "hypotheses": {
                "type": "array",
                "minItems": _HYPOTHESIS_COUNT,
                "maxItems": _HYPOTHESIS_COUNT,
                "items": hypothesis,
            },
        },
    }


def parse_hypothesis_response(raw: dict[str, Any]) -> tuple[HypothesisSpec, ...]:
    if raw.get("schema_version") != 1 or set(raw) != {"schema_version", "hypotheses"}:
        raise ValueError("response must contain schema_version 1 and hypotheses only")
    items = raw["hypotheses"]
    if not isinstance(items, list) or len(items) != _HYPOTHESIS_COUNT:
        raise ValueError(f"response must contain exactly {_HYPOTHESIS_COUNT} hypotheses")
    parsed = tuple(_parse_hypothesis(item) for item in items)
    identifiers = [item.hypothesis_id for item in parsed]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("hypothesis identifiers must be unique")
    if all(item.additional_states for item in parsed):
        raise ValueError("at least one competing hypothesis must use no additional state")
    return parsed


def compile_hypothesis(spec: HypothesisSpec) -> CompiledHypothesis:
    allowed_names = set(spec.state_names) | _FIXED_NAMES | {item.name for item in spec.parameters}
    state_names = set(spec.state_names)
    expressions = {}
    for state_name, source in spec.rhs.items():
        parsed = ast.parse(source, mode="eval")
        _validate_expression(parsed, allowed_names, state_names)
        expressions[state_name] = parsed
    return CompiledHypothesis(spec, expressions)


def simulate_hypothesis(
    compiled: CompiledHypothesis,
    parameters: dict[str, float],
    experiment: LatentGrayScottExperiment,
    reaction_scale: float = 1.0,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    expected = {item.name for item in compiled.spec.parameters}
    if set(parameters) != expected:
        raise ValueError("parameter values do not match the hypothesis declaration")
    u, v = _initial_state(experiment.grid_size, experiment.initial_family, experiment.initial_seed)
    states: dict[str, NDArray[np.float64]] = {"u": u, "v": v}
    for item in compiled.spec.additional_states:
        states[item.name] = np.full_like(u, item.initial)
    laplacian = _laplacian_periodic if experiment.boundary == "periodic" else _laplacian_reflecting
    pulse_by_step = {item.at_step: item for item in experiment.pulses}
    samples: list[NDArray[np.float64]] = []
    times: list[float] = []
    constants = {
        "feed": experiment.feed,
        "kill": experiment.kill,
        "reaction_scale": reaction_scale,
        **parameters,
    }
    for step in range(1, experiment.steps + 1):
        if pulse := pulse_by_step.get(step):
            _apply_pulse(states["v"], pulse)
        updates = {
            name: _evaluate_expression(expression.body, states, constants, laplacian)
            for name, expression in compiled.expressions.items()
        }
        for name, derivative in updates.items():
            candidate = states[name] + np.asarray(derivative, dtype=float)
            if candidate.shape != states[name].shape or not np.all(np.isfinite(candidate)):
                raise ValueError(f"hypothesis produced invalid state values for {name}")
            states[name] = np.clip(candidate, -1.5, 1.5)
        if step % experiment.sample_every == 0 or step == experiment.steps:
            samples.append(np.stack((states["u"].copy(), states["v"].copy())))
            times.append(float(step))
    return np.asarray(times), np.stack(samples)


def _proposal_prompt(evidence: dict[str, Any], baseline_scale: float) -> str:
    evidence_text = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    paragraphs = (
        "You are proposing falsifiable dynamical explanations for an anonymous two-field system.",
        "You may use only the evidence below. Do not inspect files, use tools, retrieve "
        "background material, or assume a particular omitted mechanism. The current "
        "public model is:",
        "du = 0.16*lap(u) - reaction_scale*u*v**2 + feed*(1-u)\n"
        "dv = 0.08*lap(v) + reaction_scale*u*v**2 - (feed+kill)*v\n"
        f"where reaction_scale = {baseline_scale:.17g} is a fixed public baseline constant.",
        "Propose exactly three mutually competing revisions. At least one revision must "
        "retain exactly two state fields. A revision may introduce up to two additional "
        "state fields, but extra fields are not preferred. Use only +, -, *, /, ** with "
        "numeric powers no larger than 4, names, and lap(state). Every right-hand side "
        "must be a complete derivative for u, v, and every added state. The fixed names "
        "feed, kill, and reaction_scale may be reused. Tunable parameters must be named "
        "p0, p1, ...; each lower value must be smaller than upper, and initial must lie "
        "between them. Prefer the fewest states and parameters that address a specific "
        "residual pattern. State one intervention that could falsify each proposal. "
        "Return JSON only, matching the supplied schema.",
        f"ANONYMOUS_EVIDENCE={evidence_text}",
    )
    return "\n\n".join(paragraphs)


def _screen_cases(
    config: dict[str, Any],
) -> tuple[
    tuple[LatentGrayScottExperiment, ...],
    tuple[LatentGrayScottExperiment, ...],
    LatentGrayScottWorld,
]:
    cluster = config["truth_clusters"][0]
    law = LatentLaw(
        latent_drive=float(cluster["latent_drive"]),
        latent_decay=float(cluster["latent_decay"]),
        latent_feedback=float(cluster["latent_feedback"]),
    )
    grid_size = int(config["grid_size"])
    steps = int(config["steps"])
    sample_every = int(config["sample_every"])
    seed = int(config["task_seed_base"])
    center = grid_size // 2
    measurement = MeasurementSpec(sample_every=sample_every, noise_std=0.004)
    training = (
        LatentGrayScottExperiment(
            "screen-train-0",
            initial_seed=seed,
            grid_size=grid_size,
            steps=steps,
            sample_every=sample_every,
            measurement=measurement,
        ),
        LatentGrayScottExperiment(
            "screen-train-1",
            initial_seed=seed,
            grid_size=grid_size,
            steps=steps,
            sample_every=sample_every,
            pulses=(LatentPulse(max(2, steps // 4), center, center, delta_v=0.24),),
            measurement=measurement,
        ),
        LatentGrayScottExperiment(
            "screen-train-2",
            feed=0.025,
            kill=0.054,
            initial_family="stripe",
            initial_seed=seed,
            grid_size=grid_size,
            steps=steps,
            sample_every=sample_every,
            boundary="reflecting",
            measurement=measurement,
        ),
    )
    held_out = (
        LatentGrayScottExperiment(
            "screen-test-0",
            feed=0.031,
            kill=0.059,
            initial_family="two_spots",
            initial_seed=seed + 10000,
            grid_size=grid_size,
            steps=steps + 8,
            sample_every=sample_every,
            pulses=(LatentPulse(steps * 2 // 3, center, center, delta_v=0.30),),
            measurement=measurement,
        ),
        LatentGrayScottExperiment(
            "screen-test-1",
            feed=0.020,
            kill=0.052,
            initial_seed=seed + 20000,
            grid_size=grid_size,
            steps=steps + 8,
            sample_every=sample_every,
            boundary="reflecting",
            pulses=(
                LatentPulse(max(2, steps // 5), center - 2, center, delta_v=0.20),
                LatentPulse(steps * 3 // 5, center + 2, center, delta_v=0.20),
            ),
            measurement=measurement,
        ),
    )
    world = LatentGrayScottWorld(int(config["measurement_seed_base"]), law)
    return training, held_out, world


def _validate_source_world(source_world: str) -> None:
    if source_world not in {"positive", "null"}:
        raise ValueError("source_world must be 'positive' or 'null'")


def _select_source_world(
    config: dict[str, Any],
    positive_world: LatentGrayScottWorld,
    source_world: str,
) -> LatentGrayScottWorld:
    if source_world == "positive":
        return positive_world
    return LatentGrayScottWorld(
        measurement_seed=int(config["measurement_seed_base"]) + 8000,
        law=LatentLaw(False, False, False),
    )


def _interpretation_boundary(source_world: str) -> str:
    if source_world == "null":
        return (
            "This is one development null elicitation. Proposing an extra state is not itself "
            "a false attribution because the response contains competing models. Only frozen "
            "held-out comparisons may raise the protocol warning. One case cannot estimate a "
            "false-attribution rate or establish model-wide behavior."
        )
    return (
        "This screen evaluates executable proposals from one anonymous synthetic case. The "
        "null transfer refits each proposed structure and is not a false-discovery experiment. "
        "This screen cannot establish a unique physical state, scientific novelty, or "
        "superiority."
    )


def _fit_two_field_scale(
    world: LatentGrayScottWorld, experiments: tuple[LatentGrayScottExperiment, ...]
) -> float:
    observed = [_observation_vector(world, item) for item in experiments]
    best: tuple[float, float] | None = None
    for scale in np.linspace(0.4, 1.6, 25):
        law = LatentLaw(False, False, False, reaction_scale=float(scale))
        candidate = LatentGrayScottWorld(0, law)
        predicted = [_observation_vector(candidate, item, noiseless=True) for item in experiments]
        error = _rmse_vectors(predicted, observed)
        score = (error, float(scale))
        if best is None or score < best:
            best = score
    assert best is not None
    return best[1]


def _evidence_payload(
    world: LatentGrayScottWorld,
    experiments: tuple[LatentGrayScottExperiment, ...],
    baseline_scale: float,
) -> dict[str, Any]:
    baseline = LatentGrayScottWorld(
        0, LatentLaw(False, False, False, reaction_scale=baseline_scale)
    )
    conditions = []
    for index, experiment in enumerate(experiments):
        observed = world.observe(experiment)
        noiseless = _without_measurement_noise(experiment)
        predicted = baseline.observe(noiseless)
        observed_frames = _summary_frames(observed.times, observed.fields)
        predicted_frames = _summary_frames(predicted.times, predicted.fields)
        residual_frames = _subtract_frames(observed_frames, predicted_frames)
        conditions.append(
            {
                "condition_id": f"condition-{index}",
                "feed": experiment.feed,
                "kill": experiment.kill,
                "initial_pattern": experiment.initial_family,
                "boundary": experiment.boundary,
                "duration_steps": experiment.steps,
                "sample_every": experiment.sample_every,
                "pulses": [
                    {
                        "at_step": pulse.at_step,
                        "radius": pulse.radius,
                        "delta_v": pulse.delta_v,
                    }
                    for pulse in experiment.pulses
                ],
                "observed": observed_frames,
                "baseline_prediction": predicted_frames,
                "residual_observed_minus_baseline": residual_frames,
            }
        )
    return {
        "field_names": list(_PUBLIC_FIELDS),
        "feature_names": list(_FEATURE_NAMES),
        "baseline_family": "two_field_reaction_diffusion",
        "conditions": conditions,
    }


def _parse_hypothesis(raw: Any) -> HypothesisSpec:
    if not isinstance(raw, dict):
        raise ValueError("each hypothesis must be an object")
    required = {
        "hypothesis_id",
        "summary",
        "additional_states",
        "parameters",
        "rhs",
        "falsification_test",
    }
    if set(raw) != required:
        raise ValueError("hypothesis fields do not match the response schema")
    identifier = _short_text(raw["hypothesis_id"], "hypothesis_id", 40)
    if not identifier[0].isalpha() or any(
        not (char.islower() or char.isdigit() or char == "-") for char in identifier
    ):
        raise ValueError("invalid hypothesis identifier")
    states_raw = raw["additional_states"]
    parameters_raw = raw["parameters"]
    if not isinstance(states_raw, list) or len(states_raw) > _MAX_AUXILIARY_STATES:
        raise ValueError("too many additional states")
    if not isinstance(parameters_raw, list) or len(parameters_raw) > _MAX_PARAMETERS:
        raise ValueError("too many parameters")
    states = tuple(_parse_state(item) for item in states_raw)
    parameters = tuple(_parse_parameter(item) for item in parameters_raw)
    state_names = _PUBLIC_FIELDS + tuple(item.name for item in states)
    if len(state_names) != len(set(state_names)):
        raise ValueError("state names must be unique")
    parameter_names = [item.name for item in parameters]
    if len(parameter_names) != len(set(parameter_names)):
        raise ValueError("parameter names must be unique")
    if set(state_names) & set(parameter_names):
        raise ValueError("state and parameter names must be disjoint")
    rhs_items = raw["rhs"]
    if not isinstance(rhs_items, list):
        raise ValueError("rhs must be an array of state/expression objects")
    rhs: dict[str, str] = {}
    for item in rhs_items:
        if not isinstance(item, dict) or set(item) != {"state", "expression"}:
            raise ValueError("invalid rhs entry")
        name = _symbol(item["state"])
        if name in rhs:
            raise ValueError("rhs state names must be unique")
        rhs[name] = _short_text(item["expression"], f"rhs.{name}", 500)
    if set(rhs) != set(state_names):
        raise ValueError("rhs must define every state and no unknown state")
    spec = HypothesisSpec(
        identifier,
        _short_text(raw["summary"], "summary", 240),
        states,
        parameters,
        rhs,
        _short_text(raw["falsification_test"], "falsification_test", 300),
    )
    compile_hypothesis(spec)
    return spec


def _parse_state(raw: Any) -> StateSpec:
    if not isinstance(raw, dict) or set(raw) != {"name", "initial"}:
        raise ValueError("invalid additional state")
    name = _symbol(raw["name"])
    initial = _finite_number(raw["initial"], "state initial")
    if not -1.5 <= initial <= 1.5:
        raise ValueError("state initial lies outside [-1.5, 1.5]")
    return StateSpec(name, initial)


def _parse_parameter(raw: Any) -> ParameterSpec:
    if not isinstance(raw, dict) or set(raw) != {"name", "lower", "upper", "initial"}:
        raise ValueError("invalid parameter")
    name = _symbol(raw["name"])
    if not name.startswith("p") or not name[1:].isdigit():
        raise ValueError("parameters must be named p0, p1, ...")
    lower = _finite_number(raw["lower"], "parameter lower")
    upper = _finite_number(raw["upper"], "parameter upper")
    initial = _finite_number(raw["initial"], "parameter initial")
    if not -10 <= lower < upper <= 10 or not lower <= initial <= upper:
        raise ValueError("invalid parameter bounds or initial value")
    return ParameterSpec(name, lower, upper, initial)


def _validate_expression(
    expression: ast.Expression, allowed_names: set[str], state_names: set[str]
) -> None:
    nodes = list(ast.walk(expression))
    if len(nodes) > _MAX_EXPRESSION_NODES:
        raise ValueError("right-hand side expression is too complex")
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Call,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.UAdd,
        ast.USub,
    )
    if any(not isinstance(node, allowed_nodes) for node in nodes):
        raise ValueError("right-hand side uses an unsupported syntax node")
    for node in nodes:
        if isinstance(node, ast.Name) and node.id not in allowed_names and node.id != "lap":
            raise ValueError(f"right-hand side uses unknown name: {node.id}")
        if isinstance(node, ast.Call) and (
            not isinstance(node.func, ast.Name)
            or node.func.id != "lap"
            or len(node.args) != 1
            or node.keywords
            or not isinstance(node.args[0], ast.Name)
            or node.args[0].id not in state_names
        ):
            raise ValueError("only lap(state) calls are allowed")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            exponent = node.right
            if (
                not isinstance(exponent, ast.Constant)
                or isinstance(exponent.value, bool)
                or not isinstance(exponent.value, (int, float))
            ):
                raise ValueError("powers must use numeric literal exponents")
            if not 0 <= float(exponent.value) <= 4:
                raise ValueError("power exponent lies outside [0, 4]")
        if isinstance(node, ast.Constant) and (
            isinstance(node.value, bool)
            or not isinstance(node.value, (int, float))
            or not math.isfinite(float(node.value))
        ):
            raise ValueError("constants must be finite numbers")


def _evaluate_expression(
    node: ast.AST,
    states: dict[str, NDArray[np.float64]],
    constants: dict[str, float],
    laplacian: Any,
) -> NDArray[np.float64] | float:
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return states[node.id] if node.id in states else constants[node.id]
    if isinstance(node, ast.UnaryOp):
        value = _evaluate_expression(node.operand, states, constants, laplacian)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left = _evaluate_expression(node.left, states, constants, laplacian)
        right = _evaluate_expression(node.right, states, constants, laplacian)
        with np.errstate(all="ignore"):
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                return left**right
    if isinstance(node, ast.Call):
        assert isinstance(node.args[0], ast.Name)
        return laplacian(states[node.args[0].id], "five_point")
    raise AssertionError(f"unexpected validated AST node: {type(node).__name__}")


def _fit_hypothesis(
    compiled: CompiledHypothesis,
    world: LatentGrayScottWorld,
    experiments: tuple[LatentGrayScottExperiment, ...],
    draws: int,
    seed: int,
    reaction_scale: float,
) -> tuple[dict[str, float], float]:
    observed = [_observation_vector(world, item) for item in experiments]
    specs = compiled.spec.parameters
    initial = {item.name: item.initial for item in specs}
    candidates = [initial]
    if specs:
        for item in specs:
            for value in (item.lower, item.upper):
                if len(candidates) < draws:
                    candidates.append(initial | {item.name: value})
        rng = np.random.default_rng(seed)
        for _ in range(max(0, draws - len(candidates))):
            candidates.append(
                {item.name: float(rng.uniform(item.lower, item.upper)) for item in specs}
            )
    best: tuple[float, tuple[tuple[str, float], ...]] | None = None
    best_parameters: dict[str, float] | None = None
    for parameters in candidates:
        try:
            predicted = [
                _simulated_vector(compiled, parameters, item, reaction_scale)
                for item in experiments
            ]
            error = _rmse_vectors(predicted, observed)
        except (FloatingPointError, OverflowError, ValueError):
            continue
        score = (error, tuple(sorted(parameters.items())))
        if best is None or score < best:
            best = score
            best_parameters = parameters
    if best is None or best_parameters is None:
        raise ValueError(f"no finite parameter draw for {compiled.spec.hypothesis_id}")
    return best_parameters, best[0]


def _hypothesis_rmse(
    compiled: CompiledHypothesis,
    parameters: dict[str, float],
    world: LatentGrayScottWorld,
    experiments: tuple[LatentGrayScottExperiment, ...],
    reaction_scale: float,
) -> float:
    predicted = [
        _simulated_vector(compiled, parameters, item, reaction_scale) for item in experiments
    ]
    observed = [_observation_vector(world, item) for item in experiments]
    return _rmse_vectors(predicted, observed)


def _baseline_hypothesis(scale: float) -> HypothesisSpec:
    return HypothesisSpec(
        "two-field-baseline",
        "Public two-field reaction-diffusion model",
        (),
        (),
        {
            "u": f"0.16*lap(u)-{scale:.17g}*u*v**2+feed*(1-u)",
            "v": f"0.08*lap(v)+{scale:.17g}*u*v**2-(feed+kill)*v",
        },
        "Reference model only",
    )


def _simulated_vector(
    compiled: CompiledHypothesis,
    parameters: dict[str, float],
    experiment: LatentGrayScottExperiment,
    reaction_scale: float,
) -> NDArray[np.float64]:
    times, fields = simulate_hypothesis(
        compiled,
        parameters,
        _without_measurement_noise(experiment),
        reaction_scale,
    )
    named = {"field_0": fields[:, 0], "field_1": fields[:, 1]}
    frames = _summary_frames(times, named)
    return _frames_vector(frames)


def _observation_vector(
    world: LatentGrayScottWorld,
    experiment: LatentGrayScottExperiment,
    *,
    noiseless: bool = False,
) -> NDArray[np.float64]:
    observation = world.observe(_without_measurement_noise(experiment) if noiseless else experiment)
    return _frames_vector(_summary_frames(observation.times, observation.fields))


def _summary_frames(
    times: NDArray[np.float64], fields: dict[str, NDArray[np.float64]]
) -> dict[str, list[dict[str, float]]]:
    result = {}
    for public_name, source_name in zip(_PUBLIC_FIELDS, sorted(fields), strict=True):
        frames = []
        for time, frame in zip(times, fields[source_name], strict=True):
            finite = frame[np.isfinite(frame)]
            mean = float(np.mean(finite))
            standard_deviation = float(np.std(finite))
            filled = np.nan_to_num(frame, nan=mean)
            gy, gx = np.gradient(filled)
            frames.append(
                {
                    "time": float(time),
                    "mean": mean,
                    "standard_deviation": standard_deviation,
                    "high_fraction": float(np.mean(finite > mean + standard_deviation)),
                    "gradient_energy": float(np.mean(gx * gx + gy * gy)),
                }
            )
        result[public_name] = frames
    return result


def _subtract_frames(
    observed: dict[str, list[dict[str, float]]],
    predicted: dict[str, list[dict[str, float]]],
) -> dict[str, list[dict[str, float]]]:
    result = {}
    for name in _PUBLIC_FIELDS:
        result[name] = []
        for actual, expected in zip(observed[name], predicted[name], strict=True):
            result[name].append(
                {
                    "time": actual["time"],
                    **{feature: actual[feature] - expected[feature] for feature in _FEATURE_NAMES},
                }
            )
    return result


def _frames_vector(frames: dict[str, list[dict[str, float]]]) -> NDArray[np.float64]:
    return np.asarray(
        [
            frame[feature]
            for name in _PUBLIC_FIELDS
            for frame in frames[name]
            for feature in _FEATURE_NAMES
        ],
        dtype=float,
    )


def _rmse_vectors(
    predicted: list[NDArray[np.float64]], observed: list[NDArray[np.float64]]
) -> float:
    difference = np.concatenate(predicted) - np.concatenate(observed)
    return float(np.sqrt(np.mean(difference * difference)))


def _without_measurement_noise(
    experiment: LatentGrayScottExperiment,
) -> LatentGrayScottExperiment:
    raw = asdict(experiment)
    raw["measurement"] = MeasurementSpec(
        sample_every=experiment.measurement.sample_every,
        downsample=experiment.measurement.downsample,
        mixing=experiment.measurement.mixing,
        visible_channels=experiment.measurement.visible_channels,
        noise_std=0.0,
        mask_fraction=0.0,
    )
    raw["pulses"] = tuple(LatentPulse(**item) for item in raw["pulses"])
    return LatentGrayScottExperiment(**raw)


def _apply_pulse(field: NDArray[np.float64], pulse: LatentPulse) -> None:
    yy, xx = np.ogrid[: field.shape[0], : field.shape[1]]
    mask = (yy - pulse.center_y) ** 2 + (xx - pulse.center_x) ** 2 <= pulse.radius**2
    field[mask] += pulse.delta_v
    np.clip(field, -1.5, 1.5, out=field)


def _assert_blind_packet(packet: dict[str, Any], config: dict[str, Any]) -> None:
    expected_keys = {
        "schema_version",
        "scope",
        "case_id",
        "baseline_fit",
        "evidence",
        "prompt",
        "response_schema",
        "assurance",
    }
    if set(packet) != expected_keys:
        raise ValueError("blind-screen request fields do not match the packet schema")
    if packet.get("schema_version") != 1 or packet.get("scope") != "anonymous_development_screen":
        raise ValueError("invalid blind-screen request packet")
    baseline_fit = packet.get("baseline_fit")
    if not isinstance(baseline_fit, dict) or set(baseline_fit) != {"reaction_scale"}:
        raise ValueError("invalid blind-screen baseline fit")
    baseline_scale = _finite_number(baseline_fit["reaction_scale"], "baseline reaction scale")
    evidence = packet.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("invalid blind-screen evidence")
    if packet.get("case_id") != _content_hash(evidence)[:16]:
        raise ValueError("blind-screen case identifier does not bind the evidence")
    if packet.get("prompt") != _proposal_prompt(evidence, baseline_scale):
        raise ValueError("blind-screen prompt does not bind the evidence")
    if packet.get("response_schema") != response_json_schema():
        raise ValueError("blind-screen response schema is not the supported schema")
    if packet.get("assurance") != {
        "generator_source_in_prompt": False,
        "held_out_conditions_in_prompt": False,
        "candidate_code_execution": False,
    }:
        raise ValueError("invalid blind-screen assurance record")
    serialized = json.dumps(packet, sort_keys=True).lower()
    forbidden = ("latent", "truth_cluster", "nominal-memory", "slow-memory", "fast-memory")
    if any(marker in serialized for marker in forbidden):
        raise ValueError("blind-screen request leaks a generator identifier")
    for key in ("latent_drive", "latent_decay", "latent_feedback"):
        if key in serialized:
            raise ValueError("blind-screen request leaks a generator parameter name")


def _validate_development_config(config: dict[str, Any]) -> None:
    if config.get("scope") != "development_pilot_only":
        raise ValueError("LLM hypothesis screening is restricted to development configurations")
    if not config.get("truth_clusters"):
        raise ValueError("development configuration has no synthetic cases")


def _short_text(value: Any, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be a non-empty string of at most {maximum} characters")
    return value.strip()


def _symbol(value: Any) -> str:
    name = _short_text(value, "symbol", 16)
    if not name[0].isalpha() or any(
        not (char.islower() or char.isdigit() or char == "_") for char in name
    ):
        raise ValueError("invalid symbol name")
    if name in _FIXED_NAMES or name == "lap":
        raise ValueError("reserved symbol name")
    return name


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _content_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
