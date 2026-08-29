# The Well Gray–Scott mini fixture

`the-well-gray-scott-gliders-mini-v1.npz` is a modified 16 KB subset of the
[Polymathic AI The Well Gray–Scott dataset](https://huggingface.co/datasets/polymathic-ai/gray_scott_reaction_diffusion).
The upstream dataset and this derived fixture are licensed under
[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).

Attribution: The Well dataset, Polymathic AI collaboration.

The fixture contains trajectory 0 at time indices 0 and 1 from the gliders
test shard, fields A and B, with every fourth spatial sample retained and values
stored as float32. It is only large enough to test schema, provenance, field
ordering, coordinates, and offline adapter behavior. It must not be presented
as an external performance benchmark.

The source shard revision and SHA-256, transformation, fixture byte count, and
fixture SHA-256 are recorded in
`data/manifests/the-well-gray-scott-mini-v1.json`. Regeneration requires the
`external-data` dependency extra and the explicit CC-BY derived-fixture flag.
