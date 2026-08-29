"""Provision and verify a locally self-audited sealed final-world bundle."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from typing import Any

from scientific_parallax.core.reproducibility import content_hash
from scientific_parallax.protocol.design import frozen_candidate_clusters
from scientific_parallax.protocol.dry_run import protocol_spec_from_config, validate_protocol_config
from scientific_parallax.worlds.gray_scott import GrayScottExperiment, GrayScottParameters


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


def _require_external_root(root: Path, development_root: Path) -> tuple[Path, Path]:
    resolved_root = root.expanduser().resolve()
    resolved_development = development_root.expanduser().resolve()
    if resolved_root == resolved_development or resolved_root.is_relative_to(resolved_development):
        raise ValueError("final-world root must be outside the development tree")
    return resolved_root, resolved_development


def _derived_seed(
    secret: bytes,
    protocol_hash: str,
    cluster_id: str,
    task_index: int,
    purpose: str,
) -> int:
    message = "\0".join(
        ("sealed-gray-scott-v1", protocol_hash, cluster_id, str(task_index), purpose)
    ).encode()
    return int.from_bytes(hmac.new(secret, message, hashlib.sha256).digest()[:8], "big")


def provision_local_final_world(
    *,
    config_path: Path,
    output_root: Path,
    development_root: Path,
    seed_secret: bytes | None = None,
) -> dict[str, Any]:
    """Create a write-once final-world bundle without printing hidden task seeds."""

    root, _ = _require_external_root(output_root, development_root)
    if root.exists():
        raise FileExistsError(f"refusing to overwrite final-world root: {root}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_protocol_config(config)
    spec = protocol_spec_from_config(config)
    design = config["final_world_design"]
    secret = seed_secret if seed_secret is not None else secrets.token_bytes(design["secret_bytes"])
    if len(secret) < design["secret_bytes"]:
        raise ValueError("seed secret is shorter than the frozen final-world design")

    root.mkdir(parents=True)
    task_entries: list[dict[str, Any]] = []
    initial_seeds: set[int] = set()
    task_number = 0
    clusters = frozen_candidate_clusters(config["task_design"]["steps"])
    for cluster in clusters:
        for cluster_task_index in range(design["tasks_per_cluster"]):
            initial_seed = _derived_seed(
                secret,
                spec.protocol_hash,
                cluster.cluster_id,
                cluster_task_index,
                "initial-state",
            )
            measurement_seed = _derived_seed(
                secret,
                spec.protocol_hash,
                cluster.cluster_id,
                cluster_task_index,
                "measurement",
            )
            if initial_seed in initial_seeds:
                raise RuntimeError("derived final-world initial seeds are not unique")
            initial_seeds.add(initial_seed)
            experiment = GrayScottExperiment(
                f"final-{cluster.cluster_id}-{cluster_task_index:02d}",
                parameters=GrayScottParameters(feed=cluster.feed, kill=cluster.kill),
                initial_family=cluster.initial_family,
                initial_seed=initial_seed,
                grid_size=config["task_design"]["grid_size"],
                steps=config["task_design"]["steps"],
                boundary=cluster.boundary,
                measurement=cluster.measurement,
            )
            relative_path = f"tasks/{task_number:02d}-{cluster.cluster_id}.json"
            task_path = root / relative_path
            task_payload = {
                "schema_version": 1,
                "protocol_hash": spec.protocol_hash,
                "generator_version": design["generator_version"],
                "cluster_id": cluster.cluster_id,
                "cluster_task_index": cluster_task_index,
                "measurement_seed": measurement_seed,
                "experiment": asdict(experiment),
            }
            _write_json_once(task_path, task_payload)
            task_entries.append(
                {
                    "path": relative_path,
                    "bytes": task_path.stat().st_size,
                    "sha256": _file_sha256(task_path),
                }
            )
            task_number += 1

    manifest = {
        "schema_version": 1,
        "protocol_hash": spec.protocol_hash,
        "generator_version": design["generator_version"],
        "task_format": design["task_format"],
        "task_count": task_number,
        "files": task_entries,
    }
    commitment = {
        "schema_version": 2,
        "protocol_hash": spec.protocol_hash,
        "world_hash": content_hash(manifest),
        "assurance_mode": config["assurance_mode"],
        "generator_version": design["generator_version"],
        "task_count": task_number,
    }
    _write_json_once(root / "manifest.json", manifest)
    _write_json_once(root / "commitment.json", commitment)
    summary = verify_local_final_world(
        sealed_root=root,
        expected_protocol_hash=spec.protocol_hash,
        development_root=development_root,
    )

    for entry in task_entries:
        (root / entry["path"]).chmod(0o444)
    (root / "tasks").chmod(0o555)
    (root / "manifest.json").chmod(0o444)
    (root / "commitment.json").chmod(0o444)
    return summary


def verify_local_final_world(
    *,
    sealed_root: Path,
    expected_protocol_hash: str,
    development_root: Path | None = None,
) -> dict[str, Any]:
    """Verify task bytes and return only non-sensitive bundle identities."""

    root = sealed_root.expanduser().resolve()
    if development_root is not None:
        root, _ = _require_external_root(root, development_root)
    if not root.is_dir():
        raise FileNotFoundError(root)

    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    commitment = json.loads((root / "commitment.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported final-world manifest schema")
    if commitment.get("schema_version") != 2:
        raise ValueError("unsupported sealed-world commitment schema")
    if manifest.get("protocol_hash") != expected_protocol_hash:
        raise PermissionError("final-world manifest does not match the frozen protocol")
    if commitment.get("protocol_hash") != expected_protocol_hash:
        raise PermissionError("sealed-world commitment does not match the frozen protocol")
    if commitment.get("assurance_mode") != "local_single_account_self_audit":
        raise ValueError("sealed-world commitment has the wrong assurance mode")
    if commitment.get("generator_version") != manifest.get("generator_version"):
        raise ValueError("generator identity differs between manifest and commitment")
    if manifest.get("generator_version") != "sealed-gray-scott-v1":
        raise ValueError("unsupported final-world generator")
    tasks_root = root / "tasks"
    if not tasks_root.is_dir() or tasks_root.is_symlink():
        raise ValueError("final-world task directory must be a real directory")

    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("final-world manifest must contain task files")
    declared_paths: set[str] = set()
    initial_seeds: set[int] = set()
    for entry in entries:
        relative_text = entry.get("path")
        if not isinstance(relative_text, str):
            raise ValueError("final-world manifest contains an invalid path")
        relative = PurePosixPath(relative_text)
        if relative.is_absolute() or ".." in relative.parts or relative.parts[:1] != ("tasks",):
            raise ValueError("final-world manifest path escapes the task directory")
        if relative_text in declared_paths:
            raise ValueError("final-world manifest contains a duplicate path")
        declared_paths.add(relative_text)
        task_path = root.joinpath(*relative.parts)
        if not task_path.is_file() or task_path.is_symlink():
            raise FileNotFoundError(task_path)
        claimed_digest = entry.get("sha256")
        if not isinstance(claimed_digest, str) or len(claimed_digest) != 64:
            raise ValueError("final-world manifest contains an invalid task digest")
        if task_path.stat().st_size != entry.get("bytes"):
            raise ValueError(f"final-world task byte count changed: {relative_text}")
        if _file_sha256(task_path) != claimed_digest:
            raise ValueError(f"final-world task hash changed: {relative_text}")
        task = json.loads(task_path.read_text(encoding="utf-8"))
        if task.get("schema_version") != 1 or task.get("protocol_hash") != expected_protocol_hash:
            raise ValueError(f"invalid final-world task identity: {relative_text}")
        if task.get("generator_version") != manifest["generator_version"]:
            raise ValueError(f"invalid final-world task generator: {relative_text}")
        if not isinstance(task.get("cluster_id"), str) or not isinstance(
            task.get("cluster_task_index"), int
        ):
            raise ValueError(f"invalid final-world task coordinates: {relative_text}")
        if not isinstance(task.get("measurement_seed"), int):
            raise ValueError(f"invalid final-world measurement seed: {relative_text}")
        initial_seed = task.get("experiment", {}).get("initial_seed")
        if not isinstance(initial_seed, int) or initial_seed in initial_seeds:
            raise ValueError("final-world tasks require unique integer initial seeds")
        initial_seeds.add(initial_seed)

    discovered_paths = {
        path.relative_to(root).as_posix() for path in tasks_root.glob("**/*") if path.is_file()
    }
    if discovered_paths != declared_paths:
        raise ValueError("final-world task directory differs from the committed manifest")
    if manifest.get("task_count") != len(entries):
        raise ValueError("final-world manifest task count is inconsistent")
    if commitment.get("task_count") != len(entries):
        raise ValueError("sealed-world commitment task count is inconsistent")
    if len(entries) != 30:
        raise ValueError("sealed-gray-scott-v1 requires exactly 30 final-world tasks")
    world_hash = content_hash(manifest)
    if commitment.get("world_hash") != world_hash:
        raise ValueError("sealed-world commitment does not match the final-world manifest")

    return {
        "schema_version": 1,
        "assurance_mode": commitment["assurance_mode"],
        "protocol_hash": expected_protocol_hash,
        "world_hash": world_hash,
        "commitment_hash": content_hash(commitment),
        "task_count": len(entries),
        "verified": True,
    }
