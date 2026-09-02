from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from scientific_parallax.cli import main
from scientific_parallax.core.experiment_registry import (
    ExperimentRegistryError,
    find_experiment,
    format_experiment_list,
    load_experiment_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "experiments" / "registry.json"


def test_repository_experiment_registry_is_complete_and_all_links_exist() -> None:
    registry = load_experiment_registry(REGISTRY_PATH)

    assert [item["id"] for item in registry["experiments"]] == [
        "EXP-01",
        "EXP-02",
        "EXP-03",
        "EXP-04",
        "EXP-05",
        "EXP-06",
        "EXP-07",
    ]
    assert all(item["claim_boundary_zh"] for item in registry["experiments"])


def test_registry_supports_id_slug_and_terminal_listing() -> None:
    registry = load_experiment_registry(REGISTRY_PATH)

    by_id = find_experiment(registry, "exp-07")
    by_slug = find_experiment(registry, "evidence-grounded-direction-v1")

    assert by_id is by_slug
    listing = format_experiment_list(registry, language="en")
    assert "EXP-07" in listing
    assert "Evidence-grounded research-direction pilot v1" in listing


def test_registry_rejects_duplicate_ids(tmp_path: Path) -> None:
    registry = load_experiment_registry(REGISTRY_PATH, check_paths=False)
    registry["experiments"][1]["id"] = registry["experiments"][0]["id"]
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(ExperimentRegistryError, match="duplicate experiment id"):
        load_experiment_registry(path, check_paths=False)


def test_registry_rejects_id_that_does_not_match_sequence(tmp_path: Path) -> None:
    registry = load_experiment_registry(REGISTRY_PATH, check_paths=False)
    registry["experiments"][0]["id"] = "EXP-99"
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(ExperimentRegistryError, match="must match its sequence"):
        load_experiment_registry(path, check_paths=False)


def test_registry_rejects_blank_link(tmp_path: Path) -> None:
    registry = load_experiment_registry(REGISTRY_PATH, check_paths=False)
    registry["experiments"][0]["links"]["docs"] = [""]
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(ExperimentRegistryError, match="must be a list of paths"):
        load_experiment_registry(path, check_paths=False)


def test_experiments_cli_lists_and_validates(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scientific-parallax",
            "experiments",
            "list",
            "--registry",
            str(REGISTRY_PATH),
            "--language",
            "en",
        ],
    )
    main()
    assert "EXP-07" in capsys.readouterr().out

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scientific-parallax",
            "experiments",
            "validate",
            "--registry",
            str(REGISTRY_PATH),
        ],
    )
    main()
    assert "valid registry: 7 experiments" in capsys.readouterr().out
