"""Append-only, hash-chained evidence ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class EvidenceLedger:
    """Writes preregistrations before observations and makes tampering detectable."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise FileExistsError(f"refusing to overwrite ledger: {self.path}")
        self._previous_hash = "0" * 64
        self._pending_prediction_hash: str | None = None
        self._next_index = 0

    @classmethod
    def resume(cls, path: Path) -> EvidenceLedger:
        """Continue a valid ledger, including one interrupted after preregistration."""
        if not path.exists():
            raise FileNotFoundError(path)
        state = _inspect_ledger(path, allow_pending=True)
        ledger = cls.__new__(cls)
        ledger.path = path
        ledger._previous_hash = state.previous_hash
        ledger._pending_prediction_hash = state.pending_prediction_hash
        ledger._next_index = state.event_count
        return ledger

    @property
    def pending_prediction_hash(self) -> str | None:
        return self._pending_prediction_hash

    def append(self, event_type: str, payload: dict[str, Any]) -> str:
        body = {
            "schema_version": 1,
            "event_index": self._next_index,
            "event_type": event_type,
            "payload": payload,
            "previous_hash": self._previous_hash,
        }
        event_hash = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
        event = {**body, "event_hash": event_hash}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(canonical_json(event) + "\n")
            stream.flush()
        self._previous_hash = event_hash
        self._next_index += 1
        return event_hash

    def preregister(self, payload: dict[str, Any]) -> str:
        if self._pending_prediction_hash is not None:
            raise RuntimeError("an observation is still pending for the previous preregistration")
        event_hash = self.append("prediction_preregistered", payload)
        self._pending_prediction_hash = event_hash
        return event_hash

    def record_observation(self, payload: dict[str, Any], prediction_hash: str) -> str:
        if prediction_hash != self._pending_prediction_hash:
            raise RuntimeError("observation does not match the pending preregistration")
        event_hash = self.append(
            "observation_received",
            {**payload, "prediction_event_hash": prediction_hash},
        )
        self._pending_prediction_hash = None
        return event_hash


class _LedgerState:
    def __init__(
        self,
        event_count: int,
        previous_hash: str,
        pending_prediction_hash: str | None,
    ) -> None:
        self.event_count = event_count
        self.previous_hash = previous_hash
        self.pending_prediction_hash = pending_prediction_hash


def _inspect_ledger(path: Path, *, allow_pending: bool) -> _LedgerState:
    previous_hash = "0" * 64
    pending_prediction_hash: str | None = None
    event_count = 0
    with path.open(encoding="utf-8") as stream:
        for expected_index, line in enumerate(stream):
            event = json.loads(line)
            event_hash = event.pop("event_hash")
            schema_version = event.get("schema_version", 1)
            if schema_version != 1:
                raise ValueError(f"unsupported ledger event schema: {schema_version}")
            if event["event_index"] != expected_index:
                raise ValueError("ledger event index is not contiguous")
            if event["previous_hash"] != previous_hash:
                raise ValueError("ledger hash chain is broken")
            calculated = hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()
            if calculated != event_hash:
                raise ValueError("ledger event content was modified")
            if event["event_type"] == "prediction_preregistered":
                if pending_prediction_hash is not None:
                    raise ValueError("multiple predictions precede an observation")
                pending_prediction_hash = event_hash
            elif event["event_type"] == "observation_received":
                if event["payload"].get("prediction_event_hash") != pending_prediction_hash:
                    raise ValueError("observation does not reference its prediction")
                pending_prediction_hash = None
            previous_hash = event_hash
            event_count = expected_index + 1
    if pending_prediction_hash is not None and not allow_pending:
        raise ValueError("ledger ends with an unobserved preregistration")
    return _LedgerState(event_count, previous_hash, pending_prediction_hash)


def verify_ledger(path: Path) -> None:
    _inspect_ledger(path, allow_pending=False)
