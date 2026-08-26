import pytest

from scientific_parallax.protocol.dry_run import protocol_spec_from_config
from scientific_parallax.protocol.evidence_layers import (
    CandidateEvidenceState,
    EvidenceRecord,
    EvidenceStore,
    EvidenceTier,
    ProtocolGate,
    SurvivalPolicy,
    SurvivalStatus,
    calibrate_noise,
)


def _config() -> dict[str, object]:
    return {
        "protocol_id": "test",
        "primary_endpoint": "endpoint",
        "ranking_threshold_k": 2,
        "persistence_checkpoints": 3,
        "minimum_relative_effect": 0.2,
        "world_query_budget": 10,
        "candidate_generation_budget": 2,
        "candidate_evaluation_budget": 4,
        "cpu_hour_budget": 1,
    }


def test_final_evidence_is_blocked_until_freeze_and_single_use() -> None:
    gate = ProtocolGate(lambda strategy: {"strategy": strategy})
    with pytest.raises(PermissionError):
        gate.final_evaluate_once("v1")
    gate.freeze(protocol_spec_from_config(_config()), "v1")
    with pytest.raises(PermissionError, match="differs"):
        gate.final_evaluate_once("v2")
    assert gate.final_evaluate_once("v1") == {"strategy": "v1"}
    with pytest.raises(RuntimeError, match="already"):
        gate.final_evaluate_once("v1")


def test_store_never_accepts_final_evidence() -> None:
    store = EvidenceStore()
    store.append(EvidenceRecord(EvidenceTier.TRAINING, "q", "o"))
    assert len(store.records(EvidenceTier.TRAINING)) == 1
    with pytest.raises(ValueError, match="sealed"):
        store.append(EvidenceRecord(EvidenceTier.FINAL_SEALED, "q", "o"))
    with pytest.raises(PermissionError):
        store.records(EvidenceTier.FINAL_SEALED)


def test_calibration_and_survival_rules_are_executable() -> None:
    assert calibrate_noise([0.0, 0.1, -0.1], floor=0.01) > 0.01
    policy = SurvivalPolicy(dormancy_after=2, death_after=4)
    assert policy.classify(CandidateEvidenceState("a", 0)) == SurvivalStatus.ACTIVE
    assert policy.classify(CandidateEvidenceState("a", 2)) == SurvivalStatus.DORMANT
    assert policy.classify(CandidateEvidenceState("a", 4)) == SurvivalStatus.DEAD
    assert policy.classify(CandidateEvidenceState("a", 0, 1)) == SurvivalStatus.DEAD
