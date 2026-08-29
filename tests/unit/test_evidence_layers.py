from copy import deepcopy

import pytest

from scientific_parallax.protocol.dry_run import protocol_spec_from_config, validate_protocol_config
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
        "schema_version": 1,
        "protocol_id": "test",
        "assurance_mode": "local_single_account_self_audit",
        "primary_endpoint": "endpoint",
        "ranking_threshold_k": 2,
        "persistence_checkpoints": 3,
        "minimum_relative_effect": 0.2,
        "world_query_budget": 10,
        "candidate_generation_budget": 2,
        "candidate_evaluation_budget": 4,
        "cpu_hour_budget": 1,
        "candidate_generator": {
            "version": "candidate-generator-v0.1",
            "allowed_mutations": [
                "remove_term",
                "coefficient_low",
                "coefficient_high",
                "add_decay",
            ],
            "maximum_offspring_per_parent": 2,
            "maximum_candidates_per_task": 2,
        },
        "task_design": {"seeds_per_cluster": 5, "grid_size": 32, "steps": 100},
        "final_world_design": {
            "generator_version": "sealed-gray-scott-v1",
            "tasks_per_cluster": 5,
            "secret_bytes": 32,
            "seed_derivation": "hmac-sha256-protocol-cluster-index-v1",
            "task_format": "gray-scott-experiment-json-v1",
            "commitment_rule": "canonical-manifest-content-hash-v1",
        },
        "external_data_manifest": "data/manifests/the-well-gray-scott-test-v1.json",
        "external_fixture_manifest": "data/manifests/the-well-gray-scott-mini-v1.json",
        "execution_environment_spec": "configs/environments/confirmatory-v1.json",
        "numerical_tolerances": {
            "field_mean_absolute": 0.005,
            "field_max_absolute": 0.08,
            "summary_l2": 0.015,
        },
        "numerical_methods": {
            "primary_solver": "five_point",
            "primary_integrator": "euler",
            "reference_solver": "nine_point",
            "reference_integrator": "rk4",
        },
        "noise_calibration": {"floor": 0.01, "source": "development"},
        "survival_parameters": {
            "dormancy_after": 2,
            "death_after": 4,
            "death_on_hard_contradiction": True,
        },
        "viability_thresholds": {
            "minimum_evidence_score": 0.0,
            "minimum_predictive_gain": 0.01,
            "maximum_decoder_cost": 1.0,
        },
        "niche_capacities": {
            "current_predictive_best": 4,
            "minimum_description": 4,
            "validated_structure_gain": 4,
        },
        "evaluation_accounting": {
            "world_query": "one",
            "candidate_generation": "one",
            "candidate_evaluation": "one",
            "cache_hit": "zero",
        },
        "budget_scope": {
            "world_queries": "per replicate",
            "candidate_generation": "per task",
            "candidate_evaluation": "per task",
            "cpu_hours": "per run",
        },
        "statistical_parameters": {
            "bootstrap_samples": 2000,
            "confidence_level": 0.95,
            "censoring": "world_query_budget",
        },
        "power_design": {
            "simulations": 10,
            "bootstrap_samples": 20,
            "assumed_relative_effects": [0.2, 0.3, 0.4],
            "design_detectable_effect": 0.3,
            "minimum_power": 0.8,
        },
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


def test_protocol_config_rejects_unimplemented_numerical_method() -> None:
    config = deepcopy(_config())
    config["numerical_methods"]["reference_integrator"] = "invented"  # type: ignore[index]
    with pytest.raises(ValueError, match="numerical methods"):
        validate_protocol_config(config)
