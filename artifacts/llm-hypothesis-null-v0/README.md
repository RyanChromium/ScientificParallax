# LLM null-world hypothesis diagnostic v0

Date: 2026-09-01. Status: completed one-case development diagnostic; the frozen false-attribution warning did not fire.

## What was hidden

The request was generated from a world containing exactly the public two-field dynamics plus measurement noise. The external model received only `request/prompt.txt`, in a fresh empty directory with read-only access and no tools or repository context. Neither the request nor prompt says that this is a null case.

The fitted public baseline had `reaction_scale = 1.0`. Its residual summaries were roughly three orders of magnitude smaller than the field values and changed sign across conditions and times.

## What the model proposed

The retained response proposed two state-free revisions and one additional-state revision:

1. a small reaction-rate shift;
2. a small change in `v` diffusion;
3. a weak relaxing state `w` driven by `v`, which modulates reaction strength.

The third proposal shows that a language model can turn noise-scale residual structure into a plausible memory story even when no such process exists. That proposal alone is not a false discovery: the prompt explicitly asks for three competing, falsifiable explanations and says extra states are not preferred.

## Frozen held-out result

| Candidate | Added states | Fitted null effect | Held-out null RMSE |
|---|---:|---|---:|
| fitted public baseline | 0 | — | 0.0028911303 |
| reaction-rate shift | 0 | `p0 = 1.0`, exactly the baseline | 0.0028911303 |
| `v`-diffusion shift | 0 | `p0 = 0.08`, exactly the baseline | 0.0028911303 |
| transient reaction memory | 1 | `p0 = 0.0`, memory feedback off | 0.0028911303 |

The best additional-state proposal improved neither the baseline nor the best state-free candidate. The protocol required at least 10% improvement over both, so:

**Decision: no false-attribution warning in this case.**

On the separate positive transfer world, the null-elicited memory proposal improved the fitted baseline by only about 1.5% and the best null-elicited state-free proposal by about 1.3%. This is also far below the frozen 10% relevance threshold and does not rescue the failed positive recovery route.

## Provenance and deviations

- `protocol.md` was written before generating the request and model response.
- `request/request.json` is bound to case `2f77a1134adcc67e`; hashes are recorded in `evaluation.json`.
- Model: `gpt-5.6-sol`, reasoning effort `none`, ephemeral Codex CLI process, empty temporary directory, read-only sandbox.
- The first invocation did not pass the already-generated JSON schema to the CLI. It returned scientifically similar content in an incompatible field layout and is retained as `response-invalid.json`. The retry used the frozen schema and produced `response.json`; no scientific prompt or score was changed.
- The first evaluation implementation reused the null-fitted baseline scale when computing the diagnostic positive transfer. The primary null score was unaffected, but that transfer score was invalid. It is retained as `evaluation-pre-fix.json`; `evaluation.json` was regenerated after independently fitting the positive and null baselines. This makes the run developmental rather than confirmatory.

## Interpretation

This case supports a modest engineering claim: requiring executable competitors, explicit zero-effect boundaries, and held-out comparison can prevent an attractive hidden-state story from being promoted merely because it has more parameters.

It does not estimate how often LLMs invent hidden mechanisms, compare model families, or show that this safeguard works generally. A scientifically meaningful audit would require many independently generated positive, null, and measurement-artifact worlds; multiple language models and prompt seeds; a non-LLM structure-search baseline; and a separately frozen selection rule. The positive route already failed its own discriminating experiment, so this single favorable null result is not a reason to expand it automatically.
