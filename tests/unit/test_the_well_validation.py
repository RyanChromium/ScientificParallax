import hashlib
from pathlib import Path

import numpy as np

from scientific_parallax.core.data_manifest import load_dataset_manifest
from scientific_parallax.validation.the_well import load_the_well_fixture

FIXTURE = Path("data/fixtures/the-well-gray-scott-gliders-mini-v1.npz")
MANIFEST = Path("data/manifests/the-well-gray-scott-mini-v1.json")


def test_attributed_the_well_fixture_matches_manifest() -> None:
    manifest = load_dataset_manifest(MANIFEST)
    shard = manifest["shards"][0]
    assert FIXTURE.stat().st_size == shard["bytes"]
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == shard["sha256"]
    fixture = load_the_well_fixture(FIXTURE)
    assert fixture.metadata["source_shard_sha256"] == shard["derived_from_sha256"]
    assert fixture.metadata["modified"] is True
    assert fixture.fields.dtype == np.float32
    assert np.all(np.diff(fixture.time) > 0.0)


def test_fixture_contains_two_anonymous_compatible_fields() -> None:
    fixture = load_the_well_fixture(FIXTURE)
    assert fixture.metadata["field_order"] == ["A", "B"]
    assert fixture.fields.shape == (2, 2, 32, 32)
    assert not np.allclose(fixture.fields[0], fixture.fields[1])
