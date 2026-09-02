# Changelog

## Unreleased

- Separate the research history into seven stable experiment records.
- Add a machine-readable experiment registry with bilingual questions, results,
  decisions, and claim boundaries.
- Add `experiments list`, `experiments show`, and `experiments validate` commands.
- Add bilingual paper sources and generated paper artifacts summarizing the LLM
  research-direction studies.
- Preserve all frozen evidence at its original path so previous hashes and links
  remain valid.

The package version remains `0.3.5`: the frozen experiment environment hashes
`uv.lock`, so a release bump must be performed as a separate, explicitly audited
migration rather than as part of repository organization.
