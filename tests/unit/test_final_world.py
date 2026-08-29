import json
from pathlib import Path

import pytest

from scientific_parallax.protocol.final_world import (
    provision_local_final_world,
    verify_local_final_world,
)

CONFIG = Path("configs/experiments/protocol-dry-run.json")


def test_local_final_world_is_write_once_and_verifiable(tmp_path: Path) -> None:
    root = tmp_path / "sealed"
    summary = provision_local_final_world(
        config_path=CONFIG,
        output_root=root,
        development_root=Path.cwd(),
        seed_secret=b"a" * 32,
    )
    assert summary["verified"] is True
    assert summary["assurance_mode"] == "local_single_account_self_audit"
    assert summary["task_count"] == 30
    assert len(list((root / "tasks").glob("*.json"))) == 30
    assert "6161616161" not in (root / "manifest.json").read_text(encoding="utf-8")
    assert (
        verify_local_final_world(
            sealed_root=root,
            expected_protocol_hash=summary["protocol_hash"],
            development_root=Path.cwd(),
        )
        == summary
    )
    with pytest.raises(FileExistsError, match="overwrite"):
        provision_local_final_world(
            config_path=CONFIG,
            output_root=root,
            development_root=Path.cwd(),
        )


def test_local_final_world_detects_task_tampering(tmp_path: Path) -> None:
    root = tmp_path / "sealed"
    summary = provision_local_final_world(
        config_path=CONFIG,
        output_root=root,
        development_root=Path.cwd(),
        seed_secret=b"b" * 32,
    )
    task_path = next((root / "tasks").glob("*.json"))
    task_path.chmod(0o644)
    task = json.loads(task_path.read_text(encoding="utf-8"))
    task["experiment"]["initial_seed"] += 1
    task_path.write_text(json.dumps(task), encoding="utf-8")
    with pytest.raises(ValueError, match="task byte count changed|task hash changed"):
        verify_local_final_world(
            sealed_root=root,
            expected_protocol_hash=summary["protocol_hash"],
            development_root=Path.cwd(),
        )


def test_local_final_world_refuses_development_tree(tmp_path: Path) -> None:
    development = tmp_path / "development"
    development.mkdir()
    with pytest.raises(ValueError, match="outside"):
        provision_local_final_world(
            config_path=CONFIG,
            output_root=development / "sealed",
            development_root=development,
            seed_secret=b"c" * 32,
        )
