import hashlib
import json
from pathlib import Path

import pytest

from scientific_parallax.core.environment_spec import load_environment_spec


def test_environment_spec_verifies_lock_bytes(tmp_path: Path) -> None:
    lock = tmp_path / "lock"
    lock.write_text("pinned", encoding="utf-8")
    spec = tmp_path / "environment.json"
    spec.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dependency_lock": "lock",
                "dependency_lock_sha256": hashlib.sha256(b"pinned").hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    assert load_environment_spec(spec, tmp_path)["dependency_lock"] == "lock"


def test_environment_spec_rejects_changed_lock(tmp_path: Path) -> None:
    lock = tmp_path / "lock"
    lock.write_text("changed", encoding="utf-8")
    spec = tmp_path / "environment.json"
    spec.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dependency_lock": "lock",
                "dependency_lock_sha256": "0" * 64,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="checksum"):
        load_environment_spec(spec, tmp_path)


def test_confirmatory_environment_pins_container_and_requirements() -> None:
    spec = load_environment_spec(Path("configs/environments/confirmatory-v1.json"), Path.cwd())
    assert spec["base_image_digest"].startswith("sha256:")
    assert spec["container_image_digest"].startswith("sha256:")
    assert spec["container_image_digest"] != spec["base_image_digest"]
    assert spec["frozen_mix_profiled_in_published_runner"] is True
    assert set(spec["container_platforms"]) == {"linux/amd64", "linux/arm64"}
    assert spec["requirements_sha256"]
