# Data management

Large datasets and generated trajectories are not committed to Git. Every
external or generated dataset must have a manifest under `data/manifests/`
before it is used in a reported experiment.

A manifest records the dataset version, license, access date, source, selected
shards, checksums, byte budget, generation code revision, and whether the data
source supports genuinely novel conditions or interventions. Table filtering
must not be described as an active experiment.

Local material belongs in `data/cache/`, which is ignored by Git.

The committed The Well Gray–Scott source manifest records six official test
shards. Each file is about 2.65 GB and is never bundled or downloaded in CI.
Local acquisition is deliberately opt-in:

```bash
uv run python scripts/fetch_the_well_shard.py \
  --manifest data/manifests/the-well-gray-scott-test-v1.json \
  --shard data/test/gray_scott_reaction_diffusion_gliders_F_0.014_k_0.054.hdf5 \
  --destination data/cache/the-well \
  --allow-large-download
```

Add `--resume` to continue a preserved `.partial` transfer. The downloader
rehashes the existing bytes before requesting the exact remaining byte range.

The downloader refuses undeclared shards and existing destinations, checks free
space, and only promotes the partial file after both byte count and SHA-256
match. Downloading a shard does not edit the committed source manifest;
validation status belongs in a write-once report.

The 16 KB CI fixture is a modified CC-BY-4.0 subset of the verified gliders
shard. It contains trajectory 0, the first two stored times, fields A/B, and
every fourth spatial sample. Recreate it only with explicit license
acknowledgment:

```bash
uv run --extra external-data python scripts/extract_the_well_fixture.py \
  --source data/cache/the-well/gray_scott_reaction_diffusion_gliders_F_0.014_k_0.054.hdf5 \
  --manifest data/manifests/the-well-gray-scott-test-v1.json \
  --output /tmp/the-well-mini.npz \
  --allow-cc-by-derived-fixture
```

Run the full 20-trajectory numerical validation with:

```bash
uv run --extra external-data python scripts/validate_the_well_shard.py \
  --shard data/cache/the-well/gray_scott_reaction_diffusion_gliders_F_0.014_k_0.054.hdf5 \
  --manifest data/manifests/the-well-gray-scott-test-v1.json \
  --output artifacts/external-data/runs/the-well-validation.json
```
