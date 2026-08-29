"""Local single-account sealed evaluation for Protocol v2 latent discovery."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from scientific_parallax.core.reproducibility import capture_environment, content_hash
from scientific_parallax.discovery.latent_questions import seed_questions, validation_questions
from scientific_parallax.discovery.latent_runner import (
    ARM_POLICIES,
    _arm_summaries,
    _capability_analysis,
    _checks,
    _comparative_analysis,
    _confirmatory_decision,
    _failure_modes,
    _LatentTask,
    _mechanism_analysis,
    _run_task,
    _sum_budgets,
    _validate_config,
)
from scientific_parallax.worlds.latent_gray_scott import LatentLaw


def provision_latent_final_world(
    *, config_path: Path, output_root: Path, development_root: Path
) -> dict[str, Any]:
    root = _external_root(output_root, development_root)
    if root.exists():
        raise FileExistsError(f"refusing to overwrite latent final world: {root}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_confirmatory_config(config)
    design = config["final_world_design"]
    secret = secrets.token_bytes(design["secret_bytes"])
    root.mkdir(parents=True)
    entries: list[dict[str, Any]] = []
    task_number = 0
    for cluster_index, cluster in enumerate(config["truth_clusters"]):
        for seed_index in range(config["seeds_per_truth_cluster"]):
            payload = _task_payload(
                config,
                secret,
                "latent",
                cluster["cluster_id"],
                cluster_index,
                seed_index,
                {
                    "latent_drive": cluster["latent_drive"],
                    "latent_decay": cluster["latent_decay"],
                    "latent_feedback": cluster["latent_feedback"],
                },
            )
            entries.append(_write_task(root, task_number, payload))
            task_number += 1
    for seed_index in range(config["null_control_seeds"]):
        payload = _task_payload(
            config,
            secret,
            "null",
            "no-latent-control",
            9000,
            seed_index,
            {
                "has_latent_state": False,
                "observed_drive_connected": False,
                "reaction_feedback_connected": False,
            },
        )
        entries.append(_write_task(root, task_number, payload))
        task_number += 1
    manifest = {
        "schema_version": 1,
        "experiment_version": config["experiment_version"],
        "config_hash": content_hash(config),
        "generator_version": design["generator_version"],
        "task_count": task_number,
        "files": entries,
    }
    commitment = {
        "schema_version": 1,
        "experiment_version": config["experiment_version"],
        "config_hash": content_hash(config),
        "assurance_mode": config["assurance_mode"],
        "world_hash": content_hash(manifest),
        "task_count": task_number,
    }
    _write_json_once(root / "manifest.json", manifest)
    _write_json_once(root / "commitment.json", commitment)
    return {
        "schema_version": 1,
        "experiment_version": config["experiment_version"],
        "config_hash": content_hash(config),
        "world_hash": commitment["world_hash"],
        "commitment_hash": content_hash(commitment),
        "task_count": task_number,
        "assurance_mode": config["assurance_mode"],
        "task_contents_returned": False,
    }


def freeze_latent_strategy(
    *, config_path: Path, sealed_root: Path, development_root: Path
) -> dict[str, Any]:
    root = _external_root(sealed_root, development_root)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_confirmatory_config(config)
    commitment = json.loads((root / "commitment.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if commitment["config_hash"] != content_hash(config):
        raise PermissionError("latent-world commitment differs from confirmatory config")
    if commitment["world_hash"] != content_hash(manifest):
        raise PermissionError("latent-world manifest differs from commitment")
    environment = capture_environment(development_root)
    if environment["git_dirty"] or not environment["git_revision"]:
        raise RuntimeError("strategy freeze requires a clean committed worktree")
    strategy = _strategy_identity(
        config_path, config, development_root, environment["git_revision"]
    )
    record = {
        "schema_version": 1,
        "experiment_version": config["experiment_version"],
        "config_hash": content_hash(config),
        "world_commitment_hash": content_hash(commitment),
        **strategy,
    }
    _write_json_once(root / "strategy-freeze.json", record)
    return {
        "schema_version": 1,
        "strategy_hash": record["strategy_hash"],
        "strategy_freeze_hash": content_hash(record),
        "code_revision": record["code_revision"],
        "world_commitment_hash": record["world_commitment_hash"],
    }


def evaluate_latent_final_world_once(
    *, config_path: Path, sealed_root: Path, development_root: Path
) -> dict[str, Any]:
    root = _external_root(sealed_root, development_root)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_confirmatory_config(config)
    commitment = json.loads((root / "commitment.json").read_text(encoding="utf-8"))
    freeze = json.loads((root / "strategy-freeze.json").read_text(encoding="utf-8"))
    if commitment["config_hash"] != content_hash(config):
        raise PermissionError("latent final world differs from confirmatory config")
    if freeze["world_commitment_hash"] != content_hash(commitment):
        raise PermissionError("strategy freeze differs from latent final world")
    expected = _strategy_identity(config_path, config, development_root, freeze["code_revision"])
    if freeze["strategy_hash"] != expected["strategy_hash"]:
        raise PermissionError("current strategy bytes differ from the frozen strategy")
    environment = capture_environment(development_root)
    if environment["git_dirty"] or environment["git_revision"] != freeze["code_revision"]:
        raise PermissionError("confirmatory execution requires the frozen clean revision")
    access = {
        "schema_version": 1,
        "opened_at_utc": datetime.now(UTC).isoformat(),
        "experiment_version": config["experiment_version"],
        "strategy_hash": freeze["strategy_hash"],
        "strategy_freeze_hash": content_hash(freeze),
        "world_commitment_hash": content_hash(commitment),
    }
    _write_json_once(root / "access-log.json", access)
    tasks = _load_verified_tasks(root, config)
    results = [
        _run_task(task, arm, ARM_POLICIES[arm], config, arm_index)
        for arm_index, arm in enumerate(config["arms"])
        for task in tasks
        if task.task_kind == "latent" or arm in config["null_control_arms"]
    ]
    capability = _capability_analysis(results, config)
    comparison = _comparative_analysis(results, config)
    mechanism = _mechanism_analysis(results, config)
    summaries = _arm_summaries(results, config)
    checks = _checks(results, tasks, config)
    decision = _confirmatory_decision(capability, comparison, mechanism, checks, config)
    report = {
        "schema_version": 1,
        "status": "latent_discovery_confirmatory_complete" if all(checks.values()) else "invalid",
        "scope": "one-shot sealed Protocol v2 test under local single-account self-audit",
        "experiment_version": config["experiment_version"],
        "config_hash": content_hash(config),
        "world_hash": commitment["world_hash"],
        "strategy_hash": freeze["strategy_hash"],
        "task_count": len(tasks),
        "run_count": len(results),
        "capability_analysis": capability,
        "mechanism_analysis": mechanism,
        "comparative_analysis": comparison,
        "arm_summaries": summaries,
        "decision": decision,
        "checks": checks,
        "resource_accounting": asdict(_sum_budgets(results)),
        "independent_validation_evaluations": sum(
            item["independent_validation_evaluations"] for item in results
        ),
        "failure_modes": _failure_modes(capability, comparison, summaries, config),
        "assurance": (
            "local single-account self-audit; this does not provide independent custody "
            "or independent confirmation"
        ),
    }
    task_results_path = root / "task-results.jsonl"
    with task_results_path.open("x", encoding="utf-8") as stream:
        stream.write("".join(json.dumps(item, sort_keys=True) + "\n" for item in results))
    result_record = {
        "schema_version": 1,
        "report": report,
        "report_hash": content_hash(report),
        "task_results_sha256": _file_sha256(task_results_path),
    }
    _write_json_once(root / "result.json", result_record)
    return report


def _validate_confirmatory_config(config: dict[str, Any]) -> None:
    _validate_config(config)
    if config.get("scope") != "confirmatory_v2":
        raise ValueError("latent final world requires confirmatory_v2 scope")
    if config.get("assurance_mode") != "local_single_account_self_audit":
        raise ValueError("unsupported latent final-world assurance mode")
    if config.get("null_control_seeds", 0) < 30:
        raise ValueError("confirmatory null control requires at least 30 tasks")
    if config.get("null_control_arms") != ["coevolution"]:
        raise ValueError("confirmatory null-world arm set differs from preregistration")
    design = config.get("final_world_design", {})
    if design.get("generator_version") != "sealed-latent-gray-scott-v2":
        raise ValueError("unsupported latent final-world generator")
    if design.get("secret_bytes", 0) < 32:
        raise ValueError("latent final-world secret is too short")
    if design.get("seed_derivation") != "hmac-sha256-v2-cluster-index-purpose":
        raise ValueError("unsupported latent final-world seed derivation")
    if design.get("task_format") != "latent-gray-scott-task-json-v1":
        raise ValueError("unsupported latent final-world task format")


def _task_payload(
    config: dict[str, Any],
    secret: bytes,
    task_kind: str,
    cluster_id: str,
    cluster_index: int,
    seed_index: int,
    law: dict[str, Any],
) -> dict[str, Any]:
    token = hmac.new(
        secret,
        f"token:{task_kind}:{cluster_index}:{seed_index}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return {
        "schema_version": 1,
        "experiment_version": config["experiment_version"],
        "task_token": token,
        "task_kind": task_kind,
        "truth_cluster": cluster_id,
        "seed_index": seed_index,
        "initial_seed": _derived_secret_seed(
            secret, config["experiment_version"], task_kind, cluster_index, seed_index, "initial"
        ),
        "measurement_seed": _derived_secret_seed(
            secret,
            config["experiment_version"],
            task_kind,
            cluster_index,
            seed_index,
            "measurement",
        ),
        "law": law,
    }


def _write_task(root: Path, task_number: int, payload: dict[str, Any]) -> dict[str, Any]:
    relative = f"tasks/{task_number:03d}.json"
    path = root / relative
    _write_json_once(path, payload)
    return {"path": relative, "bytes": path.stat().st_size, "sha256": _file_sha256(path)}


def _load_verified_tasks(root: Path, config: dict[str, Any]) -> tuple[_LatentTask, ...]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    commitment = json.loads((root / "commitment.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or commitment.get("schema_version") != 1:
        raise ValueError("unsupported latent final-world schema")
    if manifest.get("config_hash") != content_hash(config):
        raise ValueError("latent final-world manifest differs from config")
    if content_hash(manifest) != commitment["world_hash"]:
        raise ValueError("latent final-world manifest differs from commitment")
    tasks: list[_LatentTask] = []
    declared: set[str] = set()
    initial_seeds: set[int] = set()
    for entry in manifest["files"]:
        relative = PurePosixPath(entry["path"])
        if relative.is_absolute() or ".." in relative.parts or relative.parts[:1] != ("tasks",):
            raise ValueError("latent final-world path escapes task directory")
        path = root.joinpath(*relative.parts)
        if not path.is_file() or path.is_symlink():
            raise ValueError("latent final-world task must be a regular file")
        if path.stat().st_size != entry["bytes"] or _file_sha256(path) != entry["sha256"]:
            raise ValueError("latent final-world task bytes changed")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            payload.get("schema_version") != 1
            or payload.get("experiment_version") != config["experiment_version"]
        ):
            raise ValueError("latent final-world task identity is invalid")
        if payload["initial_seed"] in initial_seeds:
            raise ValueError("latent final-world initial seeds must be unique")
        initial_seeds.add(payload["initial_seed"])
        declared.add(entry["path"])
        law = LatentLaw(**payload["law"])
        kwargs = {
            "task_token": payload["task_token"],
            "initial_seed": payload["initial_seed"],
            "grid_size": config["grid_size"],
            "steps": config["steps"],
            "sample_every": config["sample_every"],
        }
        tasks.append(
            _LatentTask(
                payload["task_token"],
                payload["task_kind"],
                payload["truth_cluster"],
                payload["seed_index"],
                law,
                payload["measurement_seed"],
                seed_questions(**kwargs),
                validation_questions(**kwargs),
            )
        )
    discovered = {path.relative_to(root).as_posix() for path in (root / "tasks").glob("*.json")}
    if discovered != declared or len(tasks) != manifest["task_count"]:
        raise ValueError("latent final-world task set differs from manifest")
    expected_tasks = (
        len(config["truth_clusters"]) * config["seeds_per_truth_cluster"]
        + config["null_control_seeds"]
    )
    if len(tasks) != expected_tasks or commitment["task_count"] != expected_tasks:
        raise ValueError("latent final-world task count differs from confirmatory design")
    return tuple(tasks)


def _strategy_identity(
    config_path: Path, config: dict[str, Any], development_root: Path, revision: str
) -> dict[str, Any]:
    relative_files = (
        "src/scientific_parallax/discovery/latent_runner.py",
        "src/scientific_parallax/discovery/latent_model.py",
        "src/scientific_parallax/discovery/latent_questions.py",
        "src/scientific_parallax/worlds/latent_gray_scott.py",
    )
    component_hashes = {item: _file_sha256(development_root / item) for item in relative_files}
    payload = {
        "code_revision": revision,
        "config_hash": content_hash(config),
        "entrypoint": "evaluate_latent_final_world_once",
        "component_hashes": component_hashes,
        "config_file_sha256": _file_sha256(config_path),
    }
    return {**payload, "strategy_hash": content_hash(payload)}


def _derived_secret_seed(
    secret: bytes,
    version: str,
    task_kind: str,
    cluster_index: int,
    seed_index: int,
    purpose: str,
) -> int:
    message = "\0".join((version, task_kind, str(cluster_index), str(seed_index), purpose)).encode()
    return int.from_bytes(hmac.new(secret, message, hashlib.sha256).digest()[:8], "big")


def _external_root(root: Path, development_root: Path) -> Path:
    resolved = root.expanduser().resolve()
    development = development_root.expanduser().resolve()
    if resolved == development or resolved.is_relative_to(development):
        raise ValueError("latent final-world root must be outside the development tree")
    return resolved


def _write_json_once(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
