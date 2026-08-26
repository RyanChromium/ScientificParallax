# Data management

Large datasets and generated trajectories are not committed to Git. Every
external or generated dataset must have a manifest under `data/manifests/`
before it is used in a reported experiment.

A manifest records the dataset version, license, access date, source, selected
shards, checksums, byte budget, generation code revision, and whether the data
source supports genuinely novel conditions or interventions. Table filtering
must not be described as an active experiment.

Local material belongs in `data/cache/`, which is ignored by Git.
