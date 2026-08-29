"""Create a deterministic, attributed CI fixture from a verified The Well shard."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path

import h5py
import numpy as np

from scientific_parallax.core.data_manifest import load_dataset_manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-cc-by-derived-fixture", action="store_true")
    return parser


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _npy_bytes(array: np.ndarray) -> bytes:
    stream = io.BytesIO()
    np.lib.format.write_array(stream, array, allow_pickle=False)
    return stream.getvalue()


def _write_deterministic_npz(
    path: Path,
    arrays: dict[str, np.ndarray],
    metadata: dict[str, object],
) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite fixture: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        members = {
            **{f"{name}.npy": _npy_bytes(value) for name, value in arrays.items()},
            "metadata.json": (
                json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode(),
        }
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info, members[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )


def main() -> None:
    args = _parser().parse_args()
    if not args.allow_cc_by_derived_fixture:
        raise SystemExit("fixture extraction requires --allow-cc-by-derived-fixture")
    manifest = load_dataset_manifest(args.manifest)
    source_size = args.source.stat().st_size
    try:
        shard = next(
            item for item in manifest["shards"] if Path(item["path"]).name == args.source.name
        )
    except StopIteration as error:
        raise ValueError("source is not declared by the dataset manifest") from error
    if source_size != shard["bytes"] or _file_sha256(args.source) != shard["sha256"]:
        raise ValueError("source does not match the frozen shard identity")

    with h5py.File(args.source, "r") as source:
        if str(source.attrs["dataset_name"]) != "gray_scott_reaction_diffusion":
            raise ValueError("source is not a Gray–Scott shard")
        time_indices = np.asarray([0, 1], dtype=np.int64)
        downsample = 4
        fields = np.stack(
            [
                np.asarray(source[f"t0_fields/{name}"][0, time_indices, ::downsample, ::downsample])
                for name in ("A", "B")
            ],
            axis=1,
        ).astype(np.float32)
        arrays = {
            "fields": fields,
            "time": np.asarray(source["dimensions/time"])[time_indices].astype(np.float32),
            "x": np.asarray(source["dimensions/x"])[::downsample].astype(np.float32),
            "y": np.asarray(source["dimensions/y"])[::downsample].astype(np.float32),
        }
        metadata: dict[str, object] = {
            "schema_version": 1,
            "dataset_id": manifest["dataset_id"],
            "source": manifest["source"],
            "source_revision": manifest["version"],
            "source_shard": shard["path"],
            "source_shard_sha256": shard["sha256"],
            "license": "CC-BY-4.0",
            "attribution": "The Well dataset, Polymathic AI collaboration",
            "modified": True,
            "transformation": (
                "trajectory 0, time indices 0 and 1, every fourth spatial sample, "
                "fields A and B stored as float32"
            ),
            "field_order": ["A", "B"],
            "feed": float(source["scalars/F"][()]),
            "kill": float(source["scalars/k"][()]),
        }
    _write_deterministic_npz(args.output, arrays, metadata)
    print(f"fixture sha256: {_file_sha256(args.output)}")


if __name__ == "__main__":
    main()
