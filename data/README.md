# Data management

Large datasets and generated trajectories are not committed to Git. Every
external or generated dataset must have a manifest under `data/manifests/`
before it is used in a reported experiment.

A manifest records the dataset version, license, access date, source, selected
shards, checksums, byte budget, generation code revision, and whether the data
source supports genuinely novel conditions or interventions. Table filtering
must not be described as an active experiment.

Local material belongs in `data/cache/`, which is ignored by Git.

The committed The Well Gray–Scott manifest records six official test shards but
marks every shard as undownloaded. Each file is about 2.65 GB. Downloading one is
therefore deliberately opt-in:

```bash
uv run python scripts/fetch_the_well_shard.py \
  --manifest data/manifests/the-well-gray-scott-test-v1.json \
  --shard data/test/gray_scott_reaction_diffusion_gliders_F_0.014_k_0.054.hdf5 \
  --destination data/cache/the-well \
  --allow-large-download
```

The downloader refuses undeclared shards and existing destinations, checks free
space, and only promotes the partial file after both byte count and SHA-256
match. Downloading a shard does not edit the committed manifest; validation
status belongs in a write-once run manifest.
