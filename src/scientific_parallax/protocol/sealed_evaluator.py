"""One-shot evaluator boundary for final data held outside the development tree."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scientific_parallax.core.reproducibility import content_hash
from scientific_parallax.protocol.final_world import verify_local_final_world


class ExternalSealedEvaluator:
    """Open a pre-committed external world once and leave an external access record."""

    def __init__(
        self,
        *,
        sealed_root: Path,
        development_root: Path,
        protocol_hash: str,
        strategy_hash: str,
        evaluate: Callable[[Path], dict[str, Any]],
    ) -> None:
        self.sealed_root = sealed_root.resolve()
        development_root = development_root.resolve()
        self._development_root = development_root
        inside_development = (
            self.sealed_root == development_root
            or self.sealed_root.is_relative_to(development_root)
        )
        if inside_development:
            raise ValueError("sealed evaluator root must be outside the development tree")
        if not self.sealed_root.is_dir():
            raise FileNotFoundError(self.sealed_root)
        self._protocol_hash = protocol_hash
        self._strategy_hash = strategy_hash
        self._evaluate = evaluate

    def evaluate_once(self) -> dict[str, Any]:
        commitment_path = self.sealed_root / "commitment.json"
        commitment = json.loads(commitment_path.read_text(encoding="utf-8"))
        if commitment.get("schema_version") != 2:
            raise ValueError("unsupported sealed-world commitment schema")
        if commitment.get("protocol_hash") != self._protocol_hash:
            raise PermissionError("sealed-world commitment does not match the frozen protocol")
        if not commitment.get("world_hash"):
            raise ValueError("sealed-world commitment requires a world hash")
        verify_local_final_world(
            sealed_root=self.sealed_root,
            expected_protocol_hash=self._protocol_hash,
            development_root=self._development_root,
        )

        commitment_hash = content_hash(commitment)
        strategy_freeze_path = self.sealed_root / "strategy-freeze.json"
        strategy_freeze = json.loads(strategy_freeze_path.read_text(encoding="utf-8"))
        if strategy_freeze.get("schema_version") != 1:
            raise ValueError("unsupported strategy-freeze schema")
        if strategy_freeze.get("protocol_hash") != self._protocol_hash:
            raise PermissionError("strategy freeze does not match the frozen protocol")
        if strategy_freeze.get("strategy_hash") != self._strategy_hash:
            raise PermissionError("strategy freeze does not match the evaluated strategy")
        if strategy_freeze.get("world_commitment_hash") != commitment_hash:
            raise PermissionError("strategy freeze does not match the sealed world commitment")

        access_path = self.sealed_root / "access-log.json"
        access = {
            "schema_version": 1,
            "opened_at_utc": datetime.now(UTC).isoformat(),
            "protocol_hash": self._protocol_hash,
            "strategy_hash": self._strategy_hash,
            "commitment_hash": commitment_hash,
            "strategy_freeze_hash": content_hash(strategy_freeze),
        }
        with access_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(access, indent=2, sort_keys=True) + "\n")

        result = self._evaluate(self.sealed_root)
        result_record = {
            "schema_version": 1,
            "result": result,
            "result_hash": content_hash(result),
        }
        with (self.sealed_root / "result.json").open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result_record, indent=2, sort_keys=True) + "\n")
        return result
