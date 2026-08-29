"""Validation of the candidate execution environment used before Protocol Freeze."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from typing import Any


def load_environment_spec(path: Path, project_root: Path) -> dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != 1:
        raise ValueError("unsupported execution environment schema")
    lock_path = project_root / spec["dependency_lock"]
    digest = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    if digest != spec.get("dependency_lock_sha256"):
        raise ValueError("execution environment dependency lock checksum differs")
    return spec


def runtime_matches(spec: dict[str, Any]) -> dict[str, bool]:
    return {
        "python": platform.python_version() == spec["python"],
        "operating_system": (
            f"{platform.system()} {platform.release()}" == spec["operating_system"]
        ),
        "architecture": platform.machine() == spec["architecture"],
        "runner_image_pinned": bool(spec.get("container_image_digest")),
    }
