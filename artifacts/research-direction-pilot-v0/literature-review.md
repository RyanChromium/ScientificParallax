# Literature novelty-gap review

This review was limited by the frozen protocol to the critic's top two
directions.  It is a novelty *kill check*, not evidence that an unreported
search result establishes novelty.

## Direction 3 — paired-perturbation interaction

**Decision: stop as a generic research direction.**

The proposed contrast is scientifically valid, but its core move is already a
standard way to define interaction.  Hennig et al. define non-interaction as
superposition of two individual perturbation vectors and any deviation from
that superposition as interaction; they also decompose high-dimensional joint
responses into directed and emergent components.  Chatterjee et al. measured
individual and pairwise stimuli across doses and used them to predict
sequential and higher-order combinations.  Higher-order response is also a
formal subject in dynamical-systems theory: Galatolo and Sedro derive linear
and quadratic response terms for perturbed deterministic and random systems.

The candidate adds distance, lag, and order controls, but the dossier contains
no observed distance-, lag-, or order-dependent anomaly that selects this
question.  Without that evidence-specific hook, the proposal is a sound
factorial-screening template rather than a new scientific direction.

Primary sources:

- Hennig et al., “Mapping the perturbome network of cellular perturbations,”
  *Nature Communications* (2019):
  https://www.nature.com/articles/s41467-019-13058-9
- Chatterjee et al., “Pairwise agonist scanning predicts cellular signaling
  responses to combinatorial stimuli,” *Nature Biotechnology* (2010):
  https://www.nature.com/articles/nbt.1642
- Galatolo and Sedro, “Quadratic response of random and deterministic dynamical
  systems” (2019/2026 revision): https://arxiv.org/abs/1908.00025

## Direction 1 — symmetry-selective residual response

**Decision: stop as a generic research direction.**

Testing transformed copies and measuring equivariance error is also an
established research program.  Wang, Walters, and Yu directly study imperfect
symmetry in dynamics, distinguish physical symmetry breaking from effects such
as forcing, boundaries, and missing observations, and evaluate data/model
equivariance error.  Yang et al. discover nonlinear symmetries in
high-dimensional dynamical systems from data, while Calvo-Barlés et al. target
finite symmetry groups directly from observed trajectories.

Grid-refinement and boundary-separation controls remain good scientific
practice, but the dossier contains no orientation- or position-conditioned
residual that makes a particular symmetry violation a live discovery.  The
proposal therefore imports a mature diagnostic family without identifying a
new empirical gap.

Primary sources:

- Wang, Walters, and Yu, “Approximately Equivariant Networks for Imperfectly
  Symmetric Dynamics,” ICML (2022):
  https://proceedings.mlr.press/v162/wang22aa.html
- Yang et al., “Latent Space Symmetry Discovery,” ICML (2024):
  https://proceedings.mlr.press/v235/yang24g.html
- Calvo-Barlés, Rodrigo, and Martín-Moreno, “Learning finite symmetry groups of
  dynamical systems via equivariance detection” (2025):
  https://arxiv.org/abs/2503.03014

## Pilot-level conclusion

No direction passed the literature novelty-gap review.  Direction 4 was not
eligible for a third search under the frozen two-candidate limit and already
had a local-runtime concern.  Per the preregistered stop rule, v0 does not
rewrite or regenerate proposals and does not execute a downstream synthetic
experiment.

The failure is informative: a summary of earlier project failures constrains
what the LLM should avoid, but does not supply the empirical anomaly needed to
select a non-generic scientific question.  A next pilot must require each
direction to be causally anchored to a specific numeric fingerprint and must
test that removing or permuting that fingerprint changes the proposed
prediction.
