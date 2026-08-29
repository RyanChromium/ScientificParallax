"""Version boundaries and explicit migrations for persistent artifacts."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ArtifactKind(StrEnum):
    MANIFEST = "manifest"
    LEDGER_EVENT = "ledger_event"
    PARADIGM_IR = "paradigm_ir"
    REPORT = "report"


CURRENT_SCHEMA_VERSION: dict[ArtifactKind, int] = {
    ArtifactKind.MANIFEST: 1,
    ArtifactKind.LEDGER_EVENT: 1,
    ArtifactKind.PARADIGM_IR: 1,
    ArtifactKind.REPORT: 1,
}


def validate_schema(kind: ArtifactKind, artifact: dict[str, Any]) -> int:
    version = artifact.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError(f"{kind.value} requires a positive integer schema_version")
    current = CURRENT_SCHEMA_VERSION[kind]
    if version > current:
        raise ValueError(f"unsupported future {kind.value} schema: {version} > {current}")
    return version


Migration = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class MigrationKey:
    kind: ArtifactKind
    source_version: int


class MigrationRegistry:
    """Only registered one-version transitions may rewrite persisted data."""

    def __init__(self) -> None:
        self._migrations: dict[MigrationKey, Migration] = {}

    def register(self, kind: ArtifactKind, source_version: int, migration: Migration) -> None:
        key = MigrationKey(kind, source_version)
        if source_version < 1 or key in self._migrations:
            raise ValueError("migration source must be positive and registered once")
        self._migrations[key] = migration

    def migrate_current(self, kind: ArtifactKind, artifact: dict[str, Any]) -> dict[str, Any]:
        value = deepcopy(artifact)
        version = validate_schema(kind, value)
        target = CURRENT_SCHEMA_VERSION[kind]
        while version < target:
            migration = self._migrations.get(MigrationKey(kind, version))
            if migration is None:
                raise ValueError(
                    f"no registered {kind.value} migration from schema version {version}"
                )
            value = migration(value)
            next_version = value.get("schema_version")
            if next_version != version + 1:
                raise ValueError("migrations must advance exactly one schema version")
            version = next_version
        return value
