"""Load and validate the repository's experiment registry."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class ExperimentRegistryError(ValueError):
    """Raised when the experiment registry is incomplete or inconsistent."""


REQUIRED_LINK_GROUPS = ("plans", "docs", "configs", "artifacts", "code", "tests")
REQUIRED_TEXT_FIELDS = (
    "id",
    "slug",
    "family",
    "title_zh",
    "title_en",
    "stage",
    "status",
    "decision",
    "question_zh",
    "question_en",
    "result_zh",
    "result_en",
    "claim_boundary_zh",
    "claim_boundary_en",
)


def _require_relative_existing_path(repo_root: Path, value: str, context: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ExperimentRegistryError(f"{context} must be a repository-relative path: {value}")
    resolved = (repo_root / path).resolve()
    if not resolved.is_relative_to(repo_root.resolve()):
        raise ExperimentRegistryError(f"{context} escapes the repository: {value}")
    if not resolved.exists():
        raise ExperimentRegistryError(f"{context} does not exist: {value}")


def load_experiment_registry(path: Path, *, check_paths: bool = True) -> dict[str, Any]:
    """Return a validated registry loaded from *path*."""

    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExperimentRegistryError(f"cannot read experiment registry {path}: {exc}") from exc

    if registry.get("schema_version") != 1:
        raise ExperimentRegistryError("experiment registry schema_version must be 1")
    vocabulary = registry.get("status_vocabulary")
    if not isinstance(vocabulary, dict) or not vocabulary:
        raise ExperimentRegistryError("status_vocabulary must be a non-empty object")
    experiments = registry.get("experiments")
    if not isinstance(experiments, list) or not experiments:
        raise ExperimentRegistryError("experiments must be a non-empty list")

    repo_root = path.resolve().parent.parent
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()
    seen_sequences: set[int] = set()

    for index, experiment in enumerate(experiments):
        context = f"experiments[{index}]"
        if not isinstance(experiment, dict):
            raise ExperimentRegistryError(f"{context} must be an object")
        for field in REQUIRED_TEXT_FIELDS:
            value = experiment.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ExperimentRegistryError(f"{context}.{field} must be a non-empty string")

        experiment_id = experiment["id"]
        slug = experiment["slug"]
        sequence = experiment.get("sequence")
        if experiment_id in seen_ids:
            raise ExperimentRegistryError(f"duplicate experiment id: {experiment_id}")
        if slug in seen_slugs:
            raise ExperimentRegistryError(f"duplicate experiment slug: {slug}")
        if not isinstance(sequence, int) or sequence < 1:
            raise ExperimentRegistryError(f"{context}.sequence must be a positive integer")
        expected_id = f"EXP-{sequence:02d}"
        if not re.fullmatch(r"EXP-\d{2}", experiment_id) or experiment_id != expected_id:
            raise ExperimentRegistryError(
                f"{context}.id must match its sequence using the form {expected_id}"
            )
        if sequence in seen_sequences:
            raise ExperimentRegistryError(f"duplicate experiment sequence: {sequence}")
        if experiment["status"] not in vocabulary:
            raise ExperimentRegistryError(
                f"{context}.status is not declared in status_vocabulary: {experiment['status']}"
            )

        links = experiment.get("links")
        if not isinstance(links, dict):
            raise ExperimentRegistryError(f"{context}.links must be an object")
        overview = links.get("overview")
        if not isinstance(overview, str) or not overview:
            raise ExperimentRegistryError(f"{context}.links.overview must be a path")
        if check_paths:
            _require_relative_existing_path(repo_root, overview, f"{context}.links.overview")

        for group in REQUIRED_LINK_GROUPS:
            values = links.get(group)
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ExperimentRegistryError(f"{context}.links.{group} must be a list of paths")
            if len(values) != len(set(values)):
                raise ExperimentRegistryError(f"{context}.links.{group} contains duplicate paths")
            if check_paths:
                for value in values:
                    _require_relative_existing_path(repo_root, value, f"{context}.links.{group}")

        seen_ids.add(experiment_id)
        seen_slugs.add(slug)
        seen_sequences.add(sequence)

    ordered_sequences = [experiment["sequence"] for experiment in experiments]
    if ordered_sequences != sorted(ordered_sequences):
        raise ExperimentRegistryError("experiments must be ordered by sequence")
    return registry


def find_experiment(registry: dict[str, Any], identifier: str) -> dict[str, Any]:
    """Find an experiment by case-insensitive ID or slug."""

    normalized = identifier.casefold()
    for experiment in registry["experiments"]:
        if normalized in {experiment["id"].casefold(), experiment["slug"].casefold()}:
            return experiment
    raise ExperimentRegistryError(f"unknown experiment: {identifier}")


def format_experiment_list(registry: dict[str, Any], *, language: str = "zh") -> str:
    """Format a compact terminal list of registered experiments."""

    title_key = "title_zh" if language == "zh" else "title_en"
    header = "ID      STATUS                TITLE"
    rows = [
        f"{item['id']:<7} {item['status']:<21} {item[title_key]}"
        for item in registry["experiments"]
    ]
    return "\n".join([header, *rows])


def format_experiment_detail(experiment: dict[str, Any], *, language: str = "zh") -> str:
    """Format one experiment for terminal inspection."""

    if language == "zh":
        labels = ("问题", "结果", "边界")
        title = experiment["title_zh"]
        fields = ("question_zh", "result_zh", "claim_boundary_zh")
    else:
        labels = ("Question", "Result", "Claim boundary")
        title = experiment["title_en"]
        fields = ("question_en", "result_en", "claim_boundary_en")
    return "\n".join(
        (
            f"{experiment['id']} · {title}",
            f"status: {experiment['status']}",
            f"decision: {experiment['decision']}",
            f"{labels[0]}: {experiment[fields[0]]}",
            f"{labels[1]}: {experiment[fields[1]]}",
            f"{labels[2]}: {experiment[fields[2]]}",
            f"overview: {experiment['links']['overview']}",
        )
    )
