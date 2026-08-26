from pathlib import Path

import pytest

from scientific_parallax.core.reproducibility import ExperimentIdentity, RunManifest


def test_experiment_identity_is_stable_and_config_sensitive() -> None:
    first = ExperimentIdentity("p", {"b": 2, "a": 1}, 7, "abc")
    reordered = ExperimentIdentity("p", {"a": 1, "b": 2}, 7, "abc")
    changed = ExperimentIdentity("p", {"a": 1, "b": 3}, 7, "abc")
    assert first.experiment_id == reordered.experiment_id
    assert first.experiment_id != changed.experiment_id


def test_manifest_is_verified_and_never_overwritten(tmp_path: Path) -> None:
    manifest = RunManifest(1, "id", "p", "hash", 7, {}, {}, {"value": 2})
    path = tmp_path / "manifest.json"
    manifest.write_once(path)
    assert RunManifest.read_verified(path) == manifest
    with pytest.raises(FileExistsError):
        manifest.write_once(path)


def test_manifest_detects_edit(tmp_path: Path) -> None:
    manifest = RunManifest(1, "id", "p", "hash", 7, {}, {}, {"value": 2})
    path = tmp_path / "manifest.json"
    manifest.write_once(path)
    text = path.read_text(encoding="utf-8").replace('"value": 2', '"value": 3')
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        RunManifest.read_verified(path)
