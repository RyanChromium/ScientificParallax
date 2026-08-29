import json
from pathlib import Path

import pytest

from scientific_parallax.protocol.sealed_evaluator import ExternalSealedEvaluator


def _commit(root: Path, protocol_hash: str = "protocol", strategy_hash: str = "strategy") -> None:
    root.mkdir()
    (root / "commitment.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "protocol_hash": protocol_hash,
                "strategy_hash": strategy_hash,
                "world_hash": "world",
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
