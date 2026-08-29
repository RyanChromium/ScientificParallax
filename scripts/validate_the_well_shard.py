"""Validate one pinned The Well shard against both local numerical paths."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scientific_parallax.core.data_manifest import load_dataset_manifest
from scientific_parallax.core.reproducibility import capture_environment, content_hash
from scientific_parallax.validation.the_well import validate_the_well_shard


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trajectories", type=int, default=20)
    return parser


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = _parser().parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite validation report: {args.output}")
    manifest = load_dataset_manifest(args.manifest)
    try:
        shard_spec = next(
            item for item in manifest["shards"] if Path(item["path"]).name == args.shard.name
        )
    except StopIteration as error:
        raise ValueError("shard is not declared by the manifest") from error
    shard_hash = _file_sha256(args.shard)
    if args.shard.stat().st_size != shard_spec["bytes"] or shard_hash != shard_spec["sha256"]:
        raise ValueError("shard bytes do not match the frozen manifest")
    validation = validate_the_well_shard(args.shard, args.trajectories)
    report = {
        "schema_version": 1,
        "status": "validated" if validation.passed else "failed",
        "scope": "offline external numerical validation; not a queryable or final world",
        "source_manifest_hash": content_hash(manifest),
        "source_shard": shard_spec["path"],
        "source_shard_sha256": shard_hash,
        "validation": validation.to_dict(),
        "environment": capture_environment(Path.cwd()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
