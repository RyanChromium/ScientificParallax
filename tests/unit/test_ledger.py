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


def test_interrupted_ledger_resumes_pending_observation(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    prediction_hash = EvidenceLedger(path).preregister({"prediction": 1.0})

    resumed = EvidenceLedger.resume(path)
    assert resumed.pending_prediction_hash == prediction_hash
    resumed.record_observation({"observation": 1.1}, prediction_hash)
    verify_ledger(path)


def test_complete_ledger_resumes_with_contiguous_chain(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    _complete_ledger(path)

    resumed = EvidenceLedger.resume(path)
    prediction_hash = resumed.preregister({"prediction": 2.0})
    resumed.record_observation({"observation": 2.1}, prediction_hash)
    verify_ledger(path)
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [event["event_index"] for event in events] == [0, 1, 2, 3]
