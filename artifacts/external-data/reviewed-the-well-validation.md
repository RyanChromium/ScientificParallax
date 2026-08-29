# Reviewed The Well external numerical validation

Exact clean code revision:
`2d144c3e1b8f85e963165a145a81418342db2740`

The source was the pinned 2,650,800,128-byte gliders test shard with SHA-256
`b22d51b7f1b33743934b608d94f845f458dd480fac4ee981cc516fb9170ff4e9`.
The validator used all 20 trajectories and predicted the first stored
10-second interval from each trajectory's exact initial fields.

| Method | Mean absolute error | Mean RMSE | Worst-trajectory RMSE |
|---|---:|---:|---:|
| Five-point + Euler (primary) | 0.02045 | 0.03511 | 0.05697 |
| Nine-point + RK4 (reference) | 0.01107 | 0.01717 | 0.03548 |

The reference RMSE improved by 51.1%. It passed all frozen acceptance limits:
at least 25% RMSE improvement, mean RMSE at most 0.02, and worst-trajectory
RMSE at most 0.04.

The JSON report SHA-256 is
`b569d062b9456d488b0dabe147fe574e41c91b5bd2716fde9036ce5ff6cc78f8`.
This is offline external numerical validation, not a queryable world and not
final sealed evidence.
