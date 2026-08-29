"""Opt-in, checksum-enforced downloader for one declared The Well shard."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import urllib.error
import urllib.request
from pathlib import Path

from scientific_parallax.core.data_manifest import load_dataset_manifest


class ResumeRejected(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--shard", required=True, help="exact shard path from the manifest")
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--allow-large-download", action="store_true")
    parser.add_argument("--resume", action="store_true")
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
    if output.exists() or (partial.exists() and not args.resume):
        raise FileExistsError(f"refusing to overwrite existing download: {output}")
    digest = hashlib.sha256()
    written = partial.stat().st_size if partial.exists() else 0
    if written > shard["bytes"]:
        raise ValueError("partial download exceeds the declared shard size")
    remaining = shard["bytes"] - written
    if shutil.disk_usage(destination).free < int(remaining * 1.10):
        raise OSError("insufficient free space for remaining shard bytes plus margin")
    if written:
        with partial.open("rb") as existing:
            for block in iter(lambda: existing.read(1024 * 1024), b""):
                digest.update(block)
    if written == shard["bytes"]:
        if digest.hexdigest() != shard["sha256"]:
            partial.unlink()
            raise ValueError("completed partial does not match the frozen SHA-256")
        partial.replace(output)
        print(f"verified shard: {output}")
        return
    request = urllib.request.Request(shard["url"])
    if written:
        request.add_header("Range", f"bytes={written}-")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            if written:
                content_range = response.headers.get("Content-Range", "")
                if response.status != 206 or not content_range.startswith(f"bytes {written}-"):
                    raise ResumeRejected("server did not honor the requested verified byte range")
            mode = "ab" if written else "xb"
            with partial.open(mode) as stream:
                while block := response.read(1024 * 1024):
                    stream.write(block)
                    digest.update(block)
                    written += len(block)
        if written != shard["bytes"] or digest.hexdigest() != shard["sha256"]:
            raise ValueError("download does not match the frozen byte count and SHA-256")
        partial.replace(output)
    except ValueError:
        partial.unlink(missing_ok=True)
        raise
    except (OSError, ResumeRejected, TimeoutError, urllib.error.URLError):
        print(f"network transfer stopped; resumable partial preserved: {partial}")
        raise
    print(f"verified shard: {output}")


if __name__ == "__main__":
    main()
