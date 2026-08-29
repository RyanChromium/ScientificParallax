# Gray–Scott development baseline

Status: Step 2–3 development implementation. These runs are not final sealed
evidence and must not be cited as confirmation of co-evolution.

## Online world

The world implements the standard two-field Gray–Scott reaction–diffusion
equations. A question specifies parameters, initial-condition family, boundary,
solver, local pulse, and measurement operator.

Two spatial discretizations are available:

- `five_point`: axial nearest-neighbor finite-difference Laplacian;
- `nine_point`: axial plus diagonal isotropic finite-difference Laplacian.

They share the physical equation but not the spatial stencil. Agreement is a
numerical-artifact diagnostic, not proof of physical truth. The primary path
uses explicit Euler, while the reference path can use separately implemented
classical RK4 time integration. The external Well data uses a still more
independent Fourier spectral plus ETDRK4 solver.

Measurements support invertible channel mixing, anonymous field names,
downsampling, one-channel partial observation, masking, Gaussian noise, and
different sampling intervals. Complete parameter/initial-condition families
can be held out as blocks.

## Fixed baselines

The fixed representation is a declared vector of experimental conditions. A
ridge regressor and bootstrap ensemble predict anonymous field summaries.
Hidden-parameter evaluation holds out the highest feed-rate block rather than
randomly splitting trajectories.

The fixed paradigm pool contains eight executable Gray–Scott law variants,
including the standard law. Five question-selection strategies share the same
pool, observations, evidence rule, and query budget:

1. random selection;
2. parameter/condition coverage;
3. bootstrap-ensemble active learning;
4. maximum candidate disagreement;
5. Monte Carlo Bayesian experimental design.

Run the development benchmark with:

```bash
uv run scientific-parallax gray-scott benchmark \
  --config configs/experiments/gray-scott-baseline.json \
  --output artifacts/gray_scott/runs/development
```

Output directories are write-once. Each report has a run manifest containing
the configuration hash, environment, Git revision, inputs, outputs, and output
content hash. The run also preserves every query's posterior history and
selection order, every candidate predictive mean and noise scale, and every
bootstrap ensemble member prediction on the held-out block. A posterior-0.95
success rate is reported as a development diagnostic, not a confirmation claim.

Each strategy and seed also receives an independent hash-chained ledger. The
selected question, all candidate summary predictions, and the evidence state
are appended before observation; the observation summary and updated posterior
must reference that prediction event.

The report also records the ratio between held-out ensemble RMSE and average
predicted standard deviation. A ratio above one indicates under-dispersed
uncertainty and must be treated as a calibration failure rather than hidden by
the ensemble mean.
