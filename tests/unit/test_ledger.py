import json
from pathlib import Path

import pytest

from scientific_parallax.step0.ledger import EvidenceLedger, verify_ledger


def _complete_ledger(path: Path) -> None:
    ledger = EvidenceLedger(path)
    prediction_hash = ledger.preregister({"prediction": 1.0})
    ledger.record_observation({"observation": 1.1}, prediction_hash)


def test_complete_ledger_verifies(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    _complete_ledger(path)
    verify_ledger(path)


def test_ledger_refuses_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    _complete_ledger(path)
    with pytest.raises(FileExistsError):
        EvidenceLedger(path)


def test_tampered_ledger_fails_verification(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    _complete_ledger(path)
    events = path.read_text(encoding="utf-8").splitlines()
    event = json.loads(events[0])
    event["payload"]["prediction"] = 999.0
    events[0] = json.dumps(event, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(events) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="modified"):
        verify_ledger(path)
