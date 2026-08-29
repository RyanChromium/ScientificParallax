"""Append-only lineage ledger and complete Step 4 lineage reconstruction."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from scientific_parallax.core.reproducibility import canonical_json, content_hash
from scientific_parallax.evolution.model import (
    DescriptionLength,
    LineageStatus,
    MutationRecord,
    ParadigmIndividual,
    ParadigmPhenotype,
    PatchCost,
    genotype_from_dict,
    genotype_to_dict,
)


@dataclass(frozen=True, slots=True)
class RebuiltLineage:
    individuals: dict[str, ParadigmIndividual]
    parents: dict[str, str | None]
    failure_reasons: dict[str, str]
    ledger_hash: str
    event_count: int


class LineageLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise FileExistsError(f"refusing to overwrite lineage ledger: {self.path}")
        self._previous_hash = "0" * 64
        self._next_index = 0

    def _append(self, event_type: str, payload: dict[str, Any]) -> str:
        body = {
            "schema_version": 1,
            "event_index": self._next_index,
            "event_type": event_type,
            "payload": payload,
            "previous_hash": self._previous_hash,
        }
        event_hash = content_hash(body)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(canonical_json({**body, "event_hash": event_hash}) + "\n")
            stream.flush()
        self._previous_hash = event_hash
        self._next_index += 1
        return event_hash

    def add_founder(self, individual: ParadigmIndividual) -> str:
        if individual.parent_id is not None or individual.generation != 0:
            raise ValueError("lineage founders cannot have parents")
        return self._append("founder_added", {"individual": individual_to_dict(individual)})

    def add_offspring(self, individual: ParadigmIndividual) -> str:
        if individual.parent_id is None or individual.generation == 0:
            raise ValueError("lineage offspring require a parent")
        return self._append("offspring_added", {"individual": individual_to_dict(individual)})

    def set_status(
        self,
        individual_id: str,
        status: LineageStatus,
        *,
        reason: str,
    ) -> str:
        if not reason:
            raise ValueError("lineage status changes require a reason")
        return self._append(
            "status_changed",
            {"individual_id": individual_id, "status": status.value, "reason": reason},
        )


def rebuild_lineage(path: Path) -> RebuiltLineage:
    previous_hash = "0" * 64
    individuals: dict[str, ParadigmIndividual] = {}
    parents: dict[str, str | None] = {}
    failure_reasons: dict[str, str] = {}
    event_count = 0
    with path.open(encoding="utf-8") as stream:
        for expected_index, line in enumerate(stream):
            event = json.loads(line)
            event_hash = event.pop("event_hash")
            if event.get("schema_version") != 1:
                raise ValueError("unsupported lineage event schema")
            if event.get("event_index") != expected_index:
                raise ValueError("lineage event index is not contiguous")
            if event.get("previous_hash") != previous_hash:
                raise ValueError("lineage hash chain is broken")
            if content_hash(event) != event_hash:
                raise ValueError("lineage event content was modified")
            payload = event["payload"]
            if event["event_type"] in {"founder_added", "offspring_added"}:
                individual = individual_from_dict(payload["individual"])
                identifier = individual.individual_id
                if identifier in individuals:
                    raise ValueError("lineage contains a duplicate individual")
                if individual.parent_id is not None:
                    parent = individuals.get(individual.parent_id)
                    if parent is None:
                        raise ValueError("lineage offspring precedes its parent")
                    if individual.generation != parent.generation + 1:
                        raise ValueError("lineage generation is inconsistent with its parent")
                    mutation = individual.mutation
                    if (
                        mutation is None
                        or mutation.parent_genotype_hash != parent.genotype.genotype_hash
                    ):
                        raise ValueError("lineage mutation does not bind its parent genotype")
                individuals[identifier] = individual
                parents[identifier] = individual.parent_id
            elif event["event_type"] == "status_changed":
                identifier = payload["individual_id"]
                if identifier not in individuals:
                    raise ValueError("lineage status refers to an unknown individual")
                status = LineageStatus(payload["status"])
                individuals[identifier] = replace(individuals[identifier], status=status)
                if status in {LineageStatus.DEAD, LineageStatus.EQUIVALENT_DUPLICATE}:
                    failure_reasons[identifier] = payload["reason"]
            else:
                raise ValueError(f"unsupported lineage event type: {event['event_type']}")
            previous_hash = event_hash
            event_count = expected_index + 1
    if not individuals:
        raise ValueError("lineage ledger is empty")
    return RebuiltLineage(individuals, parents, failure_reasons, previous_hash, event_count)


def verify_lineage(path: Path) -> None:
    rebuild_lineage(path)


def individual_to_dict(individual: ParadigmIndividual) -> dict[str, Any]:
    return {
        "genotype": genotype_to_dict(individual.genotype),
        "phenotype": asdict(individual.phenotype),
        "generation": individual.generation,
        "parent_id": individual.parent_id,
        "mutation": asdict(individual.mutation) if individual.mutation is not None else None,
        "patch_cost": asdict(individual.patch_cost),
        "cumulative_patch_cost": asdict(individual.cumulative_patch_cost),
        "description": asdict(individual.description),
        "evidence_score": individual.evidence_score,
        "predictive_gain": individual.predictive_gain,
        "validated_structure_gain": individual.validated_structure_gain,
        "checkpoints_below_viability": individual.checkpoints_below_viability,
        "hard_contradictions": individual.hard_contradictions,
        "status": individual.status.value,
    }


def individual_from_dict(payload: dict[str, Any]) -> ParadigmIndividual:
    mutation_payload = payload["mutation"]
    mutation = MutationRecord(**mutation_payload) if mutation_payload is not None else None
    phenotype_payload = payload["phenotype"]
    return ParadigmIndividual(
        genotype=genotype_from_dict(payload["genotype"]),
        phenotype=ParadigmPhenotype(
            tuple(phenotype_payload["behavior_signature"]),
            phenotype_payload["probe_set_hash"],
            phenotype_payload["schema_version"],
        ),
        generation=payload["generation"],
        parent_id=payload["parent_id"],
        mutation=mutation,
        patch_cost=PatchCost(**payload["patch_cost"]),
        cumulative_patch_cost=PatchCost(**payload["cumulative_patch_cost"]),
        description=DescriptionLength(**payload["description"]),
        evidence_score=payload["evidence_score"],
        predictive_gain=payload["predictive_gain"],
        validated_structure_gain=payload["validated_structure_gain"],
        checkpoints_below_viability=payload["checkpoints_below_viability"],
        hard_contradictions=payload["hard_contradictions"],
        status=LineageStatus(payload["status"]),
    )
