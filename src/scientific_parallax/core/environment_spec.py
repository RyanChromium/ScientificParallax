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
    requirements_path = spec.get("requirements")
    if requirements_path is not None:
        requirements_digest = hashlib.sha256(
            (project_root / requirements_path).read_bytes()
        ).hexdigest()
        if requirements_digest != spec.get("requirements_sha256"):
            raise ValueError("confirmatory requirements checksum differs")
    return spec


def runtime_matches(spec: dict[str, Any]) -> dict[str, bool]:
    current_python = platform.python_version()
    current_system = platform.system()
    current_machine = platform.machine()
    container_architecture = "arm64" if current_machine in {"aarch64", "arm64"} else current_machine
    return {
        "development_host": (
            current_python == spec["python"]
            and f"{current_system} {platform.release()}" == spec["operating_system"]
            and current_machine == spec["architecture"]
        ),
        "confirmatory_container": (
            current_python == spec["python"]
            and current_system == "Linux"
            and f"linux/{container_architecture}" in spec.get("container_platforms", [])
        ),
        "runner_image_pinned": bool(spec.get("container_image_digest")),
    }
