"""Immutable hash-linked scheduler checkpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scientific_parallax.core.reproducibility import canonical_json, content_hash


@dataclass(frozen=True, slots=True)
class LoadedCheckpoint:
    round_index: int
    state: dict[str, Any]
    checkpoint_hash: str


def write_checkpoint(
    directory: Path,
    round_index: int,
    state: dict[str, Any],
    previous_hash: str,
) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"round-{round_index:04d}.json"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite checkpoint: {path}")
    body = {
        "schema_version": 1,
        "round_index": round_index,
        "previous_checkpoint_hash": previous_hash,
        "state": state,
    }
    checkpoint_hash = content_hash(body)
    path.write_text(
        json.dumps({**body, "checkpoint_hash": checkpoint_hash}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return checkpoint_hash


def load_latest_checkpoint(directory: Path) -> LoadedCheckpoint:
    paths = sorted(directory.glob("round-*.json"))
    if not paths:
        raise FileNotFoundError("no scheduler checkpoint is available")
    previous_hash = "0" * 64
    latest: LoadedCheckpoint | None = None
    for expected_index, path in enumerate(paths):
        payload = json.loads(path.read_text(encoding="utf-8"))
        claimed_hash = payload.pop("checkpoint_hash")
        if payload.get("schema_version") != 1 or payload.get("round_index") != expected_index:
            raise ValueError("checkpoint sequence is not contiguous")
        if payload.get("previous_checkpoint_hash") != previous_hash:
            raise ValueError("checkpoint hash chain is broken")
        if content_hash(payload) != claimed_hash:
            raise ValueError("checkpoint content was modified")
        latest = LoadedCheckpoint(expected_index, payload["state"], claimed_hash)
        previous_hash = claimed_hash
    assert latest is not None
    return latest


def canonical_state_bytes(state: dict[str, Any]) -> bytes:
    """Expose the exact canonical checkpoint payload for deterministic tests."""
    return canonical_json(state).encode("utf-8")
