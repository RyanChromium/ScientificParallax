from copy import deepcopy
from pathlib import Path

import pytest

from scientific_parallax.core.data_manifest import (
    load_dataset_manifest,
    validate_dataset_manifest,
)


def test_committed_the_well_manifest_has_pinned_shards() -> None:
    path = Path("data/manifests/the-well-gray-scott-test-v1.json")
    manifest = load_dataset_manifest(path)
    assert len(manifest["shards"]) == 6
    assert len({shard["sha256"] for shard in manifest["shards"]}) == 6
    assert all("downloaded" not in shard for shard in manifest["shards"])


def test_manifest_rejects_invalid_checksum() -> None:
    manifest = load_dataset_manifest(Path("data/manifests/the-well-gray-scott-test-v1.json"))
    invalid = deepcopy(manifest)
    invalid["shards"][0]["sha256"] = "not-a-checksum"
    with pytest.raises(ValueError, match="sha256"):
        validate_dataset_manifest(invalid)
