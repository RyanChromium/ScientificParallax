import json
from pathlib import Path

import pytest

from scientific_parallax.core.reproducibility import content_hash
from scientific_parallax.protocol.sealed_evaluator import ExternalSealedEvaluator


def _commit(root: Path, protocol_hash: str = "protocol", strategy_hash: str = "strategy") -> None:
    root.mkdir()
    commitment = {
        "schema_version": 2,
        "protocol_hash": protocol_hash,
        "world_hash": "world",
    }
    (root / "commitment.json").write_text(json.dumps(commitment), encoding="utf-8")
    (root / "strategy-freeze.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "protocol_hash": protocol_hash,
                "strategy_hash": strategy_hash,
                "world_commitment_hash": content_hash(commitment),
            }
        ),
        encoding="utf-8",
    )


def test_sealed_evaluator_requires_external_root_and_opens_once(tmp_path: Path) -> None:
    development = tmp_path / "development"
    development.mkdir()
    external = tmp_path / "external"
    _commit(external)
    evaluator = ExternalSealedEvaluator(
        sealed_root=external,
        development_root=development,
        protocol_hash="protocol",
        strategy_hash="strategy",
        evaluate=lambda root: {"score": 1.0, "root": root.name},
    )
    assert evaluator.evaluate_once()["score"] == 1.0
    assert (external / "access-log.json").exists()
    assert (external / "result.json").exists()
    with pytest.raises(FileExistsError):
        evaluator.evaluate_once()


def test_sealed_evaluator_rejects_development_subdirectory(tmp_path: Path) -> None:
    development = tmp_path / "development"
    development.mkdir()
    sealed = development / "sealed"
    _commit(sealed)
    with pytest.raises(ValueError, match="outside"):
        ExternalSealedEvaluator(
            sealed_root=sealed,
            development_root=development,
            protocol_hash="protocol",
            strategy_hash="strategy",
            evaluate=lambda root: {},
        )


def test_world_can_be_committed_before_strategy_is_frozen(tmp_path: Path) -> None:
    development = tmp_path / "development"
    development.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    commitment = {
        "schema_version": 2,
        "protocol_hash": "protocol",
        "world_hash": "world",
    }
    (external / "commitment.json").write_text(json.dumps(commitment), encoding="utf-8")
    evaluator = ExternalSealedEvaluator(
        sealed_root=external,
        development_root=development,
        protocol_hash="protocol",
        strategy_hash="strategy",
        evaluate=lambda root: {"root": root.name},
    )
    with pytest.raises(FileNotFoundError):
        evaluator.evaluate_once()

    (external / "strategy-freeze.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "protocol_hash": "protocol",
                "strategy_hash": "strategy",
                "world_commitment_hash": content_hash(commitment),
            }
        ),
        encoding="utf-8",
    )
    assert evaluator.evaluate_once() == {"root": "external"}


def test_strategy_freeze_detects_commitment_changes(tmp_path: Path) -> None:
    development = tmp_path / "development"
    development.mkdir()
    external = tmp_path / "external"
    _commit(external)
    (external / "commitment.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "protocol_hash": "protocol",
                "world_hash": "changed-after-strategy-freeze",
            }
        ),
        encoding="utf-8",
    )
    evaluator = ExternalSealedEvaluator(
        sealed_root=external,
        development_root=development,
        protocol_hash="protocol",
        strategy_hash="strategy",
        evaluate=lambda root: {},
    )
    with pytest.raises(PermissionError, match="sealed world commitment"):
        evaluator.evaluate_once()
