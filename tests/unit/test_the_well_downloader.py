import hashlib
import json
import runpy
import sys
import urllib.request
from pathlib import Path

import pytest


def _manifest(path: Path, payload: bytes) -> Path:
    manifest = path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_id": "fixture",
                "source": "https://example.invalid",
                "version": "v1",
                "license": "CC-BY-4.0",
                "access_date": "2026-08-29",
                "shards": [
                    {
                        "path": "data/test/shard.bin",
                        "url": "https://example.invalid/shard.bin",
                        "bytes": len(payload),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    }
                ],
                "supports_novel_conditions": False,
                "supports_intervention": False,
            }
        ),
        encoding="utf-8",
    )
    return manifest


def _load_script() -> dict[str, object]:
    return runpy.run_path("scripts/fetch_the_well_shard.py")


def test_completed_partial_is_verified_without_network(tmp_path: Path, monkeypatch) -> None:
    payload = b"complete pinned shard"
    manifest = _manifest(tmp_path, payload)
    destination = tmp_path / "cache"
    destination.mkdir()
    (destination / "shard.bin.partial").write_bytes(payload)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fetch",
            "--manifest",
            str(manifest),
            "--shard",
            "data/test/shard.bin",
            "--destination",
            str(destination),
            "--allow-large-download",
            "--resume",
        ],
    )
    namespace = _load_script()
    namespace["main"]()
    assert (destination / "shard.bin").read_bytes() == payload
    assert not (destination / "shard.bin.partial").exists()


def test_rejected_range_preserves_partial(tmp_path: Path, monkeypatch) -> None:
    payload = b"complete pinned shard"
    manifest = _manifest(tmp_path, payload)
    destination = tmp_path / "cache"
    destination.mkdir()
    partial = destination / "shard.bin.partial"
    partial.write_bytes(payload[:4])

    class Response:
        status = 200
        headers: dict[str, str] = {}

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(urllib.request, "urlopen", lambda *_args, **_kwargs: Response())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fetch",
            "--manifest",
            str(manifest),
            "--shard",
            "data/test/shard.bin",
            "--destination",
            str(destination),
            "--allow-large-download",
            "--resume",
        ],
    )
    namespace = _load_script()
    with pytest.raises(namespace["ResumeRejected"]):
        namespace["main"]()
    assert partial.read_bytes() == payload[:4]
