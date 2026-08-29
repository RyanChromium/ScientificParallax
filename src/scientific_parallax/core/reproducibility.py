"""Stable experiment identity, environment capture, and immutable manifests."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def seed_everything(seed: int) -> np.random.Generator:
    """Seed supported global generators and return an explicit NumPy generator."""
    random.seed(seed)
    np.random.seed(seed)
    return np.random.default_rng(seed)


def _git_output(arguments: list[str], cwd: Path | None) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def capture_environment(repository: Path | None = None) -> dict[str, Any]:
    revision = _git_output(["rev-parse", "HEAD"], repository)
    dirty_output = _git_output(["status", "--porcelain"], repository)
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy": np.__version__,
        "git_revision": revision,
        "git_dirty": bool(dirty_output) if dirty_output is not None else None,
        "process_id": os.getpid(),
    }


@dataclass(frozen=True, slots=True)
class ExperimentIdentity:
    protocol_id: str
    config: dict[str, Any]
    seed: int
    code_revision: str | None

    @property
    def config_hash(self) -> str:
        return content_hash(self.config)

    @property
    def experiment_id(self) -> str:
        payload = {
            "protocol_id": self.protocol_id,
            "config_hash": self.config_hash,
            "seed": self.seed,
            "code_revision": self.code_revision,
        }
        return f"{self.protocol_id}-{content_hash(payload)[:16]}"


@dataclass(frozen=True, slots=True)
class RunManifest:
    schema_version: int
    experiment_id: str
    protocol_id: str
    config_hash: str
    seed: int
    environment: dict[str, Any]
    inputs: dict[str, Any]
    outputs: dict[str, Any]

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported run manifest schema")

    @property
    def manifest_hash(self) -> str:
        return content_hash(asdict(self))

    def write_once(self, path: Path) -> None:
        if path.exists():
            raise FileExistsError(f"refusing to overwrite run manifest: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {**asdict(self), "manifest_hash": self.manifest_hash}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def read_verified(cls, path: Path) -> RunManifest:
        payload = json.loads(path.read_text(encoding="utf-8"))
        claimed_hash = payload.pop("manifest_hash")
        manifest = cls(**payload)
        if manifest.manifest_hash != claimed_hash:
            raise ValueError("run manifest content hash does not match")
        return manifest
