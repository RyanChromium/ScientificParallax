"""Opt-in, checksum-enforced downloader for one declared The Well shard."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import urllib.request
from pathlib import Path

from scientific_parallax.core.data_manifest import load_dataset_manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--shard", required=True, help="exact shard path from the manifest")
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--allow-large-download", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if not args.allow_large_download:
        raise SystemExit("refusing multi-gigabyte download without --allow-large-download")
    manifest = load_dataset_manifest(args.manifest)
    try:
        shard = next(item for item in manifest["shards"] if item["path"] == args.shard)
    except StopIteration as error:
        raise SystemExit("shard is not declared in the manifest") from error

    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / Path(shard["path"]).name
    partial = output.with_suffix(output.suffix + ".partial")
    if output.exists() or partial.exists():
        raise FileExistsError(f"refusing to overwrite existing download: {output}")
    if shutil.disk_usage(destination).free < int(shard["bytes"] * 1.10):
        raise OSError("insufficient free space for shard plus checksum margin")

    digest = hashlib.sha256()
    written = 0
    try:
        with urllib.request.urlopen(shard["url"]) as response, partial.open("xb") as stream:
            while block := response.read(1024 * 1024):
                stream.write(block)
                digest.update(block)
                written += len(block)
        if written != shard["bytes"] or digest.hexdigest() != shard["sha256"]:
            raise ValueError("download does not match the frozen byte count and SHA-256")
        partial.replace(output)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    print(f"verified shard: {output}")


if __name__ == "__main__":
    main()
