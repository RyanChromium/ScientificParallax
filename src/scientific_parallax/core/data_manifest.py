"""Validation for external dataset provenance and byte-level identities."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"^[0-9a-f]{64}$")


def validate_dataset_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "dataset_id",
        "source",
        "version",
        "license",
        "access_date",
        "shards",
        "supports_novel_conditions",
        "supports_intervention",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        raise ValueError(f"dataset manifest is missing: {', '.join(missing)}")
    if manifest["schema_version"] != 1:
        raise ValueError("unsupported dataset manifest schema")
    if not all(
        isinstance(manifest[key], str) and manifest[key]
        for key in required
        - {
            "schema_version",
            "shards",
            "supports_novel_conditions",
            "supports_intervention",
        }
    ):
        raise ValueError("dataset identity fields must be non-empty strings")
    try:
        date.fromisoformat(manifest["access_date"])
    except (TypeError, ValueError) as error:
        raise ValueError("access_date must be an ISO calendar date") from error
    if not isinstance(manifest["supports_novel_conditions"], bool) or not isinstance(
        manifest["supports_intervention"], bool
    ):
        raise ValueError("dataset capabilities must be boolean")
    shards = manifest["shards"]
    if not isinstance(shards, list) or not shards:
        raise ValueError("dataset manifest must declare at least one shard")
    seen: set[str] = set()
    for shard in shards:
        if not isinstance(shard, dict):
            raise ValueError("each shard must be an object")
        if set(("path", "url", "bytes", "sha256")) - shard.keys():
            raise ValueError("each shard requires path, url, bytes, and sha256")
        if shard["path"] in seen:
            raise ValueError("shard paths must be unique")
        seen.add(shard["path"])
        if not isinstance(shard["bytes"], int) or shard["bytes"] < 1:
            raise ValueError("shard byte counts must be positive integers")
        if not isinstance(shard["sha256"], str) or not SHA256.fullmatch(shard["sha256"]):
            raise ValueError("shard sha256 must be a lowercase hexadecimal digest")


def load_dataset_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_dataset_manifest(manifest)
    return manifest
